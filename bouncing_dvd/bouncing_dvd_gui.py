"""Bouncing DVD Logo — CustomTkinter GUI.

Dark-theme desktop UI. A "DVD" logo (colored rounded rectangle with text)
bounces around a canvas, cycles color on every wall hit, and shows live
bounce/corner/FPS stats. Up to 8 simultaneous logos supported.

Controls
--------
- Play/Pause button (or Space)
- Speed slider (1..60 fps)
- Logos slider (1..8)

Run:
    uv run python bouncing_dvd/bouncing_dvd_gui.py
"""
from __future__ import annotations

import random
import time
import tkinter as tk

import customtkinter as ctk

from bouncing_dvd import COLORS, Logo, random_logo

# ── palette ────────────────────────────────────────────────────────────────
BG      = '#0f172a'
PANEL   = '#1e293b'
BORDER  = '#334155'
CANVAS_BG = '#020617'

LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 22, 'bold')
STAT_FONT  = ('Consolas', 12)
LOGO_FONT  = ('Segoe UI', 18, 'bold')

CANVAS_W = 700
CANVAS_H = 500

LOGO_W_PX = 70   # pixel width of each logo rectangle
LOGO_H_PX = 38   # pixel height

# Map color names to hex for tk canvas
_HEX: dict[str, str] = {
    'red':     '#ef4444',
    'orange':  '#f97316',
    'yellow':  '#facc15',
    'green':   '#22c55e',
    'cyan':    '#06b6d4',
    'blue':    '#3b82f6',
    'magenta': '#d946ef',
    'white':   '#f8fafc',
}

# Physics operates in "pixel" units directly (not cells).
# We reuse the Logo dataclass; width/height passed to step() are pixel dims.


class BouncingDVDApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Bouncing DVD Logo')
        self.configure(fg_color=BG)
        self.resizable(False, False)

        self._n_logos   = 1
        self._fps       = 30
        self._running   = True
        self._after_id: str | None = None
        self._logos: list[Logo] = []
        self._canvas_items: list[tuple[int, int]] = []  # (rect_id, text_id) per logo
        self._last_tick = time.perf_counter()
        self._fps_display = 0.0

        self._build_ui()
        self._spawn_logos(self._n_logos)
        self._tick()

        self.bind('<space>', lambda _e: self._toggle_play())

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=18, pady=(14, 4))
        ctk.CTkLabel(header, text='BOUNCING DVD LOGO',
                     font=TITLE_FONT, text_color='#f8fafc').pack(side='left')
        self.stat_label = ctk.CTkLabel(
            header, text='', font=STAT_FONT, text_color='#94a3b8')
        self.stat_label.pack(side='right')

        canvas_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                    border_width=1, border_color=BORDER)
        canvas_frame.pack(side='top', padx=18, pady=8)
        self.canvas = tk.Canvas(canvas_frame, width=CANVAS_W, height=CANVAS_H,
                                bg=CANVAS_BG, highlightthickness=0, bd=0)
        self.canvas.pack(padx=8, pady=8)

        ctrl = ctk.CTkFrame(self, fg_color='transparent')
        ctrl.pack(side='top', fill='x', padx=18, pady=(4, 4))

        self.play_btn = ctk.CTkButton(
            ctrl, text='Pause (Space)', width=130, height=32,
            fg_color='#dc2626', hover_color='#b91c1c',
            command=self._toggle_play)
        self.play_btn.pack(side='left', padx=4)

        ctk.CTkLabel(ctrl, text='Logos:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(16, 4))
        self.logos_label = ctk.CTkLabel(ctrl, text='1', font=STAT_FONT,
                                        width=20, text_color='#f8fafc')
        self.logos_label.pack(side='left')
        ctk.CTkSlider(ctrl, from_=1, to=8, number_of_steps=7,
                      width=120, command=self._on_logos).pack(side='left', padx=(4, 16))

        ctk.CTkLabel(ctrl, text='Speed (fps):', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(0, 4))
        self.speed_label = ctk.CTkLabel(ctrl, text='30', font=STAT_FONT,
                                        width=28, text_color='#f8fafc')
        self.speed_label.pack(side='left')
        ctk.CTkSlider(ctrl, from_=1, to=60, number_of_steps=59,
                      width=180, command=self._on_speed).pack(side='left', padx=4)

        ctk.CTkLabel(self,
                     text='Space = play/pause',
                     font=('Segoe UI', 11), text_color='#64748b'
                     ).pack(side='top', pady=(0, 12))

    # ── Logo management ─────────────────────────────────────────────────────

    def _spawn_logos(self, n: int) -> None:
        """Replace logo list with n fresh logos; (re)create canvas items."""
        self.canvas.delete('all')
        self._canvas_items = []
        self._logos = []
        rng = random.Random()
        for _ in range(n):
            lg = random_logo(CANVAS_W, CANVAS_H, LOGO_W_PX, LOGO_H_PX, rng)
            self._logos.append(lg)
            rect_id = self.canvas.create_rectangle(
                lg.x, lg.y, lg.x + LOGO_W_PX, lg.y + LOGO_H_PX,
                fill=_HEX[lg.color], outline='', width=0)
            text_id = self.canvas.create_text(
                lg.x + LOGO_W_PX // 2, lg.y + LOGO_H_PX // 2,
                text='DVD', font=LOGO_FONT, fill=CANVAS_BG)
            self._canvas_items.append((rect_id, text_id))

    # ── Animation loop ──────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_tick
        self._fps_display = 1.0 / dt if dt > 0 else 0.0
        self._last_tick = now

        if self._running:
            for lg in self._logos:
                lg.step(CANVAS_W, CANVAS_H, LOGO_W_PX, LOGO_H_PX)

        self._redraw()
        self._update_stats()

        delay = max(int(1000 / max(self._fps, 1)), 16)
        self._after_id = self.after(delay, self._tick)

    def _redraw(self) -> None:
        canvas = self.canvas
        for lg, (rect_id, text_id) in zip(self._logos, self._canvas_items):
            x0, y0 = lg.x, lg.y
            x1, y1 = x0 + LOGO_W_PX, y0 + LOGO_H_PX
            canvas.coords(rect_id, x0, y0, x1, y1)
            canvas.coords(text_id, x0 + LOGO_W_PX // 2, y0 + LOGO_H_PX // 2)
            canvas.itemconfigure(rect_id, fill=_HEX[lg.color])

    def _update_stats(self) -> None:
        bounces = sum(lg.bounces for lg in self._logos)
        corners = sum(lg.corners for lg in self._logos)
        self.stat_label.configure(
            text=f'bounces {bounces:>5d}  |  corners {corners:>3d}  |  '
                 f'fps {self._fps_display:>4.1f}')

    # ── Callbacks ───────────────────────────────────────────────────────────

    def _toggle_play(self) -> None:
        self._running = not self._running
        if self._running:
            self.play_btn.configure(text='Pause (Space)',
                                    fg_color='#dc2626', hover_color='#b91c1c')
        else:
            self.play_btn.configure(text='Play (Space)',
                                    fg_color='#16a34a', hover_color='#15803d')

    def _on_logos(self, value: float) -> None:
        n = int(round(value))
        self.logos_label.configure(text=str(n))
        if n != self._n_logos:
            self._n_logos = n
            self._spawn_logos(n)

    def _on_speed(self, value: float) -> None:
        self._fps = int(round(value))
        self.speed_label.configure(text=str(self._fps))


if __name__ == '__main__':
    BouncingDVDApp().mainloop()
