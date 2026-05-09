"""Maze Runner 2D — CLI / shared core.

A top-down ASCII maze game. Generate a random maze, walk from S to E
using arrow keys (or WASD on platforms without arrow input).

Pure functions are exposed for the GUI/TUI front-ends:
    - generate(width, height, rng, algorithm) -> Maze
    - Maze.solve()                            -> shortest path via BFS
    - Maze.render()                           -> ASCII string
    - Maze.move(direction)                    -> bool, mutates player pos

Mazes use the "double-grid" convention: a logical W x H grid of cells
becomes a (2W+1) x (2H+1) grid of characters where odd rows/cols are
cells and even rows/cols are wall slots between them.

Run:
    uv run python maze_runner_2d/maze_runner_2d.py
"""
from __future__ import annotations

import random
import sys
from collections import deque
from dataclasses import dataclass, field
from typing import Iterable

# --- glyphs ----------------------------------------------------------------

WALL = '#'
FLOOR = ' '
START = 'S'
END = 'E'
PLAYER = '@'
TRAIL = '.'

DIRECTIONS = {
    'up':    (0, -1),
    'down':  (0, 1),
    'left':  (-1, 0),
    'right': (1, 0),
}

ALGORITHMS = ('backtracker', 'prim', 'wilson')


# --- maze data -------------------------------------------------------------

@dataclass
class Maze:
    """A 2D maze stored as a character grid of size (2W+1) x (2H+1).

    `width` and `height` are the *logical* cell dimensions; the underlying
    grid is twice that plus one in each direction so walls can sit between
    cells. `start` and `end` are grid coordinates (x, y), not cell coords.
    """

    width: int           # logical cells across
    height: int          # logical cells down
    grid: list[list[str]]
    start: tuple[int, int]
    end: tuple[int, int]
    player: tuple[int, int] = field(init=False)

    def __post_init__(self) -> None:
        self.player = self.start

    # ----- dimensions in grid coords ---------------------------------------

    @property
    def gw(self) -> int:
        return 2 * self.width + 1

    @property
    def gh(self) -> int:
        return 2 * self.height + 1

    # ----- queries ---------------------------------------------------------

    def is_floor(self, x: int, y: int) -> bool:
        if not (0 <= x < self.gw and 0 <= y < self.gh):
            return False
        return self.grid[y][x] != WALL

    def neighbors(self, x: int, y: int) -> Iterable[tuple[int, int]]:
        for dx, dy in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            if self.is_floor(nx, ny):
                yield nx, ny

    # ----- solve via BFS ---------------------------------------------------

    def solve(self,
              source: tuple[int, int] | None = None,
              target: tuple[int, int] | None = None
              ) -> list[tuple[int, int]]:
        """Return the shortest path from source (default: start) to target
        (default: end) as a list of (x, y) grid coordinates, inclusive of
        both endpoints. Empty list if unreachable."""
        src = source if source is not None else self.start
        tgt = target if target is not None else self.end
        if src == tgt:
            return [src]

        parent: dict[tuple[int, int], tuple[int, int]] = {src: src}
        queue: deque[tuple[int, int]] = deque([src])
        while queue:
            node = queue.popleft()
            if node == tgt:
                break
            for nb in self.neighbors(*node):
                if nb not in parent:
                    parent[nb] = node
                    queue.append(nb)

        if tgt not in parent:
            return []

        path: list[tuple[int, int]] = [tgt]
        while path[-1] != src:
            path.append(parent[path[-1]])
        path.reverse()
        return path

    # ----- player movement -------------------------------------------------

    def move(self, direction: str) -> bool:
        """Move the player one grid cell. Returns True if a move happened."""
        if direction not in DIRECTIONS:
            return False
        dx, dy = DIRECTIONS[direction]
        nx, ny = self.player[0] + dx, self.player[1] + dy
        if not self.is_floor(nx, ny):
            return False
        self.player = (nx, ny)
        return True

    @property
    def won(self) -> bool:
        return self.player == self.end

    # ----- rendering -------------------------------------------------------

    def render(self,
               show_solution: bool = False,
               fog_radius: int | None = None) -> str:
        """Return an ASCII rendering of the maze.

        - `show_solution=True` overlays the BFS shortest path with TRAIL.
        - `fog_radius=N` hides everything farther than Manhattan distance N
          from the player (fog-of-war twist).
        """
        rows: list[list[str]] = [row[:] for row in self.grid]

        if show_solution:
            for x, y in self.solve():
                if (x, y) not in (self.start, self.end, self.player):
                    rows[y][x] = TRAIL

        sx, sy = self.start
        ex, ey = self.end
        rows[sy][sx] = START
        rows[ey][ex] = END
        px, py = self.player
        rows[py][px] = PLAYER

        if fog_radius is not None:
            for y in range(self.gh):
                for x in range(self.gw):
                    if abs(x - px) + abs(y - py) > fog_radius:
                        rows[y][x] = ' ' if rows[y][x] != WALL else ' '
        return '\n'.join(''.join(r) for r in rows)


