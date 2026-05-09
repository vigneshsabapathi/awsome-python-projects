"""Mondrian Art Generator — recursive subdivision into colored rectangles.

Inspired by Piet Mondrian's *De Stijl* paintings: a canvas is recursively split
along random horizontal/vertical lines, with each leaf rectangle painted in a
weighted-random primary color (red/yellow/blue/white). Black borders frame
each rectangle.

Three style presets:

- ``mondrian``   — classic De Stijl primaries (red/yellow/blue + white)
- ``rothko``     — horizontal-only splits, muted warm bands
- ``bauhaus``    — geometric split with extended primaries (incl. black)

Run as a script to render to PNG via Pillow:

    uv run python mondrian/mondrian.py --width 1200 --height 900 --depth 5

Tags: generative-art, recursion, fractals, geometry
"""
from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
from typing import Iterable, Sequence

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Color palettes — RGB tuples. Weighted such that white dominates background.
# ---------------------------------------------------------------------------
MONDRIAN_PALETTE: tuple[tuple[str, tuple[int, int, int], int], ...] = (
    # (name, rgb, weight)
    ('red',    (218,  41,  28), 1),
    ('yellow', (252, 209,  22), 1),
    ('blue',   ( 30,  64, 175), 1),
    ('white',  (245, 245, 240), 3),  # weight 3 -> dominant background
)

ROTHKO_PALETTE: tuple[tuple[str, tuple[int, int, int], int], ...] = (
    ('crimson', (158,  42,  43), 2),
    ('orange',  (214, 102,  45), 2),
    ('ochre',   (199, 145,  72), 2),
    ('plum',    ( 87,  35,  68), 1),
    ('cream',   (231, 213, 178), 1),
)

BAUHAUS_PALETTE: tuple[tuple[str, tuple[int, int, int], int], ...] = (
    ('red',    (218,  41,  28), 2),
    ('yellow', (252, 209,  22), 2),
    ('blue',   ( 30,  64, 175), 2),
    ('black',  ( 20,  20,  20), 1),
    ('white',  (245, 245, 240), 2),
)

PALETTES = {
    'mondrian': MONDRIAN_PALETTE,
    'rothko':   ROTHKO_PALETTE,
    'bauhaus':  BAUHAUS_PALETTE,
}

BORDER_COLOR = (15, 15, 15)
BORDER_WIDTH = 6  # pixels — only used by render_image; render_canvas uses tk
MIN_DIM = 40  # don't subdivide rectangles smaller than this on the split axis


# ---------------------------------------------------------------------------
# Pure data + generation
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Rect:
    """An axis-aligned rectangle painted a single color.

    Coordinates are in pixels, color is an RGB tuple. ``(x, y)`` is top-left.
    """
    x: int
    y: int
    w: int
    h: int
    color: tuple[int, int, int]

    @property
    def area(self) -> int:
        return self.w * self.h

    def bbox(self) -> tuple[int, int, int, int]:
        """Return ``(x0, y0, x1, y1)`` for Pillow / Tk drawing APIs."""
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def _weighted_choice(
    rng: random.Random,
    palette: Sequence[tuple[str, tuple[int, int, int], int]],
) -> tuple[int, int, int]:
    total = sum(w for _, _, w in palette)
    pick = rng.uniform(0, total)
    upto = 0.0
    for _name, rgb, weight in palette:
        upto += weight
        if pick <= upto:
            return rgb
    return palette[-1][1]


def _split_probability(w: int, h: int, max_dim: int) -> float:
    """Bigger rects are likelier to split; tiny rects almost never split."""
    size_factor = max(w, h) / max(max_dim, 1)
    # squeeze into [0.15, 0.95] so even small rects sometimes split and large
    # ones occasionally stop, which keeps the composition irregular.
    return max(0.15, min(0.95, size_factor))


