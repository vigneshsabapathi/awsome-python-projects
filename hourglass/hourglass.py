"""Hourglass — animated ASCII sand simulation.

Sand falls one grain per frame from the top chamber through a narrow neck
into the bottom chamber. Grains pile up in the bottom chamber with an
angle-of-repose feel: each new grain settles at the lowest reachable
position, sliding sideways toward the wall when the center column fills.

Twist: color-graded grains. Each grain remembers when it fell, and the
``render`` method emits per-cell ages so a GUI/TUI can fade older sand.

Run:
    uv run python hourglass/hourglass.py
"""
from __future__ import annotations

import os
import sys
import time
from typing import Iterator, Optional

# --- Geometry ------------------------------------------------------------

# Hourglass width must be odd so the neck is a single column.
DEFAULT_WIDTH = 15
DEFAULT_FPS = 10.0

# Characters used by the CLI renderer.
CH_SAND = 'o'
CH_EMPTY = ' '
CH_WALL = '|'
CH_FLOOR = '='
CH_DIAG_L = '\\'
CH_DIAG_R = '/'


def _validate_width(width: int) -> int:
    if width < 5:
        raise ValueError('width must be >= 5')
    if width % 2 == 0:
        raise ValueError('width must be odd so the neck has a single column')
    return width


def chamber_height(width: int) -> int:
    """Each chamber is a triangle. Width 2H+1 gives H rows of sand cells."""
    return (width - 1) // 2


def total_capacity(width: int) -> int:
    """Number of sand cells the top chamber can hold (= number bottom holds).

    Top chamber rows top->bottom have widths width, width-2, ..., 3, 1.
    Sum = ((width+1)/2)^2 ... but we drop the neck row from the chamber and
    treat it separately, leaving H rows with widths width, width-2, ..., 3.
    Sum = H*(H+2)? Let's just compute it.
    """
    H = chamber_height(width)
    # Rows 0..H-1 have widths width - 2*r, for r in [0, H).
    return sum(width - 2 * r for r in range(H))


# --- Hourglass -----------------------------------------------------------


