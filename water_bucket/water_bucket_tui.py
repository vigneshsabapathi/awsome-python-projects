"""Water Bucket Puzzle — Textual TUI.

Two ASCII-art buckets rendered side-by-side with █ bars showing the current
water levels. Six keybindings (1-6) trigger the bucket operations; S
auto-plays the BFS solution; R resets; Ctrl+Q quits.

Run:
    uv run python water_bucket/water_bucket_tui.py
"""
from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from water_bucket import (
    OP_LABEL,
    Buckets,
    is_solvable,
    solve,
)

# Tailwind dark palette — matches the GUI for visual consistency.
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

#main-row {
    height: auto;
    align-horizontal: center;
    margin-top: 1;
}

#buckets-panel {
    width: 40;
    border: round #334155;
    background: #111827;
    padding: 1 2;
    margin-right: 2;
}

#controls-panel {
    width: 42;
    border: round #334155;
    background: #1e293b;
    padding: 1 2;
}

#bucket-display {
    height: auto;
    align-horizontal: center;
}

.bucket-art {
    width: 16;
    height: auto;
    color: #7dd3fc;
    text-style: bold;
    margin: 0 1;
}

#target-label {
    text-align: center;
    color: #eab308;
    margin-top: 1;
    text-style: bold;
}

#state-label {
    text-align: center;
    color: #94a3b8;
    margin-top: 1;
}

.op-key {
    color: #38bdf8;
    text-style: bold;
}

.op-label {
    color: #f8fafc;
}

#ops-list {
    height: auto;
    margin-bottom: 1;
}

.op-row {
    height: 1;
}

#hint-label {
    color: #94a3b8;
    margin-top: 1;
    height: auto;
}

#status {
    text-align: center;
    padding: 1;
    height: 3;
}

