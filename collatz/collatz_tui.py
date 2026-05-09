"""Collatz Sequence — Textual TUI.

Dark Tailwind palette. Type any positive integer, press Enter, and watch the
hailstone sequence render as a unicode bar chart (eighth-block resolution),
one row per step.

Keys:
  Enter   compute sequence for the n in the input
  Ctrl+R  reroll a random n in [1, 1_000_000)
  Ctrl+Q  quit

Run:
    uv run python collatz/collatz_tui.py
"""
from __future__ import annotations

import math
import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from collatz import collatz_sequence

DEFAULT_N = 27
BAR_WIDTH = 60   # max chars for a bar
EIGHTHS = ('', '▏', '▎', '▍', '▌', '▋', '▊', '▉')
MAX_ROWS = 600   # cap rendered rows for very long paths


def render_bar(value: int, peak: int, width: int = BAR_WIDTH,
               log_scale: bool = True) -> str:
    """Render a value as a unicode bar of given max width.

    With log_scale=True we map log(value) into [0, width]; this keeps the
    chart readable even when peaks are 1000x the stops. Without it small
    values vanish to nothing.
    """
    if peak <= 1:
        return ''
    if log_scale:
        # log1p so value=0 maps to 0 cleanly (although Collatz never hits 0).
        ratio = math.log1p(value - 1) / math.log1p(peak - 1)
    else:
        ratio = value / peak
    ratio = max(0.0, min(1.0, ratio))
    full_eighths = int(round(ratio * width * 8))
    full_eighths = max(0, min(full_eighths, width * 8))
    full_blocks, rem = divmod(full_eighths, 8)
    return '█' * full_blocks + EIGHTHS[rem]


class CollatzApp(App):
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
        width: 18;
        background: #0f172a;
        color: #f8fafc;
        border: tall #334155;
    }
    Input:focus { border: tall #38bdf8; }

    #stats {
        background: #1e293b;
        color: #cbd5e1;
        padding: 1 2;
        margin: 0 2;
        text-align: center;
    }

    #chart {
        padding: 1 2;
        height: 1fr;
        overflow-y: auto;
        background: #0b1220;
        margin: 0 2 1 2;
    }

    .label {
        padding: 1 1;
        color: #94a3b8;
    }
    """

    BINDINGS = [
        Binding('ctrl+r', 'reroll', 'Random n'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]
    TITLE = 'Collatz Sequence'

    def __init__(self) -> None:
        super().__init__()
        self.current_n: int = DEFAULT_N
        self.current_seq: list[int] = collatz_sequence(DEFAULT_N)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('COLLATZ SEQUENCE', id='title')
        yield Static(
            'Hailstone path:  even -> n/2,  odd -> 3n+1,  stop at 1',
            id='subtitle',
        )

        with Vertical(id='controls'):
            with Horizontal(id='controls-row'):
                yield Static('n: ', classes='label')
                yield Input(value=str(DEFAULT_N), id='n-input',
                            max_length=18, restrict=r'\d*')
                yield Static(
                    '  press Enter to plot, Ctrl+R for random',
                    classes='label')

        yield Static('', id='stats')
        yield Static('', id='chart')
        yield Footer()

    def on_mount(self) -> None:
        self._redraw()
        self.query_one('#n-input', Input).focus()

    def action_reroll(self) -> None:
        n = random.randint(1, 1_000_000)
        self.current_n = n
        self.current_seq = collatz_sequence(n)
        inp = self.query_one('#n-input', Input)
        inp.value = str(n)
        self._redraw()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != 'n-input':
            return
        raw = event.value.strip()
        if not raw or not raw.isdigit():
            self._set_stats(
                '[red]Enter a positive integer.[/]')
            return
        n = int(raw)
        if n <= 0:
            self._set_stats('[red]n must be positive.[/]')
            return
        self.current_n = n
        try:
            self.current_seq = collatz_sequence(n)
        except RecursionError:
            self._set_stats('[red]Sequence too long to render.[/]')
            return
        self._redraw()

    def _set_stats(self, markup: str) -> None:
        self.query_one('#stats', Static).update(markup)

    def _redraw(self) -> None:
        seq = self.current_seq
        n = self.current_n
        steps = len(seq) - 1
        peak = max(seq)

        # Stats line (status bar above the chart).
        ratio = peak / n if n else 0
        self._set_stats(
            f'[bold]n = {n:,}[/]   '
            f'[cyan]steps = {steps}[/]   '
            f'[yellow]peak = {peak:,}[/]   '
            f'[#94a3b8]peak/n = {ratio:.2f}x[/]'
        )

        # Build bar-chart rows.
        chart = self.query_one('#chart', Static)
        shown_seq = seq[:MAX_ROWS]
        idx_w = len(str(len(seq) - 1))
        val_w = len(f'{peak:,}')

        lines: list[str] = []
        for i, v in enumerate(shown_seq):
            bar = render_bar(v, peak, log_scale=True)
            # Color: green for the final 1, yellow at the peak, cyan otherwise.
            if v == peak:
                color = 'yellow'
            elif v == 1:
                color = 'green'
            else:
                color = 'cyan'
            lines.append(
                f'[#94a3b8]{i:>{idx_w}}[/]  '
                f'[bold]{v:>{val_w},}[/]  '
                f'[{color}]{bar}[/]'
            )
        if len(seq) > MAX_ROWS:
            lines.append(
                f'[#94a3b8]… {len(seq) - MAX_ROWS} more rows hidden …[/]')
        chart.update('\n'.join(lines))


if __name__ == '__main__':
    CollatzApp().run()
