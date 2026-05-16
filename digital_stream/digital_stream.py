"""Digital Stream — CLI.

Matrix-style falling green digital rain in the terminal.

Each column has one or more "raindrops" — a head character plus a fading tail.
The head glows bright white-green; the tail fades through shades of green using
ANSI 256-color (or 24-bit RGB) escape codes.

Character sets (cycle with the -c flag or interactively in GUI/TUI siblings):
  katakana — half-width katakana (most authentic Matrix look)
  digits   — 0-9
  latin    — ASCII letters A-Z / a-z

Run:
    uv run python digital_stream/digital_stream.py
    uv run python digital_stream/digital_stream.py --charset digits --fps 20
"""
from __future__ import annotations

import argparse
import os
import random
import shutil
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Character sets
# ---------------------------------------------------------------------------
CHARSET_KATAKANA = (
    'ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ'
    'ﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ'
)
CHARSET_DIGITS = '0123456789'
CHARSET_LATIN = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'

CHARSETS: dict[str, str] = {
    'katakana': CHARSET_KATAKANA,
    'digits': CHARSET_DIGITS,
    'latin': CHARSET_LATIN,
}

# ---------------------------------------------------------------------------
# ANSI helpers
# ---------------------------------------------------------------------------
_CSI = '\x1b['
HIDE_CURSOR = _CSI + '?25l'
SHOW_CURSOR = _CSI + '?25h'
CLEAR_SCREEN = _CSI + '2J' + _CSI + 'H'
RESET = _CSI + '0m'


def _rgb(r: int, g: int, b: int) -> str:
    """Return ANSI 24-bit foreground colour escape."""
    return f'\x1b[38;2;{r};{g};{b}m'


# Green palette: head is bright white-green, tail fades to dark green.
# Index 0 = head (brightest), higher index = older / dimmer.
_HEAD_COLOR = _rgb(200, 255, 200)   # near-white green
_TAIL_COLORS = [
    _rgb(57, 255, 20),   # neon green
    _rgb(0, 220, 0),
    _rgb(0, 185, 0),
    _rgb(0, 150, 0),
    _rgb(0, 115, 0),
    _rgb(0, 80, 0),
    _rgb(0, 50, 0),
    _rgb(0, 30, 0),
]


def _glyph_color(depth: int) -> str:
    """Return ANSI colour for a glyph *depth* cells behind the head."""
    if depth == 0:
        return _HEAD_COLOR
    idx = min(depth - 1, len(_TAIL_COLORS) - 1)
    return _TAIL_COLORS[idx]


# ---------------------------------------------------------------------------
# Pure model
# ---------------------------------------------------------------------------
@dataclass
class Drop:
    """A single raindrop: a falling column of glyphs.

    Attributes:
        col:    Terminal column (0-indexed).
        head_y: Current row of the head glyph (float for sub-cell speed).
        length: Number of tail cells (including head = length total visible).
        speed:  Rows advanced per step (fractional allowed).
        chars:  The glyph characters currently occupying each tail cell.
    """
    col: int
    head_y: float
    length: int
    speed: float
    chars: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Pre-fill chars so the tail is ready from the first visible frame.
        if not self.chars:
            self.chars = [' '] * self.length

    def step(self, height: int, charset: str, rng: random.Random) -> None:
        """Advance the drop one simulation step."""
        self.head_y += self.speed
        # Randomly mutate one existing tail glyph (flicker effect).
        if self.chars:
            mut_idx = rng.randrange(len(self.chars))
            self.chars[mut_idx] = rng.choice(charset)
        # Push a new head glyph.
        self.chars.insert(0, rng.choice(charset))
        if len(self.chars) > self.length:
            self.chars.pop()

    @property
    def head_row(self) -> int:
        return int(self.head_y)

    def is_offscreen(self, height: int) -> bool:
        """True when the entire drop (including tail) has scrolled past bottom."""
        return self.head_row - self.length >= height


