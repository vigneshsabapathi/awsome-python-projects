"""Carrot in a Box — Textual TUI.

Hot-seat 2-player bluffing game in the terminal. Two ASCII box panels
sit side-by-side. Players peek, bluff, then Player 1 swaps or keeps.

Run:
    uv run python carrot_box/carrot_box_tui.py

Bindings: p peek, s swap, k keep, n new game, Ctrl+Q quit.
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from carrot_box import Game, ai_decision


# ---- CSS (dark Tailwind palette) -------------------------------------

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

#score {
    text-align: center;
    color: #94a3b8;
    height: 1;
}

#boxes-row {
    align-horizontal: center;
    height: auto;
    margin-top: 1;
    margin-bottom: 1;
}

.player-col {
    width: 24;
    align-horizontal: center;
    margin: 0 2;
}

.player-label {
    text-align: center;
    text-style: bold;
    color: #f8fafc;
    height: 1;
    margin-bottom: 1;
}

.box-art {
    text-align: center;
    width: 22;
    height: 7;
    background: #1f2937;
    border: tall #334155;
    content-align: center middle;
    color: #6b7280;
}

.box-carrot {
    background: #431407;
    border: tall #f97316;
    color: #f97316;
    text-style: bold;
}

.box-empty {
    background: #1f2937;
    border: tall #334155;
    color: #6b7280;
}

.box-revealed-carrot {
    background: #431407;
    border: tall #f97316;
    color: #f97316;
    text-style: bold;
}

.box-revealed-empty {
    background: #1f2937;
    border: tall #16a34a;
    color: #6b7280;
}

.box-hidden {
    background: #1f2937;
    border: tall #334155;
    color: #6b7280;
}

.box-caption {
    text-align: center;
    height: 1;
    color: #94a3b8;
    margin-top: 1;
}

#current-player {
    text-align: center;
    color: #38bdf8;
    text-style: bold;
    height: 1;
    margin-bottom: 1;
}

#status {
    text-align: center;
    padding: 1;
    width: 100%;
}

.status-info  { color: #cbd5e1; }
.status-error { color: #f87171; text-style: bold; }
.status-win   { color: #34d399; text-style: bold; }
.status-prompt { color: #38bdf8; }

#hints {
    text-align: center;
    color: #475569;
    height: 1;
}
"""


# ---- App -------------------------------------------------------------

HIDDEN = "┌─────────────┐\n│             │\n│      ?      │\n│             │\n└─────────────┘"
CARROT = "┌─────────────┐\n│             │\n│      🥕     │\n│             │\n└─────────────┘"
EMPTY  = "┌─────────────┐\n│             │\n│    (empty)  │\n│             │\n└─────────────┘"


