"""Pig Latin — CustomTkinter GUI.

Two-pane dark editor: type plain English on the left, watch the Pig Latin
appear on the right (or flip the toggle and decode in the other direction).
Mode segmented button switches between the three encodings (``pig``,
``greek``, ``ubbi``). Copy button puts the right pane on your clipboard.

Run:
    uv run python pig_latin/pig_latin_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from pig_latin import MODES, translate, untranslate

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 13)
BUTTON_FONT = ('Segoe UI', 13, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#38bdf8'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
BORDER = '#334155'

SAMPLE = 'The quick brown fox jumps over the lazy dog.'


class PigLatinApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Pig Latin')
        self.geometry('1100x680')
        self.minsize(900, 540)
        self.configure(fg_color=BG)

        self.direction = tk.StringVar(value='encode')
        self.mode = tk.StringVar(value='pig')

        self._build_ui()
        self._refresh()
        self.input_box.focus()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='PIG LATIN', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text='Move leading consonants + "ay"  •  '
                          'Vowel start + "way"  •  '
                          'Preserves case, punctuation, contractions',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Bottom: copy + char-count
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

        self.swap_btn = ctk.CTkButton(bottom, text='Swap panes',
                                      width=120, height=36,
                                      font=BUTTON_FONT,
                                      fg_color='#334155',
                                      hover_color='#475569',
                                      command=self._swap_panes)
        self.swap_btn.pack(side='right', padx=(0, 8))

        # Direction toggle (encode / decode)
        ctrl = ctk.CTkFrame(self, fg_color='transparent')
        ctrl.pack(side='bottom', fill='x', padx=20, pady=(2, 4))

        left_ctrl = ctk.CTkFrame(ctrl, fg_color='transparent')
        left_ctrl.pack(side='left')
        ctk.CTkLabel(left_ctrl, text='Direction',
                     font=LABEL_FONT, text_color=MUTED).pack(anchor='w')
        self.dir_seg = ctk.CTkSegmentedButton(
            left_ctrl, values=['encode', 'decode'],
            command=self._on_direction_change,
            font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color='#0ea5e9',
        )
        self.dir_seg.set('encode')
        self.dir_seg.pack(pady=(2, 0))

        right_ctrl = ctk.CTkFrame(ctrl, fg_color='transparent')
        right_ctrl.pack(side='right')
        ctk.CTkLabel(right_ctrl, text='Mode',
                     font=LABEL_FONT, text_color=MUTED).pack(anchor='e')
        self.mode_seg = ctk.CTkSegmentedButton(
            right_ctrl, values=list(MODES),
            command=self._on_mode_change,
            font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color='#0ea5e9',
        )
        self.mode_seg.set('pig')
        self.mode_seg.pack(pady=(2, 0))

        # Two-pane body
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(8, 0))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(1, weight=1)

        self.input_label = ctk.CTkLabel(body, text='Input  (English)',
                                        font=LABEL_FONT, text_color=MUTED,
                                        anchor='w')
        self.input_label.grid(row=0, column=0, sticky='ew', padx=(0, 6))

        self.output_label = ctk.CTkLabel(body, text='Output  (Pig Latin)',
                                         font=LABEL_FONT, text_color=MUTED,
                                         anchor='w')
        self.output_label.grid(row=0, column=1, sticky='ew', padx=(6, 0))

        self.input_box = ctk.CTkTextbox(body, font=MONO_FONT,
                                        fg_color=PANEL, text_color=TEXT,
                                        border_width=1, border_color=BORDER,
                                        wrap='word')
        self.input_box.grid(row=1, column=0, sticky='nsew', padx=(0, 6),
                            pady=(2, 0))
        self.input_box.insert('1.0', SAMPLE)
        self.input_box.bind('<KeyRelease>', lambda _e: self._refresh())

        self.output_box = ctk.CTkTextbox(body, font=MONO_FONT,
                                         fg_color=PANEL, text_color=ACCENT,
                                         border_width=1, border_color=BORDER,
                                         wrap='word')
        self.output_box.grid(row=1, column=1, sticky='nsew', padx=(6, 0),
                             pady=(2, 0))

    # --------------------------------------------------------------- events
    def _on_direction_change(self, _value: str) -> None:
        self._update_labels()
        self._refresh()

    def _on_mode_change(self, _value: str) -> None:
        self._refresh()

    def _swap_panes(self) -> None:
        """Move the current output into the input box and flip direction."""
        out = self.output_box.get('1.0', 'end-1c')
        new_dir = 'decode' if self.dir_seg.get() == 'encode' else 'encode'
        self.dir_seg.set(new_dir)
        self.input_box.delete('1.0', 'end')
        self.input_box.insert('1.0', out)
        self._update_labels()
        self._refresh()

    def _copy_output(self) -> None:
        text = self.output_box.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(text)
        original = self.copy_btn.cget('text')
        self.copy_btn.configure(text='Copied!')
        self.after(900, lambda: self.copy_btn.configure(text=original))

    # ---------------------------------------------------------------- core
    def _update_labels(self) -> None:
        if self.dir_seg.get() == 'encode':
            self.input_label.configure(text='Input  (English)')
            self.output_label.configure(text='Output  (Pig Latin)')
        else:
            self.input_label.configure(text='Input  (Pig Latin)')
            self.output_label.configure(text='Output  (English)')

    def _refresh(self) -> None:
        text = self.input_box.get('1.0', 'end-1c')
        mode = self.mode_seg.get()
        if self.dir_seg.get() == 'encode':
            result = translate(text, mode=mode)
        else:
            result = untranslate(text, mode=mode)

        self.output_box.configure(state='normal')
        self.output_box.delete('1.0', 'end')
        self.output_box.insert('1.0', result)

        self.count_label.configure(
            text=f'{len(text)} chars  •  '
                 f'{sum(1 for c in text if c.isalpha())} letters  •  '
                 f'mode: {mode}'
        )


if __name__ == '__main__':
    PigLatinApp().mainloop()
