"""Royal Game of Ur — CLI + shared game logic.

Ancient Mesopotamian race game (~2600 BCE). Each player has 7 pieces and
races them along a 14-square track, hopping to the finish line. The dice
are 4 binary tetrahedral dice; the roll is the count of "marked" corners
showing — a value in 0..4 with binomial(4, ½) distribution.

Track layout (Finkel reconstruction):

      P2 path:  20  19  18              17  16  15
                                                 .
                4   3   2   1   13   12   11   10   9   8   7   5
                                                 .
      P1 path:  20  19  18              17  16  15

Internally we use a single shared board where each player's "track" is a
list of 16 path positions plus an off-board start (idx 0) and finish (idx 15).

We model the canonical Finkel layout:

- Path length 14 (positions 1..14) per player.
- Squares 1..4 are private to a player, 5..12 are shared, 13..14 are private.
- Rosettes (★) at positions 4, 8 (shared center), 14.
- Landing on a rosette = bonus turn AND piece is safe (cannot be captured).
- Landing on an opponent's piece in a SHARED square (5..12) sends it back
  to start. You cannot capture on the shared rosette (square 8) because it
  is safe.
- Two of the player's own pieces cannot stack on the same square.
- To bear off (move from 14 -> finish) the roll must be exact; otherwise
  the move is illegal.

Module exposes:

- ``Board`` — pure game state with ``move``, ``legal_moves``, ``winner``.
- ``roll(rng)`` — sum of 4 binary dice, returns 0..4.
- ``ai_move`` — expectimax (max over moves, expectation over future rolls).

Run:
    uv run python ur/ur.py
"""
from __future__ import annotations

import random
import sys
from typing import Optional

# --- Constants ---------------------------------------------------------------

PLAYER_1 = 1
PLAYER_2 = 2
PIECES_PER_PLAYER = 7
PATH_LEN = 14            # squares 1..14 per player
START = 0                # off-board start
FINISH = 15              # past-the-end (borne off)

# Rosette squares (1-indexed positions on a player's path).
PRIVATE_ROSETTES = (4, 14)
SHARED_ROSETTE = 8
ROSETTES = frozenset((4, 8, 14))

# Shared squares (overlap on the central row in the H-shape).
SHARED_RANGE = range(5, 13)  # squares 5..12 inclusive

# Difficulty -> expectimax depth.
DIFFICULTY_DEPTH = {
    'easy': 1,
    'medium': 2,
    'hard': 3,
}

# Probabilities of each binary-dice sum (4 dice, p=½ each).
# C(4,k)/16 for k in 0..4.
ROLL_PROBS = {
    0: 1 / 16,
    1: 4 / 16,
    2: 6 / 16,
    3: 4 / 16,
    4: 1 / 16,
}


def other(player: int) -> int:
    return PLAYER_2 if player == PLAYER_1 else PLAYER_1


# --- Dice --------------------------------------------------------------------


def roll(rng: random.Random) -> int:
    """Roll 4 binary tetrahedral dice. Return the sum (0..4)."""
    return sum(rng.randint(0, 1) for _ in range(4))


# --- Board -------------------------------------------------------------------


