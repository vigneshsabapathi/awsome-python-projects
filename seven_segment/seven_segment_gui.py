"""Seven-Segment Display — CustomTkinter GUI.

A dark-themed desktop showcase: type into the input, watch the text
render live in giant seven-segment ASCII. Pick LCD/LED color presets,
tune the font size, or grab a custom color from the picker.

Run:
    uv run python seven_segment/seven_segment_gui.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from tkinter import colorchooser

import customtkinter as ctk

# Allow ``from seven_segment import …`` whether launched from repo root
# or from inside the ``seven_segment/`` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from seven_segment import render  # noqa: E402

# Color presets — (label, foreground "lit segment", background "panel").
PRESETS: dict[str, tuple[str, str]] = {
    'LCD green':  ('#22c55e', '#0a0f0a'),
    'LED red':    ('#ef4444', '#120606'),
    'LED amber':  ('#f59e0b', '#120c02'),
    'Cyan':       ('#22d3ee', '#04181c'),
    'Magenta':    ('#ec4899', '#1a0612'),
}

DEFAULT_PRESET = 'LCD green'


class SevenSegApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Seven-Segment Display')
        self.geometry('820x420')
        self.minsize(600, 320)
        self.configure(fg_color='#0f172a')

        self._fg_color: str = PRESETS[DEFAULT_PRESET][0]
        self._bg_color: str = PRESETS[DEFAULT_PRESET][1]
        self._font_size: int = 22

        self._build_ui()
        self._refresh_display()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header — packed top-down.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(14, 4))
        ctk.CTkLabel(header, text='SEVEN-SEGMENT DISPLAY',
                     font=('Segoe UI', 22, 'bold'),
                     text_color='#f8fafc').pack(side='left')
        ctk.CTkLabel(header, text='LCD / LED ASCII renderer',
                     font=('Segoe UI', 13),
                     text_color='#94a3b8').pack(side='left', padx=(12, 0))

        # Controls — packed below header.
        controls = ctk.CTkFrame(self, fg_color='#111827', corner_radius=10)
        controls.pack(side='top', fill='x', padx=20, pady=(4, 8))

        ctk.CTkLabel(controls, text='Text:',
                     font=('Segoe UI', 12)).grid(
                         row=0, column=0, padx=(12, 4), pady=10, sticky='w')
        self.entry = ctk.CTkEntry(controls, font=('Segoe UI', 14),
                                  placeholder_text='Type anything…')
        self.entry.grid(row=0, column=1, padx=4, pady=10, sticky='ew')
        self.entry.insert(0, 'PI = 3.14')
        self.entry.bind('<KeyRelease>', lambda _e: self._refresh_display())

        ctk.CTkLabel(controls, text='Preset:',
                     font=('Segoe UI', 12)).grid(
                         row=0, column=2, padx=(12, 4), pady=10, sticky='w')
        self.preset_var = ctk.StringVar(value=DEFAULT_PRESET)
        self.preset_menu = ctk.CTkOptionMenu(
            controls, values=list(PRESETS), variable=self.preset_var,
            command=self._on_preset_change, width=130)
        self.preset_menu.grid(row=0, column=3, padx=4, pady=10)

        self.color_btn = ctk.CTkButton(
            controls, text='Pick color…', width=100,
            command=self._on_pick_color,
            fg_color='#334155', hover_color='#475569')
        self.color_btn.grid(row=0, column=4, padx=(8, 12), pady=10)

        ctk.CTkLabel(controls, text='Size:',
                     font=('Segoe UI', 12)).grid(
                         row=1, column=0, padx=(12, 4), pady=(0, 10),
                         sticky='w')
        self.size_slider = ctk.CTkSlider(
            controls, from_=10, to=40, number_of_steps=30,
            command=self._on_size_change)
        self.size_slider.set(self._font_size)
        self.size_slider.grid(row=1, column=1, padx=4, pady=(0, 10),
                              sticky='ew', columnspan=2)
        self.size_label = ctk.CTkLabel(
            controls, text=f'{self._font_size}pt',
            font=('Segoe UI', 12), text_color='#94a3b8')
        self.size_label.grid(row=1, column=3, padx=4, pady=(0, 10), sticky='w')

        controls.grid_columnconfigure(1, weight=1)

        # Display panel — fills the rest.
        self.panel = ctk.CTkFrame(self, fg_color=self._bg_color,
                                  corner_radius=12)
        self.panel.pack(side='top', fill='both', expand=True,
                        padx=20, pady=(4, 16))

        # The big monospace label that holds the rendered art.
        self.display = ctk.CTkLabel(
            self.panel, text='', justify='left', anchor='center',
            font=('Consolas', self._font_size, 'bold'),
            text_color=self._fg_color, fg_color=self._bg_color)
        self.display.pack(fill='both', expand=True, padx=20, pady=20)

    # -------------------------------------------------------------- handlers
    def _on_preset_change(self, name: str) -> None:
        fg, bg = PRESETS[name]
        self._fg_color = fg
        self._bg_color = bg
        self._refresh_display()

    def _on_pick_color(self) -> None:
        result = colorchooser.askcolor(initialcolor=self._fg_color,
                                       title='Pick a segment color')
        # askcolor returns (rgb_tuple, hex_string) or (None, None) on cancel.
        if result and result[1]:
            self._fg_color = result[1]
            self._refresh_display()

    def _on_size_change(self, value: float) -> None:
        size = int(round(value))
        if size != self._font_size:
            self._font_size = size
            self.size_label.configure(text=f'{size}pt')
            self.display.configure(font=('Consolas', size, 'bold'))

    def _refresh_display(self) -> None:
        text = self.entry.get()
        art = render(text) if text else render(' ')
        self.panel.configure(fg_color=self._bg_color)
        self.display.configure(text=art, text_color=self._fg_color,
                               fg_color=self._bg_color)


if __name__ == '__main__':
    SevenSegApp().mainloop()
