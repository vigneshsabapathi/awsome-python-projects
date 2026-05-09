"""Mancala (Kalah variant) — CLI + shared game logic.

Two-player Mancala on a 14-cell layout:

    P2:  12  11  10   9   8   7
    [P2 store=13]            [P1 store=6]
    P1:   0   1   2   3   4   5

Each player has 6 pits and one store on their right. On a turn the player
picks up all stones from one of their own pits and sows them counter-clockwise
one stone per cell, **skipping the opponent's store**. Special Kalah rules:

- **Free turn**: if the last stone lands in your own store, you go again.
- **Capture**: if the last stone lands in your own *empty* pit and the
  opposite pit has stones, you capture both stones into your store.
- **Game end**: when one side's pits are all empty. The other player sweeps
  any remaining stones on their side into their store. Most stones wins.

This module exposes:

- ``Board`` — pure game state with ``move``, ``winner``, ``legal_moves``.
- ``ai_move`` — minimax with alpha-beta pruning for the AI.

Run:
    uv run python mancala/mancala.py
"""
from __future__ import annotations

import sys
from typing import Optional

# --- Constants ---------------------------------------------------------------

PLAYER_1 = 1
PLAYER_2 = 2

# Board indices.
P1_PITS = (0, 1, 2, 3, 4, 5)
P1_STORE = 6
P2_PITS = (7, 8, 9, 10, 11, 12)
P2_STORE = 13
TOTAL_CELLS = 14

# Pit opposite to ``i`` (P1 pit 0 <-> P2 pit 12, etc.).
_OPPOSITE = {
    0: 12, 1: 11, 2: 10, 3: 9, 4: 8, 5: 7,
    7: 5, 8: 4, 9: 3, 10: 2, 11: 1, 12: 0,
}

INITIAL_STONES = 4

# Difficulty -> minimax depth.
DIFFICULTY_DEPTH = {
    'easy': 2,
    'medium': 4,
    'hard': 6,
    'expert': 7,
}


def other(player: int) -> int:
    return PLAYER_2 if player == PLAYER_1 else PLAYER_1


def store_of(player: int) -> int:
    return P1_STORE if player == PLAYER_1 else P2_STORE


def pits_of(player: int) -> tuple[int, ...]:
    return P1_PITS if player == PLAYER_1 else P2_PITS


def opponent_store(player: int) -> int:
    return P2_STORE if player == PLAYER_1 else P1_STORE


# --- Board -------------------------------------------------------------------


