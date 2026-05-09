# Factor Finder

Compute the divisors and prime factorization of an integer N, plus key
number-theory tags (prime / perfect / abundant / deficient) and the divisor
function values σ₀, σ₁, s, and φ.

| Version | File | Stack |
|---------|------|-------|
| CLI | `factor_finder.py` | stdlib (math, random) |
| Desktop GUI | `factor_finder_gui.py` | CustomTkinter + matplotlib |
| Terminal UI | `factor_finder_tui.py` | Textual |

## Run

```bash
# CLI — pass N on the command line, or it will prompt
uv run python factor_finder/factor_finder.py 360
uv run python factor_finder/factor_finder.py

# Desktop GUI — entry box, Compute button, embedded bar chart
uv run python factor_finder/factor_finder_gui.py

# Terminal UI — Enter to compute, Ctrl+P prime-only, Ctrl+Q quit
uv run python factor_finder/factor_finder_tui.py
```

## What it shows

- **All divisors** of N, in ascending order. Enumerated via the sqrt-trick:
  iterate `i` from 1 to √N, pair each `i` that divides N with `N // i`.
  Time O(√N), space O(d(N)).
- **Prime factorization**, rendered with Unicode superscripts (e.g.
  `360 = 2³ × 3² × 5`). Trial division by small primes up to 1000 is
  followed by Miller-Rabin and Pollard's rho for big residues.
- **Classification chip** — prime, perfect, abundant, or deficient based
  on the aliquot sum s(N) = σ₁(N) - N.
- **Divisor-function values** — σ₀ (count), σ₁ (sum), s (aliquot sum),
  φ (Euler's totient), all derived directly from the prime factorization.
- **Bar chart** (GUI only) — multiplicities of each prime factor, with
  the exponent printed above each bar.

## API

`factor_finder.py` exports pure functions used by the GUI and TUI:

| Function | Returns |
|----------|---------|
| `factors(n)` | sorted list of divisors |
| `prime_factorization(n)` | `{prime: exponent}` |
| `is_prime(n)` | Miller-Rabin (deterministic for 64-bit N) |
| `divisor_count(n)` | σ₀(N) |
| `divisor_sum(n)` | σ₁(N) |
| `proper_divisor_sum(n)` | s(N) — aliquot sum |
| `euler_totient(n)` | φ(N) |
| `classify(n)` | `'prime' \| 'perfect' \| 'abundant' \| 'deficient'` |
| `pretty_factorization(pf)` | `'2³ × 3²'` |

## Notes

- The Miller-Rabin witness set `(2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)`
  is deterministic for every N < 3.3 × 10²⁴, which more than covers any
  64-bit input.
- Pollard's rho (Brent's variant) is the fallback for residues that survive
  small-prime trial division but are still composite.
- For very large N the GUI/TUI suppresses the literal divisor list once
  N > 5,000,000 (σ₀ is still computed from the factorization).
