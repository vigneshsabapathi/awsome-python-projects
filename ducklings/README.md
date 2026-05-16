# Ducklings

Animated row of ASCII ducks waddling across the screen with bobbing motion.
A mother mallard leads and her ducklings follow in a lag chain — each one
trails the position of the duck ahead of it, creating a natural follow-the-
leader formation.

Three species with distinct ASCII art:
- **Mallard** — classic large duck (always the mother)
- **Regular** — rubber-duck style
- **Mandarin** — fancy crest

## Files

| File | Description |
|------|-------------|
| `ducklings.py` | Core engine + CLI |
| `ducklings_gui.py` | CustomTkinter GUI with sliders and colour picker |
| `ducklings_tui.py` | Textual TUI with keyboard controls |

## How to Run

```bash
# CLI
uv run python ducklings/ducklings.py
uv run python ducklings/ducklings.py --ducks 6 --fps 8 --width 100

# GUI (CustomTkinter)
uv run python ducklings/ducklings_gui.py

# TUI (Textual)
uv run python ducklings/ducklings_tui.py
```

## Controls (TUI)

| Key | Action |
|-----|--------|
| Space | Play / Pause |
| + | Increase speed |
| - | Decrease speed |
| n | Add a duck (max 10) |
| Ctrl+Q | Quit |

## Design

`Duck(x, frame, bob, species)` — pure dataclass, no I/O.

`Pond(width, num_ducks, rng)` — manages duck positions and calls `step()` /
`render()`. The mother duck wraps around the screen; each duckling reads the
*previous* duck's position history at `LAG_STEPS` frames back, producing the
waddling follow-the-leader tail.

Bob animation is implemented by prepending a blank line to the sprite art
on every third frame, making each duck bob up and down independently.
