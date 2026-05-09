"""Leetspeak — CustomTkinter GUI.

Dark-themed desktop UI with two text panes (input/output), an intensity
slider 0..100, a mode toggle (encode / decode), a brute-decode panel
that surfaces the most-English-like reading of the input, and a Copy
button. Output updates live as you type or move the slider.

Run:
    uv run python leetspeak/leetspeak_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from leetspeak import brute_decode, from_leet, to_leet

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 13)
BUTTON_FONT = ('Segoe UI', 13, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#22d3ee'   # cyan-400 — leet/cyber vibe
MUTED = '#94a3b8'
TEXT = '#f8fafc'


class LeetApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Leetspeak')
        self.geometry('780x880')
        self.minsize(720, 760)
        self.configure(fg_color=BG)

        # State
        self.intensity = tk.IntVar(value=50)  # 0..100
        # Stable RNG seed per slider movement so the live preview doesn't
        # jitter on every keystroke. Reseeded on slider change.
        self._seed = 1337

        self._build_ui()
        self._update_output()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='LEETSPEAK', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text='Probabilistic l337 substitution — h3llo -> #3||0',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # ---- Bottom-up: critical controls first.
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(side='bottom', fill='x', padx=20, pady=(4, 14))

        self.count_label = ctk.CTkLabel(bottom, text='0 chars',
                                        font=LABEL_FONT, text_color=MUTED)
        self.count_label.pack(side='left')

        self.copy_btn = ctk.CTkButton(bottom, text='Copy output',
                                      width=130, height=36,
                                      font=BUTTON_FONT,
                                      fg_color='#334155',
                                      hover_color='#475569',
                                      command=self._copy_output)
        self.copy_btn.pack(side='right')

        self.reroll_btn = ctk.CTkButton(bottom, text='Re-roll',
                                        width=110, height=36,
                                        font=BUTTON_FONT,
                                        fg_color=ACCENT,
                                        hover_color='#06b6d4',
                                        text_color='#0f172a',
                                        command=self._reroll)
        self.reroll_btn.pack(side='right', padx=(0, 8))

        # Intensity slider row
        slider_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        slider_frame.pack(side='bottom', fill='x', padx=20, pady=(4, 6))

        top_row = ctk.CTkFrame(slider_frame, fg_color='transparent')
        top_row.pack(fill='x', padx=12, pady=(10, 0))
        ctk.CTkLabel(top_row, text='Intensity', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left')
        self.intensity_lbl = ctk.CTkLabel(top_row, text='50%',
                                          font=('Segoe UI', 16, 'bold'),
                                          text_color=ACCENT)
        self.intensity_lbl.pack(side='right')

        self.slider = ctk.CTkSlider(slider_frame, from_=0, to=100,
                                    number_of_steps=100,
                                    command=self._on_slider)
        self.slider.set(50)
        self.slider.pack(fill='x', padx=12, pady=(4, 4))

        # Preset chips: mild / standard / hardcore
        preset_row = ctk.CTkFrame(slider_frame, fg_color='transparent')
        preset_row.pack(fill='x', padx=12, pady=(0, 10))
        for label, val in (('mild 20%', 20), ('standard 50%', 50),
                           ('hardcore 100%', 100)):
            ctk.CTkButton(preset_row, text=label, width=110, height=26,
                          font=LABEL_FONT, fg_color='#334155',
                          hover_color='#475569',
                          command=lambda v=val: self._set_intensity(v)
                          ).pack(side='left', padx=(0, 6))

        # Mode toggle (segmented)
        mode_frame = ctk.CTkFrame(self, fg_color='transparent')
        mode_frame.pack(side='bottom', pady=(2, 4))
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_frame, values=['encode', 'decode'],
            command=self._on_mode_change,
            font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color='#06b6d4',
        )
        self.mode_seg.set('encode')
        self.mode_seg.pack()

        # ---- Top-down: input/output/brute panel.
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(8, 0))

        # Input
        ctk.CTkLabel(body, text='Input', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.input_box = ctk.CTkTextbox(body, height=110, font=MONO_FONT,
                                        fg_color=PANEL, text_color=TEXT,
                                        border_width=1, border_color='#334155')
        self.input_box.pack(fill='x', pady=(2, 8))
        self.input_box.insert('1.0', 'Hello, World!')
        self.input_box.bind('<KeyRelease>', lambda _e: self._update_output())

        # Output
        ctk.CTkLabel(body, text='Output', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.output_box = ctk.CTkTextbox(body, height=110, font=MONO_FONT,
                                         fg_color=PANEL, text_color=ACCENT,
                                         border_width=1, border_color='#334155')
        self.output_box.pack(fill='x', pady=(2, 10))

        # Brute-decode panel
        ctk.CTkLabel(body,
                     text='Brute-decode — common patterns ranked by '
                          'English-likelihood (lower chi^2 = more English)',
                     font=LABEL_FONT, text_color=MUTED,
                     anchor='w').pack(fill='x')
        self.brute_box = ctk.CTkTextbox(body, font=MONO_FONT,
                                        fg_color=PANEL, text_color='#cbd5e1',
                                        border_width=1, border_color='#334155')
        self.brute_box.pack(fill='both', expand=True, pady=(2, 4))
        self.brute_box.configure(state='disabled')

    # --------------------------------------------------------------- events
    def _on_slider(self, value: float) -> None:
        n = int(round(value))
        self.intensity.set(n)
        self.intensity_lbl.configure(text=f'{n}%')
        self._update_output()

    def _set_intensity(self, value: int) -> None:
        self.slider.set(value)
        self._on_slider(value)

    def _on_mode_change(self, _value: str) -> None:
        self._update_output()

    def _reroll(self) -> None:
        # New seed, new randomness. Useful when the slider's current
        # output is unsatisfying.
        self._seed = random.randint(0, 2**31 - 1)
        self._update_output()

    def _copy_output(self) -> None:
        text = self.output_box.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(text)
        original = self.copy_btn.cget('text')
        self.copy_btn.configure(text='Copied!')
        self.after(900, lambda: self.copy_btn.configure(text=original))

    # ---------------------------------------------------------------- core
    def _update_output(self) -> None:
        text = self.input_box.get('1.0', 'end-1c')
        mode = self.mode_seg.get()
        if mode == 'encode':
            intensity = self.intensity.get() / 100.0
            result = to_leet(text, intensity=intensity,
                             rng=random.Random(self._seed))
        else:
            result = from_leet(text)

        self.output_box.configure(state='normal')
        self.output_box.delete('1.0', 'end')
        self.output_box.insert('1.0', result)

        self.count_label.configure(
            text=f'{len(text)} chars  •  '
                 f'{sum(1 for c in text if c.isalpha())} letters'
        )

        # Brute panel always operates on the *input* — i.e. "what English
        # sentence is this leet most likely to be?". For encoded input
        # this is mostly nonsense (already English) but still informative.
        self.brute_box.configure(state='normal')
        self.brute_box.delete('1.0', 'end')
        if text.strip():
            for i, (label, plain, score) in enumerate(brute_decode(text)):
                marker = '*' if i == 0 else ' '
                preview = plain if len(plain) <= 60 else plain[:57] + '...'
                self.brute_box.insert(
                    'end',
                    f' {marker} chi^2={score:7.2f}  [{label}]  {preview}\n'
                )
        self.brute_box.configure(state='disabled')


if __name__ == '__main__':
    LeetApp().mainloop()
