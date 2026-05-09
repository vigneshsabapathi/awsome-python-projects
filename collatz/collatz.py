"""Collatz Sequence (Hailstone Sequence).

Given a positive integer n, repeatedly apply:
    n -> n // 2     if n is even
    n -> 3*n + 1    if n is odd
until n reaches 1. The Collatz conjecture (Lothar Collatz, 1937) states
that every positive integer eventually reaches 1, but this is an unsolved
problem in mathematics — verified up to 2^68 by computer search but with
no proof in sight.

This module provides:
- collatz_sequence(n)  — full hailstone path as a list[int]
- stopping_time(n)     — number of steps to reach 1, memoized for batch use
- max_value(n)         — the peak value reached on the path

Run:
    uv run python collatz/collatz.py
"""
from __future__ import annotations

import functools
import sys


def collatz_step(n: int) -> int:
    """One step of the Collatz map. Raises for n <= 0."""
    if n <= 0:
        raise ValueError(f'Collatz is only defined for positive integers, got {n}')
    if n % 2 == 0:
        return n // 2
    return 3 * n + 1


def collatz_sequence(n: int) -> list[int]:
    """Return the full hailstone sequence starting at n and ending at 1.

    The first element is n itself; the last is 1. For n=1 the result is [1].
    Raises ValueError for n <= 0.
    """
    if n <= 0:
        raise ValueError(f'Collatz is only defined for positive integers, got {n}')
    seq = [n]
    while n != 1:
        n = collatz_step(n)
        seq.append(n)
    return seq


@functools.lru_cache(maxsize=None)
def stopping_time(n: int) -> int:
    """Number of Collatz steps required for n to reach 1.

    Memoized via lru_cache so batch calls (e.g. plotting stopping-time vs n
    for n=1..N) run in roughly O(total path length) instead of O(sum of path
    lengths). For n=1 the stopping time is 0.

    Implementation note: we recurse via the cached function so every
    intermediate value seen on any path is memoized too. Recursion depth is
    bounded by the longest known path; for n < 10^7 this is well under 1000,
    but we still raise the recursion limit defensively.
    """
    if n <= 0:
        raise ValueError(f'stopping_time requires n > 0, got {n}')
    if n == 1:
        return 0
    if n % 2 == 0:
        return 1 + stopping_time(n // 2)
    return 1 + stopping_time(3 * n + 1)


def stopping_time_iterative(n: int) -> int:
    """Iterative stopping-time, no recursion. Useful sanity check."""
    if n <= 0:
        raise ValueError(f'stopping_time requires n > 0, got {n}')
    steps = 0
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        steps += 1
    return steps


def max_value(n: int) -> int:
    """The peak (maximum) value reached on the Collatz path from n.

    For n=1 the peak is 1. For n=27 the path climbs to 9232 — a famously
    high peak relative to the starting value.
    """
    if n <= 0:
        raise ValueError(f'max_value requires n > 0, got {n}')
    peak = n
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        if n > peak:
            peak = n
    return peak


def stopping_times_up_to(limit: int) -> list[int]:
    """Compute stopping times for n=1..limit. Uses the memoized cache."""
    if limit < 1:
        return []
    return [stopping_time(n) for n in range(1, limit + 1)]


def main() -> None:
    """Tiny interactive CLI: prompt for n, print sequence, peak, stopping time."""
    print('Collatz Sequence (Hailstone numbers)')
    print('  even  -> n / 2')
    print('  odd   -> 3n + 1')
    print('  stop  -> n = 1')
    print()
    print('Lothar Collatz, 1937.  Conjecture: every positive integer reaches 1.')
    print('(Verified up to ~2^68. Still unproven.)')
    print()

    raw = input('Enter a positive integer n (default 27): ').strip()
    if not raw:
        n = 27
    else:
        try:
            n = int(raw)
        except ValueError:
            print(f'Not an integer: {raw!r}')
            sys.exit(1)
        if n <= 0:
            print(f'n must be positive, got {n}')
            sys.exit(1)

    # Bump recursion limit for the memoized recursive call on large peaks.
    sys.setrecursionlimit(max(2000, sys.getrecursionlimit()))

    seq = collatz_sequence(n)
    peak = max(seq)
    steps = len(seq) - 1

    print()
    print(f'Sequence for n = {n}:')
    print('  ' + ' -> '.join(str(x) for x in seq))
    print()
    print(f'Steps to reach 1 (stopping time): {steps}')
    print(f'Peak value on the path:           {peak}')
    if peak > n:
        print(f'  ratio peak / n = {peak / n:.2f}x')


if __name__ == '__main__':
    main()
