"""2048 — CustomTkinter desktop GUI.

A polished dark-themed window over a tk.Canvas. Each tile is a rounded
square with the classic 2048 colour palette; tiles *slide* to their new
positions with a short animation, then merged tiles do a quick "pop"
scale on top. The score panel shows current score, the all-time best
score persisted to JSON, the move counter, and an undo stack. An AI
button plays one expectimax move at a time.

Run:
    uv run python twenty_forty_eight/twenty_forty_eight_gui.py
"""
from __future__ import annotations

import json
import random
import tkinter as tk
from pathlib import Path

import customtkinter as ctk

from twenty_forty_eight import (
    DIRECTIONS,
    DOWN,
    GRID_SIZE,
    LEFT,
    RIGHT,
    UP,
    Game,
    _slide,
    expectimax_best_move,
)

# ---- chrome palette ----------------------------------------------------------
BG_APP = '#0f172a'
BG_BOARD = '#1e293b'
BG_EMPTY = '#0b1220'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
WIN_COLOR = '#34d399'
ERROR = '#f87171'

# ---- classic 2048 tile palette ----------------------------------------------
# Background colour for each tile value, plus the text colour. Values above
# 2048 fall back to the 2048 style (gold/dark-text) — the palette only
# stretches so far in the original game too.
TILE_COLORS: dict[int, tuple[str, str]] = {
    2:    ('#eee4da', '#776e65'),
    4:    ('#ede0c8', '#776e65'),
    8:    ('#f2b179', '#f9f6f2'),
    16:   ('#f59563', '#f9f6f2'),
    32:   ('#f67c5f', '#f9f6f2'),
    64:   ('#f65e3b', '#f9f6f2'),
    128:  ('#edcf72', '#f9f6f2'),
    256:  ('#edcc61', '#f9f6f2'),
    512:  ('#edc850', '#f9f6f2'),
    1024: ('#edc53f', '#f9f6f2'),
    2048: ('#edc22e', '#f9f6f2'),
}
TILE_FALLBACK = ('#3c3a32', '#f9f6f2')


def _tile_colors(value: int) -> tuple[str, str]:
    return TILE_COLORS.get(value, TILE_FALLBACK)


# ---- layout constants -------------------------------------------------------
TILE_SIZE = 96
TILE_PAD = 10
ANIM_FRAMES = 8
ANIM_DELAY_MS = 14
POP_FRAMES = 4

TITLE_FONT = ('Segoe UI', 30, 'bold')
LABEL_FONT = ('Segoe UI', 13)
HUD_FONT = ('Segoe UI', 14, 'bold')

KEY_TO_DIR = {
    'Up': UP, 'Down': DOWN, 'Left': LEFT, 'Right': RIGHT,
    'w': UP, 's': DOWN, 'a': LEFT, 'd': RIGHT,
    'W': UP, 'S': DOWN, 'A': LEFT, 'D': RIGHT,
}


def _best_score_path() -> Path:
    return Path(__file__).resolve().parent / 'best_score.json'


def load_best_score() -> int:
    path = _best_score_path()
    try:
        return int(json.loads(path.read_text())['best'])
    except Exception:
        return 0


def save_best_score(value: int) -> None:
    try:
        _best_score_path().write_text(json.dumps({'best': int(value)}))
    except Exception:
        pass  # Persistence is a nice-to-have, never crash on it.


class TwentyFortyEightApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('2048')
        self.configure(fg_color=BG_APP)
        self.minsize(560, 760)

        self.size = GRID_SIZE
        self.rng = random.Random()
        self.game = Game(self.rng, self.size)

        # Per-tile bookkeeping. We track *cells*, not tile identities —
        # 2048 spawns and merges constantly, so we draw the canvas from
        # scratch on each move and use animation only as a transition layer.
        self.canvas: tk.Canvas | None = None
        self._anim_jobs: list[str] = []
        self._anim_running = False

        # Undo stack — bounded so memory stays predictable in long games.
        self.history: list[dict] = []
        self.UNDO_LIMIT = 50

        self.best_score = load_best_score()
        self._game_over = False
        self._won_announced = False

        self._build_ui()
        self._draw_board()
        self._refresh_hud()

        for key in KEY_TO_DIR:
            self.bind(f'<{key}>', self._on_key)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='2048', font=TITLE_FONT,
                     text_color=TEXT).pack(side='left')
        ctk.CTkLabel(header,
                     text='Slide matching tiles together. Reach 2048.',
                     font=LABEL_FONT, text_color=MUTED).pack(side='left',
                                                             padx=14, pady=(12, 0))

        # ---- HUD: score chips ---------------------------------------------
        hud = ctk.CTkFrame(self, fg_color='transparent')
        hud.pack(side='top', fill='x', padx=20, pady=(4, 6))
        self.score_chip = self._chip(hud, 'SCORE', '0')
        self.score_chip.pack(side='left', padx=(0, 8))
        self.best_chip = self._chip(hud, 'BEST', f'{self.best_score}')
        self.best_chip.pack(side='left', padx=(0, 8))
        self.moves_chip = self._chip(hud, 'MOVES', '0')
        self.moves_chip.pack(side='left')
        self.max_chip = self._chip(hud, 'MAX', '0')
        self.max_chip.pack(side='right')

        # ---- buttons ------------------------------------------------------
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='top', fill='x', padx=20, pady=(4, 6))
        self.new_btn = ctk.CTkButton(controls, text='New', width=80,
                                     fg_color='#334155', hover_color='#475569',
                                     command=self._new_game)
        self.new_btn.pack(side='left', padx=(0, 6))
        self.undo_btn = ctk.CTkButton(controls, text='Undo', width=80,
                                      fg_color='#334155', hover_color='#475569',
                                      command=self._undo)
        self.undo_btn.pack(side='left', padx=(0, 6))
        self.ai_btn = ctk.CTkButton(controls, text='AI move', width=90,
                                    fg_color='#7c3aed', hover_color='#8b5cf6',
                                    command=self._ai_move)
        self.ai_btn.pack(side='left', padx=(0, 6))
        self.auto_btn = ctk.CTkButton(controls, text='Auto play', width=100,
                                      fg_color='#0369a1', hover_color='#0284c7',
                                      command=self._toggle_auto)
        self.auto_btn.pack(side='left')

        # ---- board canvas -------------------------------------------------
        board_frame = ctk.CTkFrame(self, fg_color=BG_BOARD, corner_radius=14)
        board_frame.pack(side='top', padx=20, pady=10)
        canvas_size = self._canvas_size()
        self.canvas = tk.Canvas(board_frame, bg=BG_BOARD,
                                width=canvas_size, height=canvas_size,
                                highlightthickness=0, bd=0)
        self.canvas.pack(padx=10, pady=10)

        # ---- status -------------------------------------------------------
        self.status = ctk.CTkLabel(self, text='Use arrow keys or WASD to move.',
                                   font=LABEL_FONT, text_color=MUTED)
        self.status.pack(side='top', pady=(2, 14))

        self._auto_job: str | None = None

    def _chip(self, parent: tk.Widget, label: str, value: str) -> ctk.CTkFrame:
        chip = ctk.CTkFrame(parent, fg_color='#1e293b', corner_radius=8)
        ctk.CTkLabel(chip, text=label, font=LABEL_FONT,
                     text_color=MUTED).pack(padx=10, pady=(4, 0))
        # The numeric value is exposed via .value_label so HUD updates can
        # rewrite the text without rebuilding the chip.
        chip.value_label = ctk.CTkLabel(chip, text=value, font=HUD_FONT,
                                        text_color=TEXT)
        chip.value_label.pack(padx=10, pady=(0, 4))
        return chip

    # ------------------------------------------------------------------ canvas

    def _canvas_size(self) -> int:
        return self.size * TILE_SIZE + (self.size + 1) * TILE_PAD

    def _cell_xy(self, r: int, c: int) -> tuple[int, int]:
        x = TILE_PAD + c * (TILE_SIZE + TILE_PAD)
        y = TILE_PAD + r * (TILE_SIZE + TILE_PAD)
        return x, y

    def _tile_font(self, value: int) -> tuple[str, int, str]:
        if value < 100:
            return ('Segoe UI', 32, 'bold')
        if value < 1000:
            return ('Segoe UI', 26, 'bold')
        if value < 10000:
            return ('Segoe UI', 22, 'bold')
        return ('Segoe UI', 18, 'bold')

    def _draw_board(self) -> None:
        assert self.canvas is not None
        c = self.canvas
        c.delete('all')
        # Empty cell backgrounds — drawn first so tiles overlay them.
        for r in range(self.size):
            for col in range(self.size):
                x, y = self._cell_xy(r, col)
                c.create_rectangle(x, y, x + TILE_SIZE, y + TILE_SIZE,
                                   fill=BG_EMPTY, outline='')
        # Tiles.
        for r in range(self.size):
            for col in range(self.size):
                v = self.game.grid[r][col]
                if v == 0:
                    continue
                self._draw_tile(r, col, v)

    def _draw_tile(self, r: int, c: int, value: int,
                   override_xy: tuple[int, int] | None = None) -> tuple[int, int]:
        assert self.canvas is not None
        bg, fg = _tile_colors(value)
        x, y = override_xy if override_xy is not None else self._cell_xy(r, c)
        rect = self.canvas.create_rectangle(
            x, y, x + TILE_SIZE, y + TILE_SIZE,
            fill=bg, outline='', tags='tile')
        text = self.canvas.create_text(
            x + TILE_SIZE // 2, y + TILE_SIZE // 2,
            text=str(value), fill=fg,
            font=self._tile_font(value), tags='tile')
        return rect, text

    # ------------------------------------------------------------------ HUD

    def _refresh_hud(self) -> None:
        self.score_chip.value_label.configure(text=str(self.game.score))
        self.best_chip.value_label.configure(text=str(self.best_score))
        self.moves_chip.value_label.configure(text=str(self.game.moves))
        self.max_chip.value_label.configure(text=str(self.game.max_tile()))
        self.undo_btn.configure(state='normal' if self.history else 'disabled')

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, text_color=color)

    # ------------------------------------------------------------------ flow

    def _new_game(self) -> None:
        self._cancel_auto()
        self.game = Game(self.rng, self.size)
        self.history.clear()
        self._game_over = False
        self._won_announced = False
        self._draw_board()
        self._refresh_hud()
        self._set_status('Use arrow keys or WASD to move.', MUTED)

    def _snapshot(self) -> dict:
        return {
            'grid': [row[:] for row in self.game.grid],
            'score': self.game.score,
            'moves': self.game.moves,
        }

    def _restore(self, snap: dict) -> None:
        self.game.grid = [row[:] for row in snap['grid']]
        self.game.score = snap['score']
        self.game.moves = snap['moves']

    def _undo(self) -> None:
        if self._anim_running:
            return
        if not self.history:
            return
        self._cancel_auto()
        self._restore(self.history.pop())
        self._game_over = False
        self._draw_board()
        self._refresh_hud()
        self._set_status('Undid one move.', ACCENT)

    # ------------------------------------------------------------------ input

    def _on_key(self, event: tk.Event) -> None:
        if self._anim_running or self._game_over:
            return
        direction = KEY_TO_DIR.get(event.keysym)
        if direction is None:
            return
        self._play_move(direction)

    def _play_move(self, direction: str) -> None:
        # Compute pre-move state so we can animate from old positions to new.
        prev_grid = [row[:] for row in self.game.grid]
        new_grid, score_delta, merges = _slide(prev_grid, direction)
        if new_grid == prev_grid:
            return  # no-op, don't waste an undo slot

        self.history.append(self._snapshot())
        if len(self.history) > self.UNDO_LIMIT:
            self.history.pop(0)

        result = self.game.move(direction)
        # Best-score persistence — only write when it actually improves.
        if self.game.score > self.best_score:
            self.best_score = self.game.score
            save_best_score(self.best_score)

        self._animate_transition(prev_grid, self.game.grid, result['spawned'])
        self._refresh_hud()

        if result['score_delta']:
            self._set_status(f'+{result["score_delta"]}', WIN_COLOR)

        if self.game.is_won() and not self._won_announced:
            self._won_announced = True
            self._set_status('You reached 2048! Keep going.', WIN_COLOR)
        if self.game.is_lost():
            self._game_over = True
            self._cancel_auto()
            self._set_status('Game over — no legal moves. Press New.', ERROR)

    # ------------------------------------------------------------------ anim

    def _animate_transition(self,
                            old_grid: list[list[int]],
                            new_grid: list[list[int]],
                            spawned: tuple[int, int, int] | None) -> None:
        """Move tiles from `old_grid` cells to their final positions in
        `new_grid`, then redraw cleanly.

        We don't try to track individual tile identities across merges (the
        original game's animations don't either — merged tiles "fade" into
        the destination). Instead we slide each old non-zero tile toward
        its mapped destination and snap-redraw the final board on completion.
        """
        assert self.canvas is not None
        # Wipe and re-stage so animation can run on a clean canvas.
        self.canvas.delete('all')
        # Empty cell backgrounds (always drawn).
        for r in range(self.size):
            for col in range(self.size):
                x, y = self._cell_xy(r, col)
                self.canvas.create_rectangle(
                    x, y, x + TILE_SIZE, y + TILE_SIZE,
                    fill=BG_EMPTY, outline='')

        # Build per-row mapping from old positions to new positions, in the
        # same orientation as the slide. We re-run the row mechanic by hand
        # to know where each tile ended up.
        moves: list[tuple[tuple[int, int], tuple[int, int], int]] = []
        for entry in self._compute_movements(old_grid, new_grid):
            moves.append(entry)

        # Draw a tile at each *origin* and animate to *destination*.
        anim_tiles: list[tuple[int, int, tuple[int, int], tuple[int, int]]] = []
        for (sr, sc), (dr, dc), value in moves:
            sx, sy = self._cell_xy(sr, sc)
            dx, dy = self._cell_xy(dr, dc)
            rect, text = self._draw_tile(sr, sc, value, override_xy=(sx, sy))
            anim_tiles.append((rect, text, (sx, sy), (dx, dy)))

        self._anim_running = True

        def step(i: int) -> None:
            if i >= ANIM_FRAMES:
                # Final redraw locks the canvas to the true new state and
                # paints the spawn tile (if any).
                self._draw_board()
                if spawned is not None:
                    self._spawn_pop(*spawned)
                else:
                    self._anim_running = False
                return
            t = (i + 1) / ANIM_FRAMES
            for rect, text, (sx, sy), (dx, dy) in anim_tiles:
                # Linear interpolation; cheap and looks fine at 8 frames.
                cur_x = sx + (dx - sx) * t
                cur_y = sy + (dy - sy) * t
                # Move rect to absolute coords.
                rx, ry, rx2, ry2 = self.canvas.coords(rect)
                self.canvas.move(rect, cur_x - rx, cur_y - ry)
                tx, ty = self.canvas.coords(text)
                self.canvas.coords(text,
                                   cur_x + TILE_SIZE // 2,
                                   cur_y + TILE_SIZE // 2)
            job = self.canvas.after(ANIM_DELAY_MS, lambda: step(i + 1))
            self._anim_jobs.append(job)

        step(0)

    def _compute_movements(self,
                            old_grid: list[list[int]],
                            new_grid: list[list[int]]
                            ) -> list[tuple[tuple[int, int],
                                            tuple[int, int], int]]:
        """Best-effort old-cell -> new-cell mapping for animation.

        Compute the canonical "slide left" movements per row in the
        oriented frame and rotate them back. Two old tiles that merged
        share the *same* destination — and the animation just slides
        them both there, then the post-anim redraw paints the merged
        tile on top.
        """
        # Mirror the orientation logic in `_slide`.
        if not new_grid:
            return []

        def orient(grid: list[list[int]], direction: str) -> list[list[int]]:
            if direction == LEFT:
                return [row[:] for row in grid]
            if direction == RIGHT:
                return [list(reversed(row)) for row in grid]
            if direction == UP:
                n = len(grid)
                return [[grid[r][c] for r in range(n)] for c in range(n)]
            # DOWN
            n = len(grid)
            return [[grid[n - 1 - r][c] for r in range(n)] for c in range(n)]

        # Use the same frame as `_slide` — but we just need the movements,
        # which we can derive by tracing where each non-zero column ends up
        # in a fresh "compress left" run.
        # To keep things simple and correct, we compute movements only for
        # the LEFT case using a fresh trace, then transform indices back.

        # Determine direction by trying all four and picking the one whose
        # new_grid matches.
        for direction in DIRECTIONS:
            slid, _, _ = _slide(old_grid, direction)
            if slid == new_grid:
                break
        else:
            return []

        n = self.size

        def map_idx(direction: str, r: int, c: int) -> tuple[int, int]:
            if direction == LEFT:
                return r, c
            if direction == RIGHT:
                return r, n - 1 - c
            if direction == UP:
                return c, r
            return n - 1 - c, r

        oriented_old = orient(old_grid, direction)
        moves: list[tuple[tuple[int, int], tuple[int, int], int]] = []
        for r, row in enumerate(oriented_old):
            # Trace the compress-left exactly so we know where each non-zero
            # input position ends up.
            write = 0
            merged = [False] * n
            slots: list[int] = [0] * n
            for c, v in enumerate(row):
                if v == 0:
                    continue
                if write > 0 and slots[write - 1] == v and not merged[write - 1]:
                    slots[write - 1] = v * 2
                    merged[write - 1] = True
                    dst = write - 1
                else:
                    slots[write] = v
                    dst = write
                    write += 1
                src_idx = map_idx(direction, r, c)
                dst_idx = map_idx(direction, r, dst)
                moves.append((src_idx, dst_idx, v))
        return moves

    def _spawn_pop(self, r: int, c: int, value: int) -> None:
        """Quick pop-in scale on the spawn tile, then unlock animation."""
        assert self.canvas is not None
        bg, fg = _tile_colors(value)
        x, y = self._cell_xy(r, c)
        cx = x + TILE_SIZE / 2
        cy = y + TILE_SIZE / 2

        rect = self.canvas.create_rectangle(
            cx, cy, cx, cy, fill=bg, outline='', tags='popup')
        text = self.canvas.create_text(cx, cy, text=str(value),
                                       fill=fg,
                                       font=self._tile_font(value),
                                       tags='popup')

        def step(i: int) -> None:
            if i >= POP_FRAMES:
                self.canvas.delete(rect)
                self.canvas.delete(text)
                # Final redraw to lock state.
                self._draw_board()
                self._anim_running = False
                return
            half = TILE_SIZE / 2 * ((i + 1) / POP_FRAMES)
            self.canvas.coords(rect, cx - half, cy - half,
                               cx + half, cy + half)
            self.canvas.tag_raise(text)
            self.canvas.after(ANIM_DELAY_MS, lambda: step(i + 1))

        step(0)

    # ------------------------------------------------------------------ AI

    def _ai_move(self) -> None:
        if self._anim_running or self._game_over:
            return
        direction = expectimax_best_move(self.game, depth=3)
        if direction is None:
            self._set_status('AI: no legal move.', ERROR)
            return
        self._play_move(direction)
        self._set_status(f'AI played {direction}.', ACCENT)

    def _toggle_auto(self) -> None:
        if self._auto_job is not None:
            self._cancel_auto()
            return
        self.auto_btn.configure(text='Stop')
        self._schedule_auto()

    def _schedule_auto(self) -> None:
        if self._game_over:
            self._cancel_auto()
            return
        if self._anim_running:
            self._auto_job = self.after(40, self._schedule_auto)
            return
        direction = expectimax_best_move(self.game, depth=3)
        if direction is None:
            self._cancel_auto()
            return
        self._play_move(direction)
        # 180ms beat — fast enough to feel agentic, slow enough to follow.
        self._auto_job = self.after(180, self._schedule_auto)

    def _cancel_auto(self) -> None:
        if self._auto_job is not None:
            try:
                self.after_cancel(self._auto_job)
            except Exception:
                pass
            self._auto_job = None
        self.auto_btn.configure(text='Auto play')


if __name__ == '__main__':
    TwentyFortyEightApp().mainloop()
