# Sine Message

Render a message as ASCII art that surfs a sine wave: each character of the message sits at a Y offset of `int(round(amplitude * sin(frequency * x + phase)))`. Advance the phase every frame and the wave scrolls horizontally.

Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (static + animated) | `sine_message.py` | stdlib (`math`, `time`) |
| Modern desktop GUI | `sine_message_gui.py` | CustomTkinter |
| Modern terminal UI | `sine_message_tui.py` | Textual |

## Run

```bash
# CLI - one static frame
uv run python sine_message/sine_message.py -m "Sine wave!" -w 80 -a 8 -f 0.2

# CLI - animated phase scroll (Ctrl+C to stop)
uv run python sine_message/sine_message.py --animate

# CLI - twist modes
uv run python sine_message/sine_message.py --mode overlay --animate
uv run python sine_message/sine_message.py --mode lissajous --animate

# Desktop GUI - sliders, color cycle, mode picker
uv run python sine_message/sine_message_gui.py

# Terminal UI - keyboard-driven
uv run python sine_message/sine_message_tui.py
```

## How it works

The math is one line — for each column `x` in `[0, width)`:

```python
y = int(round(amplitude * math.sin(frequency * x + phase)))
ch = message[x % len(message)]
grid[amplitude - y][x] = ch  # invert so +sin rises
```

Two ideas combined:

1. **Modulo cycle** — `message[x % len(message)]` repeats the message horizontally to fill `width` columns (same primitive as Bitmap Message and Vigenère).
2. **Discretized sine** — the continuous wave `amplitude · sin(frequency · x + phase)` is rounded to integer rows. Bigger `amplitude` → taller ribbon; bigger `frequency` → tighter wavelength; bigger `phase` step per frame → faster scroll.

The output canvas is `2 · amplitude + 1` rows tall: the wave can swing from `+amplitude` (top, sine = +1) down to `-amplitude` (bottom, sine = -1), with the centerline at row `amplitude`.

## Twists

The CLI ships with three renderers — pick with `--mode`:

- **`sine`** — the classic single wave.
- **`overlay`** — primary sine + 0.85·cosine + 0.5·second-harmonic sine, all sharing the same phase. Three semi-transparent ribbons crossing each other.
- **`lissajous`** — the column position itself wobbles via a slower cosine, so the message traces a 2-D Lissajous-style figure rather than a 1-D wave.

The GUI and TUI both expose all three modes plus an optional **rainbow color cycle** that paints each character on a hue gradient that rotates with the phase — the wave looks iridescent.

## What the GUI shows

A big monospace canvas at the bottom, message Entry up top, three sliders for **amplitude / frequency / scroll speed**, a mode dropdown (Sine / Overlay / Lissajous), a **color-cycle** toggle, and **Pause / Reset phase** buttons. Width auto-fits the canvas. ~20 fps animation loop driven by Tk's `after`.

## What the TUI shows

A single canvas pane with the message Input on top and live status at the bottom. Bindings:

- **Space** — pause / resume
- **+ / -** — amplitude up / down
- **] / [** — frequency up / down
- **> / <** — speed up / down
- **c** — toggle rainbow color cycle
- **m** — cycle render mode (sine → overlay → lissajous → …)
- **r** — reset phase to 0
- **Ctrl+Q** — quit

Status line shows the current mode, amp, freq, speed, phase, and running/paused state.

## Architecture

`sine_message.py` exposes:

- `render(message, width, amplitude, frequency, phase) -> str` — pure, no I/O. Imported by both UIs.
- `render_overlay(...)` — sine + cosine + harmonic stack.
- `render_lissajous(...)` — adds X-wobble for a 2-D figure.
- `main(argv=None)` — CLI entry-point with argparse, supports `--animate`.

The GUI and TUI both call into these `render*` functions every frame; they never reimplement the wave math.

## Verification

```bash
uv run python -c "import sys; sys.path.insert(0, 'sine_message'); import sine_message; out = sine_message.render('hello', 60, 5, 0.3, 0.0); assert 'h' in out and 'o' in out; print('OK')"
```

Should print `OK`.
