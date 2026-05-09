"""Sudoku — generate, solve, and play 9x9 puzzles.

Pure-stdlib core used by the GUI and TUI front-ends.

Run:
    uv run python sudoku/sudoku.py
"""
from __future__ import annotations

import argparse
import copy
import random
from dataclasses import dataclass, field
from typing import Iterable, Optional

SIZE = 9          # board side
BOX = 3           # box side
DIGITS = range(1, SIZE + 1)
EMPTY = 0

# How many cells are *given* (revealed) at puzzle start, per difficulty.
# Lower => harder. These are the standard ranges seen in print sudoku books.
DIFFICULTY_GIVENS = {
    'easy':   40,
    'medium': 32,
    'hard':   26,
}


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------

@dataclass
class Board:
    """A 9x9 sudoku board. ``grid[r][c] == 0`` means empty.

    ``givens`` records the cells that were filled when the puzzle was
    handed to the player — front-ends use it to render those cells in a
    distinguishable color and reject edits to them.
    """

    grid: list[list[int]]
    givens: set[tuple[int, int]] = field(default_factory=set)

    # ---- construction ----------------------------------------------------

    @classmethod
    def empty(cls) -> 'Board':
        return cls(grid=[[EMPTY] * SIZE for _ in range(SIZE)])

    def clone(self) -> 'Board':
        return Board(grid=copy.deepcopy(self.grid), givens=set(self.givens))

    # ---- access ----------------------------------------------------------

    def get(self, r: int, c: int) -> int:
        return self.grid[r][c]

    def set(self, r: int, c: int, value: int) -> None:
        self.grid[r][c] = value

    def is_given(self, r: int, c: int) -> bool:
        return (r, c) in self.givens

    def empty_cells(self) -> list[tuple[int, int]]:
        return [(r, c) for r in range(SIZE) for c in range(SIZE)
                if self.grid[r][c] == EMPTY]

    # ---- pretty-print ----------------------------------------------------

    def __str__(self) -> str:
        return format_board(self)


# ---------------------------------------------------------------------------
# Validity checks
# ---------------------------------------------------------------------------

