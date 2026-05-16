# 2048

Slide numbered tiles on a 4×4 grid. When two tiles with the same value collide they merge into one worth their sum. The classic goal is to create a 2048 tile, but the game keeps going as long as moves exist.

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `twenty_forty_eight.py` | stdlib |
| Modern desktop GUI | `twenty_forty_eight_gui.py` | CustomTkinter + tkinter |
| Modern terminal UI | `twenty_forty_eight_tui.py` | Textual |

## Controls

| Key | Action |
|-----|--------|
| Arrow keys / WASD | Slide tiles |
| n | New game |
| u | Undo last move |
| Ctrl+Q | Quit (TUI) |
| q | Quit (CLI) |

## Run

```bash
# CLI
uv run python twenty_forty_eight/twenty_forty_eight.py

# Desktop GUI (CustomTkinter)
uv run python twenty_forty_eight/twenty_forty_eight_gui.py

# Terminal UI (Textual)
uv run python twenty_forty_eight/twenty_forty_eight_tui.py
```

## Features

- **Classic 2048 palette** — tile colours match the original web game (cream → yellow → orange → gold) across all three front-ends.
- **Undo** — up to 50 moves deep; the full undo stack is preserved for the life of a session.
- **Expectimax AI** — depth-3 chance-node search. In the CLI press `a` to play one AI move or `h` for a hint; the GUI exposes an *AI move* button and an *Auto play* toggle.
- **Best-score persistence** — the GUI saves the all-time high score to `best_score.json` in the project folder.

## Architecture

`twenty_forty_eight.py` is the pure game layer — no I/O, no animation. All three front-ends import:

- `Game(rng)` — board state with `move(direction)`, `spawn_tile()`, `is_won()`, `is_lost()`, `state()`
- `expectimax_best_move(game, depth)` — chance-node AI search
- `UP`, `DOWN`, `LEFT`, `RIGHT` — direction constants

## Notes

- After each successful move the board spawns a 2 (90 %) or 4 (10 %) on a random empty cell — same probabilities as the original game.
- `is_won()` returns `True` once any tile reaches 2048 but the game continues; `is_lost()` is `True` only when no direction would change the board.
- The expectimax heuristic rewards empty cells, monotone rows/columns, and anchoring the largest tile in a corner — the three signals that drive the strongest hand-tuned 2048 bots.
