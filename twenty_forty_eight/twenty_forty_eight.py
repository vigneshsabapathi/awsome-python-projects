"""2048 — sliding-tile combination game.

A 4*4 grid where each move slides every tile in one of four directions; tiles
of equal value that collide merge into a single tile worth their sum, and a
fresh 2 (90 percent) or 4 (10 percent) appears on a random empty cell after
each successful move. The classic goal is to reach the 2048 tile, but the
game keeps going past that until the board locks up.

This module is the pure / reusable layer:

* `Game(rng=None)` — board state, `move(direction)`, `spawn_tile()`,
  `is_won()`, `is_lost()`, `state()`.
* `expectimax_best_move()` — chance-node search used by the auto-play AI.
* `main()` — the CLI entry point with arrow-key controls.

Run:
    uv run python twenty_forty_eight/twenty_forty_eight.py

Tags: game, puzzle, sliding, expectimax, chance-search
"""
from __future__ import annotations

import os
import random
import sys
from typing import Iterable

# Directions describe the way every tile slides. The math is symmetric: the
# board is rotated/transposed into a canonical "slide LEFT" frame, the row
# compress-and-merge happens once, and the result is rotated back. This
# keeps the merge logic in exactly one place.
UP, DOWN, LEFT, RIGHT = 'up', 'down', 'left', 'right'
DIRECTIONS = (UP, DOWN, LEFT, RIGHT)

GRID_SIZE = 4
WIN_TILE = 2048

# Probability the spawn tile is a 2 (vs. a 4) — matches the original game.
P_SPAWN_2 = 0.9
SPAWN_VALUES: tuple[int, ...] = (2, 4)


# ---------------------------------------------------------------- row mechanic

def _compress_left(row: list[int]) -> tuple[list[int], int, int]:
    """Slide non-zero values to the left and merge adjacent equal pairs once.

    Returns ``(new_row, score_delta, merges)`` where ``score_delta`` is the
    sum of every merged tile's *new* value (the standard 2048 score rule)
    and ``merges`` counts the number of merge operations.

    A tile produced by a merge cannot merge again on the same move — the
    classic rule that prevents `[2, 2, 4, 4]` from cascading into a single
    16. We track this with a `merged` flag per output slot.
    """
    n = len(row)
    out = [0] * n
    merged = [False] * n
    score = 0
    merges = 0
    write = 0
    for value in row:
        if value == 0:
            continue
        if write > 0 and out[write - 1] == value and not merged[write - 1]:
            out[write - 1] = value * 2
            merged[write - 1] = True
            score += value * 2
            merges += 1
        else:
            out[write] = value
            write += 1
    return out, score, merges


# --------------------------------------------------------------- grid rotation

def _rotate_cw(grid: list[list[int]]) -> list[list[int]]:
    n = len(grid)
    return [[grid[n - 1 - r][c] for r in range(n)] for c in range(n)]


def _rotate_ccw(grid: list[list[int]]) -> list[list[int]]:
    n = len(grid)
    return [[grid[r][n - 1 - c] for r in range(n)] for c in range(n)]


def _flip_h(grid: list[list[int]]) -> list[list[int]]:
    return [list(reversed(row)) for row in grid]


def _slide(grid: list[list[int]], direction: str) -> tuple[list[list[int]], int, int]:
    """Slide the whole grid in `direction`. Returns (new_grid, score, merges).

    The strategy: re-orient so the move becomes a slide LEFT, run the row
    mechanic on every row, then put it back. Each direction has a single
    pre-rotation and a single inverse-rotation — no edge cases.
    """
    if direction == LEFT:
        oriented = [row[:] for row in grid]
    elif direction == RIGHT:
        oriented = _flip_h(grid)
    elif direction == UP:
        oriented = _rotate_ccw(grid)
    elif direction == DOWN:
        oriented = _rotate_cw(grid)
    else:
        raise ValueError(f'unknown direction: {direction}')

    score_delta = 0
    merges = 0
    new_oriented: list[list[int]] = []
    for row in oriented:
        new_row, sc, mg = _compress_left(row)
        new_oriented.append(new_row)
        score_delta += sc
        merges += mg

    if direction == LEFT:
        result = new_oriented
    elif direction == RIGHT:
        result = _flip_h(new_oriented)
    elif direction == UP:
        result = _rotate_cw(new_oriented)
    else:  # DOWN
        result = _rotate_ccw(new_oriented)
    return result, score_delta, merges


