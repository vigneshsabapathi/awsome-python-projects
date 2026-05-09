# Fibonacci

Five algorithms, one sequence. Generate `F(n) = F(n-1) + F(n-2)` using iterative, naive recursive, memoized, matrix exponentiation, and Binet's closed-form approaches — and watch them race.

| Version | File | Stack |
|---------|------|-------|
| CLI | `fibonacci.py` | stdlib |
| Desktop GUI | `fibonacci_gui.py` | CustomTkinter + matplotlib |
| Terminal UI | `fibonacci_tui.py` | Textual |

## Algorithms

| Name | Time | Space | Exact? | Notes |
|------|------|-------|--------|-------|
| `iter` | O(n) | O(1) | yes | the workhorse |
| `recursive` | O(2^n) | O(n) stack | yes | teaching only — blocked for n > 35 |
| `memo` | O(n) | O(n) | yes | top-down DP via `lru_cache` |
| `matrix` | O(log n) | O(log n) | yes | matrix exponentiation by squaring |
| `binet` | O(1) | O(1) | **no** | float64 — diverges from exact ~n=70 |

## Run

```bash
# CLI — single value
uv run python fibonacci/fibonacci.py 30

# CLI — sequence
uv run python fibonacci/fibonacci.py 12 --sequence

# CLI — benchmark every algorithm
uv run python fibonacci/fibonacci.py 30 --bench

# Desktop GUI (CustomTkinter + embedded matplotlib)
uv run python fibonacci/fibonacci_gui.py

# Terminal UI (Textual)
uv run python fibonacci/fibonacci_tui.py
```

## GUI features

- Type N, choose algorithm from the dropdown, hit **Compute**.
- Embedded matplotlib chart of `F(k)` for `k = 1..N` with a **log y-scale toggle** (try N=80 with log on — the line is nearly straight, because Fibonacci growth is exponential).
- Reports `F(N)/F(N-1)` and the absolute error vs. phi (golden ratio) on a separate line — converges fast.
- **Benchmark all** checkbox runs every algorithm on the same N and shows times side-by-side, with the fastest highlighted.

## TUI shortcuts

- **Enter** — compute with the current algorithm.
- **Ctrl+A** — cycle algorithm (iter -> recursive -> memo -> matrix -> binet).
- **Ctrl+B** — benchmark every algorithm at the current N.
- **Ctrl+Q** — quit.

## Architecture

`fibonacci.py` holds the pure functions; the GUI and TUI both import them:

- `fib_iter(n)`, `fib_recursive(n)`, `fib_memo(n)`, `fib_matrix(n)`, `fib_binet(n)` — five F(n) implementations.
- `sequence_up_to(n)` — `[F(0), F(1), ..., F(n)]`.
- `compute(n, algorithm)` — dispatch by name, with a guard rail that refuses `recursive` for n > 35 (otherwise the call tree explodes).
- `benchmark(n)` — times every algorithm on the same N using `time.perf_counter`, returning `{algo: (value, seconds)}`.

The naive `fib_recursive` exists purely to teach the exponential blow-up that motivates memoization. `fib_matrix` uses the identity

```
[[1, 1],
 [1, 0]]^n  ==  [[F(n+1), F(n)],
                 [F(n),   F(n-1)]]
```

with squaring, so an n-bit exponent costs only O(log n) matrix multiplications.

## Notes

- All exact algorithms use Python bignums — `fib_iter(10000)` returns a 2,090-digit integer in milliseconds.
- `fib_binet` agrees with the others up to roughly **n = 70**; beyond that, float64 mantissa is too narrow to represent F(n) without rounding error. Try `--bench 75` and compare.
- The chart caps the plotted range at N=200 to keep the canvas responsive; the computed value is still exact for the chosen N.
