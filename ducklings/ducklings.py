"""Ducklings — CLI.

Animated row of ASCII ducks waddling across the screen with bobbing motion.
Features three duck species (regular, mallard, mandarin) plus a mother duck
that leads, with ducklings following in her wake with positional lag.

Run:
    uv run python ducklings/ducklings.py
    uv run python ducklings/ducklings.py --ducks 5 --width 80
    uv run python ducklings/ducklings.py --species mallard --fps 8
"""
from __future__ import annotations

import argparse
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# ASCII art frames — each species has 2 animation frames (wing up / wing down)
# and 2 bob offsets (normal / raised).
#
# Frame layout: list of lines (top to bottom). All frames for a species must
# have the same width and height.
# ---------------------------------------------------------------------------

# Regular duck — classic ASCII rubber-duck style
_REGULAR_FRAMES: list[list[str]] = [
    # frame 0 — wing down
    [
        " __  ",
        "<(o) ",
        " )>  ",
        "~~~~~",
    ],
    # frame 1 — wing up
    [
        " __  ",
        "<(o)~",
        " )>  ",
        "~~~~~",
    ],
]

# Mallard — slightly larger, more naturalistic
_MALLARD_FRAMES: list[list[str]] = [
    # frame 0 — wing folded
    [
        "  __   ",
        " (oo)  ",
        "_(__)_ ",
        "~~~~~~~",
    ],
    # frame 1 — wing out
    [
        "  __   ",
        "_(oo)> ",
        "(___)  ",
        "~~~~~~~",
    ],
]

# Mandarin — colorful, elaborate crest
_MANDARIN_FRAMES: list[list[str]] = [
    # frame 0
    [
        " ,^,  ",
        "(>*<) ",
        " \\/  ",
        "~~~~~~",
    ],
    # frame 1
    [
        " ,^,  ",
        "(>*<)~",
        " \\/  ",
        "~~~~~~",
    ],
]

SPECIES_FRAMES: dict[str, list[list[str]]] = {
    "regular":  _REGULAR_FRAMES,
    "mallard":  _MALLARD_FRAMES,
    "mandarin": _MANDARIN_FRAMES,
}

# Bob offsets: which lines to shift up (0 = normal, 1 = raised by 1 row)
# Achieved by prepending/removing a blank line.
BOB_OFFSETS = [0, 1, 0]  # cycle: normal, up, normal


# ---------------------------------------------------------------------------
# Dataclass: Duck
# ---------------------------------------------------------------------------

@dataclass
class Duck:
    """A single duck on the pond.

    Attributes
    ----------
    x : float
        Horizontal position (left edge of sprite), fractional for smooth motion.
    frame : int
        Animation frame index (cycles through wing positions).
    bob : int
        Bob phase index (cycles through BOB_OFFSETS).
    species : str
        One of 'regular', 'mallard', 'mandarin'.
    lag_history : list[float]
        Past x positions used to create the mother→duckling lag chain.
    """

    x: float
    frame: int = 0
    bob: int = 0
    species: str = "regular"
    lag_history: list[float] = field(default_factory=list)

    @property
    def frames(self) -> list[list[str]]:
        return SPECIES_FRAMES[self.species]

    @property
    def art_width(self) -> int:
        return len(self.frames[0][0])

    @property
    def art_height(self) -> int:
        return len(self.frames[0])

    @property
    def current_frame_lines(self) -> list[str]:
        f = self.frames[self.frame % len(self.frames)]
        bob_offset = BOB_OFFSETS[self.bob % len(BOB_OFFSETS)]
        if bob_offset:
            # Raised: shift art up by prepending blank, dropping last water line
            blank = " " * self.art_width
            return [blank] + f[:-1]
        return f


# ---------------------------------------------------------------------------
# Class: Pond
# ---------------------------------------------------------------------------

