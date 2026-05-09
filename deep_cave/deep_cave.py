"""Deep Cave — CLI.

Procedurally-generated infinite-scroll cave. Each printed row shows a
horizontal slice of an underground tunnel: walls (``#``) on either side and
walkable floor (`` ``) in the middle. The tunnel's left edge and width drift
row-to-row via a constrained random walk, producing a hand-carved feel as
the screen scrolls.

Run:
    uv run python deep_cave/deep_cave.py
    uv run python deep_cave/deep_cave.py --width 80 --fps 24 --seed 42

Pure functions
--------------
``next_row(prev_left, prev_width, rng, total_width=70)`` — given the previous
row's tunnel position, returns ``(new_left, new_width, ascii_row)`` for the
next row. Deterministic for a given ``rng`` state, so seeded runs are
reproducible.

Twist: at low probability a row sprinkles a hazard or treasure into the
walkable floor — ``*`` gem, ``~`` water trickle, ``o`` boulder. They hint
the cave is alive without changing the wall geometry.
"""
from __future__ import annotations

import argparse
import random
import sys
import time

# --- Geometry constants ---------------------------------------------------

DEFAULT_WIDTH = 70

WALL = '#'
FLOOR = ' '

# Tunnel must always leave at least one wall column on each side, and be at
# least this wide. ``MIN_WIDTH`` enforces the floor is actually walkable.
MIN_WIDTH = 6
MAX_WIDTH_RATIO = 0.75   # tunnel can fill at most 75% of total width
MIN_LEFT_MARGIN = 1      # at least one '#' on the left
MIN_RIGHT_MARGIN = 1     # at least one '#' on the right

# --- Twist: hazards and treasures ----------------------------------------

# (char, probability per row, label printed once on first sighting)
HAZARDS: list[tuple[str, float, str]] = [
    ('*', 0.020, 'a glittering gem'),
    ('~', 0.030, 'a trickle of water'),
    ('o', 0.025, 'a fallen boulder'),
]


# --- Core algorithm -------------------------------------------------------

def next_row(
    prev_left: int,
    prev_width: int,
    rng: random.Random,
    total_width: int = DEFAULT_WIDTH,
) -> tuple[int, int, str]:
    """Return the next row of the cave: ``(new_left, new_width, ascii_row)``.

    Uses a constrained random walk so the tunnel meanders smoothly:

    * ``new_left`` shifts by -1, 0, or +1 from ``prev_left``
    * ``new_width`` shifts by -1, 0, or +1 from ``prev_width``
    * Both are clamped so the tunnel stays inside the canvas with at
      least one wall column on each side.

    The output row is exactly ``total_width`` characters: walls (``#``),
    floor (`` ``), and at most one twist character (``*``/``~``/``o``)
    placed inside the floor span.
    """
    if total_width < MIN_WIDTH + MIN_LEFT_MARGIN + MIN_RIGHT_MARGIN:
        raise ValueError(f'total_width must be >= {MIN_WIDTH + 2}')

    max_width = max(MIN_WIDTH, int(total_width * MAX_WIDTH_RATIO))

    # Width drift: -1, 0, +1 — clamp to [MIN_WIDTH, max_width].
    width_delta = rng.choice((-1, 0, 0, 1))  # bias toward stable width
    new_width = max(MIN_WIDTH, min(max_width, prev_width + width_delta))

    # Left-edge drift: -1, 0, +1 — clamp so tunnel stays inside the canvas.
    left_delta = rng.choice((-1, 0, 0, 1))
    new_left = prev_left + left_delta
    min_left = MIN_LEFT_MARGIN
    max_left = total_width - new_width - MIN_RIGHT_MARGIN
    if max_left < min_left:
        # Pathological canvas — collapse to a one-column tunnel at center.
        new_left = total_width // 2
        new_width = 1
    else:
        new_left = max(min_left, min(max_left, new_left))

    # Build the row: walls, then floor span, then walls.
    chars = [WALL] * new_left + [FLOOR] * new_width \
        + [WALL] * (total_width - new_left - new_width)

    # Twist: at most one hazard/treasure per row, dropped somewhere on
    # the floor (never on a wall). Probabilities are independent per
    # candidate, but we bail after the first hit so rows stay readable.
    for char, prob, _label in HAZARDS:
        if rng.random() < prob and new_width >= 3:
            # Avoid placing right against a wall — gives the eye breathing room.
            slot = rng.randrange(new_left + 1, new_left + new_width - 1)
            chars[slot] = char
            break

    return new_left, new_width, ''.join(chars)


def initial_tunnel(total_width: int = DEFAULT_WIDTH) -> tuple[int, int]:
    """Pick a sensible starting ``(left, width)`` centered in the canvas."""
    width = max(MIN_WIDTH, total_width // 3)
    left = (total_width - width) // 2
    return left, width


def hazard_label(char: str) -> str | None:
    """Return the human-readable label for a twist character, or ``None``."""
    for c, _p, label in HAZARDS:
        if c == char:
            return label
    return None


# --- CLI driver -----------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Deep Cave — infinite procedural cave descent.')
    parser.add_argument('--width', type=int, default=DEFAULT_WIDTH,
                        help=f'Total row width (default: {DEFAULT_WIDTH})')
    parser.add_argument('--fps', type=float, default=30.0,
                        help='Rows per second (default: 30)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Optional seed for reproducible caves')
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    left, width = initial_tunnel(args.width)
    delay = 1.0 / max(args.fps, 0.1)

    print('Deep Cave — Ctrl+C to surface.')
    seen: set[str] = set()
    depth = 0
    try:
        while True:
            left, width, row = next_row(left, width, rng, args.width)
            sys.stdout.write(row + '\n')
            sys.stdout.flush()
            depth += 1

            # Whisper a hint the first time each hazard appears.
            for char, _p, _label in HAZARDS:
                if char in row and char not in seen:
                    seen.add(char)
                    label = hazard_label(char) or 'something'
                    sys.stdout.write(
                        f'  ... you spot {label} at depth {depth}.\n')
                    sys.stdout.flush()

            time.sleep(delay)
    except KeyboardInterrupt:
        print(f'\nYou climbed back out. Final depth: {depth} rows.')


if __name__ == '__main__':
    main(sys.argv[1:])
