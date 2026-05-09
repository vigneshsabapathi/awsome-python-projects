# Langton's Ant

A 2D cellular automaton with a single mobile agent (the "ant"). Two
trivial rules:

- **On a white cell:** turn right, flip the cell to black, move forward.
- **On a black cell:** turn left, flip the cell to white, move forward.

For the first ~10,000 steps the ant scribbles seeming chaos. Then, suddenly,
it locks into a perfectly periodic 104-step "highway" and rolls off in a
straight diagonal forever. Cohen-Kong (1995) proved this happens for *any*
finite initial configuration — the universality of the highway is one of
the most striking results in elementary cellular automata.

Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI animation | `langton_ant.py` | NumPy + stdlib |
| Modern desktop GUI | `langton_ant_gui.py` | CustomTkinter + tkinter Canvas |
| Modern terminal UI | `langton_ant_tui.py` | Textual (half-block rendering) |

## Run

```bash
# CLI — final frame after 11,000 steps (the highway should be visible)
uv run python langton_ant/langton_ant.py

# CLI animated, 120 evenly-spaced frames at 30 fps
uv run python langton_ant/langton_ant.py --animate

# CLI with a multi-color rule
uv run python langton_ant/langton_ant.py --rule RLR --rows 121 --cols 121

# Desktop GUI
uv run python langton_ant/langton_ant_gui.py

# Terminal UI
uv run python langton_ant/langton_ant_tui.py
```

## Controls

### GUI

- **Play / Pause** (Space) — start / stop the animation
- **Step** (N) — advance one frame (= `speed` ant steps)
- **Reset** (R) — clear grid, recenter the ant, step counter back to 0
- **Rule** entry — type any rule, e.g. `RL`, `RLR`, `LLRR`, `RRLL`,
  `LRRRRRLLR`. Press *Apply* (or Enter) to commit.
- **Speed** slider — 1..1000 ant steps per animation frame
- **Direction** buttons — restart the ant facing Up / Right / Down / Left

### TUI

- **space** play / pause
- **n** single step (advances `speed` ant moves)
- **+/-** speed up / slow down (geometric ×1.5)
- **r** reset grid
- **p** cycle through preset rules (`RL`, `RLR`, `LLRR`, `RRLL`,
  `LRRRRRLLR`)
- **ctrl+q** quit

## Architecture

The CLI module (`langton_ant.py`) holds the shared simulation core. Both
UIs import:

- `Ant(grid, x, y, direction, rule="RL")` — agent. Mutates `grid` in
  place (Langton's Ant changes one cell per step — there is no
  synchronous-double-buffer trick to apply, unlike Game of Life).
- `Ant.step()` → `None` — single-step update.
- `Ant.state()` → `dict` — JSON snapshot (`x`, `y`, `direction`,
  `steps`, `rule`, `alive`).
- `step_n(grid, x, y, direction, n, rule="RL")` → tuple — pure
  function: runs *n* steps and returns
  `(grid, x, y, direction, steps_taken)`. `steps_taken < n` if the ant
  walked off a non-toroidal grid before completing.
- `make_grid(rows, cols)` → `uint8` zero array.

### Direction encoding

`0=Up, 1=Right, 2=Down, 3=Left`. Turning right is `(d + 1) % 4`,
turning left is `(d - 1) % 4`. Movement deltas are `(drow, dcol)`
because NumPy is row-major: up is `row - 1`, *not* `y - 1` in screen
coordinates.

### Why mutate in place?

Unlike Game of Life — which is a *synchronous* automaton requiring a
fresh output buffer per step — Langton's Ant changes exactly **one
cell per step**, so reading and writing the same array is correct.
Single-cell updates are also faster in pure Python than NumPy's
broadcast machinery, which is why we use scalar indexing in `step()`
instead of vectorising; per-step overhead is what matters here, not
bulk arithmetic. Bulk NumPy ops are still used for the rendering path
(`(grid != painted).nonzero()` for the differential repaint, and
`(grid > 0).sum()` for the "filled cells" stat).

### Multi-color rule strings — the twist

A rule string is read modulo `len(rule)`. When the ant steps onto a
cell with color index `c`, it performs `rule[c]`'s turn (`R`/`L`/`U`
for U-turn / `N` for no turn), advances the cell to `(c + 1) %
len(rule)`, then moves forward. Examples:

| Rule | Behaviour |
|------|-----------|
| `RL` | Classic Langton — chaos for ~10k steps, then highway |
| `RLR` | 3-color variant — symmetric expanding fractal-ish growth |
| `LLRR` | 4-color — draws a tidy growing square spiral |
| `RRLL` | 4-color — cardioid-shaped fractal |
| `LRRRRRLLR` | 9-color — chaotic with mid-run highway-like episodes |

This is why the GUI exposes a free-form rule entry rather than a
dropdown — *any* string of `R/L/U/N` is a legal Turmite-style ant.

### Off-grid handling

The grid is bounded (no toroidal wrap) — wrapping makes the highway
collide with itself. When the ant tries to step off the edge it sets
`alive=False` and freezes; further `step()` calls are no-ops. Pick
grid dimensions that keep the ant inside for the run length you care
about — 200×200 or larger for the full 11k-step highway demo.

### GUI rendering note

The canvas allocates one `tk.Canvas` rectangle per cell once, then
each frame we recolor *only the cells whose color index changed*
(`(grid != painted).nonzero()`). With 50–1000 step-per-frame batches
that's typically just a few hundred reconfigure calls per frame —
plenty of headroom even on a 161×121 grid.

The ant itself is a single triangle polygon repositioned via
`canvas.coords()` and re-pointed by direction (`U/R/D/L` faces).

### TUI rendering note

The TUI uses the upper-half-block character (`▀`) so each terminal
line encodes two grid rows at independent foreground / background
colors. The ant is overlaid as either a directional glyph (`^>v<`)
when it sits on the *top* half of a half-block pair, or as a colored
background when it sits on the bottom half.

## Verifying the rules

The official smoke test (a single step on an empty grid):

```bash
uv run python -c "import sys, numpy as np; sys.path.insert(0, 'langton_ant'); \
    import langton_ant; \
    ant = langton_ant.Ant(np.zeros((50,50), dtype=np.uint8), 25, 25, 0); \
    ant.step(); print(ant.state()['steps'])"
# 1
```

A canonical 100-step run produces exactly **20** flipped cells (this
is reproducible across implementations and is the easiest way to
catch off-by-one bugs in the turn / move ordering):

```python
import numpy as np, langton_ant as la
g, *_ = la.step_n(np.zeros((41, 41), dtype=np.uint8), 20, 20, 0, 100)
assert (g > 0).sum() == 20
```

## Creative twist

**Multi-color rule strings.** The default `RL` is Langton's
two-color ant. Pass any string of `R`, `L`, `U`, `N` and you get a
*Turmite* — a generalized Langton ant on as many colors as the rule
length. Different rules have wildly different aesthetics: `LLRR` is a
neat growing square spiral; `RRLL` is a fractal cardioid; `RLR` is
3-color symmetric chaos. Try them in the GUI — type into the **Rule**
field and hit *Apply*.
