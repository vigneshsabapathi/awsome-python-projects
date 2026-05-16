# Gullible

An interactive trick game. The program asks whether you are gullible. Saying
"yes" proves the point. Saying anything *other* than a clean "no" loops back
or accepts your answer as gullibility. Only a firm "no" (or an international
equivalent) lets you escape.

Five question variants keep repeat players on their toes, including classics
like "do you always say yes?" and a liar's-paradox variant.

## Files

| File | Description |
|------|-------------|
| `gullible.py` | Core logic + CLI |
| `gullible_gui.py` | CustomTkinter dark-theme GUI |
| `gullible_tui.py` | Textual terminal UI |

## Run

```bash
# CLI
uv run python gullible/gullible.py

# GUI
uv run python gullible/gullible_gui.py

# TUI
uv run python gullible/gullible_tui.py
```

## Key bindings (GUI)

| Key | Action |
|-----|--------|
| Enter | Submit answer |
| Ctrl+N | New round |
| Ctrl+Q | Quit |

## Key bindings (TUI)

| Key | Action |
|-----|--------|
| Enter | Submit answer |
| Ctrl+N | New round |
| Ctrl+Q | Quit |

## Pure helpers

```python
from gullible import is_gullible_answer, Game

is_gullible_answer("maybe")  # True  — not a clean no
is_gullible_answer("no")     # False — escaped!

game = Game()
result = game.ask("yes")
# {"prompt": "...", "response": "yes", "verdict": "gullible", "message": "..."}
```

## Multilingual escape tokens

The "no" side accepts: no, nope, nah, non (French), nein (German),
nie (Polish/Czech), não (Portuguese), いいえ (Japanese), không (Vietnamese).
