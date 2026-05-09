# Seven-Segment Display

Render any number or text as classic seven-segment LCD-style ASCII art.

A focused **rendering library** — distinct from the `countdown/` project, which uses similar art for the *timer* use-case. This one is the generic, reusable showcase: pass any string, get back 3-line ASCII digits and calculator-style letters.

| Version | File | Stack |
|---------|------|-------|
| CLI / library | `seven_segment.py` | stdlib |
| Modern desktop GUI | `seven_segment_gui.py` | CustomTkinter |
| Modern terminal UI | `seven_segment_tui.py` | Textual |

## Run

```bash
# CLI — print rendered text and exit
uv run python seven_segment/seven_segment.py 12345
uv run python seven_segment/seven_segment.py "PI = 3.14"
uv run python seven_segment/seven_segment.py --warmup HELLO

# Desktop GUI — live editor, color picker, font slider, LCD/LED presets
uv run python seven_segment/seven_segment_gui.py

# Terminal UI — live editor, c to cycle colors, Ctrl+Q to quit
uv run python seven_segment/seven_segment_tui.py
```

## Library API

```python
from seven_segment import render, digit_art, available_chars, warmup_frames

render('3.14')          # -> 3-line "\n"-joined string
digit_art('A')          # -> ['  _ ', '|_|', '| |']  (always 3 lines)
available_chars()       # -> every char render() draws faithfully
warmup_frames('42', 6)  # -> 6 progressive frames lighting up
```

Every glyph is exactly 3 lines tall and a fixed width per character, so concatenating multiple chars stays aligned.

## Supported characters

```
0 1 2 3 4 5 6 7 8 9
+ - . : (space)
A B C D E F G H I J L N O P R S T U Y
```

Plus best-effort fallbacks for K, M, Q, V, W, X, Z (mapped to their nearest 7-segment neighbor — Z to 2, X to H, W and V to U, etc.). Unknown characters render as a blank cell of the same width so layout stays stable.

The letter subset is the **calculator-display convention**: most real seven-segment LCDs only render this subset, because letters like K, M, W don't have a faithful 7-bar form. We honor that limit instead of inventing fake glyphs.

## What the GUI shows

A dark-themed CustomTkinter window with:

- **Text input** — type anything, the display re-renders on every keystroke.
- **Preset menu** — *LCD green*, *LED red*, *LED amber*, *Cyan*, *Magenta*. Each preset sets both segment color and panel background.
- **Pick color…** — opens the system color picker for a custom segment color.
- **Size slider** — 10pt to 40pt monospace, live-resizing.

The display lives inside a rounded panel that adapts its background to match the chosen preset, mimicking a real LCD bezel.

## What the TUI shows

A dark Tailwind-themed Textual app with the same input + preview model.

- **c** — cycle through the same five color presets.
- **Ctrl+Q** — quit.

The display panel uses Textual's CSS to color the segment text and the panel background independently, just like the GUI.

## Twist: animated warm-up

The `--warmup` CLI flag (and the `warmup_frames()` library function) emit a sequence of frames where segments "light up" gradually. The reveal order roughly mimics a real LCD warming up: top/bottom bars first (`_`), then verticals (`|`), then dots and pluses. With `--steps 6` (the default) you see six progressive frames before the full display.

```bash
uv run python seven_segment/seven_segment.py --warmup --steps 12 8888
```

This is implemented as a pure library function returning a list of strings — the CLI just prints them in place with a small delay. No animation framework dependency.

## Architecture

`seven_segment.py` exposes:

- `digit_art(s) -> list[str]` — one char → 3-line glyph.
- `render(s) -> str` — full string → 3-line "\\n"-joined display.
- `available_chars() -> str` — sorted string of every glyph key.
- `warmup_frames(text, steps) -> list[str]` — animation frames.
- `main()` — argparse CLI with `--warmup`, `--steps`, `--list`.

The GUI and TUI both `from seven_segment import render` and call it on every keystroke. They never duplicate the rendering logic — the library is the single source of truth.

## Why a separate project from `countdown`?

`countdown/countdown.py` has its own internal seven-segment digit dict, but it's narrow on purpose: only `0-9` and `:`, because that's all an `MM:SS` timer needs. This project is the **library generalization**: full digits + symbols + the calculator-letter alphabet, with a clean import surface, a warm-up animation, and standalone GUI/TUI showcases. Same visual language, different scope.
