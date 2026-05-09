"""Drossel-Schwabl Forest Fire — CustomTkinter GUI.

Dark-theme desktop UI rendering the forest on a tk.Canvas:

    - brown  : EMPTY (bare ground)
    - green  : TREE
    - orange : BURNING (just ignited)
    - red    : BURNING (still burning, mostly aesthetic since fires are 1-step)

Controls
--------
- Play/Pause (Space)        — start/stop the simulation
- Step (N)                  — advance one generation
- Reset                     — re-seed a fresh forest with current density
- Clear                     — wipe to bare ground (let it grow back)
- Wind dropdown (twist)     — none / N / S / E / W / Moore (8-neighbor)
- Slider: p_grow            — tree growth rate (0..0.1)
- Slider: p_lightning       — lightning rate (0..0.001)
- Speed slider              — 5..30 fps

Stats bar shows tree count, burning count, and live tree density —
under classic params it self-organizes near ~0.4 (the percolation-ish
critical density for von-Neumann spread).

Click cells to cycle EMPTY -> TREE -> BURNING. Drag to paint trees.

Run:
    uv run python forest_fire/forest_fire_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk
import numpy as np

from forest_fire import (
    BURNING,
    EMPTY,
    NEIGHBOR_OFFSETS,
    TREE,
    empty_grid,
    random_grid,
    step,
)


CELL_SIZE = 16
ROWS = 30
COLS = 60

# Tailwind-ish dark palette + earthy state colors.
BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
GRID_BG = '#1c1917'
GRID_LINE = '#292524'

COLOR_EMPTY = '#78350f'      # warm brown bare ground
COLOR_TREE = '#16a34a'       # forest green
COLOR_BURNING = '#f97316'    # orange flame
COLOR_BURNING_HOT = '#dc2626'  # red — used briefly for newly-ignited cells

LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 22, 'bold')
STAT_FONT = ('Consolas', 12)


class ForestFireApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Drossel-Schwabl Forest Fire')
        self.configure(fg_color=BG)

        self.rows = ROWS
        self.cols = COLS
        self.density_init = 0.55
        self.p_grow = 0.02
        self.p_lightning = 0.0005
        self.fps = 12
        self.wind = 'none'
        self.running = False
        self.generation = 0
        self._after_id: str | None = None

        # Stdlib rng feeds numpy.random.default_rng inside step() — keeps
        # everything seeded deterministically when the user resets.
        self._rng = random.Random()

        self.grid: np.ndarray = random_grid(self.rows, self.cols,
                                            self.density_init)
        # Track which cells just ignited this step — drawn in the brighter
        # red so flame "fronts" pop visually.
        self._just_ignited: np.ndarray = np.zeros_like(self.grid, dtype=bool)

        # Cache canvas rectangle items per cell — reconfigure fill, never redraw.
        self._cell_items: list[list[int]] = []

        self._build_ui()
        self._draw_grid_initial()
        self._refresh_canvas()

        self.bind('<space>', lambda _e: self._toggle_play())
        self.bind('<n>', lambda _e: self._single_step())
        self.bind('<N>', lambda _e: self._single_step())

        # Center on screen.
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')

    # --- UI ---------------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=18, pady=(14, 4))
        ctk.CTkLabel(header, text='DROSSEL-SCHWABL FOREST FIRE',
                     font=TITLE_FONT, text_color='#f8fafc').pack(side='left')
        self.stat_label = ctk.CTkLabel(
            header, text='', font=STAT_FONT, text_color='#94a3b8')
        self.stat_label.pack(side='right')

        canvas_w = self.cols * CELL_SIZE
        canvas_h = self.rows * CELL_SIZE
        canvas_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                    border_width=1, border_color=BORDER)
        canvas_frame.pack(side='top', padx=18, pady=8)
        self.canvas = tk.Canvas(canvas_frame, width=canvas_w, height=canvas_h,
                                bg=GRID_BG, highlightthickness=0, bd=0)
        self.canvas.pack(padx=8, pady=8)
        self.canvas.bind('<Button-1>', self._on_click)
        self.canvas.bind('<B1-Motion>', self._on_drag)

        # Row 1 — buttons + wind
        ctrl1 = ctk.CTkFrame(self, fg_color='transparent')
        ctrl1.pack(side='top', fill='x', padx=18, pady=(8, 4))
        self.play_btn = ctk.CTkButton(
            ctrl1, text='Play (Space)', width=120, height=32,
            fg_color='#16a34a', hover_color='#15803d',
            command=self._toggle_play)
        self.play_btn.pack(side='left', padx=4)
        ctk.CTkButton(ctrl1, text='Step (N)', width=90, height=32,
                      fg_color='#334155', hover_color='#475569',
                      command=self._single_step).pack(side='left', padx=4)
        ctk.CTkButton(ctrl1, text='Reset', width=80, height=32,
                      fg_color='#334155', hover_color='#475569',
                      command=self._reset).pack(side='left', padx=4)
        ctk.CTkButton(ctrl1, text='Clear', width=80, height=32,
                      fg_color='#334155', hover_color='#475569',
                      command=self._clear).pack(side='left', padx=4)

        ctk.CTkLabel(ctrl1, text='Wind:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(16, 4))
        self.wind_var = ctk.StringVar(value='none')
        ctk.CTkOptionMenu(
            ctrl1, values=list(NEIGHBOR_OFFSETS),
            variable=self.wind_var, width=110,
            fg_color='#1e293b', button_color='#334155',
            button_hover_color='#475569', dropdown_fg_color='#1e293b',
            command=self._on_wind_change).pack(side='left', padx=4)

        # Row 2 — sliders for p_grow / p_lightning
        ctrl2 = ctk.CTkFrame(self, fg_color='transparent')
        ctrl2.pack(side='top', fill='x', padx=18, pady=(2, 4))

        ctk.CTkLabel(ctrl2, text='p_grow:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 4))
        self.p_grow_label = ctk.CTkLabel(
            ctrl2, text=f'{self.p_grow:.4f}', font=STAT_FONT, width=60,
            text_color='#f8fafc')
        self.p_grow_label.pack(side='left')
        self.p_grow_slider = ctk.CTkSlider(
            ctrl2, from_=0.0, to=0.1, number_of_steps=200,
            width=180, command=self._on_p_grow)
        self.p_grow_slider.set(self.p_grow)
        self.p_grow_slider.pack(side='left', padx=(4, 16))

        ctk.CTkLabel(ctrl2, text='p_lightning:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 4))
        self.p_lightning_label = ctk.CTkLabel(
            ctrl2, text=f'{self.p_lightning:.5f}', font=STAT_FONT, width=70,
            text_color='#f8fafc')
        self.p_lightning_label.pack(side='left')
        self.p_lightning_slider = ctk.CTkSlider(
            ctrl2, from_=0.0, to=0.001, number_of_steps=200,
            width=180, command=self._on_p_lightning)
        self.p_lightning_slider.set(self.p_lightning)
        self.p_lightning_slider.pack(side='left', padx=4)

        # Row 3 — speed + hint
        ctrl3 = ctk.CTkFrame(self, fg_color='transparent')
        ctrl3.pack(side='top', fill='x', padx=18, pady=(2, 12))

        ctk.CTkLabel(ctrl3, text='Speed (fps):', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 6))
        self.speed_label = ctk.CTkLabel(
            ctrl3, text=f'{self.fps}', font=STAT_FONT, width=28,
            text_color='#f8fafc')
        self.speed_label.pack(side='left')
        self.speed_slider = ctk.CTkSlider(
            ctrl3, from_=2, to=30, number_of_steps=28,
            width=180, command=self._on_speed)
        self.speed_slider.set(self.fps)
        self.speed_slider.pack(side='left', padx=(4, 16))

        ctk.CTkLabel(ctrl3,
                     text='Click cells to ignite/plant • '
                          'Drag to paint trees • Space play • N step',
                     font=('Segoe UI', 11), text_color='#64748b'
                     ).pack(side='left', padx=10)

    # --- Canvas -----------------------------------------------------------

    def _draw_grid_initial(self) -> None:
        self.canvas.delete('all')
        self._cell_items = []
        for r in range(self.rows):
            row_items: list[int] = []
            for c in range(self.cols):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                x1 = x0 + CELL_SIZE
                y1 = y0 + CELL_SIZE
                item = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=COLOR_EMPTY, outline=GRID_LINE, width=1)
                row_items.append(item)
            self._cell_items.append(row_items)

    def _refresh_canvas(self) -> None:
        canvas = self.canvas
        grid = self.grid
        ignited = self._just_ignited
        for r in range(self.rows):
            for c in range(self.cols):
                v = grid[r, c]
                if v == BURNING:
                    fill = COLOR_BURNING_HOT if ignited[r, c] else COLOR_BURNING
                elif v == TREE:
                    fill = COLOR_TREE
                else:
                    fill = COLOR_EMPTY
                canvas.itemconfigure(self._cell_items[r][c], fill=fill)
        self._update_stats()

    def _update_stats(self) -> None:
        trees = int((self.grid == TREE).sum())
        burning = int((self.grid == BURNING).sum())
        density = trees / self.grid.size
        self.stat_label.configure(
            text=(f'gen {self.generation:>5d}  |  '
                  f'trees {trees:>4d}  |  '
                  f'burning {burning:>3d}  |  '
                  f'density {density:.3f}  |  '
                  f'wind {self.wind}'))

    # --- Loop -------------------------------------------------------------

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
        delay = max(int(1000 / self.fps), 33)
        self._after_id = self.after(delay, self._tick)

    def _single_step(self) -> None:
        if self.running:
            return
        self._advance_one()

    def _advance_one(self) -> None:
        prev = self.grid
        self.grid = step(prev, self.p_grow, self.p_lightning, self._rng,
                         wind=self.wind)
        # Cells that became BURNING this step (were TREE before, BURNING now).
        self._just_ignited = (prev == TREE) & (self.grid == BURNING)
        self.generation += 1
        self._refresh_canvas()

    # --- Cell editing -----------------------------------------------------

    def _cell_at(self, x: int, y: int) -> tuple[int, int] | None:
        c = x // CELL_SIZE
        r = y // CELL_SIZE
        if 0 <= r < self.rows and 0 <= c < self.cols:
            return r, c
        return None

    def _on_click(self, event: tk.Event) -> None:
        cell = self._cell_at(event.x, event.y)
        if cell is None:
            return
        r, c = cell
        # Cycle EMPTY -> TREE -> BURNING -> EMPTY.
        v = int(self.grid[r, c])
        nxt = (EMPTY, TREE, BURNING)[(v + 1) % 3]
        self.grid[r, c] = nxt
        self._just_ignited[r, c] = (nxt == BURNING)
        self._paint_last = (r, c)
        self._refresh_canvas()

    def _on_drag(self, event: tk.Event) -> None:
        cell = self._cell_at(event.x, event.y)
        if cell is None:
            return
        r, c = cell
        last = getattr(self, '_paint_last', None)
        if last == (r, c):
            return
        # Drag plants trees — predictable for shaping the forest.
        self.grid[r, c] = TREE
        self._paint_last = (r, c)
        self._refresh_canvas()

    # --- Control callbacks ------------------------------------------------

    def _on_p_grow(self, value: float) -> None:
        self.p_grow = float(value)
        self.p_grow_label.configure(text=f'{self.p_grow:.4f}')

    def _on_p_lightning(self, value: float) -> None:
        self.p_lightning = float(value)
        self.p_lightning_label.configure(text=f'{self.p_lightning:.5f}')

    def _on_speed(self, value: float) -> None:
        self.fps = int(round(value))
        self.speed_label.configure(text=f'{self.fps}')

    def _on_wind_change(self, name: str) -> None:
        self.wind = name
        self._update_stats()

    def _reset(self) -> None:
        self.grid = random_grid(self.rows, self.cols, self.density_init)
        self._just_ignited = np.zeros_like(self.grid, dtype=bool)
        self.generation = 0
        self._refresh_canvas()

    def _clear(self) -> None:
        self.grid = empty_grid(self.rows, self.cols)
        self._just_ignited = np.zeros_like(self.grid, dtype=bool)
        self.generation = 0
        self._refresh_canvas()


if __name__ == '__main__':
    ForestFireApp().mainloop()