class Board:
    """Royal Game of Ur position.

    Per-player state is a list of 7 piece positions, each in [0, 15]:
        0  -> still in the start pile (off-board)
        1..14 -> on track at that square (using the player's own indexing)
        15 -> finished (borne off)
    """

    __slots__ = ('pieces', 'finkel')

    def __init__(self,
                 pieces: Optional[dict[int, list[int]]] = None,
                 finkel: bool = True) -> None:
        if pieces is None:
            self.pieces = {
                PLAYER_1: [START] * PIECES_PER_PLAYER,
                PLAYER_2: [START] * PIECES_PER_PLAYER,
            }
        else:
            self.pieces = {
                PLAYER_1: list(pieces[PLAYER_1]),
                PLAYER_2: list(pieces[PLAYER_2]),
            }
        # Finkel rules (reconstruction). When False, classroom variant:
        # - Captures still occur on shared squares
        # - Rosettes still grant a bonus turn
        # - But shared rosette (8) does NOT make piece safe (can be captured).
        self.finkel = finkel

    # -- Core ops ------------------------------------------------------------

    def copy(self) -> 'Board':
        b = Board(pieces=self.pieces, finkel=self.finkel)
        return b

    def finished_count(self, player: int) -> int:
        return sum(1 for p in self.pieces[player] if p == FINISH)

    def on_board(self, player: int, square: int) -> bool:
        """Does ``player`` have a piece on track ``square`` (1..14)?"""
        return any(p == square for p in self.pieces[player])

    def at_square_pieces(self, player: int, square: int) -> list[int]:
        """Indices of ``player``'s pieces sitting on ``square``."""
        return [i for i, p in enumerate(self.pieces[player]) if p == square]

    def winner(self) -> Optional[int]:
        """1 / 2 if a player has finished all pieces, else None."""
        if self.finished_count(PLAYER_1) == PIECES_PER_PLAYER:
            return PLAYER_1
        if self.finished_count(PLAYER_2) == PIECES_PER_PLAYER:
            return PLAYER_2
        return None

    @staticmethod
    def roll(rng: random.Random) -> int:
        """Convenience wrapper — see :func:`roll`."""
        return roll(rng)

    # -- Move generation -----------------------------------------------------

    def legal_moves(self, player: int, dice: int) -> list[int]:
        """Return piece indices ``player`` may move with roll ``dice``.

        A move is legal iff:
        - ``dice >= 1``.
        - Source piece is on START or on a track square 1..14.
        - Destination square == source + dice is in 1..15 (15 = bear off
          requires *exact* roll past 14).
        - Destination is not occupied by one of the player's own pieces.
        - If destination is the shared rosette (square 8) and an opponent
          piece occupies it, the move is illegal (rosettes are safe in the
          Finkel reconstruction).
        """
        if dice <= 0:
            return []
        out = []
        opp = other(player)
        for i, pos in enumerate(self.pieces[player]):
            if pos == FINISH:
                continue
            new_pos = pos + dice
            if new_pos > FINISH:
                continue  # overshoot — must be exact
            # Cannot land on own piece (except all are at START stack).
            if new_pos != FINISH and new_pos in self.pieces[player]:
                continue
            # Cannot capture on shared rosette (always safe in Finkel).
            if (new_pos == SHARED_ROSETTE
                    and self._is_shared_square(new_pos)
                    and self.finkel
                    and self.on_board(opp, new_pos)):
                continue
            out.append(i)
        return out

    def has_any_legal_move(self, player: int, dice: int) -> bool:
        return len(self.legal_moves(player, dice)) > 0

    @staticmethod
    def _is_shared_square(square: int) -> bool:
        return square in SHARED_RANGE

    # -- Move ----------------------------------------------------------------

    def move(self, player: int, piece_idx: int, dice: int) -> dict:
        """Apply move and return a result dict.

        Result keys:
            ``player``     — who moved.
            ``piece_idx``  — which piece (0..6).
            ``dice``       — the roll used.
            ``from``       — source square (0..15).
            ``to``         — destination (1..15).
            ``rosette``    — True if landed on a rosette (4, 8, or 14).
            ``capture``    — None or {'opp_idx', 'square'} if captured.
            ``finished``   — True if piece reached square 15 (borne off).
            ``free_turn``  — True if rosette landing.
            ``game_over``  — True if game is now won.
            ``winner``     — winning player or None.
            ``next_player``— player to move next.
        """
        if piece_idx not in self.legal_moves(player, dice):
            raise ValueError(f'Illegal move: player={player} piece={piece_idx} '
                             f'dice={dice}')
        opp = other(player)
        src = self.pieces[player][piece_idx]
        dst = src + dice
        # Move.
        self.pieces[player][piece_idx] = dst

        capture = None
        if (dst != FINISH
                and self._is_shared_square(dst)
                and self.on_board(opp, dst)):
            # Squarely a capture (we already disallowed capturing on the
            # shared rosette in legal_moves under Finkel rules).
            opp_idx = next(i for i, p in enumerate(self.pieces[opp])
                           if p == dst)
            self.pieces[opp][opp_idx] = START
            capture = {'opp_idx': opp_idx, 'square': dst}

        rosette = dst in ROSETTES and dst != FINISH
        finished = dst == FINISH

        win = self.winner()
        game_over = win is not None

        if game_over:
            next_player = player
        elif rosette:
            next_player = player  # bonus turn
        else:
            next_player = opp

        return {
            'player': player,
            'piece_idx': piece_idx,
            'dice': dice,
            'from': src,
            'to': dst,
            'rosette': rosette,
            'capture': capture,
            'finished': finished,
            'free_turn': rosette and not game_over,
            'game_over': game_over,
            'winner': win,
            'next_player': next_player,
        }

    # -- Misc ---------------------------------------------------------------

    def key(self) -> tuple:
        """Hashable snapshot for memoization."""
        return (
            tuple(sorted(self.pieces[PLAYER_1])),
            tuple(sorted(self.pieces[PLAYER_2])),
            self.finkel,
        )

    def __str__(self) -> str:
        # ASCII H-shape. We render the player tracks plus shared row.
        # Player paths (1..14):
        #   1..4 (top-row private) -> 5..12 (shared middle row) -> 13..14 (top-row again)
        # We draw P2 on top, shared in middle, P1 on bottom, with rosettes ★.
        def cell(player: int, square: int) -> str:
            count = sum(1 for p in self.pieces[player] if p == square)
            ros = '*' if square in ROSETTES else ' '
            if count == 0:
                return f' {ros} '
            if player == PLAYER_1:
                return f'X{count}{ros}'
            return f'O{count}{ros}'

        # Top row (P2): squares 4 3 2 1 _ _ _ _ _ _ _ _ 14 13 (with 5..12 absent)
        # We'll use a layout matching Sweigart-style boards but with no copying.
        top_priv_left = [cell(PLAYER_2, s) for s in (4, 3, 2, 1)]
        top_priv_right = [cell(PLAYER_2, s) for s in (14, 13)]
        bot_priv_left = [cell(PLAYER_1, s) for s in (4, 3, 2, 1)]
        bot_priv_right = [cell(PLAYER_1, s) for s in (14, 13)]
        # Shared middle row 5..12; both players sit here, but at most one piece
        # per square. Show whichever piece is there (or empty).
        shared_cells = []
        for s in range(5, 13):
            ros = '*' if s in ROSETTES else ' '
            if self.on_board(PLAYER_1, s):
                shared_cells.append(f'X1{ros}')
            elif self.on_board(PLAYER_2, s):
                shared_cells.append(f'O1{ros}')
            else:
                shared_cells.append(f' {ros} ')

        sep = '|'
        top = (
            sep + sep.join(top_priv_left) + sep
            + '       ' * 4
            + sep + sep.join(top_priv_right) + sep
        )
        mid = sep + sep.join(shared_cells) + sep
        bot = (
            sep + sep.join(bot_priv_left) + sep
            + '       ' * 4
            + sep + sep.join(bot_priv_right) + sep
        )
        # Score line.
        s1 = self.finished_count(PLAYER_1)
        s2 = self.finished_count(PLAYER_2)
        start1 = sum(1 for p in self.pieces[PLAYER_1] if p == START)
        start2 = sum(1 for p in self.pieces[PLAYER_2] if p == START)
        score = (f'P2: start={start2} finish={s2}     '
                 f'P1: start={start1} finish={s1}')
        return '\n'.join(['', 'P2 ->', top, mid, bot, '<- P1', score])