def _peer_values(grid: list[list[int]], r: int, c: int) -> set[int]:
    """Set of digits already used in the row, column, and 3x3 box of (r,c)."""
    used: set[int] = set()
    for i in range(SIZE):
        used.add(grid[r][i])
        used.add(grid[i][c])
    br, bc = (r // BOX) * BOX, (c // BOX) * BOX
    for i in range(BOX):
        for j in range(BOX):
            used.add(grid[br + i][bc + j])
    used.discard(EMPTY)
    return used


def candidates(board: Board, r: int, c: int) -> list[int]:
    """Digits that could legally go in (r, c) right now."""
    if board.grid[r][c] != EMPTY:
        return []
    used = _peer_values(board.grid, r, c)
    return [d for d in DIGITS if d not in used]


def is_valid(board: Board) -> bool:
    """True if no row/column/box contains a duplicate digit.

    Empty cells are ignored, so a partial board is valid as long as the
    filled cells are consistent.
    """
    grid = board.grid
    for i in range(SIZE):
        if not _no_dup(grid[i]):
            return False
        if not _no_dup([grid[r][i] for r in range(SIZE)]):
            return False
    for br in range(0, SIZE, BOX):
        for bc in range(0, SIZE, BOX):
            block = [grid[br + i][bc + j]
                     for i in range(BOX) for j in range(BOX)]
            if not _no_dup(block):
                return False
    return True


def _no_dup(values: Iterable[int]) -> bool:
    seen: set[int] = set()
    for v in values:
        if v == EMPTY:
            continue
        if v in seen:
            return False
        seen.add(v)
    return True


def is_solved(board: Board) -> bool:
    """True if every cell is filled *and* the board is valid."""
    if any(board.grid[r][c] == EMPTY
           for r in range(SIZE) for c in range(SIZE)):
        return False
    return is_valid(board)


def hints_remaining(board: Board) -> int:
    """Number of empty cells still to fill."""
    return sum(1 for r in range(SIZE) for c in range(SIZE)
               if board.grid[r][c] == EMPTY)


# ---------------------------------------------------------------------------
# Backtracking solver with MRV (minimum remaining values) heuristic
# ---------------------------------------------------------------------------

def _select_mrv_cell(grid: list[list[int]]) -> tuple[Optional[tuple[int, int]],
                                                     list[int]]:
    """Pick the empty cell with the fewest legal candidates (MRV).

    Returns (cell, candidates). If no empty cells remain, returns
    ``(None, [])``. If a cell has zero candidates, returns it immediately
    (signals an immediate dead-end so we can prune).
    """
    best_cell: Optional[tuple[int, int]] = None
    best_cands: list[int] = []
    best_n = SIZE + 1
    for r in range(SIZE):
        for c in range(SIZE):
            if grid[r][c] != EMPTY:
                continue
            used = _peer_values(grid, r, c)
            cands = [d for d in DIGITS if d not in used]
            n = len(cands)
            if n == 0:
                return (r, c), []
            if n < best_n:
                best_n = n
                best_cell = (r, c)
                best_cands = cands
                if n == 1:
                    return best_cell, best_cands
    return best_cell, best_cands


def solve(board: Board) -> bool:
    """Solve ``board`` in place using backtracking + MRV. Returns True on
    success (board is fully filled) and False if the puzzle is unsolvable.
    """
    return _solve_recursive(board.grid)


def _solve_recursive(grid: list[list[int]]) -> bool:
    cell, cands = _select_mrv_cell(grid)
    if cell is None:
        return True  # no empty cells — solved
    if not cands:
        return False  # dead end
    r, c = cell
    for d in cands:
        grid[r][c] = d
        if _solve_recursive(grid):
            return True
        grid[r][c] = EMPTY
    return False


def count_solutions(board: Board, limit: int = 2) -> int:
    """Count solutions up to ``limit``. Used to verify uniqueness during
    puzzle generation (limit=2 is enough — if we find a 2nd solution the
    puzzle is rejected). Operates on a copy so the caller's board is
    untouched.
    """
    grid = copy.deepcopy(board.grid)
    counter = [0]
    _count_recursive(grid, counter, limit)
    return counter[0]


def _count_recursive(grid: list[list[int]], counter: list[int],
                     limit: int) -> None:
    if counter[0] >= limit:
        return
    cell, cands = _select_mrv_cell(grid)
    if cell is None:
        counter[0] += 1
        return
    if not cands:
        return
    r, c = cell
    for d in cands:
        grid[r][c] = d
        _count_recursive(grid, counter, limit)
        if counter[0] >= limit:
            grid[r][c] = EMPTY
            return
        grid[r][c] = EMPTY


def find_one_empty_solution(board: Board, rng: random.Random) -> bool:
    """Fill an empty (or partial) board with a single random valid
    completion. Used by ``generate`` as the seed step. Mutates ``board``.
    """
    return _fill_random(board.grid, rng)


def _fill_random(grid: list[list[int]], rng: random.Random) -> bool:
    cell, cands = _select_mrv_cell(grid)
    if cell is None:
        return True
    if not cands:
        return False
    r, c = cell
    rng.shuffle(cands)
    for d in cands:
        grid[r][c] = d
        if _fill_random(grid, rng):
            return True
        grid[r][c] = EMPTY
    return False


# ---------------------------------------------------------------------------
# Generation — start from a fully solved grid then carve cells out
# ---------------------------------------------------------------------------

def generate(difficulty: str = 'easy',
             rng: Optional[random.Random] = None) -> Board:
    """Generate a sudoku puzzle with a unique solution.

    Strategy:
      1. Seed an empty board and fill it with one random valid completion
         (``_fill_random``). This is our solution grid.
      2. Walk the 81 cells in random order; tentatively blank each one.
         Re-test uniqueness with ``count_solutions(limit=2)``. If two
         solutions appear, restore the digit and skip this cell.
      3. Stop when the number of remaining givens hits the target for the
         requested difficulty (or no more cells can be removed safely).
    """
    if difficulty not in DIFFICULTY_GIVENS:
        raise ValueError(
            f'difficulty must be one of {list(DIFFICULTY_GIVENS)}, '
            f'got {difficulty!r}')
    if rng is None:
        rng = random.Random()

    target_givens = DIFFICULTY_GIVENS[difficulty]

    # Step 1 — full solution.
    solution = Board.empty()
    if not _fill_random(solution.grid, rng):
        # Should be unreachable for an empty 9x9 — every empty grid is
        # solvable — but fall back gracefully.
        raise RuntimeError('failed to seed solution grid')

    puzzle = solution.clone()
    cells = [(r, c) for r in range(SIZE) for c in range(SIZE)]
    rng.shuffle(cells)

    givens = SIZE * SIZE
    for r, c in cells:
        if givens <= target_givens:
            break
        saved = puzzle.grid[r][c]
        puzzle.grid[r][c] = EMPTY
        if count_solutions(puzzle, limit=2) != 1:
            # Removing this cell would create ambiguity — put it back.
            puzzle.grid[r][c] = saved
        else:
            givens -= 1

    puzzle.givens = {(r, c) for r in range(SIZE) for c in range(SIZE)
                     if puzzle.grid[r][c] != EMPTY}
    return puzzle


# ---------------------------------------------------------------------------
# Pretty printing for the CLI
# ---------------------------------------------------------------------------

def format_board(board: Board) -> str:
    """Render board with 3x3 box separators. Uses '.' for empty cells.

    Output looks like:

        . 4 7 | . 9 . | 5 . 6
        . 6 . | . . 8 | 3 . .
        . . 5 | 2 . . | . . .
        ------+-------+------
        ...
    """
    lines: list[str] = []
    for r in range(SIZE):
        if r > 0 and r % BOX == 0:
            lines.append('------+-------+------')
        cells: list[str] = []
        for c in range(SIZE):
            if c > 0 and c % BOX == 0:
                cells.append('|')
            v = board.grid[r][c]
            cells.append(str(v) if v != EMPTY else '.')
        lines.append(' '.join(cells))
    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_cell(text: str) -> Optional[tuple[int, int, int]]:
    """Parse ``r c d`` (1-indexed). Returns 0-indexed (r, c, d) or None."""
    parts = text.replace(',', ' ').split()
    if len(parts) != 3:
        return None
    try:
        r, c, d = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if not (1 <= r <= SIZE and 1 <= c <= SIZE and 0 <= d <= SIZE):
        return None
    return r - 1, c - 1, d


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Generate and play a 9x9 sudoku puzzle.')
    parser.add_argument(
        '--difficulty', '-d', default='easy',
        choices=list(DIFFICULTY_GIVENS),
        help='puzzle difficulty (default: easy)')
    parser.add_argument(
        '--seed', type=int, default=None,
        help='random seed for reproducible puzzles')
    parser.add_argument(
        '--solve-only', action='store_true',
        help='print a generated puzzle and its solution, then exit')
    args = parser.parse_args()

    rng = random.Random(args.seed)
    board = generate(args.difficulty, rng)

    print(f'Sudoku — difficulty: {args.difficulty}'
          f' ({len(board.givens)} givens)')
    print(board)

    if args.solve_only:
        solution = board.clone()
        if solve(solution):
            print('\nSolution:')
            print(solution)
        else:
            print('\n(unsolvable — this should not happen)')
        return

    print('\nCommands:')
    print('  r c d   place digit d in row r, column c (1-9; 0 to clear)')
    print('  solve   reveal the solution')
    print('  hint    fill one cell using the solver')
    print('  reset   clear your moves (givens stay)')
    print('  quit    exit')

    initial = board.clone()

    while True:
        try:
            line = input('\n> ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line:
            continue
        if line in ('q', 'quit', 'exit'):
            return
        if line == 'reset':
            board = initial.clone()
            print(board)
            continue
        if line == 'solve':
            solution = board.clone()
            if solve(solution):
                print(solution)
                print('Solved.')
            else:
                print('No solution exists — your moves contradict.')
            continue
        if line == 'hint':
            solution = board.clone()
            if not solve(solution):
                print('No solution from current state — undo a move.')
                continue
            empties = board.empty_cells()
            if not empties:
                print('Already complete!')
                continue
            r, c = rng.choice(empties)
            board.set(r, c, solution.grid[r][c])
            print(f'Hint: row {r + 1}, col {c + 1} = {solution.grid[r][c]}')
            print(board)
            continue

        parsed = _parse_cell(line)
        if parsed is None:
            print('Could not parse — try "5 3 7" or "solve" / "hint" / "quit".')
            continue
        r, c, d = parsed
        if board.is_given(r, c):
            print('That cell is a given — pick another.')
            continue
        board.set(r, c, d)
        print(board)
        if is_solved(board):
            print('\nYou solved it!')
            return
        print(f'{hints_remaining(board)} cells left.')


if __name__ == '__main__':
    main()
