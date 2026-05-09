"""Factor Finder — CLI.

Find all divisors and the prime factorization of an integer N.

Pure functions exported for the GUI/TUI to import:
    factors(n)              -> sorted list of all positive divisors
    prime_factorization(n)  -> dict mapping prime -> exponent
    is_prime(n)             -> Miller-Rabin probabilistic primality test
    divisor_sum(n)          -> sigma_1(n) = sum of all divisors
    proper_divisor_sum(n)   -> sigma_1(n) - n  (sum of proper divisors)
    classify(n)             -> 'prime' | 'perfect' | 'abundant' | 'deficient'
    euler_totient(n)        -> phi(n) computed from prime factorization

Run:
    uv run python factor_finder/factor_finder.py
"""
from __future__ import annotations

import math
import random
import sys
from typing import Dict, List

# ---------------------------------------------------------------------------
# Core factorization
# ---------------------------------------------------------------------------

# Small primes for trial division, up to 1000.  Plenty for any non-pathological N.
_SMALL_PRIMES = [
    2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67,
    71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127, 131, 137, 139, 149,
    151, 157, 163, 167, 173, 179, 181, 191, 193, 197, 199, 211, 223, 227, 229,
    233, 239, 241, 251, 257, 263, 269, 271, 277, 281, 283, 293, 307, 311, 313,
    317, 331, 337, 347, 349, 353, 359, 367, 373, 379, 383, 389, 397, 401, 409,
    419, 421, 431, 433, 439, 443, 449, 457, 461, 463, 467, 479, 487, 491, 499,
    503, 509, 521, 523, 541, 547, 557, 563, 569, 571, 577, 587, 593, 599, 601,
    607, 613, 617, 619, 631, 641, 643, 647, 653, 659, 661, 673, 677, 683, 691,
    701, 709, 719, 727, 733, 739, 743, 751, 757, 761, 769, 773, 787, 797, 809,
    811, 821, 823, 827, 829, 839, 853, 857, 859, 863, 877, 881, 883, 887, 907,
    911, 919, 929, 937, 941, 947, 953, 967, 971, 977, 983, 991, 997,
]


