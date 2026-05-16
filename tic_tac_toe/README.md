# Tic-Tac-Toe

The classic 3×3 alignment game. Two players alternate placing marks; the first to get three in a row (row, column, or diagonal) wins. With perfect play, the game is always a draw — it is fully solved. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `tic_tac_toe.py` | stdlib |
| Modern desktop GUI | `tic_tac_toe_gui.py` | CustomTkinter |
| Modern terminal UI | `tic_tac_toe_tui.py` | Textual |

## Modes

| Mode | Description |
|------|-------------|
| **2P** | Two human players, hot-seat |
| **AI Easy** | AI picks the optimal move only 30% of the time (random otherwise) |
| **AI Medium** | AI picks the optimal move 70% of the time |
| **AI Hard** | AI plays perfectly (minimax — unbeatable) |
| **AI vs AI** | Watch two perfect AIs play — always draws |
| **AI Hard misère** | Hard AI, but the player who completes a line **loses** |

## Run

```bash
# CLI
uv run python tic_tac_toe/tic_tac_toe.py

# Desktop GUI (CustomTkinter)
uv run python tic_tac_toe/tic_tac_toe_gui.py

# Terminal UI (Textual)
uv run python tic_tac_toe/tic_tac_toe_tui.py
```

## GUI Features

- Dark-themed (`#0f172a`) CustomTkinter window
- 3×3 button grid; X in sky-blue, O in orange
- Mode dropdown (`2P / AI Easy / AI Medium / AI Hard / AI vs AI / AI Hard misère`) — changing mode starts a new game automatically
- Winning line highlighted in green
- AI runs in a background thread so the UI stays responsive; shows "AI thinking…" status while computing
- **New Game** button resets without re-launching

## TUI Features (Textual)

- Full keyboard control: numpad layout (`7 8 9 / 4 5 6 / 1 2 3`) maps digits to cells
- Mode chips at the top highlight the active mode; **m** cycles through all six modes
- **n** for a new game, **Ctrl+Q** to quit
- Winning cells highlighted in green; X in sky-blue, O in orange
- AI vs AI demo auto-plays with a short timer between moves so you can watch

## Architecture

The CLI module (`tic_tac_toe.py`) holds all shared game logic. Both GUIs import from it:

- `Board` — pure game state with `play`, `undo`, `winner`, `is_full`, `legal_moves`, `legal_count`, `state`, `winning_line`
- `minimax(board, player, depth, alpha, beta, misere)` — minimax with alpha-beta pruning; returns `(score, move)`
- `ai_move(board, player, difficulty, misere)` — imperfect-AI wrapper: picks optimal with probability `DIFFICULTY_OPTIMAL_P[difficulty]`, otherwise random
- `DIFFICULTY_OPTIMAL_P` — `{'easy': 0.30, 'medium': 0.70, 'hard': 1.00}`
- `other(player)` — flips between X (1) and O (2)

### AI design

The minimax search explores the full 3×3 game tree (at most 9 plies). Alpha-beta pruning with center-first, corner-next move ordering keeps it instantaneous. Score is relative to the *root* player: `+10 − plies_used` for a win, `−10 + plies_used` for a loss, `0` for a draw.

In **misère mode**, completing a three-in-a-row line counts as a *loss* for the player who placed the final mark. The minimax function flips the terminal evaluation accordingly, and `ai_move` passes `misere=True` through.

## Notes

- The CLI uses numpad layout (1 = bottom-left, 9 = top-right) for cell selection.
- `Board.legal_moves()` returns a `_LegalMoves` list that also compares equal to its length integer — so `board.legal_moves() == 8` works correctly.
- Players are stored as integers (1 = X, 2 = O) internally; `Board.play` also accepts the strings `'X'` / `'O'` for friendlier caller code.
