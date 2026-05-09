"""Hex Grid — CustomTkinter GUI.

Dark Tailwind palette, sliders for rows + cols (1..20), monospace
preview pane, Copy button. The "Overlay" segmented button toggles the
coordinate-system labels (none / axial / cube / offset) and the values
appear inside each hex cell. "Export SVG..." writes a vector copy to
disk.

Run:
    uv run python hex_grid/hex_grid_gui.py
"""
from __future__ import annotations

from tkinter import filedialog

import customtkinter as ctk

from hex_grid import (
    COORD_SYSTEMS,
    coordinate_overlay,
    render,
    to_svg,
)

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
MONO = ('Consolas', 12)
MONO_BOLD = ('Consolas', 12, 'bold')

MIN_DIM = 1
MAX_DIM = 20
OVERLAY_LABELS = ['Plain'] + [s.capitalize() for s in COORD_SYSTEMS]


class HexGridApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Hex Grid')
        self.geometry('960x720')
        self.minsize(820, 560)
        self.configure(fg_color=BG)

        self._rows = 4
        self._cols = 6
        self._overlay = 'plain'  # 'plain' or one of COORD_SYSTEMS

        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='HEX GRID',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='ASCII honeycomb — drag the sliders, flip the '
                          'coordinate overlay, copy or export.',
                     font=('Segoe UI', 12),
                     text_color=MUTED).pack(anchor='w', pady=(2, 0))

        # Status bar at bottom
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 8))

        # Bottom action row
        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(side='bottom', padx=20, pady=(0, 4), fill='x')

        ctk.CTkLabel(actions, text='Overlay:',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(side='left')
        self.overlay_var = ctk.StringVar(value='Plain')
        self.overlay_seg = ctk.CTkSegmentedButton(
            actions, values=OVERLAY_LABELS,
            variable=self.overlay_var,
            selected_color=ACCENT, selected_hover_color='#0ea5e9',
            unselected_color=PANEL, unselected_hover_color='#334155',
            command=self._on_overlay_change,
        )
        self.overlay_seg.pack(side='left', padx=(8, 16))

        ctk.CTkButton(actions, text='Export SVG…',
                      fg_color='#a78bfa', hover_color='#8b5cf6',
                      text_color='#0f172a', font=('Segoe UI', 12, 'bold'),
                      width=130, command=self._export_svg).pack(side='right',
                                                                 padx=(8, 0))
        ctk.CTkButton(actions, text='Copy',
                      fg_color=ACCENT, hover_color='#0ea5e9',
                      text_color='#0f172a', font=('Segoe UI', 12, 'bold'),
                      width=100, command=self._copy_preview).pack(side='right')

        # Slider row — Rows + Cols
        sliders = ctk.CTkFrame(self, fg_color='transparent')
        sliders.pack(side='top', padx=20, pady=(8, 4), fill='x')
        sliders.grid_columnconfigure(1, weight=1)
        sliders.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(sliders, text='Rows:', font=('Segoe UI', 13, 'bold'),
                     text_color=FG).grid(row=0, column=0, padx=(0, 8))
        self.rows_label = ctk.CTkLabel(sliders, text=str(self._rows),
                                       font=('Consolas', 14, 'bold'),
                                       text_color=ACCENT, width=28)
        self.rows_label.grid(row=0, column=2, padx=(8, 8))
        self.rows_slider = ctk.CTkSlider(
            sliders, from_=MIN_DIM, to=MAX_DIM,
            number_of_steps=MAX_DIM - MIN_DIM,
            command=self._on_rows_change,
            progress_color=ACCENT, button_color=ACCENT,
            button_hover_color='#0ea5e9')
        self.rows_slider.set(self._rows)
        self.rows_slider.grid(row=0, column=1, sticky='ew')

        ctk.CTkLabel(sliders, text='Cols:', font=('Segoe UI', 13, 'bold'),
                     text_color=FG).grid(row=0, column=3, padx=(16, 8))
        self.cols_label = ctk.CTkLabel(sliders, text=str(self._cols),
                                       font=('Consolas', 14, 'bold'),
                                       text_color=ACCENT, width=28)
        self.cols_label.grid(row=0, column=5, padx=(8, 0))
        self.cols_slider = ctk.CTkSlider(
            sliders, from_=MIN_DIM, to=MAX_DIM,
            number_of_steps=MAX_DIM - MIN_DIM,
            command=self._on_cols_change,
            progress_color=ACCENT, button_color=ACCENT,
            button_hover_color='#0ea5e9')
        self.cols_slider.set(self._cols)
        self.cols_slider.grid(row=0, column=4, sticky='ew')

        # Preview pane
        preview_wrap = ctk.CTkFrame(self, fg_color='transparent')
        preview_wrap.pack(side='top', fill='both', expand=True,
                          padx=20, pady=(8, 4))
        ctk.CTkLabel(preview_wrap, text='Preview',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=MUTED, anchor='w').pack(anchor='w',
                                                          pady=(0, 4))
        self.preview_box = ctk.CTkTextbox(preview_wrap, font=MONO_BOLD,
                                           fg_color=PANEL, text_color=ACCENT,
                                           wrap='none')
        self.preview_box.pack(fill='both', expand=True)
        self.preview_box.configure(state='disabled')

    # ---------------------------------------------------------- callbacks

    def _on_rows_change(self, value: float) -> None:
        new = int(round(value))
        if new != self._rows:
            self._rows = new
            self.rows_label.configure(text=str(new))
            self._refresh()

    def _on_cols_change(self, value: float) -> None:
        new = int(round(value))
        if new != self._cols:
            self._cols = new
            self.cols_label.configure(text=str(new))
            self._refresh()

    def _on_overlay_change(self, choice: str) -> None:
        self._overlay = 'plain' if choice == 'Plain' else choice.lower()
        self._refresh()

    # ------------------------------------------------------------ render

    def _current_labels(self) -> dict | None:
        if self._overlay == 'plain':
            return None
        return coordinate_overlay(self._rows, self._cols, self._overlay)

    def _refresh(self) -> None:
        labels = self._current_labels()
        text = render(self._rows, self._cols, labels)
        self.preview_box.configure(state='normal')
        self.preview_box.delete('1.0', 'end')
        self.preview_box.insert('1.0', text)
        self.preview_box.configure(state='disabled')

        line_count = text.count('\n') + 1 if text else 0
        width = max((len(line) for line in text.splitlines()), default=0)
        cells = self._rows * self._cols
        self.status.configure(
            text=(f'overlay {self._overlay}  •  '
                  f'{self._rows} × {self._cols} hexes  •  '
                  f'{cells} cells  •  '
                  f'{line_count} lines × {width} chars'))

    # ----------------------------------------------------------- actions

    def _copy_preview(self) -> None:
        text = self.preview_box.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.status.configure(text='Copied honeycomb to clipboard.')

    def _export_svg(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self,
            title='Export honeycomb as SVG',
            defaultextension='.svg',
            initialfile=f'hex_{self._rows}x{self._cols}.svg',
            filetypes=[('SVG vector image', '*.svg'),
                       ('All files', '*.*')],
        )
        if not path:
            return
        labels = self._current_labels()
        try:
            svg = to_svg(self._rows, self._cols, labels)
            with open(path, 'w', encoding='utf-8') as fh:
                fh.write(svg)
        except OSError as e:
            self.status.configure(text=f'Failed to write SVG: {e}')
            return
        self.status.configure(text=f'Exported SVG to {path}')


if __name__ == '__main__':
    HexGridApp().mainloop()
