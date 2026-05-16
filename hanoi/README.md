# Tower of Hanoi

Classic 3-peg N-disk puzzle solved optimally. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `hanoi.py` | stdlib |
| Modern desktop GUI | `hanoi_gui.py` | CustomTkinter |
| Modern terminal UI | `hanoi_tui.py` | Textual |

## Rules

Move all N disks from peg **A** to peg **C** using peg **B** as scratch space, moving one disk at a time, never placing a larger disk on top of a smaller one. The optimal solution takes exactly **2^N − 1** moves — this is a proven minimum.

## Run

```bash
# CLI — animated 4-disk solve (recursive solver, default)
uv run python hanoi/hanoi.py

# CLI — 6-disk solve
uv run python hanoi/hanoi.py 6

# CLI — use iterative parity solver
uv run python hanoi/hanoi.py 5 iter

# Desktop GUI (CustomTkinter)
uv run python hanoi/hanoi_gui.py

# Terminal UI (Textual)
uv run python hanoi/hanoi_tui.py
```

## GUI features

- Dark-theme canvas with three vertical pegs rendered in colour.
- Click a peg to select it as source; click a second peg to move the top disk.
- Each disk has a distinct colour (10-colour palette, largest = red).
- **Auto-solve** button animates the full optimal sequence step-by-step.
- **N slider** (range 3–10) resets the board to a new disk count.
- Toggle between the recursive and iterative parity solver.
- Status bar shows move count vs. the 2^N − 1 optimum.

## TUI features

| Key | Action |
|-----|--------|
| `1` / `2` / `3` | First press selects source peg (A/B/C); second press picks destination |
| `s` | Auto-solve from the current state |
| `n` | New game — reset to all disks on A |
| `+` / `-` | Increase / decrease disk count (3–10) |
| `i` | Toggle iterative parity solver |
| Ctrl+Q | Quit |

Peg columns render colour-coded ASCII disk bars that update in real time.

## Architecture

The CLI module (`hanoi.py`) holds all shared game logic. Both GUIs import:

- `Hanoi` — state machine class; `reset()`, `move(src, dst)`, `is_solved(target)`, `state()`
- `solve_recursive(n, src, aux, dst)` — classic recursive solver; returns exactly 2^N − 1 `(src, dst)` tuples
- `solve_iterative(n, src, aux, dst)` — parity-bit solver; same move count, no call stack
- `render(game)` — ASCII board string (CLI only)
- `PEGS` — `('A', 'B', 'C')` peg name constants

## Notes

- Both solvers produce the **same optimal move count** (2^N − 1); they differ only in implementation strategy.
- The iterative solver uses the bit-trick: on step *k*, the disk to move is `(k & -k).bit_length()` — the position of the lowest set bit.
- Auto-solve frame rate scales with N so large puzzles do not crawl: `delay = max(0.05, min(0.5, 1.5 / moves))`.
