"""Hungry Robots — Textual TUI.

Dark-palette terminal UI. The board is rendered as a Rich ``Text`` block
inside a single Static widget so refreshes are dirt-cheap. Bindings cover
every numpad direction (``hjkl`` / ``yubn`` / ``qwead..``), wait, both
teleport flavours, new game and quit.

Run:
    uv run python hungry_robots/hungry_robots_tui.py
"""
from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

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

GLYPH_STYLE = {
    EMPTY:  'grey23',
    PLAYER: 'bold bright_cyan',
    ROBOT:  'bold red',
    WRECK:  'bold grey50',
}


class HungryRobotsApp(App):
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
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #board {
        background: #020617;
        color: #f8fafc;
        border: tall #1e293b;
        padding: 1 2;
        margin: 0 2;
        width: auto;
        height: auto;
        content-align: center middle;
    }

    #status {
        text-align: center;
        padding: 1;
        color: #cbd5e1;
    }

    .status-info  { color: #cbd5e1; }
    .status-win   { color: #34d399; text-style: bold; }
    .status-lost  { color: #f87171; text-style: bold; }
    .status-event { color: #fbbf24; }
    """

    BINDINGS = [
        # vim-style 8-direction movement
        Binding('h', 'move(-1, 0)', 'W', show=False),
        Binding('l', 'move(1, 0)', 'E', show=False),
        Binding('k', 'move(0, -1)', 'N', show=False),
        Binding('j', 'move(0, 1)', 'S', show=False),
        Binding('y', 'move(-1, -1)', 'NW', show=False),
        Binding('u', 'move(1, -1)', 'NE', show=False),
        Binding('b', 'move(-1, 1)', 'SW', show=False),
        Binding('n', 'move(1, 1)', 'SE', show=False),
        # numpad-style fallback (and 's' for stand-in-place wait)
        Binding('q', 'move(-1, -1)', 'NW', show=False),
        Binding('e', 'move(1, -1)', 'NE', show=False),
        Binding('a', 'move(-1, 0)', 'W', show=False),
        Binding('d', 'move(1, 0)', 'E', show=False),
        Binding('z', 'move(-1, 1)', 'SW', show=False),
        Binding('x', 'move(0, 1)', 'S', show=False),
        Binding('c', 'move(1, 1)', 'SE', show=False),
        Binding('s', 'move(0, 0)', 'Stay'),
        # actions
        Binding('w', 'wait_out', 'Wait until safe'),
        Binding('t', 'teleport', 'Teleport'),
        Binding('T', 'safe_teleport', 'Safe teleport'),
        Binding('N', 'new_game', 'New / Next'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Hungry Robots'

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        n_robots: int = START_ROBOTS,
    ) -> None:
        super().__init__()
        self.board_w = width
        self.board_h = height
        self.start_robots = n_robots
        self.game = Game(width, height, n_robots)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('HUNGRY ROBOTS', id='title')
        yield Static('hjkl/yubn or qweadzxc to move · w wait · t/T teleport',
                     id='subtitle')
        with Vertical():
            yield Static('', id='board')
            yield Static('', id='status', classes='status-info')
        yield Footer()

    # ------------------------------------------------------------------ render

    def on_mount(self) -> None:
        self._refresh()

    def _board_text(self) -> Text:
        """Build a Rich Text block — colours each glyph independently."""
        text = Text()
        for y in range(self.board_h):
            for x in range(self.board_w):
                glyph = self.game.cell(x, y)
                text.append(glyph, style=GLYPH_STYLE[glyph])
            if y != self.board_h - 1:
                text.append('\n')
        return text

    def _refresh(self, event_msg: str = '') -> None:
        self.query_one('#board', Static).update(self._board_text())
        status = self.query_one('#status', Static)
        line1 = (f'Level {self.game.level}   '
                 f'robots {len(self.game.robots)}   '
                 f'wrecks {len(self.game.wrecks)}   '
                 f'tele {self.game.teleports}   '
                 f'safe {self.game.safe_teleports}')
        if self.game.is_won():
            status.update(line1 + '\nVictory! Press N for next level.')
            status.set_classes('status-win')
            return
        if self.game.is_lost():
            status.update(line1 + '\nA robot caught you. Press N to restart.')
            status.set_classes('status-lost')
            return
        if event_msg:
            status.update(line1 + f'\n{event_msg}')
            status.set_classes('status-event')
        else:
            status.update(line1)
            status.set_classes('status-info')

    # ------------------------------------------------------------------ actions

    def _apply(self, ev: dict) -> None:
        msg = ev.get('message') or (
            f"Crushed {ev['killed']} robot(s)" if ev.get('killed') else '')
        self._refresh(msg)

    def action_move(self, dx: int, dy: int) -> None:
        if self.game.is_won() or self.game.is_lost():
            return
        self._apply(self.game.move_player(dx, dy))

    def action_teleport(self) -> None:
        self._apply(self.game.teleport())

    def action_safe_teleport(self) -> None:
        self._apply(self.game.safe_teleport())

    def action_wait_out(self) -> None:
        self._apply(self.game.wait_until_safe_or_dead())

    def action_new_game(self) -> None:
        if self.game.is_won():
            self.game.next_level()
        else:
            self.game = Game(self.board_w, self.board_h, self.start_robots)
        self._refresh('new round')


def main() -> None:
    HungryRobotsApp().run()


if __name__ == '__main__':
    main()
