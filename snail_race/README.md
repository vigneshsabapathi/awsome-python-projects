# Snail Race  🐌

Multiple snails race down a horizontal track. Each tick, every snail crawls
forward by a random number of steps; first to the finish line wins. The
player bets on a snail and gets paid out at live implied odds derived from
each snail's *personality* (mean step + variance).

Three frontends share one engine in `snail_race.py`.

## Run

```powershell
# CLI (ASCII animation)
uv run python snail_race/snail_race.py

# Desktop GUI (CustomTkinter, Tk Canvas lanes)
uv run python snail_race/snail_race_gui.py

# Terminal UI (Textual)
uv run python snail_race/snail_race_tui.py
```

## Files

| File | What |
|---|---|
| `snail_race.py`     | Pure engine + CLI. `Race`, `Personality`, `implied_odds`, `settle_bet`. |
| `snail_race_gui.py` | CustomTkinter window. Tk Canvas lanes, betting panel, speed slider. |
| `snail_race_tui.py` | Textual TUI with the same gameplay and keyboard bindings. |

## Engine API

```python
from snail_race import Race, implied_odds, settle_bet

race = Race(num_snails=4, track_length=40, rng=None)
while not race.is_done():
    race.step()                  # advance one tick
    print(race.positions, race.tick)
print(race.winner())             # int index of the winning snail

# Or run the whole race in one call:
race = Race(4, 40)
final = race.step_until_done()   # returns the final state dict
```

## Gameplay

- Starting bankroll: $1,000.
- Wager in steps of $10 (slider in GUI; `+`/`-` in TUI).
- Pick a snail. Win pays at the snail's decimal odds; lose forfeits the wager.

### TUI bindings

| Key | Action |
|---|---|
| `1`-`4` | Bet on snail #N |
| `space` | Start race / advance to next race |
| `+` / `-` | Adjust wager by $10 |
| `n` | Reset bankroll |
| `Ctrl+Q` | Quit |

## Twist — personalities + live odds

Each snail has a different `(min_step, max_step)` per tick:

| Snail | Steps per tick | Profile |
|---|---|---|
| Sprinter | 0 – 4 | High mean, high variance — streaky |
| Steady   | 1 – 2 | Low mean, very low variance — never stalls |
| Average  | 0 – 3 | Median field |
| Wild Card| 0 – 5 | Highest mean *and* highest variance — chaos |

The book computes **decimal odds** from each snail's mean step:

```
prob_i  ∝ mean_step_i / Σ mean_step
odds_i  = 1 / (prob_i · 1.05)        # 5% overround → small house edge
```

Implied probabilities sum to **1.05** (the house's vig), exactly the
shape of a real sportsbook line. Faster snails have shorter odds; the
slow-and-steady snail pays bigger if it pulls off the upset.

## Smoke test

```powershell
uv run python -c "import sys, random; sys.path.insert(0, 'snail_race'); import snail_race; r = snail_race.Race(4, 30, random.Random(0)); r.step_until_done(); assert r.is_done(); print('OK')"
# OK
```
