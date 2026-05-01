# Birthday Paradox

A Monte Carlo simulation of the surprising probability that two people in a small group share a birthday. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `birthday_paradox.py` | stdlib |
| Modern desktop GUI | `birthday_paradox_gui.py` | CustomTkinter + matplotlib + NumPy |
| Modern terminal UI | `birthday_paradox_tui.py` | Textual |

## The paradox

In a group of just **23 people**, there's a ~50% chance two share a birthday. With **70 people**, it climbs to ~99.9%. Most people guess much higher group sizes — that's why it's called a paradox (though it's really just an unintuitive result).

## Run

```bash
# CLI - prompt for N, runs 100k trials
uv run python birthday_paradox/birthday_paradox.py

# Desktop GUI - sweep + chart with theoretical curve, empirical points, 95% CI
uv run python birthday_paradox/birthday_paradox_gui.py

# Terminal UI - ASCII bar chart, sample N values highlighted
uv run python birthday_paradox/birthday_paradox_tui.py
```

## What the GUI shows

The desktop GUI sweeps every N from 2 to 80 in one shot (NumPy-vectorized — ~1 second for 10k trials × 79 group sizes) and renders:

- **Theoretical curve** — closed form `1 - ∏ (365-k)/365` in cyan
- **Empirical points** — Monte Carlo estimates per N in amber
- **95% Wilson confidence band** — narrows visibly as you bump trials from 1k → 100k
- **50% reference line** — makes the "23 ≈ ½" crossover obvious
- **Movable N marker** — slider highlights any N from 2 to 80, status bar shows that point's theoretical, empirical, and CI

The TUI shows the same data as a unicode bar chart at sampled N values (2, 5, 10, 15, 20, 23, 25, 30, 35, 40, 50, 60, 70, 80), with the currently-selected N highlighted. Type a new N in the input field to update the status; press **Ctrl+R** to re-run, **Ctrl+Q** to quit.

## Reference probabilities

| Group size | Match probability |
|------------|-------------------|
| 5          | ~2.7%             |
| 10         | ~11.7%            |
| 20         | ~41.1%            |
| 23         | **~50.7%**        |
| 30         | ~70.6%            |
| 50         | ~97.0%            |
| 70         | ~99.9%            |

The empirical estimate should land within ~1% of these on 10k trials and within ~0.3% on 100k trials.

## Architecture

`birthday_paradox.py` holds the shared logic:

- `getBirthdays(n)` / `getMatch(birthdays)` — the original `datetime`-based helpers
- `simulate(n, trials)` — stdlib Monte Carlo, returns the count of trials with a collision
- `theoretical(n, days=365)` — closed-form probability
- `wilson_ci(successes, trials, z=1.96)` — Wilson score 95% confidence interval

The GUI imports `theoretical` and `wilson_ci` and runs its own NumPy-vectorized sweep (`simulate_sweep`) for speed. The TUI uses the stdlib `simulate` since it only evaluates 14 sample N values.

## Notes

- 365-day year, uniform distribution. Real-world birthdays cluster (Sept peak in the US, Feb 29 rare), so the actual probability is a hair *higher* than the model predicts.
- The Monte Carlo error scales as O(1/√T) — quadrupling trials roughly halves the empirical band width. Watch the CI shrink in the GUI as you switch trials from 1k → 100k.
