"""Hangman — a word-guessing game.

Inspired by the classic Hangman / Guillotine project from
"The Big Book of Small Python Projects" by Al Sweigart.
This is an original implementation: word lists and ASCII art
are written from scratch.

Run:
    uv run python hangman/hangman.py

Public API used by the GUI / TUI front-ends:
    pick_word(category=None) -> tuple[str, str]
    mask(word, guessed) -> str
    is_won(word, guessed) -> bool
    STAGES   — list of 7 ASCII frames (0 = empty gallows ... 6 = fully hanged)
    CATEGORIES — dict[str, list[str]]
    MAX_WRONG = 6
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Iterable

MAX_WRONG: int = 6


# --------------------------------------------------------------------------- #
# ASCII gallows — 7 frames, drawn by hand (no copies of Sweigart's art).      #
# Frame index = number of wrong guesses.                                      #
# --------------------------------------------------------------------------- #
STAGES: list[str] = [
    # 0 — empty gallows
    r"""
   _________
   |/      |
   |
   |
   |
   |
   |
  _|___
""".rstrip("\n"),
    # 1 — head
    r"""
   _________
   |/      |
   |      (_)
   |
   |
   |
   |
  _|___
""".rstrip("\n"),
    # 2 — torso
    r"""
   _________
   |/      |
   |      (_)
   |       |
   |       |
   |
   |
  _|___
""".rstrip("\n"),
    # 3 — one arm
    r"""
   _________
   |/      |
   |      (_)
   |      /|
   |       |
   |
   |
  _|___
""".rstrip("\n"),
    # 4 — both arms
    r"""
   _________
   |/      |
   |      (_)
   |      /|\
   |       |
   |
   |
  _|___
""".rstrip("\n"),
    # 5 — one leg
    r"""
   _________
   |/      |
   |      (_)
   |      /|\
   |       |
   |      /
   |
  _|___
""".rstrip("\n"),
    # 6 — both legs (game over)
    r"""
   _________
   |/      |
   |      (X)
   |      /|\
   |       |
   |      / \
   |
  _|___
