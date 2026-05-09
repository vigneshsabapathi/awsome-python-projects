"""Mancala — CustomTkinter GUI.

A modern desktop UI for Kalah Mancala with animated stone-sowing
(one stone at a time, ~150ms apart), AI mode dropdown, and an
"Awari" variant toggle.

Run:
    uv run python mancala/mancala_gui.py
"""
from __future__ import annotations

import threading
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from mancala import (
    DIFFICULTY_DEPTH,
    P1_PITS,
    P1_STORE,
    P2_PITS,
    P2_STORE,
    PLAYER_1,
    PLAYER_2,
    Board,
    ai_move,
    legal_labels_for,
    other,
    pits_of,
    store_of,
)

# --- Visuals ----------------------------------------------------------------

PIT_R = 46                # pit circle radius
STORE_W = 90              # store width
STORE_H = 2 * PIT_R + 60  # store height
PAD_X = 22                # horizontal pad between pits
PAD_Y = 22                # vertical pad between rows
MARGIN = 30               # outer canvas margin

BG = '#0f172a'
BOARD_BG = '#7c2d12'      # mancala-board brown
PIT_BG = '#fde68a'        # warm sand
PIT_OUTLINE = '#78350f'
STORE_BG = '#fcd34d'
HIGHLIGHT = '#34d399'     # legal-pit ring
TURN_HIGHLIGHT = '#38bdf8'

P1_STONE = '#dc2626'
P2_STONE = '#1d4ed8'
NEUTRAL_STONE = '#475569'

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 13)
COUNT_FONT = ('Segoe UI', 18, 'bold')
STORE_FONT = ('Segoe UI', 22, 'bold')
STATUS_FONT = ('Segoe UI', 14, 'bold')

ANIM_STEP_MS = 150        # ms between sown stones


def _stone_color(cell: int) -> str:
    """Stone fill color for visual variety; differs per row."""
    if cell in P1_PITS or cell == P1_STORE:
        return P1_STONE
    if cell in P2_PITS or cell == P2_STORE:
        return P2_STONE
    return NEUTRAL_STONE


# --- App --------------------------------------------------------------------


class MancalaApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Mancala')

        # Layout sizing.
        self.row_w = 6 * (2 * PIT_R) + 5 * PAD_X
        self.canvas_w = MARGIN * 2 + STORE_W * 2 + PAD_X * 2 + self.row_w
        self.canvas_h = MARGIN * 2 + 2 * (2 * PIT_R) + PAD_Y

        win_w = self.canvas_w + 40
        win_h = self.canvas_h + 220
        self.geometry(f'{win_w}x{win_h}')
        self.minsize(win_w, win_h)
        self.configure(fg_color=BG)

        # Game state.
        self.board = Board()
        self.current: int = PLAYER_1
        self.game_over: bool = False
        self.is_animating: bool = False
        self.ai_thinking: bool = False

        self.mode_var = ctk.StringVar(value='2P')
        self.awari_var = ctk.BooleanVar(value=False)

        # Canvas item registries.
        self._pit_circles: dict[int, int] = {}
        self._pit_count_labels: dict[int, int] = {}
        self._pit_rings: dict[int, int] = {}
        self._store_count_labels: dict[int, int] = {}
        self._stone_items: dict[int, list[int]] = {}  # cell -> stone canvas ids

        # Geometry registry.
        self._pit_centers: dict[int, tuple[int, int]] = {}
        self._store_rects: dict[int, tuple[int, int, int, int]] = {}

        self._build_ui()
        self._new_game()

    # -- UI build -----------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=16, fill='x')
        ctk.CTkLabel(header, text='MANCALA', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header,
                     text='Sow stones counter-clockwise. Land in your store '
                          'for a free turn; in your empty pit to capture.',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Bottom controls.
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(side='bottom', pady=(6, 12), padx=16, fill='x')

        ctk.CTkLabel(bottom, text='Mode:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 6))
        self.mode_menu = ctk.CTkOptionMenu(
            bottom,
            values=['2P', 'AI Easy', 'AI Medium', 'AI Hard', 'AI Expert'],
            variable=self.mode_var,
            command=self._on_mode_change,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b',
        )
        self.mode_menu.pack(side='left')

        self.awari_switch = ctk.CTkSwitch(
            bottom, text='Awari (no extra turn)',
            variable=self.awari_var, command=self._on_awari_toggle,
            text_color='#cbd5e1',
        )
        self.awari_switch.pack(side='left', padx=(16, 0))

        self.new_btn = ctk.CTkButton(
            bottom, text='New Game', width=110,
            fg_color='#334155', hover_color='#475569',
            command=self._new_game,
        )
        self.new_btn.pack(side='right')

        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='bottom', pady=(0, 4))

        # Canvas.
        wrap = ctk.CTkFrame(self, fg_color='#1c1917', corner_radius=14)
        wrap.pack(side='top', pady=10)
        self.canvas = tk.Canvas(wrap, width=self.canvas_w, height=self.canvas_h,
                                bg=BOARD_BG, highlightthickness=0)
        self.canvas.pack(padx=10, pady=10)

        self._draw_board()

        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<Motion>', self._on_motion)

    def _draw_board(self) -> None:
        c = self.canvas
        c.delete('all')
        self._pit_circles.clear()
        self._pit_count_labels.clear()
        self._pit_rings.clear()
        self._store_count_labels.clear()
        self._stone_items.clear()
        self._pit_centers.clear()
        self._store_rects.clear()

        # P2 store on the LEFT, P1 store on the RIGHT.
        # Rows: P2 pits on top (right-to-left in user view), P1 pits on bottom.
        store_y0 = MARGIN
        store_y1 = MARGIN + 2 * PIT_R + PAD_Y + 2 * PIT_R

        # P2 store (left).
        p2s_x0 = MARGIN
        p2s_x1 = p2s_x0 + STORE_W
        self._draw_store(P2_STORE, p2s_x0, store_y0, p2s_x1, store_y1, 'P2')

        # Row pits area X bounds.
        row_x0 = p2s_x1 + PAD_X
        # Centers for pits.
        pit_d = 2 * PIT_R
        # Top row (P2 pits) — visually pit 12 (P2's leftmost pit) is on the
        # left, pit 7 on the right. So as x increases, we visit P2_PITS in
        # reverse order: 12, 11, 10, 9, 8, 7.
        top_y = MARGIN + PIT_R
        bot_y = MARGIN + pit_d + PAD_Y + PIT_R

        for i, pit in enumerate(reversed(P2_PITS)):
            cx = row_x0 + PIT_R + i * (pit_d + PAD_X)
            self._pit_centers[pit] = (cx, top_y)
            self._draw_pit(pit, cx, top_y)

        for i, pit in enumerate(P1_PITS):
            cx = row_x0 + PIT_R + i * (pit_d + PAD_X)
            self._pit_centers[pit] = (cx, bot_y)
            self._draw_pit(pit, cx, bot_y)

        # P1 store (right).
        p1s_x0 = row_x0 + 6 * pit_d + 5 * PAD_X + PAD_X
        p1s_x1 = p1s_x0 + STORE_W
        self._draw_store(P1_STORE, p1s_x0, store_y0, p1s_x1, store_y1, 'P1')

        # Player labels under/above pits.
        # Pit number labels for users (1..6 from each player's perspective).
        for i, pit in enumerate(P1_PITS):
            cx, _ = self._pit_centers[pit]
            c.create_text(cx, bot_y + PIT_R + 14, text=str(i + 1),
                          fill='#fde68a', font=('Segoe UI', 10, 'bold'))
        for i, pit in enumerate(P2_PITS):
            cx, _ = self._pit_centers[pit]
            c.create_text(cx, top_y - PIT_R - 14, text=str(i + 1),
                          fill='#bfdbfe', font=('Segoe UI', 10, 'bold'))

    def _draw_pit(self, pit: int, cx: int, cy: int) -> None:
        c = self.canvas
        ring = c.create_oval(cx - PIT_R - 4, cy - PIT_R - 4,
                             cx + PIT_R + 4, cy + PIT_R + 4,
                             outline='', width=4, tags=(f'ring-{pit}',))
        circle = c.create_oval(cx - PIT_R, cy - PIT_R,
                               cx + PIT_R, cy + PIT_R,
                               fill=PIT_BG, outline=PIT_OUTLINE, width=2,
                               tags=(f'pit-{pit}',))
        count = c.create_text(cx, cy, text='0', fill='#1c1917',
                              font=COUNT_FONT, tags=(f'count-{pit}',))
        self._pit_circles[pit] = circle
        self._pit_rings[pit] = ring
        self._pit_count_labels[pit] = count
        self._stone_items[pit] = []

    def _draw_store(self, store: int, x0: int, y0: int, x1: int, y1: int,
                    label: str) -> None:
        c = self.canvas
        # Rounded-ish rectangle (approx via thick rectangle).
        c.create_rectangle(x0, y0, x1, y1, fill=STORE_BG,
                           outline=PIT_OUTLINE, width=3,
                           tags=(f'store-{store}',))
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        # Big count.
        count_id = c.create_text(cx, cy - 14, text='0', fill='#1c1917',
                                 font=STORE_FONT,
                                 tags=(f'storecount-{store}',))
        c.create_text(cx, cy + 22, text=label, fill='#1c1917',
                      font=('Segoe UI', 12, 'bold'))
        self._store_count_labels[store] = count_id
        self._store_rects[store] = (x0, y0, x1, y1)
        self._stone_items[store] = []

    # -- State --------------------------------------------------------------

    def _on_mode_change(self, _value: str) -> None:
        self._new_game()

    def _on_awari_toggle(self) -> None:
        self._new_game()

    def _is_ai_mode(self) -> bool:
        return self.mode_var.get().startswith('AI')

    def _ai_depth(self) -> int:
        m = self.mode_var.get().lower()
        if 'easy' in m:
            return DIFFICULTY_DEPTH['easy']
        if 'medium' in m:
            return DIFFICULTY_DEPTH['medium']
        if 'expert' in m:
            return DIFFICULTY_DEPTH['expert']
        return DIFFICULTY_DEPTH['hard']

    def _new_game(self) -> None:
        self.board = Board(awari=self.awari_var.get())
        self.current = PLAYER_1
        self.game_over = False
        self.is_animating = False
        self.ai_thinking = False
        self._refresh_all_cells()
        self._update_status()
        self._update_legal_rings()

    def _refresh_all_cells(self) -> None:
        for pit in (*P1_PITS, *P2_PITS):
            self._refresh_pit(pit)
        self._refresh_store(P1_STORE)
        self._refresh_store(P2_STORE)

    def _refresh_pit(self, pit: int) -> None:
        n = self.board.pits[pit]
        self.canvas.itemconfigure(self._pit_count_labels[pit], text=str(n))
        # Draw small visualization stones (cap at 12 to keep it neat).
        self._redraw_stones_in_pit(pit)

    def _refresh_store(self, store: int) -> None:
        n = self.board.pits[store]
        self.canvas.itemconfigure(self._store_count_labels[store], text=str(n))

    def _redraw_stones_in_pit(self, pit: int) -> None:
        c = self.canvas
        for sid in self._stone_items[pit]:
            c.delete(sid)
        self._stone_items[pit] = []
        n = self.board.pits[pit]
        if n <= 0:
            return
        cx, cy = self._pit_centers[pit]
        # Place up to 9 small stones in a 3x3 grid; if more, just draw 9 + show count.
        max_visible = 9
        size = 9
        positions = []
        for r in range(3):
            for col in range(3):
                positions.append((cx - 18 + col * 18, cy - 18 + r * 18))
        for i in range(min(n, max_visible)):
            x, y = positions[i]
            sid = c.create_oval(x - size, y - size, x + size, y + size,
                                fill=_stone_color(pit), outline='')
            self._stone_items[pit].append(sid)
        # Make sure count label stays on top.
        c.tag_raise(self._pit_count_labels[pit])

    def _update_status(self) -> None:
        if self.game_over:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            who = 'AI'
        else:
            who = f'Player {self.current}'
        color = P1_STONE if self.current == PLAYER_1 else P2_STONE
        self.status.configure(text=f'{who}’s turn', text_color=color)

    def _update_legal_rings(self) -> None:
        # Reset all rings.
        for pit, ring in self._pit_rings.items():
            self.canvas.itemconfigure(ring, outline='')
        if self.game_over or self.is_animating or self.ai_thinking:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        for pit in self.board.legal_moves(self.current):
            self.canvas.itemconfigure(self._pit_rings[pit], outline=HIGHLIGHT)

    # -- Mouse --------------------------------------------------------------

    def _pit_at(self, x: int, y: int) -> Optional[int]:
        for pit, (cx, cy) in self._pit_centers.items():
            if (x - cx) ** 2 + (y - cy) ** 2 <= PIT_R ** 2:
                return pit
        return None

    def _on_motion(self, event: tk.Event) -> None:
        if self.game_over or self.is_animating or self.ai_thinking:
            self.canvas.config(cursor='')
            return
        pit = self._pit_at(event.x, event.y)
        legal = pit in self.board.legal_moves(self.current)
        if self._is_ai_mode() and self.current == PLAYER_2:
            legal = False
        self.canvas.config(cursor='hand2' if legal else '')

    def _on_click(self, event: tk.Event) -> None:
        if self.game_over or self.is_animating or self.ai_thinking:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        pit = self._pit_at(event.x, event.y)
        if pit is None:
            return
        if pit not in self.board.legal_moves(self.current):
            return
        self._play_move(pit)

    # -- Move + animation ---------------------------------------------------

    def _play_move(self, pit: int) -> None:
        # Compute the result *and* the sow path on a snapshot so we can
        # animate stone movement against the previous-state numbers.
        snapshot = self.board.copy()
        result = self.board.move(pit)
        # Animate from snapshot up to final state.
        self.is_animating = True
        self._update_legal_rings()
        self._animate_sow(snapshot, pit, result, on_done=self._after_move)

    def _animate_sow(self, snapshot: Board, source_pit: int,
                     result: dict, on_done) -> None:
        """Stone-by-stone sow animation, ~ANIM_STEP_MS apart."""
        # Display state starts at the snapshot.
        # We mutate ``display`` cell by cell to match the canonical sow path.
        display = snapshot.copy()
        # Empty source pit immediately for visual punch.
        display.pits[source_pit] = 0
        self._refresh_pit(source_pit)

        path = result['sow_path']

        def step(i: int) -> None:
            if i >= len(path):
                # Apply capture if any (clears own_pit + opp_pit, adds to store).
                cap = result.get('capture')
                if cap:
                    display.pits[cap['own_pit']] = 0
                    display.pits[cap['opp_pit']] = 0
                    display.pits[cap['store']] += cap['stones']
                    self._refresh_pit(cap['own_pit'])
                    self._refresh_pit(cap['opp_pit'])
                    self._refresh_store(cap['store'])
                # Apply sweep if game ended.
                sweep = result.get('sweep')
                if sweep:
                    for p in P1_PITS:
                        display.pits[p] = 0
                        self._refresh_pit(p)
                    for p in P2_PITS:
                        display.pits[p] = 0
                        self._refresh_pit(p)
                    display.pits[P1_STORE] += sweep['p1']
                    display.pits[P2_STORE] += sweep['p2']
                    self._refresh_store(P1_STORE)
                    self._refresh_store(P2_STORE)
                self.is_animating = False
                on_done(result)
                return
            cell = path[i]
            display.pits[cell] += 1
            if cell in (P1_STORE, P2_STORE):
                self._refresh_store(cell)
            else:
                self._refresh_pit(cell)
            self._flash_cell(cell)
            self.after(ANIM_STEP_MS, lambda: step(i + 1))

        step(0)

    def _flash_cell(self, cell: int) -> None:
        """Brief outline flash on the cell that just received a stone."""
        if cell in self._pit_rings:
            ring = self._pit_rings[cell]
            self.canvas.itemconfigure(ring, outline=TURN_HIGHLIGHT)
            self.after(120, lambda: self._update_legal_rings())
        # Stores: nothing to flash visually.

    def _after_move(self, result: dict) -> None:
        if result['game_over']:
            self._end_game(result)
            return
        self.current = result['next_player']
        if result['free_turn']:
            self._set_status('Free turn!', '#34d399')
            self.after(500, self._update_status)
        else:
            self._update_status()
        self._update_legal_rings()

        if self._is_ai_mode() and self.current == PLAYER_2 and not self.game_over:
            self._trigger_ai()

    def _set_status(self, text: str, color: str) -> None:
        self.status.configure(text=text, text_color=color)

    # -- AI -----------------------------------------------------------------

    def _trigger_ai(self) -> None:
        self.ai_thinking = True
        self.status.configure(text='AI thinking…', text_color='#cbd5e1')
        depth = self._ai_depth()
        snapshot = self.board.copy()
        result: dict[str, int] = {}

        def worker() -> None:
            result['pit'] = ai_move(snapshot, PLAYER_2, depth=depth)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

        def poll() -> None:
            if thread.is_alive():
                self.after(60, poll)
                return
            self.ai_thinking = False
            pit = result.get('pit')
            if pit is None or self.game_over:
                return
            self._play_move(pit)

        self.after(180, poll)

    # -- Endgame ------------------------------------------------------------

    def _end_game(self, result: dict) -> None:
        self.game_over = True
        self._update_legal_rings()
        winner = result['winner']
        s1 = self.board.score(PLAYER_1)
        s2 = self.board.score(PLAYER_2)
        if winner == 0:
            self.status.configure(text=f"Draw {s1}–{s2}",
                                  text_color='#cbd5e1')
        elif self._is_ai_mode() and winner == PLAYER_2:
            self.status.configure(text=f'AI wins {s2}–{s1}',
                                  text_color=P2_STONE)
        else:
            color = P1_STONE if winner == PLAYER_1 else P2_STONE
            self.status.configure(
                text=f'Player {winner} wins {max(s1, s2)}–{min(s1, s2)}',
                text_color=color,
            )


if __name__ == '__main__':
    MancalaApp().mainloop()
