# Three-Card Monte

The classic street-corner shuffle game. The dealer shows three cards (one is the queen), flips them face down, then shuffles by repeatedly swapping pairs of positions. You try to track the queen.

| Version | File | Stack |
|---------|------|-------|
| CLI | `three_card.py` | stdlib (animated text shuffle) |
| Desktop GUI | `three_card_gui.py` | CustomTkinter + `tk.Canvas` animation |
| Terminal UI | `three_card_tui.py` | Textual (dark Tailwind palette) |

## How to play

1. The dealer reveals the queen's starting position.
2. The cards flip face down and the dealer performs `num_swaps` random pairwise swaps.
3. You pick the slot you think holds the queen.

The math: with random swaps, the chance of *correctly* tracking the queen drops fast — but it never falls below 1/3, because random swaps are still informative. The real game is rigged with sleight of hand. Here, the only deception is whether you can actually follow the swaps.

## Run

```bash
# CLI
uv run python three_card/three_card.py

# Desktop GUI (CustomTkinter)
uv run python three_card/three_card_gui.py

# Terminal UI (Textual)
uv run python three_card/three_card_tui.py
```

## Architecture

The CLI module exposes a pure `Game` class — no I/O, deterministic when seeded. Both GUIs import it:

```python
from three_card import Game, NUM_CARDS, QUEEN
```

`Game` API:

| Member | What it does |
|---|---|
| `Game(num_swaps=10, rng=None)` | Construct. Pass a `random.Random(seed)` for reproducibility. |
| `setup()` | Place the queen randomly, plan & apply `num_swaps` distinct swaps, record `history`. |
| `swap(i, j)` | Manually swap two positions (used internally; exposed for tests / replay). |
| `pick(i) -> bool` | Player picks slot `i`. Returns `True` if the queen was there. |
| `state() -> dict` | Snapshot: `{cards, queen, initial_queen, history, num_swaps, finished, won}`. |

`history` is the list of `(i, j)` swap pairs in execution order — the GUIs replay it for the animation, and the "show solution" feature plays it back with the queen face up.

## Features

- **Tracking-difficulty slider** (GUI: 3..40 swaps, TUI: `+` / `-` keys)
- **Animation speed slider** (GUI: 60..600 ms per swap)
- **Track-eye mode** (GUI checkbox) — keeps the queen highlighted during the shuffle so you can practice
- **Show solution / replay** — re-runs the same shuffle with the queen visible the whole time
- **Stats panel** — running wins / losses / streak / accuracy across rounds

## Bindings

GUI: click cards to pick. TUI:

| Key | Action |
|---|---|
| 1 / 2 / 3 | Pick that card |
| s | Start the shuffle |
| r | Replay solution |
| n | New round |
| + / - | More / fewer swaps |
| Ctrl+Q | Quit |

## Notes

- The `Game` engine takes a dependency-injected `rng` so tests are seedable. Frontends use module-level `random` by default.
- `setup()` plans swaps where `i != j` — a no-op swap doesn't move the queen and would just waste an animation frame.
- The CLI's animation is intentionally lo-fi (printed swap notation + a `time.sleep`); the GUI does an actual canvas tween with parabolic arcs for the two cards trading places.
