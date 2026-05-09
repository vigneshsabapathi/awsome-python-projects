"""Evil Hangman — adversarial variant of the classic game.

The "computer" never commits to a single secret word. Instead it keeps a
*candidate set* of words consistent with every clue revealed so far.

When the player guesses a letter L, we partition the candidate set by the
mask pattern produced by L (e.g. ``__L___`` vs ``L_L___`` vs ``______``).
The adversary then picks the *largest* equivalence class — the one that
forces the player to reveal the **fewest** letters — and uses it as the new
candidate set. The "Bagels"-style class (no L anywhere) is preferred on ties
because it costs the player a wrong guess.

The actual secret word is only fixed once the candidate set shrinks to one,
or when the game ends.

This module is imported by the GUI/TUI to power the optional 'Evil mode'.
"""
from __future__ import annotations

import random
from collections import defaultdict
from typing import Iterable

from hangman import CATEGORIES, mask


class EvilHangman:
    """Adversarial Hangman engine.

    Parameters
    ----------
    category:
        Name of a key in :data:`hangman.CATEGORIES`, or ``None`` for random.
    rng:
        Optional :class:`random.Random` instance for deterministic tests.
    """

    def __init__(self,
                 category: str | None = None,
                 rng: random.Random | None = None) -> None:
        self._rng = rng or random
        if category is None:
            category = self._rng.choice(list(CATEGORIES))
        if category not in CATEGORIES:
            raise ValueError(f"Unknown category {category!r}")
        self.category = category

        # Group by length first; pick a length, then keep all words of that
        # length as the initial candidate set.
        by_length: dict[int, list[str]] = defaultdict(list)
        for w in CATEGORIES[category]:
            by_length[len(w)].append(w.upper())
        # Bias toward lengths that have several candidates so the adversary
        # actually has options.
        weighted_lengths = [L for L, ws in by_length.items() for _ in ws]
        chosen_len = self._rng.choice(weighted_lengths)
        self._candidates: list[str] = list(by_length[chosen_len])
        self._guessed: set[str] = set()

    # --------------------------------------------------------------- API --
    def peek_word(self) -> str:
        """Current 'public' word — any candidate works since they share the same mask.

        The GUI uses this for length and to render the masked tiles. The
        actual identity is irrelevant until commit.
        """
        return self._candidates[0]

    def guess(self, letter: str) -> bool:
        """Process a guess and return True if at least one position is revealed."""
        letter = letter.upper()
        if letter in self._guessed:
            return any(letter in w for w in self._candidates)
        self._guessed.add(letter)

        # Partition candidates by their mask pattern under the new guess set.
        groups: dict[str, list[str]] = defaultdict(list)
        for word in self._candidates:
            groups[mask(word, self._guessed)].append(word)

        # Choose the group that minimizes information leaked to the player:
        # 1. Largest group wins.
        # 2. Tie-break: the pattern with the fewest occurrences of `letter`
        #    (zero-letter "miss" group is best, costs a wrong guess).
        def score(item: tuple[str, list[str]]) -> tuple[int, int]:
            pattern, words = item
            return (len(words), -pattern.count(letter))

        best_pattern, best_words = max(groups.items(), key=score)
        self._candidates = best_words
        return letter in best_pattern

    def commit(self) -> str:
        """Pick a final secret word from the surviving candidate set."""
        return self._rng.choice(self._candidates)

    # -------------------------------------------------------- introspection
    @property
    def candidates(self) -> list[str]:
        return list(self._candidates)

    @property
    def guessed(self) -> set[str]:
        return set(self._guessed)


def _demo() -> None:  # pragma: no cover - manual smoke run
    eh = EvilHangman()
    print(f"Category: {eh.category}, candidates: {len(eh.candidates)}")
    print(f"Mask: {mask(eh.peek_word(), set())}")
    for letter in "EAIOU":
        revealed = eh.guess(letter)
        print(f"  guess {letter}: revealed={revealed}, "
              f"candidates left={len(eh.candidates)}, "
              f"mask={mask(eh.peek_word(), eh.guessed)}")


if __name__ == "__main__":  # pragma: no cover
    _demo()