class Hourglass:
    """Animated hourglass with one-grain-per-step falling.

    Layout (rows top to bottom):
        0 .. H-1     : top chamber (sand falls from here)
        H            : the neck (single column at width//2)
        H+1 .. 2H    : bottom chamber (sand piles up here)

    Each cell stores either ``None`` (empty) or an integer "age" (the step
    at which the grain entered that cell). Age 0 = oldest grain. Age lets
    the renderer color-grade grains.
    """

    def __init__(self, width: int = DEFAULT_WIDTH,
                 total_grains: Optional[int] = None) -> None:
        self.width = _validate_width(width)
        self.H = chamber_height(self.width)
        self.neck_col = self.width // 2
        self.rows = 2 * self.H + 1  # top H + neck + bottom H

        cap = total_capacity(self.width)
        if total_grains is None:
            total_grains = cap
        if total_grains < 0:
            raise ValueError('total_grains must be >= 0')
        if total_grains > cap:
            raise ValueError(
                f'total_grains={total_grains} exceeds top-chamber capacity {cap}')
        self.total_grains = total_grains

        # 2-D grid: grid[r][c] is None or an age int.
        self.grid: list[list[Optional[int]]] = [
            [None] * self.width for _ in range(self.rows)
        ]
        self.step_count: int = 0

        # Initialise top chamber with `total_grains` packed bottom-up.
        # Row r in [0, H) has cells at columns in [r, width - r) (triangle).
        cells_top: list[tuple[int, int]] = []
        for r in range(self.H - 1, -1, -1):  # bottom row of top chamber first
            for c in range(r, self.width - r):
                cells_top.append((r, c))
        # Stamp grains with age = -i so older = smaller. They haven't
        # "fallen" yet, but giving them increasing age preserves order.
        for i, (r, c) in enumerate(cells_top[:total_grains]):
            self.grid[r][c] = -i  # negative ages distinguish unfallen grains

    # -- core API --------------------------------------------------------

    def is_done(self) -> bool:
        """True once the top chamber and neck are empty."""
        for r in range(self.H + 1):
            for cell in self.grid[r]:
                if cell is not None:
                    return False
        return True

    def step(self) -> None:
        """Advance one frame: a single grain falls through the neck.

        Algorithm:
        1. If a grain sits in the neck, settle it into the bottom pile.
        2. Drop the lowest-center grain in the top chamber down through its
           column toward the neck. Grains slide laterally toward the neck
           column when they're above the neck row.
        """
        if self.is_done():
            return

        self.step_count += 1

        # 1. Settle whatever is currently in the neck into the bottom pile.
        neck = self.grid[self.H][self.neck_col]
        if neck is not None:
            self.grid[self.H][self.neck_col] = None
            self._settle_into_bottom(neck)

        # 2. Move one grain from the top chamber down by one logical step.
        #    We pick the lowest grain in the column closest to the neck.
        moved = self._advance_top_chamber()
        if not moved:
            # Top chamber is empty but neck might still have grain (handled
            # next step). Nothing else to do this frame.
            return

    # -- top-chamber motion ---------------------------------------------

    def _advance_top_chamber(self) -> bool:
        """Move one grain one step downward toward the neck.

        Each step we either:
        - Drop the bottom-most center grain into the neck (if center column
          has a grain in row H-1).
        - Otherwise, slide grains sideways toward the center to feed the
          centre column. We do this by scanning row H-1 and pulling the
          nearest-to-center grain into column = neck_col.
        - If row H-1 is empty in the inner triangle, pull a grain from the
          row above to fall into row H-1 first.

        Returns True if anything moved.
        """
        # First: if the bottom-most row of the top chamber has a grain in
        # the center column, drop it into the neck.
        if self.grid[self.H - 1][self.neck_col] is not None:
            grain = self.grid[self.H - 1][self.neck_col]
            self.grid[self.H - 1][self.neck_col] = None
            self.grid[self.H][self.neck_col] = grain
            return True

        # Second: pull a grain from row H-1 (the row just above the neck)
        # toward the center column. Row H-1's triangle spans 3 cells:
        # columns [H-1, width-(H-1)) = [H-1, H+2). Find the non-empty
        # cell nearest the centre and slide it inward.
        row = self.H - 1
        for offset in range(1, self.H + 1):
            for c in (self.neck_col - offset, self.neck_col + offset):
                if 0 <= c < self.width and self._in_top_triangle(row, c):
                    if self.grid[row][c] is not None:
                        # Slide it to the centre column on the same row.
                        self.grid[row][self.neck_col] = self.grid[row][c]
                        self.grid[row][c] = None
                        return True

        # Third: row H-1 is empty. Find any grain in the top chamber above
        # row H-1 and let it fall straight down by one row (or sideways if
        # the cell directly below is outside the triangle).
        for r in range(self.H - 2, -1, -1):
            for c in range(self.width):
                if not self._in_top_triangle(r, c):
                    continue
                if self.grid[r][c] is None:
                    continue
                # Try straight-down first.
                if (r + 1 < self.H
                        and self._in_top_triangle(r + 1, c)
                        and self.grid[r + 1][c] is None):
                    self.grid[r + 1][c] = self.grid[r][c]
                    self.grid[r][c] = None
                    return True
                # Otherwise try diagonals toward the centre.
                target = c + (1 if c < self.neck_col else -1)
                if (r + 1 < self.H
                        and self._in_top_triangle(r + 1, target)
                        and self.grid[r + 1][target] is None):
                    self.grid[r + 1][target] = self.grid[r][c]
                    self.grid[r][c] = None
                    return True

        return False

    def _in_top_triangle(self, r: int, c: int) -> bool:
        """Top chamber: row r in [0, H), cells at columns [r, width-r)."""
        if r < 0 or r >= self.H:
            return False
        return r <= c < self.width - r

    # -- bottom-chamber pile -------------------------------------------

    def _in_bottom_triangle(self, r: int, c: int) -> bool:
        """Bottom chamber: rows H+1..2H. Row index r_local = r - (H+1).

        Row r_local has width 2*r_local + 3 centered on neck_col, so
        columns span [neck_col - r_local - 1, neck_col + r_local + 2).
        Row r_local=0 (just below the neck) has 3 cells; r_local=H-1
        is the widest row (= full width = 2H+1).
        """
        r_local = r - (self.H + 1)
        if r_local < 0 or r_local >= self.H:
            return False
        left = self.neck_col - r_local - 1
        right = self.neck_col + r_local + 2
        return left <= c < right

    def _settle_into_bottom(self, grain: int) -> None:
        """Place a grain into the bottom chamber using angle-of-repose rules.

        Walk down from the neck column. At each step, prefer to drop
        straight down; if blocked, slide diagonally toward whichever side
        has the shorter pile. If everything below is blocked, settle in
        the current cell. As a last resort (centre column full to the
        neck), pile up by walking laterally from the neck column to find
        the first reachable surface cell.
        """
        # Replace negative "unfallen" age with the current step count so
        # the renderer can colour-grade by fall time.
        if grain is None or grain < 0:
            grain = self.step_count

        # Start at the row just under the neck, in the centre column.
        c = self.neck_col
        r = self.H + 1

        max_iter = self.rows * self.width  # safety bound
        for _ in range(max_iter):
            # If the current cell is occupied, we can't place here. Try a
            # surface walk to find a nearby empty surface cell.
            if self.grid[r][c] is not None:
                placed = self._surface_place(grain)
                if placed:
                    return
                # Pile is full — drop the grain on the floor (a corner).
                self._floor_place(grain)
                return

            # Cell (r, c) is empty. Can we fall further?
            below_in = (r + 1 <= 2 * self.H
                        and self._in_bottom_triangle(r + 1, c))
            below_open = below_in and self.grid[r + 1][c] is None
            if below_open:
                r += 1
                continue

            # Below is blocked or out-of-triangle. Try diagonal slide.
            left_in = (r + 1 <= 2 * self.H
                       and self._in_bottom_triangle(r + 1, c - 1))
            right_in = (r + 1 <= 2 * self.H
                        and self._in_bottom_triangle(r + 1, c + 1))
            left_open = left_in and self.grid[r + 1][c - 1] is None
            right_open = right_in and self.grid[r + 1][c + 1] is None

            if left_open and right_open:
                lh = self._column_height_bottom(c - 1)
                rh = self._column_height_bottom(c + 1)
                if lh <= rh:
                    r += 1
                    c -= 1
                else:
                    r += 1
                    c += 1
                continue
            if left_open:
                r += 1
                c -= 1
                continue
            if right_open:
                r += 1
                c += 1
                continue

            # Nowhere to go. Settle here.
            self.grid[r][c] = grain
            return

        # Failsafe.
        self._surface_place(grain) or self._floor_place(grain)

    def _surface_place(self, grain: int) -> bool:
        """Find an empty cell at the top of the pile near the centre.

        Scans rows from the top of the bottom chamber downward and picks
        the empty cell in each row closest to the centre column.
        """
        for r in range(self.H + 1, self.rows):
            best_c = None
            best_dist = 10**9
            for c in range(self.width):
                if not self._in_bottom_triangle(r, c):
                    continue
                if self.grid[r][c] is not None:
                    continue
                d = abs(c - self.neck_col)
                if d < best_dist:
                    best_dist = d
                    best_c = c
            if best_c is not None:
                self.grid[r][best_c] = grain
                return True
        return False

    def _floor_place(self, grain: int) -> bool:
        """Last resort: stick the grain in the very first empty cell."""
        for r in range(self.rows - 1, self.H, -1):
            for c in range(self.width):
                if (self._in_bottom_triangle(r, c)
                        and self.grid[r][c] is None):
                    self.grid[r][c] = grain
                    return True
        return False

    def _column_height_bottom(self, c: int) -> int:
        """Number of contiguous filled cells at the bottom of column c."""
        if c < 0 or c >= self.width:
            return 10**9  # treat out-of-bounds as infinitely tall
        h = 0
        for r in range(2 * self.H, self.H, -1):
            if not self._in_bottom_triangle(r, c):
                break
            if self.grid[r][c] is None:
                break
            h += 1
        return h

    # -- rendering ------------------------------------------------------

    def render(self) -> str:
        """Render the hourglass as ASCII art.

        Layout: each rendered line has two outer ``|`` walls plus a
        ``width``-wide interior. Inside the interior we draw a slanted
        chamber boundary (``\\`` and ``/``) and the sand cells themselves.

        Top chamber: row 0 is fully open (wall to wall). Each subsequent
        row pulls in by one column on each side, drawn with ``\\`` on the
        left and ``/`` on the right. The neck is a single column.

        Bottom chamber mirrors: it starts narrow under the neck and opens
        outward, drawn with ``/`` on the left and ``\\`` on the right.
        """
        lines: list[str] = []
        W = self.width

        # Top lid.
        lines.append('+' + CH_FLOOR * W + '+')

        # --- Top chamber ---------------------------------------------
        for r in range(self.H):
            row = [CH_EMPTY] * (W + 2)
            row[0] = CH_WALL
            row[-1] = CH_WALL
            # Slanted boundary: pinch inward by r columns on each side.
            if r > 0:
                # Left slope ``\`` sits at column r (1-based: row[1+r-1]?
                # we want it just outside the sand triangle [r, width-r).
                # That means at columns r-1 and width-r in the interior.
                left_idx = 1 + (r - 1)
                right_idx = 1 + (W - r)
                row[left_idx] = CH_DIAG_L
                row[right_idx] = CH_DIAG_R
            # Sand cells.
            for c in range(r, W - r):
                cell = self.grid[r][c]
                if cell is not None:
                    row[1 + c] = CH_SAND
            lines.append(''.join(row))

        # --- Neck row ------------------------------------------------
        neck_row = [CH_EMPTY] * (W + 2)
        neck_row[0] = CH_WALL
        neck_row[-1] = CH_WALL
        # The slants from the top chamber's deepest row converge to the
        # neck column. Left slope ``\`` sits just left of the neck, right
        # slope ``/`` just right.
        if self.neck_col - 1 >= 0:
            neck_row[1 + self.neck_col - 1] = CH_DIAG_L
        if self.neck_col + 1 < W:
            neck_row[1 + self.neck_col + 1] = CH_DIAG_R
        cell = self.grid[self.H][self.neck_col]
        neck_row[1 + self.neck_col] = CH_SAND if cell is not None else CH_EMPTY
        lines.append(''.join(neck_row))

        # --- Bottom chamber ------------------------------------------
        for r_local in range(self.H):
            r = self.H + 1 + r_local
            row = [CH_EMPTY] * (W + 2)
            row[0] = CH_WALL
            row[-1] = CH_WALL
            left = self.neck_col - r_local - 1
            right = self.neck_col + r_local + 2
            # Bottom chamber slopes ``/`` on left, ``\`` on right.
            if r_local < self.H - 1:
                # Slopes sit just outside the sand cells.
                if left - 1 >= 0:
                    row[1 + left - 1] = CH_DIAG_R
                if right < W:
                    row[1 + right] = CH_DIAG_L
            # Sand cells.
            for c in range(left, right):
                cell = self.grid[r][c]
                if cell is not None:
                    row[1 + c] = CH_SAND
            lines.append(''.join(row))

        # Bottom floor.
        lines.append('+' + CH_FLOOR * W + '+')

        # Status line.
        top = self.top_count()
        bot = self.bottom_count()
        lines.append(f'top: {top}   bottom: {bot}   step: {self.step_count}')
        return '\n'.join(lines)

    # -- introspection --------------------------------------------------

    def top_count(self) -> int:
        n = 0
        for r in range(self.H):
            for cell in self.grid[r]:
                if cell is not None:
                    n += 1
        # Include any grain currently in the neck.
        if self.grid[self.H][self.neck_col] is not None:
            n += 1
        return n

    def bottom_count(self) -> int:
        n = 0
        for r in range(self.H + 1, self.rows):
            for cell in self.grid[r]:
                if cell is not None:
                    n += 1
        return n

    def flip(self) -> None:
        """Invert top and bottom chambers, preserving grain ages.

        After a flip the bottom pile becomes the new top contents (packed
        bottom-up like a fresh start), and the previous top is empty.
        """
        bottom_grains: list[int] = []
        for r in range(self.H + 1, self.rows):
            for c in range(self.width):
                v = self.grid[r][c]
                if v is not None:
                    bottom_grains.append(v)
                    self.grid[r][c] = None

        # Clear top + neck just in case.
        for r in range(self.H + 1):
            for c in range(self.width):
                self.grid[r][c] = None

        # Repack into top chamber, packed bottom-up.
        cells_top: list[tuple[int, int]] = []
        for r in range(self.H - 1, -1, -1):
            for c in range(r, self.width - r):
                cells_top.append((r, c))
        # Reset their age so freshly-flipped grains start "young" again.
        # Use negative indices like initial fill.
        for i, (r, c) in enumerate(cells_top[:len(bottom_grains)]):
            self.grid[r][c] = -i

        self.total_grains = len(bottom_grains)
        # Don't reset step_count — it's the cumulative animation clock.

    def reset(self) -> None:
        """Reset to a brand-new hourglass with the original grain count."""
        original = self.total_grains
        # Recompute initial fill if total was zeroed by full drain.
        if original == 0:
            original = total_capacity(self.width)
        for r in range(self.rows):
            for c in range(self.width):
                self.grid[r][c] = None
        cells_top = []
        for r in range(self.H - 1, -1, -1):
            for c in range(r, self.width - r):
                cells_top.append((r, c))
        for i, (r, c) in enumerate(cells_top[:original]):
            self.grid[r][c] = -i
        self.total_grains = original
        self.step_count = 0

    def shake(self) -> None:
        """Earthquake! Scatter the bottom pile so it has to re-settle.

        Lift every grain in the bottom chamber, then re-drop them one by
        one through the settle algorithm. Visually it looks like the pile
        re-collapses with a new angle of repose.
        """
        bottom: list[int] = []
        for r in range(self.H + 1, self.rows):
            for c in range(self.width):
                v = self.grid[r][c]
                if v is not None:
                    bottom.append(v)
                    self.grid[r][c] = None
        # Drop them in a slightly randomized order so the pile shape changes.
        # Shuffle is intentionally deterministic per call sequence — we keep
        # things reproducible by reversing instead of using random.
        for grain in reversed(bottom):
            self._settle_into_bottom(grain)

    # -- iteration helpers for GUIs ------------------------------------

    def cells(self) -> Iterator[tuple[int, int, Optional[int]]]:
        """Yield (row, col, age_or_None) for every cell. Useful for GUIs."""
        for r in range(self.rows):
            for c in range(self.width):
                yield r, c, self.grid[r][c]


# --- CLI -----------------------------------------------------------------


def _clear_screen() -> None:
    if os.name == 'nt':
        os.system('cls')
    else:
        os.system('clear')


def main() -> None:
    """Animate an hourglass at ~10 fps. When the top empties, flip and repeat."""
    width = DEFAULT_WIDTH
    if len(sys.argv) > 1:
        try:
            width = int(sys.argv[1])
            if width % 2 == 0:
                width += 1  # force odd
        except ValueError:
            pass

    h = Hourglass(width=width)
    frame_delay = 1.0 / DEFAULT_FPS

    print('Hourglass — Ctrl+C to quit. Window flips automatically when drained.')
    time.sleep(0.6)

    try:
        while True:
            while not h.is_done():
                _clear_screen()
                print(h.render())
                h.step()
                time.sleep(frame_delay)
            _clear_screen()
            print(h.render())
            print()
            print('  ...flipping...')
            time.sleep(0.8)
            h.flip()
    except KeyboardInterrupt:
        print('\nbye.')


if __name__ == '__main__':
    main()
