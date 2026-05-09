"""Sudoku — Textual TUI.

Dark Tailwind-flavored terminal UI. Arrow keys move the cursor across
the 9x9 grid; press 1-9 to enter a digit, 0 (or backspace/space) to
clear. Givens cannot be edited.

Bindings:
    s        solve
    h        hint
    n        new game
    Tab      cycle difficulty
    Ctrl+Z   undo
    Ctrl+Q   quit

Run:
    uv run python sudoku/sudoku_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static

from sudoku import (
    BOX,
    DIFFICULTY_GIVENS,
    SIZE,
    Board,
    generate,
    hints_remaining,
    is_solved,
    is_valid,
    solve,
)


class SudokuApp(App):
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

    #body {
        align-horizontal: center;
        height: auto;
        width: 100%;
    }

    #grid {
        width: 39;
        height: 19;
        background: #94a3b8;
        padding: 0;
        margin: 0 2;
    }

    .row {
        height: 1;
        width: 39;
    }

    .cell {
        width: 3;
        height: 1;
        content-align: center middle;
        text-style: bold;
        background: #0b1220;
        color: #38bdf8;
    }

    .cell.given {
        background: #334155;
        color: #e2e8f0;
    }

    .cell.cursor {
        background: #1d4ed8;
        color: white;
    }

    .cell.cursor.given {
        background: #1e40af;
        color: white;
    }

    .cell.bad {
        background: #7f1d1d;
        color: #fecaca;
    }

    /* Vertical separator between 3x3 boxes — rendered as its own column. */
    .vsep {
        width: 1;
        height: 1;
        background: #94a3b8;
    }

    /* Horizontal separator row. */
    .hsep {
        height: 1;
        width: 39;
        background: #94a3b8;
    }

    #sidebar {
        width: 28;
        height: auto;
        background: #1e293b;
        padding: 1 2;
        margin-top: 1;
    }

    #sidebar Static {
        height: auto;
    }

    .label {
        color: #94a3b8;
        padding-bottom: 1;
    }

    .value {
        color: #f8fafc;
        text-style: bold;
        padding-bottom: 1;
    }

    #status {
        text-align: center;
        padding: 1;
        height: 3;
    }

    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-win   { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('up',    'move(-1, 0)', 'Up',    show=False),
        Binding('down',  'move(1, 0)',  'Down',  show=False),
        Binding('left',  'move(0, -1)', 'Left',  show=False),
        Binding('right', 'move(0, 1)',  'Right', show=False),
        Binding('1', 'place(1)', show=False),
        Binding('2', 'place(2)', show=False),
        Binding('3', 'place(3)', show=False),
        Binding('4', 'place(4)', show=False),
        Binding('5', 'place(5)', show=False),
        Binding('6', 'place(6)', show=False),
        Binding('7', 'place(7)', show=False),
        Binding('8', 'place(8)', show=False),
        Binding('9', 'place(9)', show=False),
        Binding('0',         'place(0)',   'Clear', show=False),
        Binding('backspace', 'place(0)',   'Clear', show=False),
        Binding('space',     'place(0)',   'Clear', show=False),
        Binding('s', 'solve',  'Solve'),
        Binding('h', 'hint',   'Hint'),
        Binding('n', 'new',    'New'),
        Binding('tab', 'cycle_difficulty', 'Difficulty', show=True),
        Binding('ctrl+z', 'undo', 'Undo'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Sudoku'

    cursor_r: reactive[int] = reactive(0)
    cursor_c: reactive[int] = reactive(0)

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.board: Board = Board.empty()
        self.difficulty: str = 'easy'
        self._difficulties = list(DIFFICULTY_GIVENS)
        # Stack of (r, c, prev_value).
        self.history: list[tuple[int, int, int]] = []

    # ----- compose --------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('SUDOKU', id='title')
        yield Static('Arrows to move · 1-9 fill · 0 clear · S solve · H hint',
                     id='subtitle')
        with Horizontal(id='body'):
            with Vertical(id='grid'):
                for r in range(SIZE):
                    if r > 0 and r % BOX == 0:
                        yield Static('', classes='hsep')
                    with Horizontal(classes='row'):
                        for c in range(SIZE):
                            if c > 0 and c % BOX == 0:
                                yield Static('', classes='vsep')
                            yield Static(' ', classes='cell',
                                         id=f'cell-{r}-{c}')
            with Vertical(id='sidebar'):
                yield Static('Difficulty', classes='label')
                yield Static('easy', id='difficulty', classes='value')
                yield Static('Cells left', classes='label')
                yield Static('—', id='remaining', classes='value')
                yield Static('Cursor', classes='label')
                yield Static('R1 · C1', id='cursor', classes='value')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._new_game()

    # ----- game flow ------------------------------------------------------

    def _new_game(self) -> None:
        self.board = generate(self.difficulty, self.rng)
        self.history.clear()
        self.cursor_r = 0
        self.cursor_c = 0
        self.query_one('#difficulty', Static).update(self.difficulty)
        self._render()

    def _render(self) -> None:
        bad = self._invalid_cells()
        for r in range(SIZE):
            for c in range(SIZE):
                cell = self.query_one(f'#cell-{r}-{c}', Static)
                v = self.board.grid[r][c]
                cell.update(str(v) if v else ' ')
                classes = ['cell']
                if self.board.is_given(r, c):
                    classes.append('given')
                if (r, c) in bad:
                    classes.append('bad')
                if r == self.cursor_r and c == self.cursor_c:
                    classes.append('cursor')
                cell.set_classes(' '.join(classes))

        self.query_one('#remaining', Static).update(
            str(hints_remaining(self.board)))
        self.query_one('#cursor', Static).update(
            f'R{self.cursor_r + 1} · C{self.cursor_c + 1}')

        if is_solved(self.board):
            self._set_status('Solved! Press N for a new puzzle.', 'win')
        elif not is_valid(self.board):
            self._set_status('Conflict — see highlighted cells.', 'error')
        else:
            self._set_status(
                f'{hints_remaining(self.board)} cells remaining.', 'info')

    def _invalid_cells(self) -> set[tuple[int, int]]:
        bad: set[tuple[int, int]] = set()
        for axis in ('row', 'col', 'box'):
            for k in range(SIZE):
                seen: dict[int, list[tuple[int, int]]] = {}
                for r, c in self._cells_in(axis, k):
                    v = self.board.grid[r][c]
                    if v == 0:
                        continue
                    seen.setdefault(v, []).append((r, c))
                for cells in seen.values():
                    if len(cells) > 1:
                        bad.update(cells)
        return bad

    @staticmethod
    def _cells_in(axis: str, k: int):
        if axis == 'row':
            for c in range(SIZE):
                yield (k, c)
        elif axis == 'col':
            for r in range(SIZE):
                yield (r, k)
        else:
            br, bc = (k // BOX) * BOX, (k % BOX) * BOX
            for i in range(BOX):
                for j in range(BOX):
                    yield (br + i, bc + j)

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    # ----- actions --------------------------------------------------------

    def action_move(self, dr: int, dc: int) -> None:
        self.cursor_r = (self.cursor_r + dr) % SIZE
        self.cursor_c = (self.cursor_c + dc) % SIZE
        self._render()

    def action_place(self, digit: int) -> None:
        r, c = self.cursor_r, self.cursor_c
        if self.board.is_given(r, c):
            self._set_status('That cell is a given.', 'error')
            return
        prev = self.board.grid[r][c]
        if prev == digit:
            return
        self.history.append((r, c, prev))
        self.board.set(r, c, digit)
        self._render()

    def action_solve(self) -> None:
        solution = self.board.clone()
        if not solve(solution):
            self._set_status('No solution — undo conflicting moves.', 'error')
            return
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board.grid[r][c] != solution.grid[r][c]:
                    self.history.append((r, c, self.board.grid[r][c]))
                    self.board.set(r, c, solution.grid[r][c])
        self._render()
        self._set_status('Solved.', 'win')

    def action_hint(self) -> None:
        solution = self.board.clone()
        if not solve(solution):
            self._set_status('No solution from here — undo a move.', 'error')
            return
        empties = self.board.empty_cells()
        if not empties:
            self._set_status('Already complete.', 'win')
            return
        r, c = self.rng.choice(empties)
        self.history.append((r, c, self.board.grid[r][c]))
        self.board.set(r, c, solution.grid[r][c])
        self.cursor_r, self.cursor_c = r, c
        self._render()
        self._set_status(
            f'Hint: R{r + 1}·C{c + 1} = {solution.grid[r][c]}', 'info')

    def action_new(self) -> None:
        self._new_game()

    def action_undo(self) -> None:
        if not self.history:
            self._set_status('Nothing to undo.', 'info')
            return
        r, c, prev = self.history.pop()
        self.board.set(r, c, prev)
        self.cursor_r, self.cursor_c = r, c
        self._render()

    def action_cycle_difficulty(self) -> None:
        idx = (self._difficulties.index(self.difficulty) + 1) \
            % len(self._difficulties)
        self.difficulty = self._difficulties[idx]
        self.query_one('#difficulty', Static).update(self.difficulty)
        self._set_status(
            f'Difficulty set to {self.difficulty}. Press N for new game.',
            'info')


if __name__ == '__main__':
    SudokuApp().run()
