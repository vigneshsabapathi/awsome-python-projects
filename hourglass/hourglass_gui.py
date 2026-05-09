"""Hourglass — CustomTkinter GUI.

Animated golden sand on a dark glass canvas. Buttons let you flip the
hourglass, pause/resume the animation, reset, or trigger an earthquake
that scatters the bottom pile. A speed slider controls the frame rate.

Run:
    uv run python hourglass/hourglass_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from hourglass import DEFAULT_WIDTH, Hourglass

# --- visual constants ---------------------------------------------------

CELL_PX = 22                 # pixel size of each grid cell
CELL_PAD = 2                 # gap between sand grains
GLASS_BG = '#0f172a'         # deep navy backdrop
PANEL_BG = '#111827'         # surrounding panel
WALL_COLOR = '#94a3b8'       # silver glass outline
FRAME_COLOR = '#cbd5e1'      # top/bottom caps
NECK_HIGHLIGHT = '#64748b'

# Golden palette: index by (age // bucket) % len.
SAND_PALETTE = (
    '#fde68a',  # pale honey
    '#fcd34d',
    '#fbbf24',
    '#f59e0b',
    '#d97706',
)

TITLE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 13)
BUTTON_FONT = ('Segoe UI', 13, 'bold')
STAT_FONT = ('Segoe UI', 13)


class HourglassApp(ctk.CTk):
    def __init__(self, width: int = DEFAULT_WIDTH) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Hourglass')
        self.configure(fg_color=PANEL_BG)
        self.minsize(560, 720)

        self.hourglass = Hourglass(width=width)
        self.paused: bool = False
        self.fps: float = 12.0
        self.canvas_width = (self.hourglass.width + 2) * CELL_PX
        self.canvas_height = (self.hourglass.rows + 2) * CELL_PX

        self._build_ui()
        self._draw_glass()
        self._draw_sand()
        self._tick()

    # -- layout ---------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='HOURGLASS', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header,
                     text='One grain per frame — flip when drained',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Bottom panel: controls.
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='bottom', pady=(8, 14), padx=20, fill='x')

        btn_row = ctk.CTkFrame(controls, fg_color='transparent')
        btn_row.pack(fill='x')

        self.flip_btn = ctk.CTkButton(btn_row, text='Flip',
                                      font=BUTTON_FONT,
                                      fg_color='#d97706',
                                      hover_color='#b45309',
                                      command=self._on_flip)
        self.flip_btn.pack(side='left', padx=4, expand=True, fill='x')

        self.pause_btn = ctk.CTkButton(btn_row, text='Pause',
                                       font=BUTTON_FONT,
                                       fg_color='#334155',
                                       hover_color='#475569',
                                       command=self._on_pause)
        self.pause_btn.pack(side='left', padx=4, expand=True, fill='x')

        self.reset_btn = ctk.CTkButton(btn_row, text='Reset',
                                       font=BUTTON_FONT,
                                       fg_color='#334155',
                                       hover_color='#475569',
                                       command=self._on_reset)
        self.reset_btn.pack(side='left', padx=4, expand=True, fill='x')

        self.shake_btn = ctk.CTkButton(btn_row, text='Earthquake',
                                       font=BUTTON_FONT,
                                       fg_color='#7c2d12',
                                       hover_color='#9a3412',
                                       command=self._on_shake)
        self.shake_btn.pack(side='left', padx=4, expand=True, fill='x')

        speed_row = ctk.CTkFrame(controls, fg_color='transparent')
        speed_row.pack(fill='x', pady=(10, 0))
        ctk.CTkLabel(speed_row, text='Speed', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(2, 8))
        self.speed = ctk.CTkSlider(speed_row, from_=2, to=60,
                                   number_of_steps=58,
                                   command=self._on_speed)
        self.speed.set(self.fps)
        self.speed.pack(side='left', fill='x', expand=True)
        self.speed_label = ctk.CTkLabel(speed_row,
                                        text=f'{int(self.fps)} fps',
                                        font=LABEL_FONT,
                                        text_color='#94a3b8',
                                        width=64)
        self.speed_label.pack(side='left', padx=(8, 0))

        self.stat = ctk.CTkLabel(controls, text='', font=STAT_FONT,
                                 text_color='#cbd5e1')
        self.stat.pack(pady=(8, 0))

        # Middle: the canvas. Pack last so it fills remaining space.
        canvas_holder = ctk.CTkFrame(self, fg_color=GLASS_BG,
                                     corner_radius=12)
        canvas_holder.pack(side='top', pady=10, padx=20, fill='both',
                           expand=True)
        # tk.Canvas works inside the holder.
        import tkinter as tk
        self.canvas = tk.Canvas(canvas_holder,
                                width=self.canvas_width,
                                height=self.canvas_height,
                                bg=GLASS_BG, highlightthickness=0,
                                bd=0)
        self.canvas.pack(pady=12)

    # -- glass outline (drawn once) -----------------------------------

    def _cell_xy(self, r: int, c: int) -> tuple[int, int, int, int]:
        # Interior cells are offset by 1 column for the left wall and 1
        # row for the top frame.
        x0 = (c + 1) * CELL_PX
        y0 = (r + 1) * CELL_PX
        return x0, y0, x0 + CELL_PX, y0 + CELL_PX

    def _draw_glass(self) -> None:
        c = self.canvas
        c.delete('glass')
        h = self.hourglass
        W = h.width

        # Outer rectangle (cap top + bottom).
        top_y = CELL_PX
        bot_y = (h.rows + 1) * CELL_PX
        left_x = CELL_PX
        right_x = (W + 1) * CELL_PX

        # Top cap.
        c.create_rectangle(0, 0,
                           self.canvas_width, top_y,
                           fill=FRAME_COLOR, outline='', tags='glass')
        # Bottom cap.
        c.create_rectangle(0, bot_y,
                           self.canvas_width, self.canvas_height,
                           fill=FRAME_COLOR, outline='', tags='glass')
        # Vertical glass walls.
        c.create_line(left_x, top_y, left_x, bot_y,
                      fill=WALL_COLOR, width=3, tags='glass')
        c.create_line(right_x, top_y, right_x, bot_y,
                      fill=WALL_COLOR, width=3, tags='glass')

        # Top chamber slants: from outer wall at row 0 to neck at row H.
        neck_left_x = (h.neck_col + 1) * CELL_PX
        neck_right_x = (h.neck_col + 2) * CELL_PX
        neck_top_y = (h.H + 1) * CELL_PX
        neck_bot_y = (h.H + 2) * CELL_PX

        # Left top slope.
        c.create_line(left_x, top_y, neck_left_x, neck_top_y,
                      fill=WALL_COLOR, width=3, tags='glass')
        # Right top slope.
        c.create_line(right_x, top_y, neck_right_x, neck_top_y,
                      fill=WALL_COLOR, width=3, tags='glass')

        # Bottom chamber slants: from neck to outer wall at last row.
        c.create_line(neck_left_x, neck_bot_y, left_x, bot_y,
                      fill=WALL_COLOR, width=3, tags='glass')
        c.create_line(neck_right_x, neck_bot_y, right_x, bot_y,
                      fill=WALL_COLOR, width=3, tags='glass')

        # Subtle neck highlight.
        c.create_rectangle(neck_left_x + 1, neck_top_y,
                           neck_right_x - 1, neck_bot_y,
                           outline=NECK_HIGHLIGHT, dash=(2, 2),
                           tags='glass')

    # -- sand grains (redrawn each tick) -------------------------------

    def _grain_color(self, age: int) -> str:
        # Age may be negative for "unfallen" pre-fill grains. Bucket by
        # bands so colour shifts are visible across the simulation.
        idx = max(0, age) // 8
        return SAND_PALETTE[idx % len(SAND_PALETTE)]

    def _draw_sand(self) -> None:
        c = self.canvas
        c.delete('sand')
        for r, col, age in self.hourglass.cells():
            if age is None:
                continue
            x0, y0, x1, y1 = self._cell_xy(r, col)
            colour = self._grain_color(age)
            c.create_oval(x0 + CELL_PAD, y0 + CELL_PAD,
                          x1 - CELL_PAD, y1 - CELL_PAD,
                          fill=colour, outline='', tags='sand')
        # Status line.
        h = self.hourglass
        self.stat.configure(
            text=f'top {h.top_count():>3}   bottom {h.bottom_count():>3}'
                 f'   step {h.step_count}')

    # -- animation loop -------------------------------------------------

    def _tick(self) -> None:
        if not self.paused:
            if not self.hourglass.is_done():
                self.hourglass.step()
            self._draw_sand()
        delay = max(16, int(1000.0 / self.fps))
        self.after(delay, self._tick)

    # -- button handlers -----------------------------------------------

    def _on_flip(self) -> None:
        self.hourglass.flip()
        self._draw_sand()

    def _on_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.configure(text='Resume' if self.paused else 'Pause')

    def _on_reset(self) -> None:
        self.hourglass.reset()
        self._draw_sand()

    def _on_shake(self) -> None:
        self.hourglass.shake()
        self._draw_sand()

    def _on_speed(self, value: float) -> None:
        self.fps = float(value)
        self.speed_label.configure(text=f'{int(self.fps)} fps')


if __name__ == '__main__':
    HourglassApp().mainloop()
