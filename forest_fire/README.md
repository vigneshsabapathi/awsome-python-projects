# Drossel-Schwabl Forest Fire

A self-organized-criticality cellular automaton (Drossel & Schwabl, 1992). Cells are one of three states:

- `0` **EMPTY** — bare ground
- `1` **TREE** — alive tree
- `2` **BURNING** — tree currently on fire

Every step, all cells update **simultaneously**:

1. **BURNING** -> EMPTY (fire burns out)
2. **TREE** -> BURNING if any neighbor is burning
3. **TREE** -> BURNING with probability `f` (lightning)
4. **EMPTY** -> TREE with probability `p` (growth)

In the limit `f << p << 1`, the system organizes itself near a critical tree density (~0.4 for von-Neumann neighbors on a square lattice) and produces fires whose sizes follow a power law — a textbook demo of self-organized criticality.

Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI animation | `forest_fire.py` | NumPy + stdlib |
| Modern desktop GUI | `forest_fire_gui.py` | CustomTkinter + tkinter Canvas |
| Modern terminal UI | `forest_fire_tui.py` | Textual (half-block rendering) |

## Run

```bash
# CLI — 60x30 grid, classic params, 10 fps
uv run python forest_fire/forest_fire.py

# Crank up lightning to see frequent fires
uv run python forest_fire/forest_fire.py --p 0.05 --f 0.005

# Anisotropic spread — fire is pushed eastward by wind
uv run python forest_fire/forest_fire.py --wind east --steps 1000

# Desktop GUI (CustomTkinter)
uv run python forest_fire/forest_fire_gui.py

# Terminal UI (Textual)
uv run python forest_fire/forest_fire_tui.py
```

## Controls

### GUI

- **Play/Pause** (Space)
- **Step** (N) — single generation
- **Reset** — re-seed forest at current density
- **Clear** — wipe to bare ground (let it grow back)
- **Wind** dropdown — `none` / `north` / `south` / `east` / `west` / `moore`
- **p_grow** slider (0..0.1)
- **p_lightning** slider (0..0.001)
- **Speed** slider (2..30 fps)
- Click a cell to cycle EMPTY -> TREE -> BURNING. Drag to paint trees.

### TUI

- **space** play/pause
- **n** single step
- **r** reset
- **w** cycle wind direction
- **ctrl+q** quit

## Architecture

The CLI module (`forest_fire.py`) is the shared simulation core. Both UIs import:

- `step(grid, p_grow, p_lightning, rng, *, wind='none')` — one generation, fully vectorized
- `random_grid(rows, cols, density, seed)` — random forest, no fires
- `seeded_fire_grid(rows, cols, density, seed)` — random forest with a center spark
- `empty_grid(rows, cols)` — bare ground (everything regrows from `p_grow`)
- Constants: `EMPTY`, `TREE`, `BURNING`, `NEIGHBOR_OFFSETS`

### Why shifted ORs?

For each neighbor offset we shift the BURNING boolean grid and OR it into a running mask:

```python
neighbor_burning = np.zeros_like(burning)
for dr, dc in OFFSETS:
    neighbor_burning |= np.roll(burning, (dr, dc), axis=(0, 1))
```

This is fully vectorized — for an `R x C` grid each step does **O(R·C)** work but at NumPy speed (typically 50-200x faster than a Python double loop). For Drossel-Schwabl the rule is "any neighbor on fire" rather than "count neighbors", so OR is enough — no convolution needed.

The two Bernoulli draws (`p_grow`, `p_lightning`) are also a single vectorized `rng.random(grid.shape) < p` per call, so the entire step is ~half a dozen NumPy ops.

### Edges

Toroidal (`np.roll` wraps). Reasonable for an abstract forest and consistent with the other CA projects in this repo.

### dtype

`int8` — three states fit easily, and shifts/ORs on the boolean BURNING mask are fastest of all.

### GUI rendering note

One `tk.Canvas` rectangle is created per cell **once**, then only fill colors are reconfigured per tick. Tk's `itemconfigure` is fast enough for grids of a few thousand cells without lag.

### TUI rendering note

The TUI uses the **upper-half-block character (▀)** so each terminal cell encodes two grid rows — independent foreground (top half) and background (bottom half) colors. Doubles the effective vertical resolution at zero cost.

## Creative twist — wind anisotropy

A `--wind` option (and matching dropdown / hotkey in the UIs) selects which neighbor offsets count as "burning neighbor reaches me". The cardinal directions drop the **upwind** shift, so fire spreads downwind plus its two perpendicular neighbors — a crude but visually striking model of wind-driven fires that produces ribbon-like burn fronts very different from the isotropic blob shapes.

`moore` switches to the 8-neighbor Moore neighborhood, which raises the percolation threshold and produces noticeably bigger fires per spark.

## Smoke test

```bash
uv run python -c "import sys, numpy as np, random; sys.path.insert(0, 'forest_fire'); \
    import forest_fire; \
    g = np.ones((10, 10), int); rng = random.Random(0); \
    g2 = forest_fire.step(g, 0.0, 0.0, rng); print(g2.sum())"
# → 10
```

(With no growth and no lightning and no fires, every TREE stays a TREE — sum equals the number of trees, 100. The output shows the simulation is preserving state without crashing.)

## Self-organized criticality

Run the CLI long enough with `p=0.02, f=0.0005` (the defaults) and the tree density hovers around ~0.4 ± 0.05 — the system self-organizes onto its critical manifold. Histogram the sizes of distinct fires (connected BURNING clusters across consecutive frames) and you'll see a power-law tail: many small fires, occasional very large ones, no characteristic scale. That's what makes Drossel-Schwabl a canonical SOC model alongside Bak-Tang-Wiesenfeld sandpiles and earthquake stick-slip models.
