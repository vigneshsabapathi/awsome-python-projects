# Numeral Systems

Convert numbers between **arbitrary bases (2..36)** and **Roman numerals** (1..3999), with two extras the textbook version skips: **fractional bases** (e.g. `0.625` in decimal becomes `0.101` in binary) and **two's-complement** binary for negative integers.

Three flavours, one shared core:

| Version | File | Stack |
|---|---|---|
| CLI | `numeral_systems.py` | stdlib + `argparse` |
| Desktop GUI | `numeral_systems_gui.py` | CustomTkinter |
| Terminal UI | `numeral_systems_tui.py` | Textual |

## Run

```bash
# CLI - one-shot mode
uv run python numeral_systems/numeral_systems.py --from 10 --to 16 255
# -> ff
uv run python numeral_systems/numeral_systems.py --to roman 2024
# -> MMXXIV
uv run python numeral_systems/numeral_systems.py --from 10 --to 2 --bits 8 -- -1
# -> 11111111

# CLI - interactive prompt
uv run python numeral_systems/numeral_systems.py

# Desktop GUI - multi-base entry, slider for base 2..36, Roman + two's complement panel
uv run python numeral_systems/numeral_systems_gui.py

# Terminal UI - same multi-base panel, Tailwind dark theme
uv run python numeral_systems/numeral_systems_tui.py
```

## How it works

The core lives in `numeral_systems.py` and is `import`-clean:

```python
from numeral_systems import (
    to_base, from_base,            # int <-> base 2..36
    to_base_fractional, from_base_fractional,
    to_roman, from_roman,          # 1..3999
    to_twos_complement, from_twos_complement,
)
```

### Base conversion (integers)

`to_base(n, base)` peels digits off the right with `divmod` and indexes into `'0123456789abcdefghijklmnopqrstuvwxyz'`:

```python
while n:
    n, rem = divmod(n, base)
    out.append(DIGITS[rem])
```

`from_base` defers to the standard-library `int(s, base)` for the heavy lifting, plus a small wrapper that handles signs and the optional `0b/0o/0x` prefix.

### Fractional bases

The "long division" trick. Multiply the fractional part by the base; the integer part of the result is the next digit:

```python
for _ in range(places):
    frac *= base
    d = int(frac)
    digits.append(DIGITS[d])
    frac -= d
    if frac == 0: break
```

This is why `0.625 -> 0.101` in binary: `0.625 * 2 = 1.25 -> 1`, `0.25 * 2 = 0.5 -> 0`, `0.5 * 2 = 1.0 -> 1`, then zero. The reverse uses `digit * base^-k`.

Floats can't represent every base-N fraction exactly (e.g. `0.1` in binary repeats forever), so `to_base_fractional` caps at 12 places and trims trailing zeros for clean output.

### Two's complement

Two's-complement *N*-bit representation of a negative integer is just `n + 2^N`. For positive `n`, it's the plain binary padded to width:

```python
if n < 0: n += 1 << bits
return format(n, f'0{bits}b')
```

The reverse: parse as unsigned, then if the MSB is set subtract `2^N` to recover the sign.

### Roman numerals

A greedy decomposition table. Walk it largest-to-smallest, appending the symbol whenever it fits:

```python
ROMAN_PAIRS = [
    (1000, 'M'), (900, 'CM'), (500, 'D'), (400, 'CD'),
    (100,  'C'), (90,  'XC'), (50,  'L'),  (40,  'XL'),
    (10,   'X'), (9,   'IX'), (5,   'V'),  (4,   'IV'),
    (1,    'I'),
]
for value, symbol in ROMAN_PAIRS:
    while n >= value:
        out.append(symbol); n -= value
```

The "subtractive" pairs (`CM`, `CD`, `XC`, `XL`, `IX`, `IV`) sit in the table alongside the additive ones, so the greedy pass produces canonical numerals on its own — no special-case logic.

`from_roman` does the standard right-to-left scan (subtract when a smaller digit precedes a larger one) **and** round-trips through `to_roman` to reject non-canonical forms like `IIII`, `VX`, `IC`. Garbage in — `ValueError` out.

## What the GUI shows

A live multi-base panel with one row per base (Binary, Octal, Decimal, Hex), an **arbitrary base slider** for 2..36 with its own entry, a Roman numeral entry, and a two's-complement entry with width selector (8/16/32/64 bits). Type into any field and every other field repaints from the new value. Type `0.625` into the decimal box and watch every other base render the fractional part too.

## What the TUI shows

The same multi-base panel in Textual, with the Tailwind slate/sky palette used elsewhere in this repo. Status line at the bottom turns green on parse, red on error.

Bindings:

- **Ctrl+Q** — quit
- **Ctrl+Up / Ctrl+Down** — bump the arbitrary base up or down (clamped 2..36)

## CLI flags

```
--from BASE   source base (2..36, bin/oct/dec/hex, or 'roman'). default: 10
--to BASE     target base (2..36, bin/oct/dec/hex, or 'roman'). default: 2
--bits N      when --to is 2 (binary), render as N-bit two's complement
VALUE         the value to convert (omit for interactive mode)
```

Negative values need the `--` separator so argparse doesn't parse the leading `-` as a flag:

```bash
uv run python numeral_systems/numeral_systems.py --from 10 --to 2 --bits 8 -- -1
# 11111111
```

## Architecture

`numeral_systems.py` exposes the pure functions. The GUI and TUI both:

1. Hold a single source-of-truth value (a `float`, since fractional input is allowed).
2. On any keystroke, parse the changed field into that value.
3. Re-render every *other* field from it.

That last "every other" is the whole live-update trick — guarded by a `_suspend` flag so the programmatic `set` calls don't trigger another round of `KeyRelease` handlers.
