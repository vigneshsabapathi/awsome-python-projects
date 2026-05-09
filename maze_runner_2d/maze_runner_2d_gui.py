"""Maze Runner 2D — CustomTkinter GUI.

A dark-themed desktop UI for the maze game. Walk with arrow keys (or WASD),
toggle the BFS shortest-path overlay, regenerate, swap generator algorithms,
and resize the maze with sliders.

Run:
    uv run python maze_runner_2d/maze_runner_2d_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from maze_runner_2d import ALGORITHMS, FLOOR, WALL, Maze, generate

# --- palette ---------------------------------------------------------------

BG_COLOR = '#0f172a'        # canvas/page background
WALL_COLOR = '#1e293b'      # wall block
FLOOR_COLOR = '#0f172a'     # floor / void
START_COLOR = '#22c55e'     # green
END_COLOR = '#ef4444'       # red
PLAYER_COLOR = '#facc15'    # amber
SOLUTION_COLOR = '#22d3ee'  # cyan trail
TEXT_COLOR = '#f8fafc'
MUTED = '#94a3b8'

CELL_PX = 22                # base size — recomputed to fit window
TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
STATUS_FONT = ('Segoe UI', 13)


class MazeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Maze Runner 2D')
        self.geometry('900x780')
        self.minsize(720, 640)
        self.configure(fg_color=BG_COLOR)

        self.rng = random.Random()
        self.cols_var = ctk.IntVar(value=15)
        self.rows_var = ctk.IntVar(value=11)
        self.algo_var = ctk.StringVar(value=ALGORITHMS[0])
        self.show_path = ctk.BooleanVar(value=False)
        self.maze: Maze = generate(self.cols_var.get(), self.rows_var.get(),
                                   self.rng, self.algo_var.get())
        self.cell_px: int = CELL_PX
        self.win_animation_after: str | None = None

        self._build_ui()
        self._bind_keys()
        self._redraw()

    # ----- ui -----------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='MAZE RUNNER 2D', font=TITLE_FONT,
                     text_color=TEXT_COLOR).pack(side='left')
        ctk.CTkLabel(header,
                     text='Arrow keys / WASD to move',
                     font=LABEL_FONT, text_color=MUTED).pack(side='left',
                                                              padx=(12, 0))

        # Bottom controls.
        controls = ctk.CTkFrame(self, fg_color='#111827', corner_radius=12)
        controls.pack(side='bottom', fill='x', padx=16, pady=(4, 14))

        # Row 1: status + buttons
        row1 = ctk.CTkFrame(controls, fg_color='transparent')
        row1.pack(fill='x', padx=12, pady=(10, 4))
        self.status = ctk.CTkLabel(row1, text='', font=STATUS_FONT,
                                   text_color=MUTED, anchor='w')
        self.status.pack(side='left', fill='x', expand=True)

        ctk.CTkButton(row1, text='New Maze', width=100,
                      fg_color='#334155', hover_color='#475569',
                      command=self._new_maze).pack(side='left', padx=4)
        self.path_btn = ctk.CTkButton(
            row1, text='Show Path', width=110,
            fg_color='#0e7490', hover_color='#0891b2',
            command=self._toggle_path)
        self.path_btn.pack(side='left', padx=4)

        # Row 2: sliders + algorithm picker.
        row2 = ctk.CTkFrame(controls, fg_color='transparent')
        row2.pack(fill='x', padx=12, pady=(4, 12))

        ctk.CTkLabel(row2, text='Width', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left')
        self.cols_slider = ctk.CTkSlider(
            row2, from_=5, to=35, number_of_steps=30,
            variable=self.cols_var, width=140,
            command=lambda _v: self._slider_changed())
        self.cols_slider.pack(side='left', padx=(6, 14))

        ctk.CTkLabel(row2, text='Height', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left')
        self.rows_slider = ctk.CTkSlider(
            row2, from_=5, to=25, number_of_steps=20,
            variable=self.rows_var, width=140,
            command=lambda _v: self._slider_changed())
        self.rows_slider.pack(side='left', padx=(6, 14))

        ctk.CTkLabel(row2, text='Algorithm', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left')
        self.algo_menu = ctk.CTkOptionMenu(
            row2, variable=self.algo_var, values=list(ALGORITHMS),
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b',
            command=lambda _v: self._new_maze())
        self.algo_menu.pack(side='left', padx=(6, 0))

        # Canvas — fills remaining space.
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0,
                                bd=0)
        self.canvas.pack(side='top', fill='both', expand=True,
                         padx=16, pady=(8, 4))
        self.canvas.bind('<Configure>', lambda _e: self._redraw())

    def _bind_keys(self) -> None:
        for key, direction in (('<Up>', 'up'), ('<Down>', 'down'),
                               ('<Left>', 'left'), ('<Right>', 'right'),
                               ('w', 'up'), ('s', 'down'),
                               ('a', 'left'), ('d', 'right'),
                               ('W', 'up'), ('S', 'down'),
                               ('A', 'left'), ('D', 'right')):
            self.bind(key, lambda _e, d=direction: self._handle_move(d))
        self.bind('n', lambda _e: self._new_maze())
        self.bind('N', lambda _e: self._new_maze())
        self.bind('p', lambda _e: self._toggle_path())
        self.bind('P', lambda _e: self._toggle_path())
        # Make sure key events reach us even if a widget grabbed focus.
        self.after(50, self.focus_set)

    # ----- state changes ------------------------------------------------

    def _slider_changed(self) -> None:
        # Live-update the text without regenerating; new maze on release.
        self._set_status_default()
        self._new_maze()

    def _new_maze(self) -> None:
        cols = max(2, int(self.cols_var.get()))
        rows = max(2, int(self.rows_var.get()))
        self.maze = generate(cols, rows, self.rng, self.algo_var.get())
        self.show_path.set(False)
        self.path_btn.configure(text='Show Path', fg_color='#0e7490')
        self._redraw()

    def _toggle_path(self) -> None:
        self.show_path.set(not self.show_path.get())
        if self.show_path.get():
            self.path_btn.configure(text='Hide Path', fg_color='#0891b2')
        else:
            self.path_btn.configure(text='Show Path', fg_color='#0e7490')
        self._redraw()

    def _handle_move(self, direction: str) -> bool:
        if self.maze.won:
            return False
        moved = self.maze.move(direction)
        if moved:
            self._redraw()
            if self.maze.won:
                self._on_win()
        return moved

    def _on_win(self) -> None:
        self._set_status('You reached the exit! Press N for a new maze.',
                         color=START_COLOR)
        self._flash_win()

    def _flash_win(self, count: int = 0) -> None:
        # Briefly pulse the player marker after winning.
        if count >= 6:
            self._redraw()
            return
        color = PLAYER_COLOR if count % 2 == 0 else START_COLOR
        self.canvas.itemconfigure('player', fill=color)
        self.win_animation_after = self.after(
            150, lambda: self._flash_win(count + 1))

    # ----- rendering ----------------------------------------------------

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, text_color=color)

    def _set_status_default(self) -> None:
        steps = max(0, len(self.maze.solve()) - 1)
        self._set_status(
            f'{self.maze.width}x{self.maze.height} cells  -  '
            f'algorithm: {self.algo_var.get()}  -  '
            f'shortest remaining: {steps} steps')

    def _compute_cell_px(self) -> int:
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        gw = self.maze.gw
        gh = self.maze.gh
        # Floor to int, leave a 1-px margin.
        return max(6, min((cw - 4) // gw, (ch - 4) // gh))

    def _redraw(self) -> None:
        self.canvas.delete('all')
        self.cell_px = self._compute_cell_px()
        cp = self.cell_px
        gw = self.maze.gw
        gh = self.maze.gh

        # Center the grid in the canvas.
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        ox = (cw - gw * cp) // 2
        oy = (ch - gh * cp) // 2

        # Walls + floor.
        for y in range(gh):
            for x in range(gw):
                ch_at = self.maze.grid[y][x]
                color = WALL_COLOR if ch_at == WALL else FLOOR_COLOR
                self.canvas.create_rectangle(
                    ox + x * cp, oy + y * cp,
                    ox + (x + 1) * cp, oy + (y + 1) * cp,
                    fill=color, outline='')

        # Solution overlay.
        if self.show_path.get():
            for x, y in self.maze.solve():
                if (x, y) in (self.maze.start, self.maze.end,
                              self.maze.player):
                    continue
                pad = max(2, cp // 4)
                self.canvas.create_rectangle(
                    ox + x * cp + pad, oy + y * cp + pad,
                    ox + (x + 1) * cp - pad,
                    oy + (y + 1) * cp - pad,
                    fill=SOLUTION_COLOR, outline='')

        # Start, end, player.
        self._draw_marker(ox, oy, *self.maze.start, START_COLOR, '')
        self._draw_marker(ox, oy, *self.maze.end, END_COLOR, '')
        self._draw_marker(ox, oy, *self.maze.player, PLAYER_COLOR, 'player')

        # Status.
        if self.maze.won:
            self._set_status('You reached the exit! Press N for a new maze.',
                             color=START_COLOR)
        else:
            self._set_status_default()

    def _draw_marker(self, ox: int, oy: int, x: int, y: int,
                     color: str, tag: str) -> None:
        cp = self.cell_px
        pad = max(2, cp // 6)
        self.canvas.create_oval(
            ox + x * cp + pad, oy + y * cp + pad,
            ox + (x + 1) * cp - pad, oy + (y + 1) * cp - pad,
            fill=color, outline='', tags=(tag,) if tag else ())


if __name__ == '__main__':
    MazeApp().mainloop()
