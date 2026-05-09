# Cho-Han  丁  半

Traditional Japanese dice gambling game. The dealer shakes two dice in a
bamboo cup; the player bets on whether the sum will be **chō (丁, even)** or
**han (半, odd)**. Three frontends share one set of pure functions in
`cho_han.py`.

## Run

```powershell
# CLI
uv run python cho_han/cho_han.py

# Desktop GUI (CustomTkinter, dark + tatami palette)
uv run python cho_han/cho_han_gui.py

# Terminal UI (Textual)
uv run python cho_han/cho_han_tui.py
```

## Files

| File | What |
|---|---|
| `cho_han.py`     | Pure logic + CLI. `roll_dice`, `outcome`, `play_round`, `ruin_probability`. |
| `cho_han_gui.py` | CustomTkinter window with animated dice cup, bankroll chart, ruin estimate. |
| `cho_han_tui.py` | Textual TUI with the same gameplay and keyboard bindings. |

## Gameplay

- Starting balance: ¥5,000.
- Wager in steps of ¥100 (slider in GUI; `+`/`-` in TUI).
- Pick **Cho** (even) or **Han** (odd). Win → +wager, lose → -wager.
- Two fair d6 → P(even) = P(odd) = 1/2. The base game has zero house edge.

### TUI bindings

| Key | Action |
|---|---|
| `c` | Bet chō (even) |
| `h` | Bet han (odd) |
| `+` / `-` | Adjust wager by ¥100 |
| `n` | New round / reset table after bust |
| `Ctrl+Q` | Quit |

## Twist

A **Monte Carlo "ruin probability"** estimator runs every time the wager or
balance changes. With ~1,500 trials of 200 rounds each, it shows the chance
that the bankroll hits zero before round 200 — a classic
[gambler's ruin](https://en.wikipedia.org/wiki/Gambler%27s_ruin) random walk.
Even on a fair 50/50 game, the ruin probability climbs steeply as
`wager / bankroll` grows. The GUI also plots a **bankroll history chart**
across rounds.

## Smoke test

```powershell
uv run python -c "import sys; sys.path.insert(0, 'cho_han'); import cho_han; print(cho_han.outcome((3, 4)))"
# han
```
