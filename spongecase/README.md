# sPoNgEcAsE

Convert ordinary text to the **mocking-spongebob** alternating-case meme
(`hello world` -> `hElLo WoRlD`). Three frontends share one core module.

## Run

```bash
uv run python spongecase/spongecase.py        # CLI, interactive prompt
uv run python spongecase/spongecase_gui.py    # CustomTkinter desktop UI
uv run python spongecase/spongecase_tui.py    # Textual terminal UI
```

## Architecture

```
spongecase.py        Pure-function core:
                     to_sponge(text, intensity, rng)  — biased random
                     to_sponge_strict(text)            — deterministic
spongecase_gui.py    CustomTkinter, dark slate + yellow-400 accent.
                     Two text panes, intensity slider 0..100, mode
                     toggle (random/strict), seed entry, preset chips
                     (chill 25 / mock 60 / max ridicule 100), Re-roll
                     button, Copy button.
spongecase_tui.py    Textual, slate-900 + yellow palette.
                     Ctrl+M cycle mode, Ctrl+R re-roll, Ctrl+Q quit.
```

GUI and TUI both `from spongecase import to_sponge, to_sponge_strict`
— the case-flipping logic lives in exactly one place.

## How it works

### `to_sponge(text, intensity, rng)`

Each *letter* is independently set to upper- or lower-case with a
probability biased toward **flipping** relative to the previous letter's
case. `intensity` (clamped to `[0.0, 1.0]`) controls how strong that
flip-bias is:

| `intensity` | Flip prob vs previous letter | Behaviour |
|---|---|---|
| 0.0 | 0.5 | memoryless 50/50 — chaotic, runs of same case allowed |
| 0.5 | 0.75 | strong alternation but not strict |
| 1.0 | 1.0 | strict alternation (random starting case) |

Linear interpolation: `flip_prob = 0.5 + 0.5 * intensity`.

Non-letters pass through unchanged and **don't advance the alternating
state** — `"ab cd"` and `"abcd"` produce the same case pattern on the
letters.

### `to_sponge_strict(text)`

Deterministic alternation starting upper: `Hello world` -> `HeLlO wOrLd`.
Non-letters pass through and don't advance the counter, so the *first*
letter after a space resumes whatever the alternation was — this is what
makes the punctuation-aware version look natural rather than mechanical.

### The twist — sponge emoji at maximum ridicule

At `intensity >= 0.9`, `to_sponge` appends a 🧽 emoji to the output as a
"max ridicule" indicator. The GUI/TUI surface this naturally because
they call `to_sponge` on every keystroke.

## Reproducibility

Pass `rng=random.Random(seed)` for deterministic output:

```python
>>> import random
>>> from spongecase import to_sponge, to_sponge_strict
>>> to_sponge('hello world', intensity=1.0, rng=random.Random(0))
'hElLo WoRlD🧽'
>>> to_sponge_strict('hello world')
'HeLlO wOrLd'
>>> to_sponge('hello world', intensity=0.0, rng=random.Random(0))
'HelLLo WORLD'   # chaotic — runs of same case allowed at intensity 0
```

The GUI and TUI both expose the seed; the `Re-roll` button just picks
a new random seed and re-renders.

## Smoke test

```bash
uv run python -c "import sys, random; sys.path.insert(0, 'spongecase'); \
  import spongecase; out = spongecase.to_sponge('hello world', 1.0, \
  random.Random(0)); assert any(c.isupper() for c in out) and \
  any(c.islower() for c in out); print('OK')"
# -> OK
```
