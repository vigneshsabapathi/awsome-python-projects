"""Langton's Ant — Textual TUI.

Dark Tailwind palette. The grid is rendered with the upper-half-block
character (▀) so each terminal line packs two grid rows; the ant is
drawn as a bright marker on top.

Bindings
--------
- space       play / pause
- n           step once (executes ``speed`` ant moves)
- +/=         speed up (more steps per frame)
- -/_         slow down
- r           reset (clear grid, recenter ant)
- p           cycle through preset rule strings
- ctrl+q      quit

Run:
    uv run python langton_ant/langton_ant_tui.py
"""
from __future__ import annotations

import numpy as np
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from langton_ant import Ant, make_grid


# Tailwind dark palette
BG = '#0f172a'
PANEL = '#1e293b'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
ANT = '#f59e0b'

# Per-color cell fills. Index 0 is the empty/background cell.
COLOR_PALETTE = [
    '#0f172a',    # 0  empty
    '#e2e8f0',    # 1
    '#38bdf8',    # 2
    '#f472b6',    # 3
    '#a78bfa',    # 4
    '#34d399',    # 5
    '#facc15',    # 6
    '#fb7185',    # 7
    '#22d3ee',    # 8
]

ROWS = 80   # rendered as ROWS/2 terminal lines via half-block
COLS = 140

PRESET_RULES = ['RL', 'RLR', 'LLRR', 'RRLL', 'LRRRRRLLR']


class GridView(Static):
    """Half-block renderer that overlays the ant marker."""

    def render_grid(
        self,
        grid: np.ndarray,
        ant_x: int,
        ant_y: int,
        direction: int,
    ) -> Text:
        text = Text(no_wrap=True, overflow='ellipsis')
        rows, cols = grid.shape
        n_palette = len(COLOR_PALETTE)
        # Direction glyphs for the ant cell when the ant happens to land
        # on the *top* half of a half-block pair.
        dir_glyphs = ('^', '>', 'v', '<')
        ant_glyph = dir_glyphs[direction]

        for r in range(0, rows, 2):
            top_row = grid[r]
            bot_row = grid[r + 1] if r + 1 < rows else np.zeros_like(top_row)
            for c in range(cols):
                top_idx = int(top_row[c]) % n_palette
                bot_idx = int(bot_row[c]) % n_palette
                fg = COLOR_PALETTE[top_idx]
                bg = COLOR_PALETTE[bot_idx]
                # Is this terminal cell the one containing the ant?
                if c == ant_x and (r == ant_y or r + 1 == ant_y):
                    if r == ant_y:
                        # Ant is on the top half — draw ant glyph in
                        # ant colour over the bottom-half background.
                        text.append(ant_glyph,
                                    style=f'bold {ANT} on {bg}')
                    else:
                        # Ant on bottom half — render half-block with
                        # ant colour as background.
                        text.append('▀',
                                    style=f'{fg} on {ANT}')
                else:
                    text.append('▀', style=f'{fg} on {bg}')
            if r + 2 < rows:
                text.append('\n')
        return text


class LangtonAntApp(App):
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
        background: {BG};
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
        Binding('plus', 'faster', 'Faster'),
        Binding('equals_sign', 'faster', 'Faster', show=False),
        Binding('minus', 'slower', 'Slower'),
        Binding('underscore', 'slower', 'Slower', show=False),
        Binding('r', 'reset', 'Reset'),
        Binding('p', 'cycle_rule', 'Rule'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = "Langton's Ant"

    def __init__(self) -> None:
        super().__init__()
        self.rows = ROWS
        self.cols = COLS
        self.rule_idx = 0
        self.speed = 50      # steps per frame
        self.fps = 30
        self.running = False
        self.ant: Ant = self._fresh_ant()
        self._timer = None

    def _fresh_ant(self) -> Ant:
        return Ant(
            make_grid(self.rows, self.cols),
            self.cols // 2, self.rows // 2,
            direction=0, rule=PRESET_RULES[self.rule_idx],
        )

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("LANGTON'S ANT", id='title')
        yield Static('space play/pause • n step • +/- speed • '
                     'r reset • p cycle rule • ctrl+q quit',
                     id='subtitle')
        with Vertical(id='grid_panel'):
            yield GridView(id='grid_view')
        yield Static('', id='stats')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        # Persistent timer; pauses by short-circuiting in _tick.
        self._timer = self.set_interval(1.0 / self.fps, self._tick)

    # --- Rendering --------------------------------------------------------

    def _refresh(self) -> None:
        view = self.query_one('#grid_view', GridView)
        view.update(view.render_grid(
            self.ant.grid, self.ant.x, self.ant.y, self.ant.direction))
        self._update_stats()

    def _update_stats(self) -> None:
        s = self.ant.state()
        non_white = int((self.ant.grid > 0).sum())
        dir_letter = 'URDL'[s['direction']]
        running = 'PLAYING' if self.running else 'PAUSED '
        alive = 'live' if s['alive'] else 'OFF-GRID'
        stats = (
            f'[{ACCENT}]{running}[/]   '
            f"step [{TEXT}]{s['steps']:>7d}[/]   "
            f"pos [{TEXT}]({s['x']},{s['y']}) {dir_letter}[/]   "
            f"rule [{TEXT}]{s['rule']}[/]   "
            f'filled [{TEXT}]{non_white:>5d}[/]   '
            f'speed [{TEXT}]{self.speed}[/]   '
            f'[{MUTED}]{alive}[/]'
        )
        self.query_one('#stats', Static).update(stats)

    # --- Tick loop --------------------------------------------------------

    def _tick(self) -> None:
        if not self.running or not self.ant.alive:
            if not self.ant.alive:
                self.running = False
            return
        for _ in range(self.speed):
            if not self.ant.alive:
                break
            self.ant.step()
        self._refresh()

    # --- Actions ----------------------------------------------------------

    def action_toggle_play(self) -> None:
        if not self.ant.alive:
            return
        self.running = not self.running
        self._update_stats()

    def action_single_step(self) -> None:
        if self.running or not self.ant.alive:
            return
        for _ in range(self.speed):
            if not self.ant.alive:
                break
            self.ant.step()
        self._refresh()

    def action_faster(self) -> None:
        # Geometric speedup feels right across 1..1000 range.
        self.speed = min(1000, max(1, int(self.speed * 1.5) + 1))
        self._update_stats()

    def action_slower(self) -> None:
        self.speed = max(1, int(self.speed / 1.5))
        self._update_stats()

    def action_reset(self) -> None:
        self.running = False
        self.ant = self._fresh_ant()
        self._refresh()

    def action_cycle_rule(self) -> None:
        self.rule_idx = (self.rule_idx + 1) % len(PRESET_RULES)
        self.running = False
        self.ant = self._fresh_ant()
        self._refresh()


if __name__ == '__main__':
    LangtonAntApp().run()
