"""Sliding Tile Puzzle (15-puzzle / N-puzzle).

Classic sliding tile puzzle: an n*n grid contains the numbers 1..n*n-1 plus a
single blank cell. Slide tiles into the blank to recover the goal arrangement
(numbers in order with blank in the bottom-right).

This module is the pure / reusable layer:

* `Puzzle` — board state, legal moves, slide(), shuffle(), is_solved(), state().
* `manhattan()` — admissible Manhattan-distance heuristic used by the solver.
* `solve()` — A* search returning a list of directions, or `[]` if unreachable.
* `inversion_count()` / `is_solvable()` — solvability via inversion-count parity.
* `main()` — the CLI entry point.

Run:
    uv run python sliding_puzzle/sliding_puzzle.py

Tags: puzzle, search, a-star, heuristic, manhattan
"""
from __future__ import annotations

import heapq
import random
import sys
from typing import Iterable, Iterator

# Directions describe which way the BLANK moves on the grid. Sliding a tile
# UP means the blank swaps DOWN with that tile — but exposing the action from
# the blank's perspective keeps the math symmetric and the UI explainable
# ("I moved the blank up").
UP, DOWN, LEFT, RIGHT = 'up', 'down', 'left', 'right'
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)
OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}
DELTAS = {UP: (-1, 0), DOWN: (1, 0), LEFT: (0, -1), RIGHT: (0, 1)}


class Puzzle:
    """An n*n sliding tile puzzle.

    Tiles are numbered 1..n*n-1; the blank is 0. Internally the board is a
    flat tuple of length n*n in row-major order — cheap to hash, cheap to
    copy, and friendly to A*'s closed set.
    """

    def __init__(self, n: int = 4, tiles: Iterable[int] | None = None) -> None:
        if n < 2:
            raise ValueError('n must be >= 2')
        self.n = n
        if tiles is None:
            tiles = list(range(1, n * n)) + [0]
        tiles = tuple(tiles)
        if len(tiles) != n * n or sorted(tiles) != list(range(n * n)):
            raise ValueError(f'tiles must be a permutation of 0..{n*n - 1}')
        self._tiles: tuple[int, ...] = tiles
        self._blank: int = tiles.index(0)
        self.moves: int = 0

    # ------------------------------------------------------------------ state

    def state(self) -> tuple[int, ...]:
        """Flat row-major snapshot — hashable, comparable, copy-cheap."""
        return self._tiles

    def grid(self) -> list[list[int]]:
        """2D nested-list view; convenient for renderers."""
        n = self.n
        return [list(self._tiles[r * n:(r + 1) * n]) for r in range(n)]

    def blank(self) -> tuple[int, int]:
        """`(row, col)` of the blank cell."""
        return divmod(self._blank, self.n)

    def is_solved(self) -> bool:
        n = self.n
        return self._tiles == tuple(range(1, n * n)) + (0,)

    # ------------------------------------------------------------------ moves

    def legal_moves(self) -> list[str]:
        """Directions the blank can move (== which side has a tile to slide)."""
        r, c = self.blank()
        out: list[str] = []
        if r > 0:
            out.append(UP)
        if r < self.n - 1:
            out.append(DOWN)
        if c > 0:
            out.append(LEFT)
        if c < self.n - 1:
            out.append(RIGHT)
        return out

    def slide(self, direction: str) -> bool:
        """Move the blank one step. Returns False if the move is illegal."""
        if direction not in DELTAS:
            raise ValueError(f'unknown direction: {direction}')
        dr, dc = DELTAS[direction]
        r, c = self.blank()
        nr, nc = r + dr, c + dc
        if not (0 <= nr < self.n and 0 <= nc < self.n):
            return False
        n = self.n
        new_blank = nr * n + nc
        tiles = list(self._tiles)
        tiles[self._blank], tiles[new_blank] = tiles[new_blank], tiles[self._blank]
        self._tiles = tuple(tiles)
        self._blank = new_blank
        self.moves += 1
        return True

    # ----------------------------------------------------------------- shuffle

    def shuffle(self, rng: random.Random | None = None, moves: int = 200) -> None:
        """Random-walk shuffle.

        Performs `moves` legal slides starting from the current state, never
        immediately undoing the previous one. This guarantees the resulting
        position is reachable from the goal — i.e. always solvable — without
        needing parity reasoning. Move counter is reset to 0 after shuffling.
        """
        if rng is None:
            rng = random.Random()
        last: str | None = None
        for _ in range(max(0, moves)):
            options = [d for d in self.legal_moves() if d != OPPOSITE.get(last or '')]
            choice = rng.choice(options)
            self.slide(choice)
            last = choice
        # Edge case: the random walk happened to land back on the goal.
        if self.is_solved():
            # Force one extra non-trivial move so callers always get a puzzle.
            opts = [d for d in self.legal_moves() if d != OPPOSITE.get(last or '')]
            self.slide(rng.choice(opts) if opts else self.legal_moves()[0])
        self.moves = 0

    # ----------------------------------------------------------------- helpers

    def copy(self) -> 'Puzzle':
        twin = Puzzle.__new__(Puzzle)
        twin.n = self.n
        twin._tiles = self._tiles
        twin._blank = self._blank
        twin.moves = self.moves
        return twin

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Puzzle) and self.n == other.n \
            and self._tiles == other._tiles

    def __hash__(self) -> int:
        return hash((self.n, self._tiles))

    def __repr__(self) -> str:
        return f'Puzzle(n={self.n}, tiles={self._tiles})'

    def render(self) -> str:
        """Pretty ASCII rendering of the board."""
        n = self.n
        width = len(str(n * n - 1))
        out: list[str] = []
        sep = '+' + ('-' * (width + 2) + '+') * n
        for r in range(n):
            out.append(sep)
            row = '|'
            for c in range(n):
                v = self._tiles[r * n + c]
                cell = ' ' * width if v == 0 else str(v).rjust(width)
                row += f' {cell} |'
            out.append(row)
        out.append(sep)
        return '\n'.join(out)


