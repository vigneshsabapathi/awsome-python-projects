# Four in a Row

Connect Four — drop discs into a 7-column, 6-row board. First player to align four discs (horizontally, vertically, or diagonally) wins.

| Version | File | Stack |
|---------|------|-------|
| CLI | `four_in_a_row.py` | stdlib |
| Desktop GUI | `four_in_a_row_gui.py` | CustomTkinter + tk.Canvas |
| Terminal UI | `four_in_a_row_tui.py` | Textual |

## Run

```bash
# CLI — pick mode at start (2 players, or vs AI Easy/Medium/Hard)
uv run python four_in_a_row/four_in_a_row.py

# Desktop GUI — hover preview, click to drop, animated drop
uv run python four_in_a_row/four_in_a_row_gui.py

# Terminal UI — keys 1-7 to drop, n new, m mode, Ctrl+Q quit
uv run python four_in_a_row/four_in_a_row_tui.py
```

## AI

The AI uses **minimax with alpha-beta pruning** plus a **transposition table** so identical positions (reached by different move orders) aren't re-searched. Difficulty maps to search depth:

| Difficulty | Depth | Style |
|------------|-------|-------|
| Easy | 2 | Reactive — blocks immediate threats only |
| Medium | 4 | Plans 4 plies ahead |
| Hard | 6 | Strong tactical play |

Move ordering is **center-out** (the strongest column first) — this dramatically improves alpha-beta cutoffs.

The AI has two hard-coded shortcuts that always run before the search:

1. If a winning move exists, take it.
2. Otherwise, if the opponent has a winning move next turn, block it.

This guarantees the AI never misses a one-move tactic regardless of search depth.

## Architecture

`four_in_a_row.py` holds the shared game logic. Both UIs import:

- `Board` — `drop(col, player)`, `winner()`, `winning_line()`, `is_full()`, `available_cols()`, `next_open_row(col)`
- `ai_move(board, player, depth)` — returns the AI's chosen column
- `PLAYER_1`, `PLAYER_2`, `COLS`, `ROWS`, `DIFFICULTY_DEPTH`, `other()`

Discs are stored as `1` / `2` (player IDs) with `0` for empty. Row 0 is the top of the board; a dropped disc settles at the lowest empty row of the chosen column.

## Notes

- **Why center-out move ordering?** Connect Four's center column is provably the strongest first move. Searching center moves first lets alpha-beta prune more aggressively because we find good lower bounds early.
- **Why a transposition table?** Connect Four has many transpositions — `Drop(3), Drop(4)` reaches the same position as `Drop(4), Drop(3)` at depth 2. Caching by `(grid, depth, to_move)` avoids re-searching.
- **Score depth-bias:** earlier wins are scored higher than later wins (`_WIN_SCORE + depth`), so the AI prefers fast wins and slow losses.
- **GUI threading:** AI search runs on a worker thread so the Tk event loop keeps repainting. The board snapshot is copied into the worker — `Board` is not thread-safe.
