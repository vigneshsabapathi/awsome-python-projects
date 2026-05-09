"""Four in a Row (Connect Four) — CLI + shared game logic.

A 7-column, 6-row drop-disc game. Two players alternate dropping discs;
first to align four in a row (horizontal, vertical, or diagonal) wins.

This module also exposes:

- ``Board`` — pure game state with ``drop``, ``winner``, ``is_full``, etc.
- ``ai_move`` — minimax with alpha-beta pruning + transposition table.

Run:
    uv run python four_in_a_row/four_in_a_row.py
"""
from __future__ import annotations

import sys
from typing import Optional

# --- Constants ---------------------------------------------------------------

COLS = 7
ROWS = 6
EMPTY = 0
PLAYER_1 = 1
PLAYER_2 = 2
WIN_LEN = 4

# Difficulty -> minimax depth.
DIFFICULTY_DEPTH = {
    'easy': 2,
    'medium': 4,
    'hard': 6,
}

# Direction vectors used for win-detection / scoring (dr, dc).
_DIRECTIONS = (
    (0, 1),   # horizontal
    (1, 0),   # vertical
    (1, 1),   # diagonal down-right
    (1, -1),  # diagonal down-left
)


# --- Board -------------------------------------------------------------------


class Board:
    """7x6 Connect Four board.

    ``grid[row][col]``: row 0 is the top row, row ROWS-1 is the bottom row.
    A drop in column ``c`` settles at the lowest empty row of that column.
    """

    __slots__ = ('grid',)

    def __init__(self, grid: Optional[list[list[int]]] = None) -> None:
        if grid is None:
            self.grid = [[EMPTY] * COLS for _ in range(ROWS)]
        else:
            self.grid = [row[:] for row in grid]

    # -- Core ops ------------------------------------------------------------

    def copy(self) -> 'Board':
        return Board(self.grid)

    def is_full(self) -> bool:
        return all(self.grid[0][c] != EMPTY for c in range(COLS))

    def available_cols(self) -> list[int]:
        """Columns with at least one empty slot, ordered center-out.

        Center-out ordering helps alpha-beta pruning: stronger moves are
        likely near the center, so we expand them first to maximize cutoffs.
        """
        center = COLS // 2
        order = sorted(range(COLS), key=lambda c: abs(c - center))
        return [c for c in order if self.grid[0][c] == EMPTY]

    def next_open_row(self, col: int) -> Optional[int]:
        """Return the row a disc dropped in ``col`` would land in, or None."""
        if not 0 <= col < COLS:
            return None
        for r in range(ROWS - 1, -1, -1):
            if self.grid[r][col] == EMPTY:
                return r
        return None

    def drop(self, col: int, player: int) -> Optional[int]:
        """Drop a disc into ``col`` for ``player``. Returns landing row or None."""
        if player not in (PLAYER_1, PLAYER_2):
            raise ValueError(f'player must be 1 or 2, got {player!r}')
        row = self.next_open_row(col)
        if row is None:
            return None
        self.grid[row][col] = player
        return row

    def undo(self, col: int) -> None:
        """Remove the topmost disc from ``col`` (used by the AI search)."""
        for r in range(ROWS):
            if self.grid[r][col] != EMPTY:
                self.grid[r][col] = EMPTY
                return

    # -- Win detection -------------------------------------------------------

    def winner(self) -> Optional[int]:
        """Return the winning player (1 or 2), or None if no winner yet."""
        line = self._winning_line()
        if line is None:
            return None
        r, c, _, _ = line
        return self.grid[r][c]

    def winning_line(self) -> Optional[list[tuple[int, int]]]:
        """Return the 4 cells forming the win, or None."""
        line = self._winning_line()
        if line is None:
            return None
        r, c, dr, dc = line
        return [(r + i * dr, c + i * dc) for i in range(WIN_LEN)]

    def _winning_line(self) -> Optional[tuple[int, int, int, int]]:
        g = self.grid
        for r in range(ROWS):
            for c in range(COLS):
                p = g[r][c]
                if p == EMPTY:
                    continue
                for dr, dc in _DIRECTIONS:
                    end_r = r + (WIN_LEN - 1) * dr
                    end_c = c + (WIN_LEN - 1) * dc
                    if not (0 <= end_r < ROWS and 0 <= end_c < COLS):
                        continue
                    if all(g[r + i * dr][c + i * dc] == p
                           for i in range(1, WIN_LEN)):
                        return (r, c, dr, dc)
        return None

    # -- Misc ----------------------------------------------------------------

    def __str__(self) -> str:
        glyph = {EMPTY: '.', PLAYER_1: 'X', PLAYER_2: 'O'}
        rows = ['|' + '|'.join(glyph[v] for v in row) + '|'
                for row in self.grid]
        header = ' ' + ' '.join(str(c + 1) for c in range(COLS))
        return '\n'.join([header, *rows])

    def key(self) -> tuple:
        """Hashable snapshot for the transposition table."""
        return tuple(tuple(row) for row in self.grid)


