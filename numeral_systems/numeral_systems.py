"""Numeral Systems — CLI.

Convert numbers between arbitrary bases (2..36) and Roman numerals (1..3999).

The pure functions here are imported by the GUI and TUI siblings:

    to_base(n, base)     -> str   integer -> base-N string
    from_base(s, base)   -> int   base-N string -> integer
    to_roman(n)          -> str   integer (1..3999) -> Roman numeral
    from_roman(s)        -> int   Roman numeral -> integer
    to_base_fractional(x, base)   real number -> base-N string with fraction
    from_base_fractional(s, base) base-N string with fraction -> float
    to_twos_complement(n, bits)   signed integer -> two's-complement bit string

Run:
    uv run python numeral_systems/numeral_systems.py
    uv run python numeral_systems/numeral_systems.py --from 10 --to 16 255
    uv run python numeral_systems/numeral_systems.py --to roman 2024
"""
from __future__ import annotations

import argparse
import sys

DIGITS = '0123456789abcdefghijklmnopqrstuvwxyz'

# Roman numerals: greedy decomposition table covers 1..3999.
ROMAN_PAIRS = [
    (1000, 'M'),  (900, 'CM'), (500, 'D'),  (400, 'CD'),
    (100,  'C'),  (90,  'XC'), (50,  'L'),  (40,  'XL'),
    (10,   'X'),  (9,   'IX'), (5,   'V'),  (4,   'IV'),
    (1,    'I'),
]
ROMAN_VALUE = {ch: v for v, sym in ROMAN_PAIRS for ch, v in [(sym, v)]
               if len(sym) == 1}
# Single-letter values for the validation pass.
ROMAN_VALUE = {'I': 1, 'V': 5, 'X': 10, 'L': 50,
               'C': 100, 'D': 500, 'M': 1000}


# ---------------------------------------------------------------- arbitrary base
def to_base(n: int, base: int) -> str:
    """Convert integer `n` to its base-`base` string (lowercase, no prefix).

    `base` must be 2..36. Negative `n` gets a leading '-'. Zero -> '0'.
    """
    if not 2 <= base <= 36:
        raise ValueError(f'base must be 2..36, got {base}')
    if n == 0:
        return '0'
    sign = '-' if n < 0 else ''
    n = abs(n)
    out: list[str] = []
    while n:
        n, rem = divmod(n, base)
        out.append(DIGITS[rem])
    return sign + ''.join(reversed(out))


def from_base(s: str, base: int) -> int:
    """Parse a base-`base` string into an integer.

    Accepts upper- or lowercase digits, optional leading '+' / '-', and
    common prefixes (`0b`, `0o`, `0x`) when they match the requested base.
    Whitespace is stripped.
    """
    if not 2 <= base <= 36:
        raise ValueError(f'base must be 2..36, got {base}')
    raw = s.strip()
    if not raw:
        raise ValueError('empty string')
    sign = 1
    if raw[0] in '+-':
        if raw[0] == '-':
            sign = -1
        raw = raw[1:]
    # Strip a 0x/0b/0o prefix if it matches the base.
    if len(raw) >= 2 and raw[0] == '0' and raw[1].lower() in 'bxo':
        prefix = raw[1].lower()
        prefix_base = {'b': 2, 'o': 8, 'x': 16}[prefix]
        if prefix_base == base:
            raw = raw[2:]
    if not raw:
        raise ValueError('no digits after sign/prefix')
    # Built-in int() does the heavy lifting and raises a clear ValueError
    # for digits outside the requested base.
    return sign * int(raw, base)


