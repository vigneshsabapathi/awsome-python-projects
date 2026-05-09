"""Numeral Systems — CustomTkinter GUI.

Multi-base entry panel: type into any field and the others update live.
Slider drives an arbitrary base 2..36. Roman numeral panel sits below.

Run:
    uv run python numeral_systems/numeral_systems_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from numeral_systems import (
    from_base,
    from_base_fractional,
    from_roman,
    from_twos_complement,
    to_base,
    to_base_fractional,
    to_roman,
    to_twos_complement,
)

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 14)
SMALL_FONT = ('Segoe UI', 11)
BUTTON_FONT = ('Segoe UI', 12, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#38bdf8'
GOOD = '#4ade80'
BAD = '#f87171'
MUTED = '#94a3b8'
TEXT = '#f8fafc'


# Fixed bases that always show in the multi-base panel.
FIXED = [
    ('Binary',      2),
    ('Octal',       8),
    ('Decimal',    10),
    ('Hex',        16),
]


class NumeralApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Numeral Systems')
        self.geometry('820x780')
        self.minsize(720, 700)
        self.configure(fg_color=BG)

        # Source of truth: the integer value displayed across all bases.
        # `None` means the current input doesn't parse — UI shows error state.
        self._value: float | None = 0.0
        self._fractional = False
        self._suspend = False  # re-entry guard during programmatic updates

        self.entries: dict[int, ctk.CTkEntry] = {}
        self.arbitrary_base = tk.IntVar(value=12)

        self._build_ui()
        self._refresh_all(source_base=10)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='NUMERAL SYSTEMS', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text='Type in any field — all the others update live',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Multi-base panel
        panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        panel.pack(fill='x', padx=20, pady=(10, 6))
        ctk.CTkLabel(panel, text='Bases', font=LABEL_FONT,
                     text_color=MUTED).pack(anchor='w', padx=14, pady=(10, 2))

        for label, base in FIXED:
            self._add_base_row(panel, label, base)

        # Arbitrary base row (slider + entry)
        arb = ctk.CTkFrame(panel, fg_color='transparent')
        arb.pack(fill='x', padx=14, pady=(8, 4))

        top = ctk.CTkFrame(arb, fg_color='transparent')
        top.pack(fill='x')
        self.arb_lbl = ctk.CTkLabel(top, text='Base 12',
                                    font=('Segoe UI', 13, 'bold'),
                                    text_color=ACCENT, width=90, anchor='w')
        self.arb_lbl.pack(side='left')
        ctk.CTkLabel(top, text='Arbitrary base 2..36', font=SMALL_FONT,
                     text_color=MUTED).pack(side='right')

        self.arb_slider = ctk.CTkSlider(
            arb, from_=2, to=36, number_of_steps=34,
            command=self._on_slider,
        )
        self.arb_slider.set(12)
        self.arb_slider.pack(fill='x', pady=(2, 4))

        self.arb_entry = ctk.CTkEntry(
            arb, font=MONO_FONT, fg_color=BG, text_color=TEXT,
            border_color='#334155',
        )
        self.arb_entry.pack(fill='x', pady=(0, 10))
        self.arb_entry.bind('<KeyRelease>', self._on_arb_entry)

        # Roman + two's complement panels
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(fill='x', padx=20, pady=(2, 6))

        roman = ctk.CTkFrame(bottom, fg_color=PANEL, corner_radius=12)
        roman.pack(side='left', fill='both', expand=True, padx=(0, 6))
        ctk.CTkLabel(roman, text='Roman numeral (1..3999)', font=LABEL_FONT,
                     text_color=MUTED).pack(anchor='w', padx=12, pady=(10, 2))
        self.roman_entry = ctk.CTkEntry(
            roman, font=MONO_FONT, fg_color=BG, text_color=TEXT,
            border_color='#334155',
        )
        self.roman_entry.pack(fill='x', padx=12, pady=(2, 12))
        self.roman_entry.bind('<KeyRelease>', self._on_roman)

        twos = ctk.CTkFrame(bottom, fg_color=PANEL, corner_radius=12)
        twos.pack(side='right', fill='both', expand=True, padx=(6, 0))
        twos_top = ctk.CTkFrame(twos, fg_color='transparent')
        twos_top.pack(fill='x', padx=12, pady=(10, 2))
        ctk.CTkLabel(twos_top, text="Two's complement (signed)",
                     font=LABEL_FONT, text_color=MUTED).pack(side='left')
        self.bits_var = tk.StringVar(value='8')
        self.bits_menu = ctk.CTkOptionMenu(
            twos_top, values=['8', '16', '32', '64'],
            variable=self.bits_var, width=70, command=self._on_bits_changed,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b',
        )
        self.bits_menu.pack(side='right')
        self.twos_entry = ctk.CTkEntry(
            twos, font=MONO_FONT, fg_color=BG, text_color=TEXT,
            border_color='#334155',
        )
        self.twos_entry.pack(fill='x', padx=12, pady=(2, 12))
        self.twos_entry.bind('<KeyRelease>', self._on_twos)

        # Status / hint footer
        self.status = ctk.CTkLabel(self, text='', font=SMALL_FONT,
                                   text_color=MUTED)
        self.status.pack(fill='x', padx=20, pady=(4, 12))

        # Tip about fractional input
        ctk.CTkLabel(self,
                     text='Tip: type a fractional value like "0.625" in '
                          'decimal — binary will show "0.101"',
                     font=SMALL_FONT, text_color='#64748b').pack(
                         fill='x', padx=20, pady=(0, 12))

    def _add_base_row(self, parent: ctk.CTkFrame,
                      label: str, base: int) -> None:
        row = ctk.CTkFrame(parent, fg_color='transparent')
        row.pack(fill='x', padx=14, pady=4)

        head = ctk.CTkLabel(row, text=label, font=LABEL_FONT,
                            text_color=MUTED, width=80, anchor='w')
        head.pack(side='left')

        sub = ctk.CTkLabel(row, text=f'base {base}', font=SMALL_FONT,
                           text_color='#475569', width=60, anchor='w')
        sub.pack(side='left')

        entry = ctk.CTkEntry(
            row, font=MONO_FONT, fg_color=BG, text_color=TEXT,
            border_color='#334155',
        )
        entry.pack(side='left', fill='x', expand=True)
        entry.bind('<KeyRelease>',
                   lambda _e, b=base: self._on_base_entry(b))
        self.entries[base] = entry

    # --------------------------------------------------------------- events
    def _on_slider(self, value: float) -> None:
        b = int(round(value))
        self.arbitrary_base.set(b)
        self.arb_lbl.configure(text=f'Base {b}')
        # Re-render arbitrary entry from current value.
        self._render_arbitrary(b)

    def _on_arb_entry(self, _event: tk.Event) -> None:
        if self._suspend:
            return
        base = self.arbitrary_base.get()
        text = self.arb_entry.get().strip()
        self._parse_into_value(text, base)
        self._refresh_all(source_base=base)

    def _on_base_entry(self, base: int) -> None:
        if self._suspend:
            return
        text = self.entries[base].get().strip()
        self._parse_into_value(text, base)
        self._refresh_all(source_base=base)

    def _on_roman(self, _event: tk.Event) -> None:
        if self._suspend:
            return
        text = self.roman_entry.get().strip()
        if not text:
            self._value = 0.0
            self._fractional = False
            self._refresh_all(source_base='roman')
            self._set_status('', good=True)
            return
        try:
            self._value = float(from_roman(text))
            self._fractional = False
            self._refresh_all(source_base='roman')
            self._set_status(f'Roman {text.upper()} = {int(self._value)}',
                             good=True)
        except ValueError as exc:
            self._value = None
            self._refresh_all(source_base='roman')
            self._set_status(str(exc), good=False)

    def _on_twos(self, _event: tk.Event) -> None:
        if self._suspend:
            return
        text = self.twos_entry.get().strip().replace(' ', '')
        if not text:
            return
        try:
            n = from_twos_complement(text)
            self._value = float(n)
            self._fractional = False
            self._refresh_all(source_base='twos')
            self._set_status(f"Two's complement {text} = {n}", good=True)
        except ValueError as exc:
            self._set_status(str(exc), good=False)

    def _on_bits_changed(self, _value: str) -> None:
        # Re-render twos-complement field with new width.
        self._refresh_all(source_base=10)

    # ----------------------------------------------------------------- core
    def _parse_into_value(self, text: str, base: int) -> None:
        """Parse text in `base` into self._value; update _fractional flag."""
        if not text:
            self._value = 0.0
            self._fractional = False
            self._set_status('', good=True)
            return
        try:
            if '.' in text:
                self._value = from_base_fractional(text, base)
                self._fractional = self._value != int(self._value)
            else:
                self._value = float(from_base(text, base))
                self._fractional = False
            self._set_status(f'{text} (base {base}) parsed', good=True)
        except ValueError as exc:
            self._value = None
            self._set_status(str(exc), good=False)

    def _refresh_all(self, *, source_base: int | str) -> None:
        """Repaint every other field from self._value."""
        self._suspend = True
        try:
            for base, entry in self.entries.items():
                if base == source_base:
                    continue
                entry.delete(0, 'end')
                entry.insert(0, self._render_in_base(base))

            arb_base = self.arbitrary_base.get()
            if source_base != arb_base:
                self.arb_entry.delete(0, 'end')
                self.arb_entry.insert(0, self._render_in_base(arb_base))

            if source_base != 'roman':
                self.roman_entry.delete(0, 'end')
                self.roman_entry.insert(0, self._render_roman())

            if source_base != 'twos':
                self.twos_entry.delete(0, 'end')
                self.twos_entry.insert(0, self._render_twos())
        finally:
            self._suspend = False

    def _render_in_base(self, base: int) -> str:
        if self._value is None:
            return ''
        if self._fractional:
            return to_base_fractional(self._value, base)
        n = int(self._value)
        return to_base(n, base)

    def _render_roman(self) -> str:
        if self._value is None or self._fractional:
            return ''
        n = int(self._value)
        if not 1 <= n <= 3999:
            return ''
        try:
            return to_roman(n)
        except ValueError:
            return ''

    def _render_twos(self) -> str:
        if self._value is None or self._fractional:
            return ''
        n = int(self._value)
        try:
            bits = int(self.bits_var.get())
        except ValueError:
            bits = 8
        try:
            return to_twos_complement(n, bits)
        except ValueError:
            return f'(out of {bits}-bit range)'

    def _render_arbitrary(self, base: int) -> None:
        self._suspend = True
        try:
            self.arb_entry.delete(0, 'end')
            self.arb_entry.insert(0, self._render_in_base(base))
        finally:
            self._suspend = False

    def _set_status(self, msg: str, *, good: bool) -> None:
        self.status.configure(text=msg, text_color=GOOD if good else BAD)


if __name__ == '__main__':
    NumeralApp().mainloop()