class Rain:
    """The full simulation grid.

    Parameters:
        width:    Terminal columns.
        height:   Terminal rows.
        density:  Probability of spawning a new drop per column per step.
        rng:      Optional seeded RNG (for deterministic tests).
        charset:  Name of the active character set.
    """

    def __init__(
        self,
        width: int,
        height: int,
        density: float = 0.02,
        rng: Optional[random.Random] = None,
        charset: str = 'katakana',
    ) -> None:
        self.width = width
        self.height = height
        self.density = density
        self.rng = rng if rng is not None else random.Random()
        self.charset_name = charset
        self.charset = CHARSETS.get(charset, CHARSET_KATAKANA)
        self.drops: List[Drop] = []

    # ------------------------------------------------------------------
    def _spawn(self, col: int) -> Drop:
        length = self.rng.randint(4, max(5, self.height // 3))
        speed = self.rng.uniform(0.3, 1.0)
        return Drop(col=col, head_y=-1.0, length=length, speed=speed)

    def step(self) -> None:
        """Advance all drops and maybe spawn new ones."""
        # Advance existing drops.
        for drop in self.drops:
            drop.step(self.height, self.charset, self.rng)
        # Remove drops that have fully left the screen.
        self.drops = [d for d in self.drops if not d.is_offscreen(self.height)]
        # Spawn new drops.
        for col in range(self.width):
            if self.rng.random() < self.density:
                self.drops.append(self._spawn(col))

    def render(self) -> str:
        """Render the current frame as a string with ANSI colour codes."""
        # Build a 2-D grid: grid[row][col] = (char, depth_or_None)
        # depth=0 means head, higher = older tail.
        grid: list[list[tuple[str, int] | None]] = [
            [None] * self.width for _ in range(self.height)
        ]

        for drop in self.drops:
            head = drop.head_row
            for depth, ch in enumerate(drop.chars):
                row = head - depth
                if 0 <= row < self.height and 0 <= drop.col < self.width:
                    # Keep the brightest (smallest depth) glyph if overlap.
                    existing = grid[row][drop.col]
                    if existing is None or depth < existing[1]:
                        grid[row][drop.col] = (ch, depth)

        lines: list[str] = []
        for row in grid:
            parts: list[str] = []
            for cell in row:
                if cell is None:
                    parts.append(' ')
                else:
                    ch, depth = cell
                    parts.append(_glyph_color(depth) + ch + RESET)
            lines.append(''.join(parts))
        return '\n'.join(lines)

    def set_charset(self, name: str) -> None:
        self.charset_name = name
        self.charset = CHARSETS.get(name, CHARSET_KATAKANA)
        # Re-randomise existing chars so the switch is immediate.
        for drop in self.drops:
            drop.chars = [self.rng.choice(self.charset) for _ in drop.chars]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description='Digital Stream — Matrix-style falling green rain')
    parser.add_argument('--fps', type=float, default=15.0,
                        help='Frames per second (default: 15)')
    parser.add_argument('--density', type=float, default=0.03,
                        help='Drop spawn probability per column per frame (default: 0.03)')
    parser.add_argument('--charset', choices=list(CHARSETS), default='katakana',
                        help='Character set (default: katakana)')
    args = parser.parse_args()

    cols, rows = shutil.get_terminal_size(fallback=(80, 24))
    # Leave one row for status / avoid scroll.
    rows = max(5, rows - 1)
    cols = max(10, cols)

    rain = Rain(width=cols, height=rows, density=args.density,
                charset=args.charset)
    interval = 1.0 / max(1.0, args.fps)

    sys.stdout.write(HIDE_CURSOR + CLEAR_SCREEN)
    sys.stdout.flush()

    try:
        while True:
            rain.step()
            frame = rain.render()
            # Move cursor to top-left and overwrite.
            sys.stdout.write(_CSI + 'H' + frame)
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + SHOW_CURSOR + CLEAR_SCREEN)
        sys.stdout.flush()


if __name__ == '__main__':
    main()
