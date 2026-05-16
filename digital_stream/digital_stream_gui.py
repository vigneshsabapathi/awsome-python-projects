"""Digital Stream — CustomTkinter GUI.

Matrix-style falling green digital rain rendered on a tk.Canvas.
Each glyph is drawn as a text item; the head glows bright white-green and the
tail fades through progressively darker greens.

Controls:
  Speed slider   — animation FPS (1 – 60)
  Density slider — new-drop spawn probability
  Charset toggle — Katakana / Digits / Latin

Run:
    uv run python digital_stream/digital_stream_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from digital_stream import CHARSETS, Rain

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
HEAD_COLOR = '#c8ffc8'   # near-white green for the head glyph
TAIL_COLORS = [
    '#39ff14',  # depth 1 — neon green
    '#00dc00',  # depth 2
    '#00b900',  # depth 3
    '#009600',  # depth 4
    '#007300',  # depth 5
    '#005000',  # depth 6
    '#003200',  # depth 7
    '#001e00',  # depth 8+
]
BG_COLOR = '#000000'

FONT_SIZE = 14
FONT_FAMILY = 'Courier New'
CHARSETS_LIST = list(CHARSETS.keys())


def _glyph_color(depth: int) -> str:
    if depth == 0:
        return HEAD_COLOR
    return TAIL_COLORS[min(depth - 1, len(TAIL_COLORS) - 1)]


class DigitalStreamApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Digital Stream')
        self.geometry('900x620')
        self.minsize(500, 360)
        self.configure(fg_color='#0a0a0a')

        self._fps: float = 20.0
        self._density: float = 0.03
        self._charset_idx: int = 0
        self._running: bool = True
        self._after_id: str | None = None

        self._cell_w: int = FONT_SIZE + 2
        self._cell_h: int = FONT_SIZE + 4

        self._build_ui()
        self._rebuild_rain()
        self.after(200, self._tick)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Left: canvas
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.bind('<Configure>', self._on_resize)

        # Right: control panel
        panel = ctk.CTkFrame(self, width=200, fg_color='#111111')
        panel.pack(side='right', fill='y', padx=0)
        panel.pack_propagate(False)

        ctk.CTkLabel(panel, text='DIGITAL\nSTREAM',
                     font=('Segoe UI', 20, 'bold'),
                     text_color='#39ff14').pack(pady=(20, 4))
        ctk.CTkLabel(panel, text='Matrix rain simulator',
                     font=('Segoe UI', 11),
                     text_color='#4a7c59').pack(pady=(0, 16))

        ctk.CTkLabel(panel, text='Speed (FPS)',
                     font=('Segoe UI', 12),
                     text_color='#94a3b8').pack(anchor='w', padx=16)
        self._fps_var = ctk.DoubleVar(value=self._fps)
        ctk.CTkSlider(panel, from_=1, to=60, variable=self._fps_var,
                      command=self._on_fps_change,
                      button_color='#39ff14',
                      progress_color='#1a5c1a').pack(fill='x', padx=16, pady=(2, 8))
        self._fps_label = ctk.CTkLabel(panel, text=f'{self._fps:.0f} fps',
                                       font=('Segoe UI', 11),
                                       text_color='#64748b')
        self._fps_label.pack(anchor='e', padx=16)

        ctk.CTkLabel(panel, text='Density',
                     font=('Segoe UI', 12),
                     text_color='#94a3b8').pack(anchor='w', padx=16, pady=(8, 0))
        self._density_var = ctk.DoubleVar(value=self._density * 100)
        ctk.CTkSlider(panel, from_=0.5, to=15.0, variable=self._density_var,
                      command=self._on_density_change,
                      button_color='#39ff14',
                      progress_color='#1a5c1a').pack(fill='x', padx=16, pady=(2, 8))
        self._density_label = ctk.CTkLabel(panel,
                                           text=f'{self._density * 100:.1f}%',
                                           font=('Segoe UI', 11),
                                           text_color='#64748b')
        self._density_label.pack(anchor='e', padx=16)

        ctk.CTkLabel(panel, text='Character Set',
                     font=('Segoe UI', 12),
                     text_color='#94a3b8').pack(anchor='w', padx=16, pady=(12, 4))
        self._charset_btn = ctk.CTkButton(
            panel, text=CHARSETS_LIST[0].capitalize(),
            fg_color='#1a3a1a', hover_color='#2a5a2a',
            text_color='#39ff14', font=('Segoe UI', 13, 'bold'),
            command=self._toggle_charset)
        self._charset_btn.pack(fill='x', padx=16, pady=4)

        ctk.CTkButton(panel, text='Restart',
                      fg_color='#1e293b', hover_color='#334155',
                      text_color='#94a3b8',
                      command=self._rebuild_rain).pack(fill='x', padx=16, pady=(24, 4))

    # ------------------------------------------------------------------
    # Rain management
    # ------------------------------------------------------------------
    def _rebuild_rain(self) -> None:
        w = self.canvas.winfo_width() or 800
        h = self.canvas.winfo_height() or 560
        cols = max(1, w // self._cell_w)
        rows = max(1, h // self._cell_h)
        self._rain = Rain(width=cols, height=rows,
                          density=self._density,
                          charset=CHARSETS_LIST[self._charset_idx])
        self.canvas.delete('all')
        self._text_items: list[list[int]] = []
        for r in range(rows):
            row_items = []
            for c in range(cols):
                x = c * self._cell_w + self._cell_w // 2
                y = r * self._cell_h + self._cell_h // 2
                item_id = self.canvas.create_text(
                    x, y, text=' ',
                    font=(FONT_FAMILY, FONT_SIZE),
                    fill=BG_COLOR,
                    anchor='center')
                row_items.append(item_id)
            self._text_items.append(row_items)

    def _on_resize(self, event: tk.Event) -> None:
        self._rebuild_rain()

    # ------------------------------------------------------------------
    # Animation loop
    # ------------------------------------------------------------------
    def _tick(self) -> None:
        if not self._running:
            return
        self._rain.step()
        self._draw_frame()
        delay = max(16, int(1000 / self._fps))
        self._after_id = self.after(delay, self._tick)

    def _draw_frame(self) -> None:
        rows = self._rain.height
        cols = self._rain.width

        # Build depth grid same logic as Rain.render() but for canvas.
        grid: list[list[tuple[str, int] | None]] = [
            [None] * cols for _ in range(rows)
        ]
        for drop in self._rain.drops:
            head = drop.head_row
            for depth, ch in enumerate(drop.chars):
                row = head - depth
                if 0 <= row < rows and 0 <= drop.col < cols:
                    existing = grid[row][drop.col]
                    if existing is None or depth < existing[1]:
                        grid[row][drop.col] = (ch, depth)

        for r, row_data in enumerate(grid):
            if r >= len(self._text_items):
                break
            row_items = self._text_items[r]
            for c, cell in enumerate(row_data):
                if c >= len(row_items):
                    break
                item_id = row_items[c]
                if cell is None:
                    self.canvas.itemconfigure(item_id, text=' ', fill=BG_COLOR)
                else:
                    ch, depth = cell
                    self.canvas.itemconfigure(item_id, text=ch,
                                              fill=_glyph_color(depth))

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------
    def _on_fps_change(self, value: float) -> None:
        self._fps = float(value)
        self._fps_label.configure(text=f'{self._fps:.0f} fps')

    def _on_density_change(self, value: float) -> None:
        self._density = float(value) / 100.0
        self._rain.density = self._density
        self._density_label.configure(text=f'{value:.1f}%')

    def _toggle_charset(self) -> None:
        self._charset_idx = (self._charset_idx + 1) % len(CHARSETS_LIST)
        name = CHARSETS_LIST[self._charset_idx]
        self._rain.set_charset(name)
        self._charset_btn.configure(text=name.capitalize())

    def destroy(self) -> None:
        self._running = False
        if self._after_id:
            self.after_cancel(self._after_id)
        super().destroy()


if __name__ == '__main__':
    app = DigitalStreamApp()
    app.mainloop()
