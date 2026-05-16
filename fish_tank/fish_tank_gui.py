"""Fish Tank — CustomTkinter GUI.

Deep-blue water background. Fish swim in a large monospace label.
Sliders control fish count and speed.

Controls
--------
- Fish slider    : 1..12 fish
- Speed slider   : 1..30 fps
- Play/Pause btn : Space or click

Run:
    uv run python fish_tank/fish_tank_gui.py
"""
from __future__ import annotations

import random
import time
import tkinter as tk

import customtkinter as ctk

from fish_tank import Tank

# ── palette ───────────────────────────────────────────────────────────────────
BG        = '#0d1b2a'
PANEL     = '#1b2838'
BORDER    = '#2a4a6b'
WATER_BG  = '#060f1a'
TEXT_FG   = '#b0d4ff'

TITLE_FONT = ('Segoe UI', 20, 'bold')
LABEL_FONT = ('Segoe UI', 12)
STAT_FONT  = ('Consolas', 11)
TANK_FONT  = ('Courier New', 11)

TANK_W = 90   # chars
TANK_H = 22   # rows


class FishTankApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Fish Tank')
        self.configure(fg_color=BG)
        self.resizable(False, False)

        self._fps      = 8
        self._n_fish   = 5
        self._running  = True
        self._after_id: str | None = None
        self._frame    = 0
        self._last_t   = time.perf_counter()
        self._fps_real = 0.0

        self._tank = Tank(TANK_W, TANK_H, self._n_fish)

        self._build_ui()
        self._tick()

        self.bind('<space>', lambda _e: self._toggle_play())

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Title bar
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(fill='x', padx=16, pady=(12, 4))
        ctk.CTkLabel(header, text='FISH TANK', font=TITLE_FONT,
                     text_color='#7fc8f8').pack(side='left')
        self.stat_lbl = ctk.CTkLabel(header, text='', font=STAT_FONT,
                                     text_color='#4a90b8')
        self.stat_lbl.pack(side='right')

        # Tank display
        tank_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8,
                                  border_width=1, border_color=BORDER)
        tank_frame.pack(padx=16, pady=6)
        self.tank_lbl = tk.Label(
            tank_frame, text='', font=TANK_FONT,
            bg=WATER_BG, fg=TEXT_FG,
            justify='left', anchor='nw',
            padx=8, pady=6,
        )
        self.tank_lbl.pack()

        # Controls
        ctrl = ctk.CTkFrame(self, fg_color='transparent')
        ctrl.pack(fill='x', padx=16, pady=(4, 4))

        self.play_btn = ctk.CTkButton(
            ctrl, text='Pause', width=90, height=30,
            fg_color='#1a5276', hover_color='#1f618d',
            command=self._toggle_play)
        self.play_btn.pack(side='left', padx=4)

        ctk.CTkLabel(ctrl, text='Fish:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(14, 4))
        self.fish_val_lbl = ctk.CTkLabel(ctrl, text=str(self._n_fish),
                                         font=STAT_FONT, width=22,
                                         text_color='#f8fafc')
        self.fish_val_lbl.pack(side='left')
        ctk.CTkSlider(ctrl, from_=1, to=12, number_of_steps=11,
                      width=120, command=self._on_fish).pack(side='left', padx=(2, 14))

        ctk.CTkLabel(ctrl, text='Speed (fps):', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left', padx=(0, 4))
        self.speed_val_lbl = ctk.CTkLabel(ctrl, text=str(self._fps),
                                          font=STAT_FONT, width=26,
                                          text_color='#f8fafc')
        self.speed_val_lbl.pack(side='left')
        ctk.CTkSlider(ctrl, from_=1, to=30, number_of_steps=29,
                      width=160, command=self._on_speed).pack(side='left', padx=2)

        ctk.CTkLabel(self, text='Space = play/pause',
                     font=('Segoe UI', 10), text_color='#2a4a6b').pack(pady=(0, 10))

    # ── Animation ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_t
        self._fps_real = 1.0 / dt if dt > 0 else 0.0
        self._last_t = now

        if self._running:
            self._tank.step()
            self._frame += 1

        frame_text = self._tank.render(color=False)
        self.tank_lbl.configure(text=frame_text)

        self.stat_lbl.configure(
            text=(f'frame {self._frame:>5d}  |  '
                  f'fish {len(self._tank.fish):>2d}  |  '
                  f'bubbles {len(self._tank.bubbles):>2d}  |  '
                  f'fps {self._fps_real:>4.1f}'))

        delay = max(int(1000 / max(self._fps, 1)), 33)
        self._after_id = self.after(delay, self._tick)

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _toggle_play(self) -> None:
        self._running = not self._running
        if self._running:
            self.play_btn.configure(text='Pause',
                                    fg_color='#1a5276', hover_color='#1f618d')
        else:
            self.play_btn.configure(text='Play',
                                    fg_color='#1a7a4a', hover_color='#1e8a55')

    def _on_fish(self, value: float) -> None:
        n = int(round(value))
        self.fish_val_lbl.configure(text=str(n))
        if n != self._n_fish:
            self._n_fish = n
            self._tank = Tank(TANK_W, TANK_H, n)
            self._frame = 0

    def _on_speed(self, value: float) -> None:
        self._fps = int(round(value))
        self.speed_val_lbl.configure(text=str(self._fps))


if __name__ == '__main__':
    FishTankApp().mainloop()
