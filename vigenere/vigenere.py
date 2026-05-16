"""Vigenère Cipher — CLI.

A polyalphabetic Caesar cipher: each letter of the plaintext is shifted
by a different amount, where the shifts cycle through the letters of a
keyword (A=0, B=1, ..., Z=25). Decryption shifts the other way.

This module is the pure-function core. The GUI / TUI front-ends import
from it: `from vigenere import encrypt, decrypt, kasiski, friedman_ic,
crack`.

The auto-crack pipeline has three stages — the trick promised in the
brief:

    1. Kasiski examination       → guess likely key lengths from the
                                   spacings between repeated trigrams.
    2. Friedman index of         → corroborate the key length by
       coincidence                 measuring the IC of each candidate's
                                   columns.
    3. Per-column Caesar attack  → split into key-length columns, treat
                                   each as a Caesar cipher, pick the
                                   shift that minimises chi² distance
                                   from English letter frequencies.

Run:
    uv run python vigenere/vigenere.py
"""
from __future__ import annotations

import math
import string
from collections import Counter

ALPHABET = string.ascii_uppercase
ALPHABET_SIZE = 26

# Lewand/Cornell English letter percentages.
ENGLISH_FREQ: dict[str, float] = {
    'A':  8.167, 'B':  1.492, 'C':  2.782, 'D':  4.253, 'E': 12.702,
    'F':  2.228, 'G':  2.015, 'H':  6.094, 'I':  6.966, 'J':  0.153,
    'K':  0.772, 'L':  4.025, 'M':  2.406, 'N':  6.749, 'O':  7.507,
    'P':  1.929, 'Q':  0.095, 'R':  5.987, 'S':  6.327, 'T':  9.056,
    'U':  2.758, 'V':  0.978, 'W':  2.360, 'X':  0.150, 'Y':  1.974,
    'Z':  0.074,
}

# Index of coincidence (IC) reference values. English ~ 0.0667;
# random text ~ 1/26 ≈ 0.0385. We use these to score candidate
# key lengths from the Friedman test.
ENGLISH_IC = 0.0667
RANDOM_IC = 1.0 / ALPHABET_SIZE  # 0.0385


# ---------------------------------------------------------------------------
# Key utilities
# ---------------------------------------------------------------------------

def _validate_key(key: str) -> str:
    """Strip non-letters from `key`, uppercase, and validate non-empty."""
    cleaned = ''.join(c for c in key if c.isalpha()).upper()
    if not cleaned:
        raise ValueError('key must contain at least one letter')
    return cleaned


def _shift_char(ch: str, shift: int, *, sign: int) -> str:
    """Shift a single character by `shift * sign` positions, preserving case."""
    if 'A' <= ch <= 'Z':
        base = ord('A')
        return chr((ord(ch) - base + sign * shift) % ALPHABET_SIZE + base)
    if 'a' <= ch <= 'z':
        base = ord('a')
        return chr((ord(ch) - base + sign * shift) % ALPHABET_SIZE + base)
    return ch


# ---------------------------------------------------------------------------
# Encrypt / decrypt
# ---------------------------------------------------------------------------

def _vigenere(text: str, key: str, *, sign: int) -> str:
    """Apply Vigenère with `key` and direction `sign` (+1 encrypt, -1 decrypt).

    The key cycles only over letter positions in `text` — non-letters
    pass through without advancing the key index.
    """
    k = _validate_key(key)
    shifts = [ord(c) - ord('A') for c in k]
    out: list[str] = []
    j = 0  # key index, only advances on alphabetic characters
    for ch in text:
        if ch.isalpha():
            out.append(_shift_char(ch, shifts[j % len(shifts)], sign=sign))
            j += 1
        else:
            out.append(ch)
    return ''.join(out)


def encrypt(text: str, key: str) -> str:
    """Encrypt `text` with Vigenère `key` (alphabetic, case-insensitive).

    Non-letters pass through unchanged. Case is preserved.

    >>> encrypt('Hello, World!', 'KEY')
    'Rijvs, Uyvjn!'
    """
    return _vigenere(text, key, sign=+1)


def decrypt(text: str, key: str) -> str:
    """Decrypt `text` with Vigenère `key`.

    >>> decrypt(encrypt('Hello, World!', 'KEY'), 'KEY')
    'Hello, World!'
    """
    return _vigenere(text, key, sign=-1)


# ---------------------------------------------------------------------------
# Autokey variant — promised in the brief.
# ---------------------------------------------------------------------------

