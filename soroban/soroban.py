"""Soroban — Japanese abacus renderer.

Pure functions:
    render(n, columns=8) -> str    ASCII soroban for non-negative integer n
    parse(rendered) -> int         inverse of render — read digits from ASCII

A soroban column has two decks separated by a horizontal reckoning bar:

    top deck   — 1 bead worth 5 (active when pushed DOWN to the bar)
    bottom deck — 4 beads worth 1 each (active when pushed UP to the bar)

Active beads (those touching the reckoning bar) sum to the digit in that
column. Each column represents one decimal place; the rightmost column is
the ones place.

Run:
    uv run python soroban/soroban.py 1234
    uv run python soroban/soroban.py --animate 123 456
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

DEFAULT_COLUMNS = 8

# Glyphs used for each row of a single column. Width = 3 chars per column.
# We compose the rendering row by row; each row is a string of length 3.
#   '||'  through frame uprights are the | characters bracketing each bead slot
#   'O'   = bead
#   '='   = horizontal beam where a bead currently rests (above/below the bar)
#   '-'   = reckoning bar
#
# Each column is exactly 3 chars wide so digits can be reliably parsed back.

# Row layout per column (10 rows total):
#   0: top frame                  '+-+'
#   1: top bead high position     bead here when top INACTIVE (digit < 5)
#   2: top bead low position      bead here when top ACTIVE   (digit >= 5)
#   3: reckoning bar              '+=+'
#   4..8: 5 bottom-deck slots — 4 beads + 1 gap. Active beads kiss the bar
#         from row 4 downward; inactive beads rest at the bottom (row 8 up).
#         With bottom_active = 0..4 there's always exactly one empty slot.
#   9: bottom frame               '+-+'

NUM_ROWS = 10
BOTTOM_SLOTS = 5  # 4 beads + 1 gap so movement is visible at every digit


def _column_glyphs(digit: int) -> list[str]:
    """Returns the 9 row-glyphs (3-char strings) for one digit column.

    digit must be in 0..9. Layout described in module docstring.
    """
    if not 0 <= digit <= 9:
        raise ValueError(f'digit out of range: {digit}')

    top_active = 1 if digit >= 5 else 0       # heaven bead pushed DOWN
    bottom_active = digit % 5                  # earth beads pushed UP

    rows: list[str] = []
    rows.append('+-+')  # frame top

    # Top deck: 2 slots. Bead lives in slot1 (high) when INACTIVE,
    # slot2 (low, touching bar) when ACTIVE.
    if top_active:
        rows.append(' | ')  # high slot empty
        rows.append('|O|')  # bead at low slot, kissing the bar
    else:
        rows.append('|O|')  # bead at high slot
        rows.append(' | ')  # low slot empty

    rows.append('+=+')  # reckoning bar

    # Bottom deck has 5 slots; we render top-to-bottom:
    #   `bottom_active` active beads kissing the bar
    #   1 empty slot (the gap — always exactly one, since 4 beads + 1 gap)
    #   `4 - bottom_active` inactive beads resting at the bottom of the frame
    bottom_rows: list[str] = []
    for _ in range(bottom_active):
        bottom_rows.append('|O|')
    bottom_rows.append(' | ')  # the single gap slot
    for _ in range(4 - bottom_active):
        bottom_rows.append('|O|')
    rows.extend(bottom_rows)

    rows.append('+-+')  # frame bottom

    assert len(rows) == NUM_ROWS, rows
    return rows


def _digits_for(n: int, columns: int) -> list[int]:
    """Returns digit list of length `columns`, MSB-first, zero-padded."""
    if n < 0:
        raise ValueError('render does not support negative numbers; '
                         'use signed_render for complementary form')
    s = str(n)
    if len(s) > columns:
        raise ValueError(f'{n} has {len(s)} digits, exceeds {columns} columns')
    s = s.rjust(columns, '0')
    return [int(c) for c in s]


def render(n: int, columns: int = DEFAULT_COLUMNS) -> str:
    """Render integer n as an ASCII soroban with `columns` digit columns.

    The leftmost column is the highest place (10**(columns-1)), rightmost
    is the ones place. Output is multi-line; lines are joined by '\\n' with
    no trailing newline.
    """
    digits = _digits_for(n, columns)
    col_glyphs = [_column_glyphs(d) for d in digits]

    # Each column glyph is 3 chars wide. Join them with a single space gap
    # so column boundaries are clear and parse() can split unambiguously.
    sep = ' '
    out_lines: list[str] = []
    for row_idx in range(NUM_ROWS):
        line = sep.join(col[row_idx] for col in col_glyphs)
        out_lines.append(line)

    # Add a place-value footer so it's obvious which column is ones.
    place_labels = []
    for i, d in enumerate(digits):
        place = 10 ** (columns - 1 - i)
        # Show the place value compactly: 1, 10, 100, 1k, 10k, ...
        if place < 1000:
            label = str(place)
        elif place < 10**6:
            label = f'{place // 1000}k'
        else:
            label = f'{place:.0e}'
        place_labels.append(label.center(3))
    out_lines.append(sep.join(place_labels))
    out_lines.append(sep.join(str(d).center(3) for d in digits))

    return '\n'.join(out_lines)


def parse(rendered: str) -> int:
    """Inverse of render: read the integer from an ASCII soroban string.

    Reads the rows that determine each column's digit:
      - top deck (rows 1..2): bead at row 2 -> +5
      - bottom deck (rows 4..7): each bead immediately under the bar -> +1
    Whitespace-separated columns are detected from the frame row.
    """
    lines = [ln.rstrip('\r') for ln in rendered.split('\n') if ln.strip()]
    if len(lines) < NUM_ROWS:
        raise ValueError('not enough rows to parse a soroban')

    # The first line is the top frame; columns are 3-char chunks separated
    # by single spaces. Detect column count from it.
    frame = lines[0]
    # Split into 3-char chunks ignoring single-space separators:
    cols: list[tuple[int, int]] = []
    i = 0
    while i < len(frame):
        if frame[i] == ' ':
            i += 1
            continue
        cols.append((i, i + 3))
        i += 3

    digits: list[int] = []
    for start, end in cols:
        # Extract this column's 10 rows
        col_rows = [ln[start:end] if len(ln) >= end else ln[start:].ljust(3)
                    for ln in lines[:NUM_ROWS]]
        # Top deck active iff the LOW top slot (row 2) holds a bead.
        top_low = col_rows[2]
        top_active = 1 if 'O' in top_low else 0
        # Bottom deck: count consecutive bead rows starting at row 4 going
        # down until the gap (empty row) is reached.
        bottom_active = 0
        for k in range(BOTTOM_SLOTS):
            row = col_rows[4 + k]
            if 'O' in row:
                bottom_active += 1
            else:
                break
        digit = top_active * 5 + bottom_active
        digits.append(digit)

    if not digits:
        return 0
    return int(''.join(str(d) for d in digits))


# ---------------------------------------------------------------------------
# Animation: bead movements for arithmetic
# ---------------------------------------------------------------------------

def animate_addition(a: int, b: int, columns: int = DEFAULT_COLUMNS,
                     delay: float = 0.45,
                     stream=None) -> int:
    """Animate `a + b` as bead movements, one digit-place at a time.

    Prints the soroban after each step to `stream` (default stdout) and
    returns the final sum. Steps:
        1. Render a (the starting position)
        2. For each place from ones up, add the corresponding digit of b
           by re-rendering the running total. Carries naturally appear in
           the next column.
    """
    if stream is None:
        stream = sys.stdout
    if a < 0 or b < 0:
        raise ValueError('animate_addition requires non-negative operands')

    total = a
    _print_frame(stream, total, columns, header=f'Start: {a}')
    time.sleep(delay)

    # Add digit-by-digit from least significant to most significant
    b_str = str(b).rjust(columns, '0')
    for place_index, ch in enumerate(reversed(b_str)):
        digit = int(ch)
        if digit == 0:
            continue
        addend = digit * (10 ** place_index)
        total += addend
        place_name = _place_name(place_index)
        _print_frame(stream, total, columns,
                     header=f'+ {addend} ({digit} in the {place_name} place)'
                            f' = {total}')
        time.sleep(delay)

    _print_frame(stream, total, columns, header=f'Final: {a} + {b} = {total}')
    return total


def _place_name(index: int) -> str:
    names = ['ones', 'tens', 'hundreds', 'thousands',
             'ten-thousands', 'hundred-thousands', 'millions']
    return names[index] if index < len(names) else f'10^{index}'


def _print_frame(stream, n: int, columns: int, header: str) -> None:
    bar = '-' * max(40, len(header))
    stream.write(f'\n{bar}\n{header}\n{bar}\n')
    stream.write(render(n, columns))
    stream.write('\n')
    stream.flush()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='soroban',
        description='Render integers as a Japanese soroban (abacus).',
    )
    parser.add_argument('numbers', nargs='*', type=int,
                        help='one number to render, or two numbers to '
                             'animate addition')
    parser.add_argument('-c', '--columns', type=int, default=DEFAULT_COLUMNS,
                        help=f'number of digit columns (default {DEFAULT_COLUMNS})')
    parser.add_argument('--animate', action='store_true',
                        help='animate addition; requires exactly two numbers')
    parser.add_argument('--delay', type=float, default=0.45,
                        help='animation step delay in seconds (default 0.45)')
    parser.add_argument('--roundtrip', action='store_true',
                        help='render N, parse it back, print parsed value')

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.animate:
        if len(args.numbers) != 2:
            parser.error('--animate requires exactly two numbers')
        animate_addition(args.numbers[0], args.numbers[1],
                         columns=args.columns, delay=args.delay)
        return 0

    if not args.numbers:
        # Interactive demo
        print('Soroban — Japanese abacus.')
        print('Enter a non-negative integer (blank to quit):')
        while True:
            try:
                line = input('> ').strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if not line:
                return 0
            if not line.lstrip('-').isdigit() or line.startswith('-'):
                print('  please enter a non-negative integer')
                continue
            try:
                n = int(line)
                print(render(n, args.columns))
            except ValueError as e:
                print(f'  {e}')

    n = args.numbers[0]
    rendered = render(n, args.columns)
    print(rendered)
    if args.roundtrip:
        back = parse(rendered)
        print(f'\nparsed back: {back}  (matches: {back == n})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
