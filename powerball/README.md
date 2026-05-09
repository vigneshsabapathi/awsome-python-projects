# Powerball Lottery

A simulator for the US Powerball lottery: pick 5 unique white balls from 1..69 plus 1 red Powerball from 1..26. Score against the drawing, study expected value vs. ticket cost, and watch Monte Carlo empirical hit rates converge on the theoretical odds. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `powerball.py` | stdlib + argparse |
| Desktop GUI | `powerball_gui.py` | CustomTkinter + matplotlib + NumPy |
| Terminal UI | `powerball_tui.py` | Textual |

## The game

- 5 unique white balls drawn from 1..69 (order doesn't matter)
- 1 red Powerball drawn from 1..26 (separate pool)
- 9 winning tiers from "PB only" ($4) up to the jackpot

Total outcomes: `C(69, 5) * 26 = 292,201,338`. Hence the famous "1 in 292 million" jackpot odds.

## Run

```bash
# CLI - interactive ticket entry, draw, EV table
uv run python powerball/powerball.py

# Simulate 10,000 random plays at a $1.5B jackpot
uv run python powerball/powerball.py --simulate 10000 --jackpot 1500000000 --seed 42

# Lifetime: 1 ticket/week for 50 years
uv run python powerball/powerball.py --lifetime

# Just the EV analysis at a given jackpot
uv run python powerball/powerball.py --ev --jackpot 800000000

# Desktop GUI - clickable number grid, draw + simulate + log-scale bar chart
uv run python powerball/powerball_gui.py

# Terminal UI - text inputs, unicode bar chart, hotkeys
uv run python powerball/powerball_tui.py
```

## Hotkeys (TUI)

- `Q` — generate a quick-pick ticket
- `D` — draw the winning numbers and score your ticket
- `S` — simulate N drawings (uses your ticket if valid, else fresh quick-picks)
- `Ctrl+Q` — quit

## Tier table (theoretical odds)

| Tier | Match | Prize | Odds (1 in) |
|------|-------|-------|-------------|
| PB only | 0 whites + PB | $4 | 38.3 |
| 1+PB | 1 white + PB | $4 | 91.98 |
| 2+PB | 2 whites + PB | $7 | 701.3 |
| 3 | 3 whites | $7 | 579.8 |
| 3+PB | 3 whites + PB | $100 | 14,494 |
| 4 | 4 whites | $100 | 36,525 |
| 4+PB | 4 whites + PB | $50,000 | 913,129 |
| 5 | 5 whites | $1,000,000 | 11,688,054 |
| **5+PB** | **5 whites + PB** | **JACKPOT** | **292,201,338** |

The "None" tier (0/1/2 whites without the powerball) covers ~95.98% of all draws.

## Expected value (the twist)

For a $2 ticket at jackpot J, the per-ticket EV is

```
EV = sum over tiers of (probability * prize)
   = (4 * 1/38.3) + (4 * 1/92) + ... + (J * 1/292,201,338)
```

The non-jackpot tiers contribute about **$0.32** in expectation, regardless of jackpot. So the break-even jackpot (after the 37% federal top-bracket tax on the jackpot) lands at roughly **$779 million**:

| Jackpot | Pre-tax EV | After-tax EV | Verdict |
|---------|-----------:|-------------:|---------|
| $100M | $0.66 | $0.53 | losing bet |
| $500M | $2.03 | $1.40 | losing bet |
| $779M | $3.00 | $2.00 | break-even |
| $1.5B | $5.45 | $3.55 | EV > cost (rare!) |
| $2.0B | $7.16 | $4.63 | EV > cost |

Caveats: jackpot sharing dilutes EV (with two co-winners EV drops 50%), state taxes shave more, and the lump-sum option pays out roughly half the advertised annuity. The TUI/GUI status bar shows EV continuously as you change the jackpot.

## Lifetime simulator

`--lifetime` simulates buying 1 ticket every week for 50 years (2,600 draws, $5,200 spent). Typical net result: a loss of $4,000–$5,000. You will not hit the jackpot. Across thousands of independent 50-year runs, the median lifetime player wins zero major prizes — the expected number of "5+PB" hits in 2,600 plays is `2600 / 292M ≈ 0.0000089`.

## Architecture

`powerball.py` exposes the pure simulation core that GUI and TUI import:

- `draw(rng=None)` — generate one drawing
- `quick_pick(rng=None)` — alias for ticket generation
- `score(ticket, drawing)` — return tier label
- `prize_for(tier, jackpot)` — dollars won for that tier
- `THEORETICAL_PROBS`, `ODDS_ONE_IN`, `FIXED_PRIZES`, `TIERS` — lookup tables
- `expected_value(jackpot, *, tax_rate, share_factor)` — per-ticket EV
- `break_even_jackpot(...)` — jackpot at which EV equals ticket cost
- `simulate(n, rng, ticket, jackpot)` — Monte Carlo loop returning counts/winnings/net
- `lifetime_loss(years, per_week, jackpot, rng)` — convenience wrapper

The GUI plots theoretical vs. empirical hit rates per tier on a log scale (necessary because the rates span 9 orders of magnitude). The TUI does the same with unicode bars on a log-scaled width mapping.

## Notes

- The `score` function is symmetric in ticket vs. drawing — both are validated.
- Combinatorics use `math.comb`; total outcomes = `C(69,5) * 26 = 292,201,338` matches the published jackpot odds exactly.
- The simulator is stdlib-only; only the GUI pulls in NumPy/matplotlib for plotting.