# --- AI: minimax + alpha-beta + transposition table -------------------------


_WIN_SCORE = 10_000_000


def other(player: int) -> int:
    return PLAYER_2 if player == PLAYER_1 else PLAYER_1


def _score_window(window: list[int], player: int) -> int:
    """Heuristic for a 4-cell window."""
    opp = other(player)
    pc = window.count(player)
    oc = window.count(opp)
    ec = window.count(EMPTY)

    if pc and oc:
        return 0  # blocked window — neither side can complete it
    if pc == 4:
        return 100_000
    if pc == 3 and ec == 1:
        return 50
    if pc == 2 and ec == 2:
        return 5
    if oc == 4:
        return -100_000
    if oc == 3 and ec == 1:
        return -80  # block-priority slightly higher than offense
    if oc == 2 and ec == 2:
        return -4
    return 0


def _evaluate(board: Board, player: int) -> int:
    """Static board evaluation from ``player``'s perspective."""
    g = board.grid
    score = 0

    # Center-column control bonus.
    center = COLS // 2
    center_count = sum(1 for r in range(ROWS) if g[r][center] == player)
    score += center_count * 6

    # All 4-in-a-row windows in every direction.
    for r in range(ROWS):
        for c in range(COLS):
            for dr, dc in _DIRECTIONS:
                end_r = r + (WIN_LEN - 1) * dr
                end_c = c + (WIN_LEN - 1) * dc
                if not (0 <= end_r < ROWS and 0 <= end_c < COLS):
                    continue
                window = [g[r + i * dr][c + i * dc] for i in range(WIN_LEN)]
                score += _score_window(window, player)
    return score


def _alphabeta(board: Board, depth: int, alpha: int, beta: int,
               to_move: int, root_player: int,
               tt: dict) -> int:
    """Alpha-beta minimax. Score is from ``root_player``'s perspective.

    ``to_move`` is the player about to play. We maximize when
    ``to_move == root_player``, otherwise minimize.
    """
    key = (board.key(), depth, to_move)
    cached = tt.get(key)
    if cached is not None:
        return cached

    win = board.winner()
    if win is not None:
        # Earlier wins (more depth left) score better than later ones.
        if win == root_player:
            score = _WIN_SCORE + depth
        else:
            score = -_WIN_SCORE - depth
        tt[key] = score
        return score
    if board.is_full():
        tt[key] = 0
        return 0
    if depth == 0:
        score = _evaluate(board, root_player)
        tt[key] = score
        return score

    cols = board.available_cols()
    if to_move == root_player:
        value = -10**9
        for col in cols:
            board.drop(col, to_move)
            value = max(value, _alphabeta(board, depth - 1, alpha, beta,
                                          other(to_move), root_player, tt))
            board.undo(col)
            alpha = max(alpha, value)
            if alpha >= beta:
                break  # beta cutoff
    else:
        value = 10**9
        for col in cols:
            board.drop(col, to_move)
            value = min(value, _alphabeta(board, depth - 1, alpha, beta,
                                          other(to_move), root_player, tt))
            board.undo(col)
            beta = min(beta, value)
            if alpha >= beta:
                break  # alpha cutoff

    tt[key] = value
    return value


