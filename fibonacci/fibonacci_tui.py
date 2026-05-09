"""Fibonacci — Textual TUI.

Type N, hit Enter to compute. Cycle algorithm with Ctrl+A.
Ctrl+B benchmarks every algorithm. Ctrl+Q quits.

Run:
    uv run python fibonacci/fibonacci_tui.py
"""
from __future__ import annotations

import math
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from fibonacci import ALGORITHMS, RECURSIVE_MAX, benchmark, compute

PHI = (1.0 + math.sqrt(5.0)) / 2.0


class FibonacciApp(App):
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

    #controls {
        height: auto;
        align-horizontal: center;
        padding: 0 2;
    }

    .label {
        color: #94a3b8;
        padding: 1 1 0 1;
    }

    .algo-chip {
        background: #1e293b;
        color: #38bdf8;
        text-style: bold;
        padding: 1 2;
        margin: 0 1;
    }

    #input {
        margin: 1 6;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus {
        border: tall #38bdf8;
    }

    #output {
        margin: 1 4;
        padding: 1 2;
        background: #1e293b;
        color: #f8fafc;
        height: auto;
        min-height: 8;
        border: tall #334155;
    }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-ok    { color: #34d399; text-style: bold; }
    .status-gold  { color: #f59e0b; text-style: bold; }
    """

    BINDINGS = [
        Binding('ctrl+a', 'cycle_algo', 'Cycle Algorithm'),
        Binding('ctrl+b', 'benchmark', 'Benchmark All'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Fibonacci'

    def __init__(self) -> None:
        super().__init__()
        self.algo_index = 0  # ALGORITHMS[0] == 'iter'

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('FIBONACCI', id='title')
        yield Static('F(n) = F(n-1) + F(n-2)  —  five algorithms',
                     id='subtitle')
        with Horizontal(id='controls'):
            yield Static('algorithm:', classes='label')
            yield Static(self._algo_chip_text(), id='algo', classes='algo-chip')
        yield Input(placeholder='Enter N (non-negative integer), then Enter',
                    id='input')
        yield Static('Output appears here.', id='output')
        yield Static('Ready', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#input', Input).focus()

    # ---------- Helpers ----------

    def _algo_chip_text(self) -> str:
        return f'< {ALGORITHMS[self.algo_index]} >'

    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    def _set_output(self, text: str) -> None:
        self.query_one('#output', Static).update(text)

    def _parse_n(self, raw: str) -> int | None:
        raw = raw.strip()
        try:
            n = int(raw)
        except ValueError:
            self._set_status(f'Not an integer: {raw!r}', 'error')
            return None
        if n < 0:
            self._set_status('N must be non-negative', 'error')
            return None
        return n

    # ---------- Actions ----------

    def action_cycle_algo(self) -> None:
        self.algo_index = (self.algo_index + 1) % len(ALGORITHMS)
        self.query_one('#algo', Static).update(self._algo_chip_text())
        self._set_status(
            f'algorithm = {ALGORITHMS[self.algo_index]}', 'info')

    def action_benchmark(self) -> None:
        raw = self.query_one('#input', Input).value
        n = self._parse_n(raw or '20')
        if n is None:
            return
        results = benchmark(n)
        if not results:
            self._set_status('Nothing to benchmark', 'error')
            return
        fastest = min(results, key=lambda a: results[a][1])
        lines = [f'Benchmark for F({n})', '']
        for algo in ALGORITHMS:
            if algo not in results:
                lines.append(f'  {algo:<10} skipped (n > {RECURSIVE_MAX})')
                continue
            _, secs = results[algo]
            tag = '   <-- fastest' if algo == fastest else ''
            lines.append(f'  {algo:<10} {secs * 1000:>10.3f} ms{tag}')
        self._set_output('\n'.join(lines))
        self._set_status(f'fastest: {fastest}', 'ok')

    # ---------- Events ----------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        n = self._parse_n(event.value)
        if n is None:
            return
        algo = ALGORITHMS[self.algo_index]
        if algo == 'recursive' and n > RECURSIVE_MAX:
            self._set_status(
                f'naive recursion blocked for n > {RECURSIVE_MAX}', 'error')
            return

        try:
            start = time.perf_counter()
            value = compute(n, algo)
            secs = time.perf_counter() - start
        except (ValueError, RecursionError) as exc:
            self._set_status(str(exc), 'error')
            return

        shown = str(value)
        digits = len(shown)
        if digits > 200:
            shown = shown[:100] + '\n  ...\n' + shown[-50:]

        ratio_line = ''
        if n >= 2:
            try:
                fn = compute(n, 'iter')
                fn1 = compute(n - 1, 'iter')
                ratio = fn / fn1 if fn1 else float('inf')
                err = abs(ratio - PHI)
                ratio_line = (
                    f'\nF({n})/F({n - 1}) = {ratio:.12f}'
                    f'   phi = {PHI:.12f}'
                    f'   |err| = {err:.2e}')
            except (OverflowError, ZeroDivisionError):
                ratio_line = '\nratio: (too large for float)'

        out = (
            f'F({n}) via {algo}  ({digits:,} digits, {secs * 1000:.3f} ms)\n\n'
            f'{shown}'
            f'{ratio_line}')
        self._set_output(out)
        self._set_status(f'computed F({n}) in {secs * 1000:.3f} ms', 'gold')


if __name__ == '__main__':
    FibonacciApp().run()
