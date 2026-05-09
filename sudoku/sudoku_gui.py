"""Sudoku — CustomTkinter GUI.

Dark-theme desktop UI for the sudoku puzzle. 9x9 grid of CTkEntry cells
with thick borders separating the 3x3 boxes; givens are rendered in a
distinct color and locked, solver / hint / undo / new-game live in a
sidebar.

Run:
    uv run python sudoku/sudoku_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

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

# Palette — same dark-slate vibe as the bagels GUI.
BG          = '#0f172a'
PANEL       = '#1e293b'
GRID_LINE   = '#475569'
THICK_LINE  = '#94a3b8'
GIVEN_BG    = '#334155'
GIVEN_FG    = '#e2e8f0'
INPUT_BG    = '#0b1220'
INPUT_FG    = '#38bdf8'
INVALID_FG  = '#f87171'
SOLVED_FG   = '#34d399'

CELL_FONT  = ('Segoe UI', 22, 'bold')
TITLE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 13)
BTN_FONT   = ('Segoe UI', 13, 'bold')
STATUS_FONT = ('Segoe UI', 13)


class SudokuApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Sudoku')
        self.geometry('720x640')
        self.minsize(720, 600)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.board: Board = Board.empty()
        self.cells: list[list[ctk.CTkEntry]] = []
        # StringVars: needed so we can wire trace() per-cell.
        self.vars: list[list[ctk.StringVar]] = []
        # Stack of (r, c, prev_value) for undo.
        self.history: list[tuple[int, int, int]] = []
        # Block trace events while we programmatically update cells.
        self._suspend_traces = False

        self._build_ui()
        self._new_game('easy')

    # ----- UI construction ------------------------------------------------

    def _build_ui(self) -> None:
        # Title bar.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 8))
        ctk.CTkLabel(header, text='SUDOKU', font=TITLE_FONT,
                     text_color='#f8fafc').pack(side='left')
        self.status = ctk.CTkLabel(header, text='', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='right')

        # Main split: board on the left, controls on the right.
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(0, 16))

        board_frame = ctk.CTkFrame(body, fg_color=THICK_LINE, corner_radius=6)
        board_frame.pack(side='left', padx=(0, 16), pady=0)
        self._build_board(board_frame)

        sidebar = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=8,
                               width=240)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

    def _build_board(self, parent: ctk.CTkFrame) -> None:
        # Outer thick border = parent's fg_color. Inside, build 3x3 boxes
        # separated by 2px gaps and 1px gaps between cells inside a box.
        outer = ctk.CTkFrame(parent, fg_color=THICK_LINE)
        outer.pack(padx=3, pady=3)

        for br in range(BOX):
            for bc in range(BOX):
                box = ctk.CTkFrame(outer, fg_color=GRID_LINE)
                box.grid(row=br, column=bc, padx=2, pady=2)
                for i in range(BOX):
                    for j in range(BOX):
                        r, c = br * BOX + i, bc * BOX + j
                        var = ctk.StringVar()
                        entry = ctk.CTkEntry(
                            box,
                            textvariable=var,
                            width=52, height=52,
                            font=CELL_FONT,
                            justify='center',
                            corner_radius=0,
                            border_width=0,
                            fg_color=INPUT_BG,
                            text_color=INPUT_FG,
                        )
                        entry.grid(row=i, column=j, padx=1, pady=1)
                        # Per-cell trace — fires whenever the StringVar
                        # changes (typed, pasted, programmatic edits).
                        var.trace_add(
                            'write',
                            lambda *_a, rr=r, cc=c: self._on_cell_changed(rr, cc))
                        # Click-arrow nav: tab moves to next, but allow
                        # explicit arrow keys.
                        entry.bind('<Up>',    lambda _e, rr=r, cc=c:
                                   self._focus_cell(rr - 1, cc))
                        entry.bind('<Down>',  lambda _e, rr=r, cc=c:
                                   self._focus_cell(rr + 1, cc))
                        entry.bind('<Left>',  lambda _e, rr=r, cc=c:
                                   self._focus_cell(rr, cc - 1))
                        entry.bind('<Right>', lambda _e, rr=r, cc=c:
                                   self._focus_cell(rr, cc + 1))

                        if len(self.cells) <= r:
                            self.cells.append([])
                            self.vars.append([])
                        self.cells[r].append(entry)
                        self.vars[r].append(var)

    def _build_sidebar(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text='Difficulty', font=LABEL_FONT,
                     text_color='#94a3b8').pack(pady=(16, 4), padx=16,
                                                anchor='w')
        self.difficulty_var = ctk.StringVar(value='easy')
        self.difficulty_menu = ctk.CTkOptionMenu(
            parent,
            values=list(DIFFICULTY_GIVENS),
            variable=self.difficulty_var,
            fg_color='#334155',
            button_color='#475569',
            button_hover_color='#64748b',
        )
        self.difficulty_menu.pack(fill='x', padx=16)

        def make_btn(text: str, cmd, color='#334155',
                     hover='#475569') -> ctk.CTkButton:
            btn = ctk.CTkButton(parent, text=text, font=BTN_FONT,
                                fg_color=color, hover_color=hover,
                                command=cmd)
            btn.pack(fill='x', padx=16, pady=(8, 0))
            return btn

        make_btn('New Game',
                 lambda: self._new_game(self.difficulty_var.get()))
        make_btn('Hint',  self._hint, color='#0e7490', hover='#155e75')
        make_btn('Solve', self._solve, color='#15803d', hover='#166534')
        make_btn('Undo',  self._undo)
        make_btn('Reset', self._reset)

        ctk.CTkLabel(parent,
                     text=('Click a cell, type 1–9. '
                           'Backspace to clear. '
                           'Givens are read-only.'),
                     font=('Segoe UI', 11),
                     text_color='#64748b',
                     wraplength=200, justify='left').pack(
            pady=(16, 12), padx=16)

    # ----- game flow ------------------------------------------------------

    def _new_game(self, difficulty: str) -> None:
        self.board = generate(difficulty, self.rng)
        self.history.clear()
        self._render_board()
        self._set_status(
            f'{difficulty.title()} — {hints_remaining(self.board)} cells left',
            '#cbd5e1')

    def _render_board(self) -> None:
        self._suspend_traces = True
        try:
            for r in range(SIZE):
                for c in range(SIZE):
                    var = self.vars[r][c]
                    entry = self.cells[r][c]
                    v = self.board.grid[r][c]
                    var.set(str(v) if v else '')
                    if self.board.is_given(r, c):
                        entry.configure(
                            state='disabled',
                            fg_color=GIVEN_BG,
                            text_color=GIVEN_FG,
                        )
                    else:
                        entry.configure(
                            state='normal',
                            fg_color=INPUT_BG,
                            text_color=INPUT_FG,
                        )
        finally:
            self._suspend_traces = False

    def _on_cell_changed(self, r: int, c: int) -> None:
        if self._suspend_traces:
            return
        if self.board.is_given(r, c):
            return
        raw = self.vars[r][c].get().strip()
        # Accept only the last character if user typed multiple — keeps
        # the cell to a single digit.
        if len(raw) > 1:
            raw = raw[-1]
            self._suspend_traces = True
            self.vars[r][c].set(raw)
            self._suspend_traces = False
        if raw == '':
            new_val = 0
        elif raw.isdigit() and raw != '0':
            new_val = int(raw)
        else:
            # Reject non-digits / zero — restore previous.
            self._suspend_traces = True
            old = self.board.grid[r][c]
            self.vars[r][c].set(str(old) if old else '')
            self._suspend_traces = False
            return

        prev = self.board.grid[r][c]
        if prev == new_val:
            return
        self.history.append((r, c, prev))
        self.board.set(r, c, new_val)

        # Recolor: red if this entry duplicates a peer.
        self._refresh_validity_colors()

        if is_solved(self.board):
            self._set_status('Solved! Nicely done.', SOLVED_FG)
        elif not is_valid(self.board):
            self._set_status('Conflict — see red cells.', INVALID_FG)
        else:
            self._set_status(
                f'{hints_remaining(self.board)} cells left', '#cbd5e1')

    def _refresh_validity_colors(self) -> None:
        # Find every cell that conflicts with a peer (row/col/box).
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

        for r in range(SIZE):
            for c in range(SIZE):
                if self.board.is_given(r, c):
                    continue
                fg = INVALID_FG if (r, c) in bad else INPUT_FG
                self.cells[r][c].configure(text_color=fg)

    @staticmethod
    def _cells_in(axis: str, k: int):
        if axis == 'row':
            for c in range(SIZE):
                yield (k, c)
        elif axis == 'col':
            for r in range(SIZE):
                yield (r, k)
        else:  # 'box'
            br, bc = (k // BOX) * BOX, (k % BOX) * BOX
            for i in range(BOX):
                for j in range(BOX):
                    yield (br + i, bc + j)

    # ----- buttons --------------------------------------------------------

    def _hint(self) -> None:
        solution = self.board.clone()
        if not solve(solution):
            self._set_status('No solution from here — undo a move.',
                             INVALID_FG)
            return
        empties = self.board.empty_cells()
        if not empties:
            self._set_status('Already complete.', SOLVED_FG)
            return
        r, c = self.rng.choice(empties)
        prev = self.board.grid[r][c]
        self.history.append((r, c, prev))
        self.board.set(r, c, solution.grid[r][c])
        self._suspend_traces = True
        self.vars[r][c].set(str(solution.grid[r][c]))
        self._suspend_traces = False
        self._refresh_validity_colors()
        if is_solved(self.board):
            self._set_status('Solved! Nicely done.', SOLVED_FG)
        else:
            self._set_status(
                f'Hint placed — {hints_remaining(self.board)} cells left',
                '#cbd5e1')

    def _solve(self) -> None:
        solution = self.board.clone()
        if not solve(solution):
            self._set_status('No solution — undo conflicting moves.',
                             INVALID_FG)
            return
        # Push every changed cell onto history so 'undo' rewinds in order.
        for r in range(SIZE):
            for c in range(SIZE):
                if self.board.grid[r][c] != solution.grid[r][c]:
                    self.history.append((r, c, self.board.grid[r][c]))
                    self.board.set(r, c, solution.grid[r][c])
        self._render_board()
        self._refresh_validity_colors()
        self._set_status('Solved.', SOLVED_FG)

    def _undo(self) -> None:
        if not self.history:
            self._set_status('Nothing to undo.', '#94a3b8')
            return
        r, c, prev = self.history.pop()
        self.board.set(r, c, prev)
        self._suspend_traces = True
        self.vars[r][c].set(str(prev) if prev else '')
        self._suspend_traces = False
        self._refresh_validity_colors()
        self._set_status(
            f'{hints_remaining(self.board)} cells left', '#cbd5e1')

    def _reset(self) -> None:
        # Clear all non-given cells.
        for r in range(SIZE):
            for c in range(SIZE):
                if not self.board.is_given(r, c):
                    self.board.set(r, c, 0)
        self.history.clear()
        self._render_board()
        self._set_status(
            f'Reset — {hints_remaining(self.board)} cells left', '#cbd5e1')

    # ----- helpers --------------------------------------------------------

    def _focus_cell(self, r: int, c: int) -> str:
        if 0 <= r < SIZE and 0 <= c < SIZE:
            self.cells[r][c].focus_set()
        return 'break'

    def _set_status(self, text: str, color: str) -> None:
        self.status.configure(text=text, text_color=color)


if __name__ == '__main__':
    SudokuApp().mainloop()
