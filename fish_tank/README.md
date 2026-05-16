# Fish Tank

An animated ASCII aquarium. Multiple fish swim left and right at varying
speeds, bubbles rise from the fish toward the surface, and seaweed sways
gently along the seafloor.

**Twist — Schooling behaviour:** fish nudge their direction toward the
nearest neighbour when within range, producing loose coordinated groups.

## Files

| File | Description |
|------|-------------|
| `fish_tank.py` | Core engine + CLI |
| `fish_tank_gui.py` | CustomTkinter GUI (dark deep-blue theme) |
| `fish_tank_tui.py` | Textual TUI (Tailwind palette) |

## Run

```bash
# CLI
uv run python fish_tank/fish_tank.py

# More fish, bigger tank
uv run python fish_tank/fish_tank.py --fish 8 --width 100 --height 28

# GUI
uv run python fish_tank/fish_tank_gui.py

# TUI
uv run python fish_tank/fish_tank_tui.py
```

## CLI Options

| Flag | Default | Description |
|------|---------|-------------|
| `--width` | 80 | Tank width in characters |
| `--height` | 24 | Tank height in rows |
| `--fish` | 5 | Number of fish |
| `--fps` | 8 | Frames per second |
| `--steps` | 0 | Stop after N frames (0 = forever) |
| `--seed` | — | RNG seed for reproducible runs |
| `--no-color` | off | Disable ANSI colour |

## TUI Bindings

| Key | Action |
|-----|--------|
| `space` | Play / Pause |
| `n` | Add a fish |
| `+` | Increase speed |
| `-` | Decrease speed |
| `Ctrl+Q` | Quit |

## How it works

### Fish (`Fish` dataclass)
Each fish stores a float position `(x, y)`, a velocity `dx` (positive =
rightward), and two ASCII art strings (right-facing / left-facing).  
`Fish.step()` advances `x += dx` and reflects `dx` when a wall would be
crossed.  
`Fish.apply_schooling()` checks all other fish and softly flips direction
(25% chance) toward the nearest neighbour if it is within 20 cells.

### Bubbles (`Bubble` dataclass)
A bubble is spawned near a random fish's mouth each frame (40% chance).
Each step it rises one row and wobbles ±1 column. It disappears when it
reaches row 0 (the surface).

### Plants (`Plant` dataclass)
Seaweed columns fixed to the bottom. `Plant.step()` cycles a sway offset
that maps each segment to `|`, `/`, or `\`.

### Tank
`Tank.step()` runs one simulation frame: schooling nudge → fish movement
→ bubble advance/removal → plant sway → optional new bubble.  
`Tank.render()` writes everything onto a character grid and returns the
joined string. The CLI passes `color=True` for ANSI output; the GUI and
TUI use the plain string and apply their own colour.

## Dependencies

Requires packages already in the shared `.venv`:

- `customtkinter` — GUI
- `textual` — TUI
