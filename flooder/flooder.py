"""Flooder — core game logic.

Flood-fill puzzle game. A grid of colored cells where the top-left corner
anchors the "controlled" region. Each turn, pick a color: your region expands
to absorb all adjacent cells of that color. Win by capturing the whole grid
within the move limit.

Twist: greedy_hint() picks the color that maximizes immediate region growth.

Run CLI:
    uv run python flooder/flooder.py
"""
from __future__ import annotations

import random
import sys
from collections import deque

# Default move limit for a 14×14 board
DEFAULT_MOVES = 25
DEFAULT_WIDTH = 14
DEFAULT_HEIGHT = 14
DEFAULT_COLORS = 6

# ANSI colors for CLI display
_ANSI = [
    '\033[41m',  # 0 red
    '\033[42m',  # 1 green
    '\033[43m',  # 2 yellow
    '\033[44m',  # 3 blue
    '\033[45m',  # 4 magenta
    '\033[46m',  # 5 cyan
]
_RESET = '\033[0m'
_COLOR_NAMES = ['Red', 'Green', 'Yellow', 'Blue', 'Magenta', 'Cyan']


class Game:
    """Flood-fill puzzle game.

    Parameters
    ----------
    width, height:  grid dimensions (default 14×14)
    num_colors:     number of distinct colors (default 6)
    rng:            optional ``random.Random`` instance for reproducibility
    max_moves:      move budget (default 25)
    """

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        num_colors: int = DEFAULT_COLORS,
        rng: random.Random | None = None,
        max_moves: int = DEFAULT_MOVES,
    ) -> None:
        self.width = width
        self.height = height
        self.num_colors = num_colors
        self.max_moves = max_moves
        self._rng = rng or random.Random()

        # Grid: grid[row][col] = int color index
        self._grid: list[list[int]] = [
            [self._rng.randint(0, num_colors - 1) for _ in range(width)]
            for _ in range(height)
        ]
        self._moves_used: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def moves_left(self) -> int:
        return self.max_moves - self._moves_used

    def state(self) -> dict:
        """Return a snapshot of the game state (grid copy + metadata)."""
        return {
            'grid': [row[:] for row in self._grid],
            'moves_left': self.moves_left,
            'moves_used': self._moves_used,
            'is_won': self.is_won(),
            'is_lost': self.is_lost(),
            'region_size': self._region_size(),
        }

    def flood(self, color: int) -> int:
        """Flood-fill from (0, 0) with *color*.

        Expands the controlled region (all cells reachable from (0,0) that
        share its current color) to the new *color*, then absorbs all
        adjacent cells of *color* into the region.

        Returns the new region size.
        """
        if self.is_won() or self.is_lost():
            return self._region_size()

        # Collect current controlled region via BFS
        start_color = self._grid[0][0]
        if color == start_color:
            return self._region_size()  # no-op

        region = self._bfs_region(start_color)

        # Paint the region with the new color
        for r, c in region:
            self._grid[r][c] = color

        # Expand: BFS from region frontier to absorb adjacent color-matching cells
        visited = set(region)
        queue: deque[tuple[int, int]] = deque()

        # Seed queue with neighbors of the region that match new color
        for r, c in region:
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) not in visited and self._grid[nr][nc] == color:
                    visited.add((nr, nc))
                    queue.append((nr, nc))

        while queue:
            r, c = queue.popleft()
            self._grid[r][c] = color
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) not in visited and self._grid[nr][nc] == color:
                    visited.add((nr, nc))
                    queue.append((nr, nc))

        self._moves_used += 1
        return len(visited)

    def is_won(self) -> bool:
        """True when every cell has the same color."""
        target = self._grid[0][0]
        return all(self._grid[r][c] == target for r in range(self.height)
                   for c in range(self.width))

    def is_lost(self) -> bool:
        return self._moves_used >= self.max_moves and not self.is_won()

    def greedy_hint(self) -> int:
        """Return the color that maximises immediate region growth (greedy AI)."""
        current_color = self._grid[0][0]
        best_color = -1
        best_size = -1
        for c in range(self.num_colors):
            if c == current_color:
                continue
            size = self._simulate_flood_size(c)
            if size > best_size:
                best_size = size
                best_color = c
        return best_color

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bfs_region(self, color: int) -> set[tuple[int, int]]:
        """BFS from (0,0) — collect all cells reachable with *color*."""
        visited: set[tuple[int, int]] = set()
        queue: deque[tuple[int, int]] = deque([(0, 0)])
        visited.add((0, 0))
        while queue:
            r, c = queue.popleft()
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) not in visited and self._grid[nr][nc] == color:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return visited

    def _region_size(self) -> int:
        return len(self._bfs_region(self._grid[0][0]))

    def _neighbors(self, r: int, c: int):
        if r > 0:
            yield r - 1, c
        if r < self.height - 1:
            yield r + 1, c
        if c > 0:
            yield r, c - 1
        if c < self.width - 1:
            yield r, c + 1

    def _simulate_flood_size(self, color: int) -> int:
        """Return projected region size after flooding with *color* (no mutation)."""
        start_color = self._grid[0][0]
        region = self._bfs_region(start_color)
        visited = set(region)
        queue: deque[tuple[int, int]] = deque()
        for r, c in region:
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) not in visited and self._grid[nr][nc] == color:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        while queue:
            r, c = queue.popleft()
            for nr, nc in self._neighbors(r, c):
                if (nr, nc) not in visited and self._grid[nr][nc] == color:
                    visited.add((nr, nc))
                    queue.append((nr, nc))
        return len(visited)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _render(game: Game) -> None:
    st = game.state()
    grid = st['grid']
    total = game.width * game.height
    print()
    for row in grid:
        line = ''
        for cell in row:
            line += f'{_ANSI[cell]}  {_RESET}'
        print(line)
    print()
    print(f'Moves left: {st["moves_left"]} / {game.max_moves}  '
          f'Region: {st["region_size"]}/{total} cells')
    print('Colors: ' + '  '.join(
        f'{_ANSI[i]} {i + 1}:{_COLOR_NAMES[i]} {_RESET}'
        for i in range(game.num_colors)
    ))


def main() -> None:
    print('=' * 40)
    print('  FLOODER — Flood-Fill Puzzle Game')
    print('=' * 40)
    print('Capture the whole grid within the move limit.')
    print('Type 1-6 to pick a color, H for a hint, N for new game, Q to quit.')

    game = Game()

    while True:
        _render(game)
        st = game.state()

        if st['is_won']:
            print(f'\n*** YOU WIN! Completed in {game._moves_used} moves ***')
            choice = input('Play again? [Y/n] ').strip().lower()
            if choice == 'n':
                break
            game = Game()
            continue

        if st['is_lost']:
            print('\n*** OUT OF MOVES — Game over. ***')
            choice = input('Play again? [Y/n] ').strip().lower()
            if choice == 'n':
                break
            game = Game()
            continue

        try:
            raw = input('Your move: ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if raw in ('q', 'quit'):
            break
        if raw in ('n', 'new'):
            game = Game()
            continue
        if raw in ('h', 'hint'):
            hint = game.greedy_hint()
            print(f'Hint: try color {hint + 1} ({_COLOR_NAMES[hint]})')
            continue
        if raw.isdigit() and 1 <= int(raw) <= game.num_colors:
            game.flood(int(raw) - 1)
        else:
            print(f'Invalid input. Enter 1-{game.num_colors}, H, N, or Q.')


if __name__ == '__main__':
    main()
