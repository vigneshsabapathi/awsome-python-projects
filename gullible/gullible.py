"""Gullible — CLI.

An interactive trick game: the program asks the user whether they are
gullible. Saying "yes" proves the point; saying anything *other* than a
clean "no" (or its multilingual equivalents) is treated as gullibility too.
Multiple question variants keep repeat-players on their toes.

Pure helpers:
    is_gullible_answer(text) -> bool   True = gullible (not a clean "no")

Shared class:
    Game     Core logic imported by the GUI and TUI.

Run:
    uv run python gullible/gullible.py
"""
from __future__ import annotations

import random
import re

# ---------------------------------------------------------------------------
# Question variants — the core trick
# ---------------------------------------------------------------------------
# Each entry carries:
#   prompt      — what the program asks
#   yes_reply   — printed when the user admits gullibility
#   loop_nudge  — printed on each "wrong" answer to keep them in the loop
#   yes_pattern — regex for a gullible ("yes-ish") answer
#   no_pattern  — regex for the one valid escape ("no-ish")
#
# Multilingual yes/no tokens are included for a bit of international hilarity.

VARIANTS: list[dict] = [
    {
        "prompt": (
            "Are you gullible?  (type yes or no)"
        ),
        "yes_reply": (
            "Ha! I knew you were gullible."
        ),
        "loop_nudge": (
            "Please type yes or no."
        ),
        "yes_pattern": r"^(yes|yeah|yep|yup|sure|oui|si|ja|da|hai)\s*[.!]*$",
        "no_pattern":  r"^(no|nope|nah|non|nein|nie|いいえ|não)\s*[.!]*$",
    },
    {
        "prompt": (
            "Are you the kind of person who always reads instructions "
            "carefully?  (yes / no)"
        ),
        "yes_reply": (
            "Interesting — a truly careful reader would have spotted "
            "this was a trick before answering."
        ),
        "loop_nudge": (
            "The instructions say to type yes or no.  Try again."
        ),
        "yes_pattern": r"^(yes|yeah|yep|yup|sure|absolutely|oui|si|ja|da|hai)\s*[.!]*$",
        "no_pattern":  r"^(no|nope|nah|non|nein|nie|không|não)\s*[.!]*$",
    },
    {
        "prompt": (
            "Do you always say yes when asked a question?  (yes or no)"
        ),
        "yes_reply": (
            "You just proved it."
        ),
        "loop_nudge": (
            "Only yes or no, please."
        ),
        "yes_pattern": r"^(yes|yeah|yep|sure|totally|oui|si|ja)\s*[.!]*$",
        "no_pattern":  r"^(no|nope|never|non|nein|nie)\s*[.!]*$",
    },
    {
        "prompt": (
            "Is it possible for you to answer this question with the "
            "word 'no'?  (yes / no)"
        ),
        "yes_reply": (
            "But you said yes — so it appears you cannot, or will not. "
            "Either way, gullibility confirmed."
        ),
        "loop_nudge": (
            "Please answer with yes or no."
        ),
        "yes_pattern": r"^(yes|yeah|yep|sure|oui|si|ja|da)\s*[.!]*$",
        "no_pattern":  r"^(no|nope|nah|non|nein)\s*[.!]*$",
    },
    {
        "prompt": (
            "This sentence is false. Do you believe it?  (yes or no)"
        ),
        "yes_reply": (
            "Classic. You walked straight into a liar's paradox — "
            "and believed it."
        ),
        "loop_nudge": (
            "Yes or no only, please."
        ),
        "yes_pattern": r"^(yes|yeah|yep|sure|oui|si|ja)\s*[.!]*$",
        "no_pattern":  r"^(no|nope|nah|non|nein)\s*[.!]*$",
    },
]


# ---------------------------------------------------------------------------
# Pure helper
# ---------------------------------------------------------------------------

def is_gullible_answer(text: str) -> bool:
    """Return True if *text* is NOT a clean 'no' answer (i.e. gullible).

    Uses the no_pattern of the first VARIANTS entry as the canonical
    definition of a clean escape.

    >>> is_gullible_answer('no')
    False
    >>> is_gullible_answer('maybe')
    True
    >>> is_gullible_answer('yes')
    True
    >>> is_gullible_answer('')
    True
    """
    no_pattern = re.compile(
        VARIANTS[0]["no_pattern"], re.IGNORECASE
    )
    return not bool(no_pattern.match(text.strip()))


# ---------------------------------------------------------------------------
# Game class
# ---------------------------------------------------------------------------

class Game:
    """Stateful gullibility engine.

    Attributes:
        variant     — the currently active question dict
        rounds      — total number of completed rounds (a round ends when
                      the player either escapes or admits gullibility)
        gullible_count — how many times the player was gullible
        rng         — random.Random instance (injectable for testing)
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.rounds: int = 0
        self.gullible_count: int = 0
        self.variant: dict = self.rng.choice(VARIANTS)

    def new_variant(self) -> None:
        """Pick a fresh question variant (used for each new round)."""
        self.variant = self.rng.choice(VARIANTS)

    def ask(self, response: str) -> dict:
        """Process one player response and return a result dict.

        Returns:
            {
              "prompt":   str,   the question that was shown
              "response": str,   the raw player input
              "verdict":  str,   "gullible" | "escaped" | "loop"
              "message":  str,   text to display to the player
            }

        Verdicts:
            "gullible"  — player matched the yes_pattern
            "escaped"   — player matched the no_pattern (wins!)
            "loop"      — player typed something else (keep asking)
        """
        v = self.variant
        raw = response.strip()

        yes_re = re.compile(v["yes_pattern"], re.IGNORECASE)
        no_re  = re.compile(v["no_pattern"],  re.IGNORECASE)

        if yes_re.match(raw):
            self.rounds += 1
            self.gullible_count += 1
            verdict = "gullible"
            message = v["yes_reply"]
        elif no_re.match(raw):
            self.rounds += 1
            verdict = "escaped"
            message = "Good — you resisted. You are not gullible... this time."
        else:
            verdict = "loop"
            message = v["loop_nudge"]

        return {
            "prompt":   v["prompt"],
            "response": response,
            "verdict":  verdict,
            "message":  message,
        }

    def state(self) -> dict:
        """Return a snapshot suitable for GUI/TUI status bars."""
        rate = (self.gullible_count / self.rounds) if self.rounds else 0.0
        return {
            "rounds":          self.rounds,
            "gullible_count":  self.gullible_count,
            "gullibility_rate": rate,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 52)
    print("  G U L L I B L E   —   A  T r i c k  G a m e")
    print("=" * 52)
    print("(Ctrl+C to quit at any time)\n")

    game = Game()
    playing = True

    while playing:
        game.new_variant()
        print(game.variant["prompt"])

        while True:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye!")
                return

            result = game.ask(raw)
            print(result["message"])

            if result["verdict"] in ("gullible", "escaped"):
                break

        s = game.state()
        gullible_str = "gullible" if s["gullible_count"] > 0 else "not gullible"
        print(
            f"\nRound {s['rounds']} done — "
            f"{s['gullible_count']}/{s['rounds']} times {gullible_str}.\n"
        )

        try:
            again = input("Play again? (yes/no) > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            return

        if again not in {"yes", "y", "yeah", "yep"}:
            playing = False

    s = game.state()
    print(
        f"\nFinal tally: gullible {s['gullible_count']}/{s['rounds']} "
        f"time(s)  ({s['gullibility_rate'] * 100:.0f}%)"
    )
    print("Thanks for playing!")


if __name__ == "__main__":
    main()
