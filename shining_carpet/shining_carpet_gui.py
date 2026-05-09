"""Shining Carpet — CustomTkinter GUI.

A dark-themed desktop window that fills a tk.Canvas with the tessellated
carpet tile and animates the colour phase. Switch palettes via the dropdown
(Shining-orange, Persian-blue, Bauhaus-primary), pause with the button,
or click the canvas to toggle the rotation of individual tile cells under
the cursor for a hand-crafted twist.

Run:
    uv run python shining_carpet/shining_carpet_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from shining_carpet import (PALETTE_GLYPHS, PALETTE_NAMES, PALETTES,
                            glyph_to_slot, render, tile)

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
CANVAS_BG = '#000000'

# Cell size in pixels. Tweak for chunkier or finer tile rendering.
CELL_W = 14
CELL_H = 20
FPS = 8


class ShiningCarpetApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Shining Carpet')
        self.geometry('900x620')
        self.minsize(720, 520)
        self.configure(fg_color=BG)

        self.palette_name: str = 'shining'
        self.tile_data: list[str] = tile(self.palette_name)
        self.cols: int = 60
        self.rows: int = 22
        self.frame: int = 0
        self.paused: bool = False
        self.cycle_palettes: bool = True
        # Per-cell rotation overrides — keyed by (col, row), value is the
        # extra slot offset to add at that cell. Click toggles between
        # 0 and 4 (half-cycle) so the user can stamp accents on the carpet.
        self.cell_overrides: dict[tuple[int, int], int] = {}

        self._build_ui()
        self.after(60, self._on_resize_done)
        self.after(120, self._tick)

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='SHINING CARPET',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Tessellated tile + rotating colour phase. '
                          'Click cells to stamp an accent.',
                     font=('Segoe UI', 12),
                     text_color=MUTED).pack(anchor='w', pady=(2, 0))

        # Status bar (bottom)
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 8))

        # Controls (bottom)
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='bottom', padx=20, pady=(0, 4), fill='x')

        ctk.CTkLabel(controls, text='Palette:',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(side='left')
        self.palette_var = ctk.StringVar(value=self.palette_name)
        self.palette_menu = ctk.CTkOptionMenu(
            controls, values=PALETTE_NAMES, variable=self.palette_var,
            width=140, fg_color=PANEL, button_color='#334155',
            button_hover_color='#475569',
            command=self._on_palette_change)
        self.palette_menu.pack(side='left', padx=(8, 16))

        self.cycle_var = ctk.BooleanVar(value=self.cycle_palettes)
        ctk.CTkCheckBox(
            controls, text='Auto-cycle', variable=self.cycle_var,
            command=self._on_cycle_toggle,
            text_color=FG, fg_color=ACCENT, hover_color='#0ea5e9',
        ).pack(side='left', padx=(0, 16))

        self.pause_btn = ctk.CTkButton(
            controls, text='Pause', width=90,
            fg_color='#334155', hover_color='#475569',
            command=self._toggle_pause)
        self.pause_btn.pack(side='right')

        ctk.CTkButton(
            controls, text='Clear stamps', width=120,
            fg_color='#334155', hover_color='#475569',
            command=self._clear_overrides).pack(side='right', padx=(0, 8))

        # Canvas
        self.canvas = tk.Canvas(self, bg=CANVAS_BG, highlightthickness=0,
                                bd=0)
        self.canvas.pack(side='top', fill='both', expand=True,
                         padx=20, pady=(8, 4))
        self.canvas.bind('<Configure>', self._on_canvas_configure)
        self.canvas.bind('<Button-1>', self._on_canvas_click)

    # -------- event handlers ---------------------------------------------

    def _on_canvas_configure(self, _event=None) -> None:
        # Recompute grid dimensions on resize, debounced via after().
        self.after(60, self._on_resize_done)

    def _on_resize_done(self) -> None:
        w = max(1, self.canvas.winfo_width())
        h = max(1, self.canvas.winfo_height())
        new_cols = max(8, w // CELL_W)
        new_rows = max(4, h // CELL_H)
        if (new_cols, new_rows) != (self.cols, self.rows):
            self.cols = new_cols
            self.rows = new_rows
            self.canvas.delete('all')
            self._draw_frame()

    def _on_palette_change(self, name: str) -> None:
        self.palette_name = name
        self.tile_data = tile(name)
        # Manual change disables auto-cycling so the user's choice sticks.
        self.cycle_palettes = False
        self.cycle_var.set(False)
        self.canvas.delete('all')
        self._draw_frame()

    def _on_cycle_toggle(self) -> None:
        self.cycle_palettes = bool(self.cycle_var.get())

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.configure(text='Resume' if self.paused else 'Pause')

    def _on_canvas_click(self, event) -> None:
        col = event.x // CELL_W
        row = event.y // CELL_H
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            return
        key = (int(col), int(row))
        # Toggle: 0 -> 4 (half rotation) -> remove.
        existing = self.cell_overrides.get(key, 0)
        if existing == 0:
            self.cell_overrides[key] = 4
        else:
            self.cell_overrides.pop(key, None)
        self._draw_frame()

    def _clear_overrides(self) -> None:
        self.cell_overrides.clear()
        self._draw_frame()

    # -------- animation loop ---------------------------------------------

    def _tick(self) -> None:
        if not self.paused:
            self.frame += 1
            if self.cycle_palettes and self.frame % 24 == 0:
                idx = PALETTE_NAMES.index(self.palette_name)
                self.palette_name = PALETTE_NAMES[
                    (idx + 1) % len(PALETTE_NAMES)]
                self.tile_data = tile(self.palette_name)
                self.palette_var.set(self.palette_name)
                self.canvas.delete('all')
            self._draw_frame()
        self.after(int(1000 / FPS), self._tick)

    def _draw_frame(self) -> None:
        rendered = render(self.cols, self.rows, self.tile_data,
                          offset=self.frame).splitlines()
        palette = PALETTES[self.palette_name]
        # We re-create rectangles every frame; for the modest grid sizes
        # used here this is plenty fast and keeps the code one-screen
        # simple. Heavier optimisation would cache rect ids per cell.
        self.canvas.delete('all')
        for r, line in enumerate(rendered):
            for c, ch in enumerate(line):
                slot = glyph_to_slot(ch)
                if slot == -1:
                    continue
                bonus = self.cell_overrides.get((c, r), 0)
                colour = palette[(slot + bonus) % len(palette)]
                x0 = c * CELL_W
                y0 = r * CELL_H
                self.canvas.create_rectangle(
                    x0, y0, x0 + CELL_W, y0 + CELL_H,
                    fill=colour, outline=colour, width=0)
        self._update_status()

    def _update_status(self) -> None:
        stamps = len(self.cell_overrides)
        self.status.configure(
            text=(f'palette {self.palette_name}  •  '
                  f'grid {self.cols}×{self.rows}  •  '
                  f'frame {self.frame}  •  '
                  f'{stamps} click stamp{"" if stamps == 1 else "s"}  •  '
                  f'glyph slots {len(PALETTE_GLYPHS)}'))


if __name__ == '__main__':
    ShiningCarpetApp().mainloop()
