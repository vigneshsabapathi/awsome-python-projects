# Rock Paper Scissors

Three flavors of the classic, in one mini-project — consolidates two Sweigart Big Book mini-projects:

- **#59 Rock Paper Scissors** — fair random opponent
- **#60 Rock Paper Scissors (Always-Win Version)** — cheating opponent

Plus the real twist: a **Markov-predictor** opponent that learns 1st-order transitions of your moves and counters the predicted next one.

| Version | File | Stack |
|---------|------|-------|
| CLI | `rps.py` | stdlib |
| Desktop GUI | `rps_gui.py` | CustomTkinter |
| Terminal UI | `rps_tui.py` | Textual |

## Modes

| Mode | Behaviour |
|------|-----------|
| **fair** | Computer picks uniformly at random — expected score is ~1/3 each. |
| **markov** | Computer tracks `transitions[last_move][next_move]` over your moves and plays the counter to the most-likely next move. Wins ~99% against pure repeating patterns like `r p s r p s ...`. |
| **cheat** | Computer "sees" your move and plays the counter — you can never win. |

## Run

```bash
# CLI
uv run python rps/rps.py

# Desktop GUI (CustomTkinter)
uv run python rps/rps_gui.py

# Terminal UI (Textual)
uv run python rps/rps_tui.py
```

## TUI bindings

| Key | Action |
|-----|--------|
| `r` / `p` / `s` | Play rock / paper / scissors |
| `m` | Cycle mode (fair → markov → cheat) |
| `n` | Reset score |
| `Ctrl+Q` | Quit |

## Architecture

`rps.py` holds the shared logic; both UIs import:

- `Game(mode='fair'|'markov'|'cheat', rng=None)` — stateful game; tracks score and Markov transitions.
- `Game.play(player_move) -> dict` — returns `{computer_move, result, score}`.
- `Game.reset()` — clear score and learned transitions.
- `result_of(p1, p2) -> 'tie'|'p1'|'p2'` — pure outcome resolver.
- `MOVES`, `COUNTER`, `EMOJI` — constants.

## Notes

- **Markov state isn't useful for the first round** — there's no last-move history yet, so the predictor falls back to uniform random. After your second move, the chain has its first observation.
- **Random tie-break.** When multiple next-moves tie for most-likely, the predictor picks one at random — otherwise the computer would itself become predictable to a savvy player.
- **Mode switching resets learning.** Changing modes constructs a fresh `Game` with empty transitions, since the player's strategy may also change.
- **Cheat mode is structurally unwinnable** — it's not "very high win rate", it's literally `play(COUNTER[player_move])`, returned synchronously after the player commits.
