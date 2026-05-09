# Rainbow

Animated rainbow ASCII art for the terminal. Renders text with a smooth HSV
color gradient, a moving rainbow band, or a multi-line ASCII rainbow arc —
all running on the standard 256-color ANSI palette so it works in plain
terminals without truecolor support.

## What's in here

| File | What it does |
|------|--------------|
| `rainbow.py` | CLI + reusable helpers (`colorize`, `rainbow_arc`, `animate`, `hsv_to_rgb`). |
| `rainbow_gui.py` | CustomTkinter desktop app — animated label, mode toggle, speed slider, pause. |
| `rainbow_tui.py` | Textual TUI with the same modes via Rich color spans. |

## How the gradient works

Each character is colored from `HSV(h, 1, 1)` where `h` advances per column and
per frame. The float hue is converted to RGB, then quantized into the xterm
6×6×6 cube (codes 16..231). That gives smooth gradients on any terminal that
speaks ANSI 256 colors.

Modes:

- **gradient** — per-character HSV cycling text.
- **arc** — concentric ASCII semicircles, tinted red→violet, hue scrolls.
- **bands / band** — solid horizontal color bands (vertical stack).
- **lolcat** — text repeated with a per-line phase shift, scrolls.

## Run

```bash
# CLI: animated gradient text
uv run python rainbow/rainbow.py hello world

# Static one-frame outputs (good for piping)
uv run python rainbow/rainbow.py --once hello
uv run python rainbow/rainbow.py --once --arc

# Different modes
uv run python rainbow/rainbow.py --mode lolcat --fps 20 hello world
uv run python rainbow/rainbow.py --arc

# Desktop GUI
uv run python rainbow/rainbow_gui.py

# Terminal UI (Textual)
uv run python rainbow/rainbow_tui.py
```

CLI flags: `--arc`, `--band`, `--lolcat`, `--mode <name>`, `--fps <n>`,
`--once`. Press `Ctrl+C` to exit the CLI animation.

TUI bindings: `space` pause, `m` next mode, `+` / `-` faster / slower,
`Ctrl+Q` quit.

## Public API

```python
from rainbow import colorize, rainbow_arc, animate, hsv_to_rgb

print(colorize('hello, world!'))   # ANSI 256 rainbow text
print(rainbow_arc(width=80))       # multi-line ASCII arc
animate('RAINBOW', fps=12)         # blocks until Ctrl+C
```

`colorize(text, offset=0.0, freq=1/14)` returns a string with ANSI color
escapes. Pass a non-zero `offset` to scroll the gradient between frames.
