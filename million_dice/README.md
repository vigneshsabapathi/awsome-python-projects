# Million Dice Statistics

Roll N dice millions of times and analyze the distribution of their **sums**: mean, standard deviation, frequency histogram, and how well it matches the Normal approximation predicted by the **Central Limit Theorem**. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `million_dice.py` | NumPy |
| Modern desktop GUI | `million_dice_gui.py` | CustomTkinter + matplotlib + NumPy |
| Modern terminal UI | `million_dice_tui.py` | Textual + NumPy |

## The CLT in one picture

The sum of N independent dice rolls is **uniform** for N=1, **triangular** for N=2, and rapidly approaches a **bell curve** (Normal distribution) by N=3 or N=5. That convergence is the Central Limit Theorem — and you can see it happen on screen.

For an s-sided die rolled N times:

```
mean(sum) = N · (s + 1) / 2
var(sum)  = N · (s² - 1) / 12
std(sum)  = sqrt(var(sum))
```

For 2d6: mean = 7, std ≈ 2.415. For 5d20: mean = 52.5, std ≈ 12.85.

## Run

```bash
# CLI - prints summary stats + unicode histogram
uv run python million_dice/million_dice.py --n 2 --rolls 1000000
uv run python million_dice/million_dice.py --n 5 --rolls 100000 --sides 20

# Desktop GUI - sliders for dice/rolls/sides, embedded matplotlib bar chart
# with Normal-curve overlay + CLT side-by-side toggle
uv run python million_dice/million_dice_gui.py

# Terminal UI - same controls, unicode histogram, σ-band coloring
uv run python million_dice/million_dice_tui.py
```

## What the GUI shows

- **Bar chart** of sum probability mass — one bar per integer sum from N to N·sides
- **Orange Normal-PDF overlay** — the CLT prediction from `(μ, σ)` computed analytically
- **Green μ line + ±σ / ±2σ bands** — see how well empirical reality lines up with theory
- **CLT panels toggle** — flip the switch to see N=1, 2, 3, 5 side-by-side: uniform → triangular → near-normal → bell. This is the visual money shot.
- **Stats footer** — empirical μ/σ vs theoretical μ/σ, with the deltas (which shrink as O(1/√rolls))

Sliders cover **1–10 dice**, **1k–10M rolls** (log scale), and **d4 / d6 / d8 / d10 / d12 / d20**.

## What the TUI shows

Same simulation; the bars are coloured by σ-distance from the mean:

- **green** — within ±1σ (≈68% of mass)
- **cyan** — within ±2σ (≈95%)
- **yellow** — within ±3σ
- **red** — beyond 3σ (the tails)

Markers point to μ, μ-σ, and μ+σ. The shape hint at the top tells you which CLT regime you're in.

Bindings: **Enter** to recompute, **Ctrl+Q** to quit.

## API

```python
from million_dice import simulate, normal_pdf

# Roll 2d6 a million times
result = simulate(num_dice=2, num_rolls=1_000_000, sides=6)

result['mean']             # ~7.0
result['std']              # ~2.415
result['counts']           # {2: 27778, 3: 55556, ..., 12: 27778}
result['theoretical_mean'] # 7.0 exactly
result['theoretical_std']  # ~2.415
result['sums']             # raw NumPy array, shape (num_rolls,)
```

## Why NumPy

```python
sums = rng.integers(1, sides + 1,
                    size=(num_rolls, num_dice),
                    dtype=np.int64).sum(axis=1)
```

That single line generates the entire `num_rolls × num_dice` matrix of rolls and reduces along the dice axis — for 1M rolls of 5d6 (5M random integers) it runs in well under a second. A pure-Python double loop would take minutes.

## Convergence notes

Monte Carlo error scales as **O(1/√rolls)**:

- 1k rolls: ~3% relative error on σ
- 100k rolls: ~0.3% relative error
- 10M rolls: ~0.03% relative error

The empirical histogram visibly hugs the orange Normal curve at high roll counts and visibly wobbles at low ones — that's the CLT and the LLN both demonstrating themselves at once.

## Edge cases

- **N=1** is **uniform**, not normal — the CLT needs N to grow.
- **Loaded dice** (non-uniform) still converge to a Normal by the CLT, just to a different μ/σ. The simulator here uses a fair die.
- Bar chart down-samples to ≤30 bins for large N (e.g. 10d20 has 191 possible sums).
