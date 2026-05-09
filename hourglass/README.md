# Hourglass

An animated ASCII hourglass. Sand falls one grain per frame from the top chamber through a narrow neck into the bottom chamber, where it piles up with an angle-of-repose feel — each new grain settles at the lowest reachable position, sliding diagonally toward the lower side.

| Version | File | Stack |
|---------|------|-------|
| CLI animation | `hourglass.py` | stdlib |
| Desktop GUI | `hourglass_gui.py` | CustomTkinter + tk.Canvas |
| Terminal UI | `hourglass_tui.py` | Textual |

## Run

```bash
# CLI animation (Ctrl+C to quit)
uv run python hourglass/hourglass.py

# Desktop GUI — flip / pause / reset / earthquake / speed slider
uv run python hourglass/hourglass_gui.py

# Terminal UI
uv run python hourglass/hourglass_tui.py
```

## Twist

Two extras on top of the basic simulation:

1. **Color-graded grains.** Each grain remembers when it fell. The GUI/TUI renderers shade grains by age, using a five-band golden palette (pale honey for the youngest grain through deep amber for the oldest). The CLI uses a single character but the rendering pipeline still tracks ages.
2. **Earthquake button.** Lifts the entire bottom pile and re-drops it grain-by-grain through the settle algorithm. Useful for re-shaping a too-perfectly-symmetrical pile.

## Architecture

`hourglass.py` exposes the simulation as a pure `Hourglass(width, total_grains)` class. The grid is a 2-D list where each cell is either `None` or an integer "age". Public API:

- `step()` — advance one frame (one grain falls through the neck)
- `render()` — return the ASCII frame as a string
- `is_done()` — top chamber and neck are empty
- `flip()`, `reset()`, `shake()` — mutate state for UI buttons
- `top_count()`, `bottom_count()` — live grain counts
- `cells()` — iterator over `(row, col, age_or_None)` for GUIs

The two UIs both `from hourglass import Hourglass, DEFAULT_WIDTH` and never re-implement the simulation. The GUI uses `tk.Canvas.create_oval` for grains and straight-line wall segments. The TUI uses Rich color markup so the same `o` character is shaded by age.

## Settling rules

A grain entering the neck is placed by `_settle_into_bottom`:

1. Start in the centre column at the row just below the neck.
2. While the cell directly below is empty, fall straight down.
3. If blocked, slide diagonally — prefer the side with the **shorter** column height. This is what produces the symmetrical pile.
4. If both diagonals are blocked, settle in the current cell.
5. If the centre column itself is full to the neck, walk the surface laterally and pick the empty cell closest to the centre on the highest available row.

Capacity matches: top chamber and bottom chamber both hold `((W+1)/2)^2` cells when `W` is odd, so no grains are lost during a full drain.

## Notes

- `width` must be **odd** so the neck is a single column. The default is 15.
- The status line under each frame reports `top` / `bottom` / `step` so you can sanity-check that grains are conserved.
- Speed in the GUI is variable from 2 fps to 60 fps. The TUI runs at a fixed 12 fps because terminal redraws above ~20 fps tend to flicker.
