# Monty Hall

Three doors, one car, two goats. You pick a door. Monty (who knows where the car is) opens a *different* door that hides a goat. Should you switch?

**Yes — switching wins 2/3 of the time.**

## Versions

| Version | File | Stack |
|---------|------|-------|
| CLI | `monty_hall.py` | stdlib |
| Desktop GUI | `monty_hall_gui.py` | CustomTkinter + matplotlib |
| Terminal UI | `monty_hall_tui.py` | Textual |

## Run

```bash
# CLI - interactive single round, or simulate mode
uv run python monty_hall/monty_hall.py

# GUI - 3 tabs: Play, Simulate (with N-door slider), Bayes derivation
uv run python monty_hall/monty_hall_gui.py

# TUI - same modes, keyboard-driven
uv run python monty_hall/monty_hall_tui.py
```

## TUI bindings

| Key | Action |
|-----|--------|
| `1` `2` `3` | pick door 1 / 2 / 3 |
| `s` | switch (Play, after Monty opens) / run sim (Sim tab) |
| `t` | stay (Play) / toggle highlighted strategy (Sim) |
| `n` | new round (Play) / re-run sim |
| `Tab` | switch between Play, Simulate, Bayes tabs |
| `Ctrl+Q` | quit |

## The math

Closed-form, with N doors and Monty opening exactly one goat door:

```
P(win | stay)   = 1 / N
P(win | switch) = (N - 1) / (N · (N - 2))
```

| N | stay | switch | ratio |
|---|------|--------|-------|
| 3  | 33.3% | **66.7%** | 2.00x |
| 4  | 25.0% | 37.5%   | 1.50x |
| 5  | 20.0% | 26.7%   | 1.33x |
| 10 | 10.0% | 11.25%  | 1.13x |
| 20 | 5.0%  | 5.26%   | 1.05x |

Switching always beats staying by `(N - 1) / (N - 2)`. The advantage is largest at N = 3 and shrinks as N grows — both strategies tend to 0 as N -> infinity, but switch always wins.

## Why it works (Bayes)

You picked door A. Before Monty does anything:

```
P(car=A) = 1/3        (the "stay" pile)
P(car ∈ {B, C}) = 2/3 (the "switch" pile)
```

Monty *knows* where the car is and *cannot* open it. When he opens C, he's not gathering information from a coin flip — he's collapsing the entire 2/3 pile onto B:

```
P(open=C | car=A) = 1/2   (he picks B or C uniformly)
P(open=C | car=B) = 1     (forced, can't open A or C-with-car)
P(open=C | car=C) = 0     (would reveal the car)
```

Posterior ∝ prior × likelihood:

```
car=A: (1/3)(1/2) = 1/6  →  1/3
car=B: (1/3)(1)   = 2/6  →  2/3
```

So switching to B wins 2/3 of the time. The full derivation is in the GUI's *Bayes* tab and the TUI's *Bayes* pane.

## API

```python
from monty_hall import play_round, simulate, theoretical, wilson_ci

play_round('switch', num_doors=3)            # -> True / False
simulate('switch', trials=10_000)            # -> {'wins', 'trials', 'p_win'}
theoretical('switch', num_doors=10)          # -> 0.1125
wilson_ci(successes=6700, trials=10_000)     # -> (lo, hi) 95% CI
```

All functions accept a `random.Random` instance via `rng=` for reproducibility.
