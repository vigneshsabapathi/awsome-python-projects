# Water Bucket Puzzle

The classic Die Hard 3 jug problem: given two buckets of capacities A and B,
measure exactly C liters using only **fill**, **empty**, and **pour** operations.
Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `water_bucket.py` | stdlib |
| Modern desktop GUI | `water_bucket_gui.py` | CustomTkinter |
| Modern terminal UI | `water_bucket_tui.py` | Textual |

## The Puzzle

You have two buckets (e.g. 3 L and 5 L) and need to measure an exact amount
(e.g. 4 L). There is no measurement markings — you can only fill a bucket to
the brim, empty it completely, or pour from one bucket into the other until
the source is empty or the destination is full.

**Solvability rule (Bezout's Identity):** the target C is reachable if and
only if `C ≤ max(A, B)` and `gcd(A, B)` divides `C`.

## Run

```bash
# CLI
uv run python water_bucket/water_bucket.py

# Desktop GUI (CustomTkinter)
uv run python water_bucket/water_bucket_gui.py

# Terminal UI (Textual)
uv run python water_bucket/water_bucket_tui.py
```

## GUI Features

- Two animated buckets on a canvas that fill/drain smoothly.
- A dashed target line shows the goal level inside each bucket.
- **Solve** button animates the BFS-shortest sequence step by step.
- **Why solvable?** panel explains the gcd / Bezout constraint in plain text.
- Editable capacity and target fields — change the puzzle on the fly.

## TUI Features (Textual)

- ASCII-art buckets with `█` bars showing the current water level and a `◄`
  target marker at the goal fill line.
- **Keys 1–6** trigger the six operations (fill A/B, empty A/B, pour A→B,
  pour B→A).
- **S** auto-plays the BFS solution with a short delay between steps.
- **R** resets both buckets to empty.
- **Ctrl+Q** quits.

## Architecture

The CLI module (`water_bucket.py`) holds all shared logic. Both GUIs import:

- `Buckets(a_cap, b_cap)` — stateful container; `.apply(op)` dispatches any
  of the six string op names.
- `solve(a_cap, b_cap, target)` — BFS; returns the shortest list of op names,
  or `None` if unsolvable.
- `is_solvable(a_cap, b_cap, target)` — fast gcd check.
- `explain_solvability(...)` — human-readable Bezout explanation string.
- `OP_LABEL` — dict mapping op names to display strings.

## Notes

- The BFS explores at most `(A+1) * (B+1)` states, so it is always fast for
  reasonable bucket sizes.
- The six operations are deterministic (no randomness): fill to capacity,
  empty to zero, or transfer until one bucket is full or the other is empty.
- The puzzle is unsolvable when `gcd(A, B)` does not divide C (e.g. A=4, B=6,
  target=3 is impossible since gcd(4,6)=2 and 2 does not divide 3).
