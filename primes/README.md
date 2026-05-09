# Prime Numbers

Generate primes up to N (Sieve of Eratosthenes), test primality
deterministically (Miller-Rabin), find the next prime, and explore prime
structure with the **Ulam spiral** — primes lay down unexpected diagonal
streaks on the spiral grid.

| Version | File | Stack |
|---------|------|-------|
| CLI | `primes.py` | stdlib (math, argparse) |
| Desktop GUI | `primes_gui.py` | CustomTkinter + tk.Canvas |
| Terminal UI | `primes_tui.py` | Textual |

## Run

```bash
# CLI
uv run python primes/primes.py --up-to 100
uv run python primes/primes.py --test 2147483647        # is this prime?
uv run python primes/primes.py --nth 10001              # 10001st prime
uv run python primes/primes.py --segment 1000000 1000100
uv run python primes/primes.py --goldbach 100           # Goldbach pair

# Desktop GUI — slider, Ulam spiral, twin-prime highlight
uv run python primes/primes_gui.py

# Terminal UI — Enter recompute, Ctrl+U toggle Ulam, Ctrl+Q quit
uv run python primes/primes_tui.py
```

## What it shows

- **Sieve of Eratosthenes** — every prime `p <= n` in `O(n log log n)` time
  using a bytearray for cache-friendly marking.
- **Segmented sieve** — primes in `[low, high]` for huge ranges, using only
  `O(sqrt(high) + (high - low))` memory.
- **Miller-Rabin primality test** — deterministic for every 64-bit (in
  fact, every 80-bit) integer with the witness set
  `(2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)`.
- **Next / previous / k-th prime** — wheel-style stepping plus a
  Rosser-Schoenfeld bound for the k-th-prime sieve size.
- **Ulam spiral** (GUI/TUI) — integers spiraled outward from 1; primes
  cluster on diagonals, an open question in number theory.
- **Stats** — pi(N), largest prime, average and max prime gap, twin-prime
  count.

## API

`primes.py` exports pure functions used by the GUI and TUI:

| Function | Returns |
|----------|---------|
| `sieve(n)` | `list[int]` — primes <= n |
| `sieve_segmented(low, high)` | `list[int]` — primes in `[low, high]` |
| `is_prime(n)` | Miller-Rabin (deterministic for 64-bit n) |
| `next_prime(n)` / `prev_prime(n)` | next / previous prime |
| `nth_prime(k)` | k-th prime, 1-indexed (`nth_prime(1) == 2`) |
| `prime_pi(n)` | pi(n) — number of primes <= n |
| `prime_gaps(primes)` | list of consecutive gaps |
| `twin_primes(primes)` | list of `(p, p+2)` pairs |
| `goldbach_pair(n)` | `(p, q)` with `p + q == n`, or `None` |

## Notes

- The deterministic Miller-Rabin witness set is correct for every
  `n < 3.317 * 10^24`. For inputs above that bound the test stays
  probabilistic with negligible error.
- The sieve uses a `bytearray` plus slice-assignment (`is_p[start::step] = ...`)
  which is dramatically faster than a Python-level inner loop.
- The GUI redraws the Ulam spiral every time the slider moves; cells
  scale down to 2 px so structure remains visible at `N = 10000`.
- The TUI Ulam grid uses one-character glyphs (`#` prime, `*` twin
  prime, `.` composite, `1` for the unit) coloured with Tailwind-ish
  hexes for the dark theme.
