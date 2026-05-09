"""Maze Runner 3D — first-person ASCII pseudo-3D maze explorer.

A classic Wizardry / Eye-of-the-Beholder style dungeon view: the player
sees the corridor stretching ahead, with the front wall, left wall, and
right wall rendered at three depth slices (1, 2, 3 cells away).

Run:
    uv run python maze_runner_3d/maze_runner_3d.py

Public API:
    generate(width, height, rng) -> Maze
    render_first_person(maze, x, y, facing) -> str
    render_minimap(maze, x, y, facing, *, torch=None) -> str
    move(maze, x, y, facing, action) -> (x, y, facing)

Twist:
    A torch-radius visibility model dims cells outside the lit zone
    (rendered as faint dots) and a tiny chance of a monster sprite
    appearing in the corridor on each step.
"""
from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from typing import List, Tuple

# Cell glyphs in the maze grid.
WALL = '#'
OPEN = ' '

# Cardinal directions. Right-handed: turning right cycles N→E→S→W.
FACINGS = ('N', 'E', 'S', 'W')
DELTAS = {
    'N': (0, -1),
    'E': (1, 0),
    'S': (0, 1),
    'W': (-1, 0),
}


@dataclass
class Maze:
    """A 2D maze grid stored as a list of strings.

    `grid[y][x]` is '#' for a wall, ' ' for an open corridor.
    `width` and `height` are the full grid dimensions (odd numbers).
    Cells at odd coordinates (1, 3, 5, ...) are corridor candidates;
    even coordinates are wall slabs the carving algorithm tunnels through.
    """

    width: int
    height: int
    grid: List[str] = field(default_factory=list)

    def at(self, x: int, y: int) -> str:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return WALL  # Out of bounds reads as solid wall.

    def is_wall(self, x: int, y: int) -> bool:
        return self.at(x, y) == WALL


# ---------- maze generation (recursive-backtracker DFS) ----------

def generate(width: int, height: int, rng: random.Random) -> Maze:
    """Carve a perfect maze with recursive backtracking.

    Both `width` and `height` are forced to odd numbers >= 5 so the
    carve-by-2 algorithm has clean corridor / wall slab alternation.
    """
    if width < 5:
        width = 5
    if height < 5:
        height = 5
    if width % 2 == 0:
        width += 1
    if height % 2 == 0:
        height += 1

    # Start fully solid; carve corridors as we go.
    grid = [[WALL] * width for _ in range(height)]
    visited = [[False] * width for _ in range(height)]

    def carve(cx: int, cy: int) -> None:
        visited[cy][cx] = True
        grid[cy][cx] = OPEN
        directions = list(DELTAS.values())
        rng.shuffle(directions)
        for dx, dy in directions:
            # Step two cells (skipping the wall slab between).
            nx, ny = cx + dx * 2, cy + dy * 2
            if 0 < nx < width - 1 and 0 < ny < height - 1 \
                    and not visited[ny][nx]:
                # Knock down the wall between (cx,cy) and (nx,ny).
                grid[cy + dy][cx + dx] = OPEN
                carve(nx, ny)

    # An iterative variant would handle huge mazes; recursion is fine
    # at the typical 21x21 we use here.
    sys.setrecursionlimit(max(1000, width * height * 4))
    carve(1, 1)
    return Maze(width=width, height=height,
                grid=[''.join(row) for row in grid])


# ---------- movement ----------

def turn_left(facing: str) -> str:
    return FACINGS[(FACINGS.index(facing) - 1) % 4]


def turn_right(facing: str) -> str:
    return FACINGS[(FACINGS.index(facing) + 1) % 4]


def turn_around(facing: str) -> str:
    return FACINGS[(FACINGS.index(facing) + 2) % 4]


def step_forward(maze: Maze, x: int, y: int, facing: str) -> Tuple[int, int]:
    """Walk one cell forward if the cell ahead is open, else stay put."""
    dx, dy = DELTAS[facing]
    nx, ny = x + dx, y + dy
    if not maze.is_wall(nx, ny):
        return nx, ny
    return x, y


def step_back(maze: Maze, x: int, y: int, facing: str) -> Tuple[int, int]:
    """Step backwards (without turning) if the cell behind is open."""
    dx, dy = DELTAS[turn_around(facing)]
    nx, ny = x + dx, y + dy
    if not maze.is_wall(nx, ny):
        return nx, ny
    return x, y


def move(maze: Maze, x: int, y: int, facing: str,
         action: str) -> Tuple[int, int, str]:
    """Apply a single keystroke action: w / a / s / d.

    Returns the new (x, y, facing). Invalid actions are no-ops.
    """
    a = action.lower()
    if a == 'w':
        nx, ny = step_forward(maze, x, y, facing)
        return nx, ny, facing
    if a == 's':
        nx, ny = step_back(maze, x, y, facing)
        return nx, ny, facing
    if a == 'a':
        return x, y, turn_left(facing)
    if a == 'd':
        return x, y, turn_right(facing)
    return x, y, facing


