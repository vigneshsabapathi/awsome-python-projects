# Diamonds

ASCII-art diamond pattern generator. Build outlined or solid-filled diamonds at
any size, or render a row of diamonds in increasing size — useful for banners,
greeting cards, and the occasional hourglass-with-extra-steps.

Inspired by Al Sweigart's *Diamonds* from *The Big Book of Small Python
Projects*. Implemented from scratch.

## Run

```bash
# CLI
uv run python diamonds/diamonds.py                    # demo
uv run python diamonds/diamonds.py 6 outlined         # one outlined diamond
uv run python diamonds/diamonds.py 6 filled           # one solid diamond
uv run python diamonds/diamonds.py row 1 2 3 4 5      # row of diamonds
uv run python diamonds/diamonds.py row filled 2 4 6   # row, filled style

# Desktop GUI (CustomTkinter, dark theme)
uv run python diamonds/diamonds_gui.py

# Terminal UI (Textual, dark Tailwind palette)
uv run python diamonds/diamonds_tui.py
```

## Architecture

```
diamonds/
├── diamonds.py          pure functions + CLI entrypoint
├── diamonds_gui.py      CustomTkinter GUI — slider, toggle, preview, copy
├── diamonds_tui.py      Textual TUI — input box, live preview, key bindings
└── README.md
```

`diamonds.py` exposes three pure functions; both UIs import them and never
duplicate render logic:

| Function                                   | Returns                                   |
|--------------------------------------------|-------------------------------------------|
| `outlined(size: int) -> str`               | hollow diamond, `2*size` rows tall        |
| `filled(size: int) -> str`                 | solid diamond, same dimensions            |
| `row_of_diamonds(sizes, style, gap)`       | several diamonds in one row, baselines aligned |

## How a diamond is built

The top half is generated row by row: `(size - row - 1)` leading spaces, a `/`,
`row * 2` interior spaces (or filling slashes for the filled variant), and a
closing `\`. The bottom half is the mirror image: `row` leading spaces, a `\`,
shrinking interior, and a closing `/`. Total height is `2 * size`.

## Creative twist

Both UIs include a **Grow** animation that loops the diamond from size 1 up to
the slider/input value at 4 fps — handy for live demos and a fun visual
heartbeat. In the GUI press the purple **Grow** button; in the TUI press
**Ctrl+G**.

## Key bindings (TUI)

| Key      | Action                       |
|----------|------------------------------|
| Ctrl+T   | Toggle Outlined / Filled     |
| Ctrl+G   | Start / stop grow animation  |
| Ctrl+Q   | Quit                         |
