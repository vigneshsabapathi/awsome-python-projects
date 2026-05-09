# Sliding Tile Puzzle

The classic 15-puzzle (and its 8- and 24-puzzle siblings). An n*n grid holds
the numbers 1..n*n-1 plus a single blank cell. Slide tiles into the blank
until the numbers are in order with the blank at the bottom-right.

Three front ends share the same pure model:

| File | What it is |
|------|------------|
| `sliding_puzzle.py` | Pure model + A* solver + CLI |
| `sliding_puzzle_gui.py` | CustomTkinter desktop app with sliding-tile animation |
| `sliding_puzzle_tui.py` | Textual TUI with arrow-key controls |

## Run

```powershell
uv run python sliding_puzzle/sliding_puzzle.py        # CLI
uv run python sliding_puzzle/sliding_puzzle_gui.py    # desktop
uv run python sliding_puzzle/sliding_puzzle_tui.py    # terminal UI
```

## Controls

* **GUI**: click any tile orthogonally adjacent to the blank, or use arrow
  keys / WASD. The **Hint** button highlights the next A*-optimal tile to
  slide; **Solve** plays out the whole optimal plan with animation.
* **TUI**: arrow keys (or WASD) slide; `n` new puzzle; `h` hint; `p`
  inversion-count parity; `Ctrl+Q` quit.
* **CLI**: `w/a/s/d` move, `h` hint, `n` new, `r` reshuffle, `p` parity,
  `q` quit.

## API

```python
from sliding_puzzle import Puzzle, solve, hint, is_solvable, manhattan

p = Puzzle(n=4)                 # blank starts in the bottom-right corner
p.shuffle(random.Random(42))    # legal-move random walk → always solvable
p.legal_moves()                 # ['up', 'down', 'left', 'right'] subset
p.slide('up')                   # mutate; returns False if blocked
p.is_solved()                   # bool
p.state()                       # flat tuple, hashable

solve(p)                        # A* with Manhattan heuristic → list[str]
hint(p)                         # next optimal direction or None
is_solvable(p)                  # parity check (always True after shuffle)
```

## A* solver

The solver uses A* with the **Manhattan-distance** heuristic:

```
h(s) = sum over non-blank tiles of |row_distance| + |col_distance| to goal
```

Manhattan is admissible (never overestimates — every tile must travel at
least its Manhattan distance) and consistent, so A* finds the *optimal*
solution and never re-expands a closed node.

| Board | Typical solution length | Solve time |
|-------|------------------------|------------|
| 3×3 (8-puzzle), shuffle 60 | 20–30 moves | <10 ms |
| 4×4 (15-puzzle), shuffle 40 | 30–40 moves | <500 ms |
| 4×4 fully randomised | up to 80 moves | seconds–minutes |
| 5×5 (24-puzzle) | 50+ moves | impractical with pure Manhattan |

The 24-puzzle is included as a playable mode but the hint/solve buttons
are disabled — for those sizes you'd need a stronger heuristic
(linear-conflict, walking distance, or pattern databases).

## Solvability — the inversion-count parity

Half of all permutations of the 16 cells are reachable from the goal; the
other half form a separate orbit. The test:

* **Odd n**: solvable iff the inversion count of the numbered tiles is even.
* **Even n**: solvable iff
  `inversions + blank_row_from_bottom (1-indexed)` is **odd**.

The shuffle always uses a legal-move random walk, so every position the UI
hands you is reachable. The HUD shows the parity flag live for the curious.

## Twist

* **Variable size** — pick 3, 4, or 5 from the GUI dropdown / CLI prompt.
* **A* hint system** — flashes the next optimal tile in orange.
* **Live solvability flag** — green "solvable" / red "unsolvable" chip.
