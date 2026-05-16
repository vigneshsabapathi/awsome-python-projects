"""Fish Tank — CLI.

An animated ASCII aquarium: multiple fish swim left and right at
varying speeds, bubbles rise toward the surface, and seaweed sways
gently at the bottom.

Twist: Schooling behaviour — each fish nudges its direction toward
the nearest neighbour when they are within range.

Run:
    uv run python fish_tank/fish_tank.py
    uv run python fish_tank/fish_tank.py --fish 8 --width 100 --height 28
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field

# ── fish art ──────────────────────────────────────────────────────────────────
# Each species is defined as (right-facing art, left-facing art, color_name).
# color_name is used for ANSI colouring in the CLI.

SPECIES: list[tuple[str, str, str]] = [
    ('><(((°>',  '<°)))><',  'cyan'),
    ('><((°>',   '<°))><',   'yellow'),
    ('><(°>',    '<°)><',    'green'),
    ('>°>>',     '<<°<',     'magenta'),
    ('><º>',     '<º><',     'blue'),
    ('><{{{{>',  '<}}}}><',  'red'),
    ('><(((ø>',  '<ø)))><',  'white'),
]

# ANSI 256-colour codes (fg only).
_ANSI_FG: dict[str, str] = {
    'red':     '\x1b[38;5;196m',
    'orange':  '\x1b[38;5;208m',
    'yellow':  '\x1b[38;5;226m',
    'green':   '\x1b[38;5;46m',
    'cyan':    '\x1b[38;5;51m',
    'blue':    '\x1b[38;5;39m',
    'magenta': '\x1b[38;5;201m',
    'white':   '\x1b[38;5;231m',
}
_RESET = '\x1b[0m'

# schooling radius in cells
_SCHOOL_RADIUS = 20


@dataclass
class Fish:
    """One fish in the tank.

    Attributes
    ----------
    x, y : float
        Position (column, row). Stored as float for sub-cell speed.
    dx : float
        Horizontal velocity in cells/step. Positive = rightward.
    art_right : str
        ASCII art for the fish facing right.
    art_left : str
        ASCII art for the fish facing left.
    color : str
        Key into :data:`_ANSI_FG`.
    """

    x: float
    y: float
    dx: float
    art_right: str
    art_left: str
    color: str

    @property
    def width(self) -> int:
        return len(self.art_right)

    @property
    def facing_right(self) -> bool:
        return self.dx >= 0

    @property
    def art(self) -> str:
        return self.art_right if self.facing_right else self.art_left

    def step(self, tank_width: int, tank_height: int) -> None:
        """Move one step; bounce off side walls."""
        self.x += self.dx
        # Bounce off left wall
        if self.x < 0:
            self.x = 0.0
            self.dx = abs(self.dx)
        # Bounce off right wall (fish width must stay inside)
        elif self.x + self.width > tank_width:
            self.x = float(tank_width - self.width)
            self.dx = -abs(self.dx)

    def apply_schooling(self, others: list[Fish]) -> None:
        """Nudge direction toward the nearest fish within _SCHOOL_RADIUS."""
        best_dist = float('inf')
        nearest: Fish | None = None
        for other in others:
            if other is self:
                continue
            dist = math.fabs(other.x - self.x)
            if dist < best_dist:
                best_dist = dist
                nearest = other
        if nearest is not None and best_dist < _SCHOOL_RADIUS:
            # Softly align: if neighbour is to the right and we're moving left,
            # flip direction 25% of the time.
            if nearest.x > self.x and self.dx < 0:
                if random.random() < 0.25:
                    self.dx = abs(self.dx)
            elif nearest.x < self.x and self.dx > 0:
                if random.random() < 0.25:
                    self.dx = -abs(self.dx)


@dataclass
class Bubble:
    """A rising bubble.

    Bubbles drift upward one cell per step; occasionally wobble left/right.
    """

    x: int
    y: float

    def step(self, tank_height: int) -> bool:
        """Move upward. Returns True if the bubble has escaped the tank."""
        self.y -= 1
        # Slight horizontal wobble
        if random.random() < 0.3:
            self.x += random.choice((-1, 0, 1))
        return self.y < 1

    @property
    def symbol(self) -> str:
        return random.choice(('o', 'O', '°'))


@dataclass
class Plant:
    """Seaweed column fixed to the bottom row, sways each step."""

    x: int
    height: int
    _offset: int = field(default=0, repr=False)

    def step(self) -> None:
        self._offset = (self._offset + random.choice((-1, 0, 0, 1))) % 3

    def cells(self, tank_height: int) -> list[tuple[int, int, str]]:
        """Return (col, row, char) for each seaweed segment."""
        result = []
        for i in range(self.height):
            row = tank_height - 1 - i
            sway = (i + self._offset) % 3
            ch = '|' if sway == 0 else ('/' if sway == 1 else '\\')
            result.append((self.x, row, ch))
        return result


class Tank:
    """The aquarium.

    Parameters
    ----------
    width, height : int
        Dimensions in text cells.
    num_fish : int
        How many fish to spawn initially.
    rng : random.Random | None
        Optional seeded RNG (for deterministic tests).
    """

    def __init__(
        self,
        width: int = 80,
        height: int = 24,
        num_fish: int = 5,
        rng: random.Random | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self._rng = rng or random.Random()
        self.fish: list[Fish] = []
        self.bubbles: list[Bubble] = []
        self.plants: list[Plant] = []
        self._step_count = 0

        # Plants evenly spaced along the bottom.
        n_plants = max(2, width // 10)
        xs = [int(i * width / n_plants) for i in range(n_plants)]
        for px in xs:
            h = self._rng.randint(2, max(3, height // 5))
            self.plants.append(Plant(x=px, height=h))

        for _ in range(num_fish):
            self._spawn_fish()

    # ── Public API ────────────────────────────────────────────────────────────

    def add_fish(self) -> None:
        self._spawn_fish()

    def step(self) -> None:
        """Advance the simulation by one frame."""
        self._step_count += 1

        # Schooling nudge before movement
        for fish in self.fish:
            fish.apply_schooling(self.fish)

        for fish in self.fish:
            fish.step(self.width, self.height)

        # Advance/remove bubbles
        self.bubbles = [b for b in self.bubbles if not b.step(self.height)]

        # Sway plants
        for plant in self.plants:
            plant.step()

        # Spawn new bubbles occasionally from random fish
        if self.fish and self._rng.random() < 0.4:
            src = self._rng.choice(self.fish)
            bx = int(src.x) + (src.width if src.facing_right else 0)
            by = float(max(1, src.y - 1))
            self.bubbles.append(Bubble(x=max(0, min(bx, self.width - 1)), y=by))

    def render(self, *, color: bool = False) -> str:
        """Return the tank as a multi-line string.

        The top row is a border of '~' characters (water surface).
        The bottom row is a border of '_' characters (seafloor).
        Fish, bubbles, and plants fill the interior.
        """
        # Build grid of characters (plain strings, no ANSI yet)
        grid: list[list[str]] = [[' '] * self.width for _ in range(self.height)]
        # Color grid: parallel grid of color keys (or None)
        color_grid: list[list[str | None]] = [
            [None] * self.width for _ in range(self.height)
        ]

        # Top border: water surface
        for c in range(self.width):
            grid[0][c] = '~'
            color_grid[0][c] = 'cyan'

        # Bottom border: seafloor
        for c in range(self.width):
            grid[self.height - 1][c] = '_'

        # Plants (draw before fish so fish overlap plants)
        for plant in self.plants:
            for cx, cy, ch in plant.cells(self.height):
                if 0 <= cy < self.height and 0 <= cx < self.width:
                    grid[cy][cx] = ch
                    color_grid[cy][cx] = 'green'

        # Bubbles
        for bubble in self.bubbles:
            by = int(bubble.y)
            bx = bubble.x
            if 1 <= by < self.height - 1 and 0 <= bx < self.width:
                grid[by][bx] = 'o'
                color_grid[by][bx] = 'cyan'

        # Fish
        for fish in self.fish:
            row = int(fish.y)
            if not (1 <= row < self.height - 1):
                continue
            art = fish.art
            for i, ch in enumerate(art):
                col = int(fish.x) + i
                if 0 <= col < self.width:
                    grid[row][col] = ch
                    color_grid[row][col] = fish.color

        # Assemble rows
        rows: list[str] = []
        for r in range(self.height):
            if color:
                parts: list[str] = []
                for c in range(self.width):
                    ch = grid[r][c]
                    col_key = color_grid[r][c]
                    if col_key and col_key in _ANSI_FG:
                        parts.append(f'{_ANSI_FG[col_key]}{ch}{_RESET}')
                    else:
                        parts.append(ch)
                rows.append(''.join(parts))
            else:
                rows.append(''.join(grid[r]))

        return '\n'.join(rows)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _spawn_fish(self) -> None:
        species_idx = self._rng.randrange(len(SPECIES))
        art_r, art_l, color = SPECIES[species_idx]
        fish_w = len(art_r)
        x = float(self._rng.randint(0, max(0, self.width - fish_w - 1)))
        y = float(self._rng.randint(1, max(1, self.height - 2)))
        speed = self._rng.uniform(0.3, 1.5)
        dx = speed if self._rng.random() < 0.5 else -speed
        self.fish.append(Fish(
            x=x, y=y, dx=dx,
            art_right=art_r, art_left=art_l,
            color=color,
        ))


def _clear() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Fish Tank — animated ASCII aquarium')
    parser.add_argument('--width',  type=int, default=80, help='Tank width (default 80)')
    parser.add_argument('--height', type=int, default=24, help='Tank height (default 24)')
    parser.add_argument('--fish',   type=int, default=5,  help='Number of fish (default 5)')
    parser.add_argument('--fps',    type=float, default=8.0)
    parser.add_argument('--steps',  type=int, default=0,
                        help='Frames to render before stopping (0 = run forever)')
    parser.add_argument('--seed',   type=int, default=None)
    parser.add_argument('--no-color', action='store_true')
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    tank = Tank(args.width, args.height, args.fish, rng=rng)
    delay = 1.0 / max(args.fps, 0.1)
    use_color = not args.no_color
    frame = 0

    try:
        while True:
            _clear()
            tank.step()
            header = (
                f'Fish Tank   fish={len(tank.fish)}  '
                f'bubbles={len(tank.bubbles)}  '
                f'frame={frame}  '
                f'[schooling ON]  '
                f'Ctrl+C to stop'
            )
            print(header)
            print(tank.render(color=use_color))
            frame += 1
            if args.steps and frame >= args.steps:
                break
            time.sleep(delay)
    except KeyboardInterrupt:
        print('\nDrained the tank.')


if __name__ == '__main__':
    main(sys.argv[1:])
