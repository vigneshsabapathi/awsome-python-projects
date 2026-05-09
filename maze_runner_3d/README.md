# Maze Runner 3D

First-person ASCII pseudo-3D maze explorer in the spirit of *Wizardry* and
*Eye of the Beholder*. The maze is generated as a 2D grid (recursive-
backtracker DFS), but you only ever see the corridor stretching ahead —
walls on your left, walls on your right, and a wall blocking the path —
rendered as ASCII at three depth slices (1, 2, 3 cells away).

## What's in here

| File | What it is |
|------|------------|
| `maze_runner_3d.py`     | CLI + pure rendering / generation API |
| `maze_runner_3d_gui.py` | CustomTkinter dark-theme desktop GUI |
| `maze_runner_3d_tui.py` | Textual dark-theme TUI |

## Run

```sh
uv run python maze_runner_3d/maze_runner_3d.py        # CLI
uv run python maze_runner_3d/maze_runner_3d_gui.py    # Desktop GUI
uv run python maze_runner_3d/maze_runner_3d_tui.py    # Terminal TUI
```

## Controls

| Key | Action |
|-----|--------|
| `w` / Up    | Step forward |
| `s` / Down  | Step back (no turn) |
| `a` / Left  | Turn left |
| `d` / Right | Turn right |
| `m` | Toggle minimap |
| `n` | New maze |
| `Ctrl+Q` (TUI) / `q` (CLI) | Quit |

## How the rendering works

The view is a 9-row, 23-column ASCII frame. For each depth band
`d ∈ {3, 2, 1}` the renderer asks three questions about the maze:

1. Is the cell `d` ahead a wall? → draw a **front wall** stub.
2. Is the cell `d` ahead and one to the left a wall? → draw a **left wall**.
3. Is the cell `d` ahead and one to the right a wall? → draw a **right wall**.

Bands are drawn far → near so the closer wedges overpaint farther ones,
producing the classic perspective-corridor effect. No raycasting, no
trigonometry — just three precomputed wedge templates.

## Twist

- **Torch radius** dims the minimap: cells more than ~4 Manhattan-steps
  from the player are dimmed to faint dots, simulating limited visibility.
- **Monster sprites** occasionally appear superimposed on the viewport
  (a small ASCII goblin-thing) for a flash of "you are not alone."

## Public API

```python
from maze_runner_3d import generate, render_first_person, render_minimap, move

rng = random.Random(0)
maze = generate(11, 11, rng)
view = render_first_person(maze, x=1, y=1, facing='N')
mini = render_minimap(maze, 1, 1, 'N', torch=4)
x, y, facing = move(maze, 1, 1, 'N', 'd')   # turn right
```