# --- AI: expectimax over dice rolls ------------------------------------------


_INF = 10 ** 9


def _evaluate(board: Board, player: int) -> float:
    """Static heuristic from ``player``'s perspective."""
    me = player
    opp = other(player)
    score = 0.0

    # Finished pieces are worth a lot.
    score += 12 * board.finished_count(me)
    score -= 12 * board.finished_count(opp)

    # Progress along track for non-finished pieces.
    for p in board.pieces[me]:
        if p == FINISH:
            continue
        score += p  # raw position
        # Rosette occupancy is good (safe + free turn was earned).
        if p in ROSETTES:
            score += 2
    for p in board.pieces[opp]:
        if p == FINISH:
            continue
        score -= p
        if p in ROSETTES:
            score -= 2

    # Pieces in shared zone are at risk; small penalty for being capturable.
    for p in board.pieces[me]:
        if p in SHARED_RANGE and p != SHARED_ROSETTE:
            score -= 0.5
    for p in board.pieces[opp]:
        if p in SHARED_RANGE and p != SHARED_ROSETTE:
            score += 0.5

    return score


def _expectimax(board: Board, depth: int, to_move: int,
                root_player: int, dice: int, memo: dict) -> float:
    """Expectimax search.

    At a "decision" node we have a known dice ``dice`` for ``to_move`` and
    pick the move maximizing (if ``to_move == root_player``) or minimizing
    the value. After applying a move (no rosette) we go to a "chance"
    node: opponent's dice roll, expectation over 0..4.
    With rosette: same player rolls again -> chance node for the *same*
    player.
    """
    # Terminal.
    win = board.winner()
    if win is not None:
        return _INF if win == root_player else -_INF
    if depth <= 0:
        return _evaluate(board, root_player)

    moves = board.legal_moves(to_move, dice)
    if dice == 0 or not moves:
        # Forfeit the turn — opponent rolls.
        return _chance(board, depth - 1, other(to_move), root_player, memo)

    if to_move == root_player:
        best = -_INF
        for m in moves:
            child = board.copy()
            res = child.move(to_move, m, dice)
            if res['game_over']:
                v = _INF if res['winner'] == root_player else -_INF
            elif res['free_turn']:
                # Same player rolls again.
                v = _chance(child, depth - 1, to_move, root_player, memo)
            else:
                v = _chance(child, depth - 1, other(to_move), root_player, memo)
            if v > best:
                best = v
        return best
    else:
        worst = _INF
        for m in moves:
            child = board.copy()
            res = child.move(to_move, m, dice)
            if res['game_over']:
                v = _INF if res['winner'] == root_player else -_INF
            elif res['free_turn']:
                v = _chance(child, depth - 1, to_move, root_player, memo)
            else:
                v = _chance(child, depth - 1, other(to_move), root_player, memo)
            if v < worst:
                worst = v
        return worst


