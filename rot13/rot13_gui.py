"""ROT13 Cipher — CustomTkinter GUI.

Dark-themed two-pane editor: type in the input pane, see the rot13'd text
in the output pane live. A "Self-Inverse Demo" button visualizes the
involution property by applying rot13 twice and confirming you're back to
the original.

Run:
    uv run python rot13/rot13_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from rot13 import rot13, rot47

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 13)
BUTTON_FONT = ('Segoe UI', 13, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#38bdf8'
ACCENT_HOVER = '#0ea5e9'
MUTED = '#94a3b8'
TEXT = '#f8fafc'


class Rot13App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('ROT13 Cipher')
        self.geometry('780x720')
        self.minsize(700, 620)
        self.configure(fg_color=BG)

        self.variant = tk.StringVar(value='rot13')
        self._suspend = False
        self._build_ui()
        self._update_output()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='ROT13 CIPHER', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text='Shift letters by 13 — encrypt = decrypt '
                          '(self-inverse)',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Bottom action bar (built first so it's never clipped on small screens)
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

        self.demo_btn = ctk.CTkButton(bottom, text='Self-Inverse Demo',
                                      width=170, height=36,
                                      font=BUTTON_FONT,
                                      fg_color=ACCENT,
                                      hover_color=ACCENT_HOVER,
                                      text_color='#0f172a',
                                      command=self._self_inverse_demo)
        self.demo_btn.pack(side='right', padx=(0, 8))

        # Variant toggle
        toggle_frame = ctk.CTkFrame(self, fg_color='transparent')
        toggle_frame.pack(side='bottom', pady=(2, 6))
        self.variant_seg = ctk.CTkSegmentedButton(
            toggle_frame, values=['rot13', 'rot47'],
            command=self._on_variant_change,
            font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
        )
        self.variant_seg.set('rot13')
        self.variant_seg.pack()

        # Body
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(8, 0))

        # Input pane
        ctk.CTkLabel(body, text='Input', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.input_box = ctk.CTkTextbox(body, font=MONO_FONT,
                                        fg_color=PANEL, text_color=TEXT,
                                        border_width=1,
                                        border_color='#334155')
        self.input_box.pack(fill='both', expand=True, pady=(2, 8))
        self.input_box.insert('1.0', 'Hello, World!')
        self.input_box.bind('<KeyRelease>', lambda _e: self._update_output())

        # Output pane
        ctk.CTkLabel(body, text='Output (live)', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.output_box = ctk.CTkTextbox(body, font=MONO_FONT,
                                         fg_color=PANEL, text_color=ACCENT,
                                         border_width=1,
                                         border_color='#334155')
        self.output_box.pack(fill='both', expand=True, pady=(2, 4))

        # Demo / status line
        self.demo_label = ctk.CTkLabel(
            body, text='Tip: applying ROT13 twice returns the original.',
            font=LABEL_FONT, text_color=MUTED, anchor='w', justify='left')
        self.demo_label.pack(fill='x', pady=(6, 0))

    # --------------------------------------------------------------- events
    def _on_variant_change(self, _value: str) -> None:
        self._update_output()

    def _copy_output(self) -> None:
        text = self.output_box.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(text)
        self.copy_btn.configure(text='Copied!')
        self.after(900, lambda: self.copy_btn.configure(text='Copy output'))

    def _self_inverse_demo(self) -> None:
        """Visualize encrypt = decrypt by applying twice and checking equality."""
        text = self.input_box.get('1.0', 'end-1c')
        fn = rot13 if self.variant_seg.get() == 'rot13' else rot47
        once = fn(text)
        twice = fn(once)
        ok = (twice == text)

        # Briefly flash the demo line + paint output with the round-trip.
        verdict = 'IDENTITY ✓' if ok else 'mismatch (?!)'
        self.demo_label.configure(
            text=f'apply once  → {self._truncate(once, 50)}\n'
                 f'apply twice → {self._truncate(twice, 50)}    {verdict}',
            text_color=ACCENT if ok else '#f87171',
            justify='left',
        )
        # Flash the demo button to acknowledge the click.
        self.demo_btn.configure(text='Round-trip OK' if ok else 'FAILED')
        self.after(1400, lambda: (
            self.demo_btn.configure(text='Self-Inverse Demo'),
            self.demo_label.configure(
                text='Tip: applying ROT13 twice returns the original.',
                text_color=MUTED, justify='left',
            ),
        ))

    @staticmethod
    def _truncate(s: str, n: int) -> str:
        return s if len(s) <= n else s[:n - 3] + '...'

    # ---------------------------------------------------------------- core
    def _update_output(self) -> None:
        if self._suspend:
            return
        text = self.input_box.get('1.0', 'end-1c')
        fn = rot13 if self.variant_seg.get() == 'rot13' else rot47
        result = fn(text)

        self.output_box.delete('1.0', 'end')
        self.output_box.insert('1.0', result)

        letters = sum(1 for c in text if c.isalpha())
        self.count_label.configure(
            text=f'{len(text)} chars  •  {letters} letters'
        )


if __name__ == '__main__':
    Rot13App().mainloop()
