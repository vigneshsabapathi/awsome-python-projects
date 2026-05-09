"""Prime Numbers — Textual TUI.

Sieve up to N rendered as a unicode grid. Toggle between the standard
left-to-right grid and the Ulam spiral (Ctrl+U) to see the famous
diagonal patterns. Stats panel reports pi(N), prime gaps, twin primes.

Bindings:
    Enter   — Recompute with the current N
    Ctrl+U  — Toggle Ulam spiral overlay
    Ctrl+Q  — Quit

Run:
    uv run python primes/primes_tui.py
"""
from __future__ import annotations

import math
from typing import List, Tuple

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from primes import (
    prime_gaps,
    prime_pi,
    sieve,
    twin_primes,
)


PRIME_GLYPH = '#'
TWIN_GLYPH = '*'
COMPOSITE_GLYPH = '.'
ONE_GLYPH = '1'


# ---------------------------------------------------------------------------
# Layout helpers
# ---------------------------------------------------------------------------


def ulam_coords(k: int) -> Tuple[int, int]:
    """Lattice (x, y) for k on the Ulam spiral, 1 at origin."""
    if k == 1:
        return (0, 0)
    m = math.isqrt(k - 1)
    if m % 2 == 0:
        m += 1
    if m * m < k:
        m += 2
    ring = (m - 1) // 2
    offset = m * m - k
    side = 2 * ring
    if offset < side:
        return (ring - offset, -ring)
    offset -= side
    if offset < side:
        return (-ring, -ring + offset)
    offset -= side
    if offset < side:
        return (-ring + offset, ring)
    offset -= side
    return (ring, ring - offset)


def render_linear_grid(n: int, primes_set: set[int],
                       twin_set: set[int], cols: int = 20) -> str:
    """Render integers 1..n in a left-to-right grid with markup."""
    lines: List[str] = []
    line_parts: List[str] = []
    for k in range(1, n + 1):
        if k == 1:
            cell = f'[#f59e0b]{ONE_GLYPH}[/]'
        elif k in twin_set:
            cell = f'[#34d399]{TWIN_GLYPH}[/]'
        elif k in primes_set:
            cell = f'[#a78bfa]{PRIME_GLYPH}[/]'
        else:
            cell = f'[#475569]{COMPOSITE_GLYPH}[/]'
        line_parts.append(cell)
        if len(line_parts) == cols:
            lines.append(' '.join(line_parts))
            line_parts = []
    if line_parts:
        lines.append(' '.join(line_parts))
    return '\n'.join(lines)


def render_ulam_grid(n: int, primes_set: set[int],
                     twin_set: set[int]) -> str:
    """Render 1..n on the Ulam spiral, centered."""
    coords = [ulam_coords(k) for k in range(1, n + 1)]
    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    width = x_max - x_min + 1
    height = y_max - y_min + 1

    grid = [[' ' for _ in range(width)] for _ in range(height)]
    for k, (gx, gy) in enumerate(coords, start=1):
        col = gx - x_min
        # Flip Y so up on the spiral renders up in the grid.
        row = (y_max - gy)
        if k == 1:
            grid[row][col] = f'[#f59e0b]{ONE_GLYPH}[/]'
        elif k in twin_set:
            grid[row][col] = f'[#34d399]{TWIN_GLYPH}[/]'
        elif k in primes_set:
            grid[row][col] = f'[#a78bfa]{PRIME_GLYPH}[/]'
        else:
            grid[row][col] = f'[#475569]{COMPOSITE_GLYPH}[/]'

    return '\n'.join(' '.join(row) for row in grid)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


