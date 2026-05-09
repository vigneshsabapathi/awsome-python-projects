"""Million Dice Statistics — CLI + shared helpers.

Roll N dice millions of times, then analyze the distribution of the SUMS
(mean, std, min, max, frequency histogram). The Central Limit Theorem says
that for any finite-mean / finite-variance die, the distribution of the sum
of N independent rolls converges to a Normal as N grows:

    mean(sum) = N * (s+1)/2
    var(sum)  = N * (s^2 - 1)/12

For a fair 6-sided die: mean(roll) = 3.5, var(roll) = 35/12 ≈ 2.9167.
So 2d6 has mean 7, var ≈ 5.833, std ≈ 2.415.

Run:
    uv run python million_dice/million_dice.py --n 2 --rolls 1000000
    uv run python million_dice/million_dice.py --n 5 --rolls 100000 --sides 20

Tags: monte-carlo, numpy, clt, statistics, dice
"""
from __future__ import annotations

import argparse
import math
from typing import Optional

import numpy as np


def simulate(num_dice: int, num_rolls: int, sides: int = 6,
             rng: Optional[np.random.Generator] = None) -> dict:
    """Vectorized dice-sum simulator.

    Roll `num_dice` dice with `sides` faces, `num_rolls` times, and return
    summary statistics on the distribution of the SUMS.

    Returns a dict:
        counts: dict[int, int]   sum -> frequency
        mean:   float            sample mean of the sums
        std:    float            sample standard deviation (ddof=0)
        min:    int              smallest sum observed (== num_dice in theory)
        max:    int              largest sum observed (== num_dice * sides in theory)
        sums:   np.ndarray       raw array of all sums (shape (num_rolls,))
        theoretical_mean: float  N * (s+1)/2
        theoretical_std:  float  sqrt(N * (s^2 - 1)/12)
        num_dice, num_rolls, sides: echo of inputs
    """
    if num_dice < 1:
        raise ValueError('num_dice must be >= 1')
    if num_rolls < 1:
        raise ValueError('num_rolls must be >= 1')
    if sides < 2:
        raise ValueError('sides must be >= 2')

    if rng is None:
        rng = np.random.default_rng()

    # Vectorized: (num_rolls, num_dice) random integers in [1, sides], summed
    # along axis=1 to get an array of num_rolls totals.
    sums = rng.integers(1, sides + 1, size=(num_rolls, num_dice),
                        dtype=np.int64).sum(axis=1)

    # Frequency histogram across all possible sums [num_dice, num_dice*sides]
    lo = num_dice
    hi = num_dice * sides
    bins = np.bincount(sums - lo, minlength=hi - lo + 1)
    counts: dict[int, int] = {int(s): int(c)
                              for s, c in enumerate(bins, start=lo) if c}

    theoretical_mean = num_dice * (sides + 1) / 2.0
    theoretical_var = num_dice * (sides * sides - 1) / 12.0
    theoretical_std = math.sqrt(theoretical_var)

    return {
        'counts': counts,
        'mean': float(sums.mean()),
        'std': float(sums.std(ddof=0)),
        'min': int(sums.min()),
        'max': int(sums.max()),
        'sums': sums,
        'theoretical_mean': theoretical_mean,
        'theoretical_std': theoretical_std,
        'num_dice': num_dice,
        'num_rolls': num_rolls,
        'sides': sides,
    }


def normal_pdf(x: np.ndarray, mean: float, std: float) -> np.ndarray:
    """Standard Gaussian PDF — for overlaying the CLT approximation."""
    if std <= 0:
        return np.zeros_like(x, dtype=float)
    z = (x - mean) / std
    return np.exp(-0.5 * z * z) / (std * math.sqrt(2.0 * math.pi))


def format_summary(result: dict) -> str:
    """Pretty-print the summary stats from `simulate`."""
    n = result['num_dice']
    t = result['num_rolls']
    s = result['sides']
    return (
        f'{n}d{s} x {t:,} rolls\n'
        f'  empirical    mean={result["mean"]:.4f}   '
        f'std={result["std"]:.4f}   '
        f'min={result["min"]}   max={result["max"]}\n'
        f'  theoretical  mean={result["theoretical_mean"]:.4f}   '
        f'std={result["theoretical_std"]:.4f}   '
        f'min={n}   max={n * s}'
    )


def render_histogram(result: dict, width: int = 50, max_rows: int = 30,
                     ascii_only: bool = False) -> str:
    """Render a bar chart of the sum frequencies. Uses unicode block by
    default; pass ascii_only=True for terminals that can't handle U+2588."""
    counts = result['counts']
    if not counts:
        return '(no data)'
    keys = sorted(counts.keys())
    values = [counts[k] for k in keys]
    peak = max(values) if values else 1

    # Down-sample to at most max_rows rows by binning consecutive sums together.
    if len(keys) > max_rows:
        bin_size = math.ceil(len(keys) / max_rows)
        new_keys, new_values = [], []
        for i in range(0, len(keys), bin_size):
            chunk_keys = keys[i:i + bin_size]
            chunk_vals = values[i:i + bin_size]
            new_keys.append(f'{chunk_keys[0]}-{chunk_keys[-1]}')
            new_values.append(sum(chunk_vals))
        keys = new_keys
        values = new_values
        peak = max(values) if values else 1

    block = '#' if ascii_only else '█'
    lines = []
    label_width = max(len(str(k)) for k in keys)
    for k, v in zip(keys, values):
        bar_len = int(round(v / peak * width)) if peak else 0
        bar = block * bar_len
        pct = v / result['num_rolls'] * 100
        lines.append(f'  {str(k):>{label_width}}  {bar:<{width}}  '
                     f'{v:>10,}  {pct:6.2f}%')
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Roll N dice millions of times and analyze the sum '
                    'distribution (mean, std, histogram, CLT fit).')
    parser.add_argument('--n', type=int, default=2,
                        help='Number of dice per roll (default: 2)')
    parser.add_argument('--rolls', type=int, default=1_000_000,
                        help='Number of rolls / trials (default: 1,000,000)')
    parser.add_argument('--sides', type=int, default=6,
                        help='Number of faces per die (default: 6)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Optional RNG seed for reproducibility')
    parser.add_argument('--no-hist', action='store_true',
                        help='Skip the unicode histogram')
    args = parser.parse_args()

    rng = np.random.default_rng(args.seed)
    print(f'Rolling {args.n}d{args.sides} x {args.rolls:,} times...\n')
    result = simulate(args.n, args.rolls, args.sides, rng=rng)
    print(format_summary(result))
    print()

    # Compare empirical vs theoretical mean/std
    diff_m = result['mean'] - result['theoretical_mean']
    diff_s = result['std'] - result['theoretical_std']
    print(f'  d_mean = {diff_m:+.4f}    d_std = {diff_s:+.4f}')
    print()

    if not args.no_hist:
        print('Sum frequency histogram:')
        # Detect cp1252 / ascii-only stdout and fall back to '#'
        encoding = getattr(__import__('sys').stdout, 'encoding', '') or ''
        ascii_only = encoding.lower() in ('cp1252', 'ascii', 'us-ascii',
                                          'charmap')
        try:
            print(render_histogram(result, ascii_only=ascii_only))
        except UnicodeEncodeError:
            print(render_histogram(result, ascii_only=True))


if __name__ == '__main__':
    main()
