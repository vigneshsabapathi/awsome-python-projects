# Hangman

Classic word-guessing game. The player guesses letters one at a time; each
wrong guess adds a body part to a hand-drawn ASCII gallows. Six wrong
guesses ends the round.

Inspired by Al Sweigart's *Hangman & Guillotine* from
*The Big Book of Small Python Projects*. ASCII art and word lists are
original to this repo.

## Run

```bash
# Terminal CLI
uv run python hangman/hangman.py

# CustomTkinter desktop GUI (dark theme, on-screen keyboard)
uv run python hangman/hangman_gui.py

# Textual TUI (dark Tailwind palette)
uv run python hangman/hangman_tui.py
```

### TUI bindings

| Key      | Action               |
|----------|----------------------|
| `A`–`Z`  | Guess letter          |
| `Ctrl+N` | New game             |
| `Ctrl+C` | Cycle category       |
| `Ctrl+E` | Toggle Evil mode     |
| `Ctrl+Q` | Quit                 |

## Architecture

```
hangman/
├── hangman.py        ← Pure logic + CLI (mask, is_won, pick_word, STAGES)
├── hangman_evil.py   ← Adversarial 'Evil Hangman' engine
├── hangman_gui.py    ← CustomTkinter front-end, imports from hangman/_evil
├── hangman_tui.py    ← Textual front-end, imports from hangman/_evil
└── README.md
```

`hangman.py` is the canonical module: every front-end imports `mask`,
`is_won`, `pick_word`, `STAGES`, and `CATEGORIES` from it. No game state
lives in the front-ends except UI bookkeeping.

### Categories

- **animals** (15 words)
- **fruits** (15 words)
- **countries** (15 words)

### Creative twist — Evil Hangman

`hangman_evil.py` ships an adversarial mode. The computer never picks a
single secret word at the start; it keeps a *candidate set* of all words
matching the current mask. On every guess, candidates are partitioned by
the resulting mask pattern, and the engine drops to the **largest** group
(tie-broken in favour of the *miss* pattern, which costs the player a
wrong guess). Toggle with the **Evil mode** switch in the GUI or
**Ctrl+E** in the TUI.

### Difficulty heuristic

`difficulty(word)` rates each word *Easy / Medium / Hard* based on its
length and unique-letter count. Long words with few unique letters are
easier because each correct guess reveals more positions.

## Public API

```python
from hangman import pick_word, mask, is_won, STAGES, CATEGORIES, MAX_WRONG

>>> mask("PYTHON", {"P", "O"})
'P___O_'
>>> is_won("PYTHON", set("PYTHON"))
True
>>> len(STAGES)
7
```