""".rstrip("\n"),
]


# --------------------------------------------------------------------------- #
# Word lists — original lists, three categories, 12+ words each.              #
# All-uppercase letters only (the game is case-insensitive at the boundary).  #
# --------------------------------------------------------------------------- #
CATEGORIES: dict[str, list[str]] = {
    "animals": [
        "ELEPHANT", "GIRAFFE", "DOLPHIN", "PENGUIN", "OCTOPUS",
        "KANGAROO", "PLATYPUS", "HEDGEHOG", "FLAMINGO", "CHEETAH",
        "RACCOON", "PANTHER", "OTTER", "BADGER", "CHINCHILLA",
    ],
    "fruits": [
        "BANANA", "PINEAPPLE", "STRAWBERRY", "MANGO", "PAPAYA",
        "BLUEBERRY", "RASPBERRY", "PEACH", "APRICOT", "WATERMELON",
        "POMEGRANATE", "LYCHEE", "GRAPEFRUIT", "PASSIONFRUIT", "TANGERINE",
    ],
    "countries": [
        "PORTUGAL", "ICELAND", "MOROCCO", "VIETNAM", "ARGENTINA",
        "MONGOLIA", "BELGIUM", "FINLAND", "ETHIOPIA", "MALAYSIA",
        "SLOVAKIA", "URUGUAY", "TANZANIA", "GREECE", "JAMAICA",
    ],
}


# --------------------------------------------------------------------------- #
# Pure functions — kept side-effect-free so the GUI/TUI can reuse them.       #
# --------------------------------------------------------------------------- #
def pick_word(category: str | None = None,
              rng: random.Random | None = None) -> tuple[str, str]:
    """Return ``(category, word)``.

    If ``category`` is None, a random category is chosen. Words are stored
    upper-case; pass an injected :class:`random.Random` for deterministic tests.
    """
    rng = rng or random
    if category is None:
        category = rng.choice(list(CATEGORIES))
    if category not in CATEGORIES:
        raise ValueError(
            f"Unknown category {category!r}. "
            f"Choose from {sorted(CATEGORIES)}.")
    return category, rng.choice(CATEGORIES[category]).upper()


def mask(word: str, guessed: Iterable[str]) -> str:
    """Return ``word`` with un-guessed letters replaced by ``_``.

    Non-letters (spaces, hyphens) are always revealed.
    Comparison is case-insensitive.
    """
    guessed_set = {g.upper() for g in guessed}
    return "".join(
        c if (not c.isalpha() or c.upper() in guessed_set) else "_"
        for c in word
    )


def is_won(word: str, guessed: Iterable[str]) -> bool:
    """True when every alphabetic character in ``word`` has been guessed."""
    guessed_set = {g.upper() for g in guessed}
    return all(
        (not c.isalpha()) or c.upper() in guessed_set
        for c in word
    )


def is_lost(wrong_count: int) -> bool:
    """True when wrong guesses have reached :data:`MAX_WRONG`."""
    return wrong_count >= MAX_WRONG


def difficulty(word: str) -> str:
    """Heuristic difficulty rating used by the GUI/TUI hint strip.

    Combines length + unique-letter count + vowel ratio. Longer words with
    fewer unique letters are *easier* (more reveals per correct guess).
    """
    letters = [c for c in word.upper() if c.isalpha()]
    if not letters:
        return "Easy"
    unique = len(set(letters))
    score = unique - 0.3 * len(letters)
    if score <= 4:
        return "Easy"
    if score <= 6:
        return "Medium"
    return "Hard"


def letter_frequency(word: str) -> list[tuple[str, int]]:
    """Return per-letter counts (most common first). Useful for hint UIs."""
    return Counter(c for c in word.upper() if c.isalpha()).most_common()


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #
def _format_progress(word: str, guessed: set[str], wrong: list[str]) -> str:
    art = STAGES[min(len(wrong), MAX_WRONG)]
    lines = [
        art,
        "",
        f"Word:  {' '.join(mask(word, guessed))}",
        f"Wrong: {' '.join(wrong) if wrong else '(none)'}  "
        f"({len(wrong)}/{MAX_WRONG})",
        f"Used:  {' '.join(sorted(guessed)) if guessed else '(none)'}",
    ]
    return "\n".join(lines)


def _prompt_letter(guessed: set[str]) -> str:
    while True:
        raw = input("Guess a letter: ").strip().upper()
        if len(raw) != 1 or not raw.isalpha():
            print("  -> Enter a single A-Z letter.")
            continue
        if raw in guessed:
            print(f"  -> You already tried {raw!r}.")
            continue
        return raw


def main() -> None:
    print("HANGMAN — guess the word, one letter at a time.")
    print(f"Six wrong guesses and you're done.\n")

    while True:
        cats = list(CATEGORIES) + ["random"]
        print("Categories: " + ", ".join(cats))
        choice = input("Pick one (blank = random): ").strip().lower()
        category = None if choice in ("", "random") else choice
        try:
            cat, word = pick_word(category)
        except ValueError as exc:
            print(f"  -> {exc}\n")
            continue

        guessed: set[str] = set()
        wrong: list[str] = []
        print(f"\nCategory: {cat}  |  Difficulty: {difficulty(word)}\n")

        while True:
            print(_format_progress(word, guessed, wrong))
            if is_won(word, guessed):
                print(f"\nYou won! The word was {word}.\n")
                break
            if is_lost(len(wrong)):
                print(f"\nYou lost. The word was {word}.\n")
                break
            letter = _prompt_letter(guessed)
            guessed.add(letter)
            if letter in word.upper():
                print(f"  -> {letter} is in the word.\n")
            else:
                wrong.append(letter)
                print(f"  -> {letter} is not in the word.\n")

        again = input("Play again? (y/n): ").strip().lower()
        if not again.startswith("y"):
            break

    print("Thanks for playing.")


if __name__ == "__main__":
    main()
