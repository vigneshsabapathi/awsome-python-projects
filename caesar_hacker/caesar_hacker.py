"""Caesar Hacker — brute-force Caesar cipher cracker.

Inspired by Al Sweigart's project of the same name from
"The Big Book of Small Python Projects". This is an independent
implementation: we try every one of the 26 possible Caesar shifts,
score each candidate plaintext against the English letter-frequency
distribution using a chi-squared-style metric, and return the
candidates ranked best-first.

Pure functions only — GUI/TUI front-ends import from this module.

Run:
    uv run python caesar_hacker/caesar_hacker.py
"""
from __future__ import annotations

from collections import Counter
from typing import Iterable

# Relative letter frequencies in English text, percent-style.
# Source: Lewand / Cornell letter-frequency tables. Sums to ~100.
ENGLISH_FREQ: dict[str, float] = {
    'A':  8.167, 'B':  1.492, 'C':  2.782, 'D':  4.253, 'E': 12.702,
    'F':  2.228, 'G':  2.015, 'H':  6.094, 'I':  6.966, 'J':  0.153,
    'K':  0.772, 'L':  4.025, 'M':  2.406, 'N':  6.749, 'O':  7.507,
    'P':  1.929, 'Q':  0.095, 'R':  5.987, 'S':  6.327, 'T':  9.056,
    'U':  2.758, 'V':  0.978, 'W':  2.360, 'X':  0.150, 'Y':  1.974,
    'Z':  0.074,
}

ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

# Small dictionary of very common English words. Used as a corrective
# bonus on top of chi-squared scoring — chi-squared is noisy on short
# texts ("Hello, World!" has only 10 letters), but matching even one
# common word is strong evidence that a candidate is real English.
COMMON_WORDS: frozenset[str] = frozenset({
    'THE', 'BE', 'TO', 'OF', 'AND', 'A', 'IN', 'THAT', 'HAVE', 'I',
    'IT', 'FOR', 'NOT', 'ON', 'WITH', 'HE', 'AS', 'YOU', 'DO', 'AT',
    'THIS', 'BUT', 'HIS', 'BY', 'FROM', 'THEY', 'WE', 'SAY', 'HER',
    'SHE', 'OR', 'AN', 'WILL', 'MY', 'ONE', 'ALL', 'WOULD', 'THERE',
    'THEIR', 'WHAT', 'SO', 'UP', 'OUT', 'IF', 'ABOUT', 'WHO', 'GET',
    'WHICH', 'GO', 'ME', 'WHEN', 'MAKE', 'CAN', 'LIKE', 'TIME', 'NO',
    'JUST', 'HIM', 'KNOW', 'TAKE', 'PEOPLE', 'INTO', 'YEAR', 'YOUR',
    'GOOD', 'SOME', 'COULD', 'THEM', 'SEE', 'OTHER', 'THAN', 'THEN',
    'NOW', 'LOOK', 'ONLY', 'COME', 'ITS', 'OVER', 'THINK', 'ALSO',
    'BACK', 'AFTER', 'USE', 'TWO', 'HOW', 'OUR', 'WORK', 'FIRST',
    'WELL', 'WAY', 'EVEN', 'NEW', 'WANT', 'BECAUSE', 'ANY', 'THESE',
    'GIVE', 'DAY', 'MOST', 'US', 'IS', 'WAS', 'ARE', 'WERE', 'BEEN',
    'HAS', 'HAD', 'HELLO', 'WORLD', 'YES', 'OK', 'AM',
})


def decrypt_shift(text: str, shift: int) -> str:
    """Decrypt `text` assuming a Caesar shift of `shift` (0-25).

    Non-alphabetic characters pass through untouched. Case is preserved.
    Decrypting with shift `s` shifts each letter back by `s` positions
    (modulo 26).
    """
    shift %= 26
    out: list[str] = []
    for ch in text:
        if 'A' <= ch <= 'Z':
            out.append(chr((ord(ch) - ord('A') - shift) % 26 + ord('A')))
        elif 'a' <= ch <= 'z':
            out.append(chr((ord(ch) - ord('a') - shift) % 26 + ord('a')))
        else:
            out.append(ch)
    return ''.join(out)


def encrypt_shift(text: str, shift: int) -> str:
    """Encrypt `text` with a Caesar shift of `shift`. Inverse of decrypt_shift."""
    return decrypt_shift(text, -shift)