def factors(n: int) -> List[int]:
    """Return all positive divisors of ``n`` in ascending order.

    Uses the sqrt trick: pair each divisor ``i <= sqrt(n)`` with ``n // i``.
    Time:  O(sqrt(n))
    Space: O(d(n))   where d(n) is the number of divisors
    """
    if n <= 0:
        raise ValueError('factors() requires a positive integer')
    if n == 1:
        return [1]

    small: List[int] = []
    large: List[int] = []
    i = 1
    # While i*i <= n; using integer arithmetic avoids float rounding.
    while i * i <= n:
        if n % i == 0:
            small.append(i)
            if i != n // i:
                large.append(n // i)
        i += 1
    # `large` is collected in descending order of `i` (which means ascending
    # order of `n // i`)... wait, actually as i grows, n//i shrinks, so
    # `large` ends up in *descending* order.  Reverse it before joining.
    return small + large[::-1]


def is_prime(n: int) -> bool:
    """Miller-Rabin primality test.

    Deterministic for all 64-bit integers using a fixed witness set.
    For n above 2^64 it is probabilistic but with negligible error.
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

    # Deterministic witnesses for n < 3,317,044,064,679,887,385,961,981
    # which more than covers 64-bit integers.
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


def _pollard_rho(n: int) -> int:
    """Return a non-trivial factor of composite ``n`` (n > 1, n not prime).

    Uses Brent's variant of Pollard's rho.
    """
    if n % 2 == 0:
        return 2

    while True:
        # Random starting value and constant.
        x = random.randrange(2, n - 1)
        y = x
        c = random.randrange(1, n - 1)
        d = 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = math.gcd(abs(x - y), n)
        if d != n:
            return d
        # else: cycle, try again with new c


def prime_factorization(n: int) -> Dict[int, int]:
    """Return ``{prime: exponent}`` for ``n``.

    Strategy:
        1. Trial-divide by small primes up to 1000.
        2. If the remaining cofactor is small enough, finish by trial division
           up to sqrt; otherwise alternate Miller-Rabin tests with Pollard's
           rho splits until every factor is prime.
    """
    if n <= 0:
        raise ValueError('prime_factorization() requires a positive integer')
    if n == 1:
        return {}

    factor_counts: Dict[int, int] = {}

    # Step 1 — trial divide by the small-prime table.
    for p in _SMALL_PRIMES:
        if p * p > n:
            break
        while n % p == 0:
            factor_counts[p] = factor_counts.get(p, 0) + 1
            n //= p

    if n == 1:
        return factor_counts

    # Step 2 — if the residue is itself prime, we are done.
    if is_prime(n):
        factor_counts[n] = factor_counts.get(n, 0) + 1
        return factor_counts

    # Step 3 — split via Pollard's rho until every piece is prime.
    stack = [n]
    while stack:
        m = stack.pop()
        if m == 1:
            continue
        if is_prime(m):
            factor_counts[m] = factor_counts.get(m, 0) + 1
            continue
        d = _pollard_rho(m)
        stack.append(d)
        stack.append(m // d)

    return factor_counts


# ---------------------------------------------------------------------------
# Number-theory functions on top of factorization
# ---------------------------------------------------------------------------


def divisor_count(n: int) -> int:
    """sigma_0(n) — number of divisors. Equals prod(e_i + 1)."""
    if n <= 0:
        raise ValueError('divisor_count() requires a positive integer')
    pf = prime_factorization(n)
    total = 1
    for e in pf.values():
        total *= (e + 1)
    return total


def divisor_sum(n: int) -> int:
    """sigma_1(n) — sum of all divisors. Equals prod((p^(e+1) - 1)/(p - 1))."""
    if n <= 0:
        raise ValueError('divisor_sum() requires a positive integer')
    pf = prime_factorization(n)
    total = 1
    for p, e in pf.items():
        total *= (p ** (e + 1) - 1) // (p - 1)
    return total


def proper_divisor_sum(n: int) -> int:
    """Aliquot sum: sum of divisors strictly less than n."""
    if n <= 0:
        raise ValueError('proper_divisor_sum() requires a positive integer')
    if n == 1:
        return 0
    return divisor_sum(n) - n


def euler_totient(n: int) -> int:
    """phi(n) — count of integers in [1, n] coprime to n.

    phi(n) = n * prod(1 - 1/p) over distinct prime factors p.
    """
    if n <= 0:
        raise ValueError('euler_totient() requires a positive integer')
    if n == 1:
        return 1
    pf = prime_factorization(n)
    result = n
    for p in pf:
        result = result // p * (p - 1)
    return result


def classify(n: int) -> str:
    """Return one of 'prime', 'perfect', 'abundant', 'deficient'.

    Uses the sum of *proper* divisors:
        s(n) <  n -> deficient
        s(n) == n -> perfect
        s(n) >  n -> abundant
    With 'prime' taking precedence (a prime is automatically deficient).
    """
    if n <= 0:
        raise ValueError('classify() requires a positive integer')
    if n == 1:
        return 'deficient'  # convention: 1 has aliquot sum 0
    if is_prime(n):
        return 'prime'
    s = proper_divisor_sum(n)
    if s == n:
        return 'perfect'
    if s > n:
        return 'abundant'
    return 'deficient'


# ---------------------------------------------------------------------------
# Pretty-printing helpers
# ---------------------------------------------------------------------------

_SUPERSCRIPTS = str.maketrans('0123456789', '⁰¹²³'
                                            '⁴⁵⁶⁷'
                                            '⁸⁹')


def superscript(n: int) -> str:
    """Render an integer as Unicode superscript digits (for exponents)."""
    return str(n).translate(_SUPERSCRIPTS)


def pretty_factorization(pf: Dict[int, int]) -> str:
    """Render ``{2: 3, 3: 2}`` as ``2³ × 3²``."""
    if not pf:
        return '1'
    parts = []
    for p in sorted(pf):
        e = pf[p]
        parts.append(f'{p}{superscript(e)}' if e > 1 else str(p))
    return ' × '.join(parts)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_factor_list(divs: List[int], width: int = 72) -> str:
    """Format the divisor list with line wrapping."""
    pieces = [str(d) for d in divs]
    lines: List[str] = []
    line = ''
    for piece in pieces:
        sep = ', ' if line else ''
        if line and len(line) + len(sep) + len(piece) > width:
            lines.append(line + ',')
            line = piece
        else:
            line = line + sep + piece
    if line:
        lines.append(line)
    return '\n'.join(lines)


def _read_n(argv: List[str]) -> int:
    """Read N from argv or prompt the user."""
    if len(argv) > 1:
        return int(argv[1])
    while True:
        raw = input('Enter a positive integer N: ').strip()
        try:
            n = int(raw)
            if n <= 0:
                print('  N must be positive.')
                continue
            return n
        except ValueError:
            print('  Not a valid integer.  Try again.')


def main() -> None:
    print('Factor Finder')
    print('=============')
    try:
        n = _read_n(sys.argv)
    except (KeyboardInterrupt, EOFError):
        print()
        return
    if n <= 0:
        print('N must be a positive integer.')
        sys.exit(1)

    divs = factors(n)
    pf = prime_factorization(n)
    sigma0 = len(divs)
    sigma1 = divisor_sum(n)
    phi = euler_totient(n)
    s = proper_divisor_sum(n)
    label = classify(n)

    print()
    print(f'N = {n}')
    print(f'Class: {label.upper()}')
    print()
    print(f'Divisors ({sigma0}):')
    print(_format_factor_list(divs))
    print()
    print(f'Prime factorization: {pretty_factorization(pf)}')
    print()
    print('Number-theory values:')
    print(f'  sigma_0(N)  = {sigma0}        # divisor count')
    print(f'  sigma_1(N)  = {sigma1}        # divisor sum')
    print(f'  s(N)        = {s}        # aliquot (proper-divisor) sum')
    print(f'  phi(N)      = {phi}        # Euler totient')


if __name__ == '__main__':
    main()
