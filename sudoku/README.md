# Sudoku

Generate, solve, and play 9x9 sudoku puzzles. Three flavors share a single pure-Python core.

| Version | File | Stack |
|---------|------|-------|
| CLI | `sudoku.py` | stdlib |
| Desktop GUI | `sudoku_gui.py` | CustomTkinter |
| Terminal UI | `sudoku_tui.py` | Textual |

## Run

```bash
# CLI — interactive puzzle in the terminal
uv run python sudoku/sudoku.py
uv run python sudoku/sudoku.py --difficulty hard --seed 42
uv run python sudoku/sudoku.py --solve-only        # print puzzle + solution

# Desktop GUI
uv run python sudoku/sudoku_gui.py

# Terminal UI
uv run python sudoku/sudoku_tui.py
```

## Difficulty

Difficulty is controlled by the number of cells *given* at puzzle start — fewer givens means a harder puzzle.

| Level   | Givens |
|---------|--------|
| easy    | 40     |
| medium  | 32     |
| hard    | 26     |

Every generated puzzle is guaranteed to have **exactly one** solution: the generator removes a candidate cell only if the resulting puzzle stays uniquely solvable.

## Solver

`solve(board)` is a backtracking solver with the **MRV heuristic** (minimum remaining values): at each step it picks the empty cell with the fewest legal candidates. Combined with eager constraint propagation (legal candidates are recomputed from row, column, and box peers each step), this turns the worst case into something that solves a 17-given puzzle in milliseconds.

If a cell has zero candidates the search prunes immediately. If a cell has exactly one, that's a forced move — the solver tries it without branching.

## Generation

1. Seed an empty grid and fill it with one random valid completion (same backtracker, but with the candidate list shuffled).
2. Walk all 81 cells in random order. Tentatively blank each cell, then re-count solutions up to a limit of 2.
3. If the puzzle now has two solutions, restore the digit. Otherwise, leave it blank.
4. Stop when the desired givens count is reached.

## Architecture

`sudoku.py` exports the shared core:

- `Board(grid)` — 9x9 grid plus a `givens` set of locked cells
- `solve(board) -> bool` — backtracking + MRV; mutates board in place
- `generate(difficulty, rng) -> Board` — uniquely-solvable puzzle
- `is_valid(board)`, `is_solved(board)`, `hints_remaining(board)`
- `count_solutions(board, limit=2)` — used by the generator
- `format_board(board)` — pretty-print with 3x3 box separators

Both UIs import from this core; no duplicated game logic.

## Controls

**CLI** — Type `r c d` (1-indexed) to place digit `d` at row `r`, column `c`. `solve`, `hint`, `reset`, `quit`.

**GUI** — Click a cell, type 1-9. Backspace/empty to clear. Sidebar buttons: New Game, Hint, Solve, Undo, Reset. Givens are read-only and rendered in slate; your entries are blue and turn red on conflict.

**TUI** — Arrow keys to move the cursor, 1-9 to fill, 0/space/backspace to clear. `s` solve, `h` hint, `n` new, `Tab` cycle difficulty, `Ctrl+Z` undo, `Ctrl+Q` quit.
