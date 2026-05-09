# Countdown

A visual countdown timer that renders the clock as **seven-segment ASCII digit art**. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `countdown.py` | stdlib |
| Desktop GUI | `countdown_gui.py` | CustomTkinter |
| Terminal UI | `countdown_tui.py` | Textual |

## Run

```bash
# CLI — count down 60 seconds, redrawing in place every second
uv run python countdown/countdown.py 60

# CLI — Pomodoro mode (25m work / 5m break × 4)
uv run python countdown/countdown.py --pomodoro

# CLI — stopwatch (count up)
uv run python countdown/countdown.py --stopwatch

# Desktop GUI
uv run python countdown/countdown_gui.py

# Terminal UI
uv run python countdown/countdown_tui.py
```

## What you see

```
 ___   ___     ___   ___
|   |  ___| . |   | |___
|___| |___  . |___|  ___|
```

Each digit (and the colon) is drawn from a hand-authored 3-line glyph table. The colon is rendered as **two stacked dots** (top blank, middle dot, bottom dot).

## Twists

- **Pomodoro mode** — `--pomodoro` on the CLI, `t` in the TUI, "Pomodoro" checkbox in the GUI. Cycles 25 minutes of work + 5 minutes of break for 4 rounds, beeping at each transition.
- **Stopwatch toggle** — `--stopwatch` flag on the CLI counts up instead of down.
- **Progress bar overlay** — the CLI prints a `[#####-----]` bar under the digits showing fraction elapsed; suppress with `--no-bar`.

## Architecture

`countdown.py` exposes the pure-function building blocks consumed by both UIs:

- `format_time(seconds) -> str` — formats a non-negative int as `'MM:SS'`.
- `digit_art(digit_str) -> list[str]` — returns the 3-line ASCII glyph for one of `'0'-'9'` or `':'`.
- `render_clock(seconds) -> str` — joins each digit's art horizontally into one multi-line string.

Both the GUI and the TUI import `render_clock` and drop the result into a single Static/Label widget. Decrement loops are local to each frontend (`after()` in CTk, `set_interval()` in Textual).

## Bindings (TUI)

| Key | Action |
|-----|--------|
| `s` | Start |
| `p` | Pause |
| `r` | Reset |
| `t` | Toggle Pomodoro |
| `Ctrl+Q` | Quit |

## Notes

- The seven-segment glyphs are drawn from scratch — no external font, no copying. Each digit is exactly **3 lines tall, 5 columns wide**; the colon is **1 column wide**.
- Color shifts to red when fewer than 10 seconds remain, then green at zero.
- The CLI uses ANSI cursor-up + clear-line escapes (`\033[F\033[2K`) to redraw in place. Modern Windows Terminal and most POSIX terminals handle this fine; older `cmd.exe` may scroll instead.
- The terminal bell (`\a`) fires at zero in the CLI; the GUI uses `winsound.Beep` when available, falling back to the bell.
