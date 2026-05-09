"""Fibonacci — five algorithms in one CLI.

Implements iterative, naive recursive, memoized, matrix exponentiation, and
Binet (closed-form) approaches. Provides a sequence helper and a benchmark
mode that times each algorithm side-by-side.

Run:
    uv run python fibonacci/fibonacci.py            # interactive prompt
    uv run python fibonacci/fibonacci.py 30         # compute fib(30) all algos
    uv run python fibonacci/fibonacci.py 30 --bench # benchmark
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from functools import lru_cache

ALGORITHMS = ('iter', 'recursive', 'memo', 'matrix', 'binet')

# Recursion blows up exponentially — guard the naive variant.
RECURSIVE_MAX = 35


def fib_iter(n: int) -> int:
    """Iterative Fibonacci. O(n) time, O(1) space, exact for arbitrary n."""
    if n < 0:
        raise ValueError('n must be non-negative')
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def fib_recursive(n: int) -> int:
    """Naive recursion — O(2^n) time. For teaching only; do NOT call for n>35.

    Each call branches into two more calls, building a binary tree of depth n
    with ~2^n leaves. fib_recursive(40) already takes seconds.
    """
    if n < 0:
        raise ValueError('n must be non-negative')
    if n < 2:
        return n
    return fib_recursive(n - 1) + fib_recursive(n - 2)


@lru_cache(maxsize=None)
def fib_memo(n: int) -> int:
    """Top-down memoized Fibonacci. O(n) time + O(n) space.

    Same shape as the naive recursion, but each unique sub-problem is solved
    once and cached. Demonstrates how memoization collapses an exponential
    tree into a linear chain.
    """
    if n < 0:
        raise ValueError('n must be non-negative')
    if n < 2:
        return n
    return fib_memo(n - 1) + fib_memo(n - 2)


def _mat_mul(a: tuple[int, int, int, int],
             b: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Multiply two 2x2 matrices stored as flat (a, b, c, d) tuples."""
    a11, a12, a21, a22 = a
    b11, b12, b21, b22 = b
    return (
        a11 * b11 + a12 * b21,
        a11 * b12 + a12 * b22,
        a21 * b11 + a22 * b21,
        a21 * b12 + a22 * b22,
    )


def _mat_pow(m: tuple[int, int, int, int], p: int) -> tuple[int, int, int, int]:
    """Fast matrix exponentiation by squaring — O(log p) multiplications."""
    # Identity matrix.
    result = (1, 0, 0, 1)
    base = m
    while p > 0:
        if p & 1:
            result = _mat_mul(result, base)
        base = _mat_mul(base, base)
        p >>= 1
    return result


def fib_matrix(n: int) -> int:
    """Matrix-exponentiation Fibonacci. O(log n) multiplications.

    Uses the identity:
        [[1, 1], [1, 0]]^n = [[F(n+1), F(n)], [F(n), F(n-1)]]
    Exact for arbitrary n thanks to Python's bignum integers.
    """
    if n < 0:
        raise ValueError('n must be non-negative')
    if n == 0:
        return 0
    # Q = [[1, 1], [1, 0]]; Q^n[0][1] = F(n).
    _, b, _, _ = _mat_pow((1, 1, 1, 0), n)
    return b


# Pre-compute these once — they're constants.
_PHI = (1.0 + math.sqrt(5.0)) / 2.0
_SQRT5 = math.sqrt(5.0)


def fib_binet(n: int) -> int:
    """Closed-form Fibonacci via Binet's formula. O(1) time.

    F(n) = (phi^n - psi^n) / sqrt(5),  where phi = (1+sqrt(5))/2.

    CAVEAT: uses 64-bit floats. Accurate up to roughly n=70; beyond that the
    float mantissa cannot represent F(n) exactly and rounding errors creep in.
    The simplified `round(phi**n / sqrt(5))` form works because |psi^n| < 0.5
    for all n >= 0.
    """
    if n < 0:
        raise ValueError('n must be non-negative')
    return int(round(_PHI ** n / _SQRT5))


def sequence_up_to(n: int) -> list[int]:
    """Return [F(0), F(1), ..., F(n)] using the iterative algorithm."""
    if n < 0:
        raise ValueError('n must be non-negative')
    out = [0] * (n + 1)
    a, b = 0, 1
    for i in range(n + 1):
        out[i] = a
        a, b = b, a + b
    return out


def compute(n: int, algorithm: str) -> int:
    """Dispatch by algorithm name."""
    algorithm = algorithm.lower()
    if algorithm == 'iter':
        return fib_iter(n)
    if algorithm == 'recursive':
        if n > RECURSIVE_MAX:
            raise ValueError(
                f'naive recursion is O(2^n); refusing n>{RECURSIVE_MAX}')
        return fib_recursive(n)
    if algorithm == 'memo':
        return fib_memo(n)
    if algorithm == 'matrix':
        return fib_matrix(n)
    if algorithm == 'binet':
        return fib_binet(n)
    raise ValueError(f'unknown algorithm {algorithm!r}; '
                     f'choose from {ALGORITHMS}')


def benchmark(n: int) -> dict[str, tuple[int, float]]:
    """Time every algorithm. Returns {algo: (result, seconds)}."""
    results: dict[str, tuple[int, float]] = {}
    for algo in ALGORITHMS:
        if algo == 'recursive' and n > RECURSIVE_MAX:
            continue
        if algo == 'memo':
            # Reset cache so timing isn't polluted by a previous call.
            fib_memo.cache_clear()
        start = time.perf_counter()
        value = compute(n, algo)
        elapsed = time.perf_counter() - start
        results[algo] = (value, elapsed)
    return results


def _print_one(n: int, algo: str) -> None:
    value = compute(n, algo)
    print(f'fib({n}) via {algo} = {value}')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Fibonacci — five algorithms.',
        epilog='With no N, prompts interactively.')
    parser.add_argument('n', nargs='?', type=int,
                        help='index N (non-negative integer)')
    parser.add_argument('-a', '--algorithm', choices=ALGORITHMS, default='iter',
                        help='algorithm to use (default: iter)')
    parser.add_argument('-s', '--sequence', action='store_true',
                        help='print F(0)..F(N)')
    parser.add_argument('-b', '--bench', action='store_true',
                        help='time every algorithm side-by-side')
    args = parser.parse_args(argv)

    if args.n is None:
        try:
            raw = input('Enter N (non-negative integer): ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        try:
            args.n = int(raw)
        except ValueError:
            print(f'not a valid integer: {raw!r}', file=sys.stderr)
            sys.exit(1)

    if args.n < 0:
        print('N must be non-negative', file=sys.stderr)
        sys.exit(1)

    if args.sequence:
        seq = sequence_up_to(args.n)
        print(', '.join(str(x) for x in seq))
        return

    if args.bench:
        results = benchmark(args.n)
        # Truncate result for readability when N is huge.
        print(f'{"algorithm":<12}{"time (s)":>14}   value')
        print('-' * 60)
        for algo in ALGORITHMS:
            if algo not in results:
                print(f'{algo:<12}{"skipped":>14}   '
                      f'(n>{RECURSIVE_MAX} would explode)')
                continue
            value, secs = results[algo]
            shown = str(value)
            if len(shown) > 24:
                shown = shown[:12] + '...' + shown[-8:]
            print(f'{algo:<12}{secs:>14.6f}   {shown}')
        return

    _print_one(args.n, args.algorithm)


if __name__ == '__main__':
    main()