def _chi_squared(text: str) -> float:
    """Raw chi-squared distance from English letter distribution.

    Lower is better. Non-letters are ignored. Empty input returns
    float('inf') so it sorts last.
    """
    letters = [c.upper() for c in text if c.isalpha()]
    n = len(letters)
    if n == 0:
        return float('inf')

    counts = Counter(letters)
    chi_sq = 0.0
    for letter in ALPHABET:
        observed = counts.get(letter, 0)
        # Expected count under the English distribution.
        # ENGLISH_FREQ is in percent (0-100), so divide by 100.
        expected = ENGLISH_FREQ[letter] / 100.0 * n
        # Standard chi-squared term. `expected` is always > 0 here
        # because every English-frequency entry is non-zero.
        chi_sq += (observed - expected) ** 2 / expected
    return chi_sq


def _word_hits(text: str) -> int:
    """Count tokens in `text` that appear in our common-word dictionary."""
    hits = 0
    # Split on any non-letter — punctuation and whitespace alike.
    token = []
    for ch in text:
        if ch.isalpha():
            token.append(ch.upper())
        else:
            if token:
                if ''.join(token) in COMMON_WORDS:
                    hits += 1
                token = []
    if token and ''.join(token) in COMMON_WORDS:
        hits += 1
    return hits


def english_score(text: str) -> float:
    """Score `text` for English-likelihood. Lower is better.

    Combines chi-squared distance from English letter frequencies with
    a strong bonus for common-word matches. The dictionary check
    rescues short messages like "Hello, World!" where chi-squared on
    10 letters is too noisy to pick a clear winner.

    Each common-word hit subtracts 25 points from the chi-squared
    score — typically enough to outrank near-matches without
    completely overriding the frequency signal on long texts.
    """
    chi_sq = _chi_squared(text)
    if chi_sq == float('inf'):
        return chi_sq
    bonus = _word_hits(text) * 25.0
    return chi_sq - bonus


def letter_overlap(a: str, b: str) -> float:
    """Fraction of positions where `a` and `b` agree on a letter (case-insensitive).

    Non-letter positions in `a` are skipped (they always match — both
    versions preserve punctuation). Returns a value in [0.0, 1.0].

    This powers the "diff vs ciphertext" twist: how much of the
    decrypted candidate still looks like the ciphertext? A correct
    decryption usually shares ~0% of letters with the ciphertext
    (every letter shifted), while shift=0 gives 100% overlap.
    """
    matches = 0
    total = 0
    for ca, cb in zip(a, b):
        if ca.isalpha():
            total += 1
            if ca.lower() == cb.lower():
                matches += 1
    if total == 0:
        return 0.0
    return matches / total


def crack(ciphertext: str) -> list[tuple[int, float, str]]:
    """Try every Caesar shift and rank candidates by English-likelihood.

    Returns a list of `(shift, score, plaintext)` tuples sorted
    best-first (lowest chi-squared score first). The list always has
    26 entries — one per possible shift.
    """
    candidates: list[tuple[int, float, str]] = []
    for shift in range(26):
        plaintext = decrypt_shift(ciphertext, shift)
        candidates.append((shift, english_score(plaintext), plaintext))
    candidates.sort(key=lambda row: row[1])
    return candidates


def format_table(candidates: Iterable[tuple[int, float, str]],
                 ciphertext: str = '',
                 width: int = 56) -> str:
    """Render a ranked candidate list as a plain-text table for the CLI."""
    rows = [
        f'{"#":>2}  {"shift":>5}  {"score":>9}  {"overlap":>7}  plaintext',
        '-' * (width + 24),
    ]
    for i, (shift, score, plaintext) in enumerate(candidates, start=1):
        overlap = letter_overlap(ciphertext, plaintext) if ciphertext else 0.0
        snippet = plaintext if len(plaintext) <= width else plaintext[:width - 1] + '…'
        rows.append(
            f'{i:>2}  {shift:>5}  {score:>9.2f}  '
            f'{overlap * 100:>6.1f}%  {snippet}'
        )
    return '\n'.join(rows)


def main() -> None:
    print('Caesar Hacker — brute-force every Caesar shift and rank by '
          'English-likelihood.')
    print('Paste the ciphertext below, then press Enter on a blank line.\n')

    # Read possibly-multiline input. Treat blank line as EOF.
    lines: list[str] = []
    try:
        while True:
            line = input()
            if line == '' and lines:
                break
            if line == '' and not lines:
                # Allow first blank line — but if the next is also blank, stop.
                continue
            lines.append(line)
    except EOFError:
        pass

    ciphertext = '\n'.join(lines).strip()
    if not ciphertext:
        print('No ciphertext provided. Exiting.')
        return

    candidates = crack(ciphertext)
    print()
    print(format_table(candidates, ciphertext=ciphertext))
    print()
    best_shift, best_score, best_plain = candidates[0]
    print(f'Best guess: shift={best_shift}  score={best_score:.2f}')
    print(f'Plaintext : {best_plain}')


if __name__ == '__main__':
    main()
