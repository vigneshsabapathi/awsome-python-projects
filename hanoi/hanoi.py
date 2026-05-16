"""Tower of Hanoi — CLI and shared game logic.

Move N disks from peg A to peg C using peg B as scratch space, one disk
at a time, never placing a larger disk on a smaller one.

Optimal solution = 2^N - 1 moves (proven minimum).

Run:
    uv run python hanoi/hanoi.py            # animated 4-disk solve
    uv run python hanoi/hanoi.py 6          # animated 6-disk solve
    uv run python hanoi/hanoi.py 5 iter     # use iterative parity solver
"""
from __future__ import annotations

import sys
import time
from typing import Iterable

PEGS = ('A', 'B', 'C')
DEFAULT_DISKS = 4


class Hanoi:
    """3-peg Tower of Hanoi state machine.

    Pegs are keyed by 'A', 'B', 'C'. Each peg is a list whose tail is the top
    of the stack — disks are integers 1..n_disks where 1 is the smallest disk.
    Initial state stacks all disks on peg 'A' (largest at the bottom).
    """

    def __init__(self, n_disks: int = DEFAULT_DISKS) -> None:
        if n_disks < 1:
            raise ValueError('n_disks must be >= 1')
        self.n_disks = n_disks
        self.reset()

    def reset(self) -> None:
        self.pegs: dict[str, list[int]] = {
            'A': list(range(self.n_disks, 0, -1)),  # largest to smallest
            'B': [],
            'C': [],
        }
        self.move_count = 0

    def state(self) -> dict[str, list[int]]:
        """Return a snapshot copy of the current peg state."""
        return {peg: list(stack) for peg, stack in self.pegs.items()}

    def top(self, peg: str) -> int | None:
        """Top disk on a peg, or None if empty."""
        stack = self.pegs[peg]
        return stack[-1] if stack else None

    def move(self, src: str, dst: str) -> bool:
        """Attempt to move the top disk from src to dst.

        Returns True if the move was legal and applied, False otherwise.
        Illegal: same peg, empty source, or larger-on-smaller violation.
        """
        if src == dst or src not in self.pegs or dst not in self.pegs:
            return False
        if not self.pegs[src]:
            return False
        moving = self.pegs[src][-1]
        if self.pegs[dst] and self.pegs[dst][-1] < moving:
            return False
        self.pegs[dst].append(self.pegs[src].pop())
        self.move_count += 1
        return True

    def is_solved(self, target: str = 'C') -> bool:
        """True iff all disks are stacked correctly on the target peg."""
        return len(self.pegs[target]) == self.n_disks


# --- Solvers ---------------------------------------------------------------

def solve_recursive(n: int, src: str, aux: str,
                    dst: str) -> list[tuple[str, str]]:
    """Classic recursive solver. Returns the optimal move sequence.

    Length is exactly 2^n - 1.

        T(n) = 2*T(n-1) + 1, T(0) = 0  =>  T(n) = 2^n - 1
    """
    if n <= 0:
        return []
    moves: list[tuple[str, str]] = []
    moves.extend(solve_recursive(n - 1, src, dst, aux))
    moves.append((src, dst))
    moves.extend(solve_recursive(n - 1, aux, src, dst))
    return moves