# ------------------------------------------------------------------- the game

class Game:
    """A 4x4 (configurable) game of 2048.

    The model is *pure* — no I/O, no animation, no input — so the same code
    drives the CLI, the GUI, and the TUI front-ends. Construct with a seeded
    `random.Random` for deterministic tests.
    """

    def __init__(self, rng: random.Random | None = None,
                 size: int = GRID_SIZE,
                 *,
                 _grid: list[list[int]] | None = None,
                 _score: int = 0,
                 _moves: int = 0) -> None:
        if size < 2:
            raise ValueError('size must be >= 2')
        self.size = size
        self.rng = rng if rng is not None else random.Random()
        if _grid is None:
            self.grid: list[list[int]] = [[0] * size for _ in range(size)]
            self.score = 0
            self.moves = 0
            # Every fresh game starts with two random tiles, like the original.
            self.spawn_tile()
            self.spawn_tile()
        else:
            self.grid = [row[:] for row in _grid]
            self.score = _score
            self.moves = _moves

    # ------------------------------------------------------------------ state

    def state(self) -> dict:
        """Snapshot dict with grid, score, moves, won/lost flags, max tile."""
        return {
            'grid': [row[:] for row in self.grid],
            'score': self.score,
            'moves': self.moves,
            'size': self.size,
            'max_tile': self.max_tile(),
            'empty': self.empty_cells(),
            'won': self.is_won(),
            'lost': self.is_lost(),
        }

    def max_tile(self) -> int:
        return max((v for row in self.grid for v in row), default=0)

    def empty_cells(self) -> list[tuple[int, int]]:
        return [(r, c) for r in range(self.size)
                for c in range(self.size) if self.grid[r][c] == 0]

    def copy(self) -> 'Game':
        twin = Game.__new__(Game)
        twin.size = self.size
        twin.rng = self.rng
        twin.grid = [row[:] for row in self.grid]
        twin.score = self.score
        twin.moves = self.moves
        return twin

    # ------------------------------------------------------------------ moves

    def move(self, direction: str) -> dict:
        """Apply `direction`. Returns a result dict.

        Result keys: ``moved`` (bool — did anything actually shift?),
        ``score_delta`` (points gained from merges this move),
        ``merges`` (number of merges), ``spawned`` (the (row, col, value)
        tuple of the new tile, or None if the move was a no-op).
        """
        new_grid, score_delta, merges = _slide(self.grid, direction)
        moved = new_grid != self.grid
        spawned: tuple[int, int, int] | None = None
        if moved:
            self.grid = new_grid
            self.score += score_delta
            self.moves += 1
            spawned = self.spawn_tile()
        return {
            'moved': moved,
            'score_delta': score_delta,
            'merges': merges,
            'spawned': spawned,
        }

    def spawn_tile(self) -> tuple[int, int, int] | None:
        """Drop a 2 (p=0.9) or 4 (p=0.1) on a uniformly random empty cell.

        Returns (row, col, value), or None if the board is already full.
        """
        empties = self.empty_cells()
        if not empties:
            return None
        r, c = self.rng.choice(empties)
        # Random.random() < 0.9 — keeps the probability split exactly at 90/10.
        value = 2 if self.rng.random() < P_SPAWN_2 else 4
        self.grid[r][c] = value
        return (r, c, value)

    # ------------------------------------------------------------- win / lose

    def is_won(self) -> bool:
        """True once any tile reaches 2048 — the player can keep going."""
        return self.max_tile() >= WIN_TILE

    def is_lost(self) -> bool:
        """True iff no direction would change the board (i.e. truly stuck)."""
        if self.empty_cells():
            return False
        # Any horizontal or vertical adjacent equal pair means a merge is
        # still possible.
        n = self.size
        for r in range(n):
            for c in range(n):
                v = self.grid[r][c]
                if c + 1 < n and self.grid[r][c + 1] == v:
                    return False
                if r + 1 < n and self.grid[r + 1][c] == v:
                    return False
        return True

    def legal_moves(self) -> list[str]:
        return [d for d in DIRECTIONS
                if _slide(self.grid, d)[0] != self.grid]

    # --------------------------------------------------------------- pretty

    def render(self) -> str:
        """Pretty ASCII rendering for the CLI."""
        width = max(4, len(str(self.max_tile())))
        sep = '+' + ('-' * (width + 2) + '+') * self.size
        out: list[str] = [sep]
        for row in self.grid:
            cells = ' | '.join(
                ('.' if v == 0 else str(v)).rjust(width) for v in row)
            out.append(f'| {cells} |')
            out.append(sep)
        out.append(f'score: {self.score}   moves: {self.moves}   '
                   f'max: {self.max_tile()}')
        return '\n'.join(out)


