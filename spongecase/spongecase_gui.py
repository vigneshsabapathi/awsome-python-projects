"""sPoNgEcAsE — CustomTkinter GUI.

Dark-themed desktop UI: input/output text panes, intensity slider 0..100,
mode toggle (random / strict), seed entry for reproducible randomness,
re-roll, and Copy button. Output updates live as you type or move the
slider.

Run:
    uv run python spongecase/spongecase_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from spongecase import to_sponge, to_sponge_strict

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 13)
BUTTON_FONT = ('Segoe UI', 13, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#facc15'   # yellow-400 — spongebob vibe
MUTED = '#94a3b8'
TEXT = '#f8fafc'


class SpongeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('sPoNgEcAsE')
        self.geometry('780x720')
        self.minsize(700, 620)
        self.configure(fg_color=BG)

        # State
        self.intensity = tk.IntVar(value=50)  # 0..100
        # Stable RNG seed per slider movement so the live preview doesn't
        # jitter on every keystroke. Reseeded by the Re-roll button or
        # via the explicit seed entry.
        self._seed = 1337

        self._build_ui()
        self._update_output()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='sPoNgEcAsE', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text='ThE mOcKiNg-SpOnGeBoB cAsE mEmE',
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
                                        hover_color='#eab308',
                                        text_color='#0f172a',
                                        command=self._reroll)
        self.reroll_btn.pack(side='right', padx=(0, 8))

        # Seed entry row
        seed_frame = ctk.CTkFrame(self, fg_color='transparent')
        seed_frame.pack(side='bottom', fill='x', padx=20, pady=(4, 4))
        ctk.CTkLabel(seed_frame, text='Seed', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left', padx=(2, 8))
        self.seed_entry = ctk.CTkEntry(seed_frame, width=120,
                                       font=MONO_FONT,
                                       fg_color=PANEL, text_color=TEXT,
                                       border_color='#334155')
        self.seed_entry.insert(0, str(self._seed))
        self.seed_entry.pack(side='left')
        self.seed_entry.bind('<KeyRelease>', lambda _e: self._on_seed_change())
        ctk.CTkLabel(seed_frame,
                     text='(integer — same seed + intensity = same output)',
                     font=LABEL_FONT, text_color=MUTED).pack(side='left',
                                                              padx=(8, 0))

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
                                    progress_color=ACCENT,
                                    button_color=ACCENT,
                                    button_hover_color='#eab308',
                                    command=self._on_slider)
        self.slider.set(50)
        self.slider.pack(fill='x', padx=12, pady=(4, 4))

        # Preset chips: chill / mock / max ridicule
        preset_row = ctk.CTkFrame(slider_frame, fg_color='transparent')
        preset_row.pack(fill='x', padx=12, pady=(0, 10))
        for label, val in (('chill 25%', 25), ('mock 60%', 60),
                           ('max ridicule 100%', 100)):
            ctk.CTkButton(preset_row, text=label, width=130, height=26,
                          font=LABEL_FONT, fg_color='#334155',
                          hover_color='#475569',
                          command=lambda v=val: self._set_intensity(v)
                          ).pack(side='left', padx=(0, 6))

        # Mode toggle (segmented)
        mode_frame = ctk.CTkFrame(self, fg_color='transparent')
        mode_frame.pack(side='bottom', pady=(2, 4))
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_frame, values=['random', 'strict'],
            command=self._on_mode_change,
            font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color='#eab308',
        )
        self.mode_seg.set('random')
        self.mode_seg.pack()

        # ---- Top-down: input/output panels.
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(8, 0))

        # Input
        ctk.CTkLabel(body, text='Input', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.input_box = ctk.CTkTextbox(body, height=140, font=MONO_FONT,
                                        fg_color=PANEL, text_color=TEXT,
                                        border_width=1, border_color='#334155')
        self.input_box.pack(fill='both', expand=True, pady=(2, 8))
        self.input_box.insert('1.0', 'Hello, World!')
        self.input_box.bind('<KeyRelease>', lambda _e: self._update_output())

        # Output
        ctk.CTkLabel(body, text='Output', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.output_box = ctk.CTkTextbox(body, height=140, font=MONO_FONT,
                                         fg_color=PANEL, text_color=ACCENT,
                                         border_width=1, border_color='#334155')
        self.output_box.pack(fill='both', expand=True, pady=(2, 4))

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

    def _on_seed_change(self) -> None:
        raw = self.seed_entry.get().strip()
        try:
            self._seed = int(raw) if raw else 0
        except ValueError:
            # Hash non-integer text into a stable int so weird seed strings
            # still produce reproducible output instead of crashing.
            self._seed = abs(hash(raw)) % (2**31 - 1)
        self._update_output()

    def _reroll(self) -> None:
        # New seed, new randomness. Useful when the slider's current
        # output is unsatisfying. Sync the seed entry too.
        self._seed = random.randint(0, 2**31 - 1)
        self.seed_entry.delete(0, 'end')
        self.seed_entry.insert(0, str(self._seed))
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
        if mode == 'random':
            intensity = self.intensity.get() / 100.0
            result = to_sponge(text, intensity=intensity,
                               rng=random.Random(self._seed))
        else:
            result = to_sponge_strict(text)

        self.output_box.configure(state='normal')
        self.output_box.delete('1.0', 'end')
        self.output_box.insert('1.0', result)

        self.count_label.configure(
            text=f'{len(text)} chars  •  '
                 f'{sum(1 for c in text if c.isalpha())} letters'
        )


if __name__ == '__main__':
    SpongeApp().mainloop()
