# Mondrian Art Generator

Generate Piet-Mondrian-style abstract paintings: a canvas is recursively split along random horizontal/vertical lines, with each leaf rectangle painted in a weighted-random primary color and outlined in black.

Inspired by Al Sweigart's *Mondrian Art Generator* project from *The Big Book of Small Python Projects*. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `mondrian.py` | Pillow |
| Modern desktop GUI | `mondrian_gui.py` | CustomTkinter + tk.Canvas + Pillow |
| Modern terminal UI | `mondrian_tui.py` | Textual + Rich half-block render |

## Run

```bash
# CLI - render to PNG with chosen size, depth, seed, and style
uv run python mondrian/mondrian.py --width 1200 --height 900 --depth 5 --seed 42

# Desktop GUI - interactive sliders, live tk.Canvas preview, Save PNG
uv run python mondrian/mondrian_gui.py

# Terminal UI - half-block rendering inside the terminal
uv run python mondrian/mondrian_tui.py
```

## How it works

The core is a recursive subdivision over a `Rect`:

```python
def _subdivide(rect, rng, depth, palette, horizontal_only, max_dim):
    if depth <= 0 or too_small(rect):
        return [Rect(..., color=weighted_choice(rng, palette))]
    if rng.random() > split_probability(rect):
        return [Rect(..., color=weighted_choice(rng, palette))]
    axis = pick_axis(rect, horizontal_only, rng)
    a, b = split(rect, axis, ratio=rng.uniform(0.3, 0.7))
    return _subdivide(a, ...) + _subdivide(b, ...)
```

Three knobs shape the composition:

1. **Split probability scales with size.** Bigger rectangles are likelier to split (`size_factor = max(w, h) / max_dim`, clamped to `[0.15, 0.95]`). This avoids endless splitting of tiny boxes and gives the canvas room to breathe.
2. **Axis bias toward the longer side.** Long thin rectangles split along their long axis 1.4:1 of the time, so you don't get pencil-thin slices crossed with pencil-thin slices.
3. **Weighted color choice.** White is weighted 3x in the Mondrian palette so it dominates as background; primaries appear as accents.

## Style presets

| Preset | Behavior | Palette |
|---|---|---|
| `mondrian` | Both axes, classic De Stijl | red / yellow / blue + 3x white |
| `rothko` | Horizontal-only splits, no vertical lines | crimson, orange, ochre, plum, cream |
| `bauhaus` | Both axes with extended primaries | red / yellow / blue / black / white |

## What the GUI shows

A two-pane layout. **Left:** controls — style preset dropdown, depth slider (2-8), width / height sliders, seed entry, **Generate**, **Re-render (same seed)**, and **Save PNG**. **Right:** a `tk.Canvas` rendering the current painting at native resolution. Tweaking any slider updates the labels live; pressing **Generate** rolls a new seed (or reuses the one you typed). **Save PNG** opens a file dialog and writes the painting via Pillow at canvas resolution.

## What the TUI shows

A single full-pane painting rendered using **upper-half-block characters** (U+2580 `▀`). Each character cell encodes two stacked pixels — foreground = top, background = bottom — doubling vertical resolution. Keys:

- **g** — generate a new painting (random seed)
- **r** — re-render with same seed (useful after changing depth or style)
- **p** — cycle style preset
- **+ / -** — increase / decrease recursion depth (clamped 2..8)
- **s** — save current painting as PNG in the working directory
- **Ctrl+Q** — quit

## Architecture

`mondrian.py` exposes:

- `Rect(x, y, w, h, color)` — frozen dataclass; `bbox()` returns `(x0, y0, x1, y1)` for Pillow / Tk.
- `generate(width, height, rng=None, depth=4, style='mondrian') -> list[Rect]` — pure recursive subdivision. Imported by both UIs.
- `render_image(rects, width, height) -> PIL.Image` — Pillow rasterizer with black borders.
- `PALETTES` — dict mapping style key → list of `(name, rgb, weight)` tuples.
- `main()` — CLI entry point with argparse.

The GUI uses `tk.Canvas.create_rectangle` for live drawing (no Pillow needed for the preview), but calls `render_image` when saving so the saved PNG is a clean rasterization rather than a screenshot.

The TUI rasterizes the rects into a pixel grid sized to the terminal pane, then collapses runs of equally-colored pixel pairs into single Rich `Text` segments — keeps the redraw cheap even at 200+ columns.