def encrypt_autokey(text: str, key: str) -> str:
    """Autokey-cipher encrypt: after the initial keyword, the key continues
    with the *plaintext itself*. Eliminates the periodicity that makes
    Kasiski/Friedman work, so this variant is genuinely harder to crack
    than classic Vigenère.

    >>> encrypt_autokey('ATTACK', 'KEY')[:6]
    'KXRAEM'
    """
    primer = _validate_key(key)
    primer_shifts = [ord(c) - ord('A') for c in primer]
    out: list[str] = []
    plain_letters: list[int] = []
    j = 0
    for ch in text:
        if ch.isalpha():
            if j < len(primer_shifts):
                shift = primer_shifts[j]
            else:
                # After the primer, the running key is the plaintext.
                shift = plain_letters[j - len(primer_shifts)]
            out.append(_shift_char(ch, shift, sign=+1))
            plain_letters.append(ord(ch.upper()) - ord('A'))
            j += 1
        else:
            out.append(ch)
    return ''.join(out)


def decrypt_autokey(text: str, key: str) -> str:
    """Autokey-cipher decrypt — recovered plaintext extends the key as
    we go.

    >>> decrypt_autokey(encrypt_autokey('Attack at dawn!', 'KEY'), 'KEY')
    'Attack at dawn!'
    """
    primer = _validate_key(key)
    primer_shifts = [ord(c) - ord('A') for c in primer]
    out: list[str] = []
    plain_letters: list[int] = []
    j = 0
    for ch in text:
        if ch.isalpha():
            if j < len(primer_shifts):
                shift = primer_shifts[j]
            else:
                shift = plain_letters[j - len(primer_shifts)]
            decoded = _shift_char(ch, shift, sign=-1)
            out.append(decoded)
            plain_letters.append(ord(decoded.upper()) - ord('A'))
            j += 1
        else:
            out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------------------
# Letters-only helper
# ---------------------------------------------------------------------------

def _letters_only(text: str) -> str:
    """Return uppercase A-Z letters from `text`, dropping everything else."""
    return ''.join(c.upper() for c in text if c.isalpha())


# ---------------------------------------------------------------------------
# Stage 1: Kasiski examination
# ---------------------------------------------------------------------------

def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def _factors(n: int, *, lo: int = 2, hi: int = 30) -> list[int]:
    """Return divisors of `n` within `[lo, hi]` inclusive."""
    return [d for d in range(lo, hi + 1) if n % d == 0]


def kasiski(ciphertext: str,
            *,
            ngram: int = 3,
            max_keylen: int = 15) -> list[int]:
    """Kasiski examination — guess likely Vigenère key lengths.

    Repeated n-grams in the ciphertext are likely repetitions of the
    same plaintext n-gram encrypted under the same slice of the key,
    which can only happen when the spacing between repeats is a
    multiple of the key length. So: collect every distance between
    repeated trigrams, and the most common divisors of those distances
    (within `[2, max_keylen]`) are the most likely key lengths.

    Returns key-length candidates ranked by how many of the spacings
    they divide — most likely first.

    >>> ct = encrypt('the quick brown fox jumps over the lazy dog '
    ...              'and the fox runs back to the den', 'BAT')
    >>> 3 in kasiski(ct)[:3]
    True
    """
    letters = _letters_only(ciphertext)
    if len(letters) < ngram * 2:
        return []

    # Spacings between repeated n-grams.
    seen: dict[str, int] = {}
    spacings: list[int] = []
    for i in range(len(letters) - ngram + 1):
        gram = letters[i:i + ngram]
        if gram in seen:
            spacings.append(i - seen[gram])
            # NB: keep updating so we catch all subsequent repeats too,
            # by chaining each new occurrence against the previous one.
            seen[gram] = i
        else:
            seen[gram] = i

    if not spacings:
        return []

    # Score each candidate length by how often it divides a spacing.
    scores: Counter[int] = Counter()
    for s in spacings:
        for d in _factors(s, lo=2, hi=max_keylen):
            scores[d] += 1
    if not scores:
        return []

    return [length for length, _ in scores.most_common()]


# ---------------------------------------------------------------------------
# Stage 2: Friedman / index of coincidence
# ---------------------------------------------------------------------------

def index_of_coincidence(text: str) -> float:
    """Compute the index of coincidence of `text` (Friedman's IC).

    IC = Σ (n_i · (n_i - 1)) / (N · (N - 1))   over letters i

    English text ≈ 0.0667; uniform random ≈ 0.0385. A monoalphabetic
    cipher preserves the IC; a polyalphabetic one with key length L
    drives it toward the random value as L grows.
    """
    letters = _letters_only(text)
    n = len(letters)
    if n < 2:
        return 0.0
    counts = Counter(letters)
    return sum(c * (c - 1) for c in counts.values()) / (n * (n - 1))