# --- generators ------------------------------------------------------------

def _blank_grid(width: int, height: int) -> list[list[str]]:
    """All-walls grid sized for a `width` x `height` cell maze."""
    gw = 2 * width + 1
    gh = 2 * height + 1
    return [[WALL] * gw for _ in range(gh)]


def _cell_to_grid(cx: int, cy: int) -> tuple[int, int]:
    """Cell coords -> grid coords."""
    return 2 * cx + 1, 2 * cy + 1


def _carve(grid: list[list[str]], cx: int, cy: int) -> None:
    gx, gy = _cell_to_grid(cx, cy)
    grid[gy][gx] = FLOOR


def _carve_wall(grid: list[list[str]],
                a: tuple[int, int], b: tuple[int, int]) -> None:
    """Open the wall between two adjacent cells."""
    ax, ay = _cell_to_grid(*a)
    bx, by = _cell_to_grid(*b)
    grid[(ay + by) // 2][(ax + bx) // 2] = FLOOR
    grid[ay][ax] = FLOOR
    grid[by][bx] = FLOOR


def _cell_neighbors(cx: int, cy: int, w: int, h: int
                    ) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        nx, ny = cx + dx, cy + dy
        if 0 <= nx < w and 0 <= ny < h:
            out.append((nx, ny))
    return out


def _generate_backtracker(w: int, h: int,
                          rng: random.Random) -> list[list[str]]:
    """Recursive backtracker (iterative DFS). Long, winding corridors."""
    grid = _blank_grid(w, h)
    visited: set[tuple[int, int]] = set()
    start = (0, 0)
    stack: list[tuple[int, int]] = [start]
    visited.add(start)
    _carve(grid, *start)

    while stack:
        cx, cy = stack[-1]
        unvisited = [n for n in _cell_neighbors(cx, cy, w, h)
                     if n not in visited]
        if not unvisited:
            stack.pop()
            continue
        nxt = rng.choice(unvisited)
        _carve_wall(grid, (cx, cy), nxt)
        visited.add(nxt)
        stack.append(nxt)
    return grid


def _generate_prim(w: int, h: int,
                   rng: random.Random) -> list[list[str]]:
    """Randomised Prim's algorithm. Shorter, bushier corridors."""
    grid = _blank_grid(w, h)
    in_maze: set[tuple[int, int]] = set()
    start = (rng.randrange(w), rng.randrange(h))
    in_maze.add(start)
    _carve(grid, *start)

    # Frontier = walls between an in-maze cell and an out-of-maze cell.
    frontier: list[tuple[tuple[int, int], tuple[int, int]]] = [
        (start, n) for n in _cell_neighbors(*start, w, h)
    ]
    while frontier:
        i = rng.randrange(len(frontier))
        a, b = frontier.pop(i)
        if b in in_maze:
            continue
        _carve_wall(grid, a, b)
        in_maze.add(b)
        for n in _cell_neighbors(*b, w, h):
            if n not in in_maze:
                frontier.append((b, n))
    return grid


def _generate_wilson(w: int, h: int,
                     rng: random.Random) -> list[list[str]]:
    """Wilson's algorithm — uniform spanning tree via loop-erased walks.

    Slower, but each maze is drawn uniformly at random from the set of
    all possible mazes for the given dimensions.
    """
    grid = _blank_grid(w, h)
    cells = [(x, y) for y in range(h) for x in range(w)]
    in_maze: set[tuple[int, int]] = set()

    first = rng.choice(cells)
    in_maze.add(first)
    _carve(grid, *first)

    remaining = [c for c in cells if c != first]
    rng.shuffle(remaining)

    for seed in remaining:
        if seed in in_maze:
            continue
        # Loop-erased random walk from seed until we hit the in-maze set.
        path: list[tuple[int, int]] = [seed]
        index: dict[tuple[int, int], int] = {seed: 0}
        current = seed
        while current not in in_maze:
            nxt = rng.choice(_cell_neighbors(*current, w, h))
            if nxt in index:
                # Erase the loop.
                cut = index[nxt]
                for cell in path[cut + 1:]:
                    del index[cell]
                path = path[:cut + 1]
            else:
                index[nxt] = len(path)
                path.append(nxt)
            current = nxt
        # Carve the loop-erased path into the maze.
        for a, b in zip(path, path[1:]):
            _carve_wall(grid, a, b)
            in_maze.add(a)
            in_maze.add(b)
    return grid


_GENERATORS = {
    'backtracker': _generate_backtracker,
    'prim': _generate_prim,
    'wilson': _generate_wilson,
}


def generate(width: int,
             height: int,
             rng: random.Random | None = None,
             algorithm: str = 'backtracker') -> Maze:
    """Generate a random `width` x `height` cell maze.

    `algorithm` is one of 'backtracker', 'prim', or 'wilson'. Start is the
    top-left cell, end is the bottom-right cell.
    """
    if width < 2 or height < 2:
        raise ValueError('maze must be at least 2x2 cells')
    if algorithm not in _GENERATORS:
        raise ValueError(
            f'unknown algorithm {algorithm!r}; '
            f'expected one of {sorted(_GENERATORS)}')

    rng = rng or random.Random()
    grid = _GENERATORS[algorithm](width, height, rng)

    start = _cell_to_grid(0, 0)
    end = _cell_to_grid(width - 1, height - 1)
    return Maze(width=width, height=height, grid=grid,
                start=start, end=end)


# --- CLI -------------------------------------------------------------------

KEY_HELP = """\
Controls: w/a/s/d (or i/j/k/l) to move, p = show path, n = new maze,
          t = toggle algorithm, f = fog-of-war, q = quit.
"""


def _read_key() -> str:
    """One-character read with no echo, falling back to line input on
    platforms without msvcrt/termios."""
    try:
        import msvcrt  # type: ignore
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):
            # Arrow keys come as a 2-byte sequence on Windows.
            ch2 = msvcrt.getwch()
            return {'H': 'w', 'P': 's', 'K': 'a', 'M': 'd'}.get(ch2, '')
        return ch.lower()
    except ImportError:
        pass
    try:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                seq = sys.stdin.read(2)
                return {'[A': 'w', '[B': 's',
                        '[D': 'a', '[C': 'd'}.get(seq, '')
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
    except Exception:
        return (input('move> ').strip().lower() + ' ')[0]


