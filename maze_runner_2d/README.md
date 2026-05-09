# Maze Runner 2D

Generate a random 2D maze and walk from `S` to `E`. Top-down ASCII view in three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `maze_runner_2d.py` | stdlib |
| Desktop GUI | `maze_runner_2d_gui.py` | CustomTkinter + tk.Canvas |
| Terminal UI | `maze_runner_2d_tui.py` | Textual + Rich |

## Glyphs

| Char | Meaning |
|------|---------|
| `#`  | wall |
| ` `  | floor |
| `S`  | start |
| `E`  | exit |
| `@`  | player |
| `.`  | shortest-path overlay (cyan in GUI/TUI) |

## Run

```bash
# CLI (WASD or arrow keys on Windows)
uv run python maze_runner_2d/maze_runner_2d.py

# Desktop GUI
uv run python maze_runner_2d/maze_runner_2d_gui.py

# Terminal UI
uv run python maze_runner_2d/maze_runner_2d_tui.py
```

### Controls (GUI)

- Arrow keys / WASD — move
- **N** — new maze
- **P** / `Show Path` button — overlay the BFS shortest path in cyan
- Algorithm dropdown — switch between **backtracker / prim / wilson**
- Width and Height sliders — resize and regenerate

### Controls (TUI)

- Arrows / WASD — move
- **n** — new maze
- **p** — toggle solution overlay
- **t** — cycle generator algorithm
- **f** — toggle fog-of-war
- **Ctrl+Q** — quit

## Architecture

`maze_runner_2d.py` holds the pure game logic. Both UIs import:

- `generate(width, height, rng, algorithm) -> Maze` — three algorithms
- `Maze.solve(source?, target?) -> list[(x, y)]` — BFS shortest path
- `Maze.render(show_solution=, fog_radius=) -> str` — ASCII frame
- `Maze.move(direction) -> bool` — mutates `Maze.player`
- `Maze.won: bool`
- `WALL`, `FLOOR`, `START`, `END`, `PLAYER`, `ALGORITHMS`

### Grid model

A logical `W x H` cell maze is stored as a `(2W+1) x (2H+1)` character
grid: odd rows/cols are cells, even rows/cols are wall slots between
them. Borders are always walls, so all wall checks reduce to a simple
character lookup.

### Generators

| Algorithm | Pattern |
|-----------|---------|
| `backtracker` | recursive backtracker (iterative DFS) — long, winding corridors |
| `prim` | randomized Prim's — short, bushy corridors with many junctions |
| `wilson` | Wilson's algorithm via loop-erased random walks — slower, but draws each maze uniformly at random from all spanning trees |

### Solver

BFS over the floor cells of the grid. Treats every floor character as a
graph node, every adjacent-floor pair as an edge. The result is the
shortest grid path; doubling the resolution makes the maze look nicer
without complicating the search.

## Twist

Three twists are wired in:

1. **Algorithm switcher** — backtracker / Prim / Wilson — different feel and bias.
2. **Cyan solution overlay** — toggle the BFS shortest path on the live maze.
3. **Fog of war** — only show cells within Manhattan radius `N` of the player (TUI binding `f`, also exposed in `Maze.render(fog_radius=...)`).

## Verification

```bash
uv run python -c "import sys, random; sys.path.insert(0, 'maze_runner_2d'); \
import maze_runner_2d; m = maze_runner_2d.generate(11, 11, random.Random(0)); \
print(len(m.solve()) > 0)"
# -> True
```
