# Lucky Stars

A fortune-telling toy. Roll three stars from the night sky; the
dominant theme (love, work, money, health, fortune) selects a fortune
message. Three front-ends share one pure core in `lucky_stars.py`:

- `lucky_stars.py` - CLI with a rolling-stars spinner.
- `lucky_stars_gui.py` - CustomTkinter dark theme with an animated
  twinkling starfield background and a styled fortune card.
- `lucky_stars_tui.py` - Textual TUI with an animated star roll.

## Run

```bash
# CLI - one reading
uv run python lucky_stars/lucky_stars.py

# Reproducible / shareable
uv run python lucky_stars/lucky_stars.py --seed 7

# Compatibility check between two seeded readings
uv run python lucky_stars/lucky_stars.py --compat 7 42

# Save a reading to ~/.lucky_stars_history.json
uv run python lucky_stars/lucky_stars.py --save

# Print history
uv run python lucky_stars/lucky_stars.py --history

# GUI
uv run python lucky_stars/lucky_stars_gui.py

# TUI
uv run python lucky_stars/lucky_stars_tui.py
```

## TUI bindings

| Key      | Action            |
|----------|-------------------|
| `space`  | Roll the stars    |
| `s`      | Save reading      |
| `Ctrl+Q` | Quit              |

## How it works

`read_fortune(rng=None) -> {stars, symbols, theme, message}` is the
pure core. It draws three stars from `STARS` with replacement, picks
the dominant theme by `Counter` majority (ties broken by the order in
`THEMES`), then samples one fortune from that theme's bank.

Twenty fortunes are authored from scratch (four per theme) and ten
star symbols cover all five themes. Every randomized call accepts a
`random.Random` so seeds make readings shareable and reproducible.

## Twists

- **Save history** - readings get appended (with timestamps and seed)
  to `~/.lucky_stars_history.json`. CLI, GUI, and TUI all share this
  file.
- **Compatibility check** - `--compat SEED_A SEED_B` rolls both
  readings, compares their themes, and emits a 0-100 score with a
  verdict ("celestial twins", "aligned constellations", "crossing
  orbits", "distant skies").
- **Seedable readings** - `--seed N` makes readings reproducible so
  you can share "seed 1138" with a friend and they see the same
  fortune.
