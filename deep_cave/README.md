# Deep Cave

A procedurally-generated infinite-scroll cave. Each row is drawn ASCII-style with a randomly-shifting tunnel of walkable space, producing a continuous descent past stalactites and stalagmites. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (animated) | `deep_cave.py` | stdlib |
| Modern desktop GUI | `deep_cave_gui.py` | CustomTkinter + tk Canvas |
| Modern terminal UI | `deep_cave_tui.py` | Textual + Rich |

## How it works

The cave is generated one row at a time by a constrained random walk:

- The tunnel's **left edge** can shift `-1`, `0`, or `+1` per row.
- The tunnel's **width** can grow or shrink by `±1` per row.
- Both quantities are clamped so the tunnel always sits inside the canvas with at least one wall column on each side, and the floor is always wide enough to walk through.

Because each row only depends on the previous row, the geometry stays smooth — you never get a jagged jump from one row to the next.

```
####################                    ##############################
####################                    ##############################
###################                     ##############################
###################                      #############################
####################                     #############################
###################                      #############################
###################                       ############################
```

### Twist: hazards & treasures

At low probability per row a single floor cell is replaced with a hazard or treasure character:

| Char | Meaning | Probability per row |
|------|---------|--------------------|
| `*`  | a glittering gem | 2.0% |
| `~`  | a trickle of water | 3.0% |
| `o`  | a fallen boulder | 2.5% |

The first time each is sighted the CLI prints a one-line hint (`... you spot a glittering gem at depth 412.`); the GUI flashes the same message in amber under the canvas; the TUI highlights it in the hint panel above the stats line.

## Run

```bash
# CLI — runs forever, Ctrl+C to surface
uv run python deep_cave/deep_cave.py
uv run python deep_cave/deep_cave.py --width 80 --fps 24 --seed 42

# Desktop GUI (CustomTkinter)
uv run python deep_cave/deep_cave_gui.py

# Terminal UI (Textual)
uv run python deep_cave/deep_cave_tui.py
```

## Controls

**CLI**
- `--width N` — total row width (default 70)
- `--fps F` — rows per second (default 30)
- `--seed N` — reproducible cave from a seed
- `Ctrl+C` — surface (prints final depth)

**GUI**
- Space — play/pause
- Speed slider — 5..120 fps
- Seed entry + Apply — reproducible caves
- Reseed — fresh random cave

**TUI**
- Space — play/pause
- `+` / `-` — faster/slower
- `r` — reseed (new random cave)
- `Ctrl+Q` — quit

## Architecture

The CLI module (`deep_cave.py`) is the single source of truth. Both GUIs import:

- `next_row(prev_left, prev_width, rng, total_width=70)` — pure function returning `(new_left, new_width, ascii_row)`. Deterministic for a given `random.Random` state.
- `initial_tunnel(total_width)` — pick a sensible starting `(left, width)` centered in the canvas.
- `hazard_label(char)` — human-readable label lookup for the twist characters.
- `HAZARDS`, `WALL`, `FLOOR`, `DEFAULT_WIDTH` — shared constants.

This keeps the simulation core small and unit-testable: `next_row` takes simple ints and an RNG, returns simple ints and a string.

## Notes

- **Why pass `random.Random` instead of using `random.random()` directly?** The pure function takes an RNG instance so callers can isolate the cave's stream from the rest of the program — the GUI seed entry, for example, builds a private `random.Random(seed)` so re-applying the same seed always reproduces the same cave.
- **Width vs left independence.** Both drift independently, but each row only changes by one step in either dimension — slower than the eye scrolls, so the cave reads as continuous rather than chaotic.
- **Render strategy.** The CLI is plain `sys.stdout.write` in a sleep loop. The GUI pre-creates one canvas rectangle per cell at startup and only `itemconfigure(fill=...)` per tick — repainting all rows each frame is cheap (~36×70 cells) and keeps the scroll consistent. The TUI uses Rich `Text` with style runs so wall edges, wall interior, and floor each get distinct colors without spamming markup.
