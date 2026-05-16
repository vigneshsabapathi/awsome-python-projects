"""Three-Card Monte — a street-corner shuffle game.

The dealer reveals three face-down cards (one of which is the queen),
shuffles them via a sequence of pairwise swaps, and the player must point
to the queen at the end. The CLI animates the swaps with a simple
text-based shuffle.

Pure logic lives in the `Game` class so the GUI and TUI can share it.

Tags: short, game, animation, sleight-of-hand
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

NUM_CARDS = 3
DEFAULT_NUM_SWAPS = 10
QUEEN = 'Q'
BLANK = '_'


@dataclass
class Game:
    """Pure Three-Card Monte engine — no I/O, fully deterministic with a seeded RNG.

    State is a list of card labels at positions 0..NUM_CARDS-1; one of them
    is the queen (`QUEEN`) and the rest are blanks (`BLANK`).

    The `history` is the list of swap pairs the dealer performed, in order
    — useful for "show solution" / replay features in the GUIs.
    """

    num_swaps: int = DEFAULT_NUM_SWAPS
    rng: random.Random | None = None
    cards: list[str] = field(default_factory=list)
    history: list[tuple[int, int]] = field(default_factory=list)
    queen_index: int = 0
    initial_queen_index: int = 0
    finished: bool = False
    won: bool | None = None

    def _rng(self) -> random.Random:
        return self.rng if self.rng is not None else random

    def setup(self) -> None:
        """Place the queen at a random position, plan `num_swaps` distinct swaps,
        and apply them to compute the final state. The history is preserved."""
        rng = self._rng()
        self.cards = [BLANK] * NUM_CARDS
        self.initial_queen_index = rng.randrange(NUM_CARDS)
        self.cards[self.initial_queen_index] = QUEEN
        self.queen_index = self.initial_queen_index
        self.history = []
        self.finished = False
        self.won = None

        for _ in range(max(0, self.num_swaps)):
            i = rng.randrange(NUM_CARDS)
            j = rng.randrange(NUM_CARDS - 1)
            if j >= i:  # remap to avoid i == j
                j += 1
            self.swap(i, j, _record=True)

    def swap(self, i: int, j: int, _record: bool = True) -> None:
        """Swap cards at positions i and j (both must be in range)."""
        if not (0 <= i < NUM_CARDS and 0 <= j < NUM_CARDS):
            raise ValueError(f'positions out of range: {i}, {j}')
        if i == j:
            return
        self.cards[i], self.cards[j] = self.cards[j], self.cards[i]
        if self.queen_index == i:
            self.queen_index = j
        elif self.queen_index == j:
            self.queen_index = i
        if _record:
            self.history.append((i, j))

    def pick(self, i: int) -> bool:
        """Player picks position i. Returns True if it's the queen.
        Sets `finished = True` and `won` accordingly."""
        if not (0 <= i < NUM_CARDS):
            raise ValueError(f'position out of range: {i}')
        self.finished = True
        self.won = (i == self.queen_index)
        return self.won

    def state(self) -> dict:
        """Snapshot of the current game state. Stable contract for frontends."""
        return {
            'cards': list(self.cards),
            'queen': self.queen_index,
            'initial_queen': self.initial_queen_index,
            'history': list(self.history),
            'num_swaps': self.num_swaps,
            'finished': self.finished,
            'won': self.won,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _render(cards: list[str], hidden: bool = True, hilite: int | None = None) -> str:
    """Render the row of cards. If hidden, show face-down (`?`); else show face."""
    parts = []
    for idx, c in enumerate(cards):
        face = '?' if hidden else c
        marker = '>' if idx == hilite else ' '
        parts.append(f'{marker}[{face}]')
    return ' '.join(parts) + f'\n  1   2   3'


def _animate_swap(cards: list[str], i: int, j: int, delay: float = 0.25) -> None:
    """Print a brief 2-frame swap animation in the terminal."""
    print(f'  swap {i + 1} <-> {j + 1}')
    time.sleep(delay)


def main() -> None:
    print('Three-Card Monte')
    print('-' * 40)
    print('Watch the queen (Q). After the shuffle, pick the card you think')
    print('is the queen. Three cards. One queen. Easy money — they say.')
    print()

    rng = random.Random()

    while True:
        try:
            ans = input('How many swaps? [10] ').strip()
        except EOFError:
            return
        if ans == '':
            num_swaps = DEFAULT_NUM_SWAPS
            break
        if ans.isdecimal() and 0 < int(ans) <= 200:
            num_swaps = int(ans)
            break
        print('Enter a number 1..200.')

    try:
        delay_in = input('Swap delay in seconds? [0.25] ').strip()
        delay = float(delay_in) if delay_in else 0.25
    except (EOFError, ValueError):
        delay = 0.25

    game = Game(num_swaps=num_swaps, rng=rng)
    game.setup()

    # Show the initial state with the queen face up — this is what the dealer
    # *shows* the player before the shuffle starts.
    print()
    print('The dealer shows the cards:')
    initial = [BLANK] * NUM_CARDS
    initial[game.initial_queen_index] = QUEEN
    print(_render(initial, hidden=False, hilite=game.initial_queen_index))
    print()
    input('Press Enter to begin the shuffle...')

    # Replay the recorded shuffle so we can animate it. We re-derive the
    # intermediate states from the history without needing to peek at game.cards.
    working = list(initial)
    for n, (i, j) in enumerate(game.history, start=1):
        print(f'\nShuffle {n}/{num_swaps}')
        _animate_swap(working, i, j, delay=delay)
        working[i], working[j] = working[j], working[i]
        print(_render(working, hidden=True))

    print('\nWhere is the queen?')
    while True:
        try:
            pick = input('Pick 1, 2, or 3 (or s = show solution, q = quit): ').strip().lower()
        except EOFError:
            return
        if pick == 'q':
            return
        if pick == 's':
            print('Solution trace:')
            print(f'  queen started at position {game.initial_queen_index + 1}')
            for n, (i, j) in enumerate(game.history, start=1):
                print(f'  {n:2d}. swap {i + 1} <-> {j + 1}')
            print(f'  queen ended at position {game.queen_index + 1}')
            continue
        if pick in {'1', '2', '3'}:
            won = game.pick(int(pick) - 1)
            print('\nReveal:')
            print(_render(game.cards, hidden=False, hilite=int(pick) - 1))
            if won:
                print('\n  YOU WIN! You tracked the queen.')
            else:
                print(f'\n  House wins. The queen was at position {game.queen_index + 1}.')
            return
        print('Invalid input.')


if __name__ == '__main__':
    main()
