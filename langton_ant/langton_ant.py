"""Langton's Ant — CLI.

A 2D cellular automaton with a single mobile agent (the "ant"). On a white
cell the ant turns right, flips the cell to black, and moves forward. On a
black cell it turns left, flips the cell to white, and moves forward. From
those two trivial rules the ant chaotically scribbles for ~10,000 steps
before locking into a perfectly periodic 104-step "highway" forever.

Multi-color generalization
--------------------------
The rule string lets you go beyond two colors. ``"RL"`` is classical
Langton's Ant. ``"RLR"`` is a 3-color variant; ``"LLRR"`` makes a 4-color
ant that traces a square spiral; ``"RRLL"`` makes a fractal cardioid.
Each character is the turn the ant performs when standing on a cell whose
*current* color index matches that position. After turning, the cell index
advances ``(c + 1) % len(rule)`` (cyclic flip), then the ant moves forward.

Run:
    uv run python langton_ant/langton_ant.py
    uv run python langton_ant/langton_ant.py --rule RL --steps 11000
    uv run python langton_ant/langton_ant.py --rule RLR --rows 121 --cols 121
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np


# Direction encoding: 0=Up, 1=Right, 2=Down, 3=Left.
# (drow, dcol) deltas — NumPy is row-major so "up" is row-1.
_DELTAS: tuple[tuple[int, int], ...] = (
    (-1, 0),   # 0 Up
    (0, 1),    # 1 Right
    (1, 0),    # 2 Down
    (0, -1),   # 3 Left
)

# Turn deltas keyed by rule character.
_TURNS: dict[str, int] = {
    'R': 1,    # 90° clockwise
    'L': -1,   # 90° counter-clockwise
    'U': 2,    # u-turn (used by some Turmite variants)
    'N': 0,    # no turn
}


def _validate_rule(rule: str) -> str:
    """Normalize and validate a rule string.

    Returns the upper-cased rule. Raises ValueError on invalid characters
    or empty input.
    """
    if not rule:
        raise ValueError('rule string must not be empty')
    rule = rule.upper()
    bad = [c for c in rule if c not in _TURNS]
    if bad:
        raise ValueError(
            f'rule contains invalid chars {bad!r}; use any of {sorted(_TURNS)}'
        )
    if len(rule) > 255:
        raise ValueError('rule supports at most 255 colors (uint8 limit)')
    return rule


# --- Core ant agent -------------------------------------------------------

class Ant:
    """A single Langton's Ant on a NumPy grid.

    The grid stores a color index per cell as ``uint8``. Index ``0`` is
    "white" and is the starting state. ``rule[index]`` decides which way
    the ant turns when it lands on that cell.

    The grid is mutated in place (Langton's Ant is a *moving-head*
    automaton, not synchronous like Game of Life — there is exactly one
    cell change per step).
    """

    def __init__(
        self,
        grid: np.ndarray,
        x: int,
        y: int,
        direction: int,
        rule: str = 'RL',
    ) -> None:
        if grid.ndim != 2:
            raise ValueError('grid must be 2D')
        if grid.dtype != np.uint8:
            grid = grid.astype(np.uint8, copy=False)

        self.grid = grid
        self.rule = _validate_rule(rule)
        self.n_colors = len(self.rule)

        rows, cols = grid.shape
        if not (0 <= y < rows and 0 <= x < cols):
            raise ValueError(f'(x={x}, y={y}) outside grid {grid.shape}')
        if direction not in (0, 1, 2, 3):
            raise ValueError('direction must be 0..3 (Up/Right/Down/Left)')

        self.x = int(x)
        self.y = int(y)
        self.direction = int(direction)
        self.steps = 0
        self.alive = True  # False once the ant walks off a non-toroidal grid

    # --- Single-step rule -------------------------------------------------

    def step(self) -> None:
        """Advance one step using the active rule.

        On a non-toroidal grid the ant becomes ``alive=False`` if it
        attempts to walk off the edge (subsequent ``step()`` calls are
        no-ops). The cell flip and turn still happen on the final step.
        """
        if not self.alive:
            return

        rows, cols = self.grid.shape
        color = int(self.grid[self.y, self.x])
        # Wrap color index in case the grid was seeded with a value
        # outside [0, n_colors); keeps the rule total.
        color %= self.n_colors

        # Turn first (before flipping/moving) — order matches the spec:
        # "turn, flip, move forward" is a single atomic step.
        turn = _TURNS[self.rule[color]]
        self.direction = (self.direction + turn) % 4

        # Flip the cell: cycle through colors 0 → 1 → ... → 0.
        self.grid[self.y, self.x] = (color + 1) % self.n_colors

        # Move forward.
        dy, dx = _DELTAS[self.direction]
        ny, nx = self.y + dy, self.x + dx
        if 0 <= ny < rows and 0 <= nx < cols:
            self.y, self.x = ny, nx
        else:
            # Off the edge — freeze the ant in place and mark dead.
            self.alive = False

        self.steps += 1

    # --- Snapshot ---------------------------------------------------------

    def state(self) -> dict:
        """Return a JSON-serializable snapshot of the ant."""
        return {
            'x': self.x,
            'y': self.y,
            'direction': self.direction,
            'steps': self.steps,
            'rule': self.rule,
            'alive': self.alive,
        }


# --- Pure functional helpers ---------------------------------------------

def step_n(
    grid: np.ndarray,
    x: int,
    y: int,
    direction: int,
    n: int,
    rule: str = 'RL',
) -> tuple[np.ndarray, int, int, int, int]:
    """Run *n* steps of Langton's Ant and return the new state.

    Returns a tuple ``(grid, x, y, direction, steps_taken)`` where
    ``steps_taken`` may be less than *n* if the ant walked off a
    non-toroidal grid.

    The returned grid is the same object as ``Ant.grid`` (mutated in
    place) — the caller is free to copy it beforehand if needed.
    """
    ant = Ant(grid, x, y, direction, rule=rule)
    for _ in range(n):
        if not ant.alive:
            break
        ant.step()
    return ant.grid, ant.x, ant.y, ant.direction, ant.steps


def make_grid(rows: int = 101, cols: int = 101) -> np.ndarray:
    """Allocate an empty (all-color-0) grid of the given dimensions."""
    if rows <= 0 or cols <= 0:
        raise ValueError('rows and cols must be positive')
    return np.zeros((rows, cols), dtype=np.uint8)


# --- CLI rendering --------------------------------------------------------

# Glyphs cycled through for color indices > 0 in the CLI; 0 is always blank.
_CELL_GLYPHS = ' #@%*+=:.~-'


def render(grid: np.ndarray, ant_x: int, ant_y: int, ant_glyph: str = 'A') -> str:
    """Render the grid as a string (one terminal line per grid row)."""
    rows = grid.shape[0]
    out_rows: list[str] = []
    for r in range(rows):
        row = grid[r]
        chars: list[str] = []
        for c, val in enumerate(row):
            if r == ant_y and c == ant_x:
                chars.append(ant_glyph)
            elif val == 0:
                chars.append('.')
            else:
                chars.append(_CELL_GLYPHS[int(val) % len(_CELL_GLYPHS)] or '#')
        out_rows.append(''.join(chars))
    return '\n'.join(out_rows)


def _clear() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Langton's Ant — CLI")
    parser.add_argument('--rows', type=int, default=41,
                        help='Grid rows (default 41)')
    parser.add_argument('--cols', type=int, default=81,
                        help='Grid cols (default 81)')
    parser.add_argument('--rule', type=str, default='RL',
                        help='Turn rule string (default "RL"). '
                             'Try "RLR", "LLRR", "RRLL".')
    parser.add_argument('--steps', type=int, default=11_000,
                        help='Number of simulation steps (default 11000)')
    parser.add_argument('--fps', type=float, default=30.0,
                        help='Frames per second when --animate (default 30)')
    parser.add_argument('--animate', action='store_true',
                        help='Animate live in the terminal (slow). '
                             'Default just prints the final frame.')
    parser.add_argument('--frames', type=int, default=120,
                        help='Show this many evenly-spaced frames when '
                             'animating (default 120)')
    args = parser.parse_args(argv)

    rule = _validate_rule(args.rule)
    grid = make_grid(args.rows, args.cols)
    ant = Ant(grid, args.cols // 2, args.rows // 2, direction=0, rule=rule)

    if not args.animate:
        for _ in range(args.steps):
            if not ant.alive:
                break
            ant.step()
        print(render(ant.grid, ant.x, ant.y))
        s = ant.state()
        print(f"\nrule={s['rule']}  steps={s['steps']}  "
              f"pos=({s['x']},{s['y']})  dir={s['direction']}  "
              f"alive={s['alive']}  black_cells={int((ant.grid > 0).sum())}")
        return

    # --animate: show a fixed number of evenly-spaced frames.
    frames = max(1, args.frames)
    steps_per_frame = max(1, args.steps // frames)
    delay = 1.0 / max(args.fps, 0.1)

    try:
        for f in range(frames):
            for _ in range(steps_per_frame):
                if not ant.alive:
                    break
                ant.step()
            _clear()
            print(f"Langton's Ant — rule={rule}  step={ant.steps}  "
                  f"pos=({ant.x},{ant.y})  dir={ant.direction}")
            print(render(ant.grid, ant.x, ant.y))
            print('Ctrl+C to stop.')
            if not ant.alive:
                print('Ant walked off the grid.')
                break
            time.sleep(delay)
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main(sys.argv[1:])
