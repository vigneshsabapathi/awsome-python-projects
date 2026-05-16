"""Carrot in a Box, a 2-player bluffing game.

Two boxes are placed in front of two players. One box contains a carrot.
Each player privately peeks at their own box. They then negotiate / bluff.
The first player decides to either SWAP boxes with the second player or
KEEP the boxes as they are. The boxes are revealed: whoever ends up
holding the carrot wins.

This is a tiny asymmetric-information game — once both players have
peeked, each one knows the *full* state of the game (because there are
only two boxes and one carrot). The negotiation phase is pure bluff.

Run:
    uv run python carrot_box/carrot_box.py

Tags: short, game, bluffing, two-player, asymmetric-information
"""
from __future__ import annotations

import random


PLAYERS = (1, 2)


class Game:
    """Pure carrot-in-a-box game state, no I/O.

    Players are 1 and 2. The carrot lives in box 1 or box 2. The owner
    mapping `boxes` maps each player to the box they're holding. After
    a SWAP, players exchange boxes.

    Attributes:
        carrot_box: which box (1 or 2) actually contains the carrot.
        boxes:      {player: box_number} — who currently holds which box.
        peeked:     set of players who have used their peek.
        decided:    True once player 1 has chosen swap-or-keep.
        swapped:    True if the chosen action was SWAP.
        winner:     None until reveal(); then 1 or 2.
    """

    def __init__(self, rng: random.Random | None = None) -> None:
        self.rng = rng if rng is not None else random.Random()
        # Randomly seat the carrot in box 1 or box 2.
        self.carrot_box: int = self.rng.choice([1, 2])
        # Initial assignment: player 1 holds box 1, player 2 holds box 2.
        self.boxes: dict[int, int] = {1: 1, 2: 2}
        self.peeked: set[int] = set()
        self.decided: bool = False
        self.swapped: bool = False
        self.winner: int | None = None

    # ---- queries -----------------------------------------------------

    def has_carrot(self, player: int) -> bool:
        """True if `player` is currently holding the box with the carrot."""
        self._check_player(player)
        return self.boxes[player] == self.carrot_box

    def peek(self, player: int) -> bool:
        """Player privately checks their box. Returns True if it contains
        the carrot. Marks them as having peeked (idempotent — peeking
        twice is allowed but the result is unchanged because nothing has
        moved yet)."""
        self._check_player(player)
        if self.decided:
            raise RuntimeError('Cannot peek after the swap-or-keep decision.')
        self.peeked.add(player)
        return self.has_carrot(player)

    # ---- actions -----------------------------------------------------

    def decide(self, player: int, swap: bool) -> None:
        """Player 1 chooses to swap or keep. By the rules of the game the
        decider must be player 1 (the first player). `swap=True` swaps
        both players' boxes."""
        if player != 1:
            raise ValueError('Only player 1 may decide swap-or-keep.')
        if self.decided:
            raise RuntimeError('Decision already made.')
        self.decided = True
        self.swapped = swap
        if swap:
            self.boxes[1], self.boxes[2] = self.boxes[2], self.boxes[1]

    def reveal(self) -> int:
        """Open the boxes. Returns the winning player (1 or 2). Must be
        called after `decide`."""
        if not self.decided:
            raise RuntimeError('Cannot reveal before the decision.')
        self.winner = 1 if self.boxes[1] == self.carrot_box else 2
        return self.winner

    # ---- internals ---------------------------------------------------

    def _check_player(self, player: int) -> None:
        if player not in PLAYERS:
            raise ValueError(f'Player must be 1 or 2, got {player!r}.')


# ---- AI bluff helper (twist: 1-vs-AI mode) ---------------------------

def ai_decision(ai_has_carrot: bool, rng: random.Random | None = None) -> bool:
    """Return True if the AI (acting as player 1) chooses to SWAP.

    Strategy: if the AI is *holding* the carrot, never swap. If it isn't,
    always swap. The bluffing happens during the talk phase (which the
    CLI prints), but the optimal action — given perfect knowledge of
    one's own box plus the fact that there are only two boxes — is
    deterministic. We add a tiny noise factor so the AI is exploitable
    by an attentive human.
    """
    if rng is None:
        rng = random.Random()
    # 5% mistake rate — keeps the AI human-like.
    mistake = rng.random() < 0.05
    if ai_has_carrot:
        return mistake          # would normally KEEP
    return not mistake          # would normally SWAP


