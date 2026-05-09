"""Drossel-Schwabl Forest Fire — Textual TUI.

Dark palette. Grid rendered with the upper-half-block (▀) trick — each
terminal cell encodes TWO grid rows by giving the foreground (top half)
and background (bottom half) independent colors, doubling vertical
resolution at zero cost.

Color key
---------
    brown   : EMPTY   (bare ground)
    green   : TREE
    orange  : BURNING (this step)
    red     : just-ignited TREE (still encoded as BURNING but flagged)

Bindings
--------
- space   play/pause
- n       single step
- r       reset (re-seed forest)
- w       cycle wind direction (twist: anisotropic spread)
- ctrl+q  quit

Run:
    uv run python forest_fire/forest_fire_tui.py
"""
from __future__ import annotations

import random

import numpy as np
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from forest_fire import (
    BURNING,
    NEIGHBOR_OFFSETS,
    TREE,
    random_grid,
    step,
)


# Dark Tailwind-ish palette.
BG = '#0f172a'
PANEL = '#1e293b'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'

# State colors.
COLOR_EMPTY = '#3f2810'      # dark brown bare ground
COLOR_TREE = '#16a34a'
COLOR_BURNING = '#f97316'    # orange flame

ROWS = 50   # rendered as ROWS/2 terminal lines
COLS = 100

WIND_OPTIONS = list(NEIGHBOR_OFFSETS)


class GridView(Static):
    """Renders the forest with half-block characters.

    Each terminal cell '▀' has independent foreground (top half) and
    background (bottom half) colors. We map state -> color the same way
    on both halves, so one terminal line covers two grid rows.
    """

    @staticmethod
    def _color_for(state: int) -> str:
        if state == BURNING:
            return COLOR_BURNING
        if state == TREE:
            return COLOR_TREE
        return COLOR_EMPTY

    def render_grid(self, grid: np.ndarray) -> Text:
        text = Text(no_wrap=True, overflow='ellipsis')
        rows, cols = grid.shape
        # Iterate in pairs of rows; the top half drives the foreground color
        # and the bottom half drives the background color of '▀'.
        for r in range(0, rows, 2):
            top = grid[r]
            if r + 1 < rows:
                bot = grid[r + 1]
            else:
                bot = np.zeros_like(top)
            for c in range(cols):
                fg = self._color_for(int(top[c]))
                bg = self._color_for(int(bot[c]))
                text.append('▀', style=f'{fg} on {bg}')
            if r + 2 < rows:
                text.append('\n')
        return text


class ForestFireApp(App):
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
        background: {COLOR_EMPTY};
    }}

    #stats {{
        text-align: center;
        color: {MUTED};
        padding: 0 2;
    }}
    """

    BINDINGS = [
        Binding('space', 'toggle_play', 'Play/Pause'),
        Binding('n', 'single_step', 'Step'),
        Binding('r', 'reset', 'Reset'),
        Binding('w', 'cycle_wind', 'Wind'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Drossel-Schwabl Forest Fire'

    def __init__(self) -> None:
        super().__init__()
        self.rows = ROWS
        self.cols = COLS
        self.density_init = 0.55
        self.p_grow = 0.02
        self.p_lightning = 0.0005
        self.fps = 10
        self.wind_idx = 0
        self.generation = 0
        self.running = False
        self._rng = random.Random()
        self.grid = random_grid(self.rows, self.cols, self.density_init)
        self._timer = None

    @property
    def wind(self) -> str:
        return WIND_OPTIONS[self.wind_idx]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('DROSSEL-SCHWABL FOREST FIRE', id='title')
        yield Static('space play/pause • n step • r reset • '
                     'w wind • ctrl+q quit',
                     id='subtitle')
        with Vertical(id='grid_panel'):
            yield GridView(id='grid_view')
        yield Static('', id='stats')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self._timer = self.set_interval(1.0 / self.fps, self._tick)

    # --- Render -----------------------------------------------------------

    def _refresh(self) -> None:
        view = self.query_one('#grid_view', GridView)
        view.update(view.render_grid(self.grid))
        self._update_stats()

    def _update_stats(self) -> None:
        trees = int((self.grid == TREE).sum())
        burning = int((self.grid == BURNING).sum())
        density = trees / self.grid.size
        running = 'PLAYING' if self.running else 'PAUSED '
        stats = (
            f'[{ACCENT}]{running}[/]   '
            f'gen [{TEXT}]{self.generation:>5d}[/]   '
            f'trees [{TEXT}]{trees:>5d}[/]   '
            f'burning [{TEXT}]{burning:>4d}[/]   '
            f'density [{TEXT}]{density:.3f}[/]   '
            f'wind [{TEXT}]{self.wind}[/]   '
            f'p [{TEXT}]{self.p_grow}[/]   '
            f'f [{TEXT}]{self.p_lightning}[/]'
        )
        self.query_one('#stats', Static).update(stats)

    # --- Tick -------------------------------------------------------------

    def _tick(self) -> None:
        if not self.running:
            return
        self.grid = step(self.grid, self.p_grow, self.p_lightning,
                         self._rng, wind=self.wind)
        self.generation += 1
        self._refresh()

    # --- Actions ----------------------------------------------------------

    def action_toggle_play(self) -> None:
        self.running = not self.running
        self._update_stats()

    def action_single_step(self) -> None:
        if self.running:
            return
        self.grid = step(self.grid, self.p_grow, self.p_lightning,
                         self._rng, wind=self.wind)
        self.generation += 1
        self._refresh()

    def action_reset(self) -> None:
        self.grid = random_grid(self.rows, self.cols, self.density_init)
        self.generation = 0
        self._refresh()

    def action_cycle_wind(self) -> None:
        self.wind_idx = (self.wind_idx + 1) % len(WIND_OPTIONS)
        self._update_stats()


if __name__ == '__main__':
    ForestFireApp().run()
