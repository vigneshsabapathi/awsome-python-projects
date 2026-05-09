# Collatz Sequence

The hailstone numbers. Pick any positive integer `n`, then repeatedly apply

```
n -> n / 2     if n is even
n -> 3n + 1    if n is odd
```

and you (apparently) always land on 1. The Collatz conjecture (Lothar Collatz, 1937) is one of the simplest unsolved problems in mathematics — verified by computer up to ~`2^68`, but never proved.

| Version | File | Stack |
|---------|------|-------|
| CLI | `collatz.py` | stdlib |
| Desktop GUI | `collatz_gui.py` | CustomTkinter + matplotlib |
| Terminal UI | `collatz_tui.py` | Textual |

## Run

```bash
# CLI - prompt for n, print sequence + peak + stopping time
uv run python collatz/collatz.py

# Desktop GUI - sequence chart (linear/log toggle) + stopping-time scatter
uv run python collatz/collatz_gui.py

# Terminal UI - log-scale unicode bar chart, one row per step
uv run python collatz/collatz_tui.py
```

## What you see

### GUI
- **Top chart:** the hailstone path for the current `n` (value vs step index). The peak is marked. Toggle linear / log scale — log makes paths like `n = 27` (peak 9232) legible alongside the long tail of small values.
- **Bottom chart:** stopping-time scatter for `n = 1..N`, with `N` controlled by a slider (50 to 5000). The chaotic banded structure — clusters of `n` that all halt in the same number of steps, separated by sudden vertical jumps — is the visual fingerprint of the conjecture.
- **Side panel:** the full sequence as a wrapped text list.

### TUI
- One row per step, rendered as a unicode bar with eighth-block resolution (`▏▎▍▌▋▊▉█`).
- Bars are scaled in **log space** so that small values still draw a visible sliver next to a 9000-tall peak.
- Color cues: cyan for ordinary values, yellow at the peak, green at the terminal `1`.
- `Ctrl+R` rerolls a random `n` in `[1, 1_000_000)`. `Ctrl+Q` quits.

## Architecture

`collatz.py` holds the pure logic:

- `collatz_sequence(n) -> list[int]` — full hailstone path, ending at 1.
- `stopping_time(n) -> int` — number of steps to 1, **memoized via `functools.lru_cache`** so batch calls (the GUI's scatter sweep) reuse all intermediate paths.
- `max_value(n) -> int` — peak on the path.
- `stopping_times_up_to(limit)` — convenience batch helper.

The GUI imports those four; the TUI imports only `collatz_sequence`. Both UIs follow the same dark-Tailwind palette as the other projects in this repo.

## Reference values (sanity checks)

| n | steps | peak |
|---|-------|------|
| 1 | 0 | 1 |
| 6 | 8 | 16 |
| 7 | 16 | 52 |
| 27 | 111 | 9 232 |
| 871 | 178 | 190 996 |
| 6 171 | 261 | 975 400 |

`n = 27` is the classic demo: a tiny start that climbs to nearly 10 000 before plummeting.

## Notes

- **Memoization matters.** Computing `stopping_time(n)` for `n = 1..5000` without caching does ~hundreds of thousands of redundant divisions. With the `lru_cache`, every intermediate hop is recorded once and reused forever.
- **No upper bound is proven.** The longest stopping time below `N` (OEIS [A006877](https://oeis.org/A006877)) grows without any known formula. If you find an `n` whose path never reaches 1, mathematicians would like a word.
- **Why log-scale the bars?** Hailstone peaks are often 100x to 1000x the floor. On a linear scale almost every step looks like a flatline; log spreads the structure across the chart.