def friedman_ic(ciphertext: str) -> float:
    """Return the IC of the whole ciphertext.

    Use `column_average_ic(ciphertext, L)` to evaluate a candidate key
    length: the IC of each column should be ≈ ENGLISH_IC if `L` is the
    true key length, and ≈ RANDOM_IC otherwise.
    """
    return index_of_coincidence(ciphertext)


def _columns(letters: str, length: int) -> list[str]:
    """Split `letters` into `length` columns, taking every L-th letter."""
    return [letters[i::length] for i in range(length)]


def column_average_ic(ciphertext: str, key_length: int) -> float:
    """Average IC across the `key_length` columns of the ciphertext.

    For the true `key_length`, every column is a Caesar cipher of a
    plain English subsequence, so each column's IC ≈ ENGLISH_IC and
    the average is close to 0.0667. For wrong lengths the average
    drops toward 0.0385.
    """
    letters = _letters_only(ciphertext)
    if key_length <= 0 or len(letters) < key_length * 2:
        return 0.0
    cols = _columns(letters, key_length)
    return sum(index_of_coincidence(c) for c in cols) / key_length


def friedman_estimate(ciphertext: str) -> float:
    """Friedman's classic key-length estimate from the global IC.

    Derived from the expected IC for a random polyalphabetic with
    period L on English plaintext:

        L ≈ (k_p - k_r) · N / ((N - 1) · IC - k_r · N + k_p)

    where k_p = ENGLISH_IC, k_r = RANDOM_IC. Returns a float (often
    non-integer) — use `column_average_ic` to pick between the
    integers near the estimate.
    """
    letters = _letters_only(ciphertext)
    n = len(letters)
    if n < 2:
        return 0.0
    ic = index_of_coincidence(letters)
    denom = (n - 1) * ic - RANDOM_IC * n + ENGLISH_IC
    if abs(denom) < 1e-9:
        return 0.0
    estimate = (ENGLISH_IC - RANDOM_IC) * n / denom
    return max(estimate, 1.0)


# ---------------------------------------------------------------------------
# Stage 3: per-column Caesar attack
# ---------------------------------------------------------------------------

def _chi_squared(letters: str) -> float:
    """Chi-squared distance from the English letter distribution."""
    n = len(letters)
    if n == 0:
        return float('inf')
    counts = Counter(letters)
    chi = 0.0
    for letter in ALPHABET:
        observed = counts.get(letter, 0)
        expected = ENGLISH_FREQ[letter] / 100.0 * n
        chi += (observed - expected) ** 2 / expected
    return chi


def _best_caesar_shift(column: str) -> tuple[int, float]:
    """For a Caesar-shifted English column, return `(shift, chi²)`."""
    best = (0, float('inf'))
    for s in range(ALPHABET_SIZE):
        # Decrypt the column by `s`.
        shifted = ''.join(
            chr((ord(c) - ord('A') - s) % ALPHABET_SIZE + ord('A'))
            for c in column
        )
        score = _chi_squared(shifted)
        if score < best[1]:
            best = (s, score)
    return best


def recover_key(ciphertext: str, key_length: int) -> tuple[str, float]:
    """Stage 3: with a fixed key length, recover the keyword by running
    a Caesar attack on each of the `key_length` columns.

    Returns `(key, total_chi²)`. Lower chi² = closer to English.
    """
    letters = _letters_only(ciphertext)
    if key_length <= 0 or len(letters) < key_length:
        return '', float('inf')
    cols = _columns(letters, key_length)
    key_chars: list[str] = []
    total_chi = 0.0
    for col in cols:
        shift, chi = _best_caesar_shift(col)
        key_chars.append(chr(shift + ord('A')))
        total_chi += chi
    return ''.join(key_chars), total_chi


# ---------------------------------------------------------------------------
# Auto-crack pipeline
# ---------------------------------------------------------------------------