def _chance(board: Board, depth: int, to_move: int,
            root_player: int, memo: dict) -> float:
    """Chance node: expectation over the next roll (0..4)."""
    if depth <= 0:
        return _evaluate(board, root_player)
    key = (board.key(), depth, to_move)
    cached = memo.get(key)
    if cached is not None:
        return cached
    total = 0.0
    for d, p in ROLL_PROBS.items():
        total += p * _expectimax(board, depth, to_move, root_player, d, memo)
    memo[key] = total
    return total


def ai_move(board: Board, player: int, dice: int,
            depth: int = 2) -> int:
    """Choose the best piece index for ``player`` given roll ``dice``.

    Returns the chosen piece index, or -1 if there are no legal moves.
    Uses expectimax: max over our moves, expectation over future rolls,
    min over opponent's moves.
    """
    moves = board.legal_moves(player, dice)
    if not moves:
        return -1
    if len(moves) == 1:
        return moves[0]

    memo: dict = {}
    best = -_INF
    best_move = moves[0]
    for m in moves:
        child = board.copy()
        res = child.move(player, m, dice)
        if res['game_over']:
            v = _INF if res['winner'] == player else -_INF
        elif res['free_turn']:
            v = _chance(child, depth, player, player, memo)
        else:
            v = _chance(child, depth, other(player), player, memo)
        if v > best:
            best = v
            best_move = m
    return best_move


# --- CLI ---------------------------------------------------------------------


def _ask_mode() -> tuple[bool, int, bool]:
    """Returns (vs_ai, depth, finkel)."""
    print('\nMode:')
    print('  1) Two players (hot-seat)')
    print('  2) vs AI — Easy   (depth 1)')
    print('  3) vs AI — Medium (depth 2)')
    print('  4) vs AI — Hard   (depth 3)')
    while True:
        choice = input('> ').strip()
        if choice in ('1', '2', '3', '4'):
            break
        print('Enter 1, 2, 3, or 4.')
    vs_ai = choice != '1'
    depth = {'2': 1, '3': 2, '4': 3}.get(choice, 0)

    f_in = input('Finkel rules (rosettes safe, recommended)? [Y/n] ').strip().lower()
    finkel = not f_in.startswith('n')
    return vs_ai, depth, finkel


def _ask_piece(board: Board, player: int, dice: int) -> int:
    legal = board.legal_moves(player, dice)
    labels = [str(i + 1) for i in legal]
    while True:
        raw = input(f'Player {player} — piece [{",".join(labels)}, '
                    f'q to quit]: ').strip().lower()
        if raw in ('q', 'quit', 'exit'):
            print('Bye!')
            sys.exit(0)
        if raw.isdigit():
            n = int(raw) - 1
            if n in legal:
                return n
        print('Pick a piece from the legal list.')


def main() -> None:
    print('Royal Game of Ur')
    print('================')
    print('Race 7 pieces along your 14-square path. Roll 4 binary dice (0..4).')
    print('Land on a rosette (*) for a bonus turn. Capture opponents on shared squares.')
    rng = random.Random()

    while True:
        vs_ai, depth, finkel = _ask_mode()
        board = Board(finkel=finkel)
        if not finkel:
            print('Classroom variant: shared rosette is NOT safe.')
        ai_player = PLAYER_2 if vs_ai else None
        current = PLAYER_1

        while board.winner() is None:
            print()
            print(board)

            dice = roll(rng)
            who = 'AI' if vs_ai and current == ai_player else f'Player {current}'
            print(f"\n{who}'s turn — rolled {dice}")

            if dice == 0:
                print('  Roll is 0 — turn forfeited.')
                current = other(current)
                continue

            legal = board.legal_moves(current, dice)
            if not legal:
                print('  No legal moves — turn forfeited.')
                current = other(current)
                continue

            if vs_ai and current == ai_player:
                print(f'  AI thinking (depth={depth})…')
                idx = ai_move(board, current, dice, depth=depth)
                print(f'  AI moves piece {idx + 1}.')
            else:
                idx = _ask_piece(board, current, dice)

            res = board.move(current, idx, dice)
            if res['capture']:
                print('  → Capture!')
            if res['finished']:
                print('  → Piece borne off!')
            if res['free_turn']:
                print('  → Rosette — bonus turn!')
            current = res['next_player']

        print()
        print(board)
        w = board.winner()
        if vs_ai and w == ai_player:
            print('AI wins!')
        else:
            print(f'Player {w} wins!')

        again = input('\nPlay again? (y/n) ').strip().lower()
        if not again.startswith('y'):
            print('Thanks for playing!')
            break


if __name__ == '__main__':
    main()
