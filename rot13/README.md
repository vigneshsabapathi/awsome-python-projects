# ROT13 Cipher

Shift each letter by 13. Because 13 + 13 = 26 = the size of the alphabet,
**applying ROT13 twice returns the original** — the cipher is its own inverse
(an *involution*). One function does both encrypt and decrypt. ROT13 was the
de-facto Usenet spoiler-hider for 30+ years for exactly this reason.

## Run

```bash
uv run python rot13/rot13.py "Hello, World!"        # → Uryyb, Jbeyq!
uv run python rot13/rot13.py                        # interactive prompt
uv run python rot13/rot13.py --rot 5 "Hello"        # generalize to any N
uv run python rot13/rot13.py --rot47 "Hi 42!"       # ROT47 (printable ASCII)
uv run python rot13/rot13.py --demo "Hello"         # show round-trip identity
uv run python rot13/rot13_gui.py                    # CustomTkinter desktop UI
uv run python rot13/rot13_tui.py                    # Textual terminal UI
```

## Architecture

```
rot13.py        Pure-function core: rot13(), rotate(text, n), rot47().
                CLI with --rot N (any rotation) and --rot47 (printable ASCII).
rot13_gui.py    CustomTkinter, dark theme. Two text panes (input/output) with
                live update, Copy button, rot13/rot47 toggle, and a
                Self-Inverse Demo button that applies twice and confirms
                identity.
rot13_tui.py    Textual, slate-900/sky palette. Same two-pane layout.
                Ctrl+R re-apply (input ← output), Ctrl+T toggle variant,
                Ctrl+D self-inverse demo, Ctrl+Q quit.
```

GUI and TUI both `from rot13 import rot13, rot47` — the cipher logic lives
in exactly one place. Standalone module — does *not* import from
`caesar_cipher/`.

## The involution insight

ROT13 has the rare property of being **self-inverse**:

```
rot13(rot13(s)) == s   for every string s
```

Why? Each letter is shifted by 13 modulo 26. Two shifts = 26 = 0 (mod 26).
This makes ROT13 a degree-2 element of the cyclic group ℤ/26 — only
ROT0 (identity) and ROT13 share this property.

The same logic generalizes:

| Variant | Range | Half-period | Involution? |
|---|---|---|---|
| ROT13 | A–Z (26)         | 13 | ✓ |
| ROT47 | ASCII 33..126 (94) | 47 | ✓ |
| ROT5  | digits 0–9 (10)  | 5  | ✓ |

ROT47 is the practical extension — it rotates digits and punctuation too, so
you can hide spoilers like *"the killer is on page 273"* without the numbers
giving it away.

## Smoke test

```bash
uv run python -c "import sys; sys.path.insert(0, 'rot13'); import rot13; \
    assert rot13.rot13('Hello, World!') == 'Uryyb, Jbeyq!'; \
    assert rot13.rot13(rot13.rot13('test')) == 'test'; print('OK')"
# → OK
```

## Why bother with --rot N?

A `--rot N` flag turns this into a tiny [Caesar cipher][caesar] too — same
core algorithm, no slider UI, no English-frequency cracker (see
`caesar_cipher/` for that). Useful for one-off shifts and for proving in a
single file that **ROT13 is just the special case where N = half the
alphabet**.

[caesar]: ../caesar_cipher/README.md
