"""Multiplication Table — CustomTkinter GUI.

Dark-theme desktop UI that draws the N x N multiplication table as a colored
heatmap. A slider controls N (2..30), and a switch toggles the modular
variant — multiplication mod M produces vivid symmetric patterns that
distinguish prime from composite moduli.

Run:
    uv run python mult_table/mult_table_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from mult_table import _is_prime

N_MIN, N_MAX = 2, 30
DEFAULT_N = 12
DEFAULT_MOD = 12

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
HEADER_BG = '#334155'
HEADER_FG = '#e2e8f0'

# 12-stop palette tuned for dark backgrounds: cool -> warm.
HEATMAP = (
    '#1e3a8a', '#1d4ed8', '#2563eb', '#3b82f6', '#06b6d4', '#0d9488',
    '#10b981', '#84cc16', '#eab308', '#f59e0b', '#f97316', '#dc2626',
)


def heatmap_color(value: float, vmin: float, vmax: float) -> str:
    """Map a value to a hex color across the 12-stop heatmap palette."""
    if vmax <= vmin:
        return HEATMAP[0]
    t = (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    idx = min(int(t * len(HEATMAP)), len(HEATMAP) - 1)
    return HEATMAP[idx]


def modular_color(value: int, mod: int) -> str:
    """Hue-cycle around the residue ring so equal residues share a color."""
    if mod <= 1:
        return HEATMAP[0]
    idx = int(value % mod / mod * len(HEATMAP))
    idx = min(idx, len(HEATMAP) - 1)
    return HEATMAP[idx]


class MultTableApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Multiplication Table')
        self.geometry('900x780')
        self.minsize(720, 620)
        self.configure(fg_color=BG)

        self.n = DEFAULT_N
        self.mod_enabled = False
        self.mod_value = DEFAULT_MOD
        self.cells: list[list[ctk.CTkLabel]] = []

        self._build_ui()
        self._rebuild_grid()

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='MULTIPLICATION TABLE',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(header,
                     text='Heatmap of i × j   —   toggle modular for Z/MZ patterns',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(2, 0))

        # Status bar (bottom)
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 12),
                                   text_color=MUTED, justify='center')
        self.status.pack(side='bottom', pady=(2, 10))

        # Controls
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='bottom', padx=20, pady=(4, 4), fill='x')

        # Row 1: N slider
        slider_row = ctk.CTkFrame(controls, fg_color='transparent')
        slider_row.pack(padx=14, pady=(10, 4), fill='x')
        self.n_label = ctk.CTkLabel(slider_row, text=f'Size N: {DEFAULT_N}',
                                    font=('Segoe UI', 13, 'bold'),
                                    text_color=FG, width=120, anchor='w')
        self.n_label.pack(side='left')
        self.n_slider = ctk.CTkSlider(slider_row, from_=N_MIN, to=N_MAX,
                                      number_of_steps=N_MAX - N_MIN,
                                      command=self._on_n_change)
        self.n_slider.set(DEFAULT_N)
        self.n_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Row 2: modular toggle + mod slider
        mod_row = ctk.CTkFrame(controls, fg_color='transparent')
        mod_row.pack(padx=14, pady=(4, 10), fill='x')
        self.mod_switch = ctk.CTkSwitch(mod_row, text='Modular',
                                        command=self._on_mod_toggle,
                                        font=('Segoe UI', 13))
        self.mod_switch.pack(side='left')
        self.mod_label = ctk.CTkLabel(mod_row, text=f'Mod M: {DEFAULT_MOD}',
                                      font=('Segoe UI', 13),
                                      text_color=MUTED, width=110, anchor='w')
        self.mod_label.pack(side='left', padx=(16, 0))
        self.mod_slider = ctk.CTkSlider(mod_row, from_=2, to=30,
                                        number_of_steps=28,
                                        command=self._on_mod_change)
        self.mod_slider.set(DEFAULT_MOD)
        self.mod_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Grid container fills the middle
        self.grid_frame = ctk.CTkFrame(self, fg_color=BG)
        self.grid_frame.pack(side='top', fill='both', expand=True,
                             padx=12, pady=(8, 4))

    def _on_n_change(self, value: float) -> None:
        new_n = int(round(value))
        if new_n != self.n:
            self.n = new_n
            self.n_label.configure(text=f'Size N: {self.n}')
            self._rebuild_grid()
        else:
            self.n_label.configure(text=f'Size N: {self.n}')

    def _on_mod_toggle(self) -> None:
        self.mod_enabled = bool(self.mod_switch.get())
        if self.mod_enabled:
            self.mod_label.configure(text_color=FG)
        else:
            self.mod_label.configure(text_color=MUTED)
        self._rebuild_grid()

    def _on_mod_change(self, value: float) -> None:
        new_m = int(round(value))
        if new_m != self.mod_value:
            self.mod_value = new_m
            self.mod_label.configure(text=f'Mod M: {self.mod_value}')
            if self.mod_enabled:
                self._rebuild_grid()
        else:
            self.mod_label.configure(text=f'Mod M: {self.mod_value}')

    def _rebuild_grid(self) -> None:
        # Clear previous cells
        for child in self.grid_frame.winfo_children():
            child.destroy()
        self.cells = []

        n = self.n
        # Cell size scales down as N grows.
        cell_w = max(22, min(56, 600 // (n + 1)))
        cell_h = max(20, min(40, 520 // (n + 1)))
        font_size = max(8, min(14, cell_w // 3))

        # Inner frame centered in grid_frame
        inner = ctk.CTkFrame(self.grid_frame, fg_color=BG)
        inner.pack(expand=True)

        if self.mod_enabled:
            mod = self.mod_value
            cells = [[(i * j) % mod for j in range(n)] for i in range(n)]
            row_range = range(n)
            col_range = range(n)
            row_labels = list(range(n))
            col_labels = list(range(n))
            mod_note = f' — mod {mod} ({"prime" if _is_prime(mod) else "composite"})'
        else:
            cells = [[i * j for j in range(1, n + 1)] for i in range(n)]
            row_range = range(n)
            col_range = range(n)
            row_labels = list(range(1, n + 1))
            col_labels = list(range(1, n + 1))
            mod_note = ''

        # Top-left corner cell
        corner = ctk.CTkLabel(inner, text='×', width=cell_w, height=cell_h,
                              fg_color=HEADER_BG, text_color=HEADER_FG,
                              corner_radius=4,
                              font=('Segoe UI', font_size, 'bold'))
        corner.grid(row=0, column=0, padx=1, pady=1)

        # Column headers
        for c, label in enumerate(col_labels, start=1):
            hdr = ctk.CTkLabel(inner, text=str(label),
                               width=cell_w, height=cell_h,
                               fg_color=HEADER_BG, text_color=HEADER_FG,
                               corner_radius=4,
                               font=('Segoe UI', font_size, 'bold'))
            hdr.grid(row=0, column=c, padx=1, pady=1)

        # Row headers + cells
        for r in row_range:
            row_widgets: list[ctk.CTkLabel] = []
            row_hdr = ctk.CTkLabel(inner, text=str(row_labels[r]),
                                   width=cell_w, height=cell_h,
                                   fg_color=HEADER_BG, text_color=HEADER_FG,
                                   corner_radius=4,
                                   font=('Segoe UI', font_size, 'bold'))
            row_hdr.grid(row=r + 1, column=0, padx=1, pady=1)

            for c in col_range:
                v = cells[r][c]
                if self.mod_enabled:
                    bg = modular_color(v, self.mod_value)
                else:
                    bg = heatmap_color(v, 1, n * n)
                # Pick legible foreground.
                fg = '#0f172a' if _is_light(bg) else '#f8fafc'
                cell = ctk.CTkLabel(inner, text=str(v),
                                    width=cell_w, height=cell_h,
                                    fg_color=bg, text_color=fg,
                                    corner_radius=4,
                                    font=('Segoe UI', font_size, 'bold'))
                cell.grid(row=r + 1, column=c + 1, padx=1, pady=1)
                row_widgets.append(cell)
            self.cells.append(row_widgets)

        self.status.configure(
            text=f'N={n}   {n * n} cells   max value '
                 f'{(self.mod_value - 1) if self.mod_enabled else n * n}'
                 f'{mod_note}')


def _light_value(hex_color: str) -> float:
    h = hex_color.lstrip('#')
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _is_light(hex_color: str) -> bool:
    return _light_value(hex_color) > 0.55


if __name__ == '__main__':
    MultTableApp().mainloop()
