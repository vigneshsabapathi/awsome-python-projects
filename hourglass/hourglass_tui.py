"""Hourglass — Textual TUI.

A modern terminal animation of the Hourglass simulation. Sand falls one
grain per frame; the bottom pile builds with an angle-of-repose feel.

Bindings:
    f         flip
    space     pause / resume
    r         reset
    e         earthquake (scatter the bottom pile)
    Ctrl+Q    quit

Run:
    uv run python hourglass/hourglass_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from hourglass import DEFAULT_WIDTH, Hourglass

# Golden palette tuned for the dark Textual default theme.
SAND_COLORS = (
    '#fde68a',  # pale honey (newest)
    '#fcd34d',
    '#fbbf24',
    '#f59e0b',
    '#d97706',  # deep amber (oldest)
)
WALL = '#94a3b8'
FRAME = '#cbd5e1'
NECK = '#64748b'


class HourglassWidget(Static):
    """Renders the hourglass with Rich markup for color-graded grains."""

    DEFAULT_CSS = """
    HourglassWidget {
        content-align: center middle;
        height: auto;
        width: auto;
        padding: 1 2;
    }
    """

    def __init__(self, hourglass: Hourglass) -> None:
        super().__init__()
        self.hourglass = hourglass

    def render_hourglass(self) -> str:
        h = self.hourglass
        W = h.width
        lines: list[str] = []

        # Top frame.
        lines.append(f'[{FRAME}]+' + '=' * W + '+[/]')

        # Top chamber.
        for r in range(h.H):
            cells: list[str] = [f'[{WALL}]|[/]']
            for c in range(W):
                if r > 0 and c == r - 1:
                    cells.append(f'[{WALL}]\\[/]')
                elif r > 0 and c == W - r:
                    cells.append(f'[{WALL}]/[/]')
                elif h._in_top_triangle(r, c) and h.grid[r][c] is not None:
                    cells.append(self._grain_markup(h.grid[r][c]))
                else:
                    cells.append(' ')
            cells.append(f'[{WALL}]|[/]')
            lines.append(''.join(cells))

        # Neck row.
        nr: list[str] = [f'[{WALL}]|[/]']
        for c in range(W):
            if c == h.neck_col - 1:
                nr.append(f'[{WALL}]\\[/]')
            elif c == h.neck_col + 1:
                nr.append(f'[{WALL}]/[/]')
            elif c == h.neck_col:
                v = h.grid[h.H][h.neck_col]
                nr.append(self._grain_markup(v) if v is not None else ' ')
            else:
                nr.append(' ')
        nr.append(f'[{WALL}]|[/]')
        lines.append(''.join(nr))

        # Bottom chamber.
        for r_local in range(h.H):
            r = h.H + 1 + r_local
            left = h.neck_col - r_local - 1
            right = h.neck_col + r_local + 2
            cells = [f'[{WALL}]|[/]']
            for c in range(W):
                if r_local < h.H - 1 and c == left - 1:
                    cells.append(f'[{WALL}]/[/]')
                elif r_local < h.H - 1 and c == right:
                    cells.append(f'[{WALL}]\\[/]')
                elif h._in_bottom_triangle(r, c) and h.grid[r][c] is not None:
                    cells.append(self._grain_markup(h.grid[r][c]))
                else:
                    cells.append(' ')
            cells.append(f'[{WALL}]|[/]')
            lines.append(''.join(cells))

        # Bottom frame.
        lines.append(f'[{FRAME}]+' + '=' * W + '+[/]')
        return '\n'.join(lines)

    def _grain_markup(self, age: int) -> str:
        idx = (max(0, age) // 8) % len(SAND_COLORS)
        return f'[{SAND_COLORS[idx]}]o[/]'

    def refresh_render(self) -> None:
        self.update(self.render_hourglass())


class HourglassApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #stage {
        align: center middle;
        height: auto;
        width: 100%;
        padding: 1 0;
    }

    #status {
        text-align: center;
        padding: 1;
        color: #cbd5e1;
    }

    .paused #status {
        color: #f59e0b;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding('f', 'flip', 'Flip'),
        Binding('space', 'toggle_pause', 'Pause'),
        Binding('r', 'reset', 'Reset'),
        Binding('e', 'shake', 'Earthquake'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Hourglass'
    INTERVAL = 1 / 12  # 12 fps

    def __init__(self, width: int = DEFAULT_WIDTH) -> None:
        super().__init__()
        self.hourglass = Hourglass(width=width)
        self.paused: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('HOURGLASS', id='title')
        yield Static('f flip · space pause · r reset · e earthquake',
                     id='subtitle')
        with Vertical(id='stage'):
            self.glass = HourglassWidget(self.hourglass)
            yield self.glass
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self.glass.refresh_render()
        self._update_status()
        self.set_interval(self.INTERVAL, self._tick)

    def _tick(self) -> None:
        if self.paused:
            return
        if self.hourglass.is_done():
            return
        self.hourglass.step()
        self.glass.refresh_render()
        self._update_status()

    def _update_status(self) -> None:
        h = self.hourglass
        text = (f'top {h.top_count()}   bottom {h.bottom_count()}'
                f'   step {h.step_count}')
        if self.paused:
            text = 'PAUSED · ' + text
        if h.is_done() and not self.paused:
            text = 'drained · press f to flip · ' + text
        self.query_one('#status', Static).update(text)

    # -- actions -------------------------------------------------------

    def action_flip(self) -> None:
        self.hourglass.flip()
        self.glass.refresh_render()
        self._update_status()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._update_status()

    def action_reset(self) -> None:
        self.hourglass.reset()
        self.glass.refresh_render()
        self._update_status()

    def action_shake(self) -> None:
        self.hourglass.shake()
        self.glass.refresh_render()
        self._update_status()


if __name__ == '__main__':
    HourglassApp().run()
