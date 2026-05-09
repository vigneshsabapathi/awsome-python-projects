"""Conway's Game of Life — Textual TUI.

Dark Tailwind palette. Grid rendered with the upper-half-block (▀)
trick — each terminal row encodes TWO grid rows, doubling vertical
resolution.

Bindings
--------
- space   play/pause
- n       single step
- r       reseed random pattern
- p       cycle through built-in patterns
- e       toggle toroidal vs bounded edges
- ctrl+q  quit

Run:
    uv run python game_of_life/game_of_life_tui.py
"""
from __future__ import annotations

import numpy as np
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from game_of_life import (
    blinker_grid,
    glider_grid,
    gosper_glider_gun_grid,
    pulsar_grid,
    random_grid,
    step,
)


# Tailwind dark palette
BG = '#0f172a'
PANEL = '#1e293b'
ALIVE = '#34d399'  # emerald-400
DEAD = '#0f172a'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'

ROWS = 50  # grid rows (rendered as ROWS/2 terminal lines via half-block)
COLS = 100

PATTERN_NAMES = ['Random', 'Glider', 'Pulsar', 'Gosper Gun', 'Blinker']
PATTERN_BUILDERS = {
    'Random':     lambda r, c: random_grid(r, c, density=0.30),
    'Glider':     glider_grid,
    'Pulsar':     pulsar_grid,
    'Gosper Gun': gosper_glider_gun_grid,
    'Blinker':    blinker_grid,
}


class GridView(Static):
    """Renders the cellular automaton with half-block characters.

    Each terminal cell '▀' has independent foreground (top half) and
    background (bottom half) colors, so one line of text shows two grid
    rows. Net effect: square-ish cells in a typical terminal cell ratio.
    """

    def render_grid(self, grid: np.ndarray) -> Text:
        text = Text(no_wrap=True, overflow='ellipsis')
        rows, cols = grid.shape
        for r in range(0, rows, 2):
            top = grid[r]
            bot = grid[r + 1] if r + 1 < rows else np.zeros_like(top)
            for c in range(cols):
                fg = ALIVE if top[c] else DEAD
                bg = ALIVE if bot[c] else DEAD
                text.append('▀', style=f'{fg} on {bg}')
            if r + 2 < rows:
                text.append('\n')
        return text


class GameOfLifeApp(App):
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

    #grid_panel {{
        align: center middle;
        background: {PANEL};
        border: tall #334155;
        padding: 0 1;
        margin: 1 2;
    }}

    #grid_view {{
        width: auto;
        height: auto;
        background: {DEAD};
    }}

    #stats {{
        text-align: center;
        color: {MUTED};
        padding: 0 2;
    }}

    .stat-key {{
        color: {ACCENT};
        text-style: bold;
    }}
    """

    BINDINGS = [
        Binding('space', 'toggle_play', 'Play/Pause'),
        Binding('n', 'single_step', 'Step'),
        Binding('r', 'reseed', 'Random'),
        Binding('p', 'cycle_pattern', 'Pattern'),
        Binding('e', 'toggle_edges', 'Edges'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = "Conway's Game of Life"

    def __init__(self) -> None:
        super().__init__()
        self.rows = ROWS
        self.cols = COLS
        self.grid = random_grid(self.rows, self.cols, density=0.30)
        self.generation = 0
        self.running = False
        self.fps = 12
        self.toroidal = True
        self.pattern_idx = 0  # index into PATTERN_NAMES
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("CONWAY'S GAME OF LIFE", id='title')
        yield Static('space play/pause • n step • r random • '
                     'p cycle pattern • e edges • ctrl+q quit',
                     id='subtitle')
        with Vertical(id='grid_panel'):
            yield GridView(id='grid_view')
        yield Static('', id='stats')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        # Persistent timer; pauses by short-circuiting in _tick.
        self._timer = self.set_interval(1.0 / self.fps, self._tick)

    # --- Rendering ---------------------------------------------------------

    def _refresh(self) -> None:
        view = self.query_one('#grid_view', GridView)
        view.update(view.render_grid(self.grid))
        self._update_stats()

    def _update_stats(self) -> None:
        alive = int(self.grid.sum())
        pname = PATTERN_NAMES[self.pattern_idx]
        edges = 'toroidal' if self.toroidal else 'bounded'
        running = 'PLAYING' if self.running else 'PAUSED '
        stats = (
            f'[{ACCENT}]{running}[/]   '
            f'gen [{TEXT}]{self.generation:>5d}[/]   '
            f'alive [{TEXT}]{alive:>4d}[/]   '
            f'pattern [{TEXT}]{pname}[/]   '
            f'edges [{TEXT}]{edges}[/]   '
            f'fps [{TEXT}]{self.fps}[/]'
        )
        self.query_one('#stats', Static).update(stats)

    # --- Tick loop ---------------------------------------------------------

    def _tick(self) -> None:
        if not self.running:
            return
        self.grid = step(self.grid, toroidal=self.toroidal)
        self.generation += 1
        self._refresh()

    # --- Actions -----------------------------------------------------------

    def action_toggle_play(self) -> None:
        self.running = not self.running
        self._update_stats()

    def action_single_step(self) -> None:
        if self.running:
            return
        self.grid = step(self.grid, toroidal=self.toroidal)
        self.generation += 1
        self._refresh()

    def action_reseed(self) -> None:
        self.pattern_idx = 0  # Random
        self.grid = random_grid(self.rows, self.cols, density=0.30)
        self.generation = 0
        self._refresh()

    def action_cycle_pattern(self) -> None:
        self.pattern_idx = (self.pattern_idx + 1) % len(PATTERN_NAMES)
        name = PATTERN_NAMES[self.pattern_idx]
        builder = PATTERN_BUILDERS[name]
        self.grid = builder(self.rows, self.cols).astype(np.uint8)
        self.generation = 0
        self._refresh()

    def action_toggle_edges(self) -> None:
        self.toroidal = not self.toroidal
        self._update_stats()


if __name__ == '__main__':
    GameOfLifeApp().run()
