# Royal Game of Ur

The Royal Game of Ur is a Mesopotamian race game from ~2600 BCE — the
oldest board game with a known full ruleset (cuneiform tablet, BM 33333,
~177 BCE). Each player has 7 pieces racing along a 14-square track.
Three UIs share one game core.

- `ur.py` — CLI + the `Board` class + dice + the **expectimax** AI.
- `ur_gui.py` — CustomTkinter desktop UI with H-shaped board, animated
  pieces, dice animation, and clickable piece selection.
- `ur_tui.py` — Textual terminal UI with key bindings and rosette markers.

## Rules (Finkel reconstruction)

```
P2 path:  4  3  2  1                14 13
                    5 6 7 8 9 10 11 12        (shared row)
P1 path:  4  3  2  1                14 13
```

- Each player starts with 7 pieces in their start pile.
- On a turn, **roll 4 binary dice** — the score is how many "marked"
  corners come up: a value in 0..4 with binomial(4, ½) probabilities
  (1/16, 4/16, 6/16, 4/16, 1/16).
- Move one of your pieces forward by the rolled amount along your path.
- **Rosettes** (squares 4, 8, 14, marked `*`):
  - Landing on one grants a **bonus turn** (roll again).
  - Pieces sitting on a rosette are **safe** (cannot be captured) under
    Finkel rules.
- **Capture** — if you land on an opponent's piece in the **shared zone**
  (squares 5–12), the opponent's piece returns to start. The center
  rosette (square 8) is safe in Finkel rules; in the classroom variant
  it is not.
- **Bear off** — to remove a piece (square 14 → finish) the roll must be
  **exact**.
- First to bear off all 7 pieces **wins**.

## Run

```
uv run python ur/ur.py        # CLI
uv run python ur/ur_gui.py    # GUI
uv run python ur/ur_tui.py    # TUI
```

## API smoke test

```python
import random, ur
b = ur.Board()
r = b.roll(random.Random(0))   # 0..4, binomial-distributed
assert 0 <= r <= 4
moves = b.legal_moves(ur.PLAYER_1, 4)  # 7 pieces in start pile -> 7 legal
assert len(moves) == 7
res = b.move(ur.PLAYER_1, 0, 4)  # piece 0 to square 4 (a rosette)
assert res['rosette'] and res['free_turn']
```

## AI — expectimax over dice rolls

`ur.ai_move(board, player, dice, depth=2)` runs **expectimax**:

- **Max** at our decision nodes — pick the move maximizing expected score.
- **Min** at the opponent's decision nodes.
- **Chance** between turns — average over the 5 possible rolls weighted by
  their binomial probabilities.

| Mode    | Depth |
|---------|-------|
| Easy    | 1     |
| Medium  | 2     |
| Hard    | 3     |

The static evaluator scores by:

- Finished pieces (×12), heaviest weight.
- Track progress per piece (raw position).
- Rosette bonus (+2) for occupying a safe square.
- Small penalty (−0.5) for own pieces sitting in the capture zone, with
  symmetric reward for opponent pieces there.

## Twist: Finkel vs Classroom

Toggle the rules in any UI. Finkel (default) makes rosettes safe; the
classroom simplification leaves the central rosette capturable, which
changes both opening play and AI evaluation.