def _subdivide(
    rect: Rect,
    rng: random.Random,
    depth: int,
    palette: Sequence[tuple[str, tuple[int, int, int], int]],
    horizontal_only: bool,
    max_dim: int,
) -> list[Rect]:
    """Recursively split ``rect`` until depth runs out or rect is too small."""
    too_small = rect.w < MIN_DIM * 2 and rect.h < MIN_DIM * 2
    if depth <= 0 or too_small:
        return [Rect(rect.x, rect.y, rect.w, rect.h,
                     _weighted_choice(rng, palette))]

    if rng.random() > _split_probability(rect.w, rect.h, max_dim):
        return [Rect(rect.x, rect.y, rect.w, rect.h,
                     _weighted_choice(rng, palette))]

    # Pick split axis. Rothko forces horizontal bands; Mondrian/Bauhaus
    # bias toward the longer axis so long thin rects don't cross-cut.
    if horizontal_only:
        axis = 'h'
    else:
        if rect.w > rect.h * 1.4:
            axis = 'v'
        elif rect.h > rect.w * 1.4:
            axis = 'h'
        else:
            axis = rng.choice(('h', 'v'))

    if axis == 'v' and rect.w >= MIN_DIM * 2:
        ratio = rng.uniform(0.3, 0.7)
        split_x = max(MIN_DIM, min(rect.w - MIN_DIM, int(rect.w * ratio)))
        left = Rect(rect.x, rect.y, split_x, rect.h, (0, 0, 0))
        right = Rect(rect.x + split_x, rect.y,
                     rect.w - split_x, rect.h, (0, 0, 0))
        return (_subdivide(left, rng, depth - 1, palette,
                           horizontal_only, max_dim)
                + _subdivide(right, rng, depth - 1, palette,
                             horizontal_only, max_dim))

    if axis == 'h' and rect.h >= MIN_DIM * 2:
        ratio = rng.uniform(0.3, 0.7)
        split_y = max(MIN_DIM, min(rect.h - MIN_DIM, int(rect.h * ratio)))
        top = Rect(rect.x, rect.y, rect.w, split_y, (0, 0, 0))
        bottom = Rect(rect.x, rect.y + split_y,
                      rect.w, rect.h - split_y, (0, 0, 0))
        return (_subdivide(top, rng, depth - 1, palette,
                           horizontal_only, max_dim)
                + _subdivide(bottom, rng, depth - 1, palette,
                             horizontal_only, max_dim))

    # Couldn't split on chosen axis (too small) — emit as leaf.
    return [Rect(rect.x, rect.y, rect.w, rect.h,
                 _weighted_choice(rng, palette))]


def generate(
    width: int,
    height: int,
    rng: random.Random | None = None,
    depth: int = 4,
    style: str = 'mondrian',
) -> list[Rect]:
    """Generate a list of leaf rectangles tiling the ``width × height`` canvas.

    Each rectangle is painted a single color drawn from the chosen palette.
    Successive rectangles share borders — drawing a black outline around each
    yields the iconic Mondrian grid.

    Parameters
    ----------
    width, height : int
        Canvas size in pixels. Must be positive.
    rng : random.Random | None
        Source of randomness. ``None`` uses a fresh ``random.Random()``.
    depth : int
        Maximum recursion depth (typically 2..8). Higher = more rectangles.
    style : str
        Palette key — one of ``mondrian``, ``rothko``, ``bauhaus``.
    """
    if width <= 0 or height <= 0:
        raise ValueError('width and height must be positive')
    if rng is None:
        rng = random.Random()
    if style not in PALETTES:
        raise ValueError(
            f'unknown style {style!r}; choose from {sorted(PALETTES)}')
    palette = PALETTES[style]
    horizontal_only = (style == 'rothko')
    max_dim = max(width, height)
    root = Rect(0, 0, width, height, (0, 0, 0))
    return _subdivide(root, rng, depth, palette, horizontal_only, max_dim)


# ---------------------------------------------------------------------------
# Pillow rendering
# ---------------------------------------------------------------------------
def render_image(
    rects: Iterable[Rect],
    width: int,
    height: int,
    border: int = BORDER_WIDTH,
    border_color: tuple[int, int, int] = BORDER_COLOR,
) -> Image.Image:
    """Render rectangles to a Pillow image with a black border around each."""
    img = Image.new('RGB', (width, height), border_color)
    draw = ImageDraw.Draw(img)
    for r in rects:
        x0, y0, x1, y1 = r.bbox()
        # Outer rect first (so border bleeds at edges look uniform).
        draw.rectangle((x0, y0, x1 - 1, y1 - 1),
                       fill=r.color, outline=border_color, width=border)
    # Outer frame (Mondrian paintings are framed in black too).
    draw.rectangle((0, 0, width - 1, height - 1),
                   outline=border_color, width=border)
    return img


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description='Mondrian-style art generator')
    parser.add_argument('--width', type=int, default=1200,
                        help='canvas width in pixels (default 1200)')
    parser.add_argument('--height', type=int, default=900,
                        help='canvas height in pixels (default 900)')
    parser.add_argument('--depth', type=int, default=5,
                        help='max recursion depth, 2..8 (default 5)')
    parser.add_argument('--seed', type=int, default=None,
                        help='RNG seed (default: random)')
    parser.add_argument('--style', choices=sorted(PALETTES),
                        default='mondrian', help='palette / style preset')
    parser.add_argument('-o', '--output', default='mondrian.png',
                        help='output PNG path (default mondrian.png)')
    args = parser.parse_args()

    rng = random.Random(args.seed)
    rects = generate(args.width, args.height, rng,
                     depth=args.depth, style=args.style)
    img = render_image(rects, args.width, args.height)
    img.save(args.output)
    print(f'Rendered {len(rects)} rectangles ({args.style}, depth={args.depth},'
          f' seed={args.seed}) -> {args.output}')


if __name__ == '__main__':
    main()
