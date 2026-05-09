"""Maze Runner 3D — Textual TUI.

A modern terminal UI: large monospace first-person viewport on the left,
minimap on the right, status footer below.

Run:
    uv run python maze_runner_3d/maze_runner_3d_tui.py

Bindings:
    w / a / s / d   move and turn
    n               new maze
    m               toggle minimap
    Ctrl+Q          quit
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from maze_runner_3d import (
    generate,
    maybe_monster_overlay,
    move,
    render_first_person,
    render_minimap,
    _find_goal,
)


class MazeApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
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
        padding: 0 0 1 0;
    }

    #board {
        height: 1fr;
        width: 100%;
        align: center top;
        padding: 1 2;
    }

    #viewport {
        width: 1fr;
        height: 100%;
        background: #020617;
        color: #e2e8f0;
        padding: 1 2;
        border: round #1e293b;
    }

    #map-pane {
        width: 32;
        height: 100%;
        background: #020617;
        color: #cbd5e1;
        padding: 1 2;
        border: round #1e293b;
        margin-left: 1;
    }

    #map-title {
        text-style: bold;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #status {
        text-align: center;
        padding: 1;
        color: #cbd5e1;
    }

    .status-win   { color: #34d399; text-style: bold; }
    .status-info  { color: #cbd5e1; }
    """

    BINDINGS = [
        Binding('w', 'go("w")', 'Forward'),
        Binding('s', 'go("s")', 'Back'),
        Binding('a', 'go("a")', 'Turn L'),
        Binding('d', 'go("d")', 'Turn R'),
        Binding('up', 'go("w")', 'Forward', show=False),
        Binding('down', 'go("s")', 'Back', show=False),
        Binding('left', 'go("a")', 'Turn L', show=False),
        Binding('right', 'go("d")', 'Turn R', show=False),
        Binding('n', 'new_maze', 'New'),
        Binding('m', 'toggle_map', 'Map'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Maze Runner 3D'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.size = 13
        self.torch_radius = 4
        self.maze = generate(self.size, self.size, self.rng)
        self.x, self.y, self.facing = 1, 1, 'E'
        self.goal = _find_goal(self.maze, (self.x, self.y))
        self.show_map = True
        self.game_over = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MAZE RUNNER 3D', id='title')
        yield Static('w/a/s/d move • n new • m map • Ctrl+Q quit',
                     id='subtitle')
        with Horizontal(id='board'):
            yield Static('', id='viewport')
            with Vertical(id='map-pane'):
                yield Static('MAP', id='map-title')
                yield Static('', id='map')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    # ---------- actions ----------

    def action_go(self, action: str) -> None:
        if self.game_over:
            return
        self.x, self.y, self.facing = move(
            self.maze, self.x, self.y, self.facing, action)
        self._refresh()
        if (self.x, self.y) == self.goal:
            self._set_status('You found the exit! Press n for a new maze.',
                             'win')
            self.game_over = True

    def action_new_maze(self) -> None:
        self.maze = generate(self.size, self.size, self.rng)
        self.x, self.y, self.facing = 1, 1, 'E'
        self.goal = _find_goal(self.maze, (self.x, self.y))
        self.game_over = False
        self._refresh()

    def action_toggle_map(self) -> None:
        self.show_map = not self.show_map
        self._refresh()

    # ---------- rendering ----------

    def _refresh(self) -> None:
        view = render_first_person(self.maze, self.x, self.y, self.facing)
        view = maybe_monster_overlay(self.rng, view, chance=0.06)
        self.query_one('#viewport', Static).update(view)

        if self.show_map:
            self.query_one('#map', Static).update(render_minimap(
                self.maze, self.x, self.y, self.facing,
                torch=self.torch_radius))
        else:
            self.query_one('#map', Static).update('(map hidden — press m)')

        if not self.game_over:
            self._set_status(
                f'Pos ({self.x},{self.y})   Facing {self.facing}   '
                f'Goal {self.goal}',
                'info')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')


if __name__ == '__main__':
    MazeApp().run()
