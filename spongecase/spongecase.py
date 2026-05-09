"""sPoNgEcAsE — CLI.

Convert text to "SpongeBob mocking" alternating-case meme. Two ciphers
share the file:

* :func:`to_sponge` — probabilistic per-letter upper/lower toggle, biased
  to *flip* relative to the previous letter so adjacent same-case runs
  are rare. ``intensity`` controls how strong the flip-bias is.
* :func:`to_sponge_strict` — deterministic alternating case starting
  upper (`HeLlO wOrLd`).

Run:
    uv run python spongecase/spongecase.py
"""
from __future__ import annotations

import random

# Sponge emoji appended in "maximize ridicule" mode at intensity >= 0.9.
SPONGE_EMOJI = '\U0001f9fd'  # 🧽


# ---------------------------------------------------------------- encode

def to_sponge(text: str, intensity: float = 0.5,
              rng: random.Random | None = None) -> str:
    """Return ``text`` in mocking-spongebob alternating case.

    Each *letter* is independently set to upper- or lower-case with a
    probability biased toward *flipping* relative to the previous
    letter's case. ``intensity`` (clamped to ``[0.0, 1.0]``) controls
    how strong that flip-bias is:

    * ``0.0``  — letters are 50/50 upper/lower with no memory of the
      previous letter (chaotic but uncorrelated).
    * ``0.5``  — flip with 75 percent probability vs the previous letter.
    * ``1.0``  — flip with 100 percent probability — strict alternation,
      identical to :func:`to_sponge_strict` modulo the starting case
      which is chosen randomly here.

    Non-letters pass through unchanged and do not affect the alternating
    state — i.e. ``"ab cd"`` and ``"abcd"`` produce the same case
    pattern on the letters.

    At ``intensity >= 0.9`` a sponge emoji (🧽) is appended to the
    output as a "maximize ridicule" indicator.

    ``rng`` is a :class:`random.Random` for reproducible output; if
    ``None``, the module-level :mod:`random` is used.
    """
    if not text:
        return ''
    p = max(0.0, min(1.0, float(intensity)))
    r = rng if rng is not None else random

    # Probability that the current letter *flips* case vs the previous
    # letter. At p=0 the flip probability is 0.5 (memoryless coin flip),
    # at p=1 it's 1.0 (strict alternation). Linear interpolation.
    flip_prob = 0.5 + 0.5 * p

    out: list[str] = []
    prev_upper: bool | None = None
    for ch in text:
        if not ch.isalpha():
            out.append(ch)
            continue
        if prev_upper is None:
            # First letter: pure 50/50 coin flip.
            this_upper = r.random() < 0.5
        else:
            # Bias toward NOT matching the previous letter's case.
            flip = r.random() < flip_prob
            this_upper = (not prev_upper) if flip else prev_upper
        out.append(ch.upper() if this_upper else ch.lower())
        prev_upper = this_upper

    result = ''.join(out)
    if p >= 0.9:
        result += SPONGE_EMOJI
    return result


def to_sponge_strict(text: str) -> str:
    """Deterministic alternating case starting upper.

    Letters alternate ``UPPER, lower, UPPER, lower, ...`` regardless of
    the original case. Non-letters pass through unchanged and do not
    advance the alternation counter, so ``"hi there"`` becomes
    ``"Hi ThErE"`` rather than ``"Hi tHeRe"``.
    """
    if not text:
        return ''
    out: list[str] = []
    upper_next = True
    for ch in text:
        if not ch.isalpha():
            out.append(ch)
            continue
        out.append(ch.upper() if upper_next else ch.lower())
        upper_next = not upper_next
    return ''.join(out)


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
    print('sPoNgEcAsE')
    print('=' * 40)
    print('Modes: (r)andom  (s)trict  (q)uit')
    while True:
        mode = input('\nMode [r/s/q]: ').strip().lower()
        if mode in ('q', 'quit', 'exit'):
            print('Bye.')
            return
        if mode not in ('r', 's'):
            print('  pick one of r, s, q')
            continue

        text = input('Text: ')
        if mode == 'r':
            intensity = _prompt_float('Intensity [0.0..1.0]: ')
            print('Sponge:', to_sponge(text, intensity=intensity))
        else:
            print('Sponge:', to_sponge_strict(text))


if __name__ == '__main__':
    main()
