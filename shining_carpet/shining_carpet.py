"""Shining Carpet — animated tessellated ASCII carpet.

Inspired by the iconic hexagonal carpet pattern from the Overlook Hotel
hallway in *The Shining*. The screen is filled by tiling a small repeating
ASCII tile, then a colour palette is rotated through the tile glyphs to
shimmer the whole carpet.

Three tile patterns ship out of the box:

* ``shining``  — interlocking hexagons (Overlook hallway homage).
* ``persian``  — medallion-style rug with a central diamond.
* ``penrose``  — quasi-periodic kite/dart-ish weave.

The CLI animates the carpet in your terminal using ANSI 256-colour escapes.
Press Ctrl+C to stop. The :func:`tile` and :func:`render` functions are
pure — both UIs (CustomTkinter, Textual) re-use them.

Tags: animation, patterns, tessellation, color, ascii-art
"""
from __future__ import annotations

import argparse
import sys
import time
from typing import Iterable

# ---------------------------------------------------------------------------
# Tile patterns. Every tile is a list of equal-length strings — a small
# rectangle that tessellates by simple repetition. Each non-space glyph maps
# to a *palette slot* (its index in PALETTE_GLYPHS), so the renderer can
# swap whole colour palettes without touching the geometry.
# ---------------------------------------------------------------------------

# Glyphs are deliberately distinct so the slot mapping is stable. Order
# matters: index in this string == palette slot.
PALETTE_GLYPHS = '#%@*+=:.'  # 8 slots, dense -> sparse

# 8x4 hexagon weave. The interlocking hexes give the Overlook-carpet vibe.
SHINING_TILE = [
    '##  ##  ',
    '#%##%%##',
    '%%@@%%@@',
    ' %@@ %@@',
]

# 8x4 Persian-rug medallion. Central diamond + cross fillers, mirrored.
PERSIAN_TILE = [
    '+: :+: :',
    ': @ : @ ',
    '+: :+: :',
    ': @ : @ ',
]

# 12x6 quasi-periodic Penrose-ish weave. Wider tile that *almost* repeats —
# the offset rows break the strict periodicity so the eye sees motion.
PENROSE_TILE = [
    '#  *  =  +  ',
    ' #  *  =  + ',
    '*  =  +  #  ',
    ' *  =  +  # ',
    '=  +  #  *  ',
    ' =  +  #  * ',
]

TILES: dict[str, list[str]] = {
    'shining':  SHINING_TILE,
    'persian':  PERSIAN_TILE,
    'penrose':  PENROSE_TILE,
}

# ---------------------------------------------------------------------------
# Palettes — three named colour schemes. Each maps the 8 PALETTE_GLYPHS to
# hex colours. The CLI uses ANSI 256-colour fallbacks; the GUI/TUI use the
# hex values directly. Index 0 = densest glyph, index 7 = lightest.
# ---------------------------------------------------------------------------

PALETTES: dict[str, list[str]] = {
    # Overlook orange / brown / cream — *The Shining* hallway tones.
    'shining': [
        '#3a1d0a', '#7a2e0e', '#c14d12', '#e8742a',
        '#f0a05a', '#f6c98c', '#fae6b8', '#fff5d8',
    ],
    # Persian-rug indigo + crimson + gold.
    'persian': [
        '#0d1b3d', '#1a2b6b', '#3149a8', '#7a1c2e',
        '#b03048', '#d4a017', '#e6c34a', '#f4e9b3',
    ],
    # Bauhaus primaries — bold red / yellow / blue / black / white.
    'bauhaus': [
        '#0a0a0a', '#1a1a1a', '#1f3a93', '#3b6cd1',
        '#d62828', '#e85d3a', '#f5b400', '#f4f1de',
    ],
}

PALETTE_NAMES = list(PALETTES.keys())


def tile(palette: str = 'shining') -> list[str]:
    """Return the small repeating ASCII tile for the given palette name.

    The palette name doubles as the tile-pattern name — *shining* gives the
    hexagon weave, *persian* the medallion, *bauhaus* the Penrose-ish
    quasi-periodic weave. Any unknown name falls back to the shining tile.
    """
    if palette == 'persian':
        return list(PERSIAN_TILE)
    if palette in ('bauhaus', 'penrose'):
        return list(PENROSE_TILE)
    return list(SHINING_TILE)