# --------------------------------------------------------------- expectimax AI

def _board_score(grid: list[list[int]]) -> float:
    """Heuristic for expectimax leaves — emphasises empty cells + monotone
    rows/columns + corner anchoring of the largest tile.

    These three signals drive the strongest hand-tuned 2048 bots: the
    biggest gain comes from *keeping the board breathable* (empty cells)
    and *building monotone gradients* down to a corner so merges chain.
    """
    n = len(grid)
    empty = sum(1 for r in grid for v in r if v == 0)
    mono = 0.0
    for row in grid:
        # Reward strictly non-increasing rows in either direction.
        for d in (1, -1):
            seq = row if d == 1 else list(reversed(row))
            for i in range(len(seq) - 1):
                if seq[i] >= seq[i + 1]:
                    mono += 0.25
    for c in range(n):
        col = [grid[r][c] for r in range(n)]
        for d in (1, -1):
            seq = col if d == 1 else list(reversed(col))
            for i in range(len(seq) - 1):
                if seq[i] >= seq[i + 1]:
                    mono += 0.25
    # Corner bonus — biggest tile in any corner is much easier to defend.
    biggest = max(v for r in grid for v in r)
    corner_bonus = 0.0
    if biggest > 0:
        corners = (grid[0][0], grid[0][n - 1],
                   grid[n - 1][0], grid[n - 1][n - 1])
        if biggest in corners:
            corner_bonus = biggest * 0.5
    return empty * 8.0 + mono * 4.0 + corner_bonus


def expectimax_best_move(game: 'Game', depth: int = 3) -> str | None:
    """Pick the move with the best expectimax value, or None if stuck.

    Max-nodes alternate with chance-nodes that respect the 90/10 spawn
    distribution. Depth is in *plies* (one move + its chance response).
    For a 4x4 board, depth 3 is the sweet spot of strength vs. speed.
    """
    best: tuple[float, str] | None = None
    for direction in DIRECTIONS:
        new_grid, score_delta, _ = _slide(game.grid, direction)
        if new_grid == game.grid:
            continue
        value = score_delta + _expect(new_grid, depth - 1)
        if best is None or value > best[0]:
            best = (value, direction)
    return best[1] if best else None


def _expect(grid: list[list[int]], depth: int) -> float:
    """Chance-node: average over (cell, value) spawns weighted by 0.9/0.1."""
    if depth <= 0:
        return _board_score(grid)
    empties = [(r, c) for r in range(len(grid))
               for c in range(len(grid)) if grid[r][c] == 0]
    if not empties:
        return _board_score(grid)
    # Uniform over empty cells, weighted 0.9/0.1 over the spawn value.
    total = 0.0
    for r, c in empties:
        for value, prob in ((2, P_SPAWN_2), (4, 1 - P_SPAWN_2)):
            grid[r][c] = value
            total += prob * _max(grid, depth)
            grid[r][c] = 0
    return total / len(empties)


def _max(grid: list[list[int]], depth: int) -> float:
    """Max-node: best score over the four directions."""
    if depth <= 0:
        return _board_score(grid)
    best: float | None = None
    for direction in DIRECTIONS:
        new_grid, score_delta, _ = _slide(grid, direction)
        if new_grid == grid:
            continue
        value = score_delta + _expect(new_grid, depth - 1)
        if best is None or value > best:
            best = value
    return best if best is not None else _board_score(grid)


