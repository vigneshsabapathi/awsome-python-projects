"""Deep Cave — CustomTkinter GUI.

Dark-theme desktop UI rendering each cave row as colored rectangles on a
tkinter Canvas. Rows scroll downward, simulating a descent past
stalactites and stalagmites.

Controls
--------
- Play/Pause (Space)        — start/stop the descent
- Reseed                    — generate a brand-new cave from a fresh seed
- Speed slider              — 5..120 fps
- Seed entry                — type a number for a reproducible cave

Twist: hazards (gems, water, boulders) appear as colored dots in the floor
and a hint label flashes at the bottom the first time each is sighted.

Run:
    uv run python deep_cave/deep_cave_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from deep_cave import (
    DEFAULT_WIDTH,
    HAZARDS,
    hazard_label,
    initial_tunnel,
    next_row,
)


# Geometry
COLS = DEFAULT_WIDTH
ROWS = 36
CELL_W = 10
CELL_H = 14

CANVAS_W = COLS * CELL_W
CANVAS_H = ROWS * CELL_H

# Tailwind-ish dark cave palette
BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
CAVE_BG = '#1c1917'        # warm near-black "air"
WALL_TOP = '#78350f'        # amber-900 — top tier wall
WALL_MID = '#57340a'        # darker amber
WALL_DARK = '#3b2207'       # darker still — shadow band
FLOOR_BG = '#0c0a09'        # deep cave floor

HAZARD_COLORS = {
    '*': '#fbbf24',  # amber gem
    '~': '#38bdf8',  # sky blue water
    'o': '#a8a29e',  # stone grey boulder
}

LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 22, 'bold')
STAT_FONT = ('Consolas', 12)


class DeepCaveApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Deep Cave')
        self.configure(fg_color=BG)

        self.fps = 24
        self.running = False
        self.depth = 0
        self.seen: set[str] = set()
        self._after_id: str | None = None

        # Use a private RNG so seeding is independent of the global random.
        self.seed_value: int | None = None
        self.rng = random.Random()
        self.left, self.width = initial_tunnel(COLS)

        # Cache canvas item ids per (row, col) so we can recolor cheaply
        # rather than redrawing the whole canvas every tick.
        self._cell_items: list[list[int]] = []
        # Ring buffer of (left, width, hazard_char_or_None) for each row
        # currently on screen — used to repaint after window/canvas events.
        self._row_data: list[tuple[int, int, str | None]] = []

        self._build_ui()
        self._draw_grid_initial()
        self._reset_cave(seed=None)

        self.bind('<space>', lambda _e: self._toggle_play())

        # Center window
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')

    # --- UI construction ---------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=18, pady=(14, 4))
        ctk.CTkLabel(header, text='DEEP CAVE',
                     font=TITLE_FONT, text_color='#f8fafc').pack(side='left')
        self.stat_label = ctk.CTkLabel(
            header, text='', font=STAT_FONT, text_color='#94a3b8')
        self.stat_label.pack(side='right')

        canvas_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                    border_width=1, border_color=BORDER)
        canvas_frame.pack(side='top', padx=18, pady=8)
        self.canvas = tk.Canvas(canvas_frame, width=CANVAS_W, height=CANVAS_H,
                                bg=CAVE_BG, highlightthickness=0, bd=0)
        self.canvas.pack(padx=8, pady=8)

        # Controls row 1 — buttons + seed entry
        ctrl1 = ctk.CTkFrame(self, fg_color='transparent')
        ctrl1.pack(side='top', fill='x', padx=18, pady=(8, 4))
        self.play_btn = ctk.CTkButton(
            ctrl1, text='Play (Space)', width=130, height=32,
            fg_color='#16a34a', hover_color='#15803d',
            command=self._toggle_play)
        self.play_btn.pack(side='left', padx=4)
        ctk.CTkButton(ctrl1, text='Reseed', width=90, height=32,
                      fg_color='#334155', hover_color='#475569',
                      command=self._reseed).pack(side='left', padx=4)

        ctk.CTkLabel(ctrl1, text='Seed:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(16, 4))
        self.seed_entry = ctk.CTkEntry(ctrl1, width=110, height=32,
                                       placeholder_text='random')
        self.seed_entry.pack(side='left', padx=4)
        self.seed_entry.bind('<Return>', lambda _e: self._apply_seed())
        ctk.CTkButton(ctrl1, text='Apply', width=70, height=32,
                      fg_color='#334155', hover_color='#475569',
                      command=self._apply_seed).pack(side='left', padx=4)

        # Controls row 2 — speed slider
        ctrl2 = ctk.CTkFrame(self, fg_color='transparent')
        ctrl2.pack(side='top', fill='x', padx=18, pady=(2, 8))
        ctk.CTkLabel(ctrl2, text='Speed (fps):', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 6))
        self.speed_label = ctk.CTkLabel(
            ctrl2, text=f'{self.fps}', font=STAT_FONT, width=32,
            text_color='#f8fafc')
        self.speed_label.pack(side='left')
        self.speed_slider = ctk.CTkSlider(
            ctrl2, from_=5, to=120, number_of_steps=115,
            width=240, command=self._on_speed)
        self.speed_slider.set(self.fps)
        self.speed_slider.pack(side='left', padx=(4, 16))

        # Hazard hint area (twist) — flashes the first sighting of each.
        self.hint_label = ctk.CTkLabel(
            self, text='', font=('Segoe UI', 12, 'italic'),
            text_color='#fbbf24')
        self.hint_label.pack(side='top', pady=(0, 4))

        ctk.CTkLabel(self,
                     text='Space play/pause • watch for * gems, ~ water, '
                          'o boulders',
                     font=('Segoe UI', 11), text_color='#64748b'
                     ).pack(side='top', pady=(0, 12))

    # --- Canvas drawing ----------------------------------------------------

    def _draw_grid_initial(self) -> None:
        """Pre-create one rectangle per cell — recolor in-place each tick."""
        self.canvas.delete('all')
        self._cell_items = []
        for r in range(ROWS):
            row_items: list[int] = []
            for c in range(COLS):
                x0 = c * CELL_W
                y0 = r * CELL_H
                x1 = x0 + CELL_W
                y1 = y0 + CELL_H
                item = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=FLOOR_BG, outline='', width=0)
                row_items.append(item)
            self._cell_items.append(row_items)

    def _wall_color(self, col: int, left: int, width: int) -> str:
        """Pick a wall shade so the cave looks layered, not flat.

        Columns adjacent to the floor (the cave wall edge) get the brightest
        amber; deeper into the rock face it darkens. This produces a sense of
        depth even though every wall cell is the same character.
        """
        right = left + width
        if col < left:
            dist = left - col - 1
        else:  # col >= right
            dist = col - right
        if dist <= 0:
            return WALL_TOP
        if dist <= 2:
            return WALL_MID
        return WALL_DARK

    def _paint_row(self, r: int, left: int, width: int,
                   hazard: str | None) -> None:
        for c in range(COLS):
            if left <= c < left + width:
                fill = FLOOR_BG
            else:
                fill = self._wall_color(c, left, width)
            self.canvas.itemconfigure(self._cell_items[r][c], fill=fill)
        if hazard is not None:
            # Find the column the hazard occupies (re-derive from row str).
            # We stored only the char, not the slot; pick a stable middle
            # column based on RNG-like deterministic offset.
            slot = left + width // 2
            color = HAZARD_COLORS.get(hazard, '#fbbf24')
            self.canvas.itemconfigure(self._cell_items[r][slot], fill=color)

    def _repaint_all(self) -> None:
        for r, (lf, wd, hz) in enumerate(self._row_data):
            self._paint_row(r, lf, wd, hz)

    # --- Animation loop ----------------------------------------------------

    def _toggle_play(self) -> None:
        self.running = not self.running
        if self.running:
            self.play_btn.configure(text='Pause (Space)',
                                    fg_color='#dc2626',
                                    hover_color='#b91c1c')
            self._tick()
        else:
            self.play_btn.configure(text='Play (Space)',
                                    fg_color='#16a34a',
                                    hover_color='#15803d')
            if self._after_id is not None:
                self.after_cancel(self._after_id)
                self._after_id = None

    def _tick(self) -> None:
        if not self.running:
            return
        self._advance_one()
        delay = max(int(1000 / self.fps), 8)
        self._after_id = self.after(delay, self._tick)

    def _advance_one(self) -> None:
        self.left, self.width, row = next_row(
            self.left, self.width, self.rng, COLS)
        # Detect hazard in the row (we re-scan because next_row places it
        # somewhere internal; for the canvas we just want "is one present?").
        hazard = next((ch for ch in HAZARD_COLORS if ch in row), None)

        # Scroll: drop the top row, append at the bottom.
        if len(self._row_data) >= ROWS:
            self._row_data.pop(0)
        self._row_data.append((self.left, self.width, hazard))

        # Repainting all rows each tick keeps the scroll visually consistent
        # across the whole canvas — and it's cheap (a few thousand cells).
        self._repaint_all()
        self.depth += 1

        if hazard is not None and hazard not in self.seen:
            self.seen.add(hazard)
            label = hazard_label(hazard) or 'something'
            self.hint_label.configure(
                text=f'... you spot {label} at depth {self.depth}.')
            # Auto-dim the hint after a few seconds.
            self.after(3000, lambda: self.hint_label.configure(text=''))

        self._update_stats()

    def _update_stats(self) -> None:
        seed_str = (str(self.seed_value)
                    if self.seed_value is not None else 'random')
        self.stat_label.configure(
            text=f'depth {self.depth:>5d}  |  seed {seed_str}  |  '
                 f'fps {self.fps}')

    # --- Control callbacks -------------------------------------------------

    def _on_speed(self, value: float) -> None:
        self.fps = int(round(value))
        self.speed_label.configure(text=f'{self.fps}')

    def _reseed(self) -> None:
        self.seed_entry.delete(0, 'end')
        self._reset_cave(seed=None)

    def _apply_seed(self) -> None:
        raw = self.seed_entry.get().strip()
        if not raw:
            self._reset_cave(seed=None)
            return
        try:
            seed = int(raw)
        except ValueError:
            # Hash arbitrary text into a stable integer seed.
            seed = abs(hash(raw)) % (2**32)
        self._reset_cave(seed=seed)

    def _reset_cave(self, seed: int | None) -> None:
        self.seed_value = seed
        self.rng = random.Random(seed)
        self.left, self.width = initial_tunnel(COLS)
        self.depth = 0
        self.seen.clear()
        self._row_data.clear()
        self.hint_label.configure(text='')
        # Pre-fill with a few rows so the canvas isn't blank on reset.
        for _ in range(min(ROWS, 8)):
            self.left, self.width, row = next_row(
                self.left, self.width, self.rng, COLS)
            hazard = next((ch for ch in HAZARD_COLORS if ch in row), None)
            self._row_data.append((self.left, self.width, hazard))
        self._repaint_all()
        self._update_stats()


if __name__ == '__main__':
    DeepCaveApp().mainloop()