# ---------- first-person ASCII rendering ----------
#
# The view is built from depth slices: the front-wall stub at depth 1,
# 2, 3, plus left- and right-wall side panels for each visible cell.
# Each slice is a multi-line ASCII fragment composited left-to-right.
#
# Layout (10 rows, 23 cols) — '.' means sky/ceiling, '_' means floor,
# '|' / '/' / '\' build the perspective wedge:
#
#  col:  0  1  2  3  ...  22
#  row 0: ceiling line
#  row 1-3: progressively narrower wedges (depth 3, 2, 1)
#  row 4-5: viewport center
#  row 6-8: floor wedges
#  row 9: floor baseline / status
#
# The rendering composites three depth bands (3, 2, 1) so that closer
# walls overdraw farther ones — making the corridor feel like it
# stretches into the distance.

VIEW_W = 23
VIEW_H = 9


def _blank_view() -> List[List[str]]:
    """Background: stars on the ceiling, ground on the floor."""
    rows: List[List[str]] = []
    for r in range(VIEW_H):
        if r < VIEW_H // 2:
            rows.append(['.'] * VIEW_W)  # Ceiling.
        else:
            rows.append([','] * VIEW_W)  # Floor.
    return rows


# Each depth band is described by (left_x, right_x, top_y, bot_y).
# Closer = wider, taller. The numbers were tuned by hand to look like
# a corridor stretching forward.
DEPTH_BANDS = {
    3: (10, 12, 4, 4),   # Tiny far wedge — just two columns at center.
    2: (8, 14, 3, 5),    # Mid corridor.
    1: (4, 18, 1, 7),    # Near walls — fill most of the frame.
}