class Pond:
    """Manages a collection of ducks waddling across a pond.

    The mother duck (index 0) moves at full speed. Each subsequent duckling
    follows the *previous* duck's position with a lag of ``LAG_STEPS`` history
    entries — giving a tail-following formation.

    Parameters
    ----------
    width : int
        Display width in characters.
    num_ducks : int
        Total ducks including the mother.
    rng : random.Random | None
        Optional seeded RNG for reproducibility.
    """

    LAG_STEPS = 12   # frames of lag per duckling in the chain
    SPEED = 1.2      # cells per step for mother duck

    def __init__(
        self,
        width: int = 78,
        num_ducks: int = 4,
        rng: Optional[random.Random] = None,
    ) -> None:
        self.width = width
        self.rng = rng or random.Random()
        num_ducks = max(1, num_ducks)

        species_pool = ["regular", "mallard", "mandarin"]
        # Mother is always a mallard; ducklings cycle species
        species_list = ["mallard"] + [
            species_pool[i % len(species_pool)] for i in range(num_ducks - 1)
        ]

        # Stagger starting positions so ducks don't pile up
        self.ducks: list[Duck] = []
        for i in range(num_ducks):
            sp = species_list[i]
            art_w = len(SPECIES_FRAMES[sp][0][0])
            # Space ducks with gap between them; start off left edge
            start_x = -(i * (art_w + 3))
            d = Duck(
                x=float(start_x),
                frame=self.rng.randint(0, 1),
                bob=self.rng.randint(0, len(BOB_OFFSETS) - 1),
                species=sp,
            )
            # Pre-fill history so lag works from frame 0
            for _ in range(num_ducks * self.LAG_STEPS + 1):
                d.lag_history.append(float(start_x))
            self.ducks.append(d)

        self._step_count = 0

    def step(self) -> None:
        """Advance all ducks by one animation frame."""
        self._step_count += 1

        # Mother duck moves freely, wrapping around with a brief gap
        mother = self.ducks[0]
        mother.x += self.SPEED
        wrap_at = self.width + mother.art_width + 5
        if mother.x > wrap_at:
            mother.x -= wrap_at + mother.art_width

        # Record history for lag chain
        mother.lag_history.append(mother.x)

        # Each subsequent duckling follows the previous duck with lag
        for i in range(1, len(self.ducks)):
            prev = self.ducks[i - 1]
            duck = self.ducks[i]
            # Pull from prev duck's history at LAG_STEPS ago
            lag_idx = max(0, len(prev.lag_history) - self.LAG_STEPS)
            target_x = prev.lag_history[lag_idx]
            duck.x = target_x
            duck.lag_history.append(duck.x)
            # Trim history to avoid unbounded growth
            if len(duck.lag_history) > self.LAG_STEPS * 3:
                duck.lag_history = duck.lag_history[-self.LAG_STEPS * 2:]

        # Trim mother history too
        if len(mother.lag_history) > self.LAG_STEPS * (len(self.ducks) + 2):
            mother.lag_history = mother.lag_history[-(self.LAG_STEPS * (len(self.ducks) + 1)):]

        # Advance animation frames (wing + bob) every other step
        if self._step_count % 2 == 0:
            for duck in self.ducks:
                duck.frame = (duck.frame + 1) % len(duck.frames)
        if self._step_count % 3 == 0:
            for duck in self.ducks:
                duck.bob = (duck.bob + 1) % len(BOB_OFFSETS)

    def render(self) -> str:
        """Render all ducks onto a blank canvas; return multi-line string.

        Only ducks whose bounding box intersects [0, width) are drawn.
        """
        # Determine canvas height (max art_height across all ducks + 1 for bob)
        max_h = max(d.art_height for d in self.ducks) + 1
        canvas: list[list[str]] = [[" "] * self.width for _ in range(max_h)]

        for duck in self.ducks:
            lines = duck.current_frame_lines
            col = int(duck.x)
            row_offset = max_h - duck.art_height - 1  # bottom-align all ducks

            for row_i, line in enumerate(lines):
                r = row_offset + row_i
                if r < 0 or r >= max_h:
                    continue
                for col_i, ch in enumerate(line):
                    c = col + col_i
                    if 0 <= c < self.width:
                        canvas[r][c] = ch

        return "\n".join("".join(row) for row in canvas)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Ducklings — animated ASCII ducks")
    parser.add_argument("--width", type=int, default=78,
                        help="Display width (default 78)")
    parser.add_argument("--ducks", type=int, default=5,
                        help="Number of ducks including mother (default 5)")
    parser.add_argument("--fps", type=float, default=10.0,
                        help="Frames per second (default 10)")
    parser.add_argument("--steps", type=int, default=1000,
                        help="Frames to run before stopping (default 1000)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for reproducibility")
    parser.add_argument("--species", type=str, default=None,
                        choices=list(SPECIES_FRAMES.keys()),
                        help="Force all ducks to a single species")
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    pond = Pond(width=args.width, num_ducks=args.ducks, rng=rng)

    if args.species:
        for d in pond.ducks:
            d.species = args.species

    delay = 1.0 / max(args.fps, 0.1)

    try:
        for _ in range(args.steps):
            pond.step()
            _clear()
            print("  Ducklings  —  quack quack!  (Ctrl+C to stop)")
            print(pond.render())
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\nStopped. The ducks waddled away.")


if __name__ == "__main__":
    main(sys.argv[1:])
