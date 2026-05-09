# Shining Carpet

Animated tessellated carpet pattern, inspired by the iconic hexagonal carpet from the Overlook Hotel hallway in *The Shining*. A small repeating ASCII tile is stamped across the canvas, then the colour palette is rotated through the tile glyphs to make the whole carpet shimmer.

Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI animation | `shining_carpet.py` | stdlib + ANSI truecolour |
| Modern desktop GUI | `shining_carpet_gui.py` | CustomTkinter + tk.Canvas |
| Modern terminal UI | `shining_carpet_tui.py` | Textual + Rich color spans |

## Run

```bash
# CLI - animates in the terminal until Ctrl+C
uv run python shining_carpet/shining_carpet.py

# CLI knobs
uv run python shining_carpet/shining_carpet.py --palette persian --fps 12 --width 80 --height 24
uv run python shining_carpet/shining_carpet.py --no-color --frames 1   # one-shot ASCII

# Desktop GUI - tk.Canvas, palette dropdown, pause, click-to-stamp
uv run python shining_carpet/shining_carpet_gui.py

# Terminal UI - Textual, fills the terminal, space/p/Ctrl+Q
uv run python shining_carpet/shining_carpet_tui.py
```

## How it works

Two ideas, both leaning on `%`:

1. **Geometric tessellation** — a small tile (`8×4` for *shining* and *persian*, `12×6` for *bauhaus*) is repeated across the canvas with `tile[r % tile_h][c % tile_w]`. Same modulo trick as `bitmap_message`'s message cycling, but in 2-D.
2. **Colour phase shift** — every non-space glyph in the tile maps to a *palette slot* (its position in the 8-character `PALETTE_GLYPHS` string). To animate, we add a per-frame `offset` to the slot before looking up the colour: `palette[(slot + offset) % len(palette)]`. The geometry is static; only the colour-to-glyph mapping rotates.

That separation — geometry in `render()`, colour in the palette dictionary — is what lets all three UIs share the exact same render path.

## What the GUI shows

A `tk.Canvas` filled edge-to-edge with the tessellated tile. Each non-space glyph becomes a coloured rectangle. Controls:

- **Palette** dropdown — *shining* (Overlook orange/cream), *persian* (indigo + crimson + gold), *bauhaus* (Mondrian-style primaries). Picking a palette also picks its tile geometry.
- **Auto-cycle** checkbox — drift through all three palettes every ~3 seconds.
- **Pause / Resume** button — freeze the animation.
- **Click any cell** — stamps an extra half-cycle phase shift on that single cell, painting an accent over the carpet. Click again to remove. *Clear stamps* wipes all of them.

Resize the window and the grid recomputes — bigger window, more tiles.

## What the TUI shows

A full-screen Textual app that fills the terminal with the carpet, rendered via Rich color spans. Bindings:

- **space** — pause / resume
- **p** — cycle palette
- **Ctrl+Q** — quit

The carpet redraws on every animation tick at 8 FPS.

## Architecture

`shining_carpet.py` exposes:

- `tile(palette) -> list[str]` — pure. Returns the small repeating tile for the named palette (8×4 or 12×6 strings).
- `render(width, height, tile, offset=0, palette=None) -> str` — pure. Tiles a `width×height` canvas with `tile`, applying `offset` as a phase shift on the glyph slots. Returns plain text.
- `render_ansi(width, height, tile, offset, palette)` — same geometry plus ANSI 24-bit truecolour spans (used by the CLI).
- `glyph_to_slot(ch) -> int` — maps a tile glyph to its palette slot index (used by both UIs to colour each cell).
- `PALETTES` — dict of three named palettes (lists of 8 hex colours each).
- `TILES` — dict of three named tile patterns (`shining` hexagons, `persian` medallion, `penrose` quasi-periodic weave used by *bauhaus*).
- `main()` — the CLI animation loop with argparse knobs.

The GUI and TUI both call `render()` once per frame with a monotonically increasing `offset`, then walk the result and look up colours by glyph slot. Neither reinvents the rendering logic.

## Tile patterns

```
shining (8×4 hex weave)         persian (8×4 medallion)        bauhaus / penrose (12×6 weave)
##  ##                          +: :+: :                        #  *  =  +
#%##%%##                        : @ : @                          #  *  =  +
%%@@%%@@                        +: :+: :                        *  =  +  #
 %@@ %@@                        : @ : @                          *  =  +  #
                                                                =  +  #  *
                                                                 =  +  #  *
```

The `PALETTE_GLYPHS` string `"#%@*+=:."` has 8 characters — one per palette slot. The dense glyphs (`#`, `%`) sit on dark colours; sparser glyphs (`:`, `.`) sit on lighter accents. As `offset` increments, a `#` cell walks through `% → @ → * → + → = → : → . → #` in palette space, giving the shimmer.
