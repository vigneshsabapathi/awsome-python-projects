# Bitmap Message

Print a user-supplied message as ASCII art by treating a multi-line string as a 2-tone bitmap: every space stays a space, every non-space gets replaced by characters cycled from the message.

Inspired by Al Sweigart's *Bitmap Message* project from *The Big Book of Small Python Projects*. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `bitmap_message.py` | stdlib |
| Modern desktop GUI | `bitmap_message_gui.py` | CustomTkinter |
| Modern terminal UI | `bitmap_message_tui.py` | Textual |

## Run

```bash
# CLI - prompt once, render once
uv run python bitmap_message/bitmap_message.py

# Desktop GUI - two-pane editor with live preview, Copy button
uv run python bitmap_message/bitmap_message_gui.py

# Terminal UI - live preview as you type
uv run python bitmap_message/bitmap_message_tui.py
```

## How it works

The core trick is a **modulo-cycle** over the message:

```python
for i, bit in enumerate(line):
    if bit == ' ':
        print(' ', end='')
    else:
        print(message[i % len(message)], end='')
```

`message[i % len(message)]` is the canonical "cycle through a sequence" pattern — same one used in Vigenère ciphers, round-robin schedulers, and ring-buffer indexing.

## What the GUI shows

A two-pane editor with the bitmap on the left (editable), the live render on the right, and the message input at the top. Every keystroke in either pane re-renders. The **Preset** dropdown switches between four built-in shapes — *Diamond*, *Triangle*, *Heart*, *Circle* — and replaces the editor contents instantly. **Copy preview** ships the rendered art to your clipboard; **Reset bitmap** reloads the current preset.

## What the TUI shows

A single-pane preview with the message input at the top. Keys:

- **Ctrl+P** — cycle to the next preset (Diamond → Triangle → Heart → Circle → …)
- **Ctrl+B** — toggle the bitmap editor pane
- **Ctrl+R** — reset to the current preset
- **Ctrl+Q** — quit

Type the message and the preview updates live.

## Customizing the bitmap

The default bitmap is a simple diamond. To use a different shape:

- **GUI / TUI** — type or paste directly into the bitmap editor pane.
- **CLI** — replace the `BITMAP` string in `bitmap_message.py`.

The rules:

- **Spaces** = blank pixels (stay as spaces in output).
- **Anything else** = filled pixels (get replaced by message characters).
- The bitmap is just a multi-line string — width and height are arbitrary.

If you own *The Big Book of Small Python Projects*, the famous world-map bitmap is hosted at [inventwithpython.com/bitmapworld.txt](https://inventwithpython.com/bitmapworld.txt) — paste its contents into the editor pane (GUI/TUI) or into the `BITMAP` constant (CLI).

## Architecture

`bitmap_message.py` exposes:

- `render(bitmap, message) -> str` — pure function, no I/O. Imported by both UIs.
- `PRESETS` — dict mapping preset name → bitmap string (Diamond, Triangle, Heart, Circle).
- `BITMAP` — alias of `DIAMOND`, kept for the original CLI.
- `main()` — the original CLI prompt + print loop.

The GUI and TUI both call `render()` on every keystroke; they don't reinvent the rendering logic.