# ---------------------------------------------------------------- solvability

def inversion_count(tiles: Iterable[int]) -> int:
    """Count pairs (i, j) with i < j and tiles[i] > tiles[j], ignoring blank."""
    seq = [t for t in tiles if t != 0]
    inv = 0
    for i in range(len(seq)):
        a = seq[i]
        for j in range(i + 1, len(seq)):
            if a > seq[j]:
                inv += 1
    return inv


def is_solvable(puzzle: 'Puzzle') -> bool:
    """Inversion-count parity test (Johnson-Story 1879).

    Each legal blank move changes the *row* of the blank by 0 (horizontal
    moves) or 1 (vertical moves); a vertical move jumps a tile across `n-1`
    other tiles and flips the inversion-count parity by an odd amount,
    while a horizontal move preserves it. So the value
    ``inversions + blank_row_from_bottom_1indexed`` keeps a constant parity
    along any sequence of legal moves.

    The goal state has inv = 0 and the blank in the bottom row
    (``blank_row_from_bottom_1indexed = 1``), so:

    * Even n: solvable iff ``(inv + blank_row_from_bottom_1) % 2 == 1``.
    * Odd n: vertical moves cross an even number of tiles, so they preserve
      inv parity; the test collapses to "inversions even ⇒ solvable".

    `Puzzle.shuffle()` uses a legal-move random walk so all shuffled puzzles
    pass this check by construction; the function is exposed for users who
    construct boards manually or want to verify the invariant.
    """
    n = puzzle.n
    inv = inversion_count(puzzle.state())
    if n % 2 == 1:
        return inv % 2 == 0
    blank_row_from_bottom_1 = n - puzzle.blank()[0]
    return (inv + blank_row_from_bottom_1) % 2 == 1


# ----------------------------------------------------------------- heuristic

def manhattan(state: tuple[int, ...], n: int) -> int:
    """Sum of |row distances| + |col distances| of each non-blank tile.

    Admissible (never overestimates) and consistent — A* with this heuristic
    finds optimal solutions and never re-expands a closed node.
    """
    total = 0
    for idx, value in enumerate(state):
        if value == 0:
            continue
        # Goal position of tile `value`: index `value - 1` (0-based).
        goal = value - 1
        gr, gc = divmod(goal, n)
        cr, cc = divmod(idx, n)
        total += abs(gr - cr) + abs(gc - cc)
    return total


# ------------------------------------------------------------------- A* solve

def _neighbors(state: tuple[int, ...], n: int) -> Iterator[tuple[str, tuple[int, ...]]]:
    blank = state.index(0)
    r, c = divmod(blank, n)
    for direction, (dr, dc) in DELTAS.items():
        nr, nc = r + dr, c + dc
        if not (0 <= nr < n and 0 <= nc < n):
            continue
        nb = nr * n + nc
        new = list(state)
        new[blank], new[nb] = new[nb], new[blank]
        yield direction, tuple(new)


