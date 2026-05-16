# Vigenère Cipher

A polyalphabetic substitution cipher where each letter is shifted by an amount determined by a repeating keyword (A=0, B=1, …, Z=25). Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `vigenere.py` | stdlib |
| Modern desktop GUI | `vigenere_gui.py` | CustomTkinter |
| Modern terminal UI | `vigenere_tui.py` | Textual |

## Features

- **Encrypt / Decrypt** — Classic Vigenère with any keyword; non-letter characters pass through unchanged.
- **Autokey variant** — After the initial keyword the key continues with the plaintext itself, eliminating the periodicity that makes statistical attacks possible.
- **Auto-crack pipeline** — Three stages:
  1. **Kasiski examination** — repeated trigram spacings reveal likely key lengths.
  2. **Friedman / Index of Coincidence** — column IC confirms which candidate length decomposes the ciphertext into English-shaped columns.
  3. **Per-column Caesar attack** — each column is treated as a Caesar cipher; chi-squared distance from English letter frequencies recovers each key letter.

## Run

```bash
# CLI
uv run python vigenere/vigenere.py

# Desktop GUI (CustomTkinter)
uv run python vigenere/vigenere_gui.py

# Terminal UI (Textual)
uv run python vigenere/vigenere_tui.py
```

## GUI layout

Two text panes (input / output), a keyword entry at the bottom, and an **Encrypt / Decrypt** segmented toggle. A crack-analysis panel on the right shows the IC, Friedman key-length estimate, Kasiski candidates, and per-length column IC scores in real time. The **Auto-crack** button runs the full pipeline and writes the recovered key back into the keyword field, switching to Decrypt mode automatically.

## TUI bindings

| Key | Action |
|-----|--------|
| Ctrl+S | Swap encrypt ↔ decrypt |
| Ctrl+A | Auto-crack |
| Ctrl+Q | Quit |

## Architecture

`vigenere.py` is the pure-function core. Both GUIs import from it:

- `encrypt(text, key)` / `decrypt(text, key)` — classic Vigenère
- `encrypt_autokey(text, key)` / `decrypt_autokey(text, key)` — autokey variant
- `friedman_ic(text)` — index of coincidence
- `friedman_estimate(text)` — Friedman key-length estimate
- `kasiski(text)` — trigram-spacing key-length candidates
- `candidate_key_lengths(text)` — combined Kasiski + IC ranking
- `crack(text)` — full auto-crack pipeline; returns `(key, plaintext)`

## Notes

- Non-letter characters (spaces, punctuation) pass through the cipher unchanged; the key index only advances on alphabetic input, preserving formatting.
- The Kasiski + IC approach requires roughly 100+ ciphertext letters for reliable key recovery; shorter texts may not crack cleanly.
- The autokey variant is not crackable by `crack()` because it has no periodicity.
