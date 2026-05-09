"""ROT13 Cipher — CLI.

ROT13 shifts each letter by 13 positions in the alphabet. Because the alphabet
has 26 letters, applying ROT13 twice returns the original text — the cipher is
its own inverse (an involution). This makes encrypt and decrypt the same op,
which is why ROT13 was the de-facto Usenet spoiler-hider for decades.

The CLI generalizes to any rotation via `--rot N`:

    uv run python rot13/rot13.py "Hello, World!"
    uv run python rot13/rot13.py --rot 5 "Hello"
    uv run python rot13/rot13.py --rot47 "Hello, World! 42?"

Run with no text for an interactive prompt.
"""
from __future__ import annotations

import argparse
import sys

ALPHABET_SIZE = 26

# ROT47 operates on printable ASCII 33..126 (94 chars), so 47 is its half-period
# and rot47 is also an involution. It hides punctuation/digits too — useful for
# spoilers that aren't pure prose.
ROT47_LO = 33
ROT47_HI = 126
ROT47_RANGE = ROT47_HI - ROT47_LO + 1  # 94


def rot13(text: str) -> str:
    """Apply ROT13 to `text`. Case preserved; non-letters pass through.

    Self-inverse: ``rot13(rot13(s)) == s`` for every string ``s``.
    """
    return rotate(text, 13)


def rotate(text: str, n: int) -> str:
    """Rotate letters by `n` positions. Generalization of rot13.

    `n` is taken mod 26; ``rotate(text, 0)`` is the identity. Non-letters
    pass through unchanged. Negative `n` rotates backward.
    """
    shift = n % ALPHABET_SIZE
    if shift == 0:
        return text
    out: list[str] = []
    for ch in text:
        if 'a' <= ch <= 'z':
            out.append(chr((ord(ch) - ord('a') + shift) % ALPHABET_SIZE
                           + ord('a')))
        elif 'A' <= ch <= 'Z':
            out.append(chr((ord(ch) - ord('A') + shift) % ALPHABET_SIZE
                           + ord('A')))
        else:
            out.append(ch)
    return ''.join(out)


def rot47(text: str) -> str:
    """Apply ROT47 to `text`. Affects all printable ASCII 33..126.

    Like rot13, applying ROT47 twice yields the original. Unlike rot13 it
    also rotates digits, punctuation, and symbols — handy for spoilers that
    contain numbers (e.g. "Page 273 of the book").
    """
    out: list[str] = []
    for ch in text:
        code = ord(ch)
        if ROT47_LO <= code <= ROT47_HI:
            out.append(chr((code - ROT47_LO + 47) % ROT47_RANGE + ROT47_LO))
        else:
            out.append(ch)
    return ''.join(out)


def is_involution(text: str, fn) -> bool:
    """Verify a transform is self-inverse on `text`.

    Used by the demo / test suite to make the involution property explicit.
    """
    return fn(fn(text)) == text


def _interactive() -> None:
    print('ROT13 Cipher')
    print('=' * 40)
    print('Type text and press Enter. Empty line quits.')
    print('Apply twice → identity (rot13 is its own inverse).')
    while True:
        try:
            text = input('\nText: ')
        except EOFError:
            return
        if not text:
            print('Bye.')
            return
        once = rot13(text)
        twice = rot13(once)
        print(f'  rot13     : {once}')
        print(f'  rot13² (=): {twice}    {"OK" if twice == text else "MISMATCH"}')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='rot13',
        description='ROT13 cipher (and friends). Self-inverse: '
                    'applying twice returns the original.',
    )
    parser.add_argument('text', nargs='*',
                        help='text to rotate (omit for interactive mode)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--rot', type=int, default=13, metavar='N',
                       help='rotation amount over A-Z (default 13). '
                            'Use --rot 13 to round-trip; any N works.')
    group.add_argument('--rot47', action='store_true',
                       help='use ROT47 over printable ASCII 33..126 instead')
    parser.add_argument('--demo', action='store_true',
                        help='show that applying twice returns the input')
    args = parser.parse_args()

    if not args.text:
        _interactive()
        return

    text = ' '.join(args.text)
    if args.rot47:
        out = rot47(text)
        twice = rot47(out)
        label = 'rot47'
    else:
        out = rotate(text, args.rot)
        # Round-trip works only when 2*N is a multiple of 26 — i.e. N==13 or N==0.
        twice = rotate(out, args.rot)
        label = f'rot{args.rot}'

    if args.demo:
        print(f'input         : {text}')
        print(f'{label:<13} : {out}')
        print(f'{label} x2{"":<6}: {twice}')
        print(f'identity?     : {"YES (involution)" if twice == text else "no"}')
    else:
        sys.stdout.write(out + '\n')


if __name__ == '__main__':
    main()
