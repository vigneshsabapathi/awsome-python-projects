"""Etching Drawer — Etch-A-Sketch-style drawing tool.

Move a cursor with the arrow keys to draw a continuous line on a 2D character
canvas. Diagonal moves use w/e/z/x (or numpad-style 7/9/1/3). Press the SHAKE
key to erase. The canvas is a pure-Python class so it can be reused by the GUI
and TUI front-ends.

CLI controls (Windows uses msvcrt; POSIX falls back to a single-key reader):
    Arrow keys         — move pen N/S/E/W (drawing as it goes)
    w / e / z / x      — diagonal moves (NW / NE / SW / SE)
    space              — toggle pen down/up
    c                  — cycle brush color (palette character)
    s                  — shake / clear the canvas
    p                  — playback recorded strokes from the start
    q                  — quit

Tags: drawing, canvas, ascii, ui
"""
from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field

# Public canvas defaults — re-used by the GUI / TUI front-ends.
DEFAULT_WIDTH = 60
DEFAULT_HEIGHT = 20
EMPTY = ' '

# Brush palette — one printable character per slot. The TWIST: pressing 'c'
# cycles to the next colour (character) so the same canvas can hold multiple
# stroke styles. The first entry is the default.
PALETTE: tuple[str, ...] = ('#', '*', '+', 'o', 'x', '@')

# Direction vectors: (dy, dx). 8-directional movement (TWIST).
DIRECTIONS: dict[str, tuple[int, int]] = {
    'up':         (-1,  0),
    'down':       ( 1,  0),
    'left':       ( 0, -1),
    'right':      ( 0,  1),
    'up-left':    (-1, -1),
    'up-right':   (-1,  1),
    'down-left':  ( 1, -1),
    'down-right': ( 1,  1),
}


@dataclass
class Stroke:
    """A single recorded pen mark for playback."""
    y: int
    x: int
    char: str


class Canvas:
    """A 2D character grid with a movable pen.

    The pen has a position (cy, cx), a brush character, and a pen-down flag.
    Each `move(direction)` shifts the pen by one cell in the chosen direction,
    clamped to the canvas, and stamps the brush character at the new position
    (when pen is down). Movements are recorded so playback can re-create the
    drawing stroke-by-stroke.
    """

    def __init__(self, width: int = DEFAULT_WIDTH,
                 height: int = DEFAULT_HEIGHT,
                 brush: str = PALETTE[0]) -> None:
        if width < 2 or height < 2:
            raise ValueError('canvas must be at least 2x2')
        if len(brush) != 1:
            raise ValueError('brush must be a single character')
        self.width = width
        self.height = height
        self.brush = brush
        self.pen_down = True
        self.cy = height // 2
        self.cx = width // 2
        self.grid: list[list[str]] = [
            [EMPTY for _ in range(width)] for _ in range(height)
        ]
        # Stamp the starting cell so a freshly-rendered canvas isn't blank.
        self.grid[self.cy][self.cx] = brush
        self.history: list[Stroke] = [Stroke(self.cy, self.cx, brush)]

    # ---- pure-ish operations ----------------------------------------

    def move(self, direction: str) -> tuple[int, int]:
        """Move the pen one cell in `direction`. Returns the new (y, x).
        Out-of-bounds moves clip to the edge (no wrap, no error)."""
        if direction not in DIRECTIONS:
            raise ValueError(f'unknown direction: {direction!r}')
        dy, dx = DIRECTIONS[direction]
        self.cy = max(0, min(self.height - 1, self.cy + dy))
        self.cx = max(0, min(self.width - 1, self.cx + dx))
        if self.pen_down:
            self.grid[self.cy][self.cx] = self.brush
            self.history.append(Stroke(self.cy, self.cx, self.brush))
        return self.cy, self.cx

    def clear(self) -> None:
        """Shake! Wipe the canvas and reset history. Pen position stays put."""
        self.grid = [
            [EMPTY for _ in range(self.width)] for _ in range(self.height)
        ]
        if self.pen_down:
            self.grid[self.cy][self.cx] = self.brush
        self.history = [Stroke(self.cy, self.cx, self.brush)]

    def cycle_brush(self) -> str:
        """Cycle to the next brush in the palette. Returns the new brush."""
        idx = (PALETTE.index(self.brush) + 1) % len(PALETTE) \
            if self.brush in PALETTE else 0
        self.brush = PALETTE[idx]
        return self.brush

    def toggle_pen(self) -> bool:
        """Lift / lower the pen. Returns the new pen_down state."""
        self.pen_down = not self.pen_down
        return self.pen_down

    def render(self, show_cursor: bool = True,
               cursor_char: str = '_') -> str:
        """Return the canvas as a single string with newlines.
        If show_cursor is True, overlay `cursor_char` at the pen position
        in a *copy* of the row — the underlying grid is not mutated."""
        rows: list[str] = []
        for y, row in enumerate(self.grid):
            if show_cursor and y == self.cy:
                tmp = row.copy()
                # Only overlay the cursor on cells the pen hasn't already
                # stamped — keeps the trail visible behind the cursor.
                if tmp[self.cx] == EMPTY:
                    tmp[self.cx] = cursor_char
                rows.append(''.join(tmp))
            else:
                rows.append(''.join(row))
        return '\n'.join(rows)

    def replay_frames(self) -> list[str]:
        """Yield-friendly: list of render snapshots, one per stroke.
        Used by GUIs/TUIs to drive a playback animation."""
        # Replay onto a fresh canvas keeping the same dimensions.
        ghost = Canvas(self.width, self.height, brush=self.brush)
        ghost.grid = [
            [EMPTY for _ in range(self.width)] for _ in range(self.height)
        ]
        ghost.history = []
        frames: list[str] = []
        for stroke in self.history:
            ghost.cy, ghost.cx = stroke.y, stroke.x
            ghost.grid[stroke.y][stroke.x] = stroke.char
            frames.append(ghost.render(show_cursor=False))
        return frames


