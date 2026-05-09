"""Rock Paper Scissors — three-mode CLI.

Consolidates two Sweigart Big Book mini-projects:
  #59 Rock Paper Scissors           → fair mode (uniform random)
  #60 Rock Paper Scissors (always-win) → cheat mode (computer waits)

Plus a third mode that's the real twist:
  markov mode → computer learns 1st-order transitions of player moves
                and plays the counter to the predicted next move.

Run:
    uv run python rps/rps.py
"""
from __future__ import annotations

import random
from typing import Optional

MOVES = ('rock', 'paper', 'scissors')

# Move that beats the key.
COUNTER = {
    'rock':     'paper',     # paper covers rock
    'paper':    'scissors',  # scissors cut paper
    'scissors': 'rock',      # rock crushes scissors
}

EMOJI = {'rock': '🪨', 'paper': '📄', 'scissors': '✂️'}


def result_of(p1: str, p2: str) -> str:
    """Return 'tie', 'p1', or 'p2' from p1's perspective."""
    if p1 == p2:
        return 'tie'
    return 'p1' if COUNTER[p2] == p1 else 'p2'


class Game:
    """Stateful RPS game.

    mode:
      'fair'   — computer picks uniformly at random.
      'markov' — 1st-order Markov chain over player moves; counter the
                 most-likely next move given the last move played.
      'cheat'  — computer "sees" your move and plays the counter.
                 Player can never win (Sweigart's #60 always-win version).
    """

    def __init__(self, mode: str = 'fair',
                 rng: Optional[random.Random] = None) -> None:
        if mode not in ('fair', 'markov', 'cheat'):
            raise ValueError(f"unknown mode: {mode!r}")
        self.mode = mode
        self.rng = rng or random.Random()
        self.score = {'wins': 0, 'losses': 0, 'ties': 0}
        self.last_player_move: Optional[str] = None
        # transitions[a][b] = count of times player went a -> b
        self.transitions: dict[str, dict[str, int]] = {
            m: {n: 0 for n in MOVES} for m in MOVES
        }

    # ----- prediction --------------------------------------------------

    def _predict_player(self) -> str:
        """Predict the player's next move using 1st-order Markov stats.

        With no history (or no observations from the last move yet),
        falls back to uniform random.
        """
        last = self.last_player_move
        if last is None:
            return self.rng.choice(MOVES)
        row = self.transitions[last]
        total = sum(row.values())
        if total == 0:
            return self.rng.choice(MOVES)
        # argmax with random tie-break to avoid being predictable ourselves.
        best = max(row.values())
        candidates = [m for m, c in row.items() if c == best]
        return self.rng.choice(candidates)

    def _choose_computer_move(self, player_move: str) -> str:
        if self.mode == 'fair':
            return self.rng.choice(MOVES)
        if self.mode == 'cheat':
            return COUNTER[player_move]
        # markov
        predicted = self._predict_player()
        return COUNTER[predicted]

    # ----- public API --------------------------------------------------

    def play(self, player_move: str) -> dict:
        """Play one round. Returns dict with computer_move, result, score."""
        if player_move not in MOVES:
            raise ValueError(f"invalid move: {player_move!r}")

        computer_move = self._choose_computer_move(player_move)
        outcome = result_of(player_move, computer_move)
        if outcome == 'tie':
            self.score['ties'] += 1
            result = 'tie'
        elif outcome == 'p1':
            self.score['wins'] += 1
            result = 'win'
        else:
            self.score['losses'] += 1
            result = 'lose'

        # Update transitions *after* the move is decided so this round's
        # prediction was based on the player's history up to the previous round.
        if self.last_player_move is not None:
            self.transitions[self.last_player_move][player_move] += 1
        self.last_player_move = player_move

        return {
            'computer_move': computer_move,
            'result': result,
            'score': dict(self.score),
        }

    def reset(self) -> None:
        self.score = {'wins': 0, 'losses': 0, 'ties': 0}
        self.last_player_move = None
        self.transitions = {m: {n: 0 for n in MOVES} for m in MOVES}


# ----- CLI ------------------------------------------------------------------

ALIASES = {
    'r': 'rock', 'rock': 'rock',
    'p': 'paper', 'paper': 'paper',
    's': 'scissors', 'scissors': 'scissors',
}


def _prompt_mode() -> str:
    print('Pick a mode:')
    print('  1) fair    — computer picks at random')
    print('  2) markov  — computer learns your patterns (the twist)')
    print('  3) cheat   — computer always wins (Sweigart #60)')
    while True:
        choice = input('> ').strip().lower()
        if choice in ('1', 'fair', 'f'):
            return 'fair'
        if choice in ('2', 'markov', 'm'):
            return 'markov'
        if choice in ('3', 'cheat', 'c'):
            return 'cheat'
        print('Enter 1, 2, or 3.')


def main() -> None:
    print('Rock, Paper, Scissors')
    print('=====================')
    mode = _prompt_mode()
    game = Game(mode=mode)
    print(f'\nMode: {mode}. Type r/p/s to play, q to quit.\n')

    while True:
        raw = input('Your move (r/p/s, q to quit) > ').strip().lower()
        if raw in ('q', 'quit', 'exit'):
            break
        if raw not in ALIASES:
            print('Pick rock, paper, or scissors.')
            continue
        move = ALIASES[raw]
        result = game.play(move)
        cm = result['computer_move']
        print(f'  You: {EMOJI[move]} {move}    Computer: {EMOJI[cm]} {cm}')
        if result['result'] == 'win':
            print('  -> You win!')
        elif result['result'] == 'lose':
            print('  -> Computer wins.')
        else:
            print('  -> Tie.')
        s = result['score']
        print(f'  Score: {s["wins"]}W - {s["losses"]}L - {s["ties"]}T\n')

    s = game.score
    total = s['wins'] + s['losses'] + s['ties']
    print(f'\nFinal: {s["wins"]}W - {s["losses"]}L - {s["ties"]}T '
          f'over {total} round(s).')
    print('Thanks for playing!')


if __name__ == '__main__':
    main()
