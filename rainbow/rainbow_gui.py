"""Rainbow — CustomTkinter GUI.

Big animated rainbow text label. Three modes:
  * gradient — per-character HSV cycling text
  * arc      — multi-line ASCII rainbow arc with shifting hue
  * bands    — horizontal/vertical color bands

A speed slider controls FPS, the input box updates the text live, and the
Pause toggle freezes the hue offset. Animation runs forever otherwise.

Run:
    uv run python rainbow/rainbow_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from rainbow import hsv_to_rgb, rainbow_arc, _strip_ansi

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 13)
TEXT_FONT = ('Consolas', 40, 'bold')
ARC_FONT = ('Consolas', 14, 'bold')
BAND_FONT = ('Consolas', 18, 'bold')

MODES = ('gradient', 'arc', 'bands')


def _hex(h: float) -> str:
    """HSV hue (in [0, 1)) to '#rrggbb'."""
    r, g, b = hsv_to_rgb(h, 1.0, 1.0)
    return f'#{r:02x}{g:02x}{b:02x}'


class RainbowApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Rainbow')
        self.geometry('900x520')
        self.minsize(700, 420)
        self.configure(fg_color='#0b0f1a')

        self.text_var = ctk.StringVar(value='RAINBOW')
        self.mode_var = ctk.StringVar(value='gradient')
        self.fps_var = ctk.DoubleVar(value=15.0)
        self.paused = False
        self.offset = 0.0
        self._after_id: str | None = None
        # Pre-compute the ASCII arc once; we only re-tint per frame.
        self._arc_plain = _strip_ansi(rainbow_arc(width=80)).splitlines()

        self._build_ui()
        self._tick()

    # ---- UI ----------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', pady=(14, 4), padx=20)
        ctk.CTkLabel(header, text='RAINBOW', font=TITLE_FONT,
                     text_color='#f8fafc').pack(side='left')
        ctk.CTkLabel(header, text='HSV gradient + lolcat scroll',
                     font=LABEL_FONT, text_color='#94a3b8').pack(side='left',
                                                                 padx=12)

        # Bottom controls (packed first so they're never clipped).
        controls = ctk.CTkFrame(self, fg_color='#111827', corner_radius=10)
        controls.pack(side='bottom', fill='x', padx=16, pady=(8, 14))

        row1 = ctk.CTkFrame(controls, fg_color='transparent')
        row1.pack(fill='x', padx=12, pady=(10, 4))
        ctk.CTkLabel(row1, text='Text:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left')
        entry = ctk.CTkEntry(row1, textvariable=self.text_var,
                             font=('Segoe UI', 14), height=34)
        entry.pack(side='left', fill='x', expand=True, padx=(8, 0))

        row2 = ctk.CTkFrame(controls, fg_color='transparent')
        row2.pack(fill='x', padx=12, pady=(4, 10))

        ctk.CTkLabel(row2, text='Mode:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left')
        mode_menu = ctk.CTkSegmentedButton(row2, values=list(MODES),
                                           variable=self.mode_var,
                                           command=lambda _v: self._redraw())
        mode_menu.pack(side='left', padx=(8, 16))

        ctk.CTkLabel(row2, text='Speed:', font=LABEL_FONT,
                     text_color='#cbd5e1').pack(side='left')
        slider = ctk.CTkSlider(row2, from_=1, to=60, variable=self.fps_var,
                               width=180)
        slider.pack(side='left', padx=(8, 16))

        self.pause_btn = ctk.CTkButton(row2, text='Pause', width=88,
                                       fg_color='#334155',
                                       hover_color='#475569',
                                       command=self._toggle_pause)
        self.pause_btn.pack(side='right')

        # Display area — a frame whose content depends on mode.
        self.stage = ctk.CTkFrame(self, fg_color='#0b0f1a')
        self.stage.pack(side='top', fill='both', expand=True, padx=16,
                        pady=(8, 8))

        # Gradient mode: one label per character so we can color each.
        self.text_holder = ctk.CTkFrame(self.stage, fg_color='transparent')
        self.char_labels: list[ctk.CTkLabel] = []

        # Arc mode: a tk Text-like display via many labels (one per row).
        self.arc_holder = ctk.CTkFrame(self.stage, fg_color='transparent')
        self.arc_rows: list[list[ctk.CTkLabel]] = []
        for row in self._arc_plain:
            row_frame = ctk.CTkFrame(self.arc_holder, fg_color='transparent')
            row_frame.pack()
            row_labels: list[ctk.CTkLabel] = []
            for ch in row:
                lab = ctk.CTkLabel(row_frame, text=ch if ch != ' ' else ' ',
                                   font=ARC_FONT, text_color='#f8fafc',
                                   fg_color='transparent', width=10)
                lab.pack(side='left')
                row_labels.append(lab)
            self.arc_rows.append(row_labels)

        # Bands mode: a column of solid color rows.
        self.band_holder = ctk.CTkFrame(self.stage, fg_color='transparent')
        self.band_rows: list[ctk.CTkLabel] = []
        for _ in range(10):
            row = ctk.CTkLabel(self.band_holder, text='', height=24,
                               fg_color='#000000', corner_radius=0)
            row.pack(fill='x', padx=20, pady=2)
            self.band_rows.append(row)

        self._show_mode(self.mode_var.get())

    def _show_mode(self, mode: str) -> None:
        for w in (self.text_holder, self.arc_holder, self.band_holder):
            w.pack_forget()
        if mode == 'gradient':
            self.text_holder.pack(expand=True)
            self._rebuild_text()
        elif mode == 'arc':
            self.arc_holder.pack(expand=True)
        else:
            self.band_holder.pack(fill='both', expand=True)

    def _rebuild_text(self) -> None:
        for lab in self.char_labels:
            lab.destroy()
        self.char_labels = []
        text = self.text_var.get() or 'RAINBOW'
        for ch in text:
            lab = ctk.CTkLabel(self.text_holder,
                               text=ch if ch != ' ' else ' ',
                               font=TEXT_FONT, text_color='#ffffff',
                               fg_color='transparent')
            lab.pack(side='left')
            self.char_labels.append(lab)

    # ---- Animation ---------------------------------------------------------
    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.configure(text='Resume' if self.paused else 'Pause',
                                 fg_color='#475569' if self.paused
                                 else '#334155')

    def _redraw(self) -> None:
        self._show_mode(self.mode_var.get())

    def _tick(self) -> None:
        mode = self.mode_var.get()
        # Text could have changed; rebuild labels if length differs.
        if mode == 'gradient':
            wanted = self.text_var.get() or 'RAINBOW'
            if len(wanted) != len(self.char_labels) or any(
                    (lab.cget('text') or ' ') != (
                        ch if ch != ' ' else ' ')
                    for lab, ch in zip(self.char_labels, wanted)):
                self._rebuild_text()
            for i, lab in enumerate(self.char_labels):
                hue = self.offset + i / 14.0
                lab.configure(text_color=_hex(hue))
        elif mode == 'arc':
            for r, row in enumerate(self.arc_rows):
                for c, lab in enumerate(row):
                    hue = self.offset + (r + c) / 28.0
                    lab.configure(text_color=_hex(hue))
        elif mode == 'bands':
            for r, lab in enumerate(self.band_rows):
                hue = self.offset + r / len(self.band_rows)
                lab.configure(fg_color=_hex(hue))

        if not self.paused:
            self.offset = (self.offset + 1.0 / 60.0) % 1.0

        fps = max(1.0, float(self.fps_var.get()))
        delay = max(16, int(1000 / fps))
        self._after_id = self.after(delay, self._tick)


if __name__ == '__main__':
    RainbowApp().mainloop()
