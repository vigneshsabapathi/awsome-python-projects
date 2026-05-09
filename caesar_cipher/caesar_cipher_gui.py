"""Caesar Cipher — CustomTkinter GUI.

Dark-themed desktop UI with live encrypt/decrypt, a shift slider, and
a brute-force panel scoring all 26 shifts by English-likelihood.

Run:
    uv run python caesar_cipher/caesar_cipher_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from caesar_cipher import brute_force, decrypt, encrypt

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 13)
BUTTON_FONT = ('Segoe UI', 13, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#38bdf8'
MUTED = '#94a3b8'
TEXT = '#f8fafc'


class CaesarApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Caesar Cipher')
        # Generous height so 125% DPI doesn't clip the brute-force list.
        self.geometry('780x880')
        self.minsize(720, 760)
        self.configure(fg_color=BG)

        self.mode = tk.StringVar(value='encrypt')
        self.shift = tk.IntVar(value=3)
        self._suspend_update = False

        self._build_ui()
        self._update_output()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='CAESAR CIPHER', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text='Shift each letter N positions in the alphabet',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # ---- Bottom-up: critical controls first so they're never clipped.
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

        self.crack_btn = ctk.CTkButton(bottom, text='Auto-crack',
                                       width=110, height=36,
                                       font=BUTTON_FONT,
                                       fg_color=ACCENT,
                                       hover_color='#0ea5e9',
                                       text_color='#0f172a',
                                       command=self._auto_crack)
        self.crack_btn.pack(side='right', padx=(0, 8))

        # Shift slider row
        slider_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        slider_frame.pack(side='bottom', fill='x', padx=20, pady=(4, 6))

        top_row = ctk.CTkFrame(slider_frame, fg_color='transparent')
        top_row.pack(fill='x', padx=12, pady=(10, 0))
        ctk.CTkLabel(top_row, text='Shift', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left')
        self.shift_value_lbl = ctk.CTkLabel(top_row, text='+3',
                                            font=('Segoe UI', 16, 'bold'),
                                            text_color=ACCENT)
        self.shift_value_lbl.pack(side='right')

        self.slider = ctk.CTkSlider(slider_frame, from_=-25, to=25,
                                    number_of_steps=50,
                                    command=self._on_slider)
        self.slider.set(3)
        self.slider.pack(fill='x', padx=12, pady=(4, 12))

        # Mode toggle (segmented)
        mode_frame = ctk.CTkFrame(self, fg_color='transparent')
        mode_frame.pack(side='bottom', pady=(2, 4))
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_frame, values=['encrypt', 'decrypt'],
            command=self._on_mode_change,
            font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color='#0ea5e9',
        )
        self.mode_seg.set('encrypt')
        self.mode_seg.pack()

        # ---- Top-down: input/output/brute-force in the remaining space.
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

        # Brute-force panel
        ctk.CTkLabel(body,
                     text='Brute-force — all 26 shifts ranked by '
                          'English-likelihood (lower chi² = more English)',
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
        self.shift.set(n)
        sign = '+' if n >= 0 else ''
        self.shift_value_lbl.configure(text=f'{sign}{n}')
        self._update_output()

    def _on_mode_change(self, _value: str) -> None:
        self._update_output()

    def _auto_crack(self) -> None:
        """Pick the shift that makes the input look most like English."""
        text = self.input_box.get('1.0', 'end-1c')
        if not text.strip():
            return
        results = brute_force(text)
        best_shift = results[0][0]  # decrypt-shift
        # Switch to decrypt mode and set slider to the cracked shift.
        self.mode_seg.set('decrypt')
        self.slider.set(best_shift)
        self.shift.set(best_shift)
        sign = '+' if best_shift >= 0 else ''
        self.shift_value_lbl.configure(text=f'{sign}{best_shift}')
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
        if self._suspend_update:
            return
        text = self.input_box.get('1.0', 'end-1c')
        shift = self.shift.get()
        mode = self.mode_seg.get()
        result = encrypt(text, shift) if mode == 'encrypt' \
            else decrypt(text, shift)

        self.output_box.configure(state='normal')
        self.output_box.delete('1.0', 'end')
        self.output_box.insert('1.0', result)

        self.count_label.configure(
            text=f'{len(text)} chars  •  '
                 f'{sum(1 for c in text if c.isalpha())} letters'
        )

        # Brute-force panel always shows decryption candidates from input.
        results = brute_force(text) if text.strip() else []
        self.brute_box.configure(state='normal')
        self.brute_box.delete('1.0', 'end')
        if results:
            for i, (s, plain, score) in enumerate(results):
                marker = '★' if i == 0 else ' '
                preview = plain if len(plain) <= 60 else plain[:57] + '...'
                self.brute_box.insert(
                    'end',
                    f' {marker} shift={s:>2}  chi²={score:7.2f}  {preview}\n'
                )
        self.brute_box.configure(state='disabled')


if __name__ == '__main__':
    CaesarApp().mainloop()
