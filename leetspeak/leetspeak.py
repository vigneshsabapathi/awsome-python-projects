"""Leetspeak — CLI.

Convert ordinary text to leet/1337 by probabilistic letter substitution.
At intensity=1.0 every letter that has a leet form is substituted; at 0.0
nothing is. Multi-character digraphs (e.g. ``at`` -> ``@``) get a small
chance to apply too, on top of the per-letter pass.

Run:
    uv run python leetspeak/leetspeak.py
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Iterable

# ---------------------------------------------------------------- mappings

# Per-letter leet substitutions. First entry is the "canonical" leet form
# used by from_leet for reverse mapping. Lower- and upper-case are folded.
LEET_MAP: dict[str, list[str]] = {
    'a': ['4', '@', '/-\\'],
    'b': ['8', '6'],
    'c': ['(', '<', '{'],
    'd': ['|)', '[)'],
    'e': ['3'],
    'f': ['|=', 'ph'],
    'g': ['9', '6'],
    'h': ['#', '|-|'],
    'i': ['1', '!', '|'],
    'j': ['_|'],
    'k': ['|<'],
    'l': ['1', '|', '|_'],
    'm': ['|\\/|', '/\\/\\'],
    'n': ['|\\|', '/\\/'],
    'o': ['0'],
    'p': ['|*', '|D'],
    'q': ['9', '0_'],
    'r': ['|2', '12'],
    's': ['5', '$', 'z'],
    't': ['7', '+'],
    'u': ['|_|', 'v'],
    'v': ['\\/'],
    'w': ['\\/\\/', 'vv'],
    'x': ['><', '%'],
    'y': ['`/'],
    'z': ['2', '7_'],
}

# Multi-character substitutions (digraphs/words). Applied with a lower
# probability than single-letter swaps for a more "casual leet" feel.
MULTI_MAP: dict[str, list[str]] = {
    'at': ['@'],
    'and': ['&', '&&'],
    'ate': ['8'],
    'cks': ['x'],
    'ph': ['f'],
    'you': ['u', 'j00'],
    'oo': ['00'],
    'ee': ['33'],
}

# Reverse-mapping table for from_leet. Built once; longest keys first so
# multi-char leet tokens (`|\\/|` -> m) win over single chars.
def _build_reverse() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for letter, forms in LEET_MAP.items():
        for form in forms:
            pairs.append((form, letter))
    # Sort by length descending so we prefer longer matches.
    pairs.sort(key=lambda kv: -len(kv[0]))
    return pairs


_REVERSE: list[tuple[str, str]] = _build_reverse()


# ------------------------------------------------------------------ encode

def to_leet(text: str, intensity: float = 0.5,
            rng: random.Random | None = None) -> str:
    """Return ``text`` with each letter swapped for a leet form with
    probability ``intensity``.

    ``intensity`` is clamped to [0.0, 1.0]. ``rng`` is a ``random.Random``
    for reproducible output; if ``None``, the module ``random`` is used.

    A small multi-character pass runs first (`at` -> `@`, etc.) at one
    quarter of ``intensity`` so the casual-leet feel doesn't dominate.
    Case is folded for lookups but the original letter case is preserved
    when no substitution fires.
    """
    if not text:
        return ''
    p = max(0.0, min(1.0, float(intensity)))
    r = rng if rng is not None else random

    # 1) multi-character pass (sorted longest-first so 'and' beats 'a').
    keys = sorted(MULTI_MAP.keys(), key=len, reverse=True)
    multi_p = p * 0.25
    out: list[str] = []
    i = 0
    while i < len(text):
        matched = False
        if multi_p > 0.0:
            for k in keys:
                if i + len(k) <= len(text) and text[i:i + len(k)].lower() == k:
                    if r.random() < multi_p:
                        choice = r.choice(MULTI_MAP[k])
                        out.append(choice)
                        i += len(k)
                        matched = True
                        break
        if matched:
            continue
        out.append(text[i])
        i += 1

    # 2) single-letter pass over the partially-substituted string.
    final: list[str] = []
    for ch in ''.join(out):
        low = ch.lower()
        if low in LEET_MAP and r.random() < p:
            final.append(r.choice(LEET_MAP[low]))
        else:
            final.append(ch)
    return ''.join(final)


# ------------------------------------------------------------------ decode

def from_leet(text: str) -> str:
    """Best-effort reverse of :func:`to_leet`.

    Greedy longest-match against every known leet token. Ambiguous tokens
    pick the first letter registered (e.g. ``1`` -> ``i`` since 'i' comes
    before 'l' in :data:`LEET_MAP`'s natural iteration). Tokens that
    don't appear in any leet form pass through unchanged.
    """
    if not text:
        return ''
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        replaced = False
        for token, letter in _REVERSE:
            if text.startswith(token, i):
                out.append(letter)
                i += len(token)
                replaced = True
                break
        if not replaced:
            out.append(text[i])
            i += 1
    return ''.join(out)


# ------------------------------------------------------------------- score

# Frequency of letters in typical English text (Cornell, percent).
ENGLISH_FREQ = {
    'a': 8.167, 'b': 1.492, 'c': 2.782, 'd': 4.253, 'e': 12.702,
    'f': 2.228, 'g': 2.015, 'h': 6.094, 'i': 6.966, 'j': 0.153,
    'k': 0.772, 'l': 4.025, 'm': 2.406, 'n': 6.749, 'o': 7.507,
    'p': 1.929, 'q': 0.095, 'r': 5.987, 's': 6.327, 't': 9.056,
    'u': 2.758, 'v': 0.978, 'w': 2.360, 'x': 0.150, 'y': 1.974,
    'z': 0.074,
}


def english_score(text: str) -> float:
    """Chi-squared distance from English letter frequency.

    Lower = more English-like. Used by :func:`brute_decode` to rank
    candidate decodings.
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
        chi2 += (observed - expected) ** 2 / expected
    return chi2


# ------------------------------------------------------------- brute force

# A handful of common leet preferences. Each candidate maps a leet token to
# a single letter, evaluated greedily (longest first). The first candidate
# is "no decoding" so we always have a baseline to compare against.
_BRUTE_PROFILES: list[dict[str, str]] = [
    # 1. identity (no change) — baseline
    {},
    # 2. canonical: digits -> letters
    {'4': 'a', '8': 'b', '3': 'e', '1': 'i', '0': 'o', '5': 's', '7': 't',
     '2': 'z', '9': 'g', '@': 'a', '$': 's', '!': 'i'},
    # 3. l-favoring: '1' -> 'l', '|' -> 'l'
    {'4': 'a', '8': 'b', '3': 'e', '1': 'l', '|': 'l', '0': 'o', '5': 's',
     '7': 't', '2': 'z', '@': 'a', '$': 's', '!': 'i'},
    # 4. punctuation-leet: '@' -> 'a', '#' -> 'h'
    {'@': 'a', '#': 'h', '$': 's', '!': 'i', '4': 'a', '3': 'e', '1': 'i',
     '0': 'o', '5': 's', '7': 't'},
    # 5. full from_leet (uses the global reverse table)
    None,  # type: ignore[list-item]
]


def _apply_profile(text: str, profile: dict[str, str]) -> str:
    if not profile:
        return text
    out: list[str] = []
    keys = sorted(profile.keys(), key=len, reverse=True)
    i = 0
    n = len(text)
    while i < n:
        replaced = False
        for k in keys:
            if text.startswith(k, i):
                out.append(profile[k])
                i += len(k)
                replaced = True
                break
        if not replaced:
            out.append(text[i])
            i += 1
    return ''.join(out)


def brute_decode(text: str) -> list[tuple[str, str, float]]:
    """Try a handful of common leet patterns; return ``(label, plain,
    score)`` tuples sorted by English-likelihood (lowest score first).

    The returned list always includes the identity (no decoding) so you
    can see whether the input was already English-ish.
    """
    labels = [
        'identity (no decode)',
        'digits -> letters',
        '1 = l (l-favoring)',
        'punctuation only',
        'full from_leet (greedy longest-match)',
    ]
    results: list[tuple[str, str, float]] = []
    for label, profile in zip(labels, _BRUTE_PROFILES):
        if profile is None:
            plain = from_leet(text)
        else:
            plain = _apply_profile(text, profile)
        results.append((label, plain, english_score(plain)))
    results.sort(key=lambda r: r[2])
    return results


# ---------------------------------------------------------------- CLI glue

def _prompt_float(prompt: str, lo: float = 0.0, hi: float = 1.0) -> float:
    while True:
        raw = input(prompt).strip()
        try:
            v = float(raw)
        except ValueError:
            print('  not a number — try again')
            continue
        if not (lo <= v <= hi):
            print(f'  out of range [{lo}, {hi}] — try again')
            continue
        return v


def main() -> None:
    print('Leetspeak')
    print('=' * 40)
    print('Modes: (e)ncode  (d)ecode  (b)rute-decode  (q)uit')
    while True:
        mode = input('\nMode [e/d/b/q]: ').strip().lower()
        if mode in ('q', 'quit', 'exit'):
            print('Bye.')
            return
        if mode not in ('e', 'd', 'b'):
            print('  pick one of e, d, b, q')
            continue

        text = input('Text: ')
        if mode == 'e':
            intensity = _prompt_float('Intensity [0.0..1.0]: ')
            print('Leet  :', to_leet(text, intensity=intensity))
        elif mode == 'd':
            print('Plain :', from_leet(text))
        else:
            print('\nDecoder candidates ranked by English-likelihood:')
            for label, plain, score in brute_decode(text):
                preview = plain if len(plain) <= 60 else plain[:57] + '...'
                print(f'  chi2={score:7.2f}  [{label}]  {preview!r}')


if __name__ == '__main__':
    main()
