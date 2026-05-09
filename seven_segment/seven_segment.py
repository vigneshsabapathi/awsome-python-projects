"""Seven-Segment Display — render numbers and text as classic LCD-style ASCII.

A focused rendering library: take a string, get back 3-line ASCII art that
looks like a calculator's seven-segment display. Distinct from the
``countdown`` project, which is the *timer* use-case — this one is the
generic *library* use-case (any number, any subset of letters, optional
"warm-up" animation effect on the segments).

Run:
    uv run python seven_segment/seven_segment.py 12345
    uv run python seven_segment/seven_segment.py --warmup HELLO
    uv run python seven_segment/seven_segment.py "PI = 3.14"

API:
    digit_art(ch)       -> list[str]  # 3 lines, fixed width per char
    render(text)        -> str        # 3-line concatenated display
    available_chars()   -> str        # everything we can render

Twist: the calculator-letter subset (A B C d E F H I L o P r S U y -)
that real seven-segment LCDs use, plus an animated warm-up effect that
lights segments up gradually when run from the CLI.
"""
from __future__ import annotations

import argparse
import sys
import time

DIGIT_HEIGHT = 3

# Hand-authored from scratch — 3 lines tall, fixed width per character.
# Width is 5 columns for full digits/letters; ":", ".", " " are narrower
# so they look right next to wider neighbors (just like a real LCD).
#
# Letter subset is the calculator/seven-segment convention: not every
# letter has a faithful 7-seg form, so we cover the canonical ones and
# fall back for the rest to a best-effort rendering. Lowercase 'b', 'd',
# 'h', 'n', 'o', 'r', 'u', 'y' are the traditional lowercase forms.
_GLYPHS: dict[str, list[str]] = {
    '0': [
        ' _ ',
        '| |',
        '|_|',
    ],
    '1': [
        '   ',
        '  |',
        '  |',
    ],
    '2': [
        ' _ ',
        ' _|',
        '|_ ',
    ],
    '3': [
        ' _ ',
        ' _|',
        ' _|',
    ],
    '4': [
        '   ',
        '|_|',
        '  |',
    ],
    '5': [
        ' _ ',
        '|_ ',
        ' _|',
    ],
    '6': [
        ' _ ',
        '|_ ',
        '|_|',
    ],
    '7': [
        ' _ ',
        '  |',
        '  |',
    ],
    '8': [
        ' _ ',
        '|_|',
        '|_|',
    ],
    '9': [
        ' _ ',
        '|_|',
        ' _|',
    ],
    # Punctuation & symbols.
    ':': [
        '   ',
        ' . ',
        ' . ',
    ],
    '.': [
        '   ',
        '   ',
        ' . ',
    ],
    '+': [
        '   ',
        ' + ',
        '   ',
    ],
    '-': [
        '   ',
        ' _ ',
        '   ',
    ],
    ' ': [
        '   ',
        '   ',
        '   ',
    ],
    # Calculator-display letter subset. Letters that genuinely have a
    # 7-segment form get one; others fall back gracefully.
    'A': [
        ' _ ',
        '|_|',
        '| |',
    ],
    'B': [  # really 'b' — uppercase and lowercase share this glyph
        '   ',
        '|_ ',
        '|_|',
    ],
    'C': [
        ' _ ',
        '|  ',
        '|_ ',
    ],
    'D': [  # really 'd'
        '   ',
        ' _|',
        '|_|',
    ],
    'E': [
        ' _ ',
        '|_ ',
        '|_ ',
    ],
    'F': [
        ' _ ',
        '|_ ',
        '|  ',
    ],
    'G': [  # like 6 but with the bottom-right segment
        ' _ ',
        '|_ ',
        '|_|',
    ],
    'H': [
        '   ',
        '|_|',
        '| |',
    ],
    'I': [
        '   ',
        ' | ',
        ' | ',
    ],
    'J': [
        '   ',
        '  |',
        '|_|',
    ],
    'L': [
        '   ',
        '|  ',
        '|_ ',
    ],
    'N': [  # lowercase 'n'
        '   ',
        ' _ ',
        '| |',
    ],
    'O': [  # lowercase 'o' on a calculator
        '   ',
        ' _ ',
        '|_|',
    ],
    'P': [
        ' _ ',
        '|_|',
        '|  ',
    ],
    'R': [  # lowercase 'r'
        '   ',
        ' _ ',
        '|  ',
    ],
    'S': [  # same shape as 5
        ' _ ',
        '|_ ',
        ' _|',
    ],
    'T': [  # lowercase 't'
        '   ',
        '|_ ',
        '|_ ',
    ],
    'U': [
        '   ',
        '| |',
        '|_|',
    ],
    'Y': [  # lowercase 'y'
        '   ',
        '|_|',
        ' _|',
    ],
}

# Letters with no faithful 7-seg form get fallbacks — mostly lowercase
# variants or a sensible visual stand-in. This keeps render() total over
# A-Z so callers don't have to filter input.
_FALLBACKS: dict[str, str] = {
    'K': 'H',  # closest 7-seg neighbor
    'M': 'N',
    'Q': 'O',
    'V': 'U',
    'W': 'U',
    'X': 'H',
    'Z': '2',  # 2 and Z share a shape
}


