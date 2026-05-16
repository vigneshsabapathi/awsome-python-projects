# Digital Stream

Matrix-style falling green digital rain. Each column has one or more "raindrops" — a bright head glyph followed by a fading tail — all scrolling down at randomised speeds.

## Files

| File | Interface | Run |
|---|---|---|
| `digital_stream.py` | CLI (ANSI terminal) | `uv run python digital_stream/digital_stream.py` |
| `digital_stream_gui.py` | CustomTkinter desktop | `uv run python digital_stream/digital_stream_gui.py` |
| `digital_stream_tui.py` | Textual TUI | `uv run python digital_stream/digital_stream_tui.py` |

## CLI options

```
uv run python digital_stream/digital_stream.py --help

  --fps FPS           Frames per second (default: 15)
  --density DENSITY   Drop spawn probability per column per frame (default: 0.03)
  --charset {katakana,digits,latin}
```

## Character sets

| Name | Characters | Notes |
|---|---|---|
| `katakana` | Half-width katakana (ｦ…ﾝ) | Most authentic Matrix look |
| `digits` | 0–9 | Clean numeric rain |
| `latin` | A–Z / a–z | Latin alphabet variant |

## GUI controls

- **Speed slider** — FPS (1–60)
- **Density slider** — new-drop spawn rate
- **Charset button** — cycles Katakana → Digits → Latin

## TUI bindings

| Key | Action |
|---|---|
| Space | Pause / resume |
| `+` / `-` | Faster / slower |
| `c` | Cycle character set |
| Ctrl+Q | Quit |

## How it works

A `Rain` object holds a list of `Drop` dataclasses. Each `Drop` tracks its column, head Y position (float for sub-cell speed), tail length, and current glyph characters. Every `step()` call:

1. Advances each drop's `head_y` by its `speed`.
2. Randomly mutates one tail glyph (flicker effect).
3. Prepends a fresh random glyph to the tail.
4. Removes drops whose tails have fully scrolled off screen.
5. Randomly spawns new drops according to `density`.

`render()` (CLI) and the GUI/TUI equivalents build a depth grid, then colour each glyph: depth 0 (head) = bright white-green, increasing depth fades through progressively darker greens.