def render(width: int, height: int, tile: list[str],
           offset: int = 0, palette: list[str] | None = None) -> str:
    """Tile a `width` x `height` canvas with `tile`, returning plain text.

    `offset` rotates the palette slot of every glyph by that many steps —
    this is the per-frame phase shift that animates the colour shimmer.
    `palette` is accepted for API symmetry; the plain-text render ignores
    it (no ANSI), so the geometry alone is returned. Use :func:`render_ansi`
    when you want a colourised string.
    """
    if width <= 0 or height <= 0:
        raise ValueError('width and height must be positive')
    if not tile:
        raise ValueError('tile must be a non-empty list of strings')

    tile_h = len(tile)
    tile_w = max(len(row) for row in tile)
    # Pad short rows so the modulo math always lands on a real character.
    padded = [row.ljust(tile_w) for row in tile]

    out_lines: list[str] = []
    for r in range(height):
        src = padded[r % tile_h]
        chars: list[str] = []
        for c in range(width):
            ch = src[c % tile_w]
            if ch == ' ':
                chars.append(' ')
            else:
                # Phase-shift the glyph slot for animation.
                slot = PALETTE_GLYPHS.index(ch) if ch in PALETTE_GLYPHS else 0
                slot = (slot + offset) % len(PALETTE_GLYPHS)
                chars.append(PALETTE_GLYPHS[slot])
        out_lines.append(''.join(chars))
    return '\n'.join(out_lines)


def glyph_to_slot(ch: str) -> int:
    """Return the palette slot (0..7) for a glyph, or -1 for space."""
    if ch == ' ' or ch not in PALETTE_GLYPHS:
        return -1
    return PALETTE_GLYPHS.index(ch)


# ---------------------------------------------------------------------------
# ANSI helpers (CLI animation only). 24-bit truecolour escape — terminals
# that don't support it will degrade to no colour but still show the tile.
# ---------------------------------------------------------------------------

def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _ansi_fg(hex_color: str) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    return f'\x1b[38;2;{r};{g};{b}m'


_ANSI_RESET = '\x1b[0m'


def render_ansi(width: int, height: int, tile: list[str],
                offset: int = 0, palette: list[str] | None = None) -> str:
    """Same geometry as :func:`render`, but with ANSI truecolour spans."""
    if palette is None:
        palette = PALETTES['shining']
    plain = render(width, height, tile, offset=offset)
    out: list[str] = []
    for line in plain.splitlines():
        buf: list[str] = []
        last_slot = -2
        for ch in line:
            slot = glyph_to_slot(ch)
            if slot == -1:
                if last_slot != -1:
                    buf.append(_ANSI_RESET)
                    last_slot = -1
                buf.append(' ')
                continue
            if slot != last_slot:
                buf.append(_ansi_fg(palette[slot % len(palette)]))
                last_slot = slot
            buf.append(ch)
        buf.append(_ANSI_RESET)
        out.append(''.join(buf))
    return '\n'.join(out)


# ---------------------------------------------------------------------------
# CLI animation loop
# ---------------------------------------------------------------------------

def _palette_cycle(names: Iterable[str]) -> Iterable[str]:
    names = list(names)
    i = 0
    while True:
        yield names[i % len(names)]
        i += 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='shining_carpet',
        description='Animated tessellated ASCII carpet pattern.',
    )
    parser.add_argument('--width', type=int, default=64,
                        help='canvas width in chars (default 64)')
    parser.add_argument('--height', type=int, default=20,
                        help='canvas height in rows (default 20)')
    parser.add_argument('--palette', choices=PALETTE_NAMES, default='shining',
                        help='colour palette (also picks tile pattern)')
    parser.add_argument('--fps', type=float, default=8.0,
                        help='animation frames per second (default 8)')
    parser.add_argument('--frames', type=int, default=0,
                        help='stop after N frames (0 = forever, default 0)')
    parser.add_argument('--no-color', action='store_true',
                        help='print plain ASCII without ANSI colour')
    parser.add_argument('--no-cycle', action='store_true',
                        help='stay on one palette instead of cycling')
    args = parser.parse_args()

    tile_data = tile(args.palette)
    delay = 1.0 / max(args.fps, 0.5)
    frame = 0
    palette_iter = _palette_cycle(PALETTE_NAMES)
    current_palette = args.palette

    # Hide cursor + use alt-screen for a clean animation.
    sys.stdout.write('\x1b[?25l')
    try:
        while True:
            if not args.no_cycle and frame % 16 == 0:
                current_palette = next(palette_iter)
            colours = PALETTES[current_palette]

            # Reset cursor to top-left without clearing — flicker-free redraw.
            sys.stdout.write('\x1b[H')
            if args.no_color:
                sys.stdout.write(render(args.width, args.height, tile_data,
                                        offset=frame))
            else:
                sys.stdout.write(render_ansi(args.width, args.height,
                                             tile_data, offset=frame,
                                             palette=colours))
            sys.stdout.write(f'\n[palette: {current_palette}  frame: {frame}'
                             f'  Ctrl+C to quit]\n')
            sys.stdout.flush()

            frame += 1
            if args.frames and frame >= args.frames:
                break
            time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(_ANSI_RESET + '\x1b[?25h\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
