# J'Accuse!

A mystery deduction game in three flavours — CLI, desktop GUI, and TUI.

A crime has been committed in the Belle Epoque. Six suspects, five witnesses,
and only eight rounds before the trail goes cold. Each round you visit a
witness who shares one detail about the culprit's appearance — hair colour,
clothing, or accessory. When you're confident, point a finger and shout
*J'Accuse!*

## The twist — witnesses sometimes lie

Every witness has a 10% chance of giving a false clue. The strict candidate
filter (treats every clue as truth) may eliminate the real culprit unfairly,
so the **auto-deduce** hint shows two views:

- **Strict** — suspects consistent with every clue
- **Lie-tolerant** — suspects matching the *most* clues (best guess under
  uncertainty)

When the strict filter goes empty, somebody lied — and the lie-tolerant set
is your safest play.

## Run

```sh
uv run python jaccuse/jaccuse.py        # CLI
uv run python jaccuse/jaccuse_gui.py    # CustomTkinter GUI
uv run python jaccuse/jaccuse_tui.py    # Textual TUI
```

## Files

- `jaccuse.py` — pure game logic. `Game(suspects, witnesses, max_rounds, rng)`
  with `visit(witness)`, `accuse(name)`, `deduce_strict()`,
  `deduce_tolerant()`. Inject your own `random.Random` for reproducible runs.
- `jaccuse_gui.py` — film-noir CustomTkinter UI with sepia accents, suspect
  cards, witness panel, clue log, and an accusation modal.
- `jaccuse_tui.py` — Textual TUI; numbers visit witnesses, `a` accuses,
  `h` toggles the hint, `n` starts a new case, `Ctrl+Q` quits.

## Smoke test

```sh
uv run python -c "import sys, random; sys.path.insert(0, 'jaccuse'); \
import jaccuse; g = jaccuse.Game(rng=random.Random(0)); print(len(g.suspects))"
```