# ---- CLI -------------------------------------------------------------

INTRO = """Carrot in a Box — a 2-player bluffing game.

There are two boxes. One contains a carrot. Each of you will privately
peek inside your own box, then talk it out. Player 1 then decides to
SWAP boxes with player 2, or KEEP. Whoever ends up holding the carrot
wins.
"""


def _read_yn(prompt: str) -> bool:
    while True:
        ans = input(prompt).strip().lower()
        if ans in ('y', 'yes'):
            return True
        if ans in ('n', 'no'):
            return False
        print('Please answer y or n.')


def _hold_screen(message: str) -> None:
    """Pseudo-private prompt — player presses Enter, peeks, then we
    print enough blank lines that the next player can't easily see."""
    input(message)


def _clear_screen() -> None:
    print('\n' * 40)


def _play_round(rng: random.Random, vs_ai: bool, score: dict[int, int]) -> None:
    game = Game(rng=rng)

    print('\n--- New round ---')
    p1_label = 'AI' if vs_ai else 'Player 1'
    p2_label = 'You (player 2)' if vs_ai else 'Player 2'

    if vs_ai:
        # Human is player 2.
        _hold_screen(f'{p2_label}, press Enter to peek at your box... ')
        you_have = game.peek(2)
        print(f'  Your box {"CONTAINS" if you_have else "is EMPTY"}.')
        _hold_screen('Press Enter to clear the screen... ')
        _clear_screen()
        # AI peeks silently.
        ai_has = game.peek(1)
        ai_swap = ai_decision(ai_has, rng)
        # AI's "talk" — a transparent bluff.
        bluff = rng.choice([
            'AI: "I definitely have the carrot. You should keep your box."',
            'AI: "Ugh, mine is empty. Want to swap?"',
            'AI: "Hmm, I am not sure what to do."',
        ])
        print(bluff)
        game.decide(1, ai_swap)
        action = 'SWAPPED boxes' if ai_swap else 'KEPT boxes'
        print(f'AI {action}.')
    else:
        # Two humans, hot-seat.
        _hold_screen('Player 1, press Enter to peek at your box... ')
        p1_has = game.peek(1)
        print(f'  Player 1\'s box {"CONTAINS" if p1_has else "is EMPTY"}.')
        _hold_screen('Press Enter to clear the screen... ')
        _clear_screen()
        _hold_screen('Player 2, press Enter to peek at your box... ')
        p2_has = game.peek(2)
        print(f'  Player 2\'s box {"CONTAINS" if p2_has else "is EMPTY"}.')
        _hold_screen('Press Enter to clear the screen... ')
        _clear_screen()
        print('Talk it out. Bluff if you must.\n')
        swap = _read_yn('Player 1, do you want to SWAP boxes? (y/n) ')
        game.decide(1, swap)

    winner = game.reveal()
    print()
    print(f'The carrot was in box {game.carrot_box}.')
    print(f'After the decision, player 1 held box {game.boxes[1]}, '
          f'player 2 held box {game.boxes[2]}.')
    if vs_ai:
        if winner == 2:
            print('You win the carrot!')
        else:
            print('AI wins the carrot.')
    else:
        print(f'Player {winner} wins the carrot!')

    score[winner] += 1
    print(f'Score — {p1_label}: {score[1]}  |  {p2_label}: {score[2]}')


def main() -> None:
    print(INTRO)
    vs_ai = _read_yn('Play against the AI? (y = vs AI, n = 2 humans) ')
    rng = random.Random()
    score = {1: 0, 2: 0}

    while True:
        _play_round(rng, vs_ai, score)
        if not _read_yn('\nPlay another round? (y/n) '):
            break

    p1_label = 'AI' if vs_ai else 'Player 1'
    p2_label = 'You' if vs_ai else 'Player 2'
    print(f'\nFinal score — {p1_label}: {score[1]}  |  {p2_label}: {score[2]}')
    print('Thanks for playing!')


if __name__ == '__main__':
    main()
