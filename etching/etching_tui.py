"""Etching Drawer — Textual TUI.

A modern terminal Etch-A-Sketch. Arrow keys move the pen and draw a coloured
trail; W/E/Z/X for diagonals; C cycles the brush; S shakes the canvas; P
plays back the stroke history; Ctrl+Q quits.

Run:
    uv run python etching/etching_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from etching import DEFAULT_HEIGHT, DEFAULT_WIDTH, PALETTE, Canvas

# Colour palette indexed by the same position as etching.PALETTE — gives the
# rendered TUI canvas a different colour per brush slot.
BRUSH_COLORS = (
    'cyan', 'magenta', 'yellow', 'green', 'red', 'blue',
)

DIAGONAL_KEYS = {
    'w': 'up-left', 'e': 'up-right',
    'z': 'down-left', 'x': 'down-right',
}


class EtchingApp(App):
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

    #canvas-wrap {
        align-horizontal: center;
        height: auto;
        padding: 1 2;
    }

    #canvas {
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
        padding: 1 2;
        height: auto;
        width: auto;
    }

    #status {
        background: #1e293b;
        color: #cbd5e1;
        text-align: center;
        padding: 1 2;
        margin: 1 4;
    }
    """

    BINDINGS = [
        Binding('up', 'move("up")', 'Up', priority=True),
        Binding('down', 'move("down")', 'Down', priority=True),
        Binding('left', 'move("left")', 'Left', priority=True),
        Binding('right', 'move("right")', 'Right', priority=True),
        Binding('w', 'move("up-left")', 'NW', show=False, priority=True),
        Binding('e', 'move("up-right")', 'NE', show=False, priority=True),
        Binding('z', 'move("down-left")', 'SW', show=False, priority=True),
        Binding('x', 'move("down-right")', 'SE', show=False, priority=True),
        Binding('c', 'cycle_color', 'Cycle colour'),
        Binding('s', 'shake', 'Shake'),
        Binding('p', 'playback', 'Playback'),
        Binding('space', 'toggle_pen', 'Pen'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]
    TITLE = 'Etching Drawer'

    def __init__(self) -> None:
        super().__init__()
        self.model = Canvas(DEFAULT_WIDTH, DEFAULT_HEIGHT)
        # Per-cell colour grid mirrors the model grid; populated as the user
        # draws so we can re-render the whole canvas with rich markup.
        self.colour_grid: list[list[str]] = [
            ['' for _ in range(DEFAULT_WIDTH)]
            for _ in range(DEFAULT_HEIGHT)
        ]
        # Stamp the starting cell's colour.
        self.colour_grid[self.model.cy][self.model.cx] = self._brush_colour()

    def _brush_colour(self) -> str:
        idx = PALETTE.index(self.model.brush) \
            if self.model.brush in PALETTE else 0
        return BRUSH_COLORS[idx % len(BRUSH_COLORS)]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('ETCHING DRAWER', id='title')
        yield Static(
            'arrows: draw   w/e/z/x: diagonals   c: colour   '
            's: shake   p: playback   space: pen   Ctrl+Q: quit',
            id='subtitle')
        yield Static('', id='canvas')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._render_canvas()
        self._update_status()

    # ---- actions --------------------------------------------------------

    def action_move(self, direction: str) -> None:
        old = (self.model.cy, self.model.cx)
        self.model.move(direction)
        new = (self.model.cy, self.model.cx)
        if new != old and self.model.pen_down:
            self.colour_grid[new[0]][new[1]] = self._brush_colour()
        self._render_canvas()
        self._update_status()

    def action_cycle_color(self) -> None:
        self.model.cycle_brush()
        self._update_status('colour cycled')

    def action_shake(self) -> None:
        self.model.clear()
        self.colour_grid = [
            ['' for _ in range(DEFAULT_WIDTH)]
            for _ in range(DEFAULT_HEIGHT)
        ]
        if self.model.pen_down:
            self.colour_grid[self.model.cy][self.model.cx] = \
                self._brush_colour()
        self._render_canvas()
        self._update_status('shaken')

    def action_toggle_pen(self) -> None:
        state = self.model.toggle_pen()
        self._update_status(f'pen {"DOWN" if state else "UP"}')

    def action_playback(self) -> None:
        # Snapshot, then replay onto a fresh colour grid using the timer.
        history = list(self.model.history)
        # Reset display state but keep model intact.
        self.colour_grid = [
            ['' for _ in range(DEFAULT_WIDTH)]
            for _ in range(DEFAULT_HEIGHT)
        ]
        backup_grid = [row.copy() for row in self.model.grid]
        self.model.grid = [
            [' ' for _ in range(DEFAULT_WIDTH)]
            for _ in range(DEFAULT_HEIGHT)
        ]
        self._render_canvas()
        self._update_status('playback…')

        # Step through history one stroke per timer tick.
        idx = {'i': 0}

        def step() -> None:
            if idx['i'] >= len(history):
                # Playback complete: restore the live canvas state.
                self.model.grid = backup_grid
                # Recolour everything based on whatever is currently drawn.
                self._update_status('playback done')
                return
            stroke = history[idx['i']]
            self.model.grid[stroke.y][stroke.x] = stroke.char
            colour_idx = PALETTE.index(stroke.char) \
                if stroke.char in PALETTE else 0
            self.colour_grid[stroke.y][stroke.x] = \
                BRUSH_COLORS[colour_idx % len(BRUSH_COLORS)]
            self._render_canvas(cursor_y=stroke.y, cursor_x=stroke.x)
            idx['i'] += 1
            self.set_timer(0.04, step)

        step()

    # ---- rendering ------------------------------------------------------

    def _render_canvas(self, cursor_y: int | None = None,
                       cursor_x: int | None = None) -> None:
        cy = self.model.cy if cursor_y is None else cursor_y
        cx = self.model.cx if cursor_x is None else cursor_x
        rows = []
        for y, row in enumerate(self.model.grid):
            chars = []
            for x, cell in enumerate(row):
                is_cursor = (y == cy and x == cx)
                if is_cursor and cell == ' ':
                    chars.append('[reverse #38bdf8]·[/]')
                elif is_cursor:
                    colour = self.colour_grid[y][x] or 'white'
                    chars.append(f'[reverse {colour}]{cell}[/]')
                elif cell != ' ':
                    colour = self.colour_grid[y][x] or 'white'
                    chars.append(f'[{colour}]{cell}[/]')
                else:
                    chars.append(' ')
            rows.append(''.join(chars))
        self.query_one('#canvas', Static).update('\n'.join(rows))

    def _update_status(self, extra: str = '') -> None:
        msg = (f'[bold]pos[/] ({self.model.cx},{self.model.cy})   '
               f'[bold]brush[/] [{self._brush_colour()}]'
               f'{self.model.brush}[/]   '
               f'[bold]pen[/] {"DOWN" if self.model.pen_down else "UP"}   '
               f'[bold]strokes[/] {len(self.model.history)}')
        if extra:
            msg = f'[bold green]{extra}[/]   •   {msg}'
        self.query_one('#status', Static).update(msg)


if __name__ == '__main__':
    EtchingApp().run()
