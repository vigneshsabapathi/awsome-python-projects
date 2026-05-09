"""Royal Game of Ur — CustomTkinter GUI.

Dark-themed desktop UI for the Royal Game of Ur. The H-shaped board is
drawn on a tk.Canvas with rosettes marked, pieces as colored circles,
and an animated dice roll.

Click your piece (or the start pile) after rolling to move it. Rosettes
grant a bonus turn.

Run:
    uv run python ur/ur_gui.py
"""
from __future__ import annotations

import random
import threading
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from ur import (
    DIFFICULTY_DEPTH,
    FINISH,
    PIECES_PER_PLAYER,
    PLAYER_1,
    PLAYER_2,
    ROSETTES,
    SHARED_RANGE,
    START,
    Board,
    ai_move,
    other,
    roll,
)

# --- Visuals ----------------------------------------------------------------

CELL = 70                 # cell side in px
CELL_PAD = 6
MARGIN = 36
PIECE_R = 22

BG = '#0f172a'
BOARD_BG = '#1c1917'
CELL_BG = '#fde68a'
CELL_OUTLINE = '#78350f'
ROSETTE_BG = '#fb923c'
SHARED_BG = '#fcd34d'

P1_COLOR = '#dc2626'
P2_COLOR = '#1d4ed8'
HIGHLIGHT = '#34d399'
LAST_HL = '#a3e635'

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 13)
DICE_FONT = ('Segoe UI', 28, 'bold')
STATUS_FONT = ('Segoe UI', 14, 'bold')

ANIM_STEP_MS = 220
DICE_ANIM_MS = 60
DICE_ANIM_TICKS = 8


# Board geometry mapping (player path 1..14 -> grid (col, row) on a 3-row
# H-shape). Top row = P2 path private + private-end; mid row = shared;
# bottom row = P1 path private + private-end.
#
# Layout (cols 0..7, rows 0..2):
#
#   col:        0    1    2    3    4    5    6    7
#   row 0 (P2): 4    3    2    1                   14   13
#   row 1 (sh):                5    6    7    8    9   10   11   12
#   row 2 (P1): 4    3    2    1                   14   13
#
# We split into two halves visually: cols 0..3 for the private "left" segment
# (squares 4..1 from outside in), cols 4..7 for the shared row stretch and
# the private end. We'll use 8 cols total but the shared row spans cols 0..7
# (squares 5..12 for shared row; we need 8 squares = 8 cols).
#
# Simpler: use 8 columns; private rows span cols 0..3 and 6..7 (4 + 2 cells);
# shared row spans all 8 cols (squares 5..12 = 8 squares).

# Private squares mapped to cols on top/bottom rows.
PRIVATE_TOP_COLS = {4: 0, 3: 1, 2: 2, 1: 3, 14: 6, 13: 7}
# (For P1 path, same column mapping; just the row differs.)
SHARED_COLS = {5: 0, 6: 1, 7: 2, 8: 3, 9: 4, 10: 5, 11: 6, 12: 7}
# Note: cols 4 and 5 on top/bottom rows are EMPTY (the H-shape gap).

NUM_COLS = 8
NUM_ROWS = 3


def _square_cell(player: int, square: int) -> Optional[tuple[int, int]]:
    """Return (col, row) on the canvas grid for a player's path square,
    or None for off-board squares (start / finish)."""
    if square == START or square == FINISH:
        return None
    if 1 <= square <= 4 or 13 <= square <= 14:
        col = PRIVATE_TOP_COLS[square]
        row = 0 if player == PLAYER_2 else 2
        return (col, row)
    if 5 <= square <= 12:
        return (SHARED_COLS[square], 1)
    return None


# --- App --------------------------------------------------------------------


class UrApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Royal Game of Ur')

        self.canvas_w = MARGIN * 2 + NUM_COLS * CELL
        self.canvas_h = MARGIN * 2 + NUM_ROWS * CELL + 2 * (PIECE_R + 18)
        win_w = self.canvas_w + 320
        win_h = self.canvas_h + 200
        self.geometry(f'{win_w}x{win_h}')
        self.minsize(win_w, win_h)
        self.configure(fg_color=BG)

        self.rng = random.Random()

        # Game state.
        self.board = Board()
        self.current: int = PLAYER_1
        self.current_dice: Optional[int] = None
        self.has_rolled: bool = False
        self.is_animating: bool = False
        self.ai_thinking: bool = False
        self.game_over: bool = False
        self.last_to: int = -1

        self.mode_var = ctk.StringVar(value='2P')
        self.finkel_var = ctk.BooleanVar(value=True)

        # Canvas item registries.
        self._piece_items: dict[tuple[int, int], int] = {}  # (player, idx) -> oval id
        self._cell_rects: dict[tuple[int, int, int], int] = {}  # (player, square, row?) -> rect id
        self._shared_rects: dict[int, int] = {}  # square -> rect id

        self._build_ui()
        self._new_game()

    # -- UI build ----------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=16, fill='x')
        ctk.CTkLabel(header, text='ROYAL GAME OF UR', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header,
                     text='Race 7 pieces along your path. Roll the dice, '
                          'click a piece. Rosettes (orange) give a bonus turn.',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Body: canvas (left) + control panel (right).
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=12, pady=8)

        canvas_wrap = ctk.CTkFrame(body, fg_color='#1c1917', corner_radius=14)
        canvas_wrap.pack(side='left', padx=(4, 8), pady=4)
        self.canvas = tk.Canvas(canvas_wrap, width=self.canvas_w,
                                height=self.canvas_h, bg=BOARD_BG,
                                highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Motion>', self._on_motion)

        # Right control column.
        ctrl = ctk.CTkFrame(body, fg_color='#111827', corner_radius=12)
        ctrl.pack(side='left', fill='y', padx=(4, 4), pady=4)

        ctk.CTkLabel(ctrl, text='Mode', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(pady=(12, 2), padx=12)
        self.mode_menu = ctk.CTkOptionMenu(
            ctrl, values=['2P', 'AI Easy', 'AI Medium', 'AI Hard'],
            variable=self.mode_var, command=self._on_mode_change,
            fg_color='#334155', button_color='#475569',
        )
        self.mode_menu.pack(padx=12, pady=(0, 8))

        self.finkel_switch = ctk.CTkSwitch(
            ctrl, text='Finkel rules\n(rosettes safe)',
            variable=self.finkel_var, command=self._on_rules_toggle,
            text_color='#cbd5e1',
        )
        self.finkel_switch.pack(pady=(4, 12), padx=12)

        # Dice display.
        dice_box = ctk.CTkFrame(ctrl, fg_color='#0b1220', corner_radius=10)
        dice_box.pack(padx=12, pady=(8, 4), fill='x')
        ctk.CTkLabel(dice_box, text='Dice (sum 0..4)',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(8, 0))
        self.dice_label = ctk.CTkLabel(dice_box, text='–',
                                       font=DICE_FONT, text_color='#fde68a')
        self.dice_label.pack(pady=4)
        # Mini binary-die display.
        self.dice_dots = ctk.CTkLabel(dice_box, text='[ ][ ][ ][ ]',
                                      font=('Consolas', 14),
                                      text_color='#fbbf24')
        self.dice_dots.pack(pady=(0, 8))

        self.roll_btn = ctk.CTkButton(
            ctrl, text='Roll Dice', width=180, height=42,
            fg_color='#16a34a', hover_color='#15803d',
            font=('Segoe UI', 15, 'bold'),
            command=self._on_roll,
        )
        self.roll_btn.pack(padx=12, pady=8)

        self.new_btn = ctk.CTkButton(
            ctrl, text='New Game', width=180, height=36,
            fg_color='#334155', hover_color='#475569',
            command=self._new_game,
        )
        self.new_btn.pack(padx=12, pady=(4, 12))

        # Score display.
        score_box = ctk.CTkFrame(ctrl, fg_color='#0b1220', corner_radius=10)
        score_box.pack(padx=12, pady=(4, 8), fill='x')
        self.score_p1 = ctk.CTkLabel(score_box, text='P1 0/7',
                                     font=LABEL_FONT, text_color=P1_COLOR)
        self.score_p1.pack(pady=(8, 2))
        self.score_p2 = ctk.CTkLabel(score_box, text='P2 0/7',
                                     font=LABEL_FONT, text_color='#93c5fd')
        self.score_p2.pack(pady=(2, 8))

        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='bottom', pady=(0, 8))

        self._draw_board()

    def _draw_board(self) -> None:
        c = self.canvas
        c.delete('all')

        # Grid cell origin at (MARGIN, MARGIN + start_pile_row)
        # Reserve top region for P2 start pile + score.
        start_y_offset = PIECE_R + 18

        # Helper: draw cell rect.
        def draw_cell(col: int, row: int, square: int, player_label: str,
                      draw: bool = True) -> tuple[int, int]:
            x0 = MARGIN + col * CELL + CELL_PAD
            y0 = MARGIN + start_y_offset + row * CELL + CELL_PAD
            x1 = x0 + CELL - 2 * CELL_PAD
            y1 = y0 + CELL - 2 * CELL_PAD
            if not draw:
                return ((x0 + x1) // 2, (y0 + y1) // 2)
            fill = CELL_BG
            if square in ROSETTES:
                fill = ROSETTE_BG
            elif row == 1:
                fill = SHARED_BG
            rect = c.create_rectangle(
                x0, y0, x1, y1, fill=fill, outline=CELL_OUTLINE, width=2,
                tags=(f'cell-{player_label}-{square}', f'sq-{square}'),
            )
            # Label number.
            c.create_text(
                x0 + 8, y0 + 8, text=str(square), anchor='nw',
                fill='#7c2d12', font=('Segoe UI', 9, 'bold'),
            )
            if square in ROSETTES:
                c.create_text(
                    (x0 + x1) // 2, (y0 + y1) // 2,
                    text='*', fill='#7c2d12',
                    font=('Segoe UI', 24, 'bold'),
                )
            return ((x0 + x1) // 2, (y0 + y1) // 2)

        # P2 private (top row).
        for sq, col in PRIVATE_TOP_COLS.items():
            draw_cell(col, 0, sq, f'p{PLAYER_2}')
        # Shared row.
        for sq, col in SHARED_COLS.items():
            # Use a single shared rect (no player tag) — accessible from both.
            x0 = MARGIN + col * CELL + CELL_PAD
            y0 = MARGIN + start_y_offset + 1 * CELL + CELL_PAD
            x1 = x0 + CELL - 2 * CELL_PAD
            y1 = y0 + CELL - 2 * CELL_PAD
            fill = ROSETTE_BG if sq in ROSETTES else SHARED_BG
            rect = c.create_rectangle(
                x0, y0, x1, y1, fill=fill, outline=CELL_OUTLINE, width=2,
                tags=(f'shared-{sq}', f'sq-{sq}'),
            )
            self._shared_rects[sq] = rect
            c.create_text(
                x0 + 8, y0 + 8, text=str(sq), anchor='nw',
                fill='#7c2d12', font=('Segoe UI', 9, 'bold'),
            )
            if sq in ROSETTES:
                c.create_text(
                    (x0 + x1) // 2, (y0 + y1) // 2,
                    text='*', fill='#7c2d12',
                    font=('Segoe UI', 24, 'bold'),
                )
        # P1 private (bottom row).
        for sq, col in PRIVATE_TOP_COLS.items():
            draw_cell(col, 2, sq, f'p{PLAYER_1}')

        # Start piles (off-board) above P2 row and below P1 row.
        c.create_text(
            MARGIN + 20, MARGIN + 4, text='P2 start',
            anchor='nw', fill='#93c5fd',
            font=('Segoe UI', 11, 'bold'),
        )
        c.create_text(
            MARGIN + 20,
            MARGIN + start_y_offset + NUM_ROWS * CELL + 4,
            text='P1 start', anchor='nw', fill='#fca5a5',
            font=('Segoe UI', 11, 'bold'),
        )
        # Finish areas.
        c.create_text(
            MARGIN + NUM_COLS * CELL - 80, MARGIN + 4,
            text='P2 finish', anchor='nw', fill='#93c5fd',
            font=('Segoe UI', 11, 'bold'),
        )
        c.create_text(
            MARGIN + NUM_COLS * CELL - 80,
            MARGIN + start_y_offset + NUM_ROWS * CELL + 4,
            text='P1 finish', anchor='nw', fill='#fca5a5',
            font=('Segoe UI', 11, 'bold'),
        )

    # -- Coordinate helpers ------------------------------------------------

    def _piece_position_xy(self, player: int, square: int,
                           piece_idx: int) -> tuple[int, int]:
        """Where (cx, cy) to draw the given piece on the canvas."""
        start_y_offset = PIECE_R + 18
        if square == START:
            # Stack pieces in the start pile.
            base_x = MARGIN + 88 + piece_idx * (PIECE_R + 4)
            if player == PLAYER_2:
                base_y = MARGIN + start_y_offset // 2
            else:
                base_y = (MARGIN + start_y_offset + NUM_ROWS * CELL
                          + start_y_offset // 2)
            return (base_x, base_y)
        if square == FINISH:
            base_x = (MARGIN + NUM_COLS * CELL - 100
                      + piece_idx * (PIECE_R + 4))
            if player == PLAYER_2:
                base_y = MARGIN + start_y_offset // 2
            else:
                base_y = (MARGIN + start_y_offset + NUM_ROWS * CELL
                          + start_y_offset // 2)
            return (base_x, base_y)
        # On-board: center of the cell.
        cell = _square_cell(player, square)
        if cell is None:
            return (0, 0)
        col, row = cell
        cx = MARGIN + col * CELL + CELL // 2
        cy = MARGIN + start_y_offset + row * CELL + CELL // 2
        # Offset slightly to avoid full overlap with the cell number text.
        return (cx, cy + 4)

    def _redraw_pieces(self) -> None:
        c = self.canvas
        for item in self._piece_items.values():
            c.delete(item)
        self._piece_items.clear()
        for player in (PLAYER_1, PLAYER_2):
            color = P1_COLOR if player == PLAYER_1 else P2_COLOR
            for i, sq in enumerate(self.board.pieces[player]):
                cx, cy = self._piece_position_xy(player, sq, i)
                pid = c.create_oval(
                    cx - PIECE_R, cy - PIECE_R, cx + PIECE_R, cy + PIECE_R,
                    fill=color, outline='#fef3c7', width=2,
                    tags=(f'piece-{player}-{i}',),
                )
                self._piece_items[(player, i)] = pid

    # -- Highlights ---------------------------------------------------------

    def _clear_highlights(self) -> None:
        # Reset all piece outlines.
        for (player, i), pid in self._piece_items.items():
            self.canvas.itemconfigure(pid, outline='#fef3c7', width=2)

    def _highlight_legal(self) -> None:
        self._clear_highlights()
        if self.game_over or self.is_animating or self.ai_thinking:
            return
        if not self.has_rolled or self.current_dice is None:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        legal = self.board.legal_moves(self.current, self.current_dice)
        for i in legal:
            pid = self._piece_items.get((self.current, i))
            if pid:
                self.canvas.itemconfigure(pid, outline=HIGHLIGHT, width=4)

    # -- Game state ---------------------------------------------------------

    def _is_ai_mode(self) -> bool:
        return self.mode_var.get().startswith('AI')

    def _ai_depth(self) -> int:
        m = self.mode_var.get().lower()
        if 'easy' in m:
            return DIFFICULTY_DEPTH['easy']
        if 'hard' in m:
            return DIFFICULTY_DEPTH['hard']
        return DIFFICULTY_DEPTH['medium']

    def _on_mode_change(self, _value: str) -> None:
        self._new_game()

    def _on_rules_toggle(self) -> None:
        self._new_game()

    def _new_game(self) -> None:
        self.board = Board(finkel=self.finkel_var.get())
        self.current = PLAYER_1
        self.current_dice = None
        self.has_rolled = False
        self.is_animating = False
        self.ai_thinking = False
        self.game_over = False
        self.last_to = -1
        self.dice_label.configure(text='–')
        self.dice_dots.configure(text='[ ][ ][ ][ ]')
        self._redraw_pieces()
        self._update_score()
        self._update_status()
        self.roll_btn.configure(state='normal')

    def _update_score(self) -> None:
        s1 = self.board.finished_count(PLAYER_1)
        s2 = self.board.finished_count(PLAYER_2)
        self.score_p1.configure(text=f'P1 {s1}/{PIECES_PER_PLAYER}')
        self.score_p2.configure(text=f'P2 {s2}/{PIECES_PER_PLAYER}')

    def _update_status(self) -> None:
        if self.game_over:
            return
        who = 'AI' if self._is_ai_mode() and self.current == PLAYER_2 \
            else f'Player {self.current}'
        color = P1_COLOR if self.current == PLAYER_1 else '#93c5fd'
        if not self.has_rolled:
            self.status.configure(text=f"{who}'s turn — click Roll",
                                  text_color=color)
        else:
            self.status.configure(text=f"{who} rolled {self.current_dice}",
                                  text_color=color)

    # -- Roll button --------------------------------------------------------

    def _on_roll(self) -> None:
        if self.game_over or self.is_animating or self.ai_thinking:
            return
        if self.has_rolled:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        self._do_roll(after=self._after_human_roll)

    def _do_roll(self, after) -> None:
        self.roll_btn.configure(state='disabled')
        # Animate dice for a few ticks before settling on the real value.
        final = roll(self.rng)
        self._animate_dice(DICE_ANIM_TICKS, final, after)

    def _animate_dice(self, ticks_left: int, final: int, after) -> None:
        if ticks_left <= 0:
            # Show the real result.
            self.current_dice = final
            self.has_rolled = True
            dots = ''.join('[*]' if d else '[ ]'
                           for d in self._reveal_die_pattern(final))
            self.dice_label.configure(text=str(final))
            self.dice_dots.configure(text=dots)
            after()
            return
        # Show a random temporary value.
        temp = self.rng.randint(0, 4)
        dots = ''.join('[*]' if d else '[ ]'
                       for d in self._reveal_die_pattern(temp))
        self.dice_label.configure(text=str(temp))
        self.dice_dots.configure(text=dots)
        self.after(DICE_ANIM_MS, lambda: self._animate_dice(
            ticks_left - 1, final, after))

    def _reveal_die_pattern(self, value: int) -> list[int]:
        # Show ``value`` ones in a 4-slot mini-display. Random which slots.
        slots = [0, 0, 0, 0]
        idxs = list(range(4))
        self.rng.shuffle(idxs)
        for i in idxs[:value]:
            slots[i] = 1
        return slots

    def _after_human_roll(self) -> None:
        self._update_status()
        # If no legal moves, auto-skip turn after a beat.
        if (self.current_dice == 0
                or not self.board.has_any_legal_move(self.current,
                                                    self.current_dice)):
            self.status.configure(
                text=(f"Player {self.current} rolled "
                      f"{self.current_dice} — no moves, turn forfeit."),
                text_color='#94a3b8',
            )
            self.after(900, self._end_turn_no_move)
            return
        self._highlight_legal()

    def _end_turn_no_move(self) -> None:
        self.current = other(self.current)
        self.has_rolled = False
        self.current_dice = None
        self.dice_label.configure(text='–')
        self.dice_dots.configure(text='[ ][ ][ ][ ]')
        self.roll_btn.configure(state='normal')
        self._update_status()
        # If now AI's turn, kick it off.
        if (not self.game_over and self._is_ai_mode()
                and self.current == PLAYER_2):
            self._ai_take_turn()

    # -- Click on piece -----------------------------------------------------

    def _piece_at(self, x: int, y: int) -> Optional[tuple[int, int]]:
        for (player, i), pid in self._piece_items.items():
            x0, y0, x1, y1 = self.canvas.coords(pid)
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if (x - cx) ** 2 + (y - cy) ** 2 <= PIECE_R ** 2:
                return (player, i)
        return None

    def _on_motion(self, event: tk.Event) -> None:
        if (self.game_over or self.is_animating or self.ai_thinking
                or not self.has_rolled or self.current_dice is None):
            self.canvas.config(cursor='')
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            self.canvas.config(cursor='')
            return
        hit = self._piece_at(event.x, event.y)
        if hit is None or hit[0] != self.current:
            self.canvas.config(cursor='')
            return
        legal = self.board.legal_moves(self.current, self.current_dice)
        self.canvas.config(cursor='hand2' if hit[1] in legal else '')

    def _on_click(self, event: tk.Event) -> None:
        if (self.game_over or self.is_animating or self.ai_thinking
                or not self.has_rolled or self.current_dice is None):
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        hit = self._piece_at(event.x, event.y)
        if hit is None:
            return
        player, idx = hit
        if player != self.current:
            return
        legal = self.board.legal_moves(self.current, self.current_dice)
        if idx not in legal:
            return
        self._play_move(idx)

    # -- Move ----------------------------------------------------------------

    def _play_move(self, piece_idx: int) -> None:
        self.is_animating = True
        self._clear_highlights()
        src = self.board.pieces[self.current][piece_idx]
        dst = src + self.current_dice
        result = self.board.move(self.current, piece_idx, self.current_dice)

        # Animate piece movement (just two-step tween src -> dst).
        pid = self._piece_items[(self.current, piece_idx)]
        end_x, end_y = self._piece_position_xy(self.current, dst, piece_idx)
        self._tween_piece(pid, end_x, end_y, lambda: self._after_move(result))

    def _tween_piece(self, pid: int, tx: int, ty: int, on_done) -> None:
        """Animate piece from current pos to (tx, ty)."""
        x0, y0, x1, y1 = self.canvas.coords(pid)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        steps = 8

        def step(i: int) -> None:
            if i >= steps:
                # Snap to final.
                self.canvas.coords(pid, tx - PIECE_R, ty - PIECE_R,
                                   tx + PIECE_R, ty + PIECE_R)
                on_done()
                return
            nx = cx + (tx - cx) * (i + 1) / steps
            ny = cy + (ty - cy) * (i + 1) / steps
            self.canvas.coords(pid, nx - PIECE_R, ny - PIECE_R,
                               nx + PIECE_R, ny + PIECE_R)
            self.after(ANIM_STEP_MS // steps, lambda: step(i + 1))

        step(0)

    def _after_move(self, result: dict) -> None:
        # Capture: send the captured opp piece back to start pile.
        if result['capture']:
            opp = other(result['player'])
            opp_idx = result['capture']['opp_idx']
            opp_pid = self._piece_items[(opp, opp_idx)]
            cap_x, cap_y = self._piece_position_xy(opp, START, opp_idx)
            self._tween_piece(opp_pid, cap_x, cap_y,
                              lambda: self._finalize_move(result))
            return
        self._finalize_move(result)

    def _finalize_move(self, result: dict) -> None:
        self.is_animating = False
        self._update_score()

        if result['game_over']:
            self.game_over = True
            self.has_rolled = False
            w = result['winner']
            if self._is_ai_mode() and w == PLAYER_2:
                self.status.configure(text='AI wins!', text_color='#93c5fd')
            else:
                color = P1_COLOR if w == PLAYER_1 else '#93c5fd'
                self.status.configure(text=f'Player {w} wins!',
                                      text_color=color)
            self.roll_btn.configure(state='disabled')
            return

        if result['free_turn']:
            # Same player rolls again.
            self.has_rolled = False
            self.current_dice = None
            self.dice_label.configure(text='–')
            self.dice_dots.configure(text='[ ][ ][ ][ ]')
            self.status.configure(text='Rosette! Bonus turn — roll again.',
                                  text_color='#34d399')
            self.roll_btn.configure(state='normal')
            if self._is_ai_mode() and self.current == PLAYER_2:
                self.after(450, self._ai_take_turn)
            return

        # Pass turn.
        self.current = result['next_player']
        self.has_rolled = False
        self.current_dice = None
        self.dice_label.configure(text='–')
        self.dice_dots.configure(text='[ ][ ][ ][ ]')
        self.roll_btn.configure(state='normal')
        self._update_status()
        if self._is_ai_mode() and self.current == PLAYER_2:
            self.after(400, self._ai_take_turn)

    # -- AI -----------------------------------------------------------------

    def _ai_take_turn(self) -> None:
        if self.game_over:
            return
        # AI rolls.
        self._do_roll(after=self._after_ai_roll)

    def _after_ai_roll(self) -> None:
        self.status.configure(text=f'AI rolled {self.current_dice}',
                              text_color='#93c5fd')
        if (self.current_dice == 0
                or not self.board.has_any_legal_move(self.current,
                                                    self.current_dice)):
            self.status.configure(
                text=f'AI rolled {self.current_dice} — no moves, forfeit.',
                text_color='#94a3b8',
            )
            self.after(900, self._end_turn_no_move)
            return
        # Run AI search in a worker thread.
        self.ai_thinking = True
        self.status.configure(text='AI thinking…',
                              text_color='#94a3b8')
        depth = self._ai_depth()
        snapshot = self.board.copy()
        dice = self.current_dice
        result_holder: dict[str, int] = {}

        def worker() -> None:
            result_holder['idx'] = ai_move(snapshot, PLAYER_2, dice,
                                           depth=depth)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        def poll() -> None:
            if thread.is_alive():
                self.after(80, poll)
                return
            self.ai_thinking = False
            idx = result_holder.get('idx', -1)
            if idx < 0 or self.game_over:
                return
            self._play_move(idx)

        self.after(220, poll)


if __name__ == '__main__':
    UrApp().mainloop()
