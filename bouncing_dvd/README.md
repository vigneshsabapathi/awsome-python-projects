# Bouncing DVD Logo

The classic 90s screensaver: a "DVD" logo bounces around the screen, flips its color on every wall hit, and very occasionally smashes exactly into a corner — the rare event that delights anyone watching. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `bouncing_dvd.py` | stdlib |
| Modern desktop GUI | `bouncing_dvd_gui.py` | CustomTkinter |
| Modern terminal UI | `bouncing_dvd_tui.py` | Textual |

## Run

```bash
# CLI
uv run python bouncing_dvd/bouncing_dvd.py

# CLI with multiple logos
uv run python bouncing_dvd/bouncing_dvd.py --logos 3 --width 100 --height 32

# Monte Carlo corner-hit probability estimate
uv run python bouncing_dvd/bouncing_dvd.py --probability 50000

# Desktop GUI (CustomTkinter)
uv run python bouncing_dvd/bouncing_dvd_gui.py

# Terminal UI (Textual)
uv run python bouncing_dvd/bouncing_dvd_tui.py
```

## Controls

### GUI
| Control | Action |
|---------|--------|
| **Space** | Play / Pause |
| Logos slider | 1–8 simultaneous logos |
| Speed slider | 1–60 fps |

### TUI
| Key | Action |
|-----|--------|
| **Space** | Play / Pause |
| **+** / **-** | Speed up / slow down |
| **n** | Add a new logo |
| **Ctrl+Q** | Quit |

## Architecture

The CLI module (`bouncing_dvd.py`) holds the shared physics. Both GUIs import:

- `Logo` — dataclass with `step(width, height, logo_w, logo_h) -> bool` (returns `True` on corner hit)
- `random_logo(width, height, logo_w, logo_h, rng)` — spawns a logo at a random interior position
- `COLORS` — tuple of 8 color name strings cycled on every wall hit
- `render(...)` — CLI ANSI renderer (used only by the CLI)

## Twist

The CLI `--probability` flag runs a Monte Carlo simulation and compares the empirical corner-hit rate against the theoretical value `1 / lcm(width − logo_w, height − logo_h)`. For a standard 78×22 field the probability is roughly 1 in 1,000 steps.

## Notes

- Physics operates in integer units — no floating-point drift.
- Color cycles on **every** wall hit (single-axis or corner), so the logo never stays the same color for long.
- A corner hit (both axes reflect on the same step) increments `corners` and is returned as `True` from `step()`.
