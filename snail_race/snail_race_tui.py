"""Snail Race — Textual TUI.

A terminal-native version of the race with the same betting/bankroll
mechanics as the GUI. Lanes are rendered as plain ASCII bars that
extend left-to-right as the snails crawl, and the odds panel updates
live based on each snail's personality.

Bindings:
    1-4         pick snail #N to bet on
    space       start the race / re-rack after a finish
    + / =       wager up (+10)
    -           wager down (-10)
    n           reset bankroll
    Ctrl+Q      quit

Run:
    uv run python snail_race/snail_race_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from snail_race import (
    MIN_WAGER,
    SNAILS,
    STARTING_BALANCE,
    WAGER_STEP,
    Race,
    implied_odds,
    settle_bet,
)

NUM_SNAILS = 4
TRACK_LENGTH = 40
TICK_INTERVAL = 0.10  # seconds between animation frames

# Tailwind-ish dark palette to match the GUI personality.
LANE_WIDTH = 40  # characters of track shown in the TUI


class SnailRaceApp(App):
    CSS = """
    Screen {
        background: #0b1220;
        color: #e2e8f0;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #38bdf8;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #board {
        width: 100%;
        height: auto;
        align-horizontal: center;
        padding: 1 2;
    }

    .panel {
        border: round #1d4ed8;
        background: #111a2e;
        padding: 1 2;
        margin: 1 1;
    }

    #track {
        width: 64;
        height: auto;
    }

    #stats {
        width: 1fr;
    }

    .lane {
        height: 1;
        color: #cbd5e1;
    }

    .lane-bet {
        text-style: bold;
        color: #fbbf24;
    }

    .lane-winner {
        text-style: bold;
        color: #22c55e;
    }

    #balance {
        text-align: center;
        text-style: bold;
        color: #f59e0b;
        padding: 1 0;
    }

    #wager {
        text-align: center;
        color: #e2e8f0;
        padding-bottom: 1;
    }

    .odds {
        height: 1;
        color: #cbd5e1;
    }

    .odds-picked {
        text-style: bold;
        color: #fbbf24;
    }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-win   { color: #22c55e; text-style: bold; }
    .status-lose  { color: #f87171; text-style: bold; }
    .status-error { color: #f87171; text-style: bold; }
    """

    BINDINGS = [
        Binding('1', 'bet(0)', 'Bet 1'),
        Binding('2', 'bet(1)', 'Bet 2'),
        Binding('3', 'bet(2)', 'Bet 3'),
        Binding('4', 'bet(3)', 'Bet 4'),
        Binding('space', 'go', 'Start / Next'),
        Binding('plus,equals_sign,equal', 'wager_up', 'Wager +'),
        Binding('minus', 'wager_down', 'Wager -'),
        Binding('n', 'reset', 'Reset bankroll'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Snail Race'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.balance = STARTING_BALANCE
        self.wager = MIN_WAGER * 5
        self.race: Race | None = None
        self.odds: list[float] = []
        self.bet_snail: int | None = None
        self.animating: bool = False
        self.race_done: bool = False
        self._timer = None  # textual Timer

    # ------------------------------------------------------------ layout

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('🐌  SNAIL RACE  🐌', id='title')
        yield Static(
            'Pick a snail (1-4), space to start, +/- adjust wager.',
            id='subtitle')
        with Horizontal(id='board'):
            with Vertical(id='track', classes='panel'):
                for i in range(NUM_SNAILS):
                    yield Static('', classes='lane', id=f'lane-{i}')
            with Vertical(id='stats', classes='panel'):
                yield Static('', id='balance')
                yield Static('', id='wager')
                for i in range(NUM_SNAILS):
                    yield Static('', classes='odds', id=f'odds-{i}')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._new_race()

    # ----------------------------------------------------------- helpers

    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    def _refresh_balance(self) -> None:
        self.query_one('#balance', Static).update(
            f'Bankroll:  $ {self.balance:,}')

    def _refresh_wager(self) -> None:
        self.query_one('#wager', Static).update(
            f'Wager:     $ {self.wager:,}   (+ / -)')

    def _refresh_odds(self) -> None:
        if self.race is None:
            return
        for i, p in enumerate(self.race.personalities):
            o = self.odds[i]
            line = f'{i + 1}. {p.name:<10}  μ={p.mean_step:.1f}  {o:5.2f}x'
            w = self.query_one(f'#odds-{i}', Static)
            w.update(line)
            if i == self.bet_snail:
                w.set_classes('odds odds-picked')
            else:
                w.set_classes('odds')

    def _refresh_lanes(self) -> None:
        if self.race is None:
            return
        for i, p in enumerate(self.race.personalities):
            pos = self.race.positions[i]
            frac = pos / self.race.track_length
            filled = int(round(frac * LANE_WIDTH))
            filled = min(filled, LANE_WIDTH)
            empty = LANE_WIDTH - filled
            track = '█' * max(0, filled - 1) + ('🐌' if filled > 0 else '')
            track = track + '·' * empty
            # Keep the visible width stable: emoji + bar = LANE_WIDTH cells.
            marker = ' '
            cls = 'lane'
            if self.race.winner() == i and self.race.is_done():
                marker = '★'
                cls = 'lane lane-winner'
            elif i == self.bet_snail:
                marker = '►'
                cls = 'lane lane-bet'
            line = f'{marker} {i + 1}. {p.name:<10} |{track}| {pos:>2}/{self.race.track_length}'
            w = self.query_one(f'#lane-{i}', Static)
            w.update(line)
            w.set_classes(cls)

    def _refresh_all(self) -> None:
        self._refresh_balance()
        self._refresh_wager()
        self._refresh_odds()
        self._refresh_lanes()

    # ---------------------------------------------------------- gameplay

    def _new_race(self) -> None:
        # Cancel any leftover timer from the previous race.
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.race = Race(num_snails=NUM_SNAILS,
                         track_length=TRACK_LENGTH,
                         rng=self.rng)
        self.odds = implied_odds(self.race.personalities,
                                 self.race.track_length)
        self.bet_snail = None
        self.animating = False
        self.race_done = False
        self._refresh_all()
        if self.balance <= 0:
            self._set_status(
                'Out of money. Press N to reset bankroll.', 'error')
        else:
            self._set_status(
                'Pick a snail (1-4), then press space to start.', 'info')

    # ------------------------------------------------------------ actions

    def action_bet(self, idx: int) -> None:
        if self.animating:
            return
        if self.race is None or self.race_done:
            return
        if idx < 0 or idx >= len(self.race.personalities):
            return
        if self.balance <= 0:
            self._set_status(
                'Out of money. Press N to reset bankroll.', 'error')
            return
        self.bet_snail = idx
        p = self.race.personalities[idx]
        self._refresh_odds()
        self._set_status(
            f'Locked in: {p.name} @ {self.odds[idx]:.2f}x  for ${self.wager:,}.',
            'info')

    def action_wager_up(self) -> None:
        if self.animating:
            return
        upper = max(self.balance, MIN_WAGER)
        self.wager = min(upper, self.wager + WAGER_STEP)
        self._refresh_wager()

    def action_wager_down(self) -> None:
        if self.animating:
            return
        self.wager = max(MIN_WAGER, self.wager - WAGER_STEP)
        self._refresh_wager()

    def action_go(self) -> None:
        if self.animating:
            return
        if self.race_done:
            self._new_race()
            return
        if self.bet_snail is None:
            self._set_status('Pick a snail first (1-4).', 'error')
            return
        if self.balance <= 0:
            self._set_status('Out of money — press N to reset.', 'error')
            return
        if self.wager > self.balance:
            self.wager = self.balance
            self._refresh_wager()

        self.animating = True
        self._set_status('They\'re off!', 'info')
        # Drive the race via a Textual timer so the UI keeps responding.
        self._timer = self.set_interval(TICK_INTERVAL, self._tick)

    def action_reset(self) -> None:
        if self.animating:
            return
        self.balance = STARTING_BALANCE
        self.wager = MIN_WAGER * 5
        self._new_race()
        self._set_status('Bankroll reset. Pick a snail.', 'info')

    # ----------------------------------------------------------- engine tick

    def _tick(self) -> None:
        assert self.race is not None
        self.race.step()
        self._refresh_lanes()
        if self.race.is_done():
            if self._timer is not None:
                self._timer.stop()
                self._timer = None
            self._settle()

    def _settle(self) -> None:
        assert self.race is not None
        self.animating = False
        self.race_done = True
        winner = self.race.winner()
        wp = self.race.personalities[winner]
        result = settle_bet(self.bet_snail, self.wager, self.balance,
                            winner, self.odds[self.bet_snail])
        self.balance = result['balance']
        self._refresh_balance()
        self._refresh_lanes()
        if result['win']:
            self._set_status(
                (f'{wp.name} wins in {self.race.tick} ticks! '
                 f'+${result["delta"]:,} @ {self.odds[self.bet_snail]:.2f}x. '
                 f'Press space for next race.'),
                'win')
        else:
            self._set_status(
                (f'{wp.name} wins. You lost ${self.wager:,}. '
                 f'Press space for next race.'),
                'lose')
        if self.balance <= 0:
            self._set_status(
                'You are out of money. Press N to reset.', 'error')


if __name__ == '__main__':
    SnailRaceApp().run()
