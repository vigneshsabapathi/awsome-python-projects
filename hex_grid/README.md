# Hex Grid

Generate hexagonal honeycomb-pattern ASCII grids of arbitrary width and height. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `hex_grid.py` | stdlib |
| Modern desktop GUI | `hex_grid_gui.py` | CustomTkinter |
| Modern terminal UI | `hex_grid_tui.py` | Textual |

## Run

```bash
# CLI - default 3 x 5 grid
uv run python hex_grid/hex_grid.py

# Custom rows + cols
uv run python hex_grid/hex_grid.py 4 6

# Coordinate overlay (axial / cube / offset)
uv run python hex_grid/hex_grid.py 4 6 axial

# Vector export — drops hex.svg next to your CWD
uv run python hex_grid/hex_grid.py 4 6 axial svg my_hex.svg

# GUI with sliders, overlay toggle, copy + SVG export
uv run python hex_grid/hex_grid_gui.py

# TUI with live preview and Ctrl+O to cycle overlays
uv run python hex_grid/hex_grid_tui.py
```

## What it draws

```
 _____       _____
/     \_____/     \_____
\_____/     \_____/     \
/     \_____/     \_____/
\_____/     \_____/     \
```

Each hex cell is 7 characters wide and 4 rows tall. Adjacent columns share their slanted edges, and every odd column sits exactly one character row lower than its even neighbour — that's the offset that makes the whole thing tile cleanly.

## How it works

The render walks a 2-D character grid and stamps three pieces per hex:

```python
# top: ' _____ '   mid: '/     \\'   bot: '\\_____/'
top_line = 2 * r if c % 2 == 0 else 2 * r + 1   # even cols start higher
mid_line = top_line + 1
bot_line = top_line + 2
```

Because adjacent hexes share corners, the `\` of one column is exactly the `\` of its neighbour — stamping is idempotent and the shared characters all agree without any special-casing.

## The twist — coordinate overlays + SVG

Every cell can be labelled with its position in any of the three standard hex coordinate systems used by game devs and graph algorithms:

| System | Example label | What it represents |
|--------|---------------|--------------------|
| `offset` | `0,3`     | row, col (the literal grid index) |
| `axial`  | `3,-1`    | (q, r) — two-axis hex coords |
| `cube`   | `3-1-2`   | (x, y, z) with `x + y + z = 0` |

```python
from hex_grid import coordinate_overlay, render
labels = coordinate_overlay(4, 6, 'axial')
print(render(4, 6, labels))
```

The same `labels` dict can be passed to `to_svg(rows, cols, labels)` to get a crisp **vector** version of the grid as a standalone SVG document — flat-top hexes drawn from real polygons, ready to drop into a slide deck or web page.

## What the GUI shows

Two sliders (rows / cols, both 1..20), a four-state segmented button for the coordinate overlay (Plain / Axial / Cube / Offset), a monospace preview pane, and **Copy** + **Export SVG…** buttons. Every slider tick re-renders the preview live.

## What the TUI shows

Two `Input` widgets at the top (rows + cols, 1..20), a live preview, and a `Ctrl+O` binding that cycles the coordinate overlay. `Ctrl+Q` quits. Every keystroke re-renders.

## Architecture

`hex_grid.py` exposes:

- `render(rows, cols, labels=None) -> str` — pure function, no I/O. Imported by both UIs.
- `coordinate_overlay(rows, cols, system) -> dict` — build the label dict for `axial`, `cube`, or `offset` coordinates.
- `to_svg(rows, cols, labels=None, **style) -> str` — same grid as a standalone SVG document.
- `main()` — the CLI entry point.

The GUI and TUI both call `render()` on every keystroke; they don't reinvent the rendering logic.