class Board:
    """14-cell Kalah board.

    ``pits[0..5]`` are P1's pits, ``pits[6]`` is P1's store,
    ``pits[7..12]`` are P2's pits, ``pits[13]`` is P2's store.
    """

    __slots__ = ('pits', 'awari')

    def __init__(self, pits: Optional[list[int]] = None,
                 awari: bool = False) -> None:
        if pits is None:
            self.pits = [INITIAL_STONES] * TOTAL_CELLS
            self.pits[P1_STORE] = 0
            self.pits[P2_STORE] = 0
        else:
            if len(pits) != TOTAL_CELLS:
                raise ValueError(
                    f'pits must have {TOTAL_CELLS} cells, got {len(pits)}'
                )
            self.pits = list(pits)
        # Awari variant disables free-turn rule (still allows captures).
        self.awari = awari

    # -- Core ops ------------------------------------------------------------

    def copy(self) -> 'Board':
        b = Board(self.pits)
        b.awari = self.awari
        return b

    def legal_moves(self, player: int) -> list[int]:
        """Indices of pits the ``player`` can legally play (non-empty)."""
        return [p for p in pits_of(player) if self.pits[p] > 0]

    def side_empty(self, player: int) -> bool:
        return all(self.pits[p] == 0 for p in pits_of(player))

    def is_game_over(self) -> bool:
        return self.side_empty(PLAYER_1) or self.side_empty(PLAYER_2)

    # -- Move ----------------------------------------------------------------

    def move(self, pit: int) -> dict:
        """Sow stones from ``pit``. Returns a result dict.

        Result keys:
            ``player``     — which player moved.
            ``sow_path``   — list of cell indices each sown stone landed in.
            ``last``       — final landing cell.
            ``free_turn``  — True if last stone landed in own store.
            ``capture``    — None or dict {own_pit, opp_pit, stones, store}.
            ``sweep``      — None or dict {by, swept} if game ended via sweep.
            ``game_over``  — True if game ended.
            ``next_player``— player to move next (same player on free_turn).
            ``winner``     — winning player (1, 2), 0 for draw, None if ongoing.
        """
        if pit == P1_STORE or pit == P2_STORE:
            raise ValueError('Cannot pick up stones from a store.')
        if not (0 <= pit < TOTAL_CELLS):
            raise ValueError(f'pit out of range: {pit}')

        if pit in P1_PITS:
            player = PLAYER_1
        elif pit in P2_PITS:
            player = PLAYER_2
        else:
            raise ValueError(f'invalid pit: {pit}')

        stones = self.pits[pit]
        if stones <= 0:
            raise ValueError(f'pit {pit} is empty')

        own_store = store_of(player)
        opp_store = opponent_store(player)

        self.pits[pit] = 0
        idx = pit
        sow_path: list[int] = []
        while stones > 0:
            idx = (idx + 1) % TOTAL_CELLS
            if idx == opp_store:
                continue  # Skip opponent's store.
            self.pits[idx] += 1
            sow_path.append(idx)
            stones -= 1
        last = idx

        # Free-turn rule (skipped in Awari variant).
        free_turn = (not self.awari) and (last == own_store)

        # Capture rule: last stone in own empty pit -> sweep opposite.
        capture = None
        if (last in pits_of(player)
                and self.pits[last] == 1
                and self.pits[_OPPOSITE[last]] > 0):
            opp_pit = _OPPOSITE[last]
            captured = self.pits[opp_pit] + 1  # opposite + the just-sown stone
            self.pits[opp_pit] = 0
            self.pits[last] = 0
            self.pits[own_store] += captured
            capture = {
                'own_pit': last,
                'opp_pit': opp_pit,
                'stones': captured,
                'store': own_store,
            }

        # End-of-game sweep.
        sweep = None
        game_over = False
        if self.is_game_over():
            game_over = True
            sweep = self._sweep_remaining()

        # Determine next player.
        if game_over:
            next_player = player  # irrelevant; game's done
        elif free_turn:
            next_player = player
        else:
            next_player = other(player)

        result = {
            'player': player,
            'sow_path': sow_path,
            'last': last,
            'free_turn': free_turn,
            'capture': capture,
            'sweep': sweep,
            'game_over': game_over,
            'next_player': next_player,
            'winner': self.winner() if game_over else None,
        }
        return result

    def _sweep_remaining(self) -> dict:
        """At game end: each player's leftover stones go to their own store."""
        swept = {PLAYER_1: 0, PLAYER_2: 0}
        for p in P1_PITS:
            swept[PLAYER_1] += self.pits[p]
            self.pits[p] = 0
        for p in P2_PITS:
            swept[PLAYER_2] += self.pits[p]
            self.pits[p] = 0
        self.pits[P1_STORE] += swept[PLAYER_1]
        self.pits[P2_STORE] += swept[PLAYER_2]
        return {'p1': swept[PLAYER_1], 'p2': swept[PLAYER_2]}

    # -- Win / score --------------------------------------------------------

    def score(self, player: int) -> int:
        return self.pits[store_of(player)]

    def winner(self) -> Optional[int]:
        """1 / 2 / 0 (draw) if game over, else None."""
        if not self.is_game_over():
            return None
        s1 = self.pits[P1_STORE]
        s2 = self.pits[P2_STORE]
        if s1 > s2:
            return PLAYER_1
        if s2 > s1:
            return PLAYER_2
        return 0  # Draw.

    # -- Misc ---------------------------------------------------------------

    def key(self) -> tuple:
        return tuple(self.pits)

    def __str__(self) -> str:
        # Display P2 row reversed so layout matches a real board.
        top = '       ' + '  '.join(f'{self.pits[i]:>2}'
                                    for i in reversed(P2_PITS))
        mid = f'P2[{self.pits[P2_STORE]:>2}]' + ' ' * 24 + f'[{self.pits[P1_STORE]:>2}]P1'
        bot = '       ' + '  '.join(f'{self.pits[i]:>2}' for i in P1_PITS)
        labels = '        ' + '   '.join('1 2 3 4 5 6'.split())
        return '\n'.join([top, mid, bot, labels])


