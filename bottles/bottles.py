"""99 Bottles of Beer — CLI.

Prints the classic countdown song with grammatically correct verses.
Pure functions are exposed for the GUI/TUI front-ends.

Run:
    uv run python bottles/bottles.py                   # full song, 99 -> 0
    uv run python bottles/bottles.py --start 5         # short demo run
    uv run python bottles/bottles.py --remix           # niNety nniinE BoOttels
    uv run python bottles/bottles.py --start 3 --remix
"""
from __future__ import annotations

import argparse
import random
from typing import Callable

# --- Pluralization helpers ---------------------------------------------------
# The whole project is really about three edge cases:
#   n == 1 -> "1 bottle"            (singular)
#   n == 0 -> "no more bottles"     (special phrasing, not "0 bottles")
#   n >= 2 -> "<n> bottles"         (regular plural)


def _bottles_phrase(n: int) -> str:
    """Return the count phrase used inside a verse line.

    Mirrors the song's natural English: "no more bottles", "1 bottle",
    "<n> bottles". This is the only place the singular/plural rule lives.
    """
    if n <= 0:
        return "no more bottles"
    if n == 1:
        return "1 bottle"
    return f"{n} bottles"


def verse(n: int) -> str:
    """Return a single verse for ``n`` bottles remaining at the start.

    Handles the three classic transitions:
        n=2 -> "Take one down, pass it around, 1 bottle ..."
        n=1 -> "Take one down, pass it around, no more bottles ..."
        n=0 -> the wraparound restart verse (mentions 99 again).
    """
    if n < 0:
        raise ValueError("n must be non-negative")

    if n == 0:
        # Wraparound verse — the song's punchline.
        return (
            "No more bottles of beer on the wall, no more bottles of beer.\n"
            "Go to the store and buy some more, "
            "99 bottles of beer on the wall."
        )

    current = _bottles_phrase(n)
    next_count = _bottles_phrase(n - 1)
    return (
        f"{current.capitalize()} of beer on the wall, "
        f"{current} of beer.\n"
        f"Take one down, pass it around, "
        f"{next_count} of beer on the wall."
    )


def song(start: int = 99, *, include_wraparound: bool = True) -> str:
    """Return the full song from ``start`` bottles down to 0.

    By default the closing wraparound verse is included. Verses are
    separated by a blank line, matching how the song is traditionally
    notated.
    """
    if start < 0:
        raise ValueError("start must be non-negative")
    last = -1 if include_wraparound else 0
    verses = [verse(n) for n in range(start, last, -1)]
    return "\n\n".join(verses)


# --- Remix: niNety nniinE BoOttels -------------------------------------------
# Per-character random case. Spaces, digits, and punctuation pass through
# unchanged. Letters get a coin flip per character (book uses random.random()
# < 0.5 -> lower, else upper).


def remix_text(text: str, rng: random.Random | None = None) -> str:
    """Return ``text`` with each letter randomly upper- or lower-cased."""
    rng = rng or random.Random()
    out: list[str] = []
    for ch in text:
        if ch.isalpha():
            out.append(ch.lower() if rng.random() < 0.5 else ch.upper())
        else:
            out.append(ch)
    return "".join(out)


def remix_verse(n: int, rng: random.Random | None = None) -> str:
    """Verse with random-case applied to letters only."""
    return remix_text(verse(n), rng)


def remix_song(start: int = 99, rng: random.Random | None = None,
               *, include_wraparound: bool = True) -> str:
    """Full song with random-case applied to letters only."""
    return remix_text(song(start, include_wraparound=include_wraparound), rng)


# --- Convenience dispatch (used by GUI/TUI) ---------------------------------
def render_verse(n: int, *, remix: bool = False,
                 rng: random.Random | None = None) -> str:
    """One-stop API: classic verse, or its remix variant."""
    if remix:
        return remix_verse(n, rng)
    return verse(n)


def render_song(start: int = 99, *, remix: bool = False,
                rng: random.Random | None = None,
                include_wraparound: bool = True) -> str:
    """One-stop API: classic song, or its remix variant."""
    if remix:
        return remix_song(start, rng, include_wraparound=include_wraparound)
    return song(start, include_wraparound=include_wraparound)


# Convenience type for callers that want to pass a verse-builder around.
VerseBuilder = Callable[[int], str]


# --- CLI ---------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the classic '99 Bottles of Beer' song.",
    )
    parser.add_argument(
        "--start", type=int, default=99,
        help="starting bottle count (default: 99)",
    )
    parser.add_argument(
        "--remix", action="store_true",
        help="apply random per-letter casing (niNety nniinE BoOttels variant)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="seed for reproducible remix output",
    )
    parser.add_argument(
        "--no-wraparound", action="store_true",
        help="omit the 'go to the store' closing verse",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.start < 0:
        raise SystemExit("start must be non-negative")
    rng = random.Random(args.seed)
    text = render_song(
        start=args.start,
        remix=args.remix,
        rng=rng,
        include_wraparound=not args.no_wraparound,
    )
    print(text)


if __name__ == "__main__":
    main()
