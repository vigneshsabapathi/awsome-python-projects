# Clickbait Headline Generator

A tiny generator that combines hand-authored templates with category-aware
word lists to produce sensationalized headlines like
*"10 Surprising Facts About Cats That Will Change Your Life Forever"*.

Inspired by Al Sweigart's "Clickbait Headline Generator" from
*The Big Book of Small Python Projects* — implemented from scratch with
original templates and word banks.

## Features

- **5 categories** — `general`, `animals`, `tech`, `food`, `money`
- **12 templates** with `{number}`, `{adjective}`, `{noun}`, `{outcome}` slots
  resolved by a single regex token-replace pass
- **Seedable RNG** — share favourite seeds; same seed + category +
  invocation order = same headlines
- **Outrage meter** (creative twist) — every headline gets a 0-100
  superlative-density score
- Three front-ends sharing the same pure-function core:
  CLI, CustomTkinter desktop GUI, and Textual TUI

## Run

```bash
# CLI
uv run python clickbait/clickbait.py                       # one headline
uv run python clickbait/clickbait.py --batch 5             # five at once
uv run python clickbait/clickbait.py --category tech --seed 42 --score

# Desktop GUI (CustomTkinter)
uv run python clickbait/clickbait_gui.py

# Terminal UI (Textual)
uv run python clickbait/clickbait_tui.py
```

### CLI flags

| Flag | Default | Meaning |
|---|---|---|
| `-n / --batch N` | `1` | number of headlines to print |
| `-c / --category` | `general` | one of `general`, `animals`, `tech`, `food`, `money` |
| `-s / --seed N` | random | seed the RNG for reproducible output |
| `--score` | off | prefix each line with its outrage score `[NNN]` |

### GUI bindings

- **Space** — generate a new headline
- **Ctrl+C** — copy the current headline
- **Ctrl+B** — pop a "batch of 10" window
- **Category dropdown** — change the active word bank
- **Seed entry + Apply** — lock the RNG to a specific seed

### TUI bindings

- **Space** — generate
- **B** — batch of 10 (modal)
- **C** — cycle the active category
- **Ctrl+Q** — quit

## Architecture

```
clickbait/
  clickbait.py        Pure functions + CLI
    TEMPLATES                    tuple of 12 templates
    GENERAL / ANIMALS / TECH /
    FOOD / MONEY                 per-category word banks
    CATEGORIES                   dict mapping name -> bank
    find_slots(template)         list[str] of slot names
    generate_headline(rng, cat)  -> str
    generate_batch(n, rng, cat)  -> list[str]
    outrage_score(headline)      -> 0-100
    main(argv)                   argparse entry-point
  clickbait_gui.py    CustomTkinter front-end (imports the core)
  clickbait_tui.py    Textual front-end (imports the core)
```

The core is dependency-free (stdlib only). The two front-ends each import
the `generate_*` and `outrage_score` functions from `clickbait`, so a fix
or new template instantly shows up in all three UIs.

### Slot substitution

Templates contain `{token}` placeholders. A single regex pass walks each
template and resolves every token:

```python
TOKEN_RE = re.compile(r"\{(\w+)\}")
TOKEN_RE.sub(lambda m: _resolve_slot(m.group(1), rng, bank), template)
```

`{number}` and `{small}` are synthesized (suspiciously specific list-counts
and "number #N" hooks). `{adjective}`, `{noun}`, `{outcome}` are drawn from
the active category's bank with `random.Random.choice`. Time complexity
is O(K) per headline where K is the template length — one regex pass plus
one `random.choice` per slot.

### Outrage meter

`outrage_score(headline)` lower-cases, tokenises, then counts hits against
a frozenset of clickbait words (`shocking`, `forbidden`, `secrets`, ...).
Digits and `!` add bonus weight. The hit count is divided by the word
count and scaled to 0-100.