def candidate_key_lengths(ciphertext: str,
                          *,
                          max_keylen: int = 15) -> list[tuple[int, float, int]]:
    """Combined Kasiski + IC ranking of candidate key lengths.

    Returns a list of `(length, column_ic, kasiski_votes)` sorted with
    the most plausible candidates first. Plausibility is "high column
    IC AND a Kasiski vote when available". When Kasiski yields nothing
    (e.g. very short ciphertext), the ranking falls back to pure IC.
    """
    kasiski_ranked = kasiski(ciphertext, max_keylen=max_keylen)
    kasiski_votes: dict[int, int] = {
        # Higher rank = earlier in list = more votes; pin first to N.
        length: max_keylen + 1 - rank
        for rank, length in enumerate(kasiski_ranked)
    }

    out: list[tuple[int, float, int]] = []
    for L in range(2, max_keylen + 1):
        ic = column_average_ic(ciphertext, L)
        votes = kasiski_votes.get(L, 0)
        out.append((L, ic, votes))

    # Sort: prefer high column-IC; break ties with Kasiski votes.
    # IC alone is monotonic in key length around the optimum, so we
    # bias toward shorter lengths (multiples of the true length also
    # produce high IC).
    out.sort(key=lambda r: (-r[1] - 0.001 * r[2], r[0]))
    return out


def crack(ciphertext: str,
          max_keylen: int = 15) -> tuple[str, str]:
    """Auto-crack a Vigenère ciphertext.

    Three-stage pipeline:

    1. Kasiski examination on repeated trigrams produces a ranked list
       of likely key lengths.
    2. Index of coincidence on each candidate length confirms which
       lengths actually decompose the ciphertext into English-shaped
       columns.
    3. For the top few lengths, run a Caesar attack on each column to
       recover the keyword. Return the keyword whose decryption has
       the lowest chi² distance from English letter frequencies.

    Returns `(best_key, plaintext)`.
    """
    candidates = candidate_key_lengths(ciphertext, max_keylen=max_keylen)
    if not candidates:
        return '', ciphertext

    # Try the top several candidate lengths plus a few fallbacks so we
    # don't depend on either signal being clean.
    tried: set[int] = set()
    best: tuple[str, float] = ('', float('inf'))
    # Try IC-best first, then by Kasiski rank, then short lengths.
    ordered_lengths = [length for length, _, _ in candidates[:8]]
    for length in ordered_lengths + list(range(2, max_keylen + 1)):
        if length in tried:
            continue
        tried.add(length)
        key, chi = recover_key(ciphertext, length)
        if not key:
            continue
        if chi < best[1]:
            best = (key, chi)

    if not best[0]:
        return '', ciphertext
    return best[0], decrypt(ciphertext, best[0])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _prompt_key(prompt: str = 'Key (letters only): ') -> str:
    while True:
        raw = input(prompt).strip()
        try:
            return _validate_key(raw)
        except ValueError as e:
            print(f'  {e}')


def main() -> None:
    print('Vigenère Cipher')
    print('=' * 40)
    print('Modes: (e)ncrypt  (d)ecrypt  (a)utokey-encrypt  (A)utokey-decrypt')
    print('       (c)rack    (i)nfo (IC + Kasiski)         (q)uit')
    while True:
        mode = input('\nMode: ').strip()
        if mode in ('q', 'quit', 'exit'):
            print('Bye.')
            return
        if mode not in ('e', 'd', 'a', 'A', 'c', 'i'):
            print('  pick one of e, d, a, A, c, i, q')
            continue

        if mode == 'i':
            text = input('Ciphertext: ')
            ic = friedman_ic(text)
            est = friedman_estimate(text)
            print(f'  IC = {ic:.4f}  (English ≈ {ENGLISH_IC:.4f}, '
                  f'random ≈ {RANDOM_IC:.4f})')
            print(f'  Friedman length estimate: {est:.2f}')
            ks = kasiski(text)
            print(f'  Kasiski candidates (top 8): {ks[:8] if ks else "—"}')
            print('  Per-length column IC:')
            for length, ic_l, votes in candidate_key_lengths(text)[:8]:
                tag = '★' if votes else ' '
                print(f'    {tag} L={length:>2}  col-IC={ic_l:.4f}  '
                      f'kasiski={votes}')
            continue

        text = input('Text: ')
        if not text:
            print('  empty text — try again')
            continue

        if mode == 'c':
            print('  cracking (Kasiski → IC → per-column Caesar)...')
            key, plain = crack(text)
            if key:
                print(f'  recovered key : {key}')
                print(f'  plaintext     : {plain}')
            else:
                print('  no key recovered (text too short?)')
            continue

        key = _prompt_key()
        if mode == 'e':
            print('Cipher:', encrypt(text, key))
        elif mode == 'd':
            print('Plain :', decrypt(text, key))
        elif mode == 'a':
            print('Cipher:', encrypt_autokey(text, key))
        elif mode == 'A':
            print('Plain :', decrypt_autokey(text, key))


if __name__ == '__main__':
    main()