# --- AI: minimax + alpha-beta -----------------------------------------------


_WIN_SCORE = 10_000


def _evaluate(board: Board, player: int) -> int:
    """Score from ``player``'s perspective."""
    me_store = board.pits[store_of(player)]
    opp_store = board.pits[store_of(other(player))]
    base = (me_store - opp_store) * 6

    # Bonus for stones on own side (potential).
    me_side = sum(board.pits[p] for p in pits_of(player))
    opp_side = sum(board.pits[p] for p in pits_of(other(player)))
    base += (me_side - opp_side)

    # Slight bonus for empties on own side that face opponent stones (capture
    # potential): if we have an empty pit with a non-empty opposite, that's
    # a future steal target.
    for p in pits_of(player):
        if board.pits[p] == 0 and board.pits[_OPPOSITE[p]] > 0:
            base += 1
    return base


def _alphabeta(board: Board, depth: int, alpha: int, beta: int,
               to_move: int, root_player: int, tt: dict) -> int:
    key = (board.key(), depth, to_move)
    cached = tt.get(key)
    if cached is not None:
        return cached

    if board.is_game_over():
        s_root = board.pits[store_of(root_player)]
        s_opp = board.pits[store_of(other(root_player))]
        diff = s_root - s_opp
        if diff > 0:
            score = _WIN_SCORE + diff + depth
        elif diff < 0:
            score = -_WIN_SCORE + diff - depth
        else:
            score = 0
        tt[key] = score
        return score
    if depth == 0:
        score = _evaluate(board, root_player)
        tt[key] = score
        return score

    moves = board.legal_moves(to_move)
    if not moves:
        # Pass turn to opponent (rare: only happens after a free turn that
        # left no legal moves, which would have ended the game already).
        score = _alphabeta(board, depth, alpha, beta,
                           other(to_move), root_player, tt)
        tt[key] = score
        return score

    if to_move == root_player:
        value = -10**9
        for pit in moves:
            child = board.copy()
            res = child.move(pit)
            # Same player goes again on a free turn.
            next_to_move = (to_move if res['free_turn']
                            and not res['game_over'] else other(to_move))
            v = _alphabeta(child, depth - 1, alpha, beta,
                           next_to_move, root_player, tt)
            if v > value:
                value = v
            if value > alpha:
                alpha = value
            if alpha >= beta:
                break
    else:
        value = 10**9
        for pit in moves:
            child = board.copy()
            res = child.move(pit)
            next_to_move = (to_move if res['free_turn']
                            and not res['game_over'] else other(to_move))
            v = _alphabeta(child, depth - 1, alpha, beta,
                           next_to_move, root_player, tt)
            if v < value:
                value = v
            if value < beta:
                beta = value
            if alpha >= beta:
                break

    tt[key] = value
    return value


def ai_move(board: Board, player: int, depth: int = 4) -> int:
    """Return the AI's chosen pit index for ``player``."""
    moves = board.legal_moves(player)
    if not moves:
        raise ValueError('No legal moves available.')
    if len(moves) == 1:
        return moves[0]

    tt: dict = {}
    best_pit = moves[0]
    best_val = -10**9
    alpha, beta = -10**9, 10**9

    for pit in moves:
        child = board.copy()
        res = child.move(pit)
        next_to_move = (player if res['free_turn']
                        and not res['game_over'] else other(player))
        val = _alphabeta(child, depth - 1, alpha, beta,
                         next_to_move, player, tt)
        if val > best_val:
            best_val = val
            best_pit = pit
        if val > alpha:
            alpha = val
    return best_pit


