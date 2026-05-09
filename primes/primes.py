"""Prime Numbers — CLI.

Generate primes, test primality, and explore prime structure.

Pure functions exported for the GUI/TUI to import:
    sieve(n)                -> list[int] of primes <= n (Sieve of Eratosthenes)
    sieve_segmented(lo, hi) -> list[int] of primes in [lo, hi]
    is_prime(n)             -> deterministic Miller-Rabin
    next_prime(n)           -> smallest prime strictly greater than n
    prev_prime(n)           -> largest prime strictly less than n (None if none)
    nth_prime(k)            -> the k-th prime (1-indexed: nth_prime(1) == 2)
    prime_pi(n)             -> pi(n), the prime-counting function
    prime_gaps(primes)      -> consecutive gaps p_{i+1} - p_i
    twin_primes(primes)     -> pairs (p, p+2) with both prime
    goldbach_pair(n)        -> (p, q) with p+q == n  (n even >= 4)

Run:
    uv run python primes/primes.py --up-to 100
    uv run python primes/primes.py --test 2147483647
    uv run python primes/primes.py --nth 10001
"""
from __future__ import annotations

import argparse
import math
import sys
from typing import Iterable, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Sieves
# ---------------------------------------------------------------------------


def sieve(n: int) -> List[int]:
    """Return all primes p with 2 <= p <= n via the Sieve of Eratosthenes.

    Time:  O(n log log n)
    Space: O(n)
    """
    if n < 2:
        return []
    # Bytearray is faster than list[bool] and roughly 8x more memory efficient.
    is_p = bytearray(b'\x01') * (n + 1)
    is_p[0] = 0
    is_p[1] = 0
    # Only mark from i*i upward — smaller multiples already cleared by smaller p.
    for i in range(2, math.isqrt(n) + 1):
        if is_p[i]:
            step = i
            start = i * i
            is_p[start:n + 1:step] = bytearray(len(is_p[start:n + 1:step]))
    return [i for i in range(2, n + 1) if is_p[i]]


