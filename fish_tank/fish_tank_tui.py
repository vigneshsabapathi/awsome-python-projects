"""Fish Tank — Textual TUI.

Deep-blue Tailwind palette. Fish and bubbles rendered in cyan/white
on a dark water background. Schooling behaviour is always active.

Bindings
--------
- space    play/pause
- n        add a fish
- +        increase speed
- -        decrease speed
- ctrl+q   quit

Run:
    uv run python fish_tank/fish_tank_tui.py
"""
from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from fish_tank import Tank, _ANSI_FG  # noqa: F401 — colour map used for Rich markup

# ── Tailwind-dark palette ─────────────────────────────────────────────────────
BG      = '#0f172a'   # slate-900
PANEL   = '#1e293b'   # slate-800
BORDER  = '#334155'   # slate-700
WATER   = '#0c1a2e'   # custom deep-water
SURFACE = '#38bdf8'   # sky-400  (wave tilde row)
FISH_C  = '#67e8f9'   # cyan-300
BUBBLE  = '#bae6fd'   # sky-200
PLANT_C = '#4ade80'   # green-400
SEAFLOOR= '#64748b'   # slate-500
TEXT    = '#f8fafc'
MUTED   = '#94a3b8'
ACCENT  = '#38bdf8'

# Map fish_tank color names to Rich colour strings
_RICH_COLOR: dict[str, str] = {
    'red':     '#f87171',
    'orange':  '#fb923c',
    'yellow':  '#fde047',
    'green':   '#4ade80',
    'cyan':    '#67e8f9',
    'blue':    '#60a5fa',
    'magenta': '#e879f9',
    'white':   '#f8fafc',
}

TANK_W = 88
TANK_H = 20

MIN_FPS = 2
MAX_FPS = 20
DEFAULT_FPS = 8


class TankView(Static):
    """Widget that renders the Tank as coloured Rich Text."""

    def __init__(self, tank: Tank) -> None:
        super().__init__()
        self._tank = tank

    def render_tank(self) -> Text:
        text = Text(no_wrap=True, overflow='fold')
        raw = self._tank.render(color=False)
        lines = raw.splitlines()

        # We need to re-render with per-cell colour knowledge.
        # Instead of duplicating render logic, we parse the plain text and
        # apply colour heuristics that match the visual intent.
        tank = self._tank
        w = tank.width

        # Build per-cell colour map same as Tank.render internals
        color_grid: list[list[str]] = [[''] * w for _ in range(tank.height)]

        # Surface row
        for c in range(w):
            color_grid[0][c] = SURFACE

        # Seafloor
        for c in range(w):
            color_grid[tank.height - 1][c] = SEAFLOOR

        # Plants
        for plant in tank.plants:
            for cx, cy, _ch in plant.cells(tank.height):
                if 0 <= cy < tank.height and 0 <= cx < w:
                    color_grid[cy][cx] = PLANT_C

        # Bubbles
        for bubble in tank.bubbles:
            by = int(bubble.y)
            bx = bubble.x
            if 1 <= by < tank.height - 1 and 0 <= bx < w:
                color_grid[by][bx] = BUBBLE

        # Fish
        for fish in tank.fish:
            row = int(fish.y)
            if not (1 <= row < tank.height - 1):
                continue
            art = fish.art
            fish_color = _RICH_COLOR.get(fish.color, '#f8fafc')
            for i in range(len(art)):
                col = int(fish.x) + i
                if 0 <= col < w:
                    color_grid[row][col] = fish_color

        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                col = color_grid[r][c] if r < tank.height else ''
                if col:
                    text.append(ch, style=col)
                else:
                    text.append(ch, style=MUTED)
            if r < len(lines) - 1:
                text.append('\n')

        return text


class FishTankApp(App):
    CSS = f"""
    Screen {{
        background: {BG};
        color: {TEXT};
        align: center top;
    }}
    #title {{
        text-align: center;
        text-style: bold;
        color: {ACCENT};
        padding-top: 1;
    }}
    #subtitle {{
        text-align: center;
        color: {MUTED};
        padding-bottom: 1;
    }}
    #tank_panel {{
        align: center middle;
        background: {PANEL};
        border: tall {BORDER};
        padding: 0 1;
        margin: 0 2;
    }}
    #tank_view {{
        width: auto;
        height: auto;
        background: {WATER};
    }}
    #stats {{
        text-align: center;
        color: {MUTED};
        padding: 0 2 1 2;
    }}
    """

    BINDINGS = [
        Binding('space',  'toggle_play', 'Play/Pause'),
        Binding('n',      'add_fish',    'Add fish'),
        Binding('+',      'speed_up',    'Faster'),
        Binding('-',      'slow_down',   'Slower'),
        Binding('ctrl+q', 'quit',        'Quit'),
    ]

    TITLE = 'Fish Tank'

    def __init__(self) -> None:
        super().__init__()
        self._tank    = Tank(TANK_W, TANK_H, 5)
        self._fps     = DEFAULT_FPS
        self._running = True
        self._frame   = 0
        self._timer   = None
        self._view: TankView | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('FISH TANK', id='title')
        yield Static(
            'space pause • n add fish • +/- speed • ctrl+q quit',
            id='subtitle',
        )
        self._view = TankView(self._tank)
        self._view.id = 'tank_view'
        panel = Static(id='tank_panel')
        from textual.containers import Vertical
        with Vertical(id='tank_panel'):
            yield self._view
        yield Static('', id='stats')
        yield Footer()

    def on_mount(self) -> None:
        self._start_timer()
        self._refresh()

    def _start_timer(self) -> None:
        if self._timer:
            self._timer.stop()
        self._timer = self.set_interval(1.0 / self._fps, self._tick)

    def _tick(self) -> None:
        if not self._running:
            return
        self._tank.step()
        self._frame += 1
        self._refresh()

    def _refresh(self) -> None:
        view = self.query_one('#tank_view', TankView)
        view.update(view.render_tank())
        self._update_stats()

    def _update_stats(self) -> None:
        status = f'[{ACCENT}]{"PLAYING" if self._running else "PAUSED "}[/]'
        stats = (
            f'{status}   '
            f'frame [{TEXT}]{self._frame:>5d}[/]   '
            f'fish [{TEXT}]{len(self._tank.fish):>2d}[/]   '
            f'bubbles [{TEXT}]{len(self._tank.bubbles):>2d}[/]   '
            f'fps [{TEXT}]{self._fps}[/]   '
            f'schooling [{TEXT}]ON[/]'
        )
        self.query_one('#stats', Static).update(stats)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_toggle_play(self) -> None:
        self._running = not self._running
        self._update_stats()

    def action_add_fish(self) -> None:
        self._tank.add_fish()
        self._refresh()

    def action_speed_up(self) -> None:
        self._fps = min(self._fps + 2, MAX_FPS)
        self._start_timer()
        self._update_stats()

    def action_slow_down(self) -> None:
        self._fps = max(self._fps - 2, MIN_FPS)
        self._start_timer()
        self._update_stats()


if __name__ == '__main__':
    FishTankApp().run()
