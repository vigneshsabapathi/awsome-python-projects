# Caesar Cipher

Shift each letter `N` positions in the alphabet — the simplest substitution
cipher in the book. Ships with three frontends sharing one core module.

## Run

```bash
uv run python caesar_cipher/caesar_cipher.py        # CLI, interactive prompt
uv run python caesar_cipher/caesar_cipher_gui.py    # CustomTkinter desktop UI
uv run python caesar_cipher/caesar_cipher_tui.py    # Textual terminal UI
```

## Architecture

```
caesar_cipher.py        Pure-function core: caesar_shift, encrypt, decrypt
                        Plus brute_force() that scores all 26 shifts by
                        Chi-squared distance to English letter frequency.
caesar_cipher_gui.py    CustomTkinter, dark theme. Live shift slider,
                        encrypt/decrypt segmented toggle, copy button,
                        char-count, and an Auto-crack button that picks
                        the most English-like shift.
caesar_cipher_tui.py    Textual, slate-900/sky palette. Ctrl+S swaps mode,
                        Ctrl+B toggles the brute-force panel, Ctrl+Q quits.
```

GUI and TUI both `from caesar_cipher import encrypt, decrypt, brute_force` —
the cipher logic lives in exactly one place.

## Features

- **Case preservation** — `Hello` shifted by 3 → `Khoor`.
- **Non-letters pass through** — punctuation, digits, whitespace untouched.
- **Brute-force panel** — all 26 candidate plaintexts scored by Chi-squared
  distance to English letter frequency; lowest score is most likely.
- **Auto-crack** (GUI) — one-click pick the best shift for any ciphertext.

## Smoke test

```bash
uv run python -c "import sys; sys.path.insert(0, 'caesar_cipher'); \
    import caesar_cipher; print(caesar_cipher.encrypt('Hello, World!', 3))"
# → Khoor, Zruog!
```
