"""Dice Roller — parse and roll tabletop RPG dice notation.

Supports standard notation (`2d6+3`, `1d20`, `4d20-1`, `1d100`) and an
extended `kh` / `kl` keep modifier (e.g. `4d6kh3` — roll 4d6 keep highest 3,
the classic D&D 5e ability-score roll).

Run:
    uv run python dice_roller/dice_roller.py
    uv run python dice_roller/dice_roller.py 2d6+3 1d20
    uv run python dice_roller/dice_roller.py --hist 1000 2d6
    uv run python dice_roller/dice_roller.py --seed 42 4d6kh3
"""
from __future__ import annotations

import argparse
import random
import re
import sys
from typing import Optional

# Standard notation: count d sides [+/- modifier]
# Extended:          count d sides [kh|kl N] [+/- modifier]
_DICE_RE = re.compile(
    r"""^\s*
        (?P<count>\d+)?          # optional count, default 1
        d
        (?P<sides>\d+)           # required sides
        (?:                      # optional keep clause
            (?P<keep>kh|kl)
            (?P<keep_n>\d+)
        )?
        (?P<mod>[+-]\d+)?        # optional modifier
        \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

MAX_COUNT = 1000        # sanity cap so 99999d6 doesn't lock the UI
MAX_SIDES = 1_000_000   # absurd-but-bounded


class DiceNotationError(ValueError):
    """Raised when a notation string can't be parsed or is out of range."""


def parse(notation: str) -> tuple[int, int, int]:
    """Parse standard dice notation into ``(count, sides, modifier)``.

    >>> parse('2d6+3')
    (2, 6, 3)
    >>> parse('d20')
    (1, 20, 0)
    >>> parse('4d6-1')
    (4, 6, -1)

    Extended `kh` / `kl` notation parses too but is reported via
    :func:`parse_extended`. This function returns the *raw* count.
    """
    count, sides, modifier, _, _ = parse_extended(notation)
    return count, sides, modifier


def parse_extended(notation: str) -> tuple[int, int, int, Optional[str], int]:
    """Parse extended notation supporting `kh`/`kl` keep modifiers.

    Returns ``(count, sides, modifier, keep_kind, keep_n)`` where
    ``keep_kind`` is ``'kh'``, ``'kl'``, or ``None``.
    """
    if not isinstance(notation, str) or not notation.strip():
        raise DiceNotationError('Empty dice notation.')

    match = _DICE_RE.match(notation)
    if not match:
        raise DiceNotationError(
            f'Bad dice notation: {notation!r}. '
            f"Expected something like '2d6+3', '1d20', or '4d6kh3'."
        )

    count = int(match.group('count')) if match.group('count') else 1
    sides = int(match.group('sides'))
    modifier = int(match.group('mod')) if match.group('mod') else 0
    keep_kind = match.group('keep').lower() if match.group('keep') else None
    keep_n = int(match.group('keep_n')) if match.group('keep_n') else 0

    if count <= 0:
        raise DiceNotationError(f'Dice count must be >= 1 (got {count}).')
    if count > MAX_COUNT:
        raise DiceNotationError(f'Dice count {count} exceeds cap {MAX_COUNT}.')
    if sides < 2:
        raise DiceNotationError(f'Sides must be >= 2 (got {sides}).')
    if sides > MAX_SIDES:
        raise DiceNotationError(f'Sides {sides} exceeds cap {MAX_SIDES}.')
    if keep_kind is not None:
        if keep_n <= 0:
            raise DiceNotationError(f'Keep N must be >= 1 (got {keep_n}).')
        if keep_n > count:
            raise DiceNotationError(
                f'Keep N ({keep_n}) cannot exceed dice count ({count}).'
            )

    return count, sides, modifier, keep_kind, keep_n


def roll(notation: str, rng: Optional[random.Random] = None) -> dict:
    """Roll one dice expression and return a structured result.

    Returns a dict with ``notation``, ``rolls`` (raw rolls, all of them),
    ``kept`` (subset actually summed), ``total``, ``modifier``, plus
    ``keep`` metadata when extended notation was used.

    The optional ``rng`` lets callers pass a seeded ``random.Random()`` for
    deterministic replays — handy for tests, demos, and the CLI ``--seed``.
    """
    rand = rng if rng is not None else random
    count, sides, modifier, keep_kind, keep_n = parse_extended(notation)

    # randint(1, sides) is inclusive on both ends — the off-by-one trap
    # is using randint(0, sides) which silently allows 0.
    rolls = [rand.randint(1, sides) for _ in range(count)]

    if keep_kind == 'kh':
        kept = sorted(rolls, reverse=True)[:keep_n]
    elif keep_kind == 'kl':
        kept = sorted(rolls)[:keep_n]
    else:
        kept = list(rolls)

    total = sum(kept) + modifier

    result = {
        'notation': notation,
        'count': count,
        'sides': sides,
        'rolls': rolls,
        'kept': kept,
        'modifier': modifier,
        'total': total,
    }
    if keep_kind is not None:
        result['keep'] = keep_kind
        result['keep_n'] = keep_n
    return result


def roll_many(notation: str, n: int,
              rng: Optional[random.Random] = None) -> list[int]:
    """Roll ``notation`` ``n`` times, return list of totals.

    Useful for Monte Carlo distribution views (the GUI histogram).
    """
    if n <= 0:
        raise ValueError('n must be >= 1')
    return [roll(notation, rng)['total'] for _ in range(n)]


def split_expressions(line: str) -> list[str]:
    """Split a multi-expression line like '2d6+3, 1d20; 4d6kh3' into parts."""
    parts = re.split(r'[,;]\s*', line.strip())
    return [p for p in parts if p]


def format_result(result: dict) -> str:
    """Pretty single-line summary used by the CLI."""
    rolls_str = ', '.join(str(r) for r in result['rolls'])
    if 'keep' in result:
        kept_str = ', '.join(str(r) for r in result['kept'])
        body = f'rolls=[{rolls_str}] keep={result["keep"]}{result["keep_n"]} -> [{kept_str}]'
    else:
        body = f'rolls=[{rolls_str}]'
    mod = result['modifier']
    mod_str = f' {"+" if mod >= 0 else "-"} {abs(mod)}' if mod else ''
    return f'{result["notation"]}: {body}{mod_str} = {result["total"]}'


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog='dice_roller',
        description='Parse and roll tabletop dice notation (e.g. 2d6+3, 4d6kh3).',
    )
    parser.add_argument('notation', nargs='*',
                        help='One or more dice expressions. '
                             'Omit for interactive mode.')
    parser.add_argument('--seed', type=int, default=None,
                        help='Seed the RNG for reproducible rolls.')
    parser.add_argument('--hist', type=int, default=0, metavar='N',
                        help='Roll the (single) expression N times '
                             'and print a text histogram.')
    args = parser.parse_args(argv)

    rng = random.Random(args.seed) if args.seed is not None else None

    if args.hist:
        if len(args.notation) != 1:
            parser.error('--hist requires exactly one notation argument.')
        _print_histogram(args.notation[0], args.hist, rng)
        return 0

    if args.notation:
        # Each CLI argument may itself be a comma-separated batch.
        joined = ', '.join(args.notation)
        return _run_batch(joined, rng)

    # Interactive REPL.
    print('Dice Roller. Enter notation (e.g. 2d6+3, 1d20). Ctrl+C to quit.')
    try:
        while True:
            try:
                line = input('> ').strip()
            except EOFError:
                print()
                return 0
            if not line:
                continue
            if line.lower() in {'q', 'quit', 'exit'}:
                return 0
            _run_batch(line, rng)
    except KeyboardInterrupt:
        print()
        return 0


