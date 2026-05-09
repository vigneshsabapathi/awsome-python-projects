"""Conway's Game of Life — CustomTkinter GUI.

Dark-theme desktop UI rendering the grid on a tkinter Canvas.

Controls
--------
- Play/Pause (Space)        — start/stop the animation
- Step (N)                  — advance one generation
- Reset                     — re-stamp the current pattern
- Clear                     — wipe the grid
- Pattern dropdown          — Random / Glider / Pulsar / Gosper Gun / Blinker
- Speed slider              — 5..60 fps
- Edges toggle              — toroidal (wrap) vs bounded
- Trail toggle (twist)      — dying cells leave a fading 4-frame trail

Click cells to toggle them on/off. Drag to paint multiple cells.

Run:
    uv run python game_of_life/game_of_life_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import numpy as np

from game_of_life import (
    blinker_grid,
    glider_grid,
    gosper_glider_gun_grid,
    pulsar_grid,
    random_grid,
    step,
)


CELL_SIZE = 14
ROWS = 36
COLS = 64

BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
GRID_BG = '#020617'
GRID_LINE = '#1e293b'
ALIVE = '#34d399'
TRAIL_COLORS = ['#0f5132', '#0c4128', '#08311e', '#052114']  # fade to darker

LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 22, 'bold')
STAT_FONT = ('Consolas', 12)


PATTERN_BUILDERS = {
    'Random': lambda r, c: random_grid(r, c, density=0.28),
    'Glider': glider_grid,
    'Pulsar': pulsar_grid,
    'Gosper Gun': gosper_glider_gun_grid,
    'Blinker': blinker_grid,
}


class GameOfLifeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title("Conway's Game of Life")
        self.configure(fg_color=BG)

        self.rows = ROWS
        self.cols = COLS
        self.grid: np.ndarray = random_grid(self.rows, self.cols, density=0.28)
        self.trail: np.ndarray = np.zeros_like(self.grid, dtype=np.int8)
        self.generation = 0
        self.running = False
        self.fps = 18
        self.toroidal = True
        self.use_trail = True
        self.current_pattern = 'Random'
        self._after_id: str | None = None
        # Cache canvas rectangle item ids per cell — avoids redrawing the
        # whole canvas every tick.
        self._cell_items: list[list[int]] = []

        self._build_ui()
        self._draw_grid_initial()
        self._refresh_canvas()

        self.bind('<space>', lambda _e: self._toggle_play())
        self.bind('<n>', lambda _e: self._single_step())
        self.bind('<N>', lambda _e: self._single_step())

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
        ctk.CTkLabel(header, text="CONWAY'S GAME OF LIFE",
                     font=TITLE_FONT, text_color='#f8fafc').pack(side='left')
        self.stat_label = ctk.CTkLabel(
            header, text='', font=STAT_FONT, text_color='#94a3b8')
        self.stat_label.pack(side='right')

        # Canvas frame
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

        # Controls row 1 — buttons
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
                      command=self._reset_pattern).pack(side='left', padx=4)
        ctk.CTkButton(ctrl1, text='Clear', width=80, height=32,
                      fg_color='#334155', hover_color='#475569',
                      command=self._clear).pack(side='left', padx=4)

        ctk.CTkLabel(ctrl1, text='Pattern:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(16, 4))
        self.pattern_var = ctk.StringVar(value='Random')
        ctk.CTkOptionMenu(
            ctrl1, values=list(PATTERN_BUILDERS),
            variable=self.pattern_var, width=130,
            fg_color='#1e293b', button_color='#334155',
            button_hover_color='#475569', dropdown_fg_color='#1e293b',
            command=self._on_pattern_change).pack(side='left', padx=4)

        # Controls row 2 — speed + toggles
        ctrl2 = ctk.CTkFrame(self, fg_color='transparent')
        ctrl2.pack(side='top', fill='x', padx=18, pady=(2, 12))

        ctk.CTkLabel(ctrl2, text='Speed (fps):', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 6))
        self.speed_label = ctk.CTkLabel(
            ctrl2, text=f'{self.fps}', font=STAT_FONT, width=28,
            text_color='#f8fafc')
        self.speed_label.pack(side='left')
        self.speed_slider = ctk.CTkSlider(
            ctrl2, from_=5, to=60, number_of_steps=55,
            width=180, command=self._on_speed)
        self.speed_slider.set(self.fps)
        self.speed_slider.pack(side='left', padx=(4, 16))

        self.edges_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ctrl2, text='Toroidal edges',
                      variable=self.edges_var,
                      command=self._on_edges_toggle,
                      progress_color='#16a34a').pack(side='left', padx=10)

        self.trail_var = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(ctrl2, text='Trail (fade)',
                      variable=self.trail_var,
                      command=self._on_trail_toggle,
                      progress_color='#0ea5e9').pack(side='left', padx=10)

        ctk.CTkLabel(self,
                     text='Click cells to toggle • Drag to paint • '
                          'Space play • N step',
                     font=('Segoe UI', 11), text_color='#64748b'
                     ).pack(side='top', pady=(0, 12))

    # --- Canvas drawing ----------------------------------------------------

    def _draw_grid_initial(self) -> None:
        """Create one rectangle per cell — we just reconfigure fill later."""
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
                    fill=GRID_BG, outline=GRID_LINE, width=1)
                row_items.append(item)
            self._cell_items.append(row_items)

    def _refresh_canvas(self) -> None:
        canvas = self.canvas
        alive_color = ALIVE
        dead_color = GRID_BG
        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r, c]:
                    fill = alive_color
                elif self.use_trail and self.trail[r, c] > 0:
                    idx = min(int(self.trail[r, c]) - 1, len(TRAIL_COLORS) - 1)
                    fill = TRAIL_COLORS[idx]
                else:
                    fill = dead_color
                canvas.itemconfigure(self._cell_items[r][c], fill=fill)
        self._update_stats()

    def _update_stats(self) -> None:
        alive = int(self.grid.sum())
        edges = 'toroidal' if self.toroidal else 'bounded'
        self.stat_label.configure(
            text=f'gen {self.generation:>5d}  |  alive {alive:>4d}  |  {edges}')

    # --- Simulation loop ---------------------------------------------------

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
        delay = max(int(1000 / self.fps), 16)
        self._after_id = self.after(delay, self._tick)

    def _single_step(self) -> None:
        if self.running:
            return
        self._advance_one()

    def _advance_one(self) -> None:
        prev = self.grid
        self.grid = step(self.grid, toroidal=self.toroidal)
        # Update fade trail: mark cells that just died, decay older trails.
        if self.use_trail:
            died = (prev == 1) & (self.grid == 0)
            self.trail = np.where(self.trail > 0, self.trail - 1, 0).astype(np.int8)
            self.trail[died] = len(TRAIL_COLORS)
        self.generation += 1
        self._refresh_canvas()

    # --- Cell interaction --------------------------------------------------

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
        self.grid[r, c] = 0 if self.grid[r, c] else 1
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
        # Paint alive on drag (don't toggle — predictable for stamping).
        self.grid[r, c] = 1
        self._paint_last = (r, c)
        self._refresh_canvas()

    # --- Control callbacks -------------------------------------------------

    def _on_pattern_change(self, name: str) -> None:
        self.current_pattern = name
        self._reset_pattern()

    def _reset_pattern(self) -> None:
        builder = PATTERN_BUILDERS[self.current_pattern]
        self.grid = builder(self.rows, self.cols).astype(np.uint8)
        self.trail = np.zeros_like(self.grid, dtype=np.int8)
        self.generation = 0
        self._refresh_canvas()

    def _clear(self) -> None:
        self.grid = np.zeros((self.rows, self.cols), dtype=np.uint8)
        self.trail = np.zeros_like(self.grid, dtype=np.int8)
        self.generation = 0
        self._refresh_canvas()

    def _on_speed(self, value: float) -> None:
        self.fps = int(round(value))
        self.speed_label.configure(text=f'{self.fps}')

    def _on_edges_toggle(self) -> None:
        self.toroidal = bool(self.edges_var.get())
        self._update_stats()

    def _on_trail_toggle(self) -> None:
        self.use_trail = bool(self.trail_var.get())
        if not self.use_trail:
            self.trail = np.zeros_like(self.grid, dtype=np.int8)
        self._refresh_canvas()


if __name__ == '__main__':
    GameOfLifeApp().mainloop()