# ------------------------------------------------------------------------ CLI

WASD = {'w': UP, 's': DOWN, 'a': LEFT, 'd': RIGHT,
        'W': UP, 'S': DOWN, 'A': LEFT, 'D': RIGHT}


def _read_key() -> str:
    """Block on a single keystroke; return a normalised label.

    Returns one of: 'up', 'down', 'left', 'right', 'q', 'n', 'h', 'u', 'a',
    or '' (unknown / EOF). Uses `msvcrt` on Windows, `termios` on POSIX —
    so arrow keys work without an external dependency.
    """
    if os.name == 'nt':
        try:
            import msvcrt
        except ImportError:
            return ''
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):
            # Arrow / function keys come as a two-char prefixed sequence.
            ch2 = msvcrt.getwch()
            return {'H': UP, 'P': DOWN, 'K': LEFT, 'M': RIGHT}.get(ch2, '')
        if ch in WASD:
            return WASD[ch]
        return ch.lower()

    # POSIX path — best-effort raw mode.
    try:
        import termios
        import tty
    except ImportError:
        line = sys.stdin.readline()
        if not line:
            return ''
        c = line.strip()[:1].lower()
        return WASD.get(c, c)

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':  # ESC sequence — possibly an arrow key
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            if ch2 == '[':
                return {'A': UP, 'B': DOWN, 'C': RIGHT, 'D': LEFT}.get(ch3, '')
            return ''
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    if ch in WASD:
        return WASD[ch]
    return ch.lower()


def _clear() -> None:
    print('\033[2J\033[H', end='')


def main() -> None:
    print('2048')
    print('----')
    print('Slide tiles with arrow keys (or WASD). Matching tiles merge.')
    print('Reach 2048 — but you can keep playing past that.')
    print('Commands: arrows/WASD = move, n = new game, u = undo,')
    print('          a = AI auto-play one move, h = AI hint, q = quit')
    print()

    rng = random.Random()
    game = Game(rng)
    history: list[dict] = []  # snapshots for undo
    UNDO_LIMIT = 50

    def snapshot() -> dict:
        return {
            'grid': [row[:] for row in game.grid],
            'score': game.score,
            'moves': game.moves,
        }

    def restore(snap: dict) -> None:
        game.grid = [row[:] for row in snap['grid']]
        game.score = snap['score']
        game.moves = snap['moves']

    print(game.render())
    while True:
        key = _read_key()
        if key in ('q', 'quit', 'exit', '\x03'):  # ctrl-c
            print('\nBye.')
            return
        if key == 'n':
            game = Game(rng)
            history.clear()
            _clear()
            print(game.render())
            continue
        if key == 'u':
            if history:
                restore(history.pop())
                _clear()
                print(game.render())
                print('(undo)')
            else:
                print('(nothing to undo)')
            continue
        if key == 'h':
            move = expectimax_best_move(game, depth=3)
            print(f'(AI suggests: {move or "no legal move"})')
            continue
        if key == 'a':
            move = expectimax_best_move(game, depth=3)
            if move is None:
                print('(AI: no legal move)')
                continue
            history.append(snapshot())
            if len(history) > UNDO_LIMIT:
                history.pop(0)
            game.move(move)
            _clear()
            print(game.render())
            print(f'(AI played {move})')
        elif key in DIRECTIONS:
            history.append(snapshot())
            if len(history) > UNDO_LIMIT:
                history.pop(0)
            result = game.move(key)
            if not result['moved']:
                history.pop()  # didn't actually change anything
            _clear()
            print(game.render())
            if result['score_delta']:
                print(f'(+{result["score_delta"]})')
        else:
            continue

        if game.is_won() and game.max_tile() == WIN_TILE:
            print('\n*** You reached 2048! Keep going for a higher score. ***')
        if game.is_lost():
            print('\nGame over — no legal moves. Press n for a new game, q to quit.')


if __name__ == '__main__':
    main()