# ---------------------------------------------------------------- fractional base
def to_base_fractional(x: float, base: int, places: int = 12) -> str:
    """Convert real `x` to base-`base` with up to `places` fractional digits.

    Trailing zeros are stripped. If `x` has no fractional part, the result
    has no decimal point.

        >>> to_base_fractional(0.625, 2)
        '0.101'
        >>> to_base_fractional(-2.75, 2)
        '-10.11'
        >>> to_base_fractional(255.0, 16)
        'ff'
    """
    if not 2 <= base <= 36:
        raise ValueError(f'base must be 2..36, got {base}')
    if x != x or x in (float('inf'), float('-inf')):
        raise ValueError('x must be finite')
    sign = '-' if x < 0 else ''
    x = abs(x)
    int_part = int(x)
    frac = x - int_part
    int_str = to_base(int_part, base)

    if frac == 0:
        return sign + int_str

    digits: list[str] = []
    for _ in range(places):
        frac *= base
        d = int(frac)
        if d >= base:  # float rounding edge case
            d = base - 1
        digits.append(DIGITS[d])
        frac -= d
        if frac == 0:
            break
    # Strip trailing zeros — neat output.
    while digits and digits[-1] == '0':
        digits.pop()
    if not digits:
        return sign + int_str
    return sign + int_str + '.' + ''.join(digits)


def from_base_fractional(s: str, base: int) -> float:
    """Parse a string with optional fractional part in base-`base`.

    Returns a `float`. Pure-integer input still works — '255' in base 16
    returns `255.0`.
    """
    if not 2 <= base <= 36:
        raise ValueError(f'base must be 2..36, got {base}')
    raw = s.strip()
    if not raw:
        raise ValueError('empty string')
    sign = 1.0
    if raw[0] in '+-':
        if raw[0] == '-':
            sign = -1.0
        raw = raw[1:]
    if '.' in raw:
        int_str, frac_str = raw.split('.', 1)
    else:
        int_str, frac_str = raw, ''
    if not int_str and not frac_str:
        raise ValueError('no digits')
    int_val = from_base(int_str, base) if int_str else 0
    frac_val = 0.0
    if frac_str:
        weight = 1.0 / base
        for ch in frac_str:
            d = DIGITS.find(ch.lower())
            if d < 0 or d >= base:
                raise ValueError(f'digit {ch!r} not valid in base {base}')
            frac_val += d * weight
            weight /= base
    return sign * (int_val + frac_val)


# ---------------------------------------------------------------- two's complement
def to_twos_complement(n: int, bits: int = 8) -> str:
    """Return the `bits`-wide two's-complement binary string of `n`.

    Raises if `n` doesn't fit in `bits` signed bits.
    """
    if bits < 1:
        raise ValueError('bits must be >= 1')
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    if not lo <= n <= hi:
        raise ValueError(f'{n} does not fit in {bits} signed bits '
                         f'(range {lo}..{hi})')
    if n < 0:
        n += 1 << bits
    return format(n, f'0{bits}b')


def from_twos_complement(bits_str: str) -> int:
    """Interpret a binary string as a two's-complement signed integer."""
    raw = bits_str.strip().replace(' ', '')
    if not raw or any(c not in '01' for c in raw):
        raise ValueError('expected binary digits only')
    n = int(raw, 2)
    if raw[0] == '1':  # MSB set => negative
        n -= 1 << len(raw)
    return n


# ---------------------------------------------------------------- roman numerals
def to_roman(n: int) -> str:
    """Convert integer 1..3999 to a Roman numeral.

        >>> to_roman(2024)
        'MMXXIV'
        >>> to_roman(1994)
        'MCMXCIV'
    """
    if not 1 <= n <= 3999:
        raise ValueError(f'Roman numerals defined here for 1..3999, got {n}')
    out: list[str] = []
    for value, symbol in ROMAN_PAIRS:
        while n >= value:
            out.append(symbol)
            n -= value
    return ''.join(out)