def main() -> None:
    width, height = 15, 11
    algo_idx = 0
    rng = random.Random()
    show_path = False
    fog = False
    fog_radius = 4

    maze = generate(width, height, rng, ALGORITHMS[algo_idx])

    print(KEY_HELP)
    while True:
        print(maze.render(
            show_solution=show_path,
            fog_radius=fog_radius if fog else None))
        algo = ALGORITHMS[algo_idx]
        steps_remaining = max(0, len(maze.solve()) - 1)
        print(f'algorithm={algo}  remaining={steps_remaining}  '
              f"path={'on' if show_path else 'off'}  "
              f"fog={'on' if fog else 'off'}")

        if maze.won:
            print('You reached the exit! Press n for a new maze, q to quit.')

        key = _read_key()
        if key == 'q':
            break
        elif key == 'n':
            maze = generate(width, height, rng, ALGORITHMS[algo_idx])
            show_path = False
        elif key == 'p':
            show_path = not show_path
        elif key == 'f':
            fog = not fog
        elif key == 't':
            algo_idx = (algo_idx + 1) % len(ALGORITHMS)
            maze = generate(width, height, rng, ALGORITHMS[algo_idx])
            show_path = False
        elif key in ('w', 'i'):
            maze.move('up')
        elif key in ('s', 'k'):
            maze.move('down')
        elif key in ('a', 'j'):
            maze.move('left')
        elif key in ('d', 'l'):
            maze.move('right')
        # blank line separator between frames
        print()

    print('Thanks for playing!')


if __name__ == '__main__':
    main()