# ---------- key reading -------------------------------------------------

# Cross-platform single-key reader. On Windows we lean on msvcrt because the
# spec asks for it; on POSIX we drop into a tty raw-mode read that recognises
# the standard ANSI arrow-key escape sequences (ESC [ A/B/C/D).

def _read_key_windows() -> str:
    import msvcrt  # type: ignore[import-not-found]
    ch = msvcrt.getwch()
    # Arrow keys arrive as a two-byte sequence: a lead byte (\x00 or \xe0)
    # followed by the actual scan code.
    if ch in ('\x00', '\xe0'):
        ch2 = msvcrt.getwch()
        return {
            'H': 'up', 'P': 'down', 'K': 'left', 'M': 'right',
            'G': 'up-left', 'I': 'up-right',
            'O': 'down-left', 'Q': 'down-right',
        }.get(ch2, '')
    return ch


def _read_key_posix() -> str:  # pragma: no cover - exercised only on POSIX
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            seq = sys.stdin.read(2)
            return {
                '[A': 'up', '[B': 'down', '[C': 'right', '[D': 'left',
            }.get(seq, '')
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def read_key() -> str:
    """Read a single key/arrow press. Returns a logical name for arrows,
    a single character for letters, or '' for anything we don't recognise."""
    if os.name == 'nt':
        return _read_key_windows()
    return _read_key_posix()


# ---------- CLI ---------------------------------------------------------

KEY_DIRECTIONS = {
    # Arrow keys (already normalised to direction names)
    'up': 'up', 'down': 'down', 'left': 'left', 'right': 'right',
    'up-left': 'up-left', 'up-right': 'up-right',
    'down-left': 'down-left', 'down-right': 'down-right',
    # Diagonals on letter keys (works everywhere, including dumb terminals)
    'w': 'up-left', 'e': 'up-right', 'z': 'down-left', 'x': 'down-right',
}


def _clear_screen() -> None:
    # ANSI clear works on modern Windows terminals (cmd, pwsh, Terminal).
    sys.stdout.write('\x1b[2J\x1b[H')
    sys.stdout.flush()


def _print_canvas(canvas: Canvas, status: str) -> None:
    _clear_screen()
    border = '+' + '-' * canvas.width + '+'
    print(border)
    for line in canvas.render().split('\n'):
        print('|' + line + '|')
    print(border)
    print(status)


def main() -> None:
    canvas = Canvas()
    help_line = ('arrows: draw   w/e/z/x: diagonals   space: pen   '
                 'c: color   s: shake   p: playback   q: quit')
    _print_canvas(canvas, help_line)
    while True:
        key = read_key()
        if not key:
            continue
        if key in KEY_DIRECTIONS:
            canvas.move(KEY_DIRECTIONS[key])
        elif key == ' ':
            canvas.toggle_pen()
        elif key.lower() == 'c':
            canvas.cycle_brush()
        elif key.lower() == 's':
            canvas.clear()
        elif key.lower() == 'p':
            for frame in canvas.replay_frames():
                _clear_screen()
                print('+' + '-' * canvas.width + '+')
                for line in frame.split('\n'):
                    print('|' + line + '|')
                print('+' + '-' * canvas.width + '+')
                print('PLAYBACK')
                time.sleep(0.04)
        elif key.lower() == 'q' or key == '\x03':  # Ctrl+C
            print()
            return
        status = (f'pen: {"DOWN" if canvas.pen_down else "UP"}   '
                  f'brush: {canvas.brush!r}   '
                  f'pos: ({canvas.cx},{canvas.cy})   '
                  f'strokes: {len(canvas.history)}\n' + help_line)
        _print_canvas(canvas, status)


if __name__ == '__main__':
    main()
