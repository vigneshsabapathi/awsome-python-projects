"""Langton's Ant — CustomTkinter GUI.

Dark-theme desktop UI. The grid is rendered on a tkinter Canvas, one
rectangle per cell (created once and recoloured each frame). The ant is
drawn as a coloured triangle pointed in its current direction.

Controls
--------
- Play / Pause              — start / stop the simulation
- Step                      — advance ``speed`` steps
- Reset                     — clear grid, recenter ant, step counter back to 0
- Rule entry                — e.g. "RL" (classic), "RLR", "LLRR", "RRLL"
- Speed slider (1..1000)    — steps per frame; 1 = single-step animation
- Direction buttons         — restart facing Up/Right/Down/Left

Run:
    uv run python langton_ant/langton_ant_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
import numpy as np

from langton_ant import Ant, make_grid


# --- Layout constants -----------------------------------------------------

ROWS = 121
COLS = 161
CELL_SIZE = 6     # pixels per cell on the canvas
TICK_MS = 16      # ~60 fps animation timer

# Tailwind dark palette
BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
GRID_BG = '#020617'
GRID_LINE = '#0f172a'
ANT_COLOR = '#f59e0b'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'

# Per-color cell fills for multi-color rules. Index 0 is the canvas BG
# (transparent); index 1+ cycle through this palette.
COLOR_PALETTE = [
    GRID_BG,      # 0  white / empty
    '#e2e8f0',    # 1
    '#38bdf8',    # 2
    '#f472b6',    # 3
    '#a78bfa',    # 4
    '#34d399',    # 5
    '#facc15',    # 6
    '#fb7185',    # 7
    '#22d3ee',    # 8
]

LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 22, 'bold')
STAT_FONT = ('Consolas', 12)


# --- App ------------------------------------------------------------------

class LangtonAntApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title("Langton's Ant")
        self.configure(fg_color=BG)

        self.rows = ROWS
        self.cols = COLS
        self.rule = 'RL'
        self.start_dir = 0
        self.speed = 50          # steps per frame
        self.running = False
        self._after_id: str | None = None
        # Item ids for grid rectangles + ant marker.
        self._cell_items: list[list[int]] = []
        self._ant_item: int | None = None
        # Painted-cell cache: avoids reconfiguring cells whose colour
        # didn't change. Initialised to all 0s in _draw_grid_initial.
        self._painted: np.ndarray = np.zeros((self.rows, self.cols), dtype=np.uint8)

        self.ant = self._fresh_ant()

        self._build_ui()
        self._draw_grid_initial()
        self._refresh()

        self.bind('<space>', lambda _e: self._toggle_play())
        self.bind('<n>', lambda _e: self._single_step())
        self.bind('<N>', lambda _e: self._single_step())
        self.bind('<r>', lambda _e: self._reset())
        self.bind('<R>', lambda _e: self._reset())

        # Center window
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'+{(sw - w) // 2}+{max(0, (sh - h) // 2)}')

    # --- Helpers ----------------------------------------------------------

    def _fresh_ant(self) -> Ant:
        """Make a new Ant centered on a cleared grid using the current rule."""
        grid = make_grid(self.rows, self.cols)
        return Ant(grid, self.cols // 2, self.rows // 2,
                   direction=self.start_dir, rule=self.rule)

    # --- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=18, pady=(14, 4))
        ctk.CTkLabel(header, text="LANGTON'S ANT",
                     font=TITLE_FONT, text_color=TEXT).pack(side='left')
        self.stat_label = ctk.CTkLabel(
            header, text='', font=STAT_FONT, text_color=MUTED)
        self.stat_label.pack(side='right')

        # Canvas
        canvas_w = self.cols * CELL_SIZE
        canvas_h = self.rows * CELL_SIZE
        canvas_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                    border_width=1, border_color=BORDER)
        canvas_frame.pack(side='top', padx=18, pady=8)
        self.canvas = tk.Canvas(canvas_frame, width=canvas_w, height=canvas_h,
                                bg=GRID_BG, highlightthickness=0, bd=0)
        self.canvas.pack(padx=8, pady=8)

        # Controls row 1 — playback buttons
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
        ctk.CTkButton(ctrl1, text='Reset (R)', width=100, height=32,
                      fg_color='#334155', hover_color='#475569',
                      command=self._reset).pack(side='left', padx=4)

        # Direction buttons
        ctk.CTkLabel(ctrl1, text='Start dir:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(16, 4))
        for label, val in (('U', 0), ('R', 1), ('D', 2), ('L', 3)):
            ctk.CTkButton(
                ctrl1, text=label, width=34, height=32,
                fg_color='#1e293b', hover_color='#475569',
                command=lambda v=val: self._set_dir(v),
            ).pack(side='left', padx=2)

        # Controls row 2 — rule entry + speed slider
        ctrl2 = ctk.CTkFrame(self, fg_color='transparent')
        ctrl2.pack(side='top', fill='x', padx=18, pady=(2, 12))

        ctk.CTkLabel(ctrl2, text='Rule:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(4, 6))
        self.rule_var = ctk.StringVar(value=self.rule)
        self.rule_entry = ctk.CTkEntry(
            ctrl2, width=110, textvariable=self.rule_var,
            fg_color='#0f172a', text_color=TEXT,
            border_color=BORDER, border_width=1)
        self.rule_entry.pack(side='left', padx=(0, 4))
        self.rule_entry.bind('<Return>', lambda _e: self._apply_rule())
        ctk.CTkButton(ctrl2, text='Apply', width=70, height=28,
                      fg_color='#0ea5e9', hover_color='#0284c7',
                      command=self._apply_rule).pack(side='left', padx=4)

        ctk.CTkLabel(ctrl2, text='Speed (steps/frame):', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(16, 6))
        self.speed_label = ctk.CTkLabel(
            ctrl2, text=f'{self.speed:>4d}', font=STAT_FONT, width=46,
            text_color=TEXT)
        self.speed_label.pack(side='left')
        self.speed_slider = ctk.CTkSlider(
            ctrl2, from_=1, to=1000, number_of_steps=999,
            width=220, command=self._on_speed)
        self.speed_slider.set(self.speed)
        self.speed_slider.pack(side='left', padx=(4, 16))

        ctk.CTkLabel(self,
                     text='Try rules: RL (classic) • RLR • LLRR • RRLL • LRRRRRLLR',
                     font=('Segoe UI', 11), text_color='#64748b'
                     ).pack(side='top', pady=(0, 12))

    # --- Canvas drawing ---------------------------------------------------

    def _draw_grid_initial(self) -> None:
        """Allocate one rectangle per cell + the ant marker."""
        self.canvas.delete('all')
        self._cell_items = []
        for r in range(self.rows):
            row_items: list[int] = []
            y0 = r * CELL_SIZE
            y1 = y0 + CELL_SIZE
            for c in range(self.cols):
                x0 = c * CELL_SIZE
                x1 = x0 + CELL_SIZE
                # Outline only on larger cells — keeps small cells crisp.
                outline = GRID_LINE if CELL_SIZE >= 8 else ''
                item = self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    fill=GRID_BG, outline=outline, width=1)
                row_items.append(item)
            self._cell_items.append(row_items)
        self._painted = np.zeros((self.rows, self.cols), dtype=np.uint8)
        # Ant marker — drawn last so it sits on top.
        self._ant_item = self.canvas.create_polygon(
            0, 0, 0, 0, 0, 0, fill=ANT_COLOR, outline='')
        self._update_ant_marker()

    def _refresh(self) -> None:
        """Repaint cells whose colour changed, then move the ant marker."""
        grid = self.ant.grid
        # Differential repaint: only cells whose colour index changed.
        changed = grid != self._painted
        if changed.any():
            ys, xs = np.nonzero(changed)
            for y, x in zip(ys.tolist(), xs.tolist()):
                idx = int(grid[y, x]) % len(COLOR_PALETTE)
                self.canvas.itemconfigure(
                    self._cell_items[y][x], fill=COLOR_PALETTE[idx])
            self._painted = grid.copy()
        self._update_ant_marker()
        self._update_stats()

    def _update_ant_marker(self) -> None:
        """Position the triangular ant on top of its current cell."""
        if self._ant_item is None:
            return
        x = self.ant.x * CELL_SIZE
        y = self.ant.y * CELL_SIZE
        s = CELL_SIZE
        # Triangle pointing in direction (0=Up,1=Right,2=Down,3=Left).
        if self.ant.direction == 0:    # Up
            pts = (x + s / 2, y, x, y + s, x + s, y + s)
        elif self.ant.direction == 1:  # Right
            pts = (x + s, y + s / 2, x, y, x, y + s)
        elif self.ant.direction == 2:  # Down
            pts = (x + s / 2, y + s, x, y, x + s, y)
        else:                          # Left
            pts = (x, y + s / 2, x + s, y, x + s, y + s)
        self.canvas.coords(self._ant_item, *pts)
        # Lift to top of stacking order.
        self.canvas.tag_raise(self._ant_item)

    def _update_stats(self) -> None:
        s = self.ant.state()
        non_white = int((self.ant.grid > 0).sum())
        dir_letter = 'URDL'[s['direction']]
        alive = 'live' if s['alive'] else 'OFF-GRID'
        self.stat_label.configure(
            text=(f"step {s['steps']:>7d}  |  pos ({s['x']},{s['y']}) {dir_letter}"
                  f"  |  rule {s['rule']}  |  filled {non_white:>5d}  |  {alive}"))

    # --- Simulation loop --------------------------------------------------

    def _toggle_play(self) -> None:
        if not self.ant.alive:
            return
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
        for _ in range(self.speed):
            if not self.ant.alive:
                self.running = False
                self.play_btn.configure(text='Play (Space)',
                                        fg_color='#16a34a',
                                        hover_color='#15803d')
                break
            self.ant.step()
        self._refresh()
        if self.running:
            self._after_id = self.after(TICK_MS, self._tick)

    def _single_step(self) -> None:
        if self.running or not self.ant.alive:
            return
        for _ in range(self.speed):
            if not self.ant.alive:
                break
            self.ant.step()
        self._refresh()

    # --- Control callbacks ------------------------------------------------

    def _on_speed(self, value: float) -> None:
        self.speed = max(1, int(round(value)))
        self.speed_label.configure(text=f'{self.speed:>4d}')

    def _apply_rule(self) -> None:
        rule = self.rule_var.get().strip().upper()
        try:
            # Build a probe ant with the candidate rule to validate it.
            test_ant = Ant(make_grid(2, 2), 0, 0, 0, rule=rule)
            self.rule = test_ant.rule
        except ValueError as exc:
            self.rule_var.set(self.rule)
            self.stat_label.configure(text=f'invalid rule: {exc}')
            return
        self._reset()

    def _set_dir(self, direction: int) -> None:
        self.start_dir = direction
        self._reset()

    def _reset(self) -> None:
        if self.running:
            self._toggle_play()
        self.ant = self._fresh_ant()
        # Force full repaint by zeroing the painted cache.
        self._painted = np.full((self.rows, self.cols), 255, dtype=np.uint8)
        self._refresh()


if __name__ == '__main__':
    LangtonAntApp().mainloop()
