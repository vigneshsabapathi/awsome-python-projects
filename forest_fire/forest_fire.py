"""Drossel-Schwabl Forest Fire — CLI.

A self-organized-criticality cellular automaton on a 2D grid.
Each cell is one of three states:

    0 = EMPTY    (bare ground)
    1 = TREE     (alive tree)
    2 = BURNING  (tree currently on fire)

Synchronous update rules (per generation):

    1. BURNING  -> EMPTY                       (the fire burns out)
    2. TREE     -> BURNING  if any neighbor is BURNING
    3. TREE     -> BURNING  spontaneously with probability ``p_lightning``
    4. EMPTY    -> TREE     with probability ``p_grow``

In the limit p_lightning << p_grow << 1 the system organizes itself near a
critical tree density (~0.4 for von-Neumann neighborhoods on a square lattice)
and produces fires whose sizes follow a power-law distribution — the canonical
demonstration of self-organized criticality (Drossel & Schwabl, 1992).

Run:
    uv run python forest_fire/forest_fire.py
    uv run python forest_fire/forest_fire.py --rows 30 --cols 60 --p 0.02 --f 0.0005
    uv run python forest_fire/forest_fire.py --wind east --steps 1000

Implementation note
-------------------
``step()`` is fully vectorized: the "any-burning-neighbor" check is computed by
4 (or 8) shifted boolean copies of the BURNING mask OR'ed together — never a
Python loop over cells. Wind anisotropy is implemented by **dropping** the
upwind shifts so fire only spreads in the wind direction (plus its two
perpendicular neighbors).
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time

import numpy as np


# Cell states
EMPTY = 0
TREE = 1
BURNING = 2

# Wind directions — which neighbor offsets contribute to "is a burning
# neighbor reaching me?". 'none' = isotropic von-Neumann (N, S, E, W).
# Each direction includes its main axis and the two perpendicular neighbors —
# fire spreads downwind plus a little laterally. Upwind spread is dropped.
NEIGHBOR_OFFSETS: dict[str, tuple[tuple[int, int], ...]] = {
    'none':  ((-1, 0), (1, 0), (0, -1), (0, 1)),
    'north': ((-1, 0), (0, -1), (0, 1)),           # fire spreads up + sideways
    'south': (( 1, 0), (0, -1), (0, 1)),
    'east':  (( 0, 1), (-1, 0), (1, 0)),
    'west':  (( 0,-1), (-1, 0), (1, 0)),
    'moore': ((-1,-1), (-1, 0), (-1, 1),
              ( 0,-1),          ( 0, 1),
              ( 1,-1), ( 1, 0), ( 1, 1)),
}


def step(grid: np.ndarray, p_grow: float, p_lightning: float,
         rng: random.Random | np.random.Generator | None = None,
         *, wind: str = 'none') -> np.ndarray:
    """Advance one Drossel-Schwabl generation.

    Parameters
    ----------
    grid : np.ndarray
        2D int array of cell states (0 empty, 1 tree, 2 burning).
    p_grow : float
        Probability an empty cell grows a tree this step.
    p_lightning : float
        Probability a tree spontaneously ignites this step.
    rng : random.Random | np.random.Generator | None
        Source of randomness. ``random.Random`` is accepted (the per-cell
        Bernoulli draws are vectorized via a fresh ``np.random.Generator``
        seeded from it). ``None`` uses the default unseeded generator.
    wind : str
        One of 'none', 'north', 'south', 'east', 'west', 'moore'.
        Selects which neighbor offsets count as "burning neighbor". 'none'
        is the classic 4-neighbor von Neumann rule; the cardinal directions
        drop the upwind shift to model wind-driven anisotropic spread.

    Returns
    -------
    np.ndarray
        New grid (same shape & dtype) — a fresh allocation. The input is
        never mutated, which is required for synchronous CA updates.
    """
    if grid.ndim != 2:
        raise ValueError('grid must be 2D')
    if wind not in NEIGHBOR_OFFSETS:
        raise ValueError(f'unknown wind: {wind!r}')

    # --- Promote whatever rng we got to a numpy Generator for vectorized draws.
    if rng is None:
        np_rng = np.random.default_rng()
    elif isinstance(rng, np.random.Generator):
        np_rng = rng
    elif isinstance(rng, random.Random):
        # Seed a numpy generator from the stdlib rng so the user's seed
        # propagates and successive calls advance the stream deterministically.
        np_rng = np.random.default_rng(rng.getrandbits(64))
    else:
        raise TypeError(f'unsupported rng type: {type(rng).__name__}')

    burning = (grid == BURNING)
    tree = (grid == TREE)
    empty = (grid == EMPTY)

    # --- Vectorized "any neighbor burning?" via shifted ORs.
    # np.roll wraps the grid edges (toroidal). For a forest that's reasonable
    # and matches the GoL conventions used elsewhere in the project.
    neighbor_burning = np.zeros_like(burning)
    for dr, dc in NEIGHBOR_OFFSETS[wind]:
        neighbor_burning |= np.roll(burning, (dr, dc), axis=(0, 1))

    # --- Per-cell random draws (only meaningful where the rule fires).
    grow_roll = np_rng.random(grid.shape) < p_grow
    lightning_roll = np_rng.random(grid.shape) < p_lightning

    # --- Apply rules to a fresh array (synchronous update).
    new = np.zeros_like(grid)

    # Trees: ignite if any burning neighbor or struck by lightning, else stay.
    ignites = tree & (neighbor_burning | lightning_roll)
    survives = tree & ~ignites
    new[ignites] = BURNING
    new[survives] = TREE

    # Empties: grow a tree with prob p_grow.
    grows = empty & grow_roll
    stays_empty = empty & ~grows
    new[grows] = TREE
    # stays_empty are already 0, no-op.
    _ = stays_empty  # explicit (silences linters that flag unused locals)

    # Burning cells become empty next step (already 0 in `new`).
    return new


# --- Initial conditions ---------------------------------------------------

def random_grid(rows: int = 30, cols: int = 60, density: float = 0.55,
                seed: int | None = None) -> np.ndarray:
    """Random forest with the given tree density. No initial fires."""
    np_rng = np.random.default_rng(seed)
    grid = np.zeros((rows, cols), dtype=np.int8)
    grid[np_rng.random((rows, cols)) < density] = TREE
    return grid


def empty_grid(rows: int = 30, cols: int = 60) -> np.ndarray:
    """Bare ground — trees will grow over time at rate ``p_grow``."""
    return np.zeros((rows, cols), dtype=np.int8)


def seeded_fire_grid(rows: int = 30, cols: int = 60, density: float = 0.55,
                     seed: int | None = None) -> np.ndarray:
    """Random forest with a small ignition spark at the center."""
    grid = random_grid(rows, cols, density, seed=seed)
    cr, cc = rows // 2, cols // 2
    if grid[cr, cc] == TREE:
        grid[cr, cc] = BURNING
    else:
        # Force a burn at center even if no tree there — gives the user
        # something to watch instead of an unlit forest.
        grid[cr, cc] = BURNING
    return grid


# --- CLI rendering --------------------------------------------------------

# ANSI 256-color glyphs for empty/tree/burning. 'tput'-free, just escape codes.
_RESET = '\x1b[0m'
_FG_BROWN = '\x1b[38;5;94m'    # bare ground
_FG_GREEN = '\x1b[38;5;34m'    # tree
_FG_FIRE = '\x1b[38;5;202m'    # burning (orange)


def render(grid: np.ndarray, *, color: bool = True) -> str:
    """Render a grid as a colored multi-line string."""
    rows = []
    for row in grid:
        chars = []
        for cell in row:
            if cell == BURNING:
                chars.append(f'{_FG_FIRE}#{_RESET}' if color else '#')
            elif cell == TREE:
                chars.append(f'{_FG_GREEN}T{_RESET}' if color else 'T')
            else:
                chars.append(f'{_FG_BROWN}.{_RESET}' if color else '.')
        rows.append(''.join(chars))
    return '\n'.join(rows)


def density(grid: np.ndarray) -> float:
    """Fraction of cells that are TREE — the order parameter."""
    return float((grid == TREE).sum()) / grid.size


def _clear() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Drossel-Schwabl Forest Fire — CLI')
    parser.add_argument('--rows', type=int, default=30)
    parser.add_argument('--cols', type=int, default=60)
    parser.add_argument('--p', '--p-grow', dest='p_grow', type=float, default=0.02,
                        help='Per-step tree growth probability (default 0.02)')
    parser.add_argument('--f', '--p-lightning', dest='p_lightning', type=float,
                        default=0.0005,
                        help='Per-step lightning strike probability (default 0.0005)')
    parser.add_argument('--density', type=float, default=0.55,
                        help='Initial tree density (0..1, default 0.55)')
    parser.add_argument('--wind', choices=list(NEIGHBOR_OFFSETS), default='none',
                        help='Wind direction (anisotropic spread)')
    parser.add_argument('--fps', type=float, default=10.0)
    parser.add_argument('--steps', type=int, default=400,
                        help='Generations to simulate before stopping')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--no-color', action='store_true')
    args = parser.parse_args(argv)

    rng = random.Random(args.seed) if args.seed is not None else random.Random()
    grid = seeded_fire_grid(args.rows, args.cols, args.density, seed=args.seed)

    delay = 1.0 / max(args.fps, 0.1)
    use_color = not args.no_color

    try:
        for gen in range(args.steps):
            _clear()
            trees = int((grid == TREE).sum())
            burning = int((grid == BURNING).sum())
            print(f'Drossel-Schwabl Forest Fire  '
                  f'gen={gen}  trees={trees}  burning={burning}  '
                  f'density={density(grid):.3f}  wind={args.wind}  '
                  f'p={args.p_grow}  f={args.p_lightning}')
            print(render(grid, color=use_color))
            print('Ctrl+C to stop.')
            time.sleep(delay)
            grid = step(grid, args.p_grow, args.p_lightning, rng, wind=args.wind)
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main(sys.argv[1:])