def _run_batch(line: str, rng: Optional[random.Random]) -> int:
    grand = 0
    parts = split_expressions(line)
    if not parts:
        print('No expressions found.', file=sys.stderr)
        return 2
    for part in parts:
        try:
            result = roll(part, rng)
        except DiceNotationError as exc:
            print(f'error: {exc}', file=sys.stderr)
            return 2
        print(format_result(result))
        grand += result['total']
    if len(parts) > 1:
        print(f'grand total: {grand}')
    return 0


def _print_histogram(notation: str, n: int,
                     rng: Optional[random.Random]) -> None:
    """Crude ASCII histogram of N rolls — Monte Carlo distribution view."""
    totals = roll_many(notation, n, rng)
    counts: dict[int, int] = {}
    for t in totals:
        counts[t] = counts.get(t, 0) + 1
    lo, hi = min(counts), max(counts)
    peak = max(counts.values())
    width = 40
    print(f'{notation} x{n}  range [{lo}..{hi}]  '
          f'mean={sum(totals)/n:.2f}')
    for value in range(lo, hi + 1):
        c = counts.get(value, 0)
        bar = '#' * round(width * c / peak) if peak else ''
        print(f'{value:>4} | {bar} {c}')


if __name__ == '__main__':
    sys.exit(main())
