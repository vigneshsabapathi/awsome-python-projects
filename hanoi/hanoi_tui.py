"""Tower of Hanoi — Textual TUI.

Dark Tailwind-inspired terminal UI with three ASCII pegs.
Bindings:
    1 / 2 / 3   — first press selects source peg (A/B/C),
                  second press picks destination
    s           — auto-solve from the current state
    n           — new game (resets to all-on-A)
    + / -       — increase / decrease disk count (3..10)
    i           — toggle iterative parity solver
    Ctrl+Q      — quit

Run:
    uv run python hanoi/hanoi_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from hanoi import PEGS, Hanoi, solve_iterative, solve_recursive

PEG_INDEX = {'1': 'A', '2': 'B', '3': 'C'}

# Disk colors mirror the GUI palette so the two flavors feel related.
DISK_COLORS = (
    '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16',
    '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6', '#a855f7',
)


class HanoiApp(App):
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

    #board-row {
        height: auto;
        align-horizontal: center;
    }

    .peg-col {
        width: 28;
        height: auto;
        align-horizontal: center;
        padding: 0 1;
    }

    .peg-col.selected {
        background: #1e3a8a;
    }

    .peg-art {
        height: auto;
        text-align: center;
        color: #f8fafc;
    }

    .peg-label {
        text-align: center;
        text-style: bold;
        color: #cbd5e1;
        padding-top: 1;
    }

    #info {
        text-align: center;
        color: #94a3b8;
        padding: 1;
    }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-win   { color: #34d399; text-style: bold; }
    .status-busy  { color: #38bdf8; text-style: bold; }

    #explain {
        background: #1e293b;
        color: #cbd5e1;
        padding: 1 2;
        margin: 1 4;
        height: auto;
        border: tall #334155;
    }
    """

    BINDINGS = [
        Binding('1', 'pick(\"A\")', 'Peg A'),
        Binding('2', 'pick(\"B\")', 'Peg B'),
        Binding('3', 'pick(\"C\")', 'Peg C'),
        Binding('s', 'solve', 'Auto-solve'),
        Binding('n', 'new_game', 'New'),
        Binding('plus', 'more_disks', '+ disks', show=False),
        Binding('equals_sign', 'more_disks', '+ disks', show=False),
        Binding('minus', 'fewer_disks', '- disks', show=False),
        Binding('i', 'toggle_iter', 'Toggle solver'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Tower of Hanoi'

    def __init__(self) -> None:
        super().__init__()
        self.n_disks = 4
        self.game = Hanoi(self.n_disks)
        self.selected_peg: str | None = None
        self.use_iterative = False
        self.solving = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('TOWER OF HANOI', id='title')
        yield Static(
            'Press 1/2/3 to pick source, then dest. '
            's: solve · n: new · +/-: disks · i: toggle solver',
            id='subtitle')
        with Horizontal(id='board-row'):
            for peg in PEGS:
                with Vertical(classes='peg-col', id=f'col-{peg}'):
                    yield Static('', classes='peg-art', id=f'art-{peg}')
                    yield Static(f'[ {peg} ]', classes='peg-label')
        yield Static('', id='info')
        yield Static('', id='explain')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self._set_status(self._initial_status(), 'info')

    # --- Rendering --------------------------------------------------------

    def _peg_lines(self, peg: str) -> str:
        """Render one peg as a stacked Rich-markup string."""
        n = self.n_disks
        stack = self.game.pegs[peg]
        max_w = 2 * n + 1  # widest disk width in chars
        lines: list[str] = []
        for level in range(n - 1, -1, -1):
            if level < len(stack):
                disk = stack[level]
                bar_w = 2 * disk - 1
                bar = '█' * bar_w
                pad = (max_w - bar_w) // 2
                color = DISK_COLORS[(disk - 1) % len(DISK_COLORS)]
                line = (' ' * pad) + f'[{color}]{bar}[/]' + (' ' * pad)
            else:
                pad = (max_w - 1) // 2
                line = (' ' * pad) + '[#475569]│[/]' + (' ' * pad)
            lines.append(line)
        # Base under the peg.
        lines.append('[#334155]' + ('─' * max_w) + '[/]')
        return '\n'.join(lines)

    def _refresh(self) -> None:
        for peg in PEGS:
            self.query_one(f'#art-{peg}', Static).update(self._peg_lines(peg))
            col = self.query_one(f'#col-{peg}')
            if peg == self.selected_peg:
                col.add_class('selected')
            else:
                col.remove_class('selected')
        method = 'iterative (parity bit)' if self.use_iterative \
            else 'recursive'
        self.query_one('#info', Static).update(
            f'Disks: [b]{self.n_disks}[/b]   '
            f'Optimal: [b]{(1 << self.n_disks) - 1}[/b]   '
            f'Moves: [b]{self.game.move_count}[/b]   '
            f'Solver: [b]{method}[/b]'
        )
        self.query_one('#explain', Static).update(self._explain_text())

    def _explain_text(self) -> str:
        if self.use_iterative:
            return (
                '[b]Iterative parity-bit solver[/b]\n'
                'Number moves 1..2^n−1. Step k moves the disk indexed by '
                'the lowest set bit of k. Disk 1 cycles in a fixed '
                'direction (n even: A→B→C→A; n odd: A→C→B→A); every other '
                'step is forced — only one legal non-#1 move exists.'
            )
        return (
            '[b]Recursive solver[/b]\n'
            'solve(n, src, aux, dst):\n'
            '  1. solve(n−1, src, dst, aux)  — park n−1 on aux\n'
            '  2. move src → dst             — biggest disk home\n'
            '  3. solve(n−1, aux, src, dst)  — replay onto dst\n'
            'T(n) = 2·T(n−1) + 1  ⇒  T(n) = 2^n − 1 (proven optimum).'
        )

    # --- Status ----------------------------------------------------------

    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    def _initial_status(self) -> str:
        return (f'Ready — {self.n_disks} disks on A. '
                f'Press 1/2/3 to pick a source peg.')

    # --- Actions ---------------------------------------------------------

    def action_pick(self, peg: str) -> None:
        if self.solving:
            return
        if peg not in self.game.pegs:
            return
        if self.selected_peg is None:
            if not self.game.pegs[peg]:
                self._set_status(f'Peg {peg} is empty.', 'error')
                return
            self.selected_peg = peg
            self._refresh()
            self._set_status(
                f'Source: {peg} (top disk {self.game.top(peg)}). '
                f'Pick destination (1/2/3).', 'info')
            return
        src, dst = self.selected_peg, peg
        self.selected_peg = None
        if src == dst:
            self._refresh()
            self._set_status('Move cancelled.', 'info')
            return
        ok = self.game.move(src, dst)
        self._refresh()
        if not ok:
            self._set_status(
                f'Illegal move {src}→{dst}: cannot stack larger on smaller.',
                'error')
            return
        if self.game.is_solved('C'):
            self._set_status(
                f'Solved in {self.game.move_count} moves '
                f'(optimal = {(1 << self.n_disks) - 1}).', 'win')
        else:
            self._set_status(
                f'Move #{self.game.move_count}: {src}→{dst}. Goal: stack '
                'all on C.', 'info')

    def action_solve(self) -> None:
        if self.solving:
            return
        # Reset for an honest optimal-count animation.
        self.game.reset()
        self.selected_peg = None
        self._refresh()
        if self.use_iterative:
            moves = solve_iterative(self.n_disks, 'A', 'B', 'C')
        else:
            moves = solve_recursive(self.n_disks, 'A', 'B', 'C')
        delay = max(0.05, min(0.4, 1.2 / max(1, len(moves))))
        self.solving = True
        self._run_step(moves, 0, delay)

    def _run_step(self, moves: list[tuple[str, str]],
                  idx: int, delay: float) -> None:
        if not self.solving or idx >= len(moves):
            self.solving = False
            self._refresh()
            if self.game.is_solved('C'):
                self._set_status(
                    f'Auto-solved in {self.game.move_count} moves '
                    f'(optimal = {(1 << self.n_disks) - 1}).', 'win')
            return
        s, d = moves[idx]
        self.game.move(s, d)
        self._refresh()
        self._set_status(
            f'Auto-solving — step {idx + 1}/{len(moves)}: {s}→{d}', 'busy')
        self.set_timer(delay,
                       lambda: self._run_step(moves, idx + 1, delay))

    def action_new_game(self) -> None:
        self.solving = False
        self.game = Hanoi(self.n_disks)
        self.selected_peg = None
        self._refresh()
        self._set_status(self._initial_status(), 'info')

    def action_more_disks(self) -> None:
        if self.solving or self.n_disks >= 10:
            return
        self.n_disks += 1
        self.game = Hanoi(self.n_disks)
        self.selected_peg = None
        self._refresh()
        self._set_status(
            f'Disks set to {self.n_disks}.', 'info')

    def action_fewer_disks(self) -> None:
        if self.solving or self.n_disks <= 3:
            return
        self.n_disks -= 1
        self.game = Hanoi(self.n_disks)
        self.selected_peg = None
        self._refresh()
        self._set_status(
            f'Disks set to {self.n_disks}.', 'info')

    def action_toggle_iter(self) -> None:
        if self.solving:
            return
        self.use_iterative = not self.use_iterative
        self._refresh()
        method = 'iterative parity' if self.use_iterative else 'recursive'
        self._set_status(f'Solver: {method}.', 'info')


if __name__ == '__main__':
    HanoiApp().run()
