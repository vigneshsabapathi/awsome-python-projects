"""Cho-Han — Textual TUI.

A terminal version of the dice-cup game with the same gameplay as the GUI:
balance, wager slider (via +/-), bet on chō (even) or han (odd), and a
"ruin probability" Monte Carlo readout for the current bankroll & wager.

Bindings:
    c       — bet chō (even)
    h       — bet han (odd)
    +/=, -  — adjust wager by ¥100
    n       — new round / reset table after bust
    Ctrl+Q  — quit

Run:
    uv run python cho_han/cho_han_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from cho_han import (
    CHO,
    HAN,
    KANJI,
    MIN_WAGER,
    STARTING_BALANCE,
    WAGER_STEP,
    play_round,
    ruin_probability,
)

DICE_FACES = {1: '⚀', 2: '⚁', 3: '⚂',
              4: '⚃', 5: '⚄', 6: '⚅'}


class ChoHanApp(App):
    CSS = """
    Screen {
        background: #1a0f0c;
        color: #f1e3c2;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #d4a04c;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #a89578;
        padding-bottom: 1;
    }

    #board {
        width: 100%;
        height: auto;
        align-horizontal: center;
        padding: 1 2;
    }

    .panel {
        border: round #8a6a30;
        background: #2a1410;
        padding: 1 2;
        margin: 1 1;
    }

    #cup {
        width: 40;
        height: 11;
        content-align: center middle;
        text-align: center;
        text-style: bold;
        color: #d4a04c;
    }

    #cup.revealed-win  { color: #6ed47b; border: round #6ed47b; }
    #cup.revealed-lose { color: #ff8a8a; border: round #ff8a8a; }

    #stats {
        width: 1fr;
    }

    #balance {
        text-align: center;
        text-style: bold;
        color: #d4a04c;
        padding: 1 0;
    }

    #wager {
        text-align: center;
        color: #f1e3c2;
        padding: 1 0;
    }

    #ruin {
        text-align: center;
        color: #a89578;
        padding-top: 1;
    }

    #status {
        text-align: center;
        padding: 1;
        color: #f1e3c2;
    }

    .status-info  { color: #f1e3c2; }
    .status-win   { color: #6ed47b; text-style: bold; }
    .status-lose  { color: #ff8a8a; text-style: bold; }
    .status-error { color: #ff8a8a; text-style: bold; }
    """

    BINDINGS = [
        Binding('c', 'bet_cho', 'Bet Cho 丁'),
        Binding('h', 'bet_han', 'Bet Han 半'),
        Binding('plus,equals_sign,equal', 'wager_up', 'Wager +'),
        Binding('minus', 'wager_down', 'Wager -'),
        Binding('n', 'new_round', 'New / Reset'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Cho-Han  丁  半'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.balance = STARTING_BALANCE
        self.wager = MIN_WAGER * 5
        self.last_dice: tuple[int, int] | None = None
        self.cup_revealed = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('丁  CHO-HAN  半', id='title')
        yield Static(
            'Bet on the parity of two dice — chō (even) or han (odd)',
            id='subtitle')
        with Horizontal(id='board'):
            yield Static(self._cup_text(), id='cup', classes='panel')
            with Vertical(id='stats', classes='panel'):
                yield Static('', id='balance')
                yield Static('', id='wager')
                yield Static('', id='ruin')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_all()

    # ----- helpers ----------------------------------------------------------

    def _cup_text(self) -> str:
        if self.cup_revealed and self.last_dice is not None:
            d1, d2 = self.last_dice
            from cho_han import outcome
            kanji = KANJI[outcome(self.last_dice)]
            return (f'\n  {DICE_FACES[d1]}   {DICE_FACES[d2]}\n\n'
                    f'  {d1} + {d2} = {d1 + d2}\n\n'
                    f'  → {kanji}')
        return '\n   ┌────────┐\n   │  丁  半 │\n   └────────┘\n\n  Cup is down.'

    def _refresh_all(self) -> None:
        self._refresh_cup()
        self._refresh_balance()
        self._refresh_wager()
        self._refresh_ruin()

    def _refresh_cup(self, classes: str = 'panel') -> None:
        cup = self.query_one('#cup', Static)
        cup.update(self._cup_text())
        cup.set_classes(classes)

    def _refresh_balance(self) -> None:
        self.query_one('#balance', Static).update(
            f'Balance:  ¥ {self.balance:,}')

    def _refresh_wager(self) -> None:
        self.query_one('#wager', Static).update(
            f'Wager:    ¥ {self.wager:,}   (+ / -)')

    def _refresh_ruin(self) -> None:
        if self.balance <= 0 or self.wager <= 0:
            self.query_one('#ruin', Static).update('')
            return
        # Light Monte Carlo so the keypress feels instant.
        p = ruin_probability(self.balance, self.wager,
                             rounds=200, trials=800, rng=self.rng)
        self.query_one('#ruin', Static).update(
            f'Ruin risk @ this wager (200 rounds): {p * 100:.1f}%')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    def _clamp_wager(self) -> None:
        if self.balance > 0:
            upper = max(self.balance, MIN_WAGER)
            self.wager = max(MIN_WAGER, min(self.wager, upper))

    # ----- actions ----------------------------------------------------------

    def action_wager_up(self) -> None:
        upper = max(self.balance, MIN_WAGER)
        self.wager = min(upper, self.wager + WAGER_STEP)
        self._refresh_wager()
        self._refresh_ruin()

    def action_wager_down(self) -> None:
        self.wager = max(MIN_WAGER, self.wager - WAGER_STEP)
        self._refresh_wager()
        self._refresh_ruin()

    def action_bet_cho(self) -> None:
        self._place_bet(CHO)

    def action_bet_han(self) -> None:
        self._place_bet(HAN)

    def action_new_round(self) -> None:
        if self.balance <= 0:
            # Reset whole table after a bust.
            self.balance = STARTING_BALANCE
            self.wager = MIN_WAGER * 5
            self.last_dice = None
            self.cup_revealed = False
            self._refresh_all()
            self._set_status('Fresh table. Place your bet (c / h).', 'info')
            return
        self.last_dice = None
        self.cup_revealed = False
        self._refresh_cup()
        self._set_status('Cup is down. Place your bet (c / h).', 'info')

    def _place_bet(self, bet: str) -> None:
        if self.balance <= 0:
            self._set_status(
                'You are out of money. Press n to reset.', 'error')
            return
        self._clamp_wager()
        result = play_round(bet, self.wager, self.balance, rng=self.rng)
        self.last_dice = result['dice']
        self.cup_revealed = True
        self.balance = result['balance']

        kind = 'win' if result['win'] else 'lose'
        cup_class = f"panel revealed-{kind}"
        self._refresh_cup(classes=cup_class)
        self._refresh_balance()
        self._refresh_ruin()

        kanji = KANJI[result['result']]
        if result['win']:
            self._set_status(
                f"You bet {KANJI[bet]} ({bet}) — cup shows {kanji}. "
                f"WIN ¥ {result['wager']:,}.", 'win')
        else:
            self._set_status(
                f"You bet {KANJI[bet]} ({bet}) — cup shows {kanji}. "
                f"LOSE ¥ {result['wager']:,}.", 'lose')

        if self.balance <= 0:
            self._set_status(
                'You are out of money. Press n to reset.', 'error')


if __name__ == '__main__':
    ChoHanApp().run()
