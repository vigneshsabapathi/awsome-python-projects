"""Periodic Table - CustomTkinter GUI.

Dark-theme desktop app showing all 118 elements arranged in the standard
periodic-table layout. Tiles are color-coded by category and clickable;
selecting a tile populates a details panel on the right.

Run:
    uv run python periodic_table/periodic_table_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from periodic_table import (
    CATEGORIES,
    ELEMENTS,
    Element,
    build_grid,
    lookup,
    search,
)


# Category fills tuned for a dark theme. (bg, fg) per category.
CAT_COLORS: dict[str, tuple[str, str]] = {
    'alkali':            ('#dc2626', '#fef2f2'),
    'alkaline-earth':    ('#ea580c', '#fff7ed'),
    'transition':        ('#0284c7', '#f0f9ff'),
    'post-transition':   ('#475569', '#f8fafc'),
    'metalloid':         ('#0d9488', '#ecfdf5'),
    'nonmetal':          ('#16a34a', '#f0fdf4'),
    'halogen':           ('#0891b2', '#ecfeff'),
    'noble-gas':         ('#7c3aed', '#f5f3ff'),
    'lanthanide':        ('#db2777', '#fdf2f8'),
    'actinide':          ('#be185d', '#fdf2f8'),
    'unknown':           ('#52525b', '#fafafa'),
}

# Layout constants
TILE_W = 56
TILE_H = 56
GAP = 2
SYMBOL_FONT = ('Segoe UI', 13, 'bold')
NUMBER_FONT = ('Segoe UI', 8)
TITLE_FONT = ('Segoe UI', 24, 'bold')
HEADER_FONT = ('Segoe UI', 13, 'bold')
DETAIL_FONT = ('Segoe UI', 12)


class PeriodicTableApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Periodic Table')
        self.geometry('1280x780')
        self.minsize(1100, 700)
        self.configure(fg_color='#0f172a')

        self.tiles: dict[int, ctk.CTkFrame] = {}
        self.selected: Element | None = None

        self._build_ui()
        # Highlight Hydrogen by default.
        self._select(lookup(1))

    # ----------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(14, 6))
        ctk.CTkLabel(header, text='PERIODIC TABLE',
                     font=TITLE_FONT, text_color='#f8fafc').pack(side='left')
        ctk.CTkLabel(header, text=f'  {len(ELEMENTS)} elements',
                     font=DETAIL_FONT,
                     text_color='#94a3b8').pack(side='left', pady=(6, 0))

        # Search box
        self.search_var = ctk.StringVar()
        self.search_var.trace_add('write', lambda *_: self._on_search())
        search_box = ctk.CTkEntry(
            header, textvariable=self.search_var,
            placeholder_text='Search by name, symbol, number, or category...',
            width=320, height=32, font=DETAIL_FONT)
        search_box.pack(side='right')

        # Main body: table on the left, details panel on the right.
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(0, 14))

        table_wrap = ctk.CTkFrame(body, fg_color='#111827',
                                  corner_radius=12)
        table_wrap.pack(side='left', fill='both', expand=True, padx=(0, 12))

        self.detail = self._build_detail(body)
        self.detail.pack(side='right', fill='y')

        self._build_table(table_wrap)
        self._build_legend(table_wrap)

    def _build_table(self, parent: ctk.CTkFrame) -> None:
        grid = build_grid()
        table = ctk.CTkFrame(parent, fg_color='transparent')
        table.pack(padx=14, pady=(14, 6))

        for r, row in enumerate(grid):
            if r == 7:  # spacer row between main table and lanthanides
                spacer = ctk.CTkFrame(table, fg_color='transparent',
                                      width=TILE_W, height=12)
                spacer.grid(row=r, column=0, columnspan=18)
                continue
            for c, e in enumerate(row):
                if e is None:
                    placeholder = ctk.CTkFrame(
                        table, width=TILE_W, height=TILE_H,
                        fg_color='transparent')
                    placeholder.grid(row=r, column=c,
                                     padx=GAP, pady=GAP)
                    placeholder.grid_propagate(False)
                    continue
                tile = self._make_tile(table, e)
                tile.grid(row=r, column=c, padx=GAP, pady=GAP)
                self.tiles[e.number] = tile

    def _make_tile(self, parent: ctk.CTkFrame, e: Element) -> ctk.CTkFrame:
        bg, fg = CAT_COLORS.get(e.category, CAT_COLORS['unknown'])
        tile = ctk.CTkFrame(parent, width=TILE_W, height=TILE_H,
                            fg_color=bg, corner_radius=6,
                            border_width=0)
        tile.grid_propagate(False)
        # Use pack inside the tile for two stacked labels.
        num = ctk.CTkLabel(tile, text=str(e.number),
                           font=NUMBER_FONT, text_color=fg,
                           fg_color='transparent')
        num.place(x=4, y=2)
        sym = ctk.CTkLabel(tile, text=e.symbol,
                           font=SYMBOL_FONT, text_color=fg,
                           fg_color='transparent')
        sym.place(relx=0.5, rely=0.55, anchor='center')

        def _on_click(_event=None, elem=e):
            self._select(elem)

        for w in (tile, num, sym):
            w.bind('<Button-1>', _on_click)
            w.configure(cursor='hand2')
        return tile

    def _build_legend(self, parent: ctk.CTkFrame) -> None:
        legend = ctk.CTkFrame(parent, fg_color='transparent')
        legend.pack(padx=14, pady=(4, 14), anchor='w')
        for i, (key, label) in enumerate(CATEGORIES.items()):
            bg, fg = CAT_COLORS.get(key, CAT_COLORS['unknown'])
            chip = ctk.CTkLabel(legend, text=f'  {label}  ',
                                fg_color=bg, text_color=fg,
                                corner_radius=10,
                                font=('Segoe UI', 10, 'bold'))
            chip.grid(row=i // 6, column=i % 6, padx=4, pady=2, sticky='w')

    def _build_detail(self, parent: ctk.CTkFrame) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent, fg_color='#111827', corner_radius=12,
                             width=360)
        panel.pack_propagate(False)

        self._d_chip = ctk.CTkLabel(panel, text='', fg_color='#1f2937',
                                    text_color='#f8fafc',
                                    corner_radius=8,
                                    font=('Segoe UI', 11, 'bold'))
        self._d_chip.pack(anchor='w', padx=18, pady=(20, 8))

        self._d_symbol = ctk.CTkLabel(panel, text='--',
                                      font=('Segoe UI', 64, 'bold'),
                                      text_color='#f8fafc')
        self._d_symbol.pack(padx=18, pady=(2, 0))

        self._d_name = ctk.CTkLabel(panel, text='--',
                                    font=('Segoe UI', 22, 'bold'),
                                    text_color='#f8fafc')
        self._d_name.pack(padx=18, pady=(0, 4))

        self._d_number = ctk.CTkLabel(panel, text='Atomic #--',
                                      font=DETAIL_FONT,
                                      text_color='#94a3b8')
        self._d_number.pack(padx=18, pady=(0, 14))

        sep = ctk.CTkFrame(panel, height=1, fg_color='#1f2937')
        sep.pack(fill='x', padx=18, pady=4)

        self._d_rows: dict[str, ctk.CTkLabel] = {}
        for key in ('Atomic Weight', 'Period', 'Group',
                    'Electron Config'):
            row = ctk.CTkFrame(panel, fg_color='transparent')
            row.pack(fill='x', padx=18, pady=4)
            ctk.CTkLabel(row, text=key, font=HEADER_FONT,
                         text_color='#94a3b8',
                         width=130, anchor='w').pack(side='left')
            val = ctk.CTkLabel(row, text='--', font=DETAIL_FONT,
                               text_color='#f8fafc',
                               anchor='w', justify='left',
                               wraplength=200)
            val.pack(side='left', fill='x', expand=True)
            self._d_rows[key] = val

        # Hint text at the bottom
        hint = ctk.CTkLabel(
            panel,
            text='Click any tile to inspect.\nUse the search box above\nto filter.',
            font=('Segoe UI', 10), text_color='#475569',
            justify='left')
        hint.pack(side='bottom', anchor='w', padx=18, pady=14)
        return panel

    # ----------------------------------------------------------- behavior

    def _select(self, e: Element) -> None:
        # Clear previous border highlight
        if self.selected is not None:
            prev = self.tiles.get(self.selected.number)
            if prev is not None:
                prev.configure(border_width=0)
        self.selected = e
        tile = self.tiles.get(e.number)
        if tile is not None:
            tile.configure(border_width=2, border_color='#f8fafc')

        bg, fg = CAT_COLORS.get(e.category, CAT_COLORS['unknown'])
        self._d_chip.configure(text=f'  {CATEGORIES[e.category]}  ',
                               fg_color=bg, text_color=fg)
        self._d_symbol.configure(text=e.symbol)
        self._d_name.configure(text=e.name)
        self._d_number.configure(text=f'Atomic #{e.number}')
        self._d_rows['Atomic Weight'].configure(text=f'{e.weight} u')
        self._d_rows['Period'].configure(text=str(e.period))
        self._d_rows['Group'].configure(
            text=str(e.group) if e.group else '- (f-block)')
        self._d_rows['Electron Config'].configure(text=e.config)

    def _on_search(self) -> None:
        term = self.search_var.get().strip()
        # Auto-jump to a single direct hit (number/symbol/name).
        if term:
            try:
                e = lookup(term)
                self._select(e)
            except KeyError:
                pass

        # Dim non-matching tiles.
        if not term:
            matching = set(e.number for e in ELEMENTS)
        else:
            matching = set(e.number for e in search(term))
        for num, tile in self.tiles.items():
            e = lookup(num)
            bg, _fg = CAT_COLORS.get(e.category, CAT_COLORS['unknown'])
            if num in matching or not term:
                tile.configure(fg_color=bg)
            else:
                tile.configure(fg_color='#1f2937')


if __name__ == '__main__':
    PeriodicTableApp().mainloop()
