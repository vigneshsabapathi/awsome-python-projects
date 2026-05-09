# Guess the Number

The classic higher/lower game: the program picks a secret integer in
`[low, high]`, you guess, and it tells you whether to go higher or lower
until you find it (or run out of lives).

| Version | File | Stack |
|---------|------|-------|
| CLI | `guess_number.py` | stdlib |
| Desktop GUI | `guess_number_gui.py` | CustomTkinter |
| Terminal UI | `guess_number_tui.py` | Textual |

## Run

```bash
# CLI
uv run python guess_number/guess_number.py

# Desktop GUI (CustomTkinter)
uv run python guess_number/guess_number_gui.py

# Terminal UI (Textual)
uv run python guess_number/guess_number_tui.py
```

## Defaults

| Setting | Value | Why |
|---------|-------|-----|
| Range | 1..100 | classic |
| Lives | 10 | `ceil(log2(100)) = 7`, so 10 leaves slack |

## Features

- **Range entry** — change `low` / `high` / `lives` at any time and click
  *New Game*.
- **History panel** — every past guess is shown with an arrow indicating
  the direction the secret lies.
- **Hint button** (Ctrl+H in TUI) — reveals the binary-search optimal
  next guess: the midpoint of the *currently narrowed* candidate range.
- **Info-theory display** — every guess shows how many candidates and
  how many bits of entropy are left in the search space.

## Architecture

`guess_number.py` exposes the pure game logic that both GUIs reuse:

```python
from guess_number import Game, optimal_guess, bits_remaining

g = Game(low=1, high=100, max_guesses=10)
g.guess(50)            # -> {'result': 'too_low', 'guesses_left': 9, ...}
g.hint()               # -> 76  (midpoint of narrowed range)
g.bits_left()          # -> ~5.6 bits remaining
```

| Function / Class | Purpose |
|------------------|---------|
| `Game(low, high, max_guesses, rng)` | Encapsulated session; tracks history + narrowed bounds. |
| `Game.guess(n)` | Returns `{result, guesses_left, secret}` where `result` is `'win' \| 'too_low' \| 'too_high' \| 'lose' \| 'invalid' \| 'over'`. |
| `Game.hint()` | Optimal next guess (midpoint of narrowed bounds). |
| `Game.bits_left()` | Bits of entropy remaining in candidate range. |
| `optimal_guess(low, high)` | Pure binary-search midpoint. |
| `bits_remaining(low, high)` | `log2(high - low + 1)`. |
| `ReverseGame` | Reverse-mode helper: computer guesses, you answer. |

## Why the hint is "optimal"

Each guess answers one yes/no question (`<` or `>`), removing at most
one bit of entropy. The midpoint guess maximises information gain
*regardless of where the secret actually is* — it's the only choice that
guarantees at most `ceil(log2(N))` guesses worst case.

For `[1, 100]` that's 7 guesses; the default 10 lives means a careful
binary-search player should always win.

## Twist: information-theory display

Both GUIs show "**N candidates ~ B bits**" alongside the lives counter.
Watching `B` halve with each well-placed guess is the most direct
intuition for why binary search is `O(log n)` — every step subtracts
exactly 1 bit. A non-bisecting guess subtracts less.

A `ReverseGame` helper is also exposed for tinkering with the dual
("you pick, computer guesses optimally") in a Python REPL.
