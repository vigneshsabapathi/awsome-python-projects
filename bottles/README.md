# 99 Bottles of Beer

Print the classic countdown song with grammatically correct verses — `1 bottle` (singular), `0 bottles` rendered as `no more bottles`, and a closing wraparound verse that loops back to 99.

Inspired by Al Sweigart's *Big Book of Small Python Projects*. This single project covers **both** book entries — the classic *Ninety Nine Bottles* (#50) and the random-case remix variant *niNety nniinE BoOttels* (#51) — via a `--remix` flag and an in-app toggle.

| Version | File | Stack |
|---------|------|-------|
| CLI | `bottles.py` | stdlib |
| Modern desktop GUI | `bottles_gui.py` | CustomTkinter |
| Modern terminal UI | `bottles_tui.py` | Textual |

## Run

```bash
# CLI - full song
uv run python bottles/bottles.py

# Short demo run
uv run python bottles/bottles.py --start 5

# Remix - random per-letter casing
uv run python bottles/bottles.py --start 3 --remix --seed 42

# Desktop GUI - slider, Remix toggle, scroll-through animation
uv run python bottles/bottles_gui.py

# Terminal UI - SPACE for next verse, R to toggle remix
uv run python bottles/bottles_tui.py
```

## How it works

The whole project is really three pluralization edge cases hiding inside an English-grammar quirk:

- `n == 1` -> `"1 bottle"` (singular)
- `n == 0` -> `"no more bottles"` (special phrasing — not `"0 bottles"`)
- `n >= 2` -> `"<n> bottles"` (regular plural)

A single helper centralises the rule:

```python
def _bottles_phrase(n: int) -> str:
    if n <= 0:
        return "no more bottles"
    if n == 1:
        return "1 bottle"
    return f"{n} bottles"
```

`verse(n)` then composes a four-line stanza using two phrases — the current count and `n - 1` — so the singular/plural transition between adjacent verses is always correct. `verse(0)` is the wraparound: *"Go to the store and buy some more, 99 bottles of beer on the wall."*

## Remix mode (niNety nniinE BoOttels)

Per-character random casing, applied only to letters:

```python
ch.lower() if rng.random() < 0.5 else ch.upper()
```

Spaces, digits, and punctuation pass through unchanged so the verse structure stays readable. Pass a `--seed` to make the casing reproducible.

## What the GUI shows

A big lyrics panel front-and-center with monospace text. Controls:

- **Slider** — pick any starting bottle count from 1 to 99.
- **Remix switch** — toggle the random-case variant live.
- **Next verse / SPACE** — advance one step; auto-loops after the wraparound.
- **Play scroll** — animates the countdown verse-by-verse, with a brief pause on the wraparound.
- **Reset / Enter** — jump back to the starting count.

## What the TUI shows

A single centered lyrics panel. Keys:

- **Space** — next verse
- **R** — toggle remix
- **Enter** — reset to start
- **Ctrl+Q** — quit

## Architecture

`bottles.py` exposes the pure rendering API used by both UIs:

- `verse(n) -> str` — single verse, handles n=2/n=1/n=0 transitions.
- `song(start=99) -> str` — full song with verses joined by blank lines.
- `remix_text(text, rng) -> str` — random-case any string.
- `render_verse(n, *, remix, rng)` / `render_song(...)` — convenience dispatch used by the GUI/TUI to switch modes without branching.
- `_bottles_phrase(n)` — the singular/plural rule lives here and only here.

The GUI and TUI both call `render_verse()`; they don't reinvent the lyrics.

## Verify

```bash
uv run python -c "import sys; sys.path.insert(0, 'bottles'); import bottles; v = bottles.verse(2); assert '2 bottles' in v and '1 bottle' in v; print('OK')"
```