def _draw_left_wall(view: List[List[str]], depth: int) -> None:
    """Diagonal wedge on the left side at the given depth band."""
    lx, _rx, ty, by = DEPTH_BANDS[depth]
    for r in range(ty, by + 1):
        if 0 <= r < VIEW_H and 0 <= lx < VIEW_W:
            # Use '|' for the vertical edge of the wall slab.
            view[r][lx] = '|'
    # Slanting top + bottom edges hint at perspective.
    if depth == 1:
        for i in range(0, lx):
            ty_slant = max(0, ty - 1 + (i * (ty)) // max(1, lx))
            by_slant = min(VIEW_H - 1, by + 1 - (i * ty) // max(1, lx))
            if view[ty_slant][i] == '.':
                view[ty_slant][i] = '\\'
            if view[by_slant][i] == ',':
                view[by_slant][i] = '/'


def _draw_right_wall(view: List[List[str]], depth: int) -> None:
    _lx, rx, ty, by = DEPTH_BANDS[depth]
    for r in range(ty, by + 1):
        if 0 <= r < VIEW_H and 0 <= rx < VIEW_W:
            view[r][rx] = '|'
    if depth == 1:
        for i in range(rx + 1, VIEW_W):
            offset = i - rx
            span = VIEW_W - rx
            ty_slant = max(0, ty - 1 + (offset * ty) // max(1, span))
            by_slant = min(VIEW_H - 1, by + 1 - (offset * ty) // max(1, span))
            if view[ty_slant][i] == '.':
                view[ty_slant][i] = '/'
            if view[by_slant][i] == ',':
                view[by_slant][i] = '\\'


def _draw_front_wall(view: List[List[str]], depth: int) -> None:
    """Solid wall blocking the corridor at `depth` cells ahead."""
    lx, rx, ty, by = DEPTH_BANDS[depth]
    for r in range(ty, by + 1):
        for c in range(lx, rx + 1):
            if 0 <= r < VIEW_H and 0 <= c < VIEW_W:
                view[r][c] = '#'


def _peek(maze: Maze, x: int, y: int, facing: str,
          forward: int, side: int) -> bool:
    """Return True if the cell `forward` ahead and `side` to the right is wall.

    `side` = -1 means one cell to the player's left, +1 to the right.
    """
    fdx, fdy = DELTAS[facing]
    rdx, rdy = DELTAS[turn_right(facing)]
    cx = x + fdx * forward + rdx * side
    cy = y + fdy * forward + rdy * side
    return maze.is_wall(cx, cy)


def render_first_person(maze: Maze, x: int, y: int, facing: str) -> str:
    """Render a ~10-line first-person ASCII view from (x, y) facing `facing`.

    The renderer composites three depth bands (3, 2, 1). For each depth
    we check: is there a wall on the left? on the right? blocking ahead?
    Walls are drawn far-to-near so the closer wedges overdraw the farther
    ones — yielding a believable corridor receding into the distance.
    """
    view = _blank_view()

    # Walk depth-3 → depth-1 so closer walls overpaint further ones.
    for depth in (3, 2, 1):
        # If the corridor itself is blocked at depth d-1 (or before),
        # we can still draw side walls at d to give context — but
        # nothing further than the front wall.
        # Detect the front wall: the cell `depth` ahead is a wall.
        front_blocked = _peek(maze, x, y, facing, depth, 0)
        # Side walls are drawn at this depth if the side is a wall AND
        # the path up to here is not interrupted earlier by a front wall.
        path_clear = True
        for d in range(1, depth):
            if _peek(maze, x, y, facing, d, 0):
                path_clear = False
                break
        if path_clear:
            if _peek(maze, x, y, facing, depth, -1):
                _draw_left_wall(view, depth)
            if _peek(maze, x, y, facing, depth, 1):
                _draw_right_wall(view, depth)
            if front_blocked:
                _draw_front_wall(view, depth)

    return '\n'.join(''.join(row) for row in view)


# ---------- mini-map ----------

FACING_GLYPH = {'N': '^', 'E': '>', 'S': 'v', 'W': '<'}


def render_minimap(maze: Maze, x: int, y: int, facing: str, *,
                   torch: int | None = None) -> str:
    """Compact top-down minimap. If `torch` is set, dim cells outside it."""
    out = []
    for ry in range(maze.height):
        row = []
        for rx in range(maze.width):
            if (rx, ry) == (x, y):
                row.append(FACING_GLYPH[facing])
            else:
                cell = maze.at(rx, ry)
                if torch is not None:
                    if abs(rx - x) + abs(ry - y) > torch:
                        row.append(' ' if cell == OPEN else '.')
                        continue
                row.append(cell)
        out.append(''.join(row))
    return '\n'.join(out)


# ---------- monster sprite (the "twist") ----------

MONSTER_SPRITE = [
    '   ,___,   ',
    '   (o,o)   ',
    '   /)__)   ',
    '   -"-"-   ',
]


def maybe_monster_overlay(rng: random.Random, view: str,
                          chance: float = 0.15) -> str:
    """Occasionally drop a small monster sprite into the center of the view."""
    if rng.random() >= chance:
        return view
    rows = view.splitlines()
    sprite_h = len(MONSTER_SPRITE)
    sprite_w = len(MONSTER_SPRITE[0])
    if len(rows) < sprite_h or VIEW_W < sprite_w:
        return view
    top = (len(rows) - sprite_h) // 2
    left = (VIEW_W - sprite_w) // 2
    new_rows = list(rows)
    for i, sline in enumerate(MONSTER_SPRITE):
        line = list(new_rows[top + i])
        for j, ch in enumerate(sline):
            if ch != ' ' and 0 <= left + j < len(line):
                line[left + j] = ch
        new_rows[top + i] = ''.join(line)
    return '\n'.join(new_rows)


# ---------- CLI ----------

HELP = '''
Maze Runner 3D — first-person ASCII pseudo-3D maze.

Controls:
    w  step forward
    s  step back (no turn)
    a  turn left
    d  turn right
    m  toggle minimap
    n  new maze
    q  quit

Reach any edge cell (other than the start) to win.
'''


def _find_goal(maze: Maze, start: Tuple[int, int]) -> Tuple[int, int]:
    """Pick a far-corner open cell as the exit."""
    sx, sy = start
    candidates = [(maze.width - 2, maze.height - 2),
                  (maze.width - 2, 1),
                  (1, maze.height - 2)]
    for cx, cy in candidates:
        if not maze.is_wall(cx, cy) and (cx, cy) != (sx, sy):
            return cx, cy
    return maze.width - 2, maze.height - 2


def main() -> None:
    rng = random.Random()
    width, height = 13, 13
    maze = generate(width, height, rng)
    x, y, facing = 1, 1, 'E'
    goal = _find_goal(maze, (x, y))
    show_map = True
    torch_radius = 4

    print(HELP)
    while True:
        view = render_first_person(maze, x, y, facing)
        view = maybe_monster_overlay(rng, view, chance=0.08)
        print()
        print(view)
        if show_map:
            print()
            print('Map:')
            print(render_minimap(maze, x, y, facing, torch=torch_radius))
        print()
        print(f'Pos ({x},{y})  Facing {facing}  '
              f'Goal {goal}   torch={torch_radius}')

        if (x, y) == goal:
            print('\n*** You found the exit! ***')
            print('Play again? (y/n)')
            if input('> ').lower().startswith('y'):
                maze = generate(width, height, rng)
                x, y, facing = 1, 1, 'E'
                goal = _find_goal(maze, (x, y))
                continue
            print('Thanks for playing!')
            return

        action = input('> ').strip().lower()
        if action.startswith('q'):
            print('Bye.')
            return
        if action.startswith('n'):
            maze = generate(width, height, rng)
            x, y, facing = 1, 1, 'E'
            goal = _find_goal(maze, (x, y))
            continue
        if action.startswith('m'):
            show_map = not show_map
            continue
        if action.startswith('h') or action == '?':
            print(HELP)
            continue
        if action and action[0] in 'wasd':
            x, y, facing = move(maze, x, y, facing, action[0])


if __name__ == '__main__':
    main()
