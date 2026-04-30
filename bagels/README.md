# Bagels

A deductive logic game where you guess a 3-digit secret number using clues. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `bagels.py` | stdlib |
| Modern desktop GUI | `bagels_gui.py` | CustomTkinter |
| Modern terminal UI | `bagels_tui.py` | Textual |

## Clues

| Clue | Color | Meaning |
|------|-------|---------|
| **Fermi** | green | A digit is correct **and** in the right position. |
| **Pico** | yellow | A digit is correct but in the **wrong** position. |
| **Bagels** | gray | The digit is not in the secret number. |

You have **10 guesses**. The secret has **no repeated digits**.

## Run

```bash
# CLI
uv run python bagels/bagels.py

# Desktop GUI (CustomTkinter)
uv run python bagels/bagels_gui.py

# Terminal UI (Textual)
uv run python bagels/bagels_tui.py
```

The GUI and TUI versions both render a Wordle-style board: each guess fills a row of three color-coded tiles, one per digit position. Press **Ctrl+N** in the TUI for a new game, **Ctrl+Q** to quit.

## Architecture

The CLI module (`bagels.py`) holds the shared game logic. Both GUIs import:

- `getSecretNum()` — produces a random no-repeat n-digit string
- `getCluesPerPosition(guess, secret)` — returns `['Fermi'|'Pico'|'Bagels']` per position, used to color tiles
- `getClues(guess, secret)` — original CLI clue string (sorted, alphabetized)
- `NUM_DIGITS`, `MAX_GUESSES` — constants

## Notes

- Digits are stored as **strings**, not integers — `'026'` ≠ `'26'`, but `int('026') == 26`. String comparison preserves leading zeros.
- The original CLI sorts clues alphabetically so the order doesn't reveal which digit matched which position. The GUI/TUI tile coloring intentionally exposes per-position information — that's the visual game design (same as Wordle).