def ai_move(board: Board, player: int, depth: int = 4) -> int:
    """Return the AI's chosen column for ``player`` using minimax + alpha-beta.

    Includes a transposition table for repeated positions and center-first
    move ordering for stronger pruning.
    """
    cols = board.available_cols()
    if not cols:
        raise ValueError('No available columns — board is full.')

    # Immediate-win shortcut.
    for col in cols:
        b = board.copy()
        b.drop(col, player)
        if b.winner() == player:
            return col

    # Block opponent's immediate win.
    opp = other(player)
    for col in cols:
        b = board.copy()
        b.drop(col, opp)
        if b.winner() == opp:
            return col

    tt: dict = {}
    best_col = cols[0]
    best_val = -10**9
    alpha, beta = -10**9, 10**9

    for col in cols:
        board.drop(col, player)
        val = _alphabeta(board, depth - 1, alpha, beta,
                         other(player), player, tt)
        board.undo(col)
        if val > best_val:
            best_val = val
            best_col = col
        alpha = max(alpha, val)
    return best_col


# --- CLI ---------------------------------------------------------------------


def _glyph(player: int) -> str:
    return {EMPTY: '.', PLAYER_1: 'X', PLAYER_2: 'O'}[player]


def _ask_mode() -> tuple[bool, int]:
    """Returns (vs_ai, ai_depth). ai_depth is unused for 2-player mode."""
    print('\nMode:')
    print('  1) Two players (hot-seat)')
    print('  2) vs AI — Easy   (depth 2)')
    print('  3) vs AI — Medium (depth 4)')
    print('  4) vs AI — Hard   (depth 6)')
    while True:
        choice = input('> ').strip()
        if choice == '1':
            return False, 0
        if choice == '2':
            return True, DIFFICULTY_DEPTH['easy']
        if choice == '3':
            return True, DIFFICULTY_DEPTH['medium']
        if choice == '4':
            return True, DIFFICULTY_DEPTH['hard']
        print('Enter 1, 2, 3, or 4.')


def _ask_column(player: int) -> int:
    glyph = _glyph(player)
    while True:
        raw = input(f'Player {player} ({glyph}) — column [1-7, q to quit]: ').strip().lower()
        if raw in ('q', 'quit', 'exit'):
            print('Bye!')
            sys.exit(0)
        if raw.isdigit():
            col = int(raw) - 1
            if 0 <= col < COLS:
                return col
        print(f'Enter a number 1..{COLS} or q to quit.')


def main() -> None:
    print('Four in a Row')
    print('=============')
    print('Drop discs into columns. First to 4-in-a-row wins.')

    while True:
        vs_ai, depth = _ask_mode()
        board = Board()
        current = PLAYER_1
        ai_player = PLAYER_2 if vs_ai else None

        while True:
            print()
            print(board)

            if vs_ai and current == ai_player:
                print(f'AI thinking (depth={depth})...')
                col = ai_move(board, current, depth=depth)
                print(f'AI plays column {col + 1}.')
            else:
                col = _ask_column(current)

            row = board.drop(col, current)
            if row is None:
                print('That column is full — try another.')
                continue

            win = board.winner()
            if win is not None:
                print()
                print(board)
                if vs_ai and win == ai_player:
                    print('AI wins!')
                else:
                    print(f'Player {win} ({_glyph(win)}) wins!')
                break
            if board.is_full():
                print()
                print(board)
                print("It's a draw.")
                break

            current = other(current)

        again = input('\nPlay again? (y/n) ').strip().lower()
        if not again.startswith('y'):
            print('Thanks for playing!')
            break


if __name__ == '__main__':
    main()
