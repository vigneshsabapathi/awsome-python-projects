# Pig Latin

Translate English to Pig Latin (and back, best-effort) — three encoding flavours, a CLI, a CustomTkinter desktop GUI, and a Textual TUI.

Inspired by Al Sweigart's *Pig Latin* project from *The Big Book of Small Python Projects*. This implementation was built from scratch and adds case/punctuation preservation, contraction & hyphenated-compound handling, and two extra encoding modes.

| Version | File | Stack |
|---------|------|-------|
| CLI | `pig_latin.py` | stdlib |
| Modern desktop GUI | `pig_latin_gui.py` | CustomTkinter |
| Modern terminal UI | `pig_latin_tui.py` | Textual |

## Run

```bash
# CLI - prompt loop
uv run python pig_latin/pig_latin.py

# Desktop GUI - two-pane editor with live update + Copy button
uv run python pig_latin/pig_latin_gui.py

# Terminal UI - two-pane editor with live update
uv run python pig_latin/pig_latin_tui.py
```

## Rules

| Word starts with     | Rule                                  | Example                  |
|----------------------|---------------------------------------|--------------------------|
| Consonant cluster    | move cluster to end + `ay`            | `pig` -> `igpay`         |
|                      |                                       | `string` -> `ingstray`   |
| Vowel (a, e, i, o, u)| append `way`                          | `apple` -> `appleway`    |
| `y` (anywhere else)  | treated as vowel                      | `rhythm` -> `ythmrhay`   |

`y` only counts as a consonant when it's the *first* letter (`yellow` -> `ellowyay`).

## Preservation rules

- **Case** — `Python` -> `Ythonpay` (Title case stays Title case), `HELLO` -> `ELLOHAY` (ALL CAPS stays ALL CAPS).
- **Punctuation** — `"hello,"` -> `"ellohay,"` (leading/trailing punctuation rides along).
- **Contractions** — `don't` -> `on'tday` (apostrophe stays inside the word).
- **Hyphenated compounds** — `mother-in-law` -> `othermay-inway-awlay` (each segment translated independently).

## Encoding modes

The `mode` parameter on `translate(text, mode=...)` and `untranslate(text, mode=...)` selects between:

| Mode      | Rule                                           | `pig` / `apple`              |
|-----------|------------------------------------------------|------------------------------|
| `pig`     | move consonants + `ay`  /  vowel + `way`       | `igpay` / `appleway`         |
| `greek`   | same split, suffix `uth` (no `w` for vowels)   | `iguth` / `appleuth`         |
| `ubbi`    | "Ubbi Dubbi" — insert `ub` before each vowel   | `pubig` / `ubappubluble`     |

`ubbi` is a different encoding entirely (popular from *Zoom*, the 1970s PBS show) — every vowel sound gets a `ub` prefix.

## Architecture

`pig_latin.py` exposes the pure functions used by both UIs:

- `translate_word(word, mode='pig') -> str` — single token, preserves case + surrounding punctuation.
- `translate(text, mode='pig') -> str` — free text; preserves whitespace + punctuation.
- `untranslate(text, mode='pig') -> str` — best-effort reverse.

The GUI and TUI both call `translate` / `untranslate` on every keystroke; they do not reinvent the encoding logic.

## Reverse-translation caveat

Pig Latin is **lossy**. `ousehay` could decode to `house` (cluster `h` moved) or `shouse` (cluster `sh` moved); `orryway` could be `worry` *or* `orry`. The decoder uses two heuristics:

1. **Onset-cluster bias** — prefer the longest *known* English consonant onset cluster (`str`, `spr`, `bl`, `br`, `ch`, ...) as the recovered cluster. This gets common English words right far more often than not.
2. **Vowel-initial preference** — when a body ends with `w` and starts with a vowel, prefer the vowel-initial reading (`appleway` -> `apple`).

Without a dictionary we can't do better. Round-tripping unambiguous words is reliable; ambiguous ones (`world` <-> `orld`, `how` <-> `who`) won't always round-trip.

## Verify

```bash
uv run python -c "import sys; sys.path.insert(0, 'pig_latin'); import pig_latin; assert pig_latin.translate_word('pig') == 'igpay'; assert pig_latin.translate_word('apple') == 'appleway'; print('OK')"
```
