"""Tic-Tac-Toe — CustomTkinter GUI.

A modern dark-themed desktop UI for tic-tac-toe with a 3x3 button grid,
mode selector (2P / vs AI Easy / vs AI Medium / vs AI Hard / AI vs AI demo
/ Hard misère), and a green winning-line highlight.

Run:
    uv run python tic_tac_toe/tic_tac_toe_gui.py
"""
from __future__ import annotations

import threading
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from tic_tac_toe import (
    COLS,
    DIFFICULTY_OPTIMAL_P,
    O,
    PLAYER_1,
    PLAYER_2,
    ROWS,
    X,
    Board,
    ai_move,
    other,
)

# --- Visuals ----------------------------------------------------------------

CELL = 110
BG = '#0f172a'
PANEL_BG = '#0b1220'
CELL_BG = '#1e293b'
CELL_HOVER = '#334155'
WIN_BG = '#16a34a'   # green winning-line highlight

X_COLOR = '#38bdf8'   # sky blue
O_COLOR = '#f97316'   # orange

TITLE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 13)
STATUS_FONT = ('Segoe UI', 14, 'bold')
CELL_FONT = ('Segoe UI', 56, 'bold')

GLYPH = {X: 'X', O: 'O'}
COLOR = {X: X_COLOR, O: O_COLOR}

MODES = [
    '2P',
    'AI Easy',
    'AI Medium',
    'AI Hard',
    'AI vs AI',
    'AI Hard misère',
]


def _difficulty_for(mode: str) -> str:
    m = mode.lower()
    if 'easy' in m:
        return 'easy'
    if 'medium' in m:
        return 'medium'
    return 'hard'


def _is_misere(mode: str) -> bool:
    return 'misère' in mode or 'misere' in mode.lower()


class TicTacToeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Tic-Tac-Toe')
        width = COLS * CELL + 60
        height = ROWS * CELL + 220
        self.geometry(f'{width}x{height}')
        self.minsize(width, height)
        self.configure(fg_color=BG)

        # Game state.
        self.board = Board()
        self.current: int = X
        self.game_over: bool = False
        self.ai_thinking: bool = False

        self.mode_var = ctk.StringVar(value='2P')
        self.cells: dict[tuple[int, int], ctk.CTkButton] = {}

        self._build_ui()
        self._new_game()

    # -- UI build ------------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=16, fill='x')
        ctk.CTkLabel(header, text='TIC-TAC-TOE', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header, text='Three in a row wins. Perfect play always draws.',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Bottom controls.
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(side='bottom', pady=(6, 12), padx=16, fill='x')

        ctk.CTkLabel(bottom, text='Mode:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 6))
        self.mode_menu = ctk.CTkOptionMenu(
            bottom,
            values=MODES,
            variable=self.mode_var,
            command=self._on_mode_change,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b',
        )
        self.mode_menu.pack(side='left')

        self.new_btn = ctk.CTkButton(
            bottom, text='New Game', width=110,
            fg_color='#334155', hover_color='#475569',
            command=self._new_game,
        )
        self.new_btn.pack(side='right')

        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='bottom', pady=(0, 4))

        # Board grid.
        wrap = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=12)
        wrap.pack(side='top', pady=14, padx=16)

        grid = ctk.CTkFrame(wrap, fg_color=PANEL_BG)
        grid.pack(padx=14, pady=14)
        for r in range(ROWS):
            for c in range(COLS):
                btn = ctk.CTkButton(
                    grid, text='', width=CELL, height=CELL,
                    font=CELL_FONT,
                    fg_color=CELL_BG, hover_color=CELL_HOVER,
                    text_color='#f8fafc',
                    corner_radius=10,
                    command=lambda rr=r, cc=c: self._on_cell_click(rr, cc),
                )
                btn.grid(row=r, column=c, padx=4, pady=4)
                self.cells[(r, c)] = btn

    # -- Mode / new game -----------------------------------------------------

    def _on_mode_change(self, _value: str) -> None:
        self._new_game()

    def _mode(self) -> str:
        return self.mode_var.get()

    def _is_ai_mode(self) -> bool:
        m = self._mode()
        return m.startswith('AI') and m != 'AI vs AI'

    def _is_ai_demo(self) -> bool:
        return self._mode() == 'AI vs AI'

    def _new_game(self) -> None:
        self.board = Board()
        self.current = X
        self.game_over = False
        self.ai_thinking = False
        for (r, c), btn in self.cells.items():
            btn.configure(text='', fg_color=CELL_BG, hover_color=CELL_HOVER,
                          text_color='#f8fafc', state='normal')
        self._update_status()

        # If AI is to move first (AI vs AI demo, or human-vs-AI where AI is X
        # — but X is always the human in this app), trigger AI.
        if self._is_ai_demo():
            self.after(300, self._trigger_ai)

    # -- Status --------------------------------------------------------------

    def _update_status(self) -> None:
        if self.game_over:
            return
        mode = self._mode()
        if self._is_ai_demo():
            who = f'AI ({GLYPH[self.current]})'
        elif self._is_ai_mode() and self.current == O:
            who = 'AI (O)'
        else:
            who = f'Player {self.current} ({GLYPH[self.current]})'
        suffix = '  [misère]' if _is_misere(mode) else ''
        self.status.configure(text=f"{who}'s turn{suffix}",
                              text_color=COLOR[self.current])

    def _set_status(self, text: str, color: str) -> None:
        self.status.configure(text=text, text_color=color)

    # -- Cell click ----------------------------------------------------------

    def _on_cell_click(self, row: int, col: int) -> None:
        if self.game_over or self.ai_thinking:
            return
        if self._is_ai_demo():
            return
        if self._is_ai_mode() and self.current == O:
            return
        if self.board.grid[row][col] != 0:
            return
        self._play_move(row, col, self.current)

    # -- Move logic ----------------------------------------------------------

    def _render_mark(self, row: int, col: int, player: int) -> None:
        btn = self.cells[(row, col)]
        btn.configure(text=GLYPH[player], text_color=COLOR[player],
                      hover_color=CELL_BG)

    def _play_move(self, row: int, col: int, player: int) -> None:
        if not self.board.play(row, col, player):
            return
        self._render_mark(row, col, player)

        state = self.board.state()
        if state != 'in_progress':
            self._end_game(state)
            return
        self.current = other(self.current)
        self._update_status()

        # Decide whose turn is next.
        if self._is_ai_demo() and not self.game_over:
            self.after(450, self._trigger_ai)
        elif self._is_ai_mode() and self.current == O and not self.game_over:
            self._trigger_ai()

    # -- AI ------------------------------------------------------------------

    def _trigger_ai(self) -> None:
        if self.game_over:
            return
        self.ai_thinking = True
        mode = self._mode()
        difficulty = _difficulty_for(mode)
        misere = _is_misere(mode)
        self._set_status('AI thinking...', '#cbd5e1')

        snapshot = Board(self.board.grid)
        ai_player = self.current
        result: dict[str, tuple[int, int]] = {}

        def worker() -> None:
            result['mv'] = ai_move(snapshot, ai_player,
                                   difficulty=difficulty, misere=misere)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        def poll() -> None:
            if thread.is_alive():
                self.after(50, poll)
                return
            self.ai_thinking = False
            mv = result.get('mv')
            if mv is None or self.game_over:
                return
            row, col = mv
            self._play_move(row, col, ai_player)

        # Slight delay so the "AI thinking" status stays visible briefly.
        self.after(120, poll)

    # -- Endgame -------------------------------------------------------------

    def _highlight_win(self) -> None:
        line = self.board.winning_line()
        if not line:
            return
        for r, c in line:
            btn = self.cells[(r, c)]
            btn.configure(fg_color=WIN_BG, hover_color=WIN_BG,
                          text_color='#0f172a')

    def _end_game(self, state: str) -> None:
        self.game_over = True
        # Disable empty cells.
        for (r, c), btn in self.cells.items():
            if self.board.grid[r][c] == 0:
                btn.configure(state='disabled')

        if state == 'draw':
            self._set_status("It's a draw.", '#cbd5e1')
            return

        # state is 'x_wins' or 'o_wins'.
        line_player = X if state == 'x_wins' else O
        self._highlight_win()

        misere = _is_misere(self._mode())
        winner_eff = other(line_player) if misere else line_player
        if self._is_ai_demo():
            text = f"AI ({GLYPH[winner_eff]}) wins!"
        elif self._is_ai_mode() and winner_eff == O:
            text = 'AI wins!'
        else:
            text = f'Player {winner_eff} ({GLYPH[winner_eff]}) wins!'
        if misere:
            text += '  (misère)'
        self._set_status(text, COLOR[winner_eff])


if __name__ == '__main__':
    TicTacToeApp().mainloop()
