"""Caesar Cipher — CLI.

Encrypts/decrypts text by shifting each letter N positions in the alphabet.
Case is preserved; non-letters pass through unchanged.

Run:
    uv run python caesar_cipher/caesar_cipher.py
"""
from __future__ import annotations

from collections import Counter

ALPHABET_SIZE = 26

# Frequency of letters in typical English text (Cornell, percent).
# Used to score brute-force candidates by Chi-squared distance.
ENGLISH_FREQ = {
    'a': 8.167, 'b': 1.492, 'c': 2.782, 'd': 4.253, 'e': 12.702,
    'f': 2.228, 'g': 2.015, 'h': 6.094, 'i': 6.966, 'j': 0.153,
    'k': 0.772, 'l': 4.025, 'm': 2.406, 'n': 6.749, 'o': 7.507,
    'p': 1.929, 'q': 0.095, 'r': 5.987, 's': 6.327, 't': 9.056,
    'u': 2.758, 'v': 0.978, 'w': 2.360, 'x': 0.150, 'y': 1.974,
    'z': 0.074,
}


def caesar_shift(text: str, shift: int) -> str:
    """Apply a Caesar shift of `shift` positions to `text`.

    Letters wrap around within their case. Anything non-alpha is unchanged.
    Negative shifts decrypt; shift % 26 == 0 is the identity.
    """
    s = shift % ALPHABET_SIZE
    if s == 0:
        return text
    out: list[str] = []
    for ch in text:
        if 'a' <= ch <= 'z':
            out.append(chr((ord(ch) - ord('a') + s) % ALPHABET_SIZE + ord('a')))
        elif 'A' <= ch <= 'Z':
            out.append(chr((ord(ch) - ord('A') + s) % ALPHABET_SIZE + ord('A')))
        else:
            out.append(ch)
    return ''.join(out)


def encrypt(text: str, shift: int) -> str:
    """Encrypt by shifting each letter forward by `shift` positions."""
    return caesar_shift(text, shift)


def decrypt(text: str, shift: int) -> str:
    """Decrypt by shifting each letter backward by `shift` positions."""
    return caesar_shift(text, -shift)


def english_score(text: str) -> float:
    """Return Chi-squared distance from English letter frequency.

    Lower = more English-like. Only A-Z letters contribute.
    """
    letters = [c.lower() for c in text if c.isalpha()]
    n = len(letters)
    if n == 0:
        return float('inf')
    counts = Counter(letters)
    chi2 = 0.0
    for letter, expected_pct in ENGLISH_FREQ.items():
        expected = expected_pct / 100.0 * n
        observed = counts.get(letter, 0)
        # Avoid division-by-zero for zero-expected; ENGLISH_FREQ has none.
        chi2 += (observed - expected) ** 2 / expected
    return chi2


def brute_force(ciphertext: str) -> list[tuple[int, str, float]]:
    """Try all 26 shifts; return [(shift, plaintext, score)] sorted by score.

    Best candidates (most English-like) come first.
    """
    results = []
    for k in range(ALPHABET_SIZE):
        plain = decrypt(ciphertext, k)
        results.append((k, plain, english_score(plain)))
    results.sort(key=lambda r: r[2])
    return results


def _prompt_int(prompt: str, lo: int = -25, hi: int = 25) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            n = int(raw)
        except ValueError:
            print(f'  not a number — try again')
            continue
        if not (lo <= n <= hi):
            print(f'  out of range [{lo}, {hi}] — try again')
            continue
        return n


def main() -> None:
    print('Caesar Cipher')
    print('=' * 40)
    print('Modes: (e)ncrypt  (d)ecrypt  (b)rute-force  (q)uit')
    while True:
        mode = input('\nMode [e/d/b/q]: ').strip().lower()
        if mode in ('q', 'quit', 'exit'):
            print('Bye.')
            return
        if mode not in ('e', 'd', 'b'):
            print('  pick one of e, d, b, q')
            continue

        text = input('Text: ')
        if mode == 'b':
            print('\nTop 5 most English-like decryptions:')
            for shift, plain, score in brute_force(text)[:5]:
                print(f'  shift={shift:>2}  chi2={score:7.2f}  {plain!r}')
            continue

        shift = _prompt_int('Shift [-25..25]: ')
        if mode == 'e':
            print('Cipher:', encrypt(text, shift))
        else:
            print('Plain :', decrypt(text, shift))


if __name__ == '__main__':
    main()
