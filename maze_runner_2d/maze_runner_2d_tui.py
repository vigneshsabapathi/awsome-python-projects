"""Maze Runner 2D — Textual TUI.

A modern terminal UI for the maze game. Walk with arrow keys, toggle the
shortest-path overlay, and regenerate at will. Dark Tailwind palette to
match the GUI.

Bindings:
    Arrows       move
    n            new maze
    s            show / hide solution
    t            cycle generator algorithm
    f            toggle fog-of-war
    Ctrl+Q       quit

Run:
    uv run python maze_runner_2d/maze_runner_2d_tui.py
"""
from __future__ import annotations

import random

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from maze_runner_2d import (ALGORITHMS, END, FLOOR, PLAYER, START, WALL,
                            Maze, generate)

# Tailwind-inspired color map: each glyph -> (fg, bg).
GLYPH_STYLE = {
    WALL:   ('#1e293b', '#1e293b'),   # slate-800
    FLOOR:  ('#0f172a', '#0f172a'),   # slate-900
    START:  ('#22c55e', '#0f172a'),   # green-500
    END:    ('#ef4444', '#0f172a'),   # red-500
    PLAYER: ('#facc15', '#0f172a'),   # amber-400
    '.':    ('#22d3ee', '#0f172a'),   # cyan-400 — solution trail
    ' ':    ('#0f172a', '#0f172a'),   # fog floor
}

# Block characters look more like a real maze than ASCII walls.
DISPLAY_GLYPH = {
    WALL:   '##',
    FLOOR:  '  ',
    START:  ' S',
    END:    ' E',
    PLAYER: ' @',
    '.':    ' .',
    ' ':    '  ',
}


class MazeView(Static):
    """A Rich-rendered maze widget. Re-rendered on every state change."""


class MazeApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 0 0 0;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #maze {
        width: auto;
        height: auto;
        padding: 1 2;
        background: #0f172a;
    }

    #status {
        text-align: center;
        padding: 1 2;
        color: #cbd5e1;
    }

    .status-win   { color: #34d399; text-style: bold; }
    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    """

    BINDINGS = [
        Binding('up', 'move("up")', 'Up', show=False),
        Binding('down', 'move("down")', 'Down', show=False),
        Binding('left', 'move("left")', 'Left', show=False),
        Binding('right', 'move("right")', 'Right', show=False),
        Binding('w', 'move("up")', 'Up', show=False),
        Binding('s,k', 'move("down")', 'Down', show=False),
        Binding('a,h', 'move("left")', 'Left', show=False),
        Binding('d,l', 'move("right")', 'Right', show=False),
        Binding('n', 'new_maze', 'New maze'),
        Binding('p', 'toggle_path', 'Show solution'),
        Binding('t', 'cycle_algo', 'Switch algorithm'),
        Binding('f', 'toggle_fog', 'Fog of war'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Maze Runner 2D'

    def __init__(self,
                 width: int = 21,
                 height: int = 13) -> None:
        super().__init__()
        self.cols = width
        self.rows = height
        self.algo_idx = 0
        self.rng = random.Random()
        self.show_path = False
        self.fog = False
        self.fog_radius = 4
        self.maze: Maze = generate(self.cols, self.rows, self.rng,
                                   ALGORITHMS[self.algo_idx])

    # ----- compose ------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MAZE RUNNER 2D', id='title')
        yield Static('Arrows move - n new - p path - t algo - f fog '
                     '- Ctrl+Q quit',
                     id='subtitle')
        with Vertical():
            yield MazeView(id='maze')
            yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    # ----- actions ------------------------------------------------------

    def action_move(self, direction: str) -> None:
        if self.maze.won:
            return
        if self.maze.move(direction):
            self._refresh()

    def action_new_maze(self) -> None:
        self.maze = generate(self.cols, self.rows, self.rng,
                             ALGORITHMS[self.algo_idx])
        self.show_path = False
        self._refresh()

    def action_toggle_path(self) -> None:
        self.show_path = not self.show_path
        self._refresh()

    def action_cycle_algo(self) -> None:
        self.algo_idx = (self.algo_idx + 1) % len(ALGORITHMS)
        self.action_new_maze()

    def action_toggle_fog(self) -> None:
        self.fog = not self.fog
        self._refresh()

    # ----- rendering ----------------------------------------------------

    def _build_render(self) -> Text:
        """Render the maze grid as a styled Rich Text."""
        grid: list[list[str]] = [row[:] for row in self.maze.grid]
        if self.show_path:
            for x, y in self.maze.solve():
                if (x, y) in (self.maze.start, self.maze.end,
                              self.maze.player):
                    continue
                grid[y][x] = '.'
        sx, sy = self.maze.start
        ex, ey = self.maze.end
        px, py = self.maze.player
        grid[sy][sx] = START
        grid[ey][ex] = END
        grid[py][px] = PLAYER

        text = Text()
        for y, row in enumerate(grid):
            for x, ch in enumerate(row):
                if (self.fog
                        and abs(x - px) + abs(y - py) > self.fog_radius
                        and ch != WALL):
                    fg, bg = GLYPH_STYLE[' ']
                    glyph = DISPLAY_GLYPH[' ']
                else:
                    fg, bg = GLYPH_STYLE.get(ch, GLYPH_STYLE[FLOOR])
                    glyph = DISPLAY_GLYPH.get(ch, '  ')
                text.append(glyph, style=f'{fg} on {bg}')
            text.append('\n')
        return text

    def _refresh(self) -> None:
        self.query_one('#maze', MazeView).update(self._build_render())
        steps = max(0, len(self.maze.solve()) - 1)
        algo = ALGORITHMS[self.algo_idx]
        flags = []
        if self.show_path:
            flags.append('path')
        if self.fog:
            flags.append('fog')
        flag_str = f"  [{' '.join(flags)}]" if flags else ''
        if self.maze.won:
            self._set_status(
                f'You reached the exit! n = new maze   '
                f'({algo}){flag_str}', 'win')
        else:
            self._set_status(
                f'{self.maze.width}x{self.maze.height} - {algo} - '
                f'shortest remaining: {steps}{flag_str}', 'info')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')


if __name__ == '__main__':
    MazeApp().run()
