# Simple Substitution Cipher

A monoalphabetic substitution cipher: each letter in the plaintext maps to
a different letter via a 26-character permutation key. Decryption uses the
inverse permutation. Ships with three frontends sharing one core module
plus a frequency-analysis attack that uses simulated annealing to recover
the key automatically.

## Run

```bash
uv run python simple_sub/simple_sub.py        # CLI
uv run python simple_sub/simple_sub_gui.py    # CustomTkinter desktop UI
uv run python simple_sub/simple_sub_tui.py    # Textual terminal UI
```

## Architecture

```
simple_sub.py        Pure-function core: encrypt, decrypt, random_key,
                     inverse_key, letter_frequencies, english_score,
                     and crack / crack_with_key (simulated annealing).
simple_sub_gui.py    CustomTkinter dark theme. 26-char key entry,
                     encrypt/decrypt segmented toggle, input + output
                     panes, embedded matplotlib letter-frequency chart
                     (input bars + English baseline line), Auto-crack
                     button that runs annealing on a worker thread.
simple_sub_tui.py    Textual, slate-900/sky palette. Same shape as the
                     GUI with an ASCII frequency chart. Bindings:
                     Ctrl+S swap, Ctrl+A auto-crack, Ctrl+R random
                     key, Ctrl+Q quit.
```

GUI and TUI both `from simple_sub import ...` so the cipher logic lives in
exactly one place.

## How it works

A substitution key is a permutation of `A-Z`. Position `i` in the key
gives the cipher letter substituted for the plaintext letter at position
`i` (so `key[0]` is the substitute for `A`, `key[1]` for `B`, etc).
Decryption uses the inverse permutation: `decrypt(encrypt(text, k), k) ==
text`.

```python
>>> from simple_sub import random_key, encrypt, decrypt
>>> k = random_key()                       # 26-char shuffled alphabet
>>> ct = encrypt('Hello, World!', k)
>>> decrypt(ct, k)
'Hello, World!'
```

Case is preserved; non-letters pass through untouched.

## Auto-crack: simulated annealing

The cracker tries to recover the key from ciphertext alone using
**simulated annealing** over the space of 26-letter permutations.

1. **Seed step.** Build an initial key by frequency-aligning ciphertext
   letters with English letter frequencies — most-common cipher letter
   becomes `E`, second-most becomes `T`, and so on.
2. **Score function.** Each candidate plaintext is scored as a sum of
   bigram log-frequencies, trigram log-frequencies, and a bonus for
   tokens that match a small dictionary of common English words.
   Higher = more English-like.
3. **Annealing step.** Repeatedly propose a random swap of two letters
   in the key. Always accept moves that improve the score; accept worse
   moves with probability `exp(delta / temperature)` (the Boltzmann
   criterion). The temperature decays geometrically over the iteration
   budget — high early temperature lets the chain escape local optima,
   low late temperature locks in the best solution.
4. **Restarts.** Run several short chains starting from progressively
   more-perturbed seeds. Return the highest-scoring plaintext seen
   across all chains.

For ~100-letter ciphertexts this converges in 3-8 seconds on a typical
CPU. Very short ciphertexts (like `Hello, World!` alone) rarely have
enough signal for any frequency-based attack, but the seed step alone
often gets close.

## Smoke test

```bash
uv run python -c "import sys, random; \
  sys.path.insert(0, 'simple_sub'); \
  import simple_sub; \
  k = simple_sub.random_key(random.Random(0)); \
  ct = simple_sub.encrypt('hello world', k); \
  pt = simple_sub.decrypt(ct, k); \
  assert pt == 'hello world'; print('OK')"
# → OK
```

## Related projects in this repo

- `caesar_cipher/` — the simplest substitution cipher (shift only).
- `caesar_hacker/` — brute-force attack on Caesar by chi-squared score.
- `rot13/` — Caesar with shift=13.