.status-info  { color: #cbd5e1; }
.status-error { color: #f87171; text-style: bold; }
.status-win   { color: #34d399; text-style: bold; }
.status-solving { color: #eab308; text-style: bold; }
"""

# Default puzzle — Die Hard 3.
DEFAULT_A = 3
DEFAULT_B = 5
DEFAULT_TARGET = 4

# Delay between auto-solve steps (seconds).
SOLVE_DELAY = 0.55

# Number of rows in the ASCII bucket art (water column height).
BUCKET_ROWS = 8


def _render_bucket(label: str, level: int, capacity: int,
                   target: int) -> str:
    """Return multi-line ASCII art for one bucket.

    The bucket is drawn as a column of BUCKET_ROWS rows; each row is
    either full (█) or empty (░). A target marker (◄) is shown at the
    appropriate row when target <= capacity.
    """
    rows: list[str] = []
    # Top cap — open.
    rows.append(f'  {label}:{level:>2}/{capacity:<2}  ')
    rows.append(' ┌────────┐ ')
    for r in range(BUCKET_ROWS - 1, -1, -1):
        # r == 0 is the bottom row; r == BUCKET_ROWS-1 is the top.
        # A row is filled if level / capacity > r / BUCKET_ROWS.
        threshold = r / BUCKET_ROWS
        ratio = level / capacity if capacity > 0 else 0.0
        filled = ratio > threshold
        bar = '████████' if filled else '░░░░░░░░'

        # Target marker on the right side of the bucket, outside the wall.
        target_ratio = target / capacity if capacity > 0 else -1.0
        # Show marker on the row just above or at the target fill line.
        show_target = (
            target <= capacity and
            abs(target_ratio - (r + 0.5) / BUCKET_ROWS) < (0.5 / BUCKET_ROWS)
        )
        marker = '◄' if show_target else ' '
        rows.append(f' │{bar}│{marker}')
    rows.append(' └────────┘ ')
    return '\n'.join(rows)


class WaterBucketTUI(App):
    CSS = CSS

    BINDINGS = [
        Binding('1', 'op_fill_a',      'Fill A',      show=False),
        Binding('2', 'op_fill_b',      'Fill B',      show=False),
        Binding('3', 'op_empty_a',     'Empty A',     show=False),
        Binding('4', 'op_empty_b',     'Empty B',     show=False),
        Binding('5', 'op_pour_a_to_b', 'Pour A→B',    show=False),
        Binding('6', 'op_pour_b_to_a', 'Pour B→A',    show=False),
        Binding('s', 'solve',          'Solve',       show=True),
        Binding('r', 'reset',          'Reset',       show=True),
        Binding('ctrl+q', 'quit',      'Quit',        show=True),
    ]

    TITLE = 'Water Bucket Puzzle'

    def __init__(self) -> None:
        super().__init__()
        self.a_cap = DEFAULT_A
        self.b_cap = DEFAULT_B
        self.target = DEFAULT_TARGET
        self.buckets = Buckets(self.a_cap, self.b_cap)
        self._solving = False

    # ------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('WATER BUCKET PUZZLE', id='title')
        yield Static('Die Hard 3 — measure exactly C liters', id='subtitle')
        with Horizontal(id='main-row'):
            with Vertical(id='buckets-panel'):
                with Horizontal(id='bucket-display'):
                    yield Static('', id='bucket-a', classes='bucket-art')
                    yield Static('', id='bucket-b', classes='bucket-art')
                yield Static('', id='target-label')
                yield Static('', id='state-label')
            with Vertical(id='controls-panel'):
                yield Static(
                    '[b]Key  Operation[/b]', id='ops-header',
                    markup=True)
                with Vertical(id='ops-list'):
                    ops = [
                        ('1', 'Fill A'),
                        ('2', 'Fill B'),
                        ('3', 'Empty A'),
                        ('4', 'Empty B'),
                        ('5', 'Pour A → B'),
                        ('6', 'Pour B → A'),
                        ('S', 'Auto-solve (BFS)'),
                        ('R', 'Reset'),
                    ]
                    for key, lbl in ops:
                        yield Static(
                            f'[bold cyan]{key}[/bold cyan]  {lbl}',
                            classes='op-row',
                            markup=True,
                        )
                yield Static(
                    f'Setup: A={self.a_cap}L  B={self.b_cap}L  '
                    f'Target={self.target}L\n'
                    'Edit water_bucket_tui.py to change capacities.',
                    id='hint-label',
                )
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_display()
        self._set_status(
            f'A={self.a_cap}L  B={self.b_cap}L  target={self.target}L  '
            'Press 1-6 to operate, S to solve, R to reset.',
            'info',
        )

    # ------------------------------------------------------------------
    def _refresh_display(self) -> None:
        a, b = self.buckets.state
        self.query_one('#bucket-a', Static).update(
            _render_bucket('A', a, self.a_cap, self.target))
        self.query_one('#bucket-b', Static).update(
            _render_bucket('B', b, self.b_cap, self.target))
        self.query_one('#target-label', Static).update(
            f'Target: {self.target} L')
        self.query_one('#state-label', Static).update(
            f'State: A={a}  B={b}')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        w = self.query_one('#status', Static)
        w.update(text)
        w.set_classes(f'status-{kind}')

    def _check_win(self) -> bool:
        a, b = self.buckets.state
        if a == self.target or b == self.target:
            self._set_status(
                f'Target {self.target} L reached!  state = ({a}, {b})',
                'win',
            )
            return True
        return False

    # ------------------------------------------------------------------
    def _do_op(self, op: str) -> None:
        if self._solving:
            return
        self.buckets.apply(op)
        self._refresh_display()
        if not self._check_win():
            a, b = self.buckets.state
            self._set_status(
                f'{OP_LABEL[op]}  →  ({a}, {b})', 'info')

    def action_op_fill_a(self)      -> None: self._do_op('fill_a')
    def action_op_fill_b(self)      -> None: self._do_op('fill_b')
    def action_op_empty_a(self)     -> None: self._do_op('empty_a')
    def action_op_empty_b(self)     -> None: self._do_op('empty_b')
    def action_op_pour_a_to_b(self) -> None: self._do_op('pour_a_to_b')
    def action_op_pour_b_to_a(self) -> None: self._do_op('pour_b_to_a')

    def action_reset(self) -> None:
        self._solving = False
        self.buckets.reset()
        self._refresh_display()
        self._set_status('Reset.  Press 1-6 to operate, S to solve.', 'info')

    def action_solve(self) -> None:
        if self._solving:
            return
        if not is_solvable(self.a_cap, self.b_cap, self.target):
            self._set_status(
                f'Unsolvable: target={self.target} not reachable '
                f'with A={self.a_cap}, B={self.b_cap}.',
                'error',
            )
            return
        ops = solve(self.a_cap, self.b_cap, self.target)
        if not ops:
            self._set_status('Target is 0 — already there.', 'win')
            return
        self.buckets.reset()
        self._refresh_display()
        self._set_status(
            f'Solving in {len(ops)} step(s)…', 'solving')
        self._solving = True
        self.run_worker(self._play_solution(ops), exclusive=True)

    async def _play_solution(self, ops: list[str]) -> None:
        for i, op in enumerate(ops):
            if not self._solving:
                return
            self.buckets.apply(op)
            self._refresh_display()
            a, b = self.buckets.state
            self._set_status(
                f'Step {i + 1}/{len(ops)}: {OP_LABEL[op]}  →  ({a}, {b})',
                'solving',
            )
            await asyncio.sleep(SOLVE_DELAY)
        self._solving = False
        self._check_win()


if __name__ == '__main__':
    WaterBucketTUI().run()
