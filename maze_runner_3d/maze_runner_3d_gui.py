"""Maze Runner 3D — CustomTkinter dark-theme GUI.

A desktop window with a big monospace ASCII first-person viewport,
arrow-button controls, a status bar, and a corner mini-map.

Run:
    uv run python maze_runner_3d/maze_runner_3d_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from maze_runner_3d import (
    generate,
    maybe_monster_overlay,
    move,
    render_first_person,
    render_minimap,
    _find_goal,
)


VIEW_FONT = ('Consolas', 18, 'bold')
MAP_FONT = ('Consolas', 12)
TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 13)
STATUS_FONT = ('Segoe UI', 14)
BTN_FONT = ('Segoe UI', 14, 'bold')


class MazeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Maze Runner 3D')
        self.geometry('760x720')
        self.minsize(720, 680)
        self.configure(fg_color='#0f172a')

        self.rng = random.Random()
        self.size = 13
        self.torch_radius = 4
        self.maze = generate(self.size, self.size, self.rng)
        self.x, self.y, self.facing = 1, 1, 'E'
        self.goal = _find_goal(self.maze, (self.x, self.y))
        self.show_map = True
        self.game_over = False

        self._build_ui()
        self._refresh()

        # Keyboard bindings — w/a/s/d plus arrows for ergonomics.
        for key, action in (('w', 'w'), ('s', 's'), ('a', 'a'), ('d', 'd'),
                            ('Up', 'w'), ('Down', 's'),
                            ('Left', 'a'), ('Right', 'd')):
            self.bind(f'<{key}>', lambda _e, a=action: self._do_move(a))
        self.bind('<m>', lambda _e: self._toggle_map())
        self.bind('<n>', lambda _e: self._new_maze())

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='MAZE RUNNER 3D', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(
            header,
            text='Find the exit — w/a/s/d or arrow keys, m toggles map',
            font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Bottom: status + new-game button.
        self.new_btn = ctk.CTkButton(self, text='New Maze (n)',
                                     fg_color='#334155', hover_color='#475569',
                                     command=self._new_maze)
        self.new_btn.pack(side='bottom', pady=(6, 12))

        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='bottom', pady=(2, 0))

        # Control pad (arrow buttons) — packed bottom so it stays visible.
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='bottom', pady=(8, 4))
        # Layout: a 3x3 grid where forward sits on top, left/back/right below.
        ctk.CTkButton(controls, text='Forward (w)', width=140, height=42,
                      font=BTN_FONT, command=lambda: self._do_move('w')
                      ).grid(row=0, column=1, padx=4, pady=4)
        ctk.CTkButton(controls, text='Turn L (a)', width=120, height=42,
                      font=BTN_FONT, command=lambda: self._do_move('a')
                      ).grid(row=1, column=0, padx=4, pady=4)
        ctk.CTkButton(controls, text='Back (s)', width=120, height=42,
                      font=BTN_FONT, command=lambda: self._do_move('s')
                      ).grid(row=1, column=1, padx=4, pady=4)
        ctk.CTkButton(controls, text='Turn R (d)', width=120, height=42,
                      font=BTN_FONT, command=lambda: self._do_move('d')
                      ).grid(row=1, column=2, padx=4, pady=4)
        ctk.CTkButton(controls, text='Toggle Map (m)', width=380, height=34,
                      font=('Segoe UI', 12),
                      fg_color='#1e293b', hover_color='#334155',
                      command=self._toggle_map
                      ).grid(row=2, column=0, columnspan=3, padx=4, pady=4)

        # Center: viewport + minimap side-by-side.
        center = ctk.CTkFrame(self, fg_color='transparent')
        center.pack(side='top', pady=8, padx=12, fill='both', expand=True)

        viewport_frame = ctk.CTkFrame(center, fg_color='#020617',
                                      corner_radius=12)
        viewport_frame.pack(side='left', padx=(4, 8), pady=4,
                            fill='both', expand=True)
        self.viewport = ctk.CTkLabel(viewport_frame, text='', font=VIEW_FONT,
                                     text_color='#e2e8f0', justify='left',
                                     anchor='nw')
        self.viewport.pack(padx=14, pady=14, fill='both', expand=True)

        map_frame = ctk.CTkFrame(center, fg_color='#020617',
                                 corner_radius=12, width=240)
        map_frame.pack(side='left', padx=(8, 4), pady=4, fill='y')
        map_frame.pack_propagate(False)
        ctk.CTkLabel(map_frame, text='MAP', font=('Segoe UI', 12, 'bold'),
                     text_color='#94a3b8').pack(pady=(8, 2))
        self.map_label = ctk.CTkLabel(map_frame, text='', font=MAP_FONT,
                                      text_color='#cbd5e1', justify='left')
        self.map_label.pack(padx=10, pady=4)

    # ---------- actions ----------

    def _do_move(self, action: str) -> None:
        if self.game_over:
            return
        self.x, self.y, self.facing = move(
            self.maze, self.x, self.y, self.facing, action)
        self._refresh()
        if (self.x, self.y) == self.goal:
            self._set_status('You found the exit! Press n for a new maze.',
                             '#34d399')
            self.game_over = True

    def _toggle_map(self) -> None:
        self.show_map = not self.show_map
        self._refresh()

    def _new_maze(self) -> None:
        self.maze = generate(self.size, self.size, self.rng)
        self.x, self.y, self.facing = 1, 1, 'E'
        self.goal = _find_goal(self.maze, (self.x, self.y))
        self.game_over = False
        self._refresh()

    # ---------- rendering ----------

    def _refresh(self) -> None:
        view = render_first_person(self.maze, self.x, self.y, self.facing)
        view = maybe_monster_overlay(self.rng, view, chance=0.06)
        self.viewport.configure(text=view)

        if self.show_map:
            self.map_label.configure(text=render_minimap(
                self.maze, self.x, self.y, self.facing,
                torch=self.torch_radius))
        else:
            self.map_label.configure(text='(map hidden — press m)')

        if not self.game_over:
            self._set_status(
                f'Pos ({self.x},{self.y})   Facing {self.facing}   '
                f'Goal {self.goal}',
                '#cbd5e1')

    def _set_status(self, text: str, color: str = '#cbd5e1') -> None:
        self.status.configure(text=text, text_color=color)


if __name__ == '__main__':
    MazeApp().mainloop()
