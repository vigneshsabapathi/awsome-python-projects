"""Deep Cave — Textual TUI.

Dark cave palette terminal UI. Rows scroll downward in a fixed-size viewport
showing the procedurally-generated tunnel walls and the meandering walkable
floor. Hazards and treasures (``*`` gems, ``~`` water, ``o`` boulders) get
a colored ANSI tint via Rich markup.

Bindings
--------
- space   play/pause
- +/-     speed up/slow down
- r       reseed (new random cave)
- ctrl+q  quit

Run:
    uv run python deep_cave/deep_cave_tui.py
"""
from __future__ import annotations

import random

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from deep_cave import (
    DEFAULT_WIDTH,
    HAZARDS,
    WALL,
    hazard_label,
    initial_tunnel,
    next_row,
)


# Tailwind dark cave palette
BG = '#0f172a'
PANEL = '#1c1917'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#fbbf24'

WALL_COLOR = '#78350f'      # amber-900
WALL_EDGE = '#a16207'       # amber-700, edge of the wall
FLOOR_COLOR = '#0c0a09'     # near-black floor

HAZARD_STYLES = {
    '*': '#fbbf24 bold',     # gem
    '~': '#38bdf8 bold',     # water
    'o': '#a8a29e bold',     # boulder
}

COLS = DEFAULT_WIDTH
VIEWPORT_ROWS = 28


class CaveView(Static):
    """Renders the rolling cave buffer with Rich-styled walls and hazards."""

    def render_buffer(self, rows: list[str]) -> Text:
        text = Text(no_wrap=True, overflow='ellipsis')
        for i, row in enumerate(rows):
            self._append_row(text, row)
            if i + 1 < len(rows):
                text.append('\n')
        return text

    def _append_row(self, text: Text, row: str) -> None:
        # Walk the row character by character. Wall runs use the amber
        # color; the first/last wall char of a run gets the brighter edge
        # tone to make the cave "lip" pop. Hazards inside the floor use
        # their dedicated color.
        n = len(row)
        i = 0
        while i < n:
            ch = row[i]
            if ch == WALL:
                # Find run end
                j = i
                while j < n and row[j] == WALL:
                    j += 1
                run = row[i:j]
                if len(run) == 1:
                    text.append(run, style=WALL_EDGE)
                else:
                    # First+last char are the visible "lip" of the wall;
                    # the rest is solid amber rock.
                    text.append(run[0], style=WALL_EDGE)
                    text.append(run[1:-1], style=WALL_COLOR)
                    text.append(run[-1], style=WALL_EDGE)
                i = j
            elif ch in HAZARD_STYLES:
                text.append(ch, style=HAZARD_STYLES[ch])
                i += 1
            else:
                # Floor — render as space on the floor background so the
                # walkable area reads as a darker void.
                text.append(ch, style=f'on {FLOOR_COLOR}')
                i += 1


class DeepCaveApp(App):
    CSS = f"""
    Screen {{
        background: {BG};
        color: {TEXT};
        align: center top;
    }}

    #title {{
        text-align: center;
        text-style: bold;
        color: {TEXT};
        padding-top: 1;
    }}

    #subtitle {{
        text-align: center;
        color: {MUTED};
        padding-bottom: 1;
    }}

    #cave_panel {{
        align: center middle;
        background: {PANEL};
        border: tall #334155;
        padding: 0 1;
        margin: 1 2;
    }}

    #cave_view {{
        width: auto;
        height: auto;
    }}

    #stats {{
        text-align: center;
        color: {MUTED};
        padding: 0 2;
    }}

    #hint {{
        text-align: center;
        color: {ACCENT};
        text-style: italic;
        padding: 0 2;
    }}
    """

    BINDINGS = [
        Binding('space', 'toggle_play', 'Play/Pause'),
        Binding('plus,equals_sign,equal', 'faster', 'Faster'),
        Binding('minus', 'slower', 'Slower'),
        Binding('r', 'reseed', 'Reseed'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Deep Cave'

    def __init__(self) -> None:
        super().__init__()
        self.fps = 24
        self.running = True
        self.depth = 0
        self.seed_value: int | None = None
        self.rng = random.Random()
        self.left, self.width = initial_tunnel(COLS)
        self.buffer: list[str] = []
        self.seen: set[str] = set()
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('DEEP CAVE', id='title')
        yield Static('space play/pause • +/- speed • r reseed • ctrl+q quit',
                     id='subtitle')
        with Vertical(id='cave_panel'):
            yield CaveView(id='cave_view')
        yield Static('', id='hint')
        yield Static('', id='stats')
        yield Footer()

    def on_mount(self) -> None:
        # Pre-fill the viewport so the screen isn't blank at startup.
        for _ in range(VIEWPORT_ROWS):
            self._append_row()
        self._refresh()
        self._restart_timer()

    # --- Timer / animation -------------------------------------------------

    def _restart_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        # Persistent timer; pause is implemented by short-circuiting in _tick.
        self._timer = self.set_interval(1.0 / max(self.fps, 1), self._tick)

    def _tick(self) -> None:
        if not self.running:
            return
        self._append_row()
        self._refresh()

    def _append_row(self) -> None:
        self.left, self.width, row = next_row(
            self.left, self.width, self.rng, COLS)
        if len(self.buffer) >= VIEWPORT_ROWS:
            self.buffer.pop(0)
        self.buffer.append(row)
        self.depth += 1

        # Twist: announce first sighting of each hazard.
        for char, _p, _label in HAZARDS:
            if char in row and char not in self.seen:
                self.seen.add(char)
                label = hazard_label(char) or 'something'
                self.query_one('#hint', Static).update(
                    f'... you spot {label} at depth {self.depth}.')
                # Schedule a clear after a few seconds without blocking.
                self.set_timer(3.0, self._clear_hint)
                break

    def _clear_hint(self) -> None:
        self.query_one('#hint', Static).update('')

    # --- Rendering ---------------------------------------------------------

    def _refresh(self) -> None:
        view = self.query_one('#cave_view', CaveView)
        view.update(view.render_buffer(self.buffer))
        self._update_stats()

    def _update_stats(self) -> None:
        seed_str = (str(self.seed_value)
                    if self.seed_value is not None else 'random')
        running = 'DESCENDING' if self.running else 'PAUSED    '
        stats = (
            f'[{ACCENT}]{running}[/]   '
            f'depth [{TEXT}]{self.depth:>5d}[/]   '
            f'seed [{TEXT}]{seed_str}[/]   '
            f'fps [{TEXT}]{self.fps}[/]'
        )
        self.query_one('#stats', Static).update(stats)

    # --- Actions -----------------------------------------------------------

    def action_toggle_play(self) -> None:
        self.running = not self.running
        self._update_stats()

    def action_faster(self) -> None:
        self.fps = min(120, self.fps + 4)
        self._restart_timer()
        self._update_stats()

    def action_slower(self) -> None:
        self.fps = max(4, self.fps - 4)
        self._restart_timer()
        self._update_stats()

    def action_reseed(self) -> None:
        # Pick a fresh, time-based seed and reset state.
        self.seed_value = random.randrange(1, 2**31)
        self.rng = random.Random(self.seed_value)
        self.left, self.width = initial_tunnel(COLS)
        self.depth = 0
        self.buffer.clear()
        self.seen.clear()
        self.query_one('#hint', Static).update('')
        for _ in range(VIEWPORT_ROWS):
            self._append_row()
        self._refresh()


if __name__ == '__main__':
    DeepCaveApp().run()
