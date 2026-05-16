"""Flooder — CustomTkinter GUI.

Dark-theme desktop UI with a tk.Canvas grid.  Color buttons at the bottom,
moves counter, win/lose indicator, greedy-hint button, and a new-game button.

Run:
    uv run python flooder/flooder_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from flooder import DEFAULT_COLORS, DEFAULT_HEIGHT, DEFAULT_MOVES, DEFAULT_WIDTH, Game

# --- Layout constants --------------------------------------------------------
CELL_SIZE = 36
BUTTON_H = 38
GAP = 4

# --- Color palette (Tailwind-inspired dark palette) --------------------------
# Each entry: (hex fill, hex text)
COLOR_PALETTE = [
    ('#ef4444', '#ffffff'),  # 0 red
    ('#22c55e', '#ffffff'),  # 1 green
    ('#eab308', '#1f2937'),  # 2 yellow
    ('#3b82f6', '#ffffff'),  # 3 blue
    ('#a855f7', '#ffffff'),  # 4 purple
    ('#06b6d4', '#1f2937'),  # 5 cyan
]
COLOR_NAMES = ['Red', 'Green', 'Yellow', 'Blue', 'Purple', 'Cyan']

BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
GRID_BG = '#020617'
GRID_LINE = '#1e293b'
LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 20, 'bold')
STAT_FONT = ('Consolas', 12)


class FlooderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Flooder')
        self.configure(fg_color=BG)
        self.resizable(False, False)

        self._game = Game(DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_COLORS,
                          max_moves=DEFAULT_MOVES)
        # Cache canvas item ids
        self._cell_items: list[list[int]] = []

        self._build_ui()
        self._draw_grid_initial()
        self._refresh()

        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = self.winfo_reqwidth(), self.winfo_reqheight()
        self.geometry(f'+{(sw - w) // 2}+{(sh - h) // 2}')

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Title row
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=16, pady=(12, 4))
        ctk.CTkLabel(header, text='FLOODER', font=TITLE_FONT,
                     text_color='#f8fafc').pack(side='left')
        self.stat_label = ctk.CTkLabel(
            header, text='', font=STAT_FONT, text_color='#94a3b8')
        self.stat_label.pack(side='right')

        # Canvas
        canvas_w = DEFAULT_WIDTH * CELL_SIZE
        canvas_h = DEFAULT_HEIGHT * CELL_SIZE
        canvas_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                    border_width=1, border_color=BORDER)
        canvas_frame.pack(side='top', padx=16, pady=8)
        self.canvas = tk.Canvas(canvas_frame, width=canvas_w, height=canvas_h,
                                bg=GRID_BG, highlightthickness=0, bd=0)
        self.canvas.pack(padx=8, pady=8)

        # Status label (win/lose message)
        self.status_label = ctk.CTkLabel(
            self, text='', font=('Segoe UI', 14, 'bold'), text_color='#34d399')
        self.status_label.pack(side='top', pady=(0, 4))

        # Color buttons row
        color_row = ctk.CTkFrame(self, fg_color='transparent')
        color_row.pack(side='top', padx=16, pady=(0, 4))
        self._color_btns: list[ctk.CTkButton] = []
        for i in range(DEFAULT_COLORS):
            fill, text_c = COLOR_PALETTE[i]
            btn = ctk.CTkButton(
                color_row,
                text=f'{i + 1} {COLOR_NAMES[i]}',
                width=90, height=BUTTON_H,
                fg_color=fill,
                hover_color=fill,
                text_color=text_c,
                font=('Segoe UI', 12, 'bold'),
                command=lambda c=i: self._on_color(c),
            )
            btn.pack(side='left', padx=4)
            self._color_btns.append(btn)

        # Controls row
        ctrl_row = ctk.CTkFrame(self, fg_color='transparent')
        ctrl_row.pack(side='top', padx=16, pady=(4, 12))
        self.hint_btn = ctk.CTkButton(
            ctrl_row, text='Hint (greedy)', width=110, height=32,
            fg_color='#0ea5e9', hover_color='#0284c7',
            command=self._show_hint)
        self.hint_btn.pack(side='left', padx=4)
        ctk.CTkButton(
            ctrl_row, text='New Game', width=100, height=32,
            fg_color='#334155', hover_color='#475569',
            command=self._new_game).pack(side='left', padx=4)

        ctk.CTkLabel(
            self,
            text='Click a color button (or press 1-6) to flood',
            font=('Segoe UI', 11), text_color='#64748b',
        ).pack(side='top', pady=(0, 8))

        # Keyboard shortcuts
        self.bind('<Key>', self._on_key)

    # ------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------

    def _draw_grid_initial(self) -> None:
        self.canvas.delete('all')
        self._cell_items = []
        for r in range(DEFAULT_HEIGHT):
            row_items: list[int] = []
            for c in range(DEFAULT_WIDTH):
                x0 = c * CELL_SIZE
                y0 = r * CELL_SIZE
                item = self.canvas.create_rectangle(
                    x0, y0, x0 + CELL_SIZE, y0 + CELL_SIZE,
                    fill=GRID_BG, outline=GRID_LINE, width=1)
                row_items.append(item)
            self._cell_items.append(row_items)

    def _refresh(self) -> None:
        st = self._game.state()
        grid = st['grid']
        total = DEFAULT_WIDTH * DEFAULT_HEIGHT
        for r in range(DEFAULT_HEIGHT):
            for c in range(DEFAULT_WIDTH):
                fill = COLOR_PALETTE[grid[r][c]][0]
                self.canvas.itemconfigure(self._cell_items[r][c], fill=fill)

        self.stat_label.configure(
            text=f'Moves left: {st["moves_left"]} / {self._game.max_moves}  '
                 f'Region: {st["region_size"]}/{total}')

        if st['is_won']:
            self.status_label.configure(
                text=f'YOU WIN!  Completed in {self._game._moves_used} moves',
                text_color='#34d399')
            self._disable_color_btns()
        elif st['is_lost']:
            self.status_label.configure(
                text='OUT OF MOVES — Game over!', text_color='#f87171')
            self._disable_color_btns()
        else:
            self.status_label.configure(text='')
            self._enable_color_btns()

        # Highlight current-color button
        current = grid[0][0]
        for i, btn in enumerate(self._color_btns):
            if i == current:
                btn.configure(border_width=3, border_color='#f8fafc')
            else:
                btn.configure(border_width=0)

    def _disable_color_btns(self) -> None:
        for btn in self._color_btns:
            btn.configure(state='disabled')

    def _enable_color_btns(self) -> None:
        for btn in self._color_btns:
            btn.configure(state='normal')

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_color(self, color: int) -> None:
        self._game.flood(color)
        self._refresh()

    def _on_key(self, event: tk.Event) -> None:
        if event.char.isdigit():
            idx = int(event.char) - 1
            if 0 <= idx < DEFAULT_COLORS:
                self._on_color(idx)
        elif event.char.lower() == 'n':
            self._new_game()
        elif event.char.lower() == 'h':
            self._show_hint()

    def _show_hint(self) -> None:
        hint = self._game.greedy_hint()
        name = COLOR_NAMES[hint]
        fill, _ = COLOR_PALETTE[hint]
        self.status_label.configure(
            text=f'Hint: try {hint + 1} {name}', text_color=fill)

    def _new_game(self) -> None:
        self._game = Game(DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_COLORS,
                          max_moves=DEFAULT_MOVES)
        self._draw_grid_initial()
        self._refresh()


if __name__ == '__main__':
    FlooderApp().mainloop()
