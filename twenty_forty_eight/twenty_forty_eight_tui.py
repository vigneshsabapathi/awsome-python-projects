"""2048 — Textual TUI.

A modern terminal UI with a Tailwind-dark palette. Each tile is a Static
widget coloured with the classic 2048 palette (2 = light-cream → ... →
2048 = gold). Arrow keys / WASD move, n starts a new game, u undoes the
last move, ctrl+q quits.

Run:
    uv run python twenty_forty_eight/twenty_forty_eight_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from twenty_forty_eight import (
    DOWN,
    LEFT,
    RIGHT,
    UP,
    Game,
    expectimax_best_move,
)

# ---- classic 2048 tile palette (bg, fg) ------------------------------------
# Matches the GUI palette so the two front-ends stay visually consistent.
TILE_STYLE: dict[int, tuple[str, str]] = {
    2:    ('#eee4da', '#776e65'),
    4:    ('#ede0c8', '#776e65'),
    8:    ('#f2b179', '#f9f6f2'),
    16:   ('#f59563', '#f9f6f2'),
    32:   ('#f67c5f', '#f9f6f2'),
    64:   ('#f65e3b', '#f9f6f2'),
    128:  ('#edcf72', '#f9f6f2'),
    256:  ('#edcc61', '#f9f6f2'),
    512:  ('#edc850', '#f9f6f2'),
    1024: ('#edc53f', '#f9f6f2'),
    2048: ('#edc22e', '#f9f6f2'),
}
TILE_FALLBACK = ('#3c3a32', '#f9f6f2')

GRID_N = 4


def _tile_style(value: int) -> tuple[str, str]:
    return TILE_STYLE.get(value, TILE_FALLBACK)


class TwentyFortyEightApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
        align: center middle;
    }

    #wrap {
        align: center middle;
        height: auto;
        width: auto;
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

    #hud {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .hud-chip {
        padding: 0 2;
        margin: 0 1;
        height: 1;
        background: #1e293b;
        color: #cbd5e1;
    }

    #board {
        grid-gutter: 1 2;
        width: auto;
        height: auto;
        background: #1e293b;
        padding: 1 2;
        border: round #334155;
    }

    .tile {
        width: 9;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: #3b82f6;
        color: #f8fafc;
    }

    .tile-empty {
        background: #0b1220;
        color: #0b1220;
    }

    #status {
        text-align: center;
        padding: 1;
        color: #94a3b8;
    }

    .status-win   { color: #34d399; text-style: bold; }
    .status-error { color: #f87171; text-style: bold; }
    .status-info  { color: #38bdf8; }
    .status-muted { color: #94a3b8; }
    """

    BINDINGS = [
        Binding('up,w',     'move_up',    'Up'),
        Binding('down,s',   'move_down',  'Down'),
        Binding('left,a',   'move_left',  'Left'),
        Binding('right,d',  'move_right', 'Right'),
        Binding('n',        'new_game',   'New'),
        Binding('u',        'undo',       'Undo'),
        Binding('ctrl+q',   'quit',       'Quit'),
    ]

    TITLE = '2048'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.game = Game(self.rng)
        self._history: list[dict] = []
        self._UNDO_LIMIT = 50
        self._won_announced = False

    # ---------------------------------------------------------------- compose

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id='wrap'):
            yield Static('2048', id='title')
            yield Static(
                'Arrows / WASD move  ·  n new  ·  u undo  ·  ctrl+q quit',
                id='subtitle',
            )
            with Horizontal(id='hud'):
                yield Static('Score: 0',  id='score',  classes='hud-chip')
                yield Static('Moves: 0',  id='moves',  classes='hud-chip')
                yield Static('Max: 0',    id='max',    classes='hud-chip')
            with Grid(id='board'):
                for idx in range(GRID_N * GRID_N):
                    yield Static('', classes='tile tile-empty', id=f'cell-{idx}')
            yield Static('Slide tiles together to reach 2048.',
                         id='status', classes='status-muted')
        yield Footer()

    # ---------------------------------------------------------------- mount

    def on_mount(self) -> None:
        board = self.query_one('#board', Grid)
        board.styles.grid_size_columns = GRID_N
        board.styles.grid_size_rows = GRID_N
        self._render_board()
        self._update_hud()

    # ---------------------------------------------------------------- render

    def _render_board(self) -> None:
        for r in range(GRID_N):
            for c in range(GRID_N):
                idx = r * GRID_N + c
                value = self.game.grid[r][c]
                cell = self.query_one(f'#cell-{idx}', Static)
                if value == 0:
                    cell.update(' ')
                    cell.set_classes('tile tile-empty')
                else:
                    bg, fg = _tile_style(value)
                    cell.update(str(value))
                    # Textual CSS custom properties via inline style
                    cell.set_classes('tile')
                    cell.styles.background = bg
                    cell.styles.color = fg

    def _update_hud(self) -> None:
        self.query_one('#score', Static).update(f'Score: {self.game.score}')
        self.query_one('#moves', Static).update(f'Moves: {self.game.moves}')
        self.query_one('#max',   Static).update(f'Max: {self.game.max_tile()}')

    def _set_status(self, text: str, kind: str = 'muted') -> None:
        st = self.query_one('#status', Static)
        st.update(text)
        st.set_classes(f'status-{kind}')

    # ---------------------------------------------------------------- game helpers

    def _snapshot(self) -> dict:
        return {
            'grid':  [row[:] for row in self.game.grid],
            'score': self.game.score,
            'moves': self.game.moves,
        }

    def _restore(self, snap: dict) -> None:
        self.game.grid  = [row[:] for row in snap['grid']]
        self.game.score = snap['score']
        self.game.moves = snap['moves']

    def _push_history(self) -> None:
        self.history_push = True
        self._history.append(self._snapshot())
        if len(self._history) > self._UNDO_LIMIT:
            self._history.pop(0)

    def _new_game(self) -> None:
        self.game = Game(self.rng)
        self._history.clear()
        self._won_announced = False
        self._render_board()
        self._update_hud()
        self._set_status('Slide tiles together to reach 2048.', 'muted')

    # ---------------------------------------------------------------- play

    def _play(self, direction: str) -> None:
        if self.game.is_lost():
            return
        self._history.append(self._snapshot())
        if len(self._history) > self._UNDO_LIMIT:
            self._history.pop(0)

        result = self.game.move(direction)
        if not result['moved']:
            self._history.pop()  # no-op — discard the snapshot
            return

        self._render_board()
        self._update_hud()

        if result['score_delta']:
            self._set_status(f'+{result["score_delta"]}', 'info')

        if self.game.is_won() and not self._won_announced:
            self._won_announced = True
            self._set_status('You reached 2048! Keep going.', 'win')
        elif self.game.is_lost():
            self._set_status('Game over — no legal moves. Press n for a new game.', 'error')

    # ---------------------------------------------------------------- actions

    def action_move_up(self)    -> None: self._play(UP)
    def action_move_down(self)  -> None: self._play(DOWN)
    def action_move_left(self)  -> None: self._play(LEFT)
    def action_move_right(self) -> None: self._play(RIGHT)

    def action_new_game(self) -> None:
        self._new_game()

    def action_undo(self) -> None:
        if not self._history:
            self._set_status('Nothing to undo.', 'muted')
            return
        self._restore(self._history.pop())
        self._won_announced = self.game.is_won()
        self._render_board()
        self._update_hud()
        self._set_status('Undid one move.', 'info')


if __name__ == '__main__':
    TwentyFortyEightApp().run()
