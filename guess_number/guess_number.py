"""Guess the Number — classic higher/lower guessing game.

The program picks a secret integer in [low, high]; the player guesses and
gets 'too low' / 'too high' feedback until they find it or run out of
guesses.

Run:
    uv run python guess_number/guess_number.py

This module also exposes pure functions used by the GUI and TUI front
ends:

    Game(low, high, max_guesses, rng)   - encapsulated game state
    Game.guess(n) -> dict               - submit a guess, get a verdict
    optimal_guess(low, high) -> int     - binary-search midpoint
    bits_remaining(low, high) -> float  - log2 of remaining candidates
    REVERSE_LOW / REVERSE_HIGH defaults

Tags: short, game, search, binary-search, info-theory
"""
from __future__ import annotations

import math
import random
from typing import Optional

DEFAULT_LOW = 1
DEFAULT_HIGH = 100
DEFAULT_MAX_GUESSES = 10  # ceil(log2(100)) == 7, so 10 is generous


def optimal_guess(low: int, high: int) -> int:
    """Return the binary-search midpoint of [low, high].

    This is the guess that maximally bisects the remaining candidate
    set, removing exactly one bit of entropy in the worst case.
    """
    if low > high:
        raise ValueError(f'empty range: low={low} > high={high}')
    return (low + high) // 2


def bits_remaining(low: int, high: int) -> float:
    """Bits of entropy still in the candidate set [low, high].

    log2(N) where N = high - low + 1. Returns 0.0 for a singleton range
    (the secret is fully determined).
    """
    n = high - low + 1
    if n <= 1:
        return 0.0
    return math.log2(n)


class Game:
    """Encapsulated guess-the-number session.

    Parameters
    ----------
    low, high : int
        Inclusive bounds for the secret number.
    max_guesses : int
        How many guesses the player gets before they lose.
    rng : random.Random | None
        Inject a seeded RNG for deterministic tests.

    Attributes
    ----------
    candidate_low, candidate_high : int
        Current narrowed bounds the secret is known to lie within
        (updated from each 'too_low'/'too_high' verdict). Used by GUIs
        to compute hints + entropy.
    history : list[tuple[int, str]]
        (guess, result) pairs in submission order.
    """

    def __init__(
        self,
        low: int = DEFAULT_LOW,
        high: int = DEFAULT_HIGH,
        max_guesses: int = DEFAULT_MAX_GUESSES,
        rng: Optional[random.Random] = None,
    ) -> None:
        if low >= high:
            raise ValueError(f'low must be < high (got {low}, {high})')
        if max_guesses < 1:
            raise ValueError(f'max_guesses must be >= 1 (got {max_guesses})')

        self.low = low
        self.high = high
        self.max_guesses = max_guesses
        self._rng = rng if rng is not None else random.Random()
        self.secret: int = self._rng.randint(low, high)
        self.guesses_left: int = max_guesses
        self.over: bool = False
        self.won: bool = False
        # Narrowed bounds — start at full range, shrink per verdict.
        self.candidate_low: int = low
        self.candidate_high: int = high
        self.history: list[tuple[int, str]] = []

    def guess(self, n: int) -> dict:
        """Submit a guess.

        Returns a dict::

            {
                'result': 'win' | 'too_low' | 'too_high' | 'lose'
                          | 'invalid' | 'over',
                'guesses_left': int,
                'secret': Optional[int],   # only revealed on win/lose
            }

        - 'invalid'  - n outside [low, high]; does not consume a guess.
        - 'over'     - game already finished; does not consume a guess.
        - 'win'      - n == secret.
        - 'lose'     - last guess wrong; secret is revealed.
        - 'too_low'  - n < secret; candidate_low updated to n + 1.
        - 'too_high' - n > secret; candidate_high updated to n - 1.
        """
        if self.over:
            return {
                'result': 'over',
                'guesses_left': self.guesses_left,
                'secret': self.secret if self.won or self.guesses_left == 0
                          else None,
            }
        if not (self.low <= n <= self.high):
            return {
                'result': 'invalid',
                'guesses_left': self.guesses_left,
                'secret': None,
            }

        self.guesses_left -= 1

        if n == self.secret:
            self.over = True
            self.won = True
            self.history.append((n, 'win'))
            return {
                'result': 'win',
                'guesses_left': self.guesses_left,
                'secret': self.secret,
            }

        if n < self.secret:
            result = 'too_low'
            # Tighten lower bound — secret is strictly above n.
            if n + 1 > self.candidate_low:
                self.candidate_low = n + 1
        else:
            result = 'too_high'
            if n - 1 < self.candidate_high:
                self.candidate_high = n - 1

        # Out of guesses?
        if self.guesses_left == 0:
            self.over = True
            self.history.append((n, result))
            return {
                'result': 'lose',
                'guesses_left': 0,
                'secret': self.secret,
            }

        self.history.append((n, result))
        return {
            'result': result,
            'guesses_left': self.guesses_left,
            'secret': None,
        }

    def hint(self) -> int:
        """Optimal next guess given current narrowed bounds."""
        return optimal_guess(self.candidate_low, self.candidate_high)

    def bits_left(self) -> float:
        """Entropy (in bits) remaining in the candidate range."""
        return bits_remaining(self.candidate_low, self.candidate_high)


