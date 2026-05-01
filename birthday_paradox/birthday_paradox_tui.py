"""Birthday Paradox — Textual TUI.

Modern terminal UI showing a probability bar chart for sampled group sizes.
The currently-selected N is highlighted; theoretical, empirical, and 95% Wilson
CI are shown in the status bar.

Run:
    uv run python birthday_paradox/birthday_paradox_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button, Footer, Header, Input, RadioButton, RadioSet, Static,
)

from birthday_paradox import simulate, theoretical, wilson_ci

N_MIN, N_MAX = 2, 80
DEFAULT_N = 23
TRIALS_OPTIONS = (1_000, 10_000, 100_000)
DEFAULT_TRIALS = 10_000

# Sample N values to display in the bar chart.
SAMPLE_NS = (2, 5, 10, 15, 20, 23, 25, 30, 35, 40, 50, 60, 70, 80)

BAR_WIDTH = 50  # max chars for the bar
EIGHTHS = ('', '▏', '▎', '▍', '▌', '▋', '▊', '▉')


def render_bar(p: float, width: int = BAR_WIDTH) -> str:
    """Render a probability 0..1 as a unicode bar of given max width."""
    full_eighths = int(round(p * width * 8))
    full_eighths = max(0, min(full_eighths, width * 8))
    full_blocks, rem = divmod(full_eighths, 8)
    return '█' * full_blocks + EIGHTHS[rem]


class BirthdayParadoxApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
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

    #controls {
        height: auto;
        padding: 1 2;
        background: #1e293b;
        margin: 0 2;
    }

    #controls-row {
        height: 3;
        align: center middle;
    }

    Input {
        width: 8;
        background: #0f172a;
        color: #f8fafc;
        border: tall #334155;
    }
    Input:focus { border: tall #38bdf8; }

    RadioSet {
        height: 3;
        background: transparent;
        border: none;
        layout: horizontal;
        width: auto;
    }
    RadioButton {
        margin: 0 1;
        background: transparent;
    }

    #run-btn {
        background: #38bdf8;
        color: #0f172a;
        text-style: bold;
    }

    #chart {
        padding: 1 2;
    }

    #status {
        background: #1e293b;
        color: #cbd5e1;
        padding: 1 2;
        margin: 0 2 1 2;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding('ctrl+r', 'run', 'Run'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]
    TITLE = 'Birthday Paradox'

    def __init__(self) -> None:
        super().__init__()
        self.current_n = DEFAULT_N
        self.current_trials = DEFAULT_TRIALS
        self.matches_by_n: dict[int, int] = {}
        self.trials_used = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('BIRTHDAY PARADOX', id='title')
        yield Static('Probability that any 2 of N people share a birthday',
                     id='subtitle')

        with Vertical(id='controls'):
            with Horizontal(id='controls-row'):
                yield Static('N: ', classes='label')
                yield Input(value=str(DEFAULT_N), id='n-input',
                            max_length=3, restrict=r'\d*')
                yield Static('  Trials: ', classes='label')
                with RadioSet(id='trials'):
                    for t in TRIALS_OPTIONS:
                        label = f'{t // 1000}k' if t >= 1000 else str(t)
                        rb = RadioButton(label, value=(t == DEFAULT_TRIALS),
                                          id=f'trials-{t}')
                        yield rb
                yield Button('Run (Ctrl+R)', id='run-btn', variant='primary')

        yield Static('', id='chart')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._run()

    def action_run(self) -> None:
        self._run()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'run-btn':
            self._run()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'n-input':
            self._update_n_from_input(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'n-input':
            self._update_n_from_input(event.value)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == 'trials':
            label = str(event.pressed.label).strip()
            if label.endswith('k'):
                self.current_trials = int(label[:-1]) * 1000
            else:
                self.current_trials = int(label)

    def _update_n_from_input(self, raw: str) -> None:
        if raw.isdigit():
            n = max(N_MIN, min(N_MAX, int(raw)))
            self.current_n = n
            self._redraw()

    def _run(self) -> None:
        rng = random.Random()
        chart = self.query_one('#chart', Static)
        chart.update('Running simulations…')
        self.refresh()
        self.matches_by_n = {
            n: simulate(n, self.current_trials, rng)
            for n in SAMPLE_NS
        }
        self.trials_used = self.current_trials
        self._redraw()

    def _redraw(self) -> None:
        chart = self.query_one('#chart', Static)
        lines = []
        for n in SAMPLE_NS:
            th = theoretical(n)
            bar = render_bar(th)
            marker = ' ◀ here' if n == self.current_n else ''
            color = 'green' if n == self.current_n else 'cyan'
            lines.append(
                f'[bold]N={n:>3}[/]  '
                f'[{color}]{bar:<{BAR_WIDTH}}[/]  '
                f'{th * 100:6.2f}%[bold green]{marker}[/]'
            )
        chart.update('\n'.join(lines))

        status = self.query_one('#status', Static)
        n = self.current_n
        th = theoretical(n)
        if self.matches_by_n and n in self.matches_by_n:
            m = self.matches_by_n[n]
            emp = m / self.trials_used
            lo, hi = wilson_ci(m, self.trials_used)
            status.update(
                f'[bold]N={n}[/]   '
                f'theoretical [cyan]{th * 100:.2f}%[/]   '
                f'empirical [yellow]{emp * 100:.2f}%[/]   '
                f'95% CI [[/]{lo * 100:.2f}%, {hi * 100:.2f}%[bold]][/]   '
                f'({self.trials_used:,} trials)'
            )
        elif self.matches_by_n:
            status.update(
                f'[bold]N={n}[/]   theoretical [cyan]{th * 100:.2f}%[/]   '
                f'(empirical only at sampled N values; press Ctrl+R)'
            )
        else:
            status.update(
                f'[bold]N={n}[/]   theoretical [cyan]{th * 100:.2f}%[/]'
            )


if __name__ == '__main__':
    BirthdayParadoxApp().run()
