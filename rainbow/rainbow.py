"""Rainbow — animated ASCII rainbow gradients in the terminal.

Pure helpers:
    hsv_to_rgb(h, s, v)         -> (r, g, b) in 0..255
    rgb_to_ansi256(r, g, b)     -> int 16..231 (xterm 6x6x6 cube)
    rainbow_color(t)            -> ansi escape for hue t in [0, 1)
    colorize(text, offset=0)    -> str with per-char rainbow gradient
    rainbow_arc(width=80)       -> str (multi-line ASCII arc)
    horizontal_band(width, off) -> str (single-line rainbow band)

Animation:
    animate(text, fps=10)       -> infinite scrolling rainbow text loop
    main()                      -> CLI

The CLI parses argv (or prompts for text). Ctrl+C exits cleanly.

Tags: ascii-art, color, animation
"""
from __future__ import annotations

import math
import os
import sys
import time

# ANSI escape sequences.
RESET = '\033[0m'
CLEAR = '\033[2J\033[H'  # clear screen, home cursor
HIDE_CURSOR = '\033[?25l'
SHOW_CURSOR = '\033[?25h'


def hsv_to_rgb(h: float, s: float, v: float) -> tuple[int, int, int]:
    """Convert HSV in [0,1] to RGB triple in 0..255."""
    h = h - math.floor(h)  # wrap into [0, 1)
    i = int(h * 6.0)
    f = h * 6.0 - i
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    i %= 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return int(r * 255), int(g * 255), int(b * 255)


def rgb_to_ansi256(r: int, g: int, b: int) -> int:
    """Map 24-bit RGB to the xterm 256-color 6x6x6 cube (16..231)."""
    def _q(x: int) -> int:
        # Quantize 0..255 into 0..5 using the standard xterm thresholds.
        if x < 48:
            return 0
        if x < 115:
            return 1
        return (x - 35) // 40
    return 16 + 36 * _q(r) + 6 * _q(g) + _q(b)


def rainbow_color(t: float) -> str:
    """Return an ANSI 256-color foreground escape for hue t in [0, 1)."""
    r, g, b = hsv_to_rgb(t, 1.0, 1.0)
    return f'\033[38;5;{rgb_to_ansi256(r, g, b)}m'


def colorize(text: str, offset: float = 0.0, freq: float = 1.0 / 14.0) -> str:
    """Return `text` with per-character rainbow coloring (ANSI 256).

    `offset` shifts the phase so successive frames scroll smoothly.
    `freq` controls how fast the hue cycles per character (lower = wider band).
    Newlines and carriage returns are kept untouched (no color applied).
    """
    out: list[str] = []
    col = 0
    for ch in text:
        if ch == '\n' or ch == '\r':
            out.append(RESET)
            out.append(ch)
            col = 0
            continue
        out.append(rainbow_color(offset + col * freq))
        out.append(ch)
        col += 1
    out.append(RESET)
    return ''.join(out)


def horizontal_band(width: int = 80, offset: float = 0.0,
                    char: str = '█') -> str:
    """Return one line of full-block characters with a moving rainbow band."""
    width = max(1, int(width))
    parts: list[str] = []
    for i in range(width):
        parts.append(rainbow_color(offset + i / max(1, width)))
        parts.append(char)
    parts.append(RESET)
    return ''.join(parts)


def vertical_bands(width: int = 80, height: int = 8,
                   offset: float = 0.0) -> str:
    """Stack of horizontal bands where each row has its own hue (vertical)."""
    width = max(1, int(width))
    height = max(1, int(height))
    lines: list[str] = []
    for r in range(height):
        hue = offset + r / height
        line = rainbow_color(hue) + ('█' * width) + RESET
        lines.append(line)
    return '\n'.join(lines)


