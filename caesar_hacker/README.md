# Caesar Hacker

Brute-force Caesar cipher cracker. Tries every one of the 26 possible shifts and ranks the candidates by English-likelihood. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `caesar_hacker.py` | stdlib |
| Modern desktop GUI | `caesar_hacker_gui.py` | CustomTkinter |
| Modern terminal UI | `caesar_hacker_tui.py` | Textual |

## How the scoring works

Each candidate plaintext is rated with a hybrid English-likelihood score (lower = more English-like):

1. **Chi-squared distance** from the standard English letter-frequency distribution. Robust on long texts.
2. **Common-word bonus.** Each token that appears in a small dictionary of the ~100 most common English words subtracts 25 points. This rescues short messages like `"Hello, World!"` where chi-squared on 10 letters is too noisy to pick a clear winner.

The candidate with the lowest combined score is reported as the most likely plaintext.

## Twist: diff vs ciphertext

Every candidate is also displayed with a **letter-overlap percentage** — the fraction of letter positions where the candidate matches the original ciphertext (case-insensitive). It's a quick visual diagnostic:

- Shift 0 always shows 100% overlap (no change).
- A correct decryption usually shows ~0% overlap (every letter shifted).
- Near-zero overlap + low score = strong evidence of a real plaintext.

## Run

```bash
# CLI — paste ciphertext, blank line submits.
uv run python caesar_hacker/caesar_hacker.py

# Desktop GUI (CustomTkinter)
uv run python caesar_hacker/caesar_hacker_gui.py

# Terminal UI (Textual)
uv run python caesar_hacker/caesar_hacker_tui.py
```

## Architecture

The core module `caesar_hacker.py` is pure functions only — no I/O coupled to UI. Both the GUI and TUI import:

- `decrypt_shift(text, shift)` — Caesar decryption for shift 0..25 (case + punctuation preserved)
- `encrypt_shift(text, shift)` — inverse of `decrypt_shift`, useful for tests
- `english_score(text)` — chi-squared distance plus common-word bonus, lower is better
- `crack(ciphertext)` — returns `list[(shift, score, plaintext)]` sorted best-first, always 26 entries
- `letter_overlap(a, b)` — fraction of letter positions that agree (powers the diff visualisation)

## Front-ends

### CLI

Reads multiline input, prints a ranked table with rank / shift / score / overlap / plaintext, and highlights the best guess.

### CustomTkinter GUI

Dark Tailwind palette. A multiline textbox accepts ciphertext, **Crack** triggers scoring, and the results panel renders a 26-row table:

- Rank, shift, score, overlap %, plaintext snippet
- Top row highlighted green (best guess)
- "Use this shift" button on every row copies that candidate to the clipboard
- "Copy Best" button does the same for the top result

### Textual TUI

Same Tailwind palette as `bagels_tui.py`. A single-line `Input` accepts ciphertext, **Enter** triggers a crack, and the `DataTable` shows all 26 candidates ranked by score.

| Binding | Action |
|---------|--------|
| **Enter** | Crack the current input |
| **Ctrl+C** | Copy top result to the clipboard |
| **Ctrl+Q** | Quit |

## Notes

- Chi-squared alone gets the wrong answer on `"Khoor, Zruog!"` — only 10 letters of signal. The word-hit bonus is what makes the smoke test pass.
- The dictionary is intentionally tiny (~100 words). It's a corrective nudge, not a full English-detection oracle. Long texts crack fine on chi-squared alone.
- Non-letter characters always pass through untouched, so punctuation, digits and whitespace are preserved across encrypt/decrypt round-trips.
