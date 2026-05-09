# Leetspeak

Convert ordinary text to **leet/1337** by probabilistic letter substitution
(`hello` -> `h3ll0`, or at full blast `#3||0`). Three frontends share one
core module.

## Run

```bash
uv run python leetspeak/leetspeak.py        # CLI, interactive prompt
uv run python leetspeak/leetspeak_gui.py    # CustomTkinter desktop UI
uv run python leetspeak/leetspeak_tui.py    # Textual terminal UI
```

## Architecture

```
leetspeak.py        Pure-function core: LEET_MAP, MULTI_MAP,
                    to_leet(text, intensity, rng), from_leet(text),
                    brute_decode(text) -> ranked candidates.
leetspeak_gui.py    CustomTkinter, dark slate + cyan-400 accent.
                    Two text panes, intensity slider 0..100,
                    encode/decode segmented toggle, preset chips
                    (mild 20% / standard 50% / hardcore 100%),
                    Re-roll button, Copy button, brute-decode panel.
leetspeak_tui.py    Textual, slate-900 + cyan palette.
                    Ctrl+S swap mode, Ctrl+R re-roll randomness,
                    Ctrl+B toggle brute-decode, Ctrl+Q quit.
```

GUI and TUI both `from leetspeak import to_leet, from_leet, brute_decode`
— the substitution logic lives in exactly one place.

## How it works

### Encoding (`to_leet`)
Two passes, both probabilistic:

1. **Multi-character pass** at `intensity * 0.25` — common digraphs and
   words get a casual leet swap (`at` -> `@`, `and` -> `&`, `oo` -> `00`,
   `you` -> `j00`).
2. **Single-letter pass** at `intensity` — every letter that has a leet
   form swaps with that probability, choosing uniformly among
   `LEET_MAP[letter]` (e.g. `a` -> one of `4`, `@`, `/-\`).

Pass an explicit `rng=random.Random(seed)` for reproducible output.

### Decoding (`from_leet`)
Greedy longest-match against every leet token in `LEET_MAP`. Ambiguous
tokens (e.g. `1` could be `i` or `l`) pick the first letter registered
in the dict — `from_leet` is best-effort, not invertible.

### Brute-decode panel (the twist)
Five canned profiles (identity, digits-only, l-favoring, punctuation-only,
full `from_leet`) each produce a candidate decoding. Each candidate is
scored against English letter frequency with **Chi-squared distance**
— lowest score wins. Surfaces the most-English-like reading even when
the leet is ambiguous.

## Features

- **Configurable intensity** — 0% leaves text alone, 100% substitutes
  every letter that has a leet form.
- **Multi-character substitutions** — `at` -> `@`, `and` -> `&`,
  `oo` -> `00`, `you` -> `j00`, applied at lower probability for a
  realistic "casual leet" feel.
- **Re-roll** — same input + intensity, different randomness. Useful in
  the GUI/TUI when the live preview is unsatisfying.
- **Brute-decode** — one panel, five strategies, ranked by English
  letter-frequency Chi-squared.

## Smoke test

```bash
uv run python -c "import sys, random; sys.path.insert(0, 'leetspeak'); \
  import leetspeak; print(leetspeak.to_leet('hello', intensity=1.0, \
  rng=random.Random(0)))"
# -> |-|3||0
```