# --- CLI ---------------------------------------------------------------------


def _ask_mode() -> tuple[bool, int, bool]:
    """Returns (vs_ai, ai_depth, awari)."""
    print('\nMode:')
    print('  1) Two players (hot-seat)')
    print('  2) vs AI — Easy   (depth 2)')
    print('  3) vs AI — Medium (depth 4)')
    print('  4) vs AI — Hard   (depth 6)')
    print('  5) vs AI — Expert (depth 7)')
    while True:
        choice = input('> ').strip()
        if choice in ('1', '2', '3', '4', '5'):
            break
        print('Enter 1, 2, 3, 4, or 5.')
    vs_ai = choice != '1'
    depth = {'2': 2, '3': 4, '4': 6, '5': 7}.get(choice, 0)

    awari_in = input('Awari variant (no extra-turn rule)? [y/N] ').strip().lower()
    awari = awari_in.startswith('y')
    return vs_ai, depth, awari


def _ask_pit(board: Board, player: int) -> int:
    """Prompts the player for a pit (1-6) and returns the 0-indexed pit."""
    legal = board.legal_moves(player)
    legal_labels = sorted(legal_labels_for(player, legal))
    while True:
        raw = input(f'Player {player} — pit '
                    f'[{",".join(legal_labels)}, q to quit]: ').strip().lower()
        if raw in ('q', 'quit', 'exit'):
            print('Bye!')
            sys.exit(0)
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= 6:
                pit = n - 1 if player == PLAYER_1 else (12 - (n - 1))
                if pit in legal:
                    return pit
                print('That pit is empty — choose another.')
                continue
        print('Enter 1..6 or q to quit.')


def legal_labels_for(player: int, legal: list[int]) -> list[str]:
    """Convert internal indices to user-facing 1..6 labels."""
    out = []
    for p in legal:
        if player == PLAYER_1:
            out.append(str(P1_PITS.index(p) + 1))
        else:
            # P2 pits 7..12 map to user labels 1..6 (mirrored).
            out.append(str(6 - P2_PITS.index(p)))
    return out


def main() -> None:
    print('Mancala (Kalah)')
    print('===============')
    print('Sow stones counter-clockwise. Free turn if last stone in your store.')
    print('Capture if last stone lands in your own empty pit.')

    while True:
        vs_ai, depth, awari = _ask_mode()
        board = Board(awari=awari)
        if awari:
            print('Awari variant: no extra-turn rule.')
        ai_player = PLAYER_2 if vs_ai else None
        current = PLAYER_1

        while not board.is_game_over():
            print()
            print(board)
            if vs_ai and current == ai_player:
                print(f'AI thinking (depth={depth})...')
                pit = ai_move(board, current, depth=depth)
                # Display label for AI move.
                label = legal_labels_for(current, [pit])[0]
                print(f'AI plays pit {label}.')
            else:
                pit = _ask_pit(board, current)
            res = board.move(pit)
            if res['capture']:
                cap = res['capture']
                print(f'  → Capture! +{cap["stones"]} to P{current} store.')
            if res['free_turn'] and not res['game_over']:
                print('  → Free turn!')
            if res['game_over']:
                print()
                print(board)
                if res['sweep']:
                    print(f'Sweep: P1 +{res["sweep"]["p1"]}, '
                          f'P2 +{res["sweep"]["p2"]}.')
                w = res['winner']
                if w == 0:
                    print("It's a draw.")
                elif vs_ai and w == ai_player:
                    print('AI wins!')
                else:
                    print(f'Player {w} wins!  '
                          f'({board.score(PLAYER_1)}-{board.score(PLAYER_2)})')
                break
            current = res['next_player']

        again = input('\nPlay again? (y/n) ').strip().lower()
        if not again.startswith('y'):
            print('Thanks for playing!')
            break


if __name__ == '__main__':
    main()