def available_chars() -> str:
    """Return every character render() can faithfully draw."""
    return ''.join(sorted(_GLYPHS))


def digit_art(s: str) -> list[str]:
    """Return the 3-line seven-segment ASCII art for a single character.

    Accepts any single char in ``available_chars()`` plus A-Z (case
    insensitive — calculator letters are conventionally one case anyway).
    Falls back to a best-effort glyph for letters without a faithful
    7-seg form, and to a blank cell for unknown chars.
    """
    if len(s) != 1:
        raise ValueError(f'digit_art expects one char, got {s!r}')
    key = s.upper()
    if key in _GLYPHS:
        return list(_GLYPHS[key])
    if key in _FALLBACKS:
        return list(_GLYPHS[_FALLBACKS[key]])
    # Unknown char — render as blank space, same width as a digit so
    # multi-char rendering stays aligned.
    return list(_GLYPHS[' '])


def render(text: str) -> str:
    """Render ``text`` as a 3-line seven-segment string.

    Characters are concatenated horizontally with no gutter — each
    glyph already has its own internal padding. The result has exactly
    ``DIGIT_HEIGHT`` (3) lines joined by '\\n'.
    """
    if text == '':
        return '\n' * (DIGIT_HEIGHT - 1)
    rows = ['' for _ in range(DIGIT_HEIGHT)]
    for ch in text:
        art = digit_art(ch)
        for r in range(DIGIT_HEIGHT):
            rows[r] += art[r]
    return '\n'.join(rows)


# --- Twist: animated warm-up effect ----------------------------------------
# Segments "light up" gradually — we reveal the rendered glyph one
# character of segment at a time, in a fixed reveal order that approximates
# a real LCD warming up (top bar first, then sides, then bottom bar).
#
# Implementation is intentionally simple: render the final art, then for
# each step replace some fraction of the non-space chars with spaces in
# the prefix so they appear progressively. Steps go from 0 to 1.0.

_REVEAL_ORDER = '_|.+'  # roughly: bars first, then verticals, then dots/plus


def warmup_frames(text: str, steps: int = 6) -> list[str]:
    """Return ``steps`` progressive frames of ``text`` lighting up.

    The final frame is always the fully rendered display. Earlier frames
    have segments hidden (replaced with spaces) according to a reveal
    order that mimics a real LCD warming up.
    """
    if steps < 1:
        raise ValueError('steps must be >= 1')
    full = render(text)
    if steps == 1:
        return [full]

    # Collect all segment positions, ordered by char-priority then row.
    positions: list[tuple[int, int, str]] = []  # (line_idx, col, char)
    for li, line in enumerate(full.splitlines()):
        for col, ch in enumerate(line):
            if ch != ' ':
                positions.append((li, col, ch))
    # Sort by reveal priority: chars in _REVEAL_ORDER come first in order.
    def _key(item: tuple[int, int, str]) -> tuple[int, int, int]:
        _li, _col, c = item
        try:
            pri = _REVEAL_ORDER.index(c)
        except ValueError:
            pri = len(_REVEAL_ORDER)
        return (pri, _li, _col)
    positions.sort(key=_key)

    frames: list[str] = []
    for step in range(1, steps + 1):
        ratio = step / steps
        cutoff = int(len(positions) * ratio)
        visible = set((li, col) for li, col, _c in positions[:cutoff])
        lines = full.splitlines()
        out_lines = []
        for li, line in enumerate(lines):
            new_line = ''.join(
                ch if ch == ' ' or (li, col) in visible else ' '
                for col, ch in enumerate(line)
            )
            out_lines.append(new_line)
        frames.append('\n'.join(out_lines))
    return frames


def _animate_warmup(text: str, steps: int = 6, delay: float = 0.08) -> None:
    """Print warm-up frames in place (terminal must support ANSI)."""
    frames = warmup_frames(text, steps)
    for i, frame in enumerate(frames):
        if i > 0:
            # Move cursor up DIGIT_HEIGHT lines and clear them.
            sys.stdout.write('\033[F\033[2K' * DIGIT_HEIGHT)
        sys.stdout.write(frame + '\n')
        sys.stdout.flush()
        if i < len(frames) - 1:
            time.sleep(delay)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Render text as classic seven-segment LCD-style ASCII.')
    parser.add_argument('text', nargs='*',
                        help='text to render (default: prompt)')
    parser.add_argument('--warmup', action='store_true',
                        help='animate a segment warm-up effect')
    parser.add_argument('--steps', type=int, default=6,
                        help='warm-up steps (default: 6)')
    parser.add_argument('--list', action='store_true',
                        help='list all renderable characters and exit')
    args = parser.parse_args()

    if args.list:
        print('Renderable characters:')
        print(' ' + ' '.join(available_chars()))
        return

    text = ' '.join(args.text) if args.text else input('Text: ')
    if args.warmup:
        try:
            _animate_warmup(text, args.steps)
        except KeyboardInterrupt:
            print()
    else:
        print(render(text))


if __name__ == '__main__':
    main()