def sieve_segmented(low: int, high: int) -> List[int]:
    """Return primes p with low <= p <= high using a segmented sieve.

    Suitable for huge ranges where a full [0, high] sieve would not fit in
    memory. Strategy:

        1. Build a base sieve of primes up to sqrt(high).
        2. Mark a window [low, high] using only those base primes.

    Time:  O((high - low + sqrt(high)) log log high)
    Space: O(sqrt(high) + (high - low))
    """
    if high < 2 or high < low:
        return []
    low = max(low, 2)
    base = sieve(math.isqrt(high))

    size = high - low + 1
    is_p = bytearray(b'\x01') * size
    for p in base:
        # Smallest multiple of p that is >= low and >= p*p
        start = max(p * p, ((low + p - 1) // p) * p)
        for j in range(start, high + 1, p):
            is_p[j - low] = 0
    # Edge: when low == 0 or 1 they are not primes; range starts at low >= 2.
    return [low + i for i, v in enumerate(is_p) if v]


# ---------------------------------------------------------------------------
# Primality test (Miller-Rabin)
# ---------------------------------------------------------------------------


# Trial-division primes — a quick rejection filter before Miller-Rabin.
_SMALL_PRIMES = (
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67,
    71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149,
    151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229,
    233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313,
    317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409,
)


def is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin primality test.

    Witness set ``(2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)`` is
    deterministic for every n < 3.317 * 10^24, which more than covers
    every 64-bit (and 80-bit) integer. For n above that bound the test
    is probabilistic with negligible error.
    """
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n == p:
            return True
        if n % p == 0:
            return False

    # Write n-1 = d * 2^r with d odd
    d = n - 1
    r = 0
    while d % 2 == 0:
        d //= 2
        r += 1

    witnesses = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for a in witnesses:
        if a >= n:
            continue
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


# ---------------------------------------------------------------------------
# Prime navigation
# ---------------------------------------------------------------------------


def next_prime(n: int) -> int:
    """Smallest prime strictly greater than n.

    Steps along the 6k +/- 1 wheel: after 2 and 3, every prime is one of
    those two residues mod 6, so we scan only ~1/3 of integers.
    """
    if n < 2:
        return 2
    candidate = n + 1
    if candidate <= 2:
        return 2
    if candidate <= 3:
        return 3
    # Round up to the next 6k+/-1 candidate.
    if candidate % 2 == 0:
        candidate += 1
    while True:
        if is_prime(candidate):
            return candidate
        candidate += 2


def prev_prime(n: int) -> Optional[int]:
    """Largest prime strictly less than n, or None if no such prime exists."""
    if n <= 2:
        return None
    if n == 3:
        return 2
    candidate = n - 1
    if candidate % 2 == 0:
        candidate -= 1
    while candidate >= 2:
        if is_prime(candidate):
            return candidate
        candidate -= 2
    return None


def nth_prime(k: int) -> int:
    """Return the k-th prime (1-indexed). nth_prime(1) == 2.

    Uses a sieve sized by the Rosser bound `p_k <= k(ln k + ln ln k)` for
    k >= 6, with safety padding. Falls back to the small-k case directly.
    """
    if k < 1:
        raise ValueError('nth_prime() requires k >= 1')
    if k < 6:
        return [2, 3, 5, 7, 11][k - 1]

    # Rosser-Schoenfeld upper bound for the k-th prime, padded by 5%.
    ln_k = math.log(k)
    upper = int(k * (ln_k + math.log(ln_k))) + 10
    upper = int(upper * 1.05) + 10

    primes = sieve(upper)
    while len(primes) < k:
        # Extremely unlikely with the padding, but be safe.
        upper *= 2
        primes = sieve(upper)
    return primes[k - 1]


# ---------------------------------------------------------------------------
# Stats / decorations
# ---------------------------------------------------------------------------


def prime_pi(n: int) -> int:
    """pi(n) -- number of primes <= n. Computed via the sieve."""
    if n < 2:
        return 0
    return len(sieve(n))


def prime_gaps(primes: Iterable[int]) -> List[int]:
    """Consecutive gaps p_{i+1} - p_i for a sorted iterable of primes."""
    primes_list = list(primes)
    return [primes_list[i + 1] - primes_list[i]
            for i in range(len(primes_list) - 1)]


def twin_primes(primes: Iterable[int]) -> List[Tuple[int, int]]:
    """Twin-prime pairs (p, p+2) within the given sorted prime list."""
    primes_list = list(primes)
    primes_set = set(primes_list)
    return [(p, p + 2) for p in primes_list if (p + 2) in primes_set]


def goldbach_pair(n: int) -> Optional[Tuple[int, int]]:
    """Return (p, q) primes with p + q == n, or None if n is not even >= 4.

    The Goldbach conjecture says such a pair always exists for even n >= 4
    (verified up to ~4 * 10^18). We search greedily from p = 2 upward.
    """
    if n < 4 or n % 2 != 0:
        return None
    p = 2
    while p <= n // 2:
        if is_prime(p) and is_prime(n - p):
            return (p, n - p)
        p = next_prime(p)
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_columns(values: List[int], width: int = 72) -> str:
    """Format integers in a column-wrapped grid for terminal output."""
    if not values:
        return '(none)'
    cell_w = max(len(str(v)) for v in values) + 2
    cols = max(1, width // cell_w)
    lines: List[str] = []
    for i in range(0, len(values), cols):
        row = values[i:i + cols]
        lines.append(''.join(str(v).rjust(cell_w) for v in row))
    return '\n'.join(lines)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='primes',
        description='Prime Numbers — sieve, test, locate, summarize.',
    )
    g = p.add_mutually_exclusive_group()
    g.add_argument('--up-to', type=int, metavar='N',
                   help='List every prime p with 2 <= p <= N.')
    g.add_argument('--test', type=int, metavar='N',
                   help='Run a Miller-Rabin primality test on N.')
    g.add_argument('--nth', type=int, metavar='K',
                   help='Print the K-th prime (1-indexed; nth=1 -> 2).')
    g.add_argument('--segment', nargs=2, type=int,
                   metavar=('LOW', 'HIGH'),
                   help='List primes in [LOW, HIGH] via a segmented sieve.')
    g.add_argument('--goldbach', type=int, metavar='N',
                   help='Find a Goldbach pair (p, q) with p + q == N.')
    return p


def _summarize_sieve(primes: List[int]) -> str:
    if not primes:
        return 'No primes in range.'
    gaps = prime_gaps(primes)
    twins = twin_primes(primes)
    parts = [
        f'pi = {len(primes)}',
        f'first = {primes[0]}',
        f'last  = {primes[-1]}',
    ]
    if gaps:
        parts.append(f'avg gap = {sum(gaps) / len(gaps):.2f}')
        parts.append(f'max gap = {max(gaps)}')
    parts.append(f'twin pairs = {len(twins)}')
    return '   '.join(parts)


def main(argv: Optional[List[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    print('Prime Numbers')
    print('=============')

    if args.test is not None:
        n = args.test
        verdict = 'PRIME' if is_prime(n) else 'COMPOSITE'
        print(f'is_prime({n}) -> {verdict}')
        return

    if args.nth is not None:
        k = args.nth
        if k < 1:
            print('K must be >= 1.', file=sys.stderr)
            sys.exit(1)
        p = nth_prime(k)
        print(f'p_{k} = {p}')
        return

    if args.segment is not None:
        lo, hi = args.segment
        if lo > hi:
            print('LOW must be <= HIGH.', file=sys.stderr)
            sys.exit(1)
        primes = sieve_segmented(lo, hi)
        print(f'Primes in [{lo}, {hi}]:')
        print(_format_columns(primes))
        print()
        print(_summarize_sieve(primes))
        return

    if args.goldbach is not None:
        n = args.goldbach
        pair = goldbach_pair(n)
        if pair is None:
            print(f'No Goldbach pair for {n} '
                  '(must be an even integer >= 4).')
        else:
            p, q = pair
            print(f'{n} = {p} + {q}    (both prime)')
        return

    # Default action: --up-to (with a sensible default if omitted).
    n = args.up_to if args.up_to is not None else 100
    primes = sieve(n)
    print(f'Primes up to {n}:')
    print(_format_columns(primes))
    print()
    print(_summarize_sieve(primes))


if __name__ == '__main__':
    main()
