# Carrot in a Box

A 2-player bluffing game where one carrot is hidden in one of two boxes. Each player privately peeks at their own box — then the mind games begin. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `carrot_box.py` | stdlib |
| Modern desktop GUI | `carrot_box_gui.py` | CustomTkinter |
| Modern terminal UI | `carrot_box_tui.py` | Textual |

## Rules

1. Two boxes are placed in front of two players. One box contains a carrot.
2. Each player **privately peeks** at their own box — they now know the full game state (there are only two boxes).
3. Players talk it out. Bluff freely.
4. **Player 1** decides to **SWAP** boxes with Player 2, or **KEEP** them as-is.
5. Both boxes are revealed. Whoever holds the carrot **wins**.

The negotiation phase is pure bluff — once you've peeked you already know the optimal move. Can you convince your opponent otherwise?

## Run

```bash
# CLI
uv run python carrot_box/carrot_box.py

# Desktop GUI (CustomTkinter)
uv run python carrot_box/carrot_box_gui.py

# Terminal UI (Textual)
uv run python carrot_box/carrot_box_tui.py
```

All versions support **hot-seat 2-human** play and a **vs-AI** mode.

In the TUI, use keyboard shortcuts: **p** peek / reveal, **s** swap, **k** keep, **n** new round, **Ctrl+Q** quit.

## Architecture

The CLI module (`carrot_box.py`) holds all game logic. The GUI and TUI import:

- `Game` — pure game state: `peek(player)`, `decide(player, swap)`, `reveal()`
- `ai_decision(ai_has_carrot)` — simple bluff-with-noise AI strategy

## Notes

- This is a **complete-information** bluffing game: after peeking, each player knows *exactly* what's in both boxes. The entire "game" is the negotiation.
- The optimal strategy for Player 1 is deterministic (swap if empty, keep if holding carrot), so the AI implements this with a 5% mistake rate to stay human-like.
- Related to [[Cho-Han]] and other two-outcome bluffing games from [[Game Theory]].
