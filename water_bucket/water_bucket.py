"""Water Bucket Puzzle — Die-Hard-style measuring puzzle.

Given two buckets of capacities A and B and a target volume C, find the
shortest sequence of {fill, empty, transfer} operations that leaves
exactly C liters in one of the buckets.

The solver runs a breadth-first search over the state graph:
    state  = (a, b)            with 0 <= a <= A, 0 <= b <= B
    moves  = 6 deterministic operations
The puzzle is solvable iff:
    target <= max(A, B)              (capacity constraint)
    gcd(A, B) divides target          (Bezout's identity)

Run:
    uv run python water_bucket/water_bucket.py
"""
from __future__ import annotations

from collections import deque
from math import gcd
from typing import Optional


# Operation labels — also used as button text in the GUI/TUI.
OPS = (
    'fill_a',
    'fill_b',
    'empty_a',
    'empty_b',
    'pour_a_to_b',
    'pour_b_to_a',
)


class Buckets:
    """Pure state container for two buckets of capacity a_cap and b_cap.

    All six operations mutate (a, b) in place and return self so they
    can be chained. None of them ever raise — illegal moves (e.g.
    pour from an empty bucket) are no-ops.
    """

    def __init__(self, a_cap: int, b_cap: int,
                 a: int = 0, b: int = 0) -> None:
        if a_cap <= 0 or b_cap <= 0:
            raise ValueError('Capacities must be positive integers.')
        self.a_cap = a_cap
        self.b_cap = b_cap
        self.a = a
        self.b = b

    @property
    def state(self) -> tuple[int, int]:
        return (self.a, self.b)

    def reset(self) -> 'Buckets':
        self.a = 0
        self.b = 0
        return self

    def fill_a(self) -> 'Buckets':
        self.a = self.a_cap
        return self

    def fill_b(self) -> 'Buckets':
        self.b = self.b_cap
        return self

    def empty_a(self) -> 'Buckets':
        self.a = 0
        return self

    def empty_b(self) -> 'Buckets':
        self.b = 0
        return self

    def pour_a_to_b(self) -> 'Buckets':
        # Transfer until either A is empty or B is full.
        room = self.b_cap - self.b
        amount = min(self.a, room)
        self.a -= amount
        self.b += amount
        return self

    def pour_b_to_a(self) -> 'Buckets':
        room = self.a_cap - self.a
        amount = min(self.b, room)
        self.b -= amount
        self.a += amount
        return self

    def apply(self, op: str) -> 'Buckets':
        """Dispatch a string op name to the matching method."""
        if op not in OPS:
            raise ValueError(f'Unknown op: {op!r}')
        return getattr(self, op)()

    def __repr__(self) -> str:
        return f'Buckets({self.a_cap},{self.b_cap}) a={self.a} b={self.b}'


def is_solvable(a_cap: int, b_cap: int, target: int) -> bool:
    """Theoretical solvability check — Bezout's identity.

    Any reachable state (a, b) satisfies gcd(A, B) | a and gcd(A, B) | b,
    so target must be a multiple of gcd(A, B). Target also can't exceed
    the larger bucket (no bucket can hold more than its capacity).
    """
    if target < 0:
        return False
    if target > max(a_cap, b_cap):
        return False
    return target % gcd(a_cap, b_cap) == 0


def _next_states(state: tuple[int, int],
                 a_cap: int, b_cap: int) -> list[tuple[str, tuple[int, int]]]:
    """Return (op_name, new_state) for all 6 ops applied to state."""
    a, b = state
    results: list[tuple[str, tuple[int, int]]] = []
    # fill_a
    results.append(('fill_a', (a_cap, b)))
    # fill_b
    results.append(('fill_b', (a, b_cap)))
    # empty_a
    results.append(('empty_a', (0, b)))
    # empty_b
    results.append(('empty_b', (a, 0)))
    # pour_a_to_b
    pour_ab = min(a, b_cap - b)
    results.append(('pour_a_to_b', (a - pour_ab, b + pour_ab)))
    # pour_b_to_a
    pour_ba = min(b, a_cap - a)
    results.append(('pour_b_to_a', (a + pour_ba, b - pour_ba)))
    return results


def solve(a_cap: int, b_cap: int, target: int) -> Optional[list[str]]:
    """BFS for the shortest sequence of ops that lands exactly target
    liters in either bucket. Returns the list of op names, or None if
    unsolvable. An empty list means the start state already matches
    (target == 0).
    """
    if not is_solvable(a_cap, b_cap, target):
        return None

    start = (0, 0)
    if target == 0:
        return []

    # BFS — each entry is a state; parents map records (prev_state, op).
    visited: set[tuple[int, int]] = {start}
    parent: dict[tuple[int, int], tuple[tuple[int, int], str]] = {}
    queue: deque[tuple[int, int]] = deque([start])

    goal: Optional[tuple[int, int]] = None
    while queue:
        cur = queue.popleft()
        if cur[0] == target or cur[1] == target:
            goal = cur
            break
        for op, nxt in _next_states(cur, a_cap, b_cap):
            if nxt in visited:
                continue
            visited.add(nxt)
            parent[nxt] = (cur, op)
            queue.append(nxt)

    if goal is None:
        # Should be unreachable thanks to is_solvable, but guard anyway.
        return None

    # Reconstruct the path from start to goal.
    path: list[str] = []
    cur = goal
    while cur in parent:
        prev, op = parent[cur]
        path.append(op)
        cur = prev
    path.reverse()
    return path


