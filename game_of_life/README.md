# Conway's Game of Life

Cellular automaton on a 2D grid. Each cell is alive or dead. Every step:

- A **live** cell with **2 or 3** live neighbors stays alive.
- A **dead** cell with **exactly 3** live neighbors becomes alive.
- Otherwise the cell dies / stays dead.

Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI animation | `game_of_life.py` | NumPy + stdlib |
| Modern desktop GUI | `game_of_life_gui.py` | CustomTkinter + tkinter Canvas |
| Modern terminal UI | `game_of_life_tui.py` | Textual (half-block rendering) |

## Run

```bash
# CLI — random soup, toroidal edges, 12 fps, 400 generations
uv run python game_of_life/game_of_life.py

# CLI with a specific pattern
uv run python game_of_life/game_of_life.py --pattern gosper --rows 30 --cols 60

# CLI with bounded edges (no wrap)
uv run python game_of_life/game_of_life.py --pattern glider --bounded

# Desktop GUI (CustomTkinter)
uv run python game_of_life/game_of_life_gui.py

# Terminal UI (Textual)
uv run python game_of_life/game_of_life_tui.py
```

## Controls

### GUI

- **Play/Pause** (Space)
- **Step** (N) — single generation
- **Reset** — re-stamp the current pattern
- **Clear** — empty grid
- **Pattern** dropdown — Random / Glider / Pulsar / Gosper Gun / Blinker
- **Speed** slider — 5..60 fps
- **Toroidal edges** switch — wrap vs bounded
- **Trail (fade)** switch — dying cells leave a 4-frame fade
- Click cells to toggle, drag to paint

### TUI

- **space** play/pause
- **n** single step
- **r** reseed random
- **p** cycle through patterns
- **e** toggle toroidal vs bounded edges
- **ctrl+q** quit

## Architecture

The CLI module (`game_of_life.py`) holds the shared simulation core. Both UIs import:

- `step(grid, toroidal=True)` — one generation, fully vectorized via 8 shifted sums (no Python double loop)
- `random_grid(rows, cols, density)` — uniform random fill
- `glider_grid()`, `blinker_grid()`, `pulsar_grid()`, `gosper_glider_gun_grid()` — preset patterns

### Why shifted sums?

For each of the 8 neighbor offsets we shift the binary grid and add it to a running counter:

```python
n = sum(np.roll(grid, (dr, dc), axis=(0, 1))
        for (dr, dc) in NEIGHBOR_OFFSETS)
new_grid = (n == 3) | (grid & (n == 2))
```

This is fully vectorized — for an `R×C` grid each step does **O(R·C)** work but at NumPy speed (typically 50-200x faster than a Python double loop). For very large grids `scipy.signal.convolve2d` with a 3×3 kernel of ones is another option; for *enormous* sparse universes the canonical algorithm is **HashLife** (memoized quad-tree), which is super-linear faster on patterns with structure but irrelevant for the grid sizes here.

### Edges

`step()` accepts `toroidal=True/False`. Toroidal wraps via `np.roll`; bounded uses `np.pad(..., 0)` so off-grid neighbors are dead. Both UIs expose the toggle.

### GUI rendering note

The GUI builds one `tk.Canvas` rectangle per cell **once**, then only reconfigures fill colors per tick. This avoids rebuilding the canvas item tree at 60 fps — Tk handles `itemconfigure` calls fast enough for grids up to ~5000 cells without lag.

### TUI rendering note

The TUI uses the **upper-half-block character (▀)** to encode two grid rows in one terminal line. Each character has independent foreground (top half) and background (bottom half) colors, doubling effective vertical resolution at zero cost.

## Creative twist

**Trail fade** — when the GUI's "Trail" switch is on, every cell that just died leaves a 4-frame color fade (emerald → near-black). This makes oscillators visibly breathe and gliders draw a comet tail behind them. Toggle it off to see the canonical binary view.

## Verifying the rules

```bash
uv run python -c "import sys, numpy as np; sys.path.insert(0, 'game_of_life'); \
    import game_of_life as gl; \
    g = gl.blinker_grid(); print('blinker step alive:', gl.step(g).sum())"
# blinker step alive: 3
```

A glider after 4 steps reproduces its starting shape translated by `(+1, +1)` — the simplest non-trivial verification of the step function.
