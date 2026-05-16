"""Bouncing DVD Logo — CLI.

The classic 90s screensaver: a "DVD" logo bounces around the screen,
flips its color on every wall hit, and very occasionally smashes
exactly into a corner — the rare event that delights anyone watching.

Run:
    uv run python bouncing_dvd/bouncing_dvd.py
    uv run python bouncing_dvd/bouncing_dvd.py --logos 3 --width 100 --height 32
    uv run python bouncing_dvd/bouncing_dvd.py --probability 50000

A logo is a small axis-aligned rectangle moving with integer velocity
``(dx, dy) in {-1, +1} x {-1, +1}``. On each step:

    1. Tentatively advance ``(x + dx, y + dy)``.
    2. If a wall would be crossed, reflect the corresponding velocity
       component AND cycle the color.
    3. If both components reflect on the same step, that's a corner
       hit — count it.

The ``Logo`` class is pure (no I/O, no rng inside ``step``), so the CLI,
GUI, and TUI can all reuse the same physics.

Twist
-----
The headline trick is a Monte Carlo estimate of the **corner-hit
probability** — run many simulations from random starts and report
the empirical rate. For a w×h field with a 1×1 logo this approaches
``2 / (lcm(w-1, h-1))`` per step in the limit; we measure it directly.
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field

# 8 cycle colors — bright, distinguishable, screensaver-vibes.
COLORS: tuple[str, ...] = (
    'red',
    'orange',
    'yellow',
    'green',
    'cyan',
    'blue',
    'magenta',
    'white',
)

# ANSI 256-color codes for each name above. Used only by the CLI renderer.
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


@dataclass
class Logo:
    """A single bouncing DVD logo.

    Coordinates are integer cell positions of the logo's top-left corner.
    The logo occupies ``logo_w`` cells horizontally and ``logo_h`` vertically.

    Attributes
    ----------
    x, y : int
        Top-left position.
    dx, dy : int
        Velocity per step. Each must be ``+1`` or ``-1``.
    color_idx : int
        Index into :data:`COLORS`.
    bounces : int
        Number of wall reflections this logo has performed (1 per axis).
        Two-axis (corner) hits count as 2 bounces AND increment ``corners``.
    corners : int
        Number of corner hits (both axes reflected on the same step).
    """

    x: int
    y: int
    dx: int
    dy: int
    color_idx: int
    bounces: int = 0
    corners: int = 0
    history: list[tuple[int, int]] = field(default_factory=list, repr=False)

    def step(self, width: int, height: int, logo_w: int, logo_h: int) -> bool:
        """Advance one frame; return True iff this step was a corner hit.

        ``width``/``height`` are the play-field dimensions in cells.
        The logo's right edge is at ``x + logo_w``, bottom edge at
        ``y + logo_h``; both must stay within the field.
        """
        if width <= logo_w or height <= logo_h:
            # Field too small — clamp and idle. Avoids divide-by-zero
            # corner cases in tiny terminals.
            self.x = max(0, min(self.x, width - logo_w))
            self.y = max(0, min(self.y, height - logo_h))
            return False

        # Tentative new position.
        nx = self.x + self.dx
        ny = self.y + self.dy

        hit_x = False
        hit_y = False

        if nx < 0:
            nx = -nx                           # reflect off left wall
            self.dx = -self.dx
            hit_x = True
        elif nx + logo_w > width:
            # nx_max = width - logo_w; reflect symmetrically off it.
            nx = 2 * (width - logo_w) - nx
            self.dx = -self.dx
            hit_x = True

        if ny < 0:
            ny = -ny
            self.dy = -self.dy
            hit_y = True
        elif ny + logo_h > height:
            ny = 2 * (height - logo_h) - ny
            self.dy = -self.dy
            hit_y = True

        self.x = nx
        self.y = ny

        if hit_x or hit_y:
            # Each axis reflected counts as one bounce. Corner = 2.
            self.bounces += int(hit_x) + int(hit_y)
            # Cycle to next color on every wall hit (single OR corner).
            self.color_idx = (self.color_idx + 1) % len(COLORS)

        corner = hit_x and hit_y
        if corner:
            self.corners += 1

        return corner

    @property
    def color(self) -> str:
        return COLORS[self.color_idx]


def random_logo(width: int, height: int, logo_w: int, logo_h: int,
                rng: random.Random | None = None) -> Logo:
    """Spawn a logo at a random interior position with random velocity & color."""
    rng = rng or random.Random()
    x_max = max(width - logo_w - 1, 1)
    y_max = max(height - logo_h - 1, 1)
    return Logo(
        x=rng.randint(1, x_max),
        y=rng.randint(1, y_max),
        dx=rng.choice((-1, 1)),
        dy=rng.choice((-1, 1)),
        color_idx=rng.randrange(len(COLORS)),
    )


def render(width: int, height: int, logos: list[Logo],
           *, color: bool = True, label: str = 'DVD') -> str:
    """Render the play field as a single multi-line string.

    Each logo is drawn as a label (default 'DVD') padded to ``logo_w``
    characters wide and ``logo_h`` rows tall. If logos overlap, the
    later logo wins — same as the GUI canvas z-order.
    """
    grid: list[list[str]] = [[' '] * width for _ in range(height)]

    for lg in logos:
        # Logo width/height are inferred from the label length / 1 row.
        lw = len(label)
        lh = 1
        # Use the logo's *own* extents to draw — the caller is responsible
        # for stepping with matching logo_w/logo_h.
        for dy in range(lh):
            for dx in range(lw):
                px = lg.x + dx
                py = lg.y + dy
                if 0 <= px < width and 0 <= py < height:
                    ch = label[dx]
                    if color:
                        grid[py][px] = f'{_ANSI_FG[lg.color]}{ch}{_RESET}'
                    else:
                        grid[py][px] = ch

    return '\n'.join(''.join(row) for row in grid)


def estimate_corner_probability(width: int, height: int,
                                 logo_w: int = 3, logo_h: int = 1,
                                 trials: int = 5,
                                 steps_per_trial: int = 100_000,
                                 seed: int | None = None) -> dict:
    """Monte-Carlo estimate of corner-hit rate per step.

    For each trial, spawn a random logo and step it ``steps_per_trial``
    times; count corners. The reported rate is corners / total_steps,
    averaged over trials. Useful for the "rare event" stat.
    """
    rng = random.Random(seed)
    total_corners = 0
    total_steps = 0
    per_trial: list[int] = []
    for _ in range(trials):
        lg = random_logo(width, height, logo_w, logo_h, rng)
        c0 = lg.corners
        for _ in range(steps_per_trial):
            lg.step(width, height, logo_w, logo_h)
        per_trial.append(lg.corners - c0)
        total_corners += lg.corners - c0
        total_steps += steps_per_trial
    rate = total_corners / total_steps if total_steps else 0.0
    # Theoretical limit: corners coincide on a period of lcm(w-1, h-1)
    # steps for a 1x1 logo. For wider logos the field shrinks accordingly.
    eff_w = max(width - logo_w, 1)
    eff_h = max(height - logo_h, 1)
    period = math.lcm(eff_w, eff_h)
    theoretical = 1.0 / period if period else 0.0
    return {
        'trials': trials,
        'steps_per_trial': steps_per_trial,
        'corners': total_corners,
        'empirical_rate': rate,
        'theoretical_rate': theoretical,
        'per_trial': per_trial,
    }


def _clear() -> None:
    os.system('cls' if os.name == 'nt' else 'clear')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description='Bouncing DVD Logo — CLI')
    parser.add_argument('--width', type=int, default=78,
                        help='Field width in cells (default 78)')
    parser.add_argument('--height', type=int, default=22,
                        help='Field height in rows (default 22)')
    parser.add_argument('--logos', type=int, default=1,
                        help='Number of bouncing logos (default 1)')
    parser.add_argument('--label', type=str, default='DVD',
                        help='Logo text (default "DVD")')
    parser.add_argument('--fps', type=float, default=15.0)
    parser.add_argument('--steps', type=int, default=2_000,
                        help='Frames to render before stopping')
    parser.add_argument('--seed', type=int, default=None)
    parser.add_argument('--no-color', action='store_true')
    parser.add_argument('--probability', type=int, default=0, metavar='STEPS',
                        help='Skip the animation; instead estimate the '
                             'corner-hit probability over STEPS frames.')
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)
    logo_w = len(args.label)
    logo_h = 1

    if args.probability:
        result = estimate_corner_probability(
            args.width, args.height, logo_w, logo_h,
            trials=5, steps_per_trial=args.probability, seed=args.seed)
        print(f'Field: {args.width}x{args.height}, '
              f'logo: {logo_w}x{logo_h}')
        print(f'Trials: {result["trials"]}  '
              f'Steps/trial: {result["steps_per_trial"]:,}')
        print(f'Corners observed: {result["corners"]}  '
              f'(per trial: {result["per_trial"]})')
        print(f'Empirical rate:   {result["empirical_rate"]:.6f} per step')
        print(f'Theoretical rate: {result["theoretical_rate"]:.6f} per step '
              '(1/lcm(w-logo_w, h-logo_h))')
        return

    logos = [random_logo(args.width, args.height, logo_w, logo_h, rng)
             for _ in range(max(1, args.logos))]
    use_color = not args.no_color

    delay = 1.0 / max(args.fps, 0.1)

    try:
        for frame in range(args.steps):
            _clear()
            corner_this_frame = False
            for lg in logos:
                if lg.step(args.width, args.height, logo_w, logo_h):
                    corner_this_frame = True
            print(f'Bouncing DVD  frame={frame}  '
                  f'logos={len(logos)}  '
                  f'bounces={sum(l.bounces for l in logos)}  '
                  f'corners={sum(l.corners for l in logos)}'
                  f'{"  *** CORNER! ***" if corner_this_frame else ""}')
            print(render(args.width, args.height, logos,
                         color=use_color, label=args.label))
            print('Ctrl+C to stop.')
            time.sleep(delay)
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main(sys.argv[1:])