class CarrotBoxTUI(App):
    CSS = CSS

    BINDINGS = [
        Binding('p', 'peek', 'Peek'),
        Binding('s', 'swap', 'Swap'),
        Binding('k', 'keep', 'Keep'),
        Binding('n', 'new_game', 'New Game'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Carrot in a Box'

    # States: menu | peek1 | after_peek1 | peek2 | after_peek2 |
    #         decide | reveal_pending | revealed

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.score: dict[int, int] = {1: 0, 2: 0}
        self.vs_ai: bool = False
        self.game: Game | None = None
        self.state: str = 'menu'

    # ---- compose -----------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('CARROT IN A BOX', id='title')
        yield Static('2-player bluffing — one carrot, two boxes', id='subtitle')
        yield Static('', id='score')
        yield Static('', id='current-player')
        with Horizontal(id='boxes-row'):
            for player in (1, 2):
                with Vertical(classes='player-col'):
                    yield Static(f'Player {player}',
                                 classes='player-label',
                                 id=f'label-{player}')
                    yield Static(HIDDEN,
                                 classes='box-art box-hidden',
                                 id=f'box-{player}')
                    yield Static('', classes='box-caption',
                                 id=f'caption-{player}')
        yield Static('', id='status', classes='status-info')
        yield Static('', id='hints')
        yield Footer()

    def on_mount(self) -> None:
        self._show_menu()

    # ---- helpers -----------------------------------------------------

    def _set_status(self, text: str, kind: str = 'info') -> None:
        w = self.query_one('#status', Static)
        w.update(text)
        w.set_classes(f'status-{kind}')

    def _set_score(self) -> None:
        p1 = 'AI' if self.vs_ai else 'Player 1'
        p2 = 'You' if self.vs_ai else 'Player 2'
        self.query_one('#score', Static).update(
            f'{p1}: {self.score[1]}   |   {p2}: {self.score[2]}')

    def _set_current_player(self, text: str) -> None:
        self.query_one('#current-player', Static).update(text)

    def _set_hints(self, text: str) -> None:
        self.query_one('#hints', Static).update(text)

    def _set_box(self, player: int, art: str, css_class: str,
                 caption: str = '') -> None:
        box = self.query_one(f'#box-{player}', Static)
        box.update(art)
        box.set_classes(f'box-art {css_class}')
        self.query_one(f'#caption-{player}', Static).update(caption)

    def _hide_both(self) -> None:
        for p in (1, 2):
            self._set_box(p, HIDDEN, 'box-hidden', '')

    # ---- state transitions ------------------------------------------

    def _show_menu(self) -> None:
        self.state = 'menu'
        self.game = None
        self._hide_both()
        self._set_score()
        p1 = 'AI' if self.vs_ai else 'Player 1'
        self._set_current_player(
            f'Mode: {"vs AI" if self.vs_ai else "2 humans"}')
        self._set_status(
            f'Press [n] to start a new round. '
            f'The carrot is hidden — find it!', 'prompt')
        self._set_hints('[n] new round   [ctrl+q] quit')

    def _start_round(self) -> None:
        self.game = Game(rng=self.rng)
        self._hide_both()
        if self.vs_ai:
            self.game.peek(1)          # AI peeks silently
            self.state = 'peek2'
            self._set_current_player('Your turn (Player 2)')
            self._set_status(
                'Press [p] to privately peek inside your box.', 'prompt')
            self._set_hints('[p] peek')
        else:
            self.state = 'peek1'
            self._set_current_player('Player 1 — look away, Player 2!')
            self._set_status(
                'Player 1: press [p] to peek inside your box.', 'prompt')
            self._set_hints('[p] peek')

    def _do_peek(self, player: int) -> None:
        assert self.game is not None
        has = self.game.peek(player)
        if has:
            self._set_box(player, CARROT, 'box-carrot', 'CARROT!')
        else:
            self._set_box(player, EMPTY, 'box-empty', 'empty')
        self.state = f'after_peek{player}'
        self._set_status(
            f'{"Your box has" if self.vs_ai and player == 2 else f"Player {player}\'s box has"} '
            f'{"the CARROT!" if has else "nothing."}  '
            f'Press [p] again to hide and continue.', 'info')
        self._set_hints('[p] hide & continue')

    def _hide_after_peek(self, player: int) -> None:
        self._set_box(player, HIDDEN, 'box-hidden', '')
        if self.vs_ai:
            self._ai_acts()
        elif player == 1:
            self.state = 'peek2'
            self._set_current_player('Player 2 — look away, Player 1!')
            self._set_status(
                'Player 2: press [p] to peek inside your box.', 'prompt')
            self._set_hints('[p] peek')
        else:
            self.state = 'decide'
            self._set_current_player('Player 1 decides')
            self._set_status(
                'Talk it out. Player 1: [s] to SWAP boxes, [k] to KEEP.',
                'prompt')
            self._set_hints('[s] swap   [k] keep')

    def _ai_acts(self) -> None:
        assert self.game is not None
        ai_has = self.game.has_carrot(1)
        bluffs = [
            '"I definitely have the carrot. You should keep your box."',
            '"Ugh, mine is empty. Want to swap?"',
            '"Hmm, I am not sure what to do."',
            '"Trust me. You do not want to swap."',
        ]
        bluff = self.rng.choice(bluffs)
        swap = ai_decision(ai_has, self.rng)
        self.game.decide(1, swap)
        verb = 'SWAPPED' if swap else 'KEPT'
        self._set_current_player(f'AI {verb} the boxes')
        self._set_status(
            f'AI says: {bluff}\nAI {verb} the boxes. Press [p] to reveal!',
            'info')
        self.state = 'reveal_pending'
        self._set_hints('[p] reveal')

    def _do_decide(self, swap: bool) -> None:
        assert self.game is not None
        self.game.decide(1, swap)
        verb = 'SWAPPED' if swap else 'KEPT'
        self._set_current_player(f'Player 1 {verb}')
        self._set_status(
            f'Player 1 {verb} the boxes. Press [p] to reveal!', 'info')
        self.state = 'reveal_pending'
        self._set_hints('[p] reveal')

    def _reveal(self) -> None:
        assert self.game is not None
        winner = self.game.reveal()
        for p in (1, 2):
            has = self.game.has_carrot(p)
            if has:
                self._set_box(p, CARROT, 'box-revealed-carrot', 'CARROT!')
            else:
                self._set_box(p, EMPTY, 'box-revealed-empty', 'empty')
        self.score[winner] += 1
        self._set_score()
        if self.vs_ai:
            if winner == 2:
                msg, kind = 'You win the carrot!', 'win'
            else:
                msg, kind = 'AI wins the carrot.', 'error'
        else:
            msg, kind = f'Player {winner} wins the carrot!', 'win'
        self._set_current_player(msg)
        self._set_status(msg, kind)
        self.state = 'revealed'
        self._set_hints('[n] new round   [ctrl+q] quit')

    # ---- actions (key bindings) -------------------------------------

    def action_peek(self) -> None:
        s = self.state
        if s == 'menu':
            self._start_round()
        elif s == 'peek1':
            self._do_peek(1)
        elif s == 'after_peek1':
            self._hide_after_peek(1)
        elif s == 'peek2':
            self._do_peek(2)
        elif s == 'after_peek2':
            self._hide_after_peek(2)
        elif s == 'reveal_pending':
            self._reveal()

    def action_swap(self) -> None:
        if self.state == 'decide':
            self._do_decide(swap=True)

    def action_keep(self) -> None:
        if self.state == 'decide':
            self._do_decide(swap=False)

    def action_new_game(self) -> None:
        self._show_menu()
        self._start_round()


if __name__ == '__main__':
    CarrotBoxTUI().run()
