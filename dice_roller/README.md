# Dice Roller

A tabletop-RPG dice tool. Parses standard notation like `2d6+3`, `1d20`, `4d20-1`, `1d100`, and rolls. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI / library | `dice_roller.py` | stdlib (`re`, `random`, `argparse`) |
| Modern desktop GUI | `dice_roller_gui.py` | CustomTkinter |
| Modern terminal UI | `dice_roller_tui.py` | Textual |

## Notation

| Form | Meaning |
|------|---------|
| `NdS` | Roll N dice with S sides each. `d20` is shorthand for `1d20`. |
| `NdS+M` / `NdS-M` | Add or subtract a flat modifier from the total. |
| `NdSkhK` | Keep highest K of N dice — the D&D 5e ability-score roll is `4d6kh3`. |
| `NdSklK` | Keep lowest K (e.g. disadvantage-style aggregates). |
| `expr1, expr2; expr3` | Multiple expressions per line — comma- or semicolon-separated. The CLI prints each plus a grand total. |

## Run

```bash
# REPL
uv run python dice_roller/dice_roller.py

# One-shot
uv run python dice_roller/dice_roller.py 2d6+3 1d20 4d6kh3

# Reproducible rolls (seedable RNG)
uv run python dice_roller/dice_roller.py --seed 42 2d6+3

# Monte Carlo histogram — distribution of N rolls
uv run python dice_roller/dice_roller.py --hist 1000 2d6

# Desktop GUI
uv run python dice_roller/dice_roller_gui.py

# Terminal UI
uv run python dice_roller/dice_roller_tui.py
```

GUI extras: quick-roll preset buttons (`1d6`, `1d20`, `2d6`, `4d6kh3`), big total display, per-die colored cards (dropped dice are grayed out under `kh`/`kl`), and a 10-entry history panel. Press **Enter** to roll.

TUI bindings: **Enter** rolls, **Ctrl+H** toggles history, **Ctrl+L** clears history, **Ctrl+Q** quits.

## Architecture

`dice_roller.py` is the shared library. Both UIs import:

- `parse(notation) -> (count, sides, modifier)` — strict regex parser
- `parse_extended(notation) -> (count, sides, modifier, keep_kind, keep_n)` — supports `kh`/`kl`
- `roll(notation, rng=None) -> dict` — returns `{notation, count, sides, rolls, kept, modifier, total[, keep, keep_n]}`
- `roll_many(notation, n, rng=None)` — bulk roll for histograms
- `split_expressions(line)` — split `'2d6, 1d20'` into parts
- `DiceNotationError` — raised on malformed or out-of-range input

The core regex is `^(\d+)?d(\d+)((?:kh|kl)\d+)?([+-]\d+)?$` (verbose form in source). Count defaults to 1 when omitted (so `d20` works), modifier defaults to 0. Sides must be ≥ 2; count is capped at `MAX_COUNT = 1000` so a stray `99999d6` can't lock the UI.

## Notes

- **Off-by-one trap.** `random.randint(1, sides)` is inclusive on both ends — that's correct. `random.randint(0, sides)` would silently allow a 0 face (and return `sides+1` values total).
- **Seedable rolls.** Pass any `random.Random(seed)` as `rng=` for deterministic replays — used by the `--seed` flag and useful for tests.
- **Keep-highest filtering.** `4d6kh3` rolls four dice, sorts descending, keeps three. The dropped die is shown grayed out in the GUI and struck-through in the TUI so you can see what was discarded.
