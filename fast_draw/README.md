# Fast Draw

A quick-reaction game: wait for the signal, then respond as fast as possible.

The screen shows **WAIT** for a random 1–5 seconds. The instant it switches to
**DRAW!**, press a key (or click). Your reaction time is measured in
milliseconds. Pressing too early counts as a **false start**.

**Twist:** Stats are tracked over many rounds — mean, std-dev, personal best,
and false-start rate — so you can benchmark and improve your reflexes.

## Files

| File | Description |
|------|-------------|
| `fast_draw.py` | Core `Game` class + CLI |
| `fast_draw_gui.py` | CustomTkinter desktop GUI |
| `fast_draw_tui.py` | Textual terminal UI |

## How to run

```bash
# CLI
uv run python fast_draw/fast_draw.py

# GUI (CustomTkinter)
uv run python fast_draw/fast_draw_gui.py

# TUI (Textual)
uv run python fast_draw/fast_draw_tui.py
```

## Controls

| Interface | Action | Key / Input |
|-----------|--------|-------------|
| CLI | React | Any key |
| GUI | React | Click window or Space |
| TUI | React | Space |
| TUI | New round | N |
| TUI | Quit | Ctrl+Q |

## Stats tracked

- **Last** — reaction time of the most recent valid round
- **Best** — fastest reaction time ever
- **Avg 10** — rolling average of the last 10 valid rounds
- **False starts** — count of early-press penalties

## `Game` API

```python
from fast_draw import Game

g = Game()
wait_secs = g.start_round()   # returns float in [1, 5]
g.draw_now()                  # call when DRAW signal fires
result = g.react(elapsed_ms)  # returns stats dict
```
