"""Million Dice Statistics — Textual TUI.

Modern terminal UI: tweak dice count / rolls / sides, hit Enter (or Run),
see a unicode bar chart of the sum distribution with a Normal CLT overlay
marker (μ, μ±σ, μ±2σ).

Bindings:
    Enter   recompute
    Ctrl+R  recompute
    Ctrl+Q  quit

Run:
    uv run python million_dice/million_dice_tui.py
"""
from __future__ import annotations

import math

import numpy as np
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button, Footer, Header, Input, RadioButton, RadioSet, Static,
)

from million_dice import simulate

DICE_MIN, DICE_MAX = 1, 10
ROLLS_OPTIONS = (1_000, 10_000, 100_000, 1_000_000)
SIDES_OPTIONS = (4, 6, 8, 10, 12, 20)
DEFAULT_DICE = 2
DEFAULT_ROLLS = 100_000
DEFAULT_SIDES = 6

BAR_WIDTH = 50
EIGHTHS = ('', '▏', '▎', '▍', '▌', '▋', '▊', '▉')


def render_bar(p: float, peak: float, width: int = BAR_WIDTH) -> str:
    """Render a value `p` (relative to `peak`) as a unicode bar."""
    if peak <= 0:
        return ''
    frac = max(0.0, min(1.0, p / peak))
    full_eighths = int(round(frac * width * 8))
    full_blocks, rem = divmod(full_eighths, 8)
    return '█' * full_blocks + EIGHTHS[rem]


def fmt_rolls(n: int) -> str:
    if n >= 1_000_000:
        return f'{n // 1_000_000}M'
    if n >= 1_000:
        return f'{n // 1000}k'
    return str(n)


class MillionDiceApp(App):
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

    .row {
        height: 3;
        align: left middle;
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

    .label {
        color: #f8fafc;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding('enter', 'run', 'Run', show=True),
        Binding('ctrl+r', 'run', 'Run'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]
    TITLE = 'Million Dice Statistics'

    def __init__(self) -> None:
        super().__init__()
        self.current_dice = DEFAULT_DICE
        self.current_rolls = DEFAULT_ROLLS
        self.current_sides = DEFAULT_SIDES
        self.result: dict | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MILLION DICE STATISTICS', id='title')
        yield Static('Roll N dice many times — watch the CLT bell curve emerge',
                     id='subtitle')

        with Vertical(id='controls'):
            with Horizontal(classes='row'):
                yield Static('Dice (1-10): ', classes='label')
                yield Input(value=str(DEFAULT_DICE), id='dice-input',
                            max_length=2, restrict=r'\d*')
                yield Static('  Rolls: ', classes='label')
                with RadioSet(id='rolls'):
                    for t in ROLLS_OPTIONS:
                        yield RadioButton(fmt_rolls(t),
                                          value=(t == DEFAULT_ROLLS),
                                          id=f'rolls-{t}')
            with Horizontal(classes='row'):
                yield Static('Sides: ', classes='label')
                with RadioSet(id='sides'):
                    for s in SIDES_OPTIONS:
                        yield RadioButton(f'd{s}',
                                          value=(s == DEFAULT_SIDES),
                                          id=f'sides-{s}')
                yield Button('Run (Enter)', id='run-btn', variant='primary')

        yield Static('', id='chart')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._run()

    # ------------------------------------------------------------ events

    def action_run(self) -> None:
        self._run()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'run-btn':
            self._run()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'dice-input':
            self._update_dice(event.value)
            self._run()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'dice-input':
            self._update_dice(event.value)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        rsid = event.radio_set.id
        label = str(event.pressed.label).strip()
        if rsid == 'rolls':
            if label.endswith('M'):
                self.current_rolls = int(label[:-1]) * 1_000_000
            elif label.endswith('k'):
                self.current_rolls = int(label[:-1]) * 1_000
            else:
                self.current_rolls = int(label)
        elif rsid == 'sides':
            self.current_sides = int(label.lstrip('d'))

    def _update_dice(self, raw: str) -> None:
        if raw.isdigit():
            self.current_dice = max(DICE_MIN, min(DICE_MAX, int(raw)))

    # ----------------------------------------------------------- compute

    def _run(self) -> None:
        chart = self.query_one('#chart', Static)
        chart.update(
            f'Rolling {self.current_dice}d{self.current_sides} × '
            f'{self.current_rolls:,}…')
        self.refresh()

        rng = np.random.default_rng()
        self.result = simulate(self.current_dice, self.current_rolls,
                               self.current_sides, rng=rng)
        self._redraw()

    # ------------------------------------------------------------- draw

    def _redraw(self) -> None:
        r = self.result
        chart = self.query_one('#chart', Static)
        status = self.query_one('#status', Static)
        if r is None:
            chart.update('(no data)')
            return

        counts = r['counts']
        keys = sorted(counts.keys())
        peak = max(counts.values()) if counts else 1
        rolls = r['num_rolls']
        mean = r['theoretical_mean']
        std = r['theoretical_std']

        label_w = max(len(str(k)) for k in keys)

        # CLT shape hint
        n = r['num_dice']
        shape = {1: 'uniform (flat)',
                 2: 'triangular',
                 3: 'near-normal',
                 4: 'near-normal'}.get(n, 'normal (CLT)')

        lines: list[str] = []
        lines.append(
            f'[bold]{n}d{r["sides"]} → expected shape: '
            f'[cyan]{shape}[/][/]\n'
        )

        # Down-sample if there are too many bars
        max_rows = 28
        bin_size = max(1, math.ceil(len(keys) / max_rows))

        for i in range(0, len(keys), bin_size):
            chunk = keys[i:i + bin_size]
            v = sum(counts[k] for k in chunk)
            label = (str(chunk[0]) if len(chunk) == 1
                     else f'{chunk[0]}-{chunk[-1]}')
            bar = render_bar(v, peak)
            pct = v / rolls * 100

            # Color the bar by σ-band of its center
            center = (chunk[0] + chunk[-1]) / 2
            if std > 0:
                z = abs(center - mean) / std
                if z <= 1:
                    color = 'green'
                elif z <= 2:
                    color = 'cyan'
                elif z <= 3:
                    color = 'yellow'
                else:
                    color = 'red'
            else:
                color = 'cyan'

            marker = ''
            if std > 0:
                if abs(center - mean) < 0.5 * bin_size:
                    marker = '  [bold green]◀ μ[/]'
                elif abs(center - (mean - std)) < 0.5 * bin_size:
                    marker = '  [green]◀ μ-σ[/]'
                elif abs(center - (mean + std)) < 0.5 * bin_size:
                    marker = '  [green]◀ μ+σ[/]'

            lines.append(
                f'  [bold]{label:>{label_w}}[/]  '
                f'[{color}]{bar:<{BAR_WIDTH}}[/]  '
                f'{v:>10,}  {pct:6.2f}%{marker}'
            )
        chart.update('\n'.join(lines))

        dm = r['mean'] - mean
        ds = r['std'] - std
        status.update(
            f'[bold]empirical[/]  μ=[cyan]{r["mean"]:.4f}[/]  '
            f'σ=[cyan]{r["std"]:.4f}[/]  '
            f'min=[cyan]{r["min"]}[/]  max=[cyan]{r["max"]}[/]   '
            f'[bold]theory[/]  μ=[yellow]{mean:.4f}[/]  '
            f'σ=[yellow]{std:.4f}[/]   '
            f'Δμ={dm:+.4f}  Δσ={ds:+.4f}'
        )


if __name__ == '__main__':
    MillionDiceApp().run()