def rainbow_arc(width: int = 80) -> str:
    """Return a multi-line ASCII rainbow arc colored with the 7-band rainbow.

    Bands from outer to inner: red, orange, yellow, green, blue, indigo, violet.
    The arc is drawn as concentric semicircles using ASCII characters.
    """
    width = max(20, int(width))
    bands = 7
    radius = max(bands + 1, width // 2 - 1)
    height = radius + 1
    cx = radius
    # Each cell: which band index does it belong to? -1 if blank.
    grid = [[-1] * (radius * 2 + 1) for _ in range(height)]
    for band in range(bands):
        r_outer = radius - band
        r_inner = r_outer - 1
        for y in range(height):
            for x in range(radius * 2 + 1):
                dx = x - cx
                dy = (radius - y)  # arc opens downward; top row is the peak
                if dy < 0:
                    continue
                d2 = dx * dx + dy * dy
                if r_inner * r_inner < d2 <= r_outer * r_outer:
                    if grid[y][x] == -1:
                        grid[y][x] = band

    band_chars = ['*', 'o', '=', '~', '-', '.', '`']
    out_lines: list[str] = []
    for y in range(height):
        chars: list[str] = []
        for x, band in enumerate(grid[y]):
            if band == -1:
                chars.append(' ')
            else:
                hue = band / bands  # 0=red, ~0.86=violet
                chars.append(rainbow_color(hue) + band_chars[band])
        chars.append(RESET)
        out_lines.append(''.join(chars))
    return '\n'.join(out_lines)


def _term_width(default: int = 80) -> int:
    try:
        return max(20, os.get_terminal_size().columns)
    except OSError:
        return default


def animate(text: str, fps: float = 10.0, mode: str = 'gradient') -> None:
    """Scroll a rainbow forever. Press Ctrl+C to stop.

    mode: 'gradient' (cycling text), 'arc' (static arc, hue scrolls),
          'band' (horizontal moving band), 'lolcat' (per-line phase shift).
    """
    fps = max(0.5, float(fps))
    delay = 1.0 / fps
    step = 1.0 / 30.0  # hue advance per frame
    offset = 0.0
    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()
    try:
        while True:
            sys.stdout.write(CLEAR)
            if mode == 'gradient':
                sys.stdout.write(colorize(text, offset))
            elif mode == 'arc':
                # Re-tint the arc by shifting the foreground hue each frame.
                width = _term_width()
                sys.stdout.write(_recolor_arc(rainbow_arc(width), offset))
            elif mode == 'band':
                width = _term_width()
                lines = []
                for r in range(8):
                    lines.append(horizontal_band(width, offset + r * 0.02))
                sys.stdout.write('\n'.join(lines))
                sys.stdout.write('\n\n')
                sys.stdout.write(colorize(text, offset))
            elif mode == 'lolcat':
                # Random horizontal phase per line (deterministic from row).
                lines = []
                for i, line in enumerate(text.splitlines() or [text]):
                    lines.append(colorize(line, offset + i * 0.13))
                sys.stdout.write('\n'.join(lines))
            else:
                sys.stdout.write(colorize(text, offset))
            sys.stdout.write('\n')
            sys.stdout.flush()
            offset = (offset + step) % 1.0
            time.sleep(delay)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write(RESET + SHOW_CURSOR + '\n')
        sys.stdout.flush()


def _recolor_arc(arc: str, offset: float) -> str:
    """Re-emit an existing colored arc with hues shifted by `offset`.

    The arc text already contains ANSI color escapes. To animate, we strip
    those and re-color each character based on its column position.
    """
    # Strip existing ANSI sequences then re-colorize.
    plain = _strip_ansi(arc)
    return colorize(plain, offset)


def _strip_ansi(s: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(s):
        if s[i] == '\033' and i + 1 < len(s) and s[i + 1] == '[':
            j = i + 2
            while j < len(s) and not (0x40 <= ord(s[j]) <= 0x7E):
                j += 1
            i = j + 1
        else:
            out.append(s[i])
            i += 1
    return ''.join(out)


def main() -> None:
    """CLI entry point.

    Usage:
        python rainbow.py [text...]
        python rainbow.py --arc
        python rainbow.py --mode lolcat hello world
    """
    args = sys.argv[1:]
    mode = 'gradient'
    fps = 12.0
    text_parts: list[str] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-h', '--help'):
            print(__doc__)
            return
        if a == '--arc':
            mode = 'arc'
        elif a == '--band':
            mode = 'band'
        elif a == '--lolcat':
            mode = 'lolcat'
        elif a == '--mode' and i + 1 < len(args):
            mode = args[i + 1]
            i += 1
        elif a == '--fps' and i + 1 < len(args):
            try:
                fps = float(args[i + 1])
            except ValueError:
                pass
            i += 1
        elif a == '--once':
            # Print one frame and exit (useful for piping/screenshots).
            text = ' '.join(text_parts) or 'RAINBOW'
            if mode == 'arc':
                print(rainbow_arc(_term_width()))
            elif mode == 'band':
                print(horizontal_band(_term_width()))
            else:
                print(colorize(text))
            return
        else:
            text_parts.append(a)
        i += 1

    text = ' '.join(text_parts).strip()
    if not text and mode == 'gradient':
        try:
            text = input('Text to rainbow-ify: ').strip() or 'RAINBOW'
        except EOFError:
            text = 'RAINBOW'
    elif not text:
        text = 'RAINBOW'

    animate(text, fps=fps, mode=mode)


if __name__ == '__main__':
    main()
