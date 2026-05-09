"""Etching Drawer — CustomTkinter GUI.

A modern desktop Etch-A-Sketch. Hold an arrow key to drag a coloured line
across a canvas, cycle the brush colour with the C-button, save a PNG, or
shake the window (clear).

Run:
    uv run python etching/etching_gui.py
"""
from __future__ import annotations

from typing import Optional

import customtkinter as ctk
from PIL import Image, ImageDraw
from tkinter import colorchooser, filedialog

from etching import DEFAULT_HEIGHT, DEFAULT_WIDTH, Canvas

# Visual constants — same dark slate palette as the rest of the project.
BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'

# Pixel size of each canvas cell (the underlying logical canvas is character-
# sized; the GUI scales it up). Larger CELL = beefier strokes.
CELL = 14
# Initial palette: a curated rainbow that reads well against the dark BG.
COLOR_PALETTE: tuple[str, ...] = (
    '#38bdf8',  # sky
    '#34d399',  # emerald
    '#fbbf24',  # amber
    '#f472b6',  # pink
    '#a78bfa',  # violet
    '#f87171',  # rose
)
# How long (ms) between auto-repeat moves while an arrow key is held down.
REPEAT_MS = 60
# Cursor blink rate.
BLINK_MS = 400


class EtchingApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Etching Drawer')
        self.minsize(720, 520)
        self.configure(fg_color=BG)

        # Logical model — small char canvas drives the *direction* logic so
        # bounds-clamping and history live in one place. Pixel rendering is
        # done directly on the Tk Canvas / PIL image.
        self.canvas_w = DEFAULT_WIDTH
        self.canvas_h = DEFAULT_HEIGHT
        self.model = Canvas(self.canvas_w, self.canvas_h)

        self.color_idx = 0
        self.current_color = COLOR_PALETTE[0]
        # Stroke history for PNG export and clear: list of (x1,y1,x2,y2,color).
        self.segments: list[tuple[int, int, int, int, str]] = []

        # Keys currently held down → repeating direction set.
        self._held: set[str] = set()
        self._repeat_job: Optional[str] = None
        self._blink_job: Optional[str] = None
        self._cursor_id: Optional[int] = None
        self._cursor_visible = True

        self._build_ui()
        self._bind_keys()
        self._draw_cursor()
        self._schedule_blink()
        self.after(100, lambda: self.focus_force())

    # ---- UI construction ------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='ETCHING DRAWER',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Hold arrow keys to draw   •   C: cycle colour   '
                          '•   space: pen up/down   •   Save = PNG',
                     font=('Segoe UI', 12), text_color=MUTED).pack(
            anchor='w', pady=(2, 0))

        # Status & controls bar (packed first so they're never clipped).
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 8))

        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='bottom', padx=16, pady=(2, 4), fill='x')
        ctk.CTkButton(controls, text='Clear (S)', width=110,
                      fg_color='#334155', hover_color='#475569',
                      command=self.action_clear).pack(side='left',
                                                       padx=(12, 6), pady=8)
        ctk.CTkButton(controls, text='Cycle colour (C)', width=140,
                      fg_color='#334155', hover_color='#475569',
                      command=self.action_cycle_color).pack(side='left',
                                                             padx=6, pady=8)
        ctk.CTkButton(controls, text='Pick colour…', width=120,
                      fg_color='#334155', hover_color='#475569',
                      command=self.action_pick_color).pack(side='left',
                                                            padx=6, pady=8)
        ctk.CTkButton(controls, text='Playback (P)', width=120,
                      fg_color='#334155', hover_color='#475569',
                      command=self.action_playback).pack(side='left',
                                                          padx=6, pady=8)
        ctk.CTkButton(controls, text='Save PNG…', width=120,
                      fg_color=ACCENT, hover_color='#0ea5e9',
                      text_color='#0f172a', font=('Segoe UI', 12, 'bold'),
                      command=self.action_save).pack(side='right',
                                                      padx=(6, 12), pady=8)

        self.color_chip = ctk.CTkLabel(controls, text=' ',
                                       fg_color=self.current_color,
                                       width=24, height=24, corner_radius=4)
        self.color_chip.pack(side='right', padx=(0, 6), pady=8)

        # Tk canvas in a CTk frame.
        canvas_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        canvas_frame.pack(side='top', fill='both', expand=True,
                          padx=16, pady=(8, 4))
        self.tk_canvas = ctk.CTkCanvas(
            canvas_frame, bg=PANEL, highlightthickness=0,
            width=self.canvas_w * CELL, height=self.canvas_h * CELL)
        self.tk_canvas.pack(padx=8, pady=8)

        self._set_status()

    def _set_status(self, extra: str = '') -> None:
        msg = (f'pos ({self.model.cx},{self.model.cy})   '
               f'colour {self.current_color}   '
               f'segments {len(self.segments)}')
        if extra:
            msg = f'{extra}   •   {msg}'
        self.status.configure(text=msg)

    # ---- keyboard wiring ------------------------------------------------

    def _bind_keys(self) -> None:
        # Each arrow → a direction; pressing/holding adds it to _held.
        arrow_map = {
            '<KeyPress-Up>': 'up',
            '<KeyPress-Down>': 'down',
            '<KeyPress-Left>': 'left',
            '<KeyPress-Right>': 'right',
        }
        release_map = {
            '<KeyRelease-Up>': 'up',
            '<KeyRelease-Down>': 'down',
            '<KeyRelease-Left>': 'left',
            '<KeyRelease-Right>': 'right',
        }
        for ev, direction in arrow_map.items():
            self.bind_all(ev, lambda _e, d=direction: self._on_press(d))
        for ev, direction in release_map.items():
            self.bind_all(ev, lambda _e, d=direction: self._on_release(d))
        self.bind_all('<KeyPress-c>', lambda _e: self.action_cycle_color())
        self.bind_all('<KeyPress-s>', lambda _e: self.action_clear())
        self.bind_all('<KeyPress-p>', lambda _e: self.action_playback())
        self.bind_all('<KeyPress-space>',
                      lambda _e: self.action_toggle_pen())

    def _on_press(self, direction: str) -> None:
        self._held.add(direction)
        # Move once immediately for a snappy response, then auto-repeat.
        self._step()
        if self._repeat_job is None:
            self._repeat_job = self.after(REPEAT_MS, self._tick)

    def _on_release(self, direction: str) -> None:
        self._held.discard(direction)
        if not self._held and self._repeat_job is not None:
            self.after_cancel(self._repeat_job)
            self._repeat_job = None

    def _tick(self) -> None:
        if not self._held:
            self._repeat_job = None
            return
        self._step()
        self._repeat_job = self.after(REPEAT_MS, self._tick)

    # ---- drawing primitives --------------------------------------------

    def _step(self) -> None:
        """Combine all currently-held arrows into a single (possibly
        diagonal) move. Holding Up+Right draws a NE diagonal."""
        dy = (-1 if 'up' in self._held else 0) + \
             (1 if 'down' in self._held else 0)
        dx = (-1 if 'left' in self._held else 0) + \
             (1 if 'right' in self._held else 0)
        if dy == 0 and dx == 0:
            return
        direction = {
            (-1,  0): 'up',    ( 1,  0): 'down',
            ( 0, -1): 'left',  ( 0,  1): 'right',
            (-1, -1): 'up-left',   (-1,  1): 'up-right',
            ( 1, -1): 'down-left', ( 1,  1): 'down-right',
        }[(dy, dx)]
        old_x, old_y = self.model.cx, self.model.cy
        self.model.move(direction)
        new_x, new_y = self.model.cx, self.model.cy
        if (old_x, old_y) != (new_x, new_y) and self.model.pen_down:
            self._draw_segment(old_x, old_y, new_x, new_y,
                               self.current_color)
        self._draw_cursor()
        self._set_status()

    def _draw_segment(self, x1: int, y1: int, x2: int, y2: int,
                      color: str) -> None:
        px1 = x1 * CELL + CELL // 2
        py1 = y1 * CELL + CELL // 2
        px2 = x2 * CELL + CELL // 2
        py2 = y2 * CELL + CELL // 2
        self.tk_canvas.create_line(px1, py1, px2, py2, fill=color,
                                   width=3, capstyle='round',
                                   tags='ink')
        self.segments.append((x1, y1, x2, y2, color))

    def _draw_cursor(self) -> None:
        if self._cursor_id is not None:
            self.tk_canvas.delete(self._cursor_id)
            self._cursor_id = None
        if not self._cursor_visible:
            return
        cx = self.model.cx * CELL + CELL // 2
        cy = self.model.cy * CELL + CELL // 2
        r = CELL // 2 - 1
        self._cursor_id = self.tk_canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=ACCENT, width=2, tags='cursor')

    def _schedule_blink(self) -> None:
        self._cursor_visible = not self._cursor_visible
        self._draw_cursor()
        self._blink_job = self.after(BLINK_MS, self._schedule_blink)

    # ---- actions --------------------------------------------------------

    def action_clear(self) -> None:
        self.tk_canvas.delete('ink')
        self.segments.clear()
        self.model.clear()
        self._draw_cursor()
        self._set_status('shaken')

    def action_cycle_color(self) -> None:
        self.color_idx = (self.color_idx + 1) % len(COLOR_PALETTE)
        self.current_color = COLOR_PALETTE[self.color_idx]
        self.color_chip.configure(fg_color=self.current_color)
        self._set_status('colour cycled')

    def action_pick_color(self) -> None:
        result = colorchooser.askcolor(color=self.current_color,
                                       title='Pick brush colour')
        if result and result[1]:
            self.current_color = result[1]
            self.color_chip.configure(fg_color=self.current_color)
            self._set_status('custom colour')

    def action_toggle_pen(self) -> None:
        state = self.model.toggle_pen()
        self._set_status(f'pen {"DOWN" if state else "UP"}')

    def action_playback(self) -> None:
        # Replay all stored segments with a tiny delay between each.
        self.tk_canvas.delete('ink')
        snap = list(self.segments)
        self.segments.clear()

        def step(i: int = 0) -> None:
            if i >= len(snap):
                self._set_status('playback done')
                return
            x1, y1, x2, y2, color = snap[i]
            self._draw_segment(x1, y1, x2, y2, color)
            self._draw_cursor()
            self.after(20, step, i + 1)

        self._set_status('playback…')
        step()

    def action_save(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension='.png', filetypes=[('PNG image', '*.png')],
            title='Save etching as PNG')
        if not path:
            return
        # Render the same segments onto a PIL image. We use the GUI-pixel
        # geometry so the PNG matches what the user sees.
        w = self.canvas_w * CELL
        h = self.canvas_h * CELL
        img = Image.new('RGB', (w, h), color=PANEL)
        draw = ImageDraw.Draw(img)
        for x1, y1, x2, y2, color in self.segments:
            px1 = x1 * CELL + CELL // 2
            py1 = y1 * CELL + CELL // 2
            px2 = x2 * CELL + CELL // 2
            py2 = y2 * CELL + CELL // 2
            draw.line((px1, py1, px2, py2), fill=color, width=3)
        img.save(path, format='PNG')
        self._set_status(f'saved {path}')


if __name__ == '__main__':
    EtchingApp().mainloop()