# ----------------------------------------------------------------------
# Reverse mode — player picks, computer guesses (used by GUI/TUI twist).
# ----------------------------------------------------------------------

class ReverseGame:
    """Computer-as-guesser binary search demo.

    The player thinks of a number in [low, high]; the computer proposes
    midpoints; the player answers 'too_low' / 'too_high' / 'correct'.

    Each `step(verdict)` call advances the search and returns the next
    proposed guess plus the bits-of-entropy removed by the answer.
    """

    def __init__(self, low: int = DEFAULT_LOW, high: int = DEFAULT_HIGH) -> None:
        if low >= high:
            raise ValueError(f'low must be < high (got {low}, {high})')
        self.low = low
        self.high = high
        self.cur_low = low
        self.cur_high = high
        self.over = False
        self.found: Optional[int] = None
        self.proposal: int = optimal_guess(low, high)
        self.history: list[tuple[int, str, float]] = []

    def step(self, verdict: str) -> dict:
        """Advance search after the player's verdict on `self.proposal`.

        verdict in {'correct', 'too_low', 'too_high'}.
        - 'too_low'  means the proposal was too low (secret > proposal).
        - 'too_high' means the proposal was too high (secret < proposal).

        Returns dict::

            {
                'over': bool,
                'proposal': int,        # next guess (or last if over)
                'bits_removed': float,  # information gained this step
                'cur_low': int,
                'cur_high': int,
            }
        """
        if self.over:
            return self._snapshot(0.0)

        before_bits = bits_remaining(self.cur_low, self.cur_high)
        prev = self.proposal

        if verdict == 'correct':
            self.found = prev
            self.over = True
            after_bits = 0.0
        elif verdict == 'too_low':
            self.cur_low = prev + 1
            if self.cur_low > self.cur_high:
                # Player gave inconsistent answers — fall back gracefully.
                self.over = True
                after_bits = 0.0
            else:
                self.proposal = optimal_guess(self.cur_low, self.cur_high)
                after_bits = bits_remaining(self.cur_low, self.cur_high)
        elif verdict == 'too_high':
            self.cur_high = prev - 1
            if self.cur_low > self.cur_high:
                self.over = True
                after_bits = 0.0
            else:
                self.proposal = optimal_guess(self.cur_low, self.cur_high)
                after_bits = bits_remaining(self.cur_low, self.cur_high)
        else:
            raise ValueError(f'unknown verdict: {verdict!r}')

        bits_removed = max(0.0, before_bits - after_bits)
        self.history.append((prev, verdict, bits_removed))
        return self._snapshot(bits_removed)

    def _snapshot(self, bits_removed: float) -> dict:
        return {
            'over': self.over,
            'proposal': self.proposal if not self.over else (
                self.found if self.found is not None else self.proposal),
            'bits_removed': bits_removed,
            'cur_low': self.cur_low,
            'cur_high': self.cur_high,
        }


# ----------------------------------------------------------------------
# CLI front-end.
# ----------------------------------------------------------------------

def _read_int(prompt: str, default: Optional[int] = None) -> int:
    while True:
        raw = input(prompt).strip()
        if raw == '' and default is not None:
            return default
        try:
            return int(raw)
        except ValueError:
            print('  Please enter an integer.')


def main() -> None:
    print('Guess the Number')
    print('================')
    print('I will pick a secret number, you guess higher or lower.\n')

    while True:
        low = _read_int(f'Low bound  [default {DEFAULT_LOW}]: ', DEFAULT_LOW)
        high = _read_int(f'High bound [default {DEFAULT_HIGH}]: ', DEFAULT_HIGH)
        if low >= high:
            print('  low must be strictly less than high.\n')
            continue
        break

    # Default budget = ceil(log2(N)) + a little slack so casual play feels fair.
    span = high - low + 1
    suggested = max(DEFAULT_MAX_GUESSES, math.ceil(math.log2(span)) + 3)
    max_guesses = _read_int(
        f'Max guesses [default {suggested}]: ', suggested)

    game = Game(low, high, max_guesses)
    print(f'\nI am thinking of a number between {low} and {high}.')
    print(f'You have {max_guesses} guesses.\n')

    while not game.over:
        print(f'  ({game.guesses_left} guess'
              f'{"" if game.guesses_left == 1 else "es"} left, '
              f'{game.bits_left():.2f} bits of uncertainty)')
        try:
            n = _read_int('Your guess: ')
        except (EOFError, KeyboardInterrupt):
            print('\nQuitting.')
            return

        verdict = game.guess(n)
        result = verdict['result']

        if result == 'invalid':
            print(f'  Out of range. Stay within [{low}, {high}].')
            continue
        if result == 'too_low':
            print('  Too low.')
        elif result == 'too_high':
            print('  Too high.')
        elif result == 'win':
            print(f'  You got it in {len(game.history)}!')
        elif result == 'lose':
            print(f'  Out of guesses. The secret was {verdict["secret"]}.')

    print('\nThanks for playing!')


if __name__ == '__main__':
    main()
