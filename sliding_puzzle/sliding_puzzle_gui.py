"""Sliding Tile Puzzle — CustomTkinter desktop GUI.

A polished dark-themed window over a tk.Canvas. Each numbered tile is a
rounded rectangle that *slides* into the blank cell with a short animation.
Click a tile adjacent to the blank or use the arrow keys; the move counter
and timer update live. The hint button shows the next A*-optimal move as a
faint highlighted target.

Run:
    uv run python sliding_puzzle/sliding_puzzle_gui.py
"""
from __future__ import annotations

import random
import time
import tkinter as tk

import customtkinter as ctk

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

# --- palette (Tailwind-ish dark) ------------------------------------------------
BG_APP = '#0f172a'
BG_BOARD = '#1e293b'
BG_BLANK = '#0b1220'
TILE_BG = '#3b82f6'
TILE_BG_GOAL = '#16a34a'
TILE_BG_HINT = '#f59e0b'
TILE_FG = '#f8fafc'
ACCENT = '#38bdf8'
MUTED = '#94a3b8'
ERROR = '#f87171'
WIN = '#34d399'

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 13)
STATUS_FONT = ('Segoe UI', 13)
TILE_FONT = ('Segoe UI', 28, 'bold')

TILE_SIZE = 90
TILE_PAD = 6
ANIM_FRAMES = 8
ANIM_DELAY_MS = 14

KEY_TO_DIR = {
    'Up': UP, 'Down': DOWN, 'Left': LEFT, 'Right': RIGHT,
    'w': UP, 's': DOWN, 'a': LEFT, 'd': RIGHT,
    'W': UP, 'S': DOWN, 'A': LEFT, 'D': RIGHT,
}


class SlidingPuzzleApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Sliding Tile Puzzle')
        self.configure(fg_color=BG_APP)
        self.minsize(520, 720)

        self.n: int = 4
        self.rng = random.Random()
        self.puzzle = Puzzle(self.n)

        self._tile_ids: dict[int, int] = {}    # value -> canvas rect id
        self._text_ids: dict[int, int] = {}    # value -> canvas text id
        self._anim_running: bool = False
        self._hint_value: int | None = None    # tile to flash for the hint
        self._start_ts: float | None = None
        self._game_over: bool = False
        self._timer_job: str | None = None

        self._build_ui()
        self._new_game()

        # Arrow / wasd keys bound on the toplevel — works no matter who has focus.
        for key in KEY_TO_DIR:
            self.bind(f'<{key}>', self._on_key)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='SLIDING TILE PUZZLE',
                     font=TITLE_FONT, text_color=TILE_FG).pack()
        ctk.CTkLabel(header,
                     text='Click a neighbour of the blank or use arrow keys',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # --- size selector + new game ----------------------------------
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='top', fill='x', padx=20, pady=(6, 4))

        ctk.CTkLabel(controls, text='Size:', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 6))
        self.size_var = tk.StringVar(value=str(self.n))
        self.size_menu = ctk.CTkOptionMenu(
            controls, values=['3', '4', '5'], variable=self.size_var,
            width=70, command=self._on_size_change,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b')
        self.size_menu.pack(side='left', padx=(0, 14))

        self.new_btn = ctk.CTkButton(controls, text='New', width=70,
                                     fg_color='#334155', hover_color='#475569',
                                     command=self._new_game)
        self.new_btn.pack(side='left', padx=(0, 6))
        self.hint_btn = ctk.CTkButton(controls, text='Hint', width=70,
                                      fg_color='#0369a1', hover_color='#0284c7',
                                      command=self._show_hint)
        self.hint_btn.pack(side='left', padx=(0, 6))
        self.solve_btn = ctk.CTkButton(controls, text='Solve', width=70,
                                       fg_color='#7c3aed', hover_color='#8b5cf6',
                                       command=self._auto_solve)
        self.solve_btn.pack(side='left')

        # --- HUD: moves + timer + parity --------------------------------
        hud = ctk.CTkFrame(self, fg_color='transparent')
        hud.pack(side='top', fill='x', padx=20, pady=(4, 6))
        self.move_label = ctk.CTkLabel(hud, text='Moves: 0',
                                       font=LABEL_FONT, text_color=ACCENT)
        self.move_label.pack(side='left')
        self.time_label = ctk.CTkLabel(hud, text='00:00',
                                       font=LABEL_FONT, text_color=MUTED)
        self.time_label.pack(side='left', padx=20)
        self.parity_label = ctk.CTkLabel(hud, text='', font=LABEL_FONT,
                                         text_color=MUTED)
        self.parity_label.pack(side='right')

        # --- board ------------------------------------------------------
        board_frame = ctk.CTkFrame(self, fg_color=BG_BOARD, corner_radius=14)
        board_frame.pack(side='top', padx=20, pady=8)
        # Canvas size depends on n; built lazily.
        self.canvas = tk.Canvas(board_frame, bg=BG_BOARD,
                                highlightthickness=0, bd=0)
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind('<Button-1>', self._on_click)

        # --- status -----------------------------------------------------
        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color=MUTED)
        self.status.pack(side='top', pady=(4, 14))

    # ------------------------------------------------------------------ canvas

    def _canvas_size(self) -> int:
        return self.n * TILE_SIZE + (self.n + 1) * TILE_PAD

    def _cell_xy(self, r: int, c: int) -> tuple[int, int]:
        x = TILE_PAD + c * (TILE_SIZE + TILE_PAD)
        y = TILE_PAD + r * (TILE_SIZE + TILE_PAD)
        return x, y

    def _draw_board(self) -> None:
        self.canvas.delete('all')
        size = self._canvas_size()
        self.canvas.configure(width=size, height=size)
        # Goal slots (faint) — shows where each tile belongs when nearly done.
        for r in range(self.n):
            for c in range(self.n):
                x, y = self._cell_xy(r, c)
                self.canvas.create_rectangle(
                    x, y, x + TILE_SIZE, y + TILE_SIZE,
                    fill=BG_BLANK, outline='')
        # Tiles.
        self._tile_ids.clear()
        self._text_ids.clear()
        for idx, value in enumerate(self.puzzle.state()):
            if value == 0:
                continue
            r, c = divmod(idx, self.n)
            self._spawn_tile(value, r, c)

    def _spawn_tile(self, value: int, r: int, c: int) -> None:
        x, y = self._cell_xy(r, c)
        rect = self.canvas.create_rectangle(
            x, y, x + TILE_SIZE, y + TILE_SIZE,
            fill=TILE_BG, outline=ACCENT, width=2,
        )
        text = self.canvas.create_text(
            x + TILE_SIZE // 2, y + TILE_SIZE // 2,
            text=str(value), fill=TILE_FG, font=TILE_FONT,
        )
        self._tile_ids[value] = rect
        self._text_ids[value] = text

    # ------------------------------------------------------------------ flow

    def _on_size_change(self, value: str) -> None:
        try:
            self.n = int(value)
        except ValueError:
            return
        self._new_game()

    def _new_game(self) -> None:
        self.puzzle = Puzzle(self.n)
        self.puzzle.shuffle(self.rng, moves=_default_shuffle(self.n))
        self._game_over = False
        self._hint_value = None
        self._start_ts = None
        self._cancel_timer()
        self._draw_board()
        self._update_hud()
        self._set_status('Slide tiles into the blank cell.', MUTED)
        # Hint/solve only enabled at sizes A* handles fast.
        for btn in (self.hint_btn, self.solve_btn):
            btn.configure(state='normal' if self.n <= 4 else 'disabled')

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, text_color=color)

    def _update_hud(self) -> None:
        self.move_label.configure(text=f'Moves: {self.puzzle.moves}')
        ok = is_solvable(self.puzzle)
        self.parity_label.configure(
            text=('solvable' if ok else 'unsolvable'),
            text_color=(WIN if ok else ERROR),
        )

    def _start_timer_if_needed(self) -> None:
        if self._start_ts is None and not self._game_over:
            self._start_ts = time.time()
            self._tick_timer()

    def _tick_timer(self) -> None:
        if self._start_ts is None or self._game_over:
            return
        elapsed = int(time.time() - self._start_ts)
        m, s = divmod(elapsed, 60)
        self.time_label.configure(text=f'{m:02d}:{s:02d}')
        self._timer_job = self.after(500, self._tick_timer)

    def _cancel_timer(self) -> None:
        if self._timer_job is not None:
            try:
                self.after_cancel(self._timer_job)
            except Exception:
                pass
            self._timer_job = None
        self.time_label.configure(text='00:00')

    # ------------------------------------------------------------------ input

    def _on_key(self, event: tk.Event) -> None:
        if self._game_over or self._anim_running:
            return
        direction = KEY_TO_DIR.get(event.keysym)
        if direction is None:
            return
        self._try_slide(direction)

    def _on_click(self, event: tk.Event) -> None:
        if self._game_over or self._anim_running:
            return
        # Translate canvas pixel into grid cell.
        c = (event.x - TILE_PAD) // (TILE_SIZE + TILE_PAD)
        r = (event.y - TILE_PAD) // (TILE_SIZE + TILE_PAD)
        if not (0 <= r < self.n and 0 <= c < self.n):
            return
        br, bc = self.puzzle.blank()
        # Determine the direction the BLANK would move so the clicked tile
        # ends up in the blank slot.
        for d, (dr, dc) in DELTAS.items():
            if (br + dr, bc + dc) == (r, c):
                self._try_slide(d)
                return

    # ------------------------------------------------------------------ logic

    def _try_slide(self, direction: str) -> None:
        if not self.puzzle.slide(direction):
            return  # blocked
        self._start_timer_if_needed()
        # `slide(direction)` moved the BLANK by DELTAS[direction]. The tile
        # that swapped with it now sits at the blank's *old* coordinates.
        br_new, bc_new = self.puzzle.blank()
        dr, dc = DELTAS[direction]
        old_blank_r, old_blank_c = br_new - dr, bc_new - dc
        moved_value = self.puzzle.state()[old_blank_r * self.n + old_blank_c]
        # The moved tile slid from (br_new, bc_new) → (old_blank_r, old_blank_c).
        self._animate_tile(moved_value,
                           dst=(old_blank_r, old_blank_c))

    def _animate_tile(self, value: int, dst: tuple[int, int]) -> None:
        # Slides the existing tile from its current canvas coords to the cell
        # at `dst`. The puzzle model has already been updated.
        rect = self._tile_ids[value]
        x0, y0, _x1, _y1 = self.canvas.coords(rect)
        target_x, target_y = self._cell_xy(*dst)
        dx = (target_x - x0) / ANIM_FRAMES
        dy = (target_y - y0) / ANIM_FRAMES
        self._anim_running = True

        def step(i: int) -> None:
            if i >= ANIM_FRAMES:
                # Snap to final to avoid float drift.
                cur_x, cur_y, _, _ = self.canvas.coords(rect)
                self.canvas.move(rect, target_x - cur_x, target_y - cur_y)
                # Move the text to match.
                tx, ty = (target_x + TILE_SIZE // 2, target_y + TILE_SIZE // 2)
                self.canvas.coords(self._text_ids[value], tx, ty)
                self._anim_running = False
                self._after_slide()
                return
            self.canvas.move(rect, dx, dy)
            self.canvas.move(self._text_ids[value], dx, dy)
            self.after(ANIM_DELAY_MS, lambda: step(i + 1))

        step(0)

    def _after_slide(self) -> None:
        self._update_hud()
        # Clear any active hint highlight.
        if self._hint_value is not None and self._hint_value in self._tile_ids:
            self.canvas.itemconfigure(self._tile_ids[self._hint_value],
                                      fill=TILE_BG)
            self._hint_value = None
        if self.puzzle.is_solved():
            self._win()

    def _win(self) -> None:
        self._game_over = True
        # Recolor every tile green.
        for value, rect in self._tile_ids.items():
            self.canvas.itemconfigure(rect, fill=TILE_BG_GOAL)
        elapsed = '—'
        if self._start_ts is not None:
            sec = int(time.time() - self._start_ts)
            m, s = divmod(sec, 60)
            elapsed = f'{m:02d}:{s:02d}'
        self._set_status(
            f'Solved in {self.puzzle.moves} moves ({elapsed}). Press New for another.',
            WIN)

    # ------------------------------------------------------------------ A*

    def _show_hint(self) -> None:
        if self._game_over or self._anim_running:
            return
        nxt = compute_hint(self.puzzle)
        if nxt is None:
            self._set_status('Already solved.', WIN)
            return
        # Compute which tile would move (the one adjacent to the blank in
        # the suggested direction).
        br, bc = self.puzzle.blank()
        dr, dc = DELTAS[nxt]
        tr, tc = br + dr, bc + dc
        idx = tr * self.n + tc
        value = self.puzzle.state()[idx]
        # Highlight that tile briefly.
        if self._hint_value is not None and self._hint_value in self._tile_ids:
            self.canvas.itemconfigure(self._tile_ids[self._hint_value],
                                      fill=TILE_BG)
        if value in self._tile_ids:
            self.canvas.itemconfigure(self._tile_ids[value], fill=TILE_BG_HINT)
        self._hint_value = value
        self._set_status(f'Hint: slide tile {value} ({nxt}).', ACCENT)

    def _auto_solve(self) -> None:
        if self._game_over or self._anim_running:
            return
        from sliding_puzzle import solve as compute_solve
        plan = compute_solve(self.puzzle, max_expansions=1_500_000)
        if not plan:
            self._set_status(
                'Solver budget exhausted — try a fresh shuffle.', ERROR)
            return
        self._set_status(f'Auto-solving in {len(plan)} moves...', ACCENT)
        self._play_plan(plan, 0)

    def _play_plan(self, plan: list[str], i: int) -> None:
        if i >= len(plan):
            return
        if self._game_over:
            return
        # Wait for any in-flight animation, then slide once and recurse.
        if self._anim_running:
            self.after(ANIM_DELAY_MS, lambda: self._play_plan(plan, i))
            return
        self._try_slide(plan[i])
        self.after(ANIM_FRAMES * ANIM_DELAY_MS + 30,
                   lambda: self._play_plan(plan, i + 1))


if __name__ == '__main__':
    SlidingPuzzleApp().mainloop()
