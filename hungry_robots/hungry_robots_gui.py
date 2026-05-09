"""Hungry Robots — CustomTkinter GUI.

Dark-themed desktop UI for the chase grid. The board is a ``tk.Canvas`` so
each cell is a coloured rectangle (player blue, robots red, wrecks grey,
empty very dark). A 3x3 numpad of buttons drives the eight directions plus
a centre 'wait', flanked by Teleport / Safe Teleport / Wait-out / New.

Run:
    uv run python hungry_robots/hungry_robots_gui.py
"""
from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from hungry_robots import (
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    EMPTY,
    PLAYER,
    ROBOT,
    START_ROBOTS,
    WRECK,
    Game,
)

# Visual palette — kept consistent with the bagels GUI for repo continuity.
BG = '#0f172a'
GRID_BG = '#020617'
LINE = '#1e293b'
TEXT = '#f8fafc'
SUBTEXT = '#94a3b8'
COLORS = {
    EMPTY:  '#0b1220',
    PLAYER: '#38bdf8',  # sky blue
    ROBOT:  '#ef4444',  # red
    WRECK:  '#475569',  # slate grey
}

CELL_PX = 22  # square cell size — adjust for higher-DPI displays


class HungryRobotsApp(ctk.CTk):
    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        n_robots: int = START_ROBOTS,
    ) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Hungry Robots')
        self.configure(fg_color=BG)
        self.minsize(640, 560)

        self.board_w = width
        self.board_h = height
        self.start_robots = n_robots
        self.game = Game(width, height, n_robots)

        self._build_ui()
        self._draw_board()
        self._refresh_status()
        # Keyboard parity with the TUI — numpad / hjkl-style directions.
        self.bind('<Key>', self._on_key)
        self.focus_set()

    # ----------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        title = ctk.CTkLabel(
            self, text='HUNGRY ROBOTS', font=('Segoe UI', 24, 'bold'),
            text_color=TEXT)
        title.pack(side='top', pady=(14, 0))

        self.subtitle = ctk.CTkLabel(
            self, text='', font=('Segoe UI', 12), text_color=SUBTEXT)
        self.subtitle.pack(side='top', pady=(2, 8))

        # Canvas board — sized to the grid; resizing the window doesn't
        # rescale, but the canvas centers nicely inside the frame.
        canvas_w = self.board_w * CELL_PX
        canvas_h = self.board_h * CELL_PX
        canvas_frame = ctk.CTkFrame(self, fg_color=GRID_BG, corner_radius=10)
        canvas_frame.pack(side='top', padx=16, pady=8)
        self.canvas = tk.Canvas(
            canvas_frame, width=canvas_w, height=canvas_h,
            bg=GRID_BG, highlightthickness=0, bd=0)
        self.canvas.pack(padx=8, pady=8)

        # Status bar lives just below the board.
        self.status = ctk.CTkLabel(
            self, text='', font=('Segoe UI', 13), text_color=TEXT)
        self.status.pack(side='top', pady=(4, 0))
        self.event_label = ctk.CTkLabel(
            self, text='', font=('Segoe UI', 12), text_color=SUBTEXT)
        self.event_label.pack(side='top', pady=(0, 6))

        # Controls row — numpad on the left, action buttons on the right.
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='top', pady=(4, 14))

        numpad = ctk.CTkFrame(controls, fg_color='transparent')
        numpad.grid(row=0, column=0, padx=(0, 24))
        # 3x3 grid: rows = up/mid/down, cols = left/centre/right.
        layout = [
            ('NW', -1, -1, 0, 0), ('N', 0, -1, 0, 1), ('NE', 1, -1, 0, 2),
            ('W', -1, 0, 1, 0),   ('Wait', 0, 0, 1, 1), ('E', 1, 0, 1, 2),
            ('SW', -1, 1, 1, 0),  ('S', 0, 1, 1, 1), ('SE', 1, 1, 1, 2),
        ]
        # Arrange properly: rows 0/1/2 by y direction.
        for label, dx, dy, _, col in layout:
            row = {-1: 0, 0: 1, 1: 2}[dy]
            btn = ctk.CTkButton(
                numpad, text=label, width=64, height=40,
                fg_color='#1e293b', hover_color='#334155',
                command=lambda x=dx, y=dy: self._do_move(x, y))
            btn.grid(row=row, column=col, padx=3, pady=3)

        actions = ctk.CTkFrame(controls, fg_color='transparent')
        actions.grid(row=0, column=1)
        self.tele_btn = ctk.CTkButton(
            actions, text='Teleport (t)', width=140,
            fg_color='#7c3aed', hover_color='#6d28d9',
            command=self._do_teleport)
        self.tele_btn.grid(row=0, column=0, padx=4, pady=3)
        self.safe_btn = ctk.CTkButton(
            actions, text='Safe Teleport (T)', width=140,
            fg_color='#0891b2', hover_color='#0e7490',
            command=self._do_safe_teleport)
        self.safe_btn.grid(row=0, column=1, padx=4, pady=3)
        self.waitout_btn = ctk.CTkButton(
            actions, text='Wait Out (W)', width=140,
            fg_color='#f59e0b', hover_color='#d97706', text_color='#0f172a',
            command=self._do_wait_out)
        self.waitout_btn.grid(row=1, column=0, padx=4, pady=3)
        self.new_btn = ctk.CTkButton(
            actions, text='New / Next', width=140,
            fg_color='#16a34a', hover_color='#15803d',
            command=self._new_game)
        self.new_btn.grid(row=1, column=1, padx=4, pady=3)

    # ----------------------------------------------------------------- draw

    def _draw_board(self) -> None:
        self.canvas.delete('all')
        for y in range(self.board_h):
            for x in range(self.board_w):
                glyph = self.game.cell(x, y)
                color = COLORS[glyph]
                x0 = x * CELL_PX
                y0 = y * CELL_PX
                self.canvas.create_rectangle(
                    x0, y0, x0 + CELL_PX, y0 + CELL_PX,
                    fill=color, outline=LINE)
                # Subtle glyph overlays for accessibility / colour-blind play.
                if glyph == PLAYER:
                    self._draw_token(x0, y0, '@', '#ffffff')
                elif glyph == ROBOT:
                    self._draw_token(x0, y0, 'R', '#fee2e2')
                elif glyph == WRECK:
                    self._draw_token(x0, y0, '#', '#cbd5e1')

    def _draw_token(self, x0: int, y0: int, text: str, color: str) -> None:
        self.canvas.create_text(
            x0 + CELL_PX // 2, y0 + CELL_PX // 2,
            text=text, fill=color, font=('Consolas', 12, 'bold'))

    def _refresh_status(self) -> None:
        self.subtitle.configure(
            text=f'Level {self.game.level} — chase the wrecks, dodge the robots')
        self.status.configure(
            text=(f'Robots: {len(self.game.robots)}   '
                  f'Wrecks: {len(self.game.wrecks)}   '
                  f'Teleports: {self.game.teleports}   '
                  f'Safe: {self.game.safe_teleports}'))
        if self.game.is_won():
            self.event_label.configure(
                text='Victory! Press New / Next for the next level.',
                text_color='#34d399')
        elif self.game.is_lost():
            self.event_label.configure(
                text='A robot caught you. New / Next restarts the run.',
                text_color='#f87171')

    # ----------------------------------------------------------------- actions

    def _do_move(self, dx: int, dy: int) -> None:
        if self.game.is_won() or self.game.is_lost():
            return
        ev = self.game.move_player(dx, dy)
        self._post_action(ev)

    def _do_teleport(self) -> None:
        ev = self.game.teleport()
        self._post_action(ev)

    def _do_safe_teleport(self) -> None:
        ev = self.game.safe_teleport()
        self._post_action(ev)

    def _do_wait_out(self) -> None:
        ev = self.game.wait_until_safe_or_dead()
        self._post_action(ev)

    def _post_action(self, ev: dict) -> None:
        self._draw_board()
        if ev.get('message'):
            self.event_label.configure(text=ev['message'], text_color=SUBTEXT)
        elif ev.get('killed'):
            self.event_label.configure(
                text=f"Crushed {ev['killed']} robot(s)", text_color='#fbbf24')
        else:
            self.event_label.configure(text='', text_color=SUBTEXT)
        self._refresh_status()

    def _new_game(self) -> None:
        if self.game.is_won():
            self.game.next_level()
        else:
            self.game = Game(self.board_w, self.board_h, self.start_robots)
        self._draw_board()
        self.event_label.configure(text='', text_color=SUBTEXT)
        self._refresh_status()

    # ----------------------------------------------------------------- input

    def _on_key(self, event: tk.Event) -> None:
        # Keysym lets us treat 'shift+t' separately from 't'.
        keysym = event.keysym
        # Letter directions: hjkl + yubn (vim-style) and qweadzxc (numpad).
        key_map = {
            'h': (-1, 0), 'l': (1, 0), 'k': (0, -1), 'j': (0, 1),
            'y': (-1, -1), 'u': (1, -1), 'b': (-1, 1), 'n': (1, 1),
            'q': (-1, -1), 'w': (0, -1), 'e': (1, -1),
            'a': (-1, 0), 'd': (1, 0),
            'z': (-1, 1), 'x': (0, 1), 'c': (1, 1),
        }
        if keysym in key_map:
            dx, dy = key_map[keysym]
            self._do_move(dx, dy)
            return
        # Single-character actions — distinguish T (safe) from t (regular).
        ch = event.char
        if ch == 't':
            self._do_teleport()
        elif ch == 'T':
            self._do_safe_teleport()
        elif ch == 'W':
            self._do_wait_out()
        elif ch == 's':
            self._do_move(0, 0)
        elif keysym == 'F2':
            self._new_game()


def main() -> None:
    HungryRobotsApp().mainloop()


if __name__ == '__main__':
    main()
