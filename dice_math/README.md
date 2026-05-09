# Dice Math

A fast-paced math drill: the program rolls N dice (rendered as ASCII pip
faces), and you have to type the answer before the timer runs away with
your score. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `dice_math.py` | stdlib |
| Desktop GUI | `dice_math_gui.py` | CustomTkinter |
| Terminal UI | `dice_math_tui.py` | Textual |

## Modes

Pick the kind of math you want to drill:

| Mode | Question | Answer |
|------|----------|--------|
| `sum` | What's the total of all the pips? | integer |
| `product` | What's the product of the dice? | integer |
| `max` | What's the largest face shown? | integer |
| `pair` | Do any two dice match? | `y` / `n` |

## Scoring

Each correct round earns `100 - 8 * elapsed_seconds` points (clamped to a
minimum of `10` for slow-but-correct answers). Wrong or empty answers earn
zero **and reset your streak**. Final scores get appended to a JSON
leaderboard at `dice_math/dice_math_scores.json` (top 10 kept).

## Run

```bash
# CLI — defaults: sum mode, 3 dice, 10 rounds
uv run python dice_math/dice_math.py

# Pick a different mode and difficulty
uv run python dice_math/dice_math.py --mode product --num-dice 4 --rounds 5

# Reproducible rolls (handy for demos / tests)
uv run python dice_math/dice_math.py --seed 42

# Desktop GUI (CustomTkinter)
uv run python dice_math/dice_math_gui.py

# Terminal UI (Textual)
uv run python dice_math/dice_math_tui.py
```

## Bindings

**GUI:** `Enter` submits, mode dropdown switches mode, slider sets dice
count (2..6), `New Round` re-rolls.

**TUI:** `Enter` submits, `n` re-rolls, `m` cycles modes, `+` / `-` change
dice count, `Ctrl+Q` quits.

## Architecture

`dice_math.py` holds all the pure logic — both UIs import:

- `roll(num_dice, rng=None) -> list[int]` — accepts a `random.Random` for
  reproducibility
- `dice_face(value) -> str` — 5-line 3x3 ASCII pip face for one die
- `format_dice(values) -> str` — joins multiple dice horizontally
- `correct_answer(values, mode) -> int | str` — the expected answer
- `score_round(answer, correct, elapsed_s) -> int` — speed-weighted points
- `save_high_score(name, score, mode)` / `load_high_scores()` — JSON
  leaderboard persistence
- `MODES` — the tuple `('sum', 'product', 'max', 'pair')`

## Notes

- Dice are rendered with ASCII pips (`o` for a pip, `+--+` borders). Each
  die is exactly 5 lines tall, 7 chars wide, with a 1-char gap between dice.
- Pip patterns follow the standard Western convention (1 center, 2 anti-
  diagonal, 3 diagonal, 4 corners, 5 corners + center, 6 two columns).
- `correct_answer` for `pair` mode returns `'y'` or `'n'`; the matcher
  accepts case-insensitive input.
- The leaderboard file is created lazily; the project still works in a
  read-only directory (saves silently no-op).
