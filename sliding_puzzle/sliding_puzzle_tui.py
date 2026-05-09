"""Sliding Tile Puzzle — Textual TUI.

A modern terminal UI with a Tailwind-dark palette. Each tile is a Static cell
that recolors green on the goal-state win, blue otherwise; the blank is a
darker cell. Use arrow keys (or WASD) to slide the blank, h to highlight
the next A* hint, n for a new puzzle, ctrl+q to quit.

Run:
    uv run python sliding_puzzle/sliding_puzzle_tui.py
"""
from __future__ import annotations

import random
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from sliding_puzzle import (
    DELTAS,
    DOWN,
    LEFT,
    Puzzle,
    RIGHT,
    UP,
    _default_shuffle,
    hint as compute_hint,
    is_solvable,
)


class SlidingPuzzleApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
        align: center middle;
    }

    #wrap {
        align: center middle;
        height: auto;
        width: auto;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 0 0 0;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #hud {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .hud-chip {
        padding: 0 1;
        margin: 0 1;
        height: 1;
        background: #1e293b;
        color: #cbd5e1;
    }
    .hud-chip-warn { background: #1e293b; color: #f87171; }
    .hud-chip-ok   { background: #1e293b; color: #34d399; }

    #board {
        grid-gutter: 1 1;
        width: auto;
        height: auto;
        background: #1e293b;
        padding: 1 2;
        border: round #334155;
    }

    .tile {
        width: 7;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: #3b82f6;
        color: #f8fafc;
    }
    .tile-blank { background: #0b1220; color: #0b1220; }
    .tile-hint  { background: #f59e0b; color: #1f2937; }
    .tile-goal  { background: #16a34a; color: #f8fafc; }

    #status {
        text-align: center;
        padding: 1;
    }
    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-win   { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('up,w', 'slide_up', 'Up'),
        Binding('down,s', 'slide_down', 'Down'),
        Binding('left,a', 'slide_left', 'Left'),
        Binding('right,d', 'slide_right', 'Right'),
        Binding('n', 'new_game', 'New'),
        Binding('h', 'hint', 'Hint'),
        Binding('p', 'parity', 'Parity'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Sliding Tile Puzzle'

    def __init__(self, n: int = 4) -> None:
        super().__init__()
        self.n = n
        self.rng = random.Random()
        self.puzzle = Puzzle(self.n)
        self._game_over = False
        self._start_ts: float | None = None
        self._hint_idx: int | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id='wrap'):
            yield Static('SLIDING TILE PUZZLE', id='title')
            yield Static('Arrows / WASD slide · n new · h hint · p parity · ctrl+q quit',
                         id='subtitle')
            with Horizontal(id='hud'):
                yield Static('Moves: 0', id='moves', classes='hud-chip')
                yield Static('00:00', id='timer', classes='hud-chip')
                yield Static('size 4', id='size', classes='hud-chip')
                yield Static('solvable', id='parity', classes='hud-chip hud-chip-ok')
            with Grid(id='board'):
                for idx in range(self.n * self.n):
                    yield Static('', classes='tile', id=f'cell-{idx}')
            yield Static('', id='status', classes='status-info')
        yield Footer()

    # ---------------------------------------------------------- lifecycle

    def on_mount(self) -> None:
        board = self.query_one('#board', Grid)
        board.styles.grid_size_columns = self.n
        board.styles.grid_size_rows = self.n
        self._new_game()
        self.set_interval(0.5, self._tick_timer)

    def _new_game(self) -> None:
        self.puzzle = Puzzle(self.n)
        self.puzzle.shuffle(self.rng, moves=_default_shuffle(self.n))
        self._game_over = False
        self._start_ts = None
        self._hint_idx = None
        self._render_board()
        self._update_hud()
        self._set_status('Slide tiles into the blank cell.', 'info')

    def _render_board(self) -> None:
        for idx, value in enumerate(self.puzzle.state()):
            cell = self.query_one(f'#cell-{idx}', Static)
            cell.update(str(value) if value else ' ')
            if value == 0:
                cell.set_classes('tile tile-blank')
            elif self._game_over:
                cell.set_classes('tile tile-goal')
            elif self._hint_idx == idx:
                cell.set_classes('tile tile-hint')
            else:
                cell.set_classes('tile')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        st = self.query_one('#status', Static)
        st.update(text)
        st.set_classes(f'status-{kind}')

    def _update_hud(self) -> None:
        self.query_one('#moves', Static).update(f'Moves: {self.puzzle.moves}')
        self.query_one('#size', Static).update(f'size {self.n}')
        ok = is_solvable(self.puzzle)
        parity = self.query_one('#parity', Static)
        parity.update('solvable' if ok else 'unsolvable')
        parity.set_classes(
            f'hud-chip hud-chip-{"ok" if ok else "warn"}')

    def _tick_timer(self) -> None:
        if self._start_ts is None or self._game_over:
            return
        sec = int(time.time() - self._start_ts)
        m, s = divmod(sec, 60)
        self.query_one('#timer', Static).update(f'{m:02d}:{s:02d}')

    # ---------------------------------------------------------- actions

    def _slide(self, direction: str) -> None:
        if self._game_over:
            return
        if not self.puzzle.slide(direction):
            return
        if self._start_ts is None:
            self._start_ts = time.time()
        self._hint_idx = None
        self._render_board()
        self._update_hud()
        if self.puzzle.is_solved():
            self._win()

    def action_slide_up(self) -> None:    self._slide(UP)
    def action_slide_down(self) -> None:  self._slide(DOWN)
    def action_slide_left(self) -> None:  self._slide(LEFT)
    def action_slide_right(self) -> None: self._slide(RIGHT)

    def action_new_game(self) -> None:
        self._new_game()

    def action_hint(self) -> None:
        if self._game_over:
            return
        if self.n > 4:
            self._set_status('Hints unavailable for n > 4.', 'error')
            return
        nxt = compute_hint(self.puzzle)
        if nxt is None:
            self._set_status('Already solved.', 'win')
            return
        br, bc = self.puzzle.blank()
        dr, dc = DELTAS[nxt]
        tr, tc = br + dr, bc + dc
        self._hint_idx = tr * self.n + tc
        value = self.puzzle.state()[self._hint_idx]
        self._render_board()
        self._set_status(f'Hint: slide tile {value} ({nxt}).', 'info')

    def action_parity(self) -> None:
        from sliding_puzzle import inversion_count
        inv = inversion_count(self.puzzle.state())
        ok = is_solvable(self.puzzle)
        verdict = 'solvable' if ok else 'unsolvable'
        self._set_status(f'inversions = {inv}, {verdict}.',
                         'info' if ok else 'error')

    # ---------------------------------------------------------- win

    def _win(self) -> None:
        self._game_over = True
        elapsed = '—'
        if self._start_ts is not None:
            sec = int(time.time() - self._start_ts)
            m, s = divmod(sec, 60)
            elapsed = f'{m:02d}:{s:02d}'
        self._render_board()
        self._set_status(
            f'Solved in {self.puzzle.moves} moves ({elapsed})! Press n for a new puzzle.',
            'win')


if __name__ == '__main__':
    SlidingPuzzleApp().run()
