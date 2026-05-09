"""Dice Math — Textual TUI.

A modern terminal UI for the Dice Math drill. Same flow as the GUI:
big rendered dice, answer entry, score/streak/timer, mode + difficulty.

Bindings:
    Enter   submit answer
    n       new round
    Ctrl+Q  quit

Run:
    uv run python dice_math/dice_math_tui.py
"""
from __future__ import annotations

import random
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from dice_math import (
    MODES,
    correct_answer,
    format_dice,
    roll,
    save_high_score,
    score_round,
)


class DiceMathApp(App):
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

    #stats {
        height: 3;
        align-horizontal: center;
        margin: 0 2;
        padding: 1 2;
        background: #1e293b;
    }

    .stat {
        width: 1fr;
        text-align: center;
        text-style: bold;
    }

    .stat-score  { color: #f8fafc; }
    .stat-streak { color: #38bdf8; }
    .stat-timer  { color: #34d399; }

    #dice {
        height: auto;
        width: auto;
        margin: 1 2;
        padding: 1 2;
        background: #1e293b;
        color: #f8fafc;
        text-align: center;
    }

    #settings {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
        color: #94a3b8;
    }

    #input {
        margin: 1 6;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus { border: tall #38bdf8; }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-win   { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('n', 'new_round', 'New Round'),
        Binding('m', 'cycle_mode', 'Mode'),
        Binding('plus,equals_sign,equal', 'difficulty_up', '+ Dice'),
        Binding('minus', 'difficulty_down', '- Dice'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Dice Math'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.num_dice = 3
        self.mode = 'sum'
        self.values: list[int] = []
        self.target: int | str = 0
        self.score = 0
        self.streak = 0
        self.best_streak = 0
        self.round_num = 0
        self.start_time: float | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('DICE MATH', id='title')
        yield Static('Roll. Compute. Beat the clock.', id='subtitle')
        with Horizontal(id='stats'):
            yield Static('Score: 0', id='score', classes='stat stat-score')
            yield Static('Streak: 0', id='streak', classes='stat stat-streak')
            yield Static('Time: 0.0s', id='timer', classes='stat stat-timer')
        yield Static('', id='settings')
        with Vertical():
            yield Static('', id='dice')
        yield Input(placeholder='answer (Enter to submit)', id='input')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_settings_label()
        self._new_round()
        # Update the timer display ten times a second.
        self.set_interval(0.1, self._tick_timer)

    # --- Game flow -------------------------------------------------------

    def _new_round(self) -> None:
        self.values = roll(self.num_dice, self.rng)
        self.target = correct_answer(self.values, self.mode)
        self.query_one('#dice', Static).update(format_dice(self.values))
        self.round_num += 1
        prompt = self._prompt_for_mode()
        self._set_status(f'Round {self.round_num}: {prompt}', 'info')

        input_widget = self.query_one('#input', Input)
        input_widget.value = ''
        input_widget.disabled = False
        input_widget.focus()
        self.start_time = time.perf_counter()

    def _prompt_for_mode(self) -> str:
        return {
            'sum':     'enter the sum',
            'product': 'enter the product',
            'max':     'enter the largest face',
            'pair':    "type 'y' if any two match, else 'n'",
        }[self.mode]

    def _tick_timer(self) -> None:
        if self.start_time is None:
            return
        elapsed = time.perf_counter() - self.start_time
        self.query_one('#timer', Static).update(f'Time: {elapsed:.1f}s')

    def _refresh_settings_label(self) -> None:
        self.query_one('#settings', Static).update(
            f'Mode: [b]{self.mode}[/b]   Dice: [b]{self.num_dice}[/b]   '
            "(m=mode  +/-=dice  n=new  Ctrl+Q=quit)")

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    # --- Actions ---------------------------------------------------------

    def action_new_round(self) -> None:
        self._new_round()

    def action_cycle_mode(self) -> None:
        idx = MODES.index(self.mode)
        self.mode = MODES[(idx + 1) % len(MODES)]
        self._refresh_settings_label()
        self._new_round()

    def action_difficulty_up(self) -> None:
        if self.num_dice < 6:
            self.num_dice += 1
            self._refresh_settings_label()
            self._new_round()

    def action_difficulty_down(self) -> None:
        if self.num_dice > 2:
            self.num_dice -= 1
            self._refresh_settings_label()
            self._new_round()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.start_time is None:
            return
        elapsed = time.perf_counter() - self.start_time
        answer = event.value
        points = score_round(answer, self.target, elapsed)

        if points > 0:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            self.score += points
            self._set_status(
                f'Correct! +{points} pts in {elapsed:.2f}s', 'win')
        else:
            self.streak = 0
            self._set_status(
                f'Wrong. Answer was {self.target} ({elapsed:.2f}s)', 'error')

        self.query_one('#score', Static).update(f'Score: {self.score}')
        self.query_one('#streak', Static).update(f'Streak: {self.streak}')
        self.query_one('#timer', Static).update(f'Time: {elapsed:.2f}s')
        event.input.disabled = True
        self.start_time = None
        # Auto-advance after a short pause so the player can read the result.
        self.set_timer(0.9, self._new_round)

    # --- Cleanup ---------------------------------------------------------

    def on_unmount(self) -> None:
        if self.score > 0:
            try:
                save_high_score('player', self.score, self.mode)
            except Exception:
                pass


if __name__ == '__main__':
    DiceMathApp().run()
