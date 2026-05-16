# Flooder

A flood-fill puzzle game. The grid starts full of randomly coloured cells.
The top-left corner anchors your **controlled region**. Each turn you pick one
of six colours — your region expands to absorb every adjacent cell that shares
that colour. Win by capturing the entire grid within the move budget (25 moves
for the default 14 × 14 grid).

## Twist — Greedy AI Hint

Press **H** (or click *Hint* in the GUI) for an AI suggestion. The hint engine
runs a one-step look-ahead and returns the colour that maximises immediate
region growth. It won't solve the puzzle optimally (the general problem is
NP-hard) but it gives a useful nudge when you're stuck.

## Files

| File | Description |
|------|-------------|
| `flooder.py` | Core `Game` class + CLI (`uv run python flooder/flooder.py`) |
| `flooder_gui.py` | CustomTkinter dark-theme GUI |
| `flooder_tui.py` | Textual TUI |

## How to Run

```bash
# CLI
uv run python flooder/flooder.py

# GUI (CustomTkinter)
uv run python flooder/flooder_gui.py

# TUI (Textual)
uv run python flooder/flooder_tui.py
```

## Controls

### CLI
| Input | Action |
|-------|--------|
| `1`–`6` | Pick colour |
| `H` | Greedy hint |
| `N` | New game |
| `Q` | Quit |

### GUI
| Input | Action |
|-------|--------|
| Click colour button | Flood |
| `1`–`6` | Pick colour by keyboard |
| `H` | Hint |
| `N` | New game |

### TUI
| Key | Action |
|-----|--------|
| `1`–`6` | Pick colour |
| `H` | Hint |
| `N` | New game |
| `Ctrl+Q` | Quit |

## Algorithm

Flood is a two-phase BFS:

1. **Collect** — BFS from `(0, 0)` gathering all cells currently sharing the
   top-left colour (the controlled region).
2. **Paint + expand** — repaint the region with the new colour, then BFS
   outward absorbing all adjacent cells that already have the new colour.

The greedy hint simulates each candidate colour with a non-mutating version of
the same BFS and returns the one that yields the largest region.

## Game parameters

```python
Game(width=14, height=14, num_colors=6, max_moves=25, rng=None)
```

Pass a `random.Random` instance to `rng` for reproducible puzzles.
