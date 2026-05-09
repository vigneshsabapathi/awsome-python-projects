"""Factor Finder — Textual TUI.

Modern terminal UI for divisor enumeration and prime factorization.

Bindings:
    Enter   — Compute
    Ctrl+P  — Toggle prime-factorization-only view
    Ctrl+Q  — Quit

Run:
    uv run python factor_finder/factor_finder_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Static

from factor_finder import (
    classify,
    divisor_sum,
    euler_totient,
    factors,
    pretty_factorization,
    prime_factorization,
    proper_divisor_sum,
)


CLASS_CHIP_CLASS = {
    'prime':     'chip-prime',
    'perfect':   'chip-perfect',
    'abundant':  'chip-abundant',
    'deficient': 'chip-deficient',
}


class FactorFinderApp(App):
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

    #class-row {
        height: 1;
        align-horizontal: center;
        margin: 0 4 1 4;
    }

    .chip {
        padding: 0 2;
        margin: 0 1;
        height: 1;
        text-style: bold;
    }
    .chip-prime     { background: #a78bfa; color: #0f172a; }
    .chip-perfect   { background: #34d399; color: #0f172a; }
    .chip-abundant  { background: #f59e0b; color: #0f172a; }
    .chip-deficient { background: #38bdf8; color: #0f172a; }
    .chip-error     { background: #f87171; color: #0f172a; }
    .chip-idle      { background: #334155; color: #94a3b8; }

    #class-line {
        color: #cbd5e1;
        padding: 0 1;
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

    #factorization {
        color: #38bdf8;
        text-style: bold;
        padding: 1 0;
    }

    #factor-count {
        color: #94a3b8;
        padding-bottom: 1;
    }

    #factor-list {
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
        Binding('ctrl+p', 'toggle_prime', 'Prime-only'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Factor Finder'

    def __init__(self) -> None:
        super().__init__()
        self.last_n: int | None = None
        self.prime_only: bool = False

    # --------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('FACTOR FINDER', id='title')
        yield Static('Divisors, prime factorization, and number-theory tags',
                     id='subtitle')

        with Horizontal(id='input-row'):
            yield Input(placeholder='Enter a positive integer N, then Enter',
                        id='input')

        with Horizontal(id='class-row'):
            yield Static('IDLE', id='class-chip', classes='chip chip-idle')
            yield Static('Awaiting input…', id='class-line')

        with Horizontal(id='panels'):
            with Vertical(classes='panel'):
                yield Static('Prime factorization', classes='panel-title')
                yield Static('—', id='factorization')
                yield Static('', id='primes-detail', classes='muted')
            with Vertical(classes='panel'):
                yield Static('Divisors', classes='panel-title')
                yield Static('', id='factor-count')
                with VerticalScroll():
                    yield Static('', id='factor-list')

        with Horizontal(id='stats-row'):
            yield Static('σ₀: —', id='stat-sigma0', classes='stat')
            yield Static('σ₁: —', id='stat-sigma1', classes='stat')
            yield Static('s: —', id='stat-aliquot', classes='stat')
            yield Static('φ: —', id='stat-phi', classes='stat')

        yield Static(
            'Enter to compute · Ctrl+P toggle prime-only · Ctrl+Q quit',
            id='footer-hint')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#input', Input).focus()

    # --------------------------------------------------------------- helpers
    def _set_chip(self, label: str) -> None:
        chip = self.query_one('#class-chip', Static)
        chip.update(label.upper())
        css = CLASS_CHIP_CLASS.get(label, 'chip-idle')
        chip.set_classes(f'chip {css}')

    def _set_chip_error(self, message: str) -> None:
        chip = self.query_one('#class-chip', Static)
        chip.update('ERROR')
        chip.set_classes('chip chip-error')
        self.query_one('#class-line', Static).update(message)

    def _apply_prime_only_view(self) -> None:
        """Show/hide the divisor panel content depending on prime-only mode."""
        # Toggle the factor list / count visibility by swapping their text.
        if self.last_n is None:
            return
        if self.prime_only:
            self.query_one('#factor-count', Static).update(
                '[divisor list hidden — Ctrl+P to show]')
            self.query_one('#factor-list', Static).update('')
        else:
            self._refresh_divisors(self.last_n)

    def _refresh_divisors(self, n: int) -> None:
        if n <= 5_000_000:
            divs = factors(n)
            count = len(divs)
            text = ', '.join(str(d) for d in divs)
        else:
            from math import prod
            pf = prime_factorization(n)
            count = prod((e + 1) for e in pf.values()) if pf else 1
            text = '(divisor list suppressed for very large N)'
        self.query_one('#factor-count', Static).update(
            f'{count} divisor{"s" if count != 1 else ""}')
        self.query_one('#factor-list', Static).update(text)

    # --------------------------------------------------------------- actions
    def action_toggle_prime(self) -> None:
        self.prime_only = not self.prime_only
        self._apply_prime_only_view()

    # --------------------------------------------------------------- events
    def on_input_submitted(self, event: Input.Submitted) -> None:
        raw = event.value.strip()
        try:
            n = int(raw)
            if n <= 0:
                raise ValueError('non-positive')
        except ValueError:
            self._set_chip_error('Enter a positive integer.')
            self.query_one('#factorization', Static).update('—')
            self.query_one('#primes-detail', Static).update('')
            self.query_one('#factor-count', Static).update('')
            self.query_one('#factor-list', Static).update('')
            for k in ('sigma0', 'sigma1', 'aliquot', 'phi'):
                self.query_one(f'#stat-{k}', Static).update(
                    {'sigma0': 'σ₀: —', 'sigma1': 'σ₁: —',
                     'aliquot': 's: —', 'phi': 'φ: —'}[k])
            return

        self.last_n = n
        pf = prime_factorization(n)
        label = classify(n)
        sigma1 = divisor_sum(n)
        phi = euler_totient(n)
        aliquot = proper_divisor_sum(n)

        # Class chip + summary line
        self._set_chip(label)
        if label == 'prime':
            note = 'no proper factors except 1'
        elif label == 'perfect':
            note = f's(N) = {aliquot} = N'
        elif label == 'abundant':
            note = f's(N) = {aliquot} > N'
        else:
            note = f's(N) = {aliquot} < N'
        self.query_one('#class-line', Static).update(
            f'N = {n:,} — {note}')

        # Prime factorization
        if pf:
            self.query_one('#factorization', Static).update(
                f'{n} = {pretty_factorization(pf)}')
            details = ', '.join(f'{p}^{e}' for p, e in sorted(pf.items()))
            self.query_one('#primes-detail', Static).update(
                f'Primes: {details}  ·  '
                f'distinct primes ω(N) = {len(pf)}')
        else:
            self.query_one('#factorization', Static).update(
                '1 = 1 (no prime factors)')
            self.query_one('#primes-detail', Static).update('')

        # Divisors panel (respect current prime-only mode)
        self._apply_prime_only_view()
        # Re-derive count for the stats row even if the list is hidden
        if n <= 5_000_000:
            count = len(factors(n))
        else:
            from math import prod
            count = prod((e + 1) for e in pf.values()) if pf else 1

        self.query_one('#stat-sigma0', Static).update(f'σ₀: {count:,}')
        self.query_one('#stat-sigma1', Static).update(f'σ₁: {sigma1:,}')
        self.query_one('#stat-aliquot', Static).update(f's: {aliquot:,}')
        self.query_one('#stat-phi', Static).update(f'φ: {phi:,}')


if __name__ == '__main__':
    FactorFinderApp().run()
