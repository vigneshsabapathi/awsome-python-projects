"""Four in a Row — CustomTkinter GUI.

A modern desktop UI for Connect Four with hover preview, animated drops,
and a switchable mode (2P / vs AI Easy / Medium / Hard).

Run:
    uv run python four_in_a_row/four_in_a_row_gui.py
"""
from __future__ import annotations

import threading
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from four_in_a_row import (
    COLS,
    DIFFICULTY_DEPTH,
    PLAYER_1,
    PLAYER_2,
    ROWS,
    Board,
    ai_move,
    other,
)

# --- Visuals ----------------------------------------------------------------

CELL = 72        # px per cell
PAD = 8          # padding between disc and cell edge
BOARD_BG = '#1e3a8a'   # board frame
SLOT_BG = '#0f172a'    # empty slot (looks like a hole)
HOVER_BG = '#1e293b'   # hovered column highlight
WIN_BG = '#facc15'     # winning slot highlight

# Player colors — easy to extend with more cycles.
PLAYER_COLORS = {
    PLAYER_1: ('#ef4444', '#fca5a5'),  # red
    PLAYER_2: ('#facc15', '#fde68a'),  # yellow
}

TITLE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 13)
STATUS_FONT = ('Segoe UI', 14, 'bold')

ANIM_STEP_MS = 14  # frame interval for the drop animation
ANIM_PIXELS_PER_FRAME = 28


def _slot_center(row: int, col: int) -> tuple[int, int]:
    return col * CELL + CELL // 2, row * CELL + CELL // 2


class FourInARowApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Four in a Row')
        width = COLS * CELL + 40
        height = ROWS * CELL + 220
        self.geometry(f'{width}x{height}')
        self.minsize(width, height)
        self.configure(fg_color='#0f172a')

        # Game state.
        self.board = Board()
        self.current: int = PLAYER_1
        self.game_over: bool = False
        self.is_animating: bool = False
        self.ai_thinking: bool = False
        self.hover_col: Optional[int] = None

        # Mode: '2p' | 'easy' | 'medium' | 'hard'. AI always plays as PLAYER_2.
        self.mode_var = ctk.StringVar(value='2P')

        self._disc_items: dict[tuple[int, int], int] = {}
        self._win_cells: list[tuple[int, int]] = []

        self._build_ui()
        self._new_game()

    # -- UI build ------------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=16, fill='x')
        ctk.CTkLabel(header, text='FOUR IN A ROW', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header, text='Drop discs — first to 4 in a row wins.',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Bottom controls (packed first so they're always visible).
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(side='bottom', pady=(6, 12), padx=16, fill='x')

        ctk.CTkLabel(bottom, text='Mode:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 6))
        self.mode_menu = ctk.CTkOptionMenu(
            bottom,
            values=['2P', 'AI Easy', 'AI Medium', 'AI Hard'],
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

        # Canvas board.
        canvas_w = COLS * CELL
        canvas_h = ROWS * CELL
        # +1 row of "drop preview" space above the board.
        preview_h = CELL // 2
        wrap = ctk.CTkFrame(self, fg_color='#0b1220', corner_radius=12)
        wrap.pack(side='top', pady=10)

        self.preview = tk.Canvas(wrap, width=canvas_w, height=preview_h,
                                 bg='#0b1220', highlightthickness=0)
        self.preview.pack(side='top', padx=10, pady=(10, 0))

        self.canvas = tk.Canvas(wrap, width=canvas_w, height=canvas_h,
                                bg=BOARD_BG, highlightthickness=0)
        self.canvas.pack(side='top', padx=10, pady=(2, 10))

        self._draw_empty_board()

        self.canvas.bind('<Motion>', self._on_motion)
        self.canvas.bind('<Leave>', self._on_leave)
        self.canvas.bind('<Button-1>', self._on_click)

    def _draw_empty_board(self) -> None:
        c = self.canvas
        c.delete('all')
        # Column hover overlays (drawn first so discs appear on top).
        self._col_overlays: list[int] = []
        for col in range(COLS):
            x0 = col * CELL
            ovl = c.create_rectangle(
                x0, 0, x0 + CELL, ROWS * CELL,
                fill='', outline='', tags=('overlay', f'col{col}'),
            )
            self._col_overlays.append(ovl)
        # Slots (holes).
        for r in range(ROWS):
            for col in range(COLS):
                cx, cy = _slot_center(r, col)
                c.create_oval(cx - CELL // 2 + PAD, cy - CELL // 2 + PAD,
                              cx + CELL // 2 - PAD, cy + CELL // 2 - PAD,
                              fill=SLOT_BG, outline='', tags=(f'slot-{r}-{col}',))
        self._disc_items.clear()
        self._win_cells = []

    # -- Mode / new game -----------------------------------------------------

    def _on_mode_change(self, _value: str) -> None:
        self._new_game()

    def _is_ai_mode(self) -> bool:
        return self.mode_var.get().startswith('AI')

    def _ai_depth(self) -> int:
        m = self.mode_var.get().lower()
        if 'easy' in m:
            return DIFFICULTY_DEPTH['easy']
        if 'medium' in m:
            return DIFFICULTY_DEPTH['medium']
        return DIFFICULTY_DEPTH['hard']

    def _new_game(self) -> None:
        self.board = Board()
        self.current = PLAYER_1
        self.game_over = False
        self.is_animating = False
        self.ai_thinking = False
        self.hover_col = None
        self._draw_empty_board()
        self._update_preview()
        self._update_status()

    # -- Status / preview ----------------------------------------------------

    def _update_status(self) -> None:
        if self.game_over:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            who = 'AI'
        else:
            who = f'Player {self.current}'
        color = PLAYER_COLORS[self.current][0]
        self.status.configure(text=f'{who}’s turn', text_color=color)

    def _update_preview(self) -> None:
        self.preview.delete('all')
        if (self.game_over or self.is_animating or self.ai_thinking
                or self.hover_col is None):
            return
        col = self.hover_col
        if self.board.next_open_row(col) is None:
            return
        # Highlight column.
        self.canvas.itemconfigure(f'col{col}', fill=HOVER_BG)
        cx = col * CELL + CELL // 2
        cy = self.preview.winfo_reqheight() // 2
        radius = CELL // 2 - PAD
        fill, _glow = PLAYER_COLORS[self.current]
        self.preview.create_oval(cx - radius, cy - radius,
                                 cx + radius, cy + radius,
                                 fill=fill, outline='')

    # -- Mouse ---------------------------------------------------------------

    def _column_at(self, x: int) -> Optional[int]:
        col = x // CELL
        if 0 <= col < COLS:
            return int(col)
        return None

    def _on_motion(self, event: tk.Event) -> None:
        if self.game_over or self.is_animating or self.ai_thinking:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        col = self._column_at(event.x)
        if col != self.hover_col:
            # Clear previous overlay.
            if self.hover_col is not None:
                self.canvas.itemconfigure(f'col{self.hover_col}', fill='')
            self.hover_col = col
            self._update_preview()

    def _on_leave(self, _event: tk.Event) -> None:
        if self.hover_col is not None:
            self.canvas.itemconfigure(f'col{self.hover_col}', fill='')
        self.hover_col = None
        self.preview.delete('all')

    def _on_click(self, event: tk.Event) -> None:
        if self.game_over or self.is_animating or self.ai_thinking:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        col = self._column_at(event.x)
        if col is None:
            return
        self._play_move(col)

    # -- Move playing --------------------------------------------------------

    def _play_move(self, col: int) -> None:
        row = self.board.next_open_row(col)
        if row is None:
            return
        self.board.drop(col, self.current)
        self._animate_drop(row, col, self.current,
                           on_done=self._after_move)

    def _after_move(self) -> None:
        win = self.board.winner()
        if win is not None:
            self._end_game_win(win)
            return
        if self.board.is_full():
            self._end_game_draw()
            return
        self.current = other(self.current)
        self._update_status()
        self._update_preview()

        if self._is_ai_mode() and self.current == PLAYER_2 and not self.game_over:
            self._trigger_ai()

    # -- Animation -----------------------------------------------------------

    def _animate_drop(self, target_row: int, col: int, player: int,
                      on_done) -> None:
        """Animate a disc falling from above the board to (target_row, col)."""
        self.is_animating = True
        # Clear any preview/hover artifacts during the drop.
        if self.hover_col is not None:
            self.canvas.itemconfigure(f'col{self.hover_col}', fill='')
        self.preview.delete('all')

        cx = col * CELL + CELL // 2
        radius = CELL // 2 - PAD
        target_y = target_row * CELL + CELL // 2
        # Start above the board (above y=0).
        y = -CELL // 2

        fill, _ = PLAYER_COLORS[player]
        disc = self.canvas.create_oval(
            cx - radius, y - radius, cx + radius, y + radius,
            fill=fill, outline='',
        )

        def step(current_y: int) -> None:
            if current_y >= target_y:
                # Snap to final position.
                self.canvas.coords(disc,
                                   cx - radius, target_y - radius,
                                   cx + radius, target_y + radius)
                self._disc_items[(target_row, col)] = disc
                self.is_animating = False
                on_done()
                return
            new_y = min(current_y + ANIM_PIXELS_PER_FRAME, target_y)
            self.canvas.coords(disc,
                               cx - radius, new_y - radius,
                               cx + radius, new_y + radius)
            self.after(ANIM_STEP_MS, lambda: step(new_y))

        step(y)

    # -- AI ------------------------------------------------------------------

    def _trigger_ai(self) -> None:
        self.ai_thinking = True
        self.status.configure(text='AI thinking…', text_color='#cbd5e1')
        depth = self._ai_depth()

        # Snapshot grid for the worker thread (Board is not thread-safe).
        snapshot = Board(self.board.grid)
        result: dict[str, int] = {}

        def worker() -> None:
            result['col'] = ai_move(snapshot, PLAYER_2, depth=depth)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        def poll() -> None:
            if thread.is_alive():
                self.after(50, poll)
                return
            self.ai_thinking = False
            col = result.get('col')
            if col is None or self.game_over:
                return
            self._play_move(col)

        # Slight delay so the "AI thinking" status is visible even on fast moves.
        self.after(120, poll)

    # -- Endgame -------------------------------------------------------------

    def _highlight_win(self) -> None:
        line = self.board.winning_line()
        if not line:
            return
        for r, c in line:
            cx, cy = _slot_center(r, c)
            # Draw a glow ring under the disc.
            self.canvas.create_oval(
                cx - CELL // 2 + 3, cy - CELL // 2 + 3,
                cx + CELL // 2 - 3, cy + CELL // 2 - 3,
                outline=WIN_BG, width=4, tags=('winring',),
            )
            disc = self._disc_items.get((r, c))
            if disc is not None:
                self.canvas.tag_raise(disc)

    def _end_game_win(self, winner: int) -> None:
        self.game_over = True
        self._highlight_win()
        if self._is_ai_mode() and winner == PLAYER_2:
            text = 'AI wins!'
        else:
            text = f'Player {winner} wins!'
        self.status.configure(text=text, text_color=PLAYER_COLORS[winner][0])

    def _end_game_draw(self) -> None:
        self.game_over = True
        self.status.configure(text="It's a draw.", text_color='#cbd5e1')


if __name__ == '__main__':
    FourInARowApp().mainloop()
