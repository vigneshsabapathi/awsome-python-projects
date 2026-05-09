# Etching Drawer

An Etch-A-Sketch-style drawing tool. Move a cursor around with the arrow keys to draw a continuous line on a 2D canvas. Shake to erase. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `etching.py` | stdlib (`msvcrt` on Windows, `termios` fallback elsewhere) |
| Desktop GUI | `etching_gui.py` | CustomTkinter + Pillow (PNG export) |
| Terminal UI | `etching_tui.py` | Textual |

## Run

```bash
# CLI
uv run python etching/etching.py

# Desktop GUI (CustomTkinter)
uv run python etching/etching_gui.py

# Terminal UI (Textual)
uv run python etching/etching_tui.py
```

## Controls

| Key | Action |
|-----|--------|
| Arrow keys | Move pen N/S/E/W (drawing) |
| W / E / Z / X | Diagonal moves NW / NE / SW / SE (CLI/TUI). In the GUI, hold two arrows together. |
| Space | Toggle pen up / down |
| C | Cycle brush colour through the palette |
| S | Shake (clear the canvas) |
| P | Playback — replay the drawing stroke-by-stroke |
| Q (CLI) / Ctrl+Q (TUI) | Quit |

The GUI also has buttons for **Clear**, **Cycle colour**, **Pick colour…** (full colour wheel), **Playback**, and **Save PNG…**.

## Twists

- **Multi-colour brush** — `C` cycles through a six-colour palette so a single canvas can hold multiple stroke styles. The GUI also has a free colour-wheel picker.
- **8-directional movement** — diagonals draw single-cell strokes (so pressing Up + Right in the GUI, or `e` in the CLI/TUI, etches a 45° line).
- **Playback** — every stroke is recorded; press `P` to replay the drawing one cell at a time. Useful for bragging.

## Architecture

The CLI module (`etching.py`) holds the shared logic. Both GUIs import:

- `Canvas(width, height, brush)` — the 2-D char grid with a movable pen
  - `move(direction)` — clamped 8-directional move; appends to history
  - `clear()` — shake; wipes grid + history
  - `cycle_brush()` — advances the brush to the next palette character
  - `toggle_pen()` — pen up / pen down
  - `render(show_cursor=True)` — return a newline-joined string snapshot
  - `replay_frames()` — list of render snapshots, one per stroke (for animation)
- `PALETTE`, `DIRECTIONS`, `DEFAULT_WIDTH`, `DEFAULT_HEIGHT` — constants
- `read_key()` — single-key reader (`msvcrt.getwch()` on Windows; `termios` raw-mode + ANSI escape parsing elsewhere)

## Notes

- The character canvas is the *logical* model. The GUI scales each cell to a 14-pixel block when rendering to the Tk Canvas, and uses the same geometry to write the PNG with PIL — so what you see is what you save.
- Out-of-bounds moves clip to the edge; they don't wrap. This matches a real Etch-A-Sketch (you can't drive the cursor off the screen).
- The cursor blinks in the GUI (`tk.Canvas.create_oval` toggled every 400 ms) so it stays visible against drawn strokes.
- `replay_frames()` builds a fresh ghost canvas to avoid mutating the live grid mid-render, which keeps playback decoupled from the live drawing state.