class PrimesApp(App):
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

    #input-row {
        height: 3;
        align-horizontal: center;
        margin: 1 4;
    }

    #input {
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
        width: 1fr;
    }
    #input:focus {
        border: tall #38bdf8;
    }

    #mode-row {
        height: 1;
        align-horizontal: center;
        margin: 0 4 1 4;
    }

    .chip {
        padding: 0 2;
        margin: 0 1;
        height: 1;
        text-style: bold;
        background: #334155;
        color: #f8fafc;
    }
    .chip-active {
        background: #38bdf8;
        color: #0f172a;
    }

    #panels {
        height: 1fr;
        margin: 0 4;
    }

    .panel {
        background: #1e293b;
        border: round #334155;
        padding: 1 2;
        margin: 0 1;
        height: 1fr;
    }

    .panel-title {
        text-style: bold;
        color: #f8fafc;
        padding-bottom: 1;
    }

    .muted {
        color: #94a3b8;
    }

    #grid {
        color: #f8fafc;
    }

    #stats-row {
        height: 1;
        margin: 0 4 0 4;
    }

    .stat {
        width: 1fr;
        text-align: center;
        background: #1e293b;
        color: #f8fafc;
        margin: 0 1;
    }

    #footer-hint {
        color: #94a3b8;
        text-align: center;
        padding: 1 0;
    }
    """

    BINDINGS = [
        Binding('ctrl+u', 'toggle_ulam', 'Ulam spiral'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Prime Numbers'

    def __init__(self) -> None:
        super().__init__()
        self.last_n: int = 100
        self.ulam: bool = False

    # --------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('PRIME NUMBERS', id='title')
        yield Static('Sieve of Eratosthenes · Ulam spiral · pi(N) and gaps',
                     id='subtitle')

        with Horizontal(id='input-row'):
            yield Input(value='100',
                        placeholder='N (10..2000) — Enter to compute',
                        id='input')

        with Horizontal(id='mode-row'):
            yield Static('LINEAR', id='mode-linear', classes='chip chip-active')
            yield Static('ULAM', id='mode-ulam', classes='chip')

        with Horizontal(id='panels'):
            with Vertical(classes='panel'):
                yield Static('Sieve grid', classes='panel-title')
                yield Static('# prime · * twin · . composite · 1 unit',
                             classes='muted')
                yield Static('', id='grid')
            with Vertical(classes='panel'):
                yield Static('Stats', classes='panel-title')
                yield Static('—', id='stat-pi')
                yield Static('—', id='stat-largest')
                yield Static('—', id='stat-avg-gap')
                yield Static('—', id='stat-max-gap')
                yield Static('—', id='stat-twins')
                yield Static('', id='stat-twin-list', classes='muted')

        with Horizontal(id='stats-row'):
            yield Static('mode: LINEAR', id='mode-readout', classes='stat')

        yield Static(
            'Enter recompute · Ctrl+U toggle Ulam spiral · Ctrl+Q quit',
            id='footer-hint')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#input', Input).focus()
        self._recompute()

    # --------------------------------------------------------------- helpers
    def _set_mode_chip(self) -> None:
        linear = self.query_one('#mode-linear', Static)
        ulam = self.query_one('#mode-ulam', Static)
        if self.ulam:
            linear.set_classes('chip')
            ulam.set_classes('chip chip-active')
            self.query_one('#mode-readout', Static).update('mode: ULAM')
        else:
            linear.set_classes('chip chip-active')
            ulam.set_classes('chip')
            self.query_one('#mode-readout', Static).update('mode: LINEAR')

    def _recompute(self) -> None:
        n = self.last_n
        primes_list = sieve(n)
        primes_set = set(primes_list)
        twins = twin_primes(primes_list)
        twin_members: set[int] = set()
        for p, q in twins:
            twin_members.add(p)
            twin_members.add(q)

        # Render grid
        if self.ulam:
            text = render_ulam_grid(n, primes_set, twin_members)
        else:
            cols = 20 if n <= 400 else 30 if n <= 900 else 40
            text = render_linear_grid(n, primes_set, twin_members, cols=cols)
        self.query_one('#grid', Static).update(text)

        # Stats
        gaps = prime_gaps(primes_list)
        avg_gap = (sum(gaps) / len(gaps)) if gaps else 0.0
        max_gap = max(gaps) if gaps else 0

        self.query_one('#stat-pi', Static).update(
            f'[#38bdf8]pi(N)[/]    = {prime_pi(n):,}')
        self.query_one('#stat-largest', Static).update(
            f'[#a78bfa]largest[/]  = '
            f'{primes_list[-1] if primes_list else "—"}')
        self.query_one('#stat-avg-gap', Static).update(
            f'[#94a3b8]avg gap[/]  = {avg_gap:.2f}')
        self.query_one('#stat-max-gap', Static).update(
            f'[#94a3b8]max gap[/]  = {max_gap}')
        self.query_one('#stat-twins', Static).update(
            f'[#34d399]twin pairs[/] = {len(twins):,}')

        if twins:
            preview = ', '.join(f'({p},{q})' for p, q in twins[:6])
            if len(twins) > 6:
                preview += ', …'
            self.query_one('#stat-twin-list', Static).update(preview)
        else:
            self.query_one('#stat-twin-list', Static).update(
                '(no twin primes in range)')

        self._set_mode_chip()

    # --------------------------------------------------------------- actions
    def action_toggle_ulam(self) -> None:
        self.ulam = not self.ulam
        self._recompute()

    # --------------------------------------------------------------- events
    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        try:
            n = int(raw)
        except ValueError:
            self.query_one('#grid', Static).update(
                '[#f87171]Enter a positive integer N.[/]')
            return
        # Clamp to a sensible TUI range — past 10k the grid blows up.
        n = max(2, min(n, 10000))
        self.last_n = n
        self._recompute()


if __name__ == '__main__':
    PrimesApp().run()
