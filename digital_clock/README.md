# Digital Clock

Real-time clock displayed as ASCII seven-segment digits, updating every second.

## What it does

Renders the current time as large three-line ASCII art using hand-crafted
seven-segment digit shapes. Three interfaces are provided: a CLI, a CustomTkinter
GUI, and a Textual TUI.

**Twist:** World-clock mode shows multiple timezones side-by-side (`--world`),
and 12-hour mode displays a ☀/🌙 AM/PM indicator.

## Files

| File | Description |
|------|-------------|
| `digital_clock.py` | CLI + pure library (`format_time`, `render_clock`) |
| `digital_clock_gui.py` | CustomTkinter dark GUI |
| `digital_clock_tui.py` | Textual TUI |

## How to run

### CLI

```bash
# 24-hour clock (default)
uv run python digital_clock/digital_clock.py

# 12-hour format with ☀/🌙 AM/PM indicator
uv run python digital_clock/digital_clock.py --12h

# World-clock mode (multiple timezones)
uv run python digital_clock/digital_clock.py --world
uv run python digital_clock/digital_clock.py --world --12h
```

### GUI (CustomTkinter)

```bash
uv run python digital_clock/digital_clock_gui.py
```

Features: 12/24h toggle, seconds toggle, date label, color picker (LCD green /
LED red / Amber).

### TUI (Textual)

```bash
uv run python digital_clock/digital_clock_tui.py
```

Bindings:

| Key | Action |
|-----|--------|
| `c` | Cycle color (LCD Green → LED Red → Amber → Sky Blue) |
| `t` | Toggle 12/24-hour |
| `d` | Toggle date display |
| `s` | Toggle seconds |
| `Ctrl+Q` | Quit |

## Example output

```
Wednesday, 15 May 2024
 ___   ___       ___   ___       ___   ___
|   |    | .    |   |  ___  .      | |___|
|___|    |     .|___|  ___|      . |  ___|
```

## Dependencies

Uses the shared `.venv/` at the repo root. See `requirements.txt` for the full
list. Key packages: `customtkinter`, `textual`, `tzdata` (for world-clock mode
on Windows/older systems).