def solve_iterative(n: int, src: str = 'A', aux: str = 'B',
                    dst: str = 'C') -> list[tuple[str, str]]:
    """Iterative parity-bit solver — also optimal (2^n - 1 moves).

    Trick: number the moves 1..2^n-1. On step k, move disk
    `(k & -k).bit_length()` (the lowest set bit of k = the smallest disk
    that must move on this step). The smallest disk (#1) cycles in a
    fixed direction depending on parity of n:

      - n even: disk 1 cycles A -> B -> C -> A
      - n odd:  disk 1 cycles A -> C -> B -> A

    Every other step is forced — only one legal non-#1 move exists.
    """
    if n <= 0:
        return []
    pegs = {src: list(range(n, 0, -1)), aux: [], dst: []}
    if n % 2 == 0:
        cycle = (src, aux, dst)  # disk 1 traverses src -> aux -> dst
    else:
        cycle = (src, dst, aux)  # disk 1 traverses src -> dst -> aux
    pos1 = 0  # current index of disk 1 in the cycle
    moves: list[tuple[str, str]] = []
    total = (1 << n) - 1
    for step in range(1, total + 1):
        # Bit-trick: smallest set bit of step = which disk to move.
        if step & 1:
            # Step is odd: move disk 1 to next cycle position.
            from_peg = cycle[pos1]
            pos1 = (pos1 + 1) % 3
            to_peg = cycle[pos1]
            pegs[to_peg].append(pegs[from_peg].pop())
            moves.append((from_peg, to_peg))
        else:
            # Step is even: only one legal move between the two pegs
            # that are not currently topped by disk 1.
            disk1_peg = cycle[pos1]
            other = [p for p in (src, aux, dst) if p != disk1_peg]
            a, b = other
            top_a = pegs[a][-1] if pegs[a] else None
            top_b = pegs[b][-1] if pegs[b] else None
            if top_a is None:
                from_peg, to_peg = b, a
            elif top_b is None:
                from_peg, to_peg = a, b
            elif top_a < top_b:
                from_peg, to_peg = a, b
            else:
                from_peg, to_peg = b, a
            pegs[to_peg].append(pegs[from_peg].pop())
            moves.append((from_peg, to_peg))
    return moves


# --- CLI rendering ---------------------------------------------------------

def render(game: Hanoi) -> str:
    """ASCII render of the current state — pegs side by side, top-down."""
    n = game.n_disks
    width = 2 * n + 1  # widest disk + spacing
    lines: list[str] = []
    for level in range(n - 1, -1, -1):
        row_parts = []
        for peg in PEGS:
            stack = game.pegs[peg]
            if level < len(stack):
                disk = stack[level]
                bar = '=' * (2 * disk - 1)
                cell = bar.center(width)
            else:
                cell = '|'.center(width)
            row_parts.append(cell)
        lines.append('  '.join(row_parts))
    base = '-' * width
    lines.append('  '.join(base for _ in PEGS))
    labels = '  '.join(p.center(width) for p in PEGS)
    lines.append(labels)
    return '\n'.join(lines)


def animate(game: Hanoi, moves: Iterable[tuple[str, str]],
            delay: float = 0.4) -> None:
    """Apply moves one by one, printing the board after each step."""
    print(render(game))
    print()
    for i, (s, d) in enumerate(moves, start=1):
        time.sleep(delay)
        ok = game.move(s, d)
        marker = '*' if ok else '!'
        print(f'Move {i}: {s} -> {d}  {marker}')
        print(render(game))
        print()


def main() -> None:
    """CLI entry point. Animates the optimal solve."""
    n = DEFAULT_DISKS
    method = 'recursive'
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
        except ValueError:
            print(f'Invalid disk count: {sys.argv[1]!r}')
            return
    if len(sys.argv) > 2:
        method = sys.argv[2].lower()

    print(f'Tower of Hanoi — {n} disks, {method} solver')
    print(f'Optimal moves: {(1 << n) - 1}')
    print()

    game = Hanoi(n_disks=n)
    if method.startswith('iter'):
        moves = solve_iterative(n, 'A', 'B', 'C')
    else:
        moves = solve_recursive(n, 'A', 'B', 'C')

    # Frame rate scales with disk count so big runs don't crawl.
    delay = max(0.05, min(0.5, 1.5 / max(1, len(moves))))
    animate(game, moves, delay=delay)

    if game.is_solved('C'):
        print(f'Solved in {game.move_count} moves '
              f'(optimal = {(1 << n) - 1}).')
    else:
        print('Solver produced an invalid sequence (this is a bug).')


if __name__ == '__main__':
    main()