def solve(puzzle: 'Puzzle', max_expansions: int = 1_000_000) -> list[str]:
    """A* with Manhattan-distance heuristic. Returns directions for the blank.

    Returns `[]` if already solved, or if the search budget is exhausted.
    For n=3 (8-puzzle) this terminates in milliseconds; for n=4 (15-puzzle)
    most random shuffles solve in well under a second, but pathological ones
    can take tens of millions of expansions — hence the budget.
    """
    n = puzzle.n
    start = puzzle.state()
    goal = tuple(range(1, n * n)) + (0,)
    if start == goal:
        return []

    # Open set: (f, tie, g, state, parent_state, action). Tie counter keeps the
    # heap stable even when two entries have the same f-score.
    tie = 0
    open_heap: list[tuple[int, int, int, tuple[int, ...], tuple[int, ...] | None, str | None]] = []
    heapq.heappush(open_heap, (manhattan(start, n), tie, 0, start, None, None))

    came_from: dict[tuple[int, ...], tuple[tuple[int, ...] | None, str | None]] = {start: (None, None)}
    g_score: dict[tuple[int, ...], int] = {start: 0}
    expansions = 0

    while open_heap:
        f, _, g, state, _parent, _act = heapq.heappop(open_heap)
        if state == goal:
            return _reconstruct(came_from, state)
        if g > g_score[state]:
            continue  # stale entry
        expansions += 1
        if expansions > max_expansions:
            return []
        for direction, neighbor in _neighbors(state, n):
            ng = g + 1
            if ng < g_score.get(neighbor, sys.maxsize):
                g_score[neighbor] = ng
                came_from[neighbor] = (state, direction)
                tie += 1
                heapq.heappush(open_heap,
                               (ng + manhattan(neighbor, n), tie, ng,
                                neighbor, state, direction))
    return []


def _reconstruct(came_from: dict, end: tuple[int, ...]) -> list[str]:
    actions: list[str] = []
    cur = end
    while True:
        parent, action = came_from[cur]
        if parent is None:
            break
        actions.append(action)  # type: ignore[arg-type]
        cur = parent
    return list(reversed(actions))


def hint(puzzle: 'Puzzle') -> str | None:
    """Return the next optimal blank-move direction, or None if solved/stuck."""
    if puzzle.is_solved():
        return None
    plan = solve(puzzle)
    return plan[0] if plan else None


# ------------------------------------------------------------------------ CLI

WASD = {'w': UP, 's': DOWN, 'a': LEFT, 'd': RIGHT}


def _default_shuffle(n: int) -> int:
    """Shuffle depth tuned per board size so A* hints stay responsive."""
    if n == 3:
        return 60
    if n == 4:
        return 40
    return 80  # n=5 and beyond — A* won't solve these, but the puzzle plays.


def main() -> None:
    print('Sliding Tile Puzzle')
    print('-------------------')
    print('Pick a board size: 3 (8-puzzle), 4 (15-puzzle, default), or 5.')
    raw = input('n> ').strip()
    try:
        n = int(raw) if raw else 4
    except ValueError:
        n = 4
    n = max(3, min(5, n))

    rng = random.Random()
    puzzle = Puzzle(n)
    puzzle.shuffle(rng, moves=_default_shuffle(n))

    print()
    print('Slide tiles into the blank. The blank moves with W/A/S/D.')
    print('Commands: w/a/s/d move, h hint, n new puzzle, p inversion parity,')
    print('          r reset (re-shuffle), q quit.')
    print()

    while True:
        print(puzzle.render())
        if puzzle.is_solved():
            print(f'\nSolved in {puzzle.moves} moves! Type n for a new puzzle, q to quit.')
        choice = input(f'[{puzzle.moves}]> ').strip().lower()
        if not choice:
            continue
        if choice in ('q', 'quit', 'exit'):
            print('Bye.')
            return
        if choice == 'n':
            puzzle = Puzzle(n)
            puzzle.shuffle(rng, moves=_default_shuffle(n))
            continue
        if choice == 'r':
            puzzle.shuffle(rng, moves=_default_shuffle(n))
            continue
        if choice == 'p':
            inv = inversion_count(puzzle.state())
            ok = is_solvable(puzzle)
            print(f'inversions = {inv}, solvable = {ok}')
            continue
        if choice == 'h':
            nxt = hint(puzzle)
            if nxt is None:
                print('(already solved)')
            else:
                print(f'hint: move blank {nxt}')
            continue
        if choice in WASD:
            if not puzzle.slide(WASD[choice]):
                print('blocked — edge of the board')
            continue
        print('?')


if __name__ == '__main__':
    main()