def from_roman(s: str) -> int:
    """Parse a (case-insensitive) Roman numeral.

    Validates that the input round-trips through `to_roman` — anything that
    isn't canonical (e.g. `IIII`, `VX`, `IM`) raises `ValueError`.
    """
    raw = s.strip().upper()
    if not raw:
        raise ValueError('empty Roman numeral')
    if any(ch not in ROMAN_VALUE for ch in raw):
        bad = [ch for ch in raw if ch not in ROMAN_VALUE]
        raise ValueError(f'invalid Roman character(s): {bad}')
    # Standard left-to-right scan: subtract when a smaller numeral precedes
    # a larger one (e.g. IV = 4, IX = 9), otherwise add.
    total = 0
    prev = 0
    for ch in reversed(raw):
        v = ROMAN_VALUE[ch]
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    if not 1 <= total <= 3999:
        raise ValueError(f'Roman numeral parses to {total}, out of range')
    # Round-trip guard: rejects malformed forms like IIII, VX, IC.
    if to_roman(total) != raw:
        raise ValueError(f'{s!r} is not a canonical Roman numeral '
                         f'(canonical form is {to_roman(total)!r})')
    return total


# ---------------------------------------------------------------- helpers / CLI
BASE_ALIASES = {
    'bin': 2, 'binary': 2, 'b': 2,
    'oct': 8, 'octal': 8, 'o': 8,
    'dec': 10, 'decimal': 10, 'd': 10,
    'hex': 16, 'hexadecimal': 16, 'h': 16, 'x': 16,
}


def parse_base(spec: str) -> str | int:
    """Resolve a base spec (e.g. '16', 'hex', 'roman') to an int or 'roman'."""
    s = spec.strip().lower()
    if s == 'roman':
        return 'roman'
    if s in BASE_ALIASES:
        return BASE_ALIASES[s]
    try:
        n = int(s)
    except ValueError as exc:
        raise ValueError(f'unknown base {spec!r}') from exc
    if not 2 <= n <= 36:
        raise ValueError(f'numeric base must be 2..36, got {n}')
    return n


def convert(value: str, src: str | int, dst: str | int) -> str:
    """Convert `value` from base `src` to base `dst`.

    `src` and `dst` may be int (2..36) or the string 'roman'.
    """
    if src == 'roman':
        n = from_roman(value)
    else:
        # Fractional input is allowed for numeric bases.
        if '.' in value:
            x = from_base_fractional(value, src)
            if dst == 'roman':
                if x != int(x):
                    raise ValueError('cannot convert non-integer to Roman')
                return to_roman(int(x))
            return to_base_fractional(x, dst)
        n = from_base(value, src)
    if dst == 'roman':
        return to_roman(n)
    return to_base(n, dst)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='numeral_systems',
        description='Convert numbers between bases (2..36) and Roman numerals.',
    )
    parser.add_argument('--from', dest='src', default='10',
                        help="source base: 2..36, 'bin/oct/dec/hex', or 'roman'")
    parser.add_argument('--to', dest='dst', default='2',
                        help="target base: 2..36, 'bin/oct/dec/hex', or 'roman'")
    parser.add_argument('--bits', type=int, default=0,
                        help="if set, render binary as N-bit two's complement")
    parser.add_argument('value', nargs='?',
                        help='value to convert (omit for interactive mode)')
    args = parser.parse_args(argv)

    if args.value is None:
        return _interactive()

    try:
        src = parse_base(args.src)
        dst = parse_base(args.dst)
        if args.bits and dst == 2 and src != 'roman' and '.' not in args.value:
            n = from_base(args.value, src)
            print(to_twos_complement(n, args.bits))
        else:
            print(convert(args.value, src, dst))
    except ValueError as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1
    return 0


def _interactive() -> int:
    print('Numeral Systems')
    print('=' * 40)
    print("Bases: 2..36 (or bin/oct/dec/hex), plus 'roman'.")
    print("Type 'q' to quit.")
    while True:
        raw_src = input('\nFrom base [dec]: ').strip() or 'dec'
        if raw_src.lower() in ('q', 'quit', 'exit'):
            print('Bye.')
            return 0
        raw_dst = input('To base   [hex]: ').strip() or 'hex'
        value = input('Value          : ').strip()
        if not value:
            continue
        try:
            src = parse_base(raw_src)
            dst = parse_base(raw_dst)
            print('  =', convert(value, src, dst))
        except ValueError as exc:
            print('  error:', exc)


if __name__ == '__main__':
    raise SystemExit(main())
