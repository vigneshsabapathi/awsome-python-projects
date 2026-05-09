"""Powerball — Textual TUI.

Pick numbers, draw, simulate, and inspect EV, all in a dark Tailwind-themed
terminal UI. Unicode bar chart shows empirical vs theoretical hit rates.

Bindings: Q quick-pick, D draw, S simulate, Ctrl+Q quit.

Run:
    uv run python powerball/powerball_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from powerball import (
    RED_POOL,
    THEORETICAL_PROBS,
    TICKET_COST,
    TIERS,
    WHITE_POOL,
    WHITE_PICK,
    break_even_jackpot,
    draw,
    expected_value,
    format_drawing,
    prize_for,
    quick_pick,
    score,
    simulate,
)

DEFAULT_JACKPOT = 100_000_000
DEFAULT_TRIALS = 10_000

PLOT_TIERS = tuple(t for t in TIERS if t != 'None')

BAR_WIDTH = 40
EIGHTHS = ('', '▏', '▎', '▍', '▌', '▋', '▊', '▉')


def render_bar(p: float, max_log: float = 9.0, width: int = BAR_WIDTH) -> str:
    """Map probability to a unicode bar via log scale (so jackpot is visible)."""
    if p <= 0:
        return ''
    # log10(p) ranges roughly -9..0; remap to 0..1.
    import math
    frac = max(0.0, min(1.0, 1.0 + math.log10(p) / max_log))
    full_eighths = int(round(frac * width * 8))
    full_eighths = max(0, min(full_eighths, width * 8))
    full, rem = divmod(full_eighths, 8)
    return '█' * full + EIGHTHS[rem]


class PowerballTUI(App):
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
        align: left middle;
    }
    .label {
        color: #cbd5e1;
        margin: 0 1;
    }

    Input {
        width: 14;
        background: #0f172a;
        color: #f8fafc;
        border: tall #334155;
    }
    Input:focus { border: tall #38bdf8; }

    #ticket {
        background: #1e293b;
        color: #38bdf8;
        padding: 1 2;
        margin: 0 2;
        height: auto;
    }

    #chart {
        padding: 1 2;
        margin: 0 2;
        height: auto;
    }

    #status {
        background: #1e293b;
        color: #cbd5e1;
        padding: 1 2;
        margin: 0 2 1 2;
        text-align: center;
        height: auto;
    }

    Button {
        margin: 0 1;
    }
    #draw-btn {
        background: #38bdf8;
        color: #0f172a;
        text-style: bold;
    }
    #sim-btn {
        background: #f59e0b;
        color: #0f172a;
        text-style: bold;
    }
    """

    BINDINGS = [
        Binding('q', 'quick', 'Quick-pick'),
        Binding('d', 'draw', 'Draw'),
        Binding('s', 'simulate', 'Simulate'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]
    TITLE = 'Powerball Lottery'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.ticket: dict | None = None
        self.last_drawing: dict | None = None
        self.last_tier: str | None = None
        self.sim_counts: dict[str, int] | None = None
        self.sim_total = 0
        self.sim_winnings = 0
        self.jackpot = DEFAULT_JACKPOT
        self.trials = DEFAULT_TRIALS

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('POWERBALL LOTTERY', id='title')
        yield Static(
            f'Pick {WHITE_PICK} whites (1..{WHITE_POOL}) + 1 red '
            f'(1..{RED_POOL}). Q quick-pick · D draw · S simulate · Ctrl+Q quit',
            id='subtitle')

        with Vertical(id='controls'):
            with Horizontal(id='controls-row'):
                yield Static('Whites:', classes='label')
                yield Input(value='', placeholder='5 7 11 22 38',
                            id='whites-input')
                yield Static('PB:', classes='label')
                yield Input(value='', placeholder='17', id='pb-input',
                            max_length=3, restrict=r'\d*')
                yield Static('Jackpot $:', classes='label')
                yield Input(value=f'{DEFAULT_JACKPOT}',
                            id='jackpot-input',
                            max_length=12, restrict=r'\d*')
                yield Static('Trials:', classes='label')
                yield Input(value=str(DEFAULT_TRIALS),
                            id='trials-input',
                            max_length=8, restrict=r'\d*')
            with Horizontal(id='controls-row'):
                yield Button('Quick-pick (Q)', id='quick-btn')
                yield Button('Draw (D)', id='draw-btn', variant='primary')
                yield Button('Simulate (S)', id='sim-btn', variant='warning')

        yield Static('', id='ticket')
        yield Static('', id='chart')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_ticket()
        self._redraw_chart()
        self._refresh_status()

    # ---- actions -----------------------------------------------------------

    def action_quick(self) -> None:
        self.ticket = quick_pick(self.rng)
        self.query_one('#whites-input', Input).value = ' '.join(
            str(w) for w in self.ticket['whites'])
        self.query_one('#pb-input', Input).value = str(self.ticket['powerball'])
        self._refresh_ticket()
        self._refresh_status('Quick-pick generated. Press D to draw.')

    def action_draw(self) -> None:
        self._sync_inputs()
        if self.ticket is None:
            self._refresh_status(
                'Need a valid ticket: 5 unique whites + 1 powerball '
                '(or press Q for quick-pick).')
            return
        drawing = draw(self.rng)
        tier = score(self.ticket, drawing)
        self.last_drawing = drawing
        self.last_tier = tier
        prize = prize_for(tier, self.jackpot)
        self._refresh_ticket()
        if tier == '5+PB':
            self._refresh_status(
                f'JACKPOT! ${prize:,}  Drawn: {format_drawing(drawing)}')
        elif tier == 'None':
            self._refresh_status(
                f'No match. Drawn: {format_drawing(drawing)}')
        else:
            self._refresh_status(
                f'Tier {tier}: ${prize:,}.  Drawn: {format_drawing(drawing)}')

    def action_simulate(self) -> None:
        self._sync_inputs()
        try:
            trials = int(self.query_one('#trials-input', Input).value or
                         DEFAULT_TRIALS)
        except ValueError:
            trials = DEFAULT_TRIALS
        trials = max(1, min(trials, 10_000_000))
        ticket = self.ticket  # None -> quick-pick each draw
        self._refresh_status(f'Simulating {trials:,} draws…')
        self.refresh()
        result = simulate(trials, rng=self.rng, ticket=ticket,
                          jackpot=self.jackpot)
        self.sim_counts = result['counts']
        self.sim_total = trials
        self.sim_winnings = result['winnings']
        self._redraw_chart()
        net = result['net']
        mode = 'fixed ticket' if ticket else 'quick-pick each draw'
        self._refresh_status(
            f'Simulated {trials:,} draws ({mode}). '
            f'Spent ${result["spent"]:,}, won ${result["winnings"]:,}, '
            f'net ${net:,}.')

    # ---- input wiring ------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'quick-btn':
            self.action_quick()
        elif event.button.id == 'draw-btn':
            self.action_draw()
        elif event.button.id == 'sim-btn':
            self.action_simulate()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id in ('whites-input', 'pb-input'):
            self._sync_inputs()
            self._refresh_ticket()
        elif event.input.id == 'jackpot-input':
            try:
                self.jackpot = int(event.value or 0)
            except ValueError:
                self.jackpot = 0
            self._redraw_chart()
            self._refresh_status()

    def _sync_inputs(self) -> None:
        whites_raw = self.query_one('#whites-input', Input).value.strip()
        pb_raw = self.query_one('#pb-input', Input).value.strip()
        try:
            jackpot_raw = self.query_one('#jackpot-input', Input).value.strip()
            self.jackpot = int(jackpot_raw) if jackpot_raw else 0
        except ValueError:
            pass

        if not whites_raw or not pb_raw:
            self.ticket = None
            return
        try:
            parts = [int(p) for p in
                     whites_raw.replace(',', ' ').split() if p]
            if len(parts) != WHITE_PICK or len(set(parts)) != WHITE_PICK:
                self.ticket = None
                return
            if any(not (1 <= p <= WHITE_POOL) for p in parts):
                self.ticket = None
                return
            pb = int(pb_raw)
            if not (1 <= pb <= RED_POOL):
                self.ticket = None
                return
            self.ticket = {'whites': tuple(sorted(parts)), 'powerball': pb}
        except ValueError:
            self.ticket = None

    # ---- rendering ---------------------------------------------------------

    def _refresh_ticket(self) -> None:
        widget = self.query_one('#ticket', Static)
        if self.ticket is None:
            widget.update(
                '[dim]Ticket: enter 5 whites + 1 PB above, '
                'or press Q for quick-pick.[/]')
            return
        line = f'[bold]Ticket:[/] {format_drawing(self.ticket)}'
        if self.last_drawing is not None and self.last_tier is not None:
            prize = prize_for(self.last_tier, self.jackpot)
            color = ('yellow' if self.last_tier == '5+PB'
                     else ('green' if self.last_tier != 'None' else 'red'))
            line += (f'\n[bold]Drawn:[/]  {format_drawing(self.last_drawing)}'
                     f'\n[bold]Result:[/] [{color}]{self.last_tier}[/]   '
                     f'prize [yellow]${prize:,}[/]')
        widget.update(line)

    def _redraw_chart(self) -> None:
        chart = self.query_one('#chart', Static)
        lines = ['[bold cyan]Theoretical[/]   vs   [bold yellow]Empirical[/]   '
                 '(log-scale bars, prize $)']
        for tier in PLOT_TIERS:
            th = THEORETICAL_PROBS[tier]
            th_bar = render_bar(th)
            if self.sim_counts is not None and self.sim_total:
                emp = self.sim_counts[tier] / self.sim_total
                emp_bar = render_bar(emp) if emp > 0 else ''
                emp_str = f'{emp * 100:8.4f}%'
            else:
                emp_bar = ''
                emp_str = '       —'
            prize = prize_for(tier, self.jackpot)
            prize_str = f'${prize:>13,}'
            lines.append(
                f'[bold]{tier:<8}[/]  '
                f'[cyan]{th_bar:<{BAR_WIDTH}}[/]  '
                f'th [cyan]{th * 100:8.5f}%[/]  '
                f'emp [yellow]{emp_str}[/]  '
                f'prize [yellow]{prize_str}[/]'
            )
        chart.update('\n'.join(lines))

    def _refresh_status(self, msg: str | None = None) -> None:
        ev = expected_value(self.jackpot)
        ev_pre = expected_value(self.jackpot, tax_rate=0.0)
        be = break_even_jackpot()
        verdict = ('[green]EV > cost ✓[/]' if ev > TICKET_COST
                   else '[red]EV < cost ✗[/]')
        body = (
            f'Jackpot [yellow]${self.jackpot:,}[/]  |  '
            f'EV/ticket: [yellow]${ev:.3f}[/] (after tax), '
            f'[yellow]${ev_pre:.3f}[/] (pre-tax)  |  '
            f'cost [yellow]${TICKET_COST}[/]  {verdict}  |  '
            f'break-even jackpot [yellow]${be:,.0f}[/]'
        )
        if msg:
            body = f'{msg}\n{body}'
        self.query_one('#status', Static).update(body)


if __name__ == '__main__':
    PowerballTUI().run()
