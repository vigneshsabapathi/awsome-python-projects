# Mancala

Two-player Kalah Mancala — the most common Mancala variant — with three UIs
that share one game core.

- `mancala.py` — CLI + the `Board` class + the AI search.
- `mancala_gui.py` — CustomTkinter desktop UI with **animated stone-sowing**
  (one stone at a time, ~150ms apart), AI mode dropdown, and an **Awari toggle**
  (Awari = no extra-turn rule).
- `mancala_tui.py` — Textual terminal UI with `[N]` cells, color-coded turns,
  legal-move highlighting, and key bindings.

## Rules (Kalah)

Layout — 6 pits per player + one store on the right:

```
P2:  12  11  10   9   8   7
[P2 store=13]            [P1 store=6]
P1:   0   1   2   3   4   5
```

Each pit starts with 4 stones. On a turn:

1. Pick up all stones from one of your own pits.
2. Sow them counter-clockwise, one per cell, **skipping the opponent's store**.
3. **Free turn** if the last stone lands in your own store.
4. **Capture** if the last stone lands in your own *empty* pit and the opposite
   pit has stones — take both into your store.
5. The game ends when a player's six pits are all empty. The other player
   sweeps any remaining stones on their side into their store. Most stones in
   your store wins.

The Awari variant disables rule 3 (no free turn).

## Run

```
uv run python mancala/mancala.py        # CLI
uv run python mancala/mancala_gui.py    # GUI
uv run python mancala/mancala_tui.py    # TUI
```

## API smoke test

```python
import mancala
b = mancala.Board()
res = b.move(2)              # P1 plays pit 2 (0-indexed)
assert b.pits[6] == 1        # one stone landed in P1's store
assert res['free_turn']      # last stone in own store -> free turn
assert len(b.pits) == 14
```

## AI

`mancala.ai_move(board, player, depth=4)` runs minimax with alpha-beta pruning
and a transposition table. Difficulty maps to depth:

| Mode    | Depth |
|---------|-------|
| Easy    | 2     |
| Medium  | 4     |
| Hard    | 6     |
| Expert  | 7     |

The evaluator scores by store-difference (×6 weight), stone-distribution
difference, and capture-potential bonus.