def solve_states(a_cap: int, b_cap: int, target: int
                 ) -> Optional[list[tuple[str, tuple[int, int]]]]:
    """Like solve(), but returns each step's (op, resulting_state) for
    GUI/TUI animation. The first entry is the first op applied to (0,0).
    """
    ops = solve(a_cap, b_cap, target)
    if ops is None:
        return None
    buckets = Buckets(a_cap, b_cap)
    out: list[tuple[str, tuple[int, int]]] = []
    for op in ops:
        buckets.apply(op)
        out.append((op, buckets.state))
    return out


def explain_solvability(a_cap: int, b_cap: int, target: int) -> str:
    """Human-readable explanation — the 'Why solvable?' panel.

    Covers gcd / Bezout's identity. Explains why target must be a
    multiple of gcd(A, B) and why it can't exceed the larger bucket.
    """
    g = gcd(a_cap, b_cap)
    lines = [
        f'Capacities: A = {a_cap}, B = {b_cap}',
        f'Target:     C = {target}',
        f'gcd(A, B) = gcd({a_cap}, {b_cap}) = {g}',
        '',
        'Theorem (Bezout):',
        f'  Any reachable amount in either bucket is a multiple of {g}.',
        f'  So C must satisfy  {g} | C  and  C <= max(A, B).',
        '',
    ]
    if target > max(a_cap, b_cap):
        lines.append(
            f'  C = {target} exceeds max(A, B) = {max(a_cap, b_cap)} '
            '— UNSOLVABLE.')
    elif target % g != 0:
        lines.append(
            f'  {target} is NOT a multiple of {g} — UNSOLVABLE.')
    else:
        lines.append(
            f'  {target} = {target // g} x {g}  AND  '
            f'{target} <= {max(a_cap, b_cap)} — SOLVABLE.')
        # Optional Bezout coefficients for the canonical 1-bucket-of-A,
        # 1-bucket-of-B identity (only meaningful when target == g).
        if target == g:
            x, y = _bezout(a_cap, b_cap)
            lines.append(
                f'  Bezout coefficients: {x}*A + {y}*B = {g}.')
    return '\n'.join(lines)


def _bezout(a: int, b: int) -> tuple[int, int]:
    """Extended Euclidean algorithm — returns (x, y) with x*a + y*b = gcd(a, b)."""
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_s, old_t


# Pretty op labels used by the CLI (and shareable with the UIs).
OP_LABEL = {
    'fill_a':      'Fill bucket A',
    'fill_b':      'Fill bucket B',
    'empty_a':     'Empty bucket A',
    'empty_b':     'Empty bucket B',
    'pour_a_to_b': 'Pour A -> B',
    'pour_b_to_a': 'Pour B -> A',
}


def main() -> None:
    print('Water Bucket Puzzle')
    print('===================')
    print('Two buckets, capacities A and B. Measure exactly C liters using')
    print('fill / empty / pour operations. (Famous example: A=3, B=5, C=4 —')
    print('the Die Hard 3 jug problem.)')
    print()

    while True:
        try:
            a_cap = _ask_int('Capacity of bucket A (liters): ', minimum=1)
            b_cap = _ask_int('Capacity of bucket B (liters): ', minimum=1)
            target = _ask_int('Target amount C (liters): ', minimum=0)
        except (EOFError, KeyboardInterrupt):
            print()
            return

        print()
        print(explain_solvability(a_cap, b_cap, target))
        print()

        steps = solve_states(a_cap, b_cap, target)
        if steps is None:
            print('No solution exists.')
        else:
            print(f'Shortest solution — {len(steps)} step(s):')
            print(f'  start                   ({0:>3}, {0:>3})')
            for i, (op, (a, b)) in enumerate(steps, 1):
                print(f'  {i:>2}. {OP_LABEL[op]:<20}({a:>3}, {b:>3})')

        print()
        again = input('Solve another? (y/n) ').strip().lower()
        if not again.startswith('y'):
            print('Bye.')
            return


def _ask_int(prompt: str, minimum: int = 0) -> int:
    while True:
        raw = input(prompt).strip()
        if not raw:
            continue
        try:
            value = int(raw)
        except ValueError:
            print('  Please enter a whole number.')
            continue
        if value < minimum:
            print(f'  Must be >= {minimum}.')
            continue
        return value


if __name__ == '__main__':
    main()
