# Hacking

A Fallout-style password hacking minigame. The terminal shows a wall of junk
characters with ~15 candidate passwords hidden inside. One of them is the real
password; each wrong attempt reports a **likeness** score — the number of
letter positions matching the secret, like Mastermind. You get **4 tries**.

| Version | File | Stack |
|---------|------|-------|
| CLI | `hacking.py` | stdlib |
| Desktop GUI | `hacking_gui.py` | CustomTkinter |
| Terminal UI | `hacking_tui.py` | Textual |

## Run

```bash
uv run python hacking/hacking.py
uv run python hacking/hacking_gui.py
uv run python hacking/hacking_tui.py
```

## How it works

`likeness(guess, secret)` is a Hamming-distance complement: count of
positions where the two same-length strings match. Length mismatch raises;
comparison is case-insensitive.

```python
likeness('TRAINS', 'BRAINS') == 5   # all but position 0
likeness('ABCDEFG', 'GFEDCBA') == 1 # only D at idx 3
```

`pick_words(n, length, rng=None)` samples from an embedded ~300-entry
7-letter word pool. Pass a seeded `random.Random` for deterministic tests.

`Game(words, secret_idx, max_tries)` is the UI-agnostic state machine.
`Game.try_word(w)` returns:

```python
{'result': 'win'|'wrong'|'lose'|'invalid'|'over',
 'tries_left': int,
 'likeness': int}
```

## Twist — optimal-guess hint

Press the **OPTIMAL HINT** button (GUI) or **h** (TUI) to get a suggested next
pick that maximises **expected information gain** (Shannon entropy in bits)
against the candidates still consistent with all observed (guess, likeness)
clues. This is the same idea Knuth used for Mastermind solvers and 3Blue1Brown
popularised for Wordle.

```python
def expected_info_gain(candidate, remaining):
    bucket = Counter(likeness(candidate, w) for w in remaining)
    total = len(remaining)
    return sum(-(c/total) * log2(c/total) for c in bucket.values())
```

The candidate that splits the remaining set into the most evenly-sized
likeness buckets is the one that, in expectation, eliminates the most
possibilities.

## Bindings

| Action | CLI | GUI | TUI |
|---|---|---|---|
| Try a word | tag (`1`-`9`,`0`,`a`-`e`) or type word | click word | tag key (`1`-`9`,`0`,`a`-`e`) |
| Hint | type `hint` | OPTIMAL HINT button | `h` |
| New game | answer `y` after a round | NEW GAME button | `n` |
| Quit | type `quit` | close window | `Ctrl+Q` |

## Architecture

`hacking.py` is the only module with game logic. Both UIs `from hacking import
...` to share `pick_words`, `likeness`, `render_junk_wall`, and the `Game`
class. The Fallout-style junk wall is generated deterministically given a
seeded RNG — useful for testing layout rendering.
