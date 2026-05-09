"""Conway's Game of Life — CLI.

Cellular automaton on a 2D grid. Each cell is alive (1) or dead (0).
Rules per step:
    - A live cell with 2 or 3 live neighbors stays alive.
    - A dead cell with exactly 3 live neighbors becomes alive.
    - Otherwise the cell dies / stays dead.

Run:
    uv run python game_of_life/game_of_life.py
    uv run python game_of_life/game_of_life.py --pattern glider --rows 30 --cols 60
    uv run python game_of_life/game_of_life.py --pattern gosper --bounded

Implementation note
-------------------
`step()` uses an 8-shifted-sum NumPy vectorization (no Python double loop).
Each of the 8 neighbor offsets contributes a shifted copy to the count grid;
final mask is `(count == 3) | ((count == 2) & alive)`.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import numpy as np


# --- Core algorithm -------------------------------------------------------

def step(grid: np.ndarray, *, toroidal: bool = True) -> np.ndarray:
    """Advance one Game-of-Life generation.

    Vectorized via 8 shifted sums — no Python-level loops over cells.
    `toroidal=True` wraps edges (np.roll); False uses zero-padding.
    """
    if grid.ndim != 2:
        raise ValueError('grid must be 2D')
    g = grid.astype(np.uint8, copy=False)

    if toroidal:
        # 8 neighbor shifts via np.roll — wraps around edges.
        n = (
            np.roll(g, (-1, -1), axis=(0, 1))
            + np.roll(g, (-1,  0), axis=(0, 1))
            + np.roll(g, (-1,  1), axis=(0, 1))
            + np.roll(g, ( 0, -1), axis=(0, 1))
            + np.roll(g, ( 0,  1), axis=(0, 1))
            + np.roll(g, ( 1, -1), axis=(0, 1))
            + np.roll(g, ( 1,  0), axis=(0, 1))
            + np.roll(g, ( 1,  1), axis=(0, 1))
        )
    else:
        # Bounded: zero-pad and slice — neighbors past the edge count as dead.
        p = np.pad(g, 1, mode='constant', constant_values=0)
        n = (
            p[ :-2,  :-2] + p[ :-2, 1:-1] + p[ :-2, 2:]
            + p[1:-1,  :-2]                + p[1:-1, 2:]
            + p[2:  ,  :-2] + p[2:  , 1:-1] + p[2:  , 2:]
        )
    # Live with 2 or 3 neighbors stays alive; dead with exactly 3 becomes alive.
    alive = g.astype(bool)
    return ((n == 3) | (alive & (n == 2))).astype(np.uint8)


# --- Pattern factories ----------------------------------------------------

def _embed(rows: int, cols: int, cells: list[tuple[int, int]],
           top: int = 1, left: int = 1) -> np.ndarray:
    grid = np.zeros((rows, cols), dtype=np.uint8)
    for r, c in cells:
        rr, cc = top + r, left + c
        if 0 <= rr < rows and 0 <= cc < cols:
            grid[rr, cc] = 1
    return grid


def random_grid(rows: int = 40, cols: int = 80, density: float = 0.25,
                seed: int | None = None) -> np.ndarray:
    """Random alive/dead grid with given live-cell probability."""
    rng = np.random.default_rng(seed)
    return (rng.random((rows, cols)) < density).astype(np.uint8)


def blinker_grid(rows: int = 5, cols: int = 5) -> np.ndarray:
    """Period-2 oscillator: 3 cells in a row."""
    cy, cx = rows // 2, cols // 2
    return _embed(rows, cols, [(0, -1), (0, 0), (0, 1)], top=cy, left=cx)


def glider_grid(rows: int = 20, cols: int = 30) -> np.ndarray:
    """Classic 5-cell glider, top-left corner."""
    cells = [(0, 1), (1, 2), (2, 0), (2, 1), (2, 2)]
    return _embed(rows, cols, cells, top=1, left=1)


def pulsar_grid(rows: int = 17, cols: int = 17) -> np.ndarray:
    """Period-3 oscillator (15-cell symmetric pulsar)."""
    base = [
        (2, 4), (2, 5), (2, 6), (2, 10), (2, 11), (2, 12),
        (4, 2), (5, 2), (6, 2),
        (4, 7), (5, 7), (6, 7),
        (4, 9), (5, 9), (6, 9),
        (4, 14), (5, 14), (6, 14),
        (7, 4), (7, 5), (7, 6), (7, 10), (7, 11), (7, 12),
        (9, 4), (9, 5), (9, 6), (9, 10), (9, 11), (9, 12),
        (10, 2), (11, 2), (12, 2),
        (10, 7), (11, 7), (12, 7),
        (10, 9), (11, 9), (12, 9),
        (10, 14), (11, 14), (12, 14),
        (14, 4), (14, 5), (14, 6), (14, 10), (14, 11), (14, 12),
    ]
    # Center the pattern on the requested grid.
    top = max(0, (rows - 17) // 2)
    left = max(0, (cols - 17) // 2)
    return _embed(rows, cols, base, top=top, left=left)


def gosper_glider_gun_grid(rows: int = 30, cols: int = 60) -> np.ndarray:
    """Gosper glider gun — first known finite pattern with unbounded growth."""
    cells = [
        (0, 24),
        (1, 22), (1, 24),
        (2, 12), (2, 13), (2, 20), (2, 21), (2, 34), (2, 35),
        (3, 11), (3, 15), (3, 20), (3, 21), (3, 34), (3, 35),
        (4, 0), (4, 1), (4, 10), (4, 16), (4, 20), (4, 21),
        (5, 0), (5, 1), (5, 10), (5, 14), (5, 16), (5, 17), (5, 22), (5, 24),
        (6, 10), (6, 16), (6, 24),
        (7, 11), (7, 15),
        (8, 12), (8, 13),
    ]
    return _embed(rows, cols, cells, top=1, left=1)


PATTERNS = {
    'random': random_grid,
    'glider': glider_grid,
    'pulsar': pulsar_grid,
    'gosper': gosper_glider_gun_grid,
    'blinker': blinker_grid,
}


# --- CLI rendering --------------------------------------------------------

def render(grid: np.ndarray, alive_char: str = '█') -> str:
    """Render a grid as a string of ' '/'█' rows."""
    out_rows = []
    for row in grid:
        out_rows.append(''.join(alive_char if c else ' ' for c in row))
    return '\n'.join(out_rows)


def _clear() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Conway's Game of Life — CLI")
    parser.add_argument('--pattern', choices=list(PATTERNS), default='random',
                        help='Initial pattern (default: random)')
    parser.add_argument('--rows', type=int, default=30)
    parser.add_argument('--cols', type=int, default=80)
    parser.add_argument('--density', type=float, default=0.25,
                        help='Random fill density (0..1)')
    parser.add_argument('--fps', type=float, default=12.0)
    parser.add_argument('--steps', type=int, default=400,
                        help='Generations to simulate before stopping')
    parser.add_argument('--bounded', action='store_true',
                        help='Use bounded (zero-padded) edges instead of toroidal')
    parser.add_argument('--seed', type=int, default=None)
    args = parser.parse_args(argv)

    if args.pattern == 'random':
        grid = random_grid(args.rows, args.cols, args.density, seed=args.seed)
    elif args.pattern == 'blinker':
        grid = blinker_grid(args.rows, args.cols)
    elif args.pattern == 'glider':
        grid = glider_grid(args.rows, args.cols)
    elif args.pattern == 'pulsar':
        grid = pulsar_grid(args.rows, args.cols)
    elif args.pattern == 'gosper':
        grid = gosper_glider_gun_grid(args.rows, args.cols)
    else:  # pragma: no cover — argparse guards this
        raise SystemExit(f'unknown pattern: {args.pattern}')

    delay = 1.0 / max(args.fps, 0.1)
    toroidal = not args.bounded

    try:
        for gen in range(args.steps):
            _clear()
            print(f"Conway's Game of Life — pattern={args.pattern} "
                  f"gen={gen} alive={int(grid.sum())} "
                  f"edges={'toroidal' if toroidal else 'bounded'}")
            print(render(grid))
            print('Ctrl+C to stop.')
            time.sleep(delay)
            grid = step(grid, toroidal=toroidal)
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main(sys.argv[1:])
