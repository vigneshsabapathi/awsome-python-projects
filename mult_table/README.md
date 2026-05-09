# Multiplication Table

Render the classic 1..N × 1..N times table with proper alignment, headers, and unicode borders — plus a modular variant that exposes the symmetric patterns of the cyclic group **Z/MZ**. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `mult_table.py` | stdlib |
| Modern desktop GUI | `mult_table_gui.py` | CustomTkinter |
| Modern terminal UI | `mult_table_tui.py` | Textual |

## Run

```bash
# CLI — default 12x12
uv run python mult_table/mult_table.py

# CLI — pick N
uv run python mult_table/mult_table.py 10

# CLI — modular
uv run python mult_table/mult_table.py 12 --mod 7

# Desktop GUI (CustomTkinter)
uv run python mult_table/mult_table_gui.py

# Terminal UI (Textual)
uv run python mult_table/mult_table_tui.py
```

## CLI output

The CLI uses Unicode box-drawing characters with a heavy double rule separating the headers from the body, so columns line up cleanly:

```
╔═══╦═══╤═══╤═══╤═══╤═══╗
║   │ 1 │ 2 │ 3 │ 4 │ 5 ║
╠═══╬═══╪═══╪═══╪═══╪═══╣
║ 1 ║ 1 │ 2 │ 3 │ 4 │ 5 ║
╟───╫───┼───┼───┼───┼───╢
║ 2 ║ 2 │ 4 │ 6 │ 8 │10 ║
...
║ 5 ║ 5 │10 │15 │20 │25 ║
╚═══╩═══╧═══╧═══╧═══╧═══╝
```

> On Windows, set `PYTHONIOENCODING=utf-8` if the console mangles box characters.

## GUI / TUI

Both modern UIs draw the table as a colored heatmap. A 12-stop palette runs cool → warm; in the modular view, equal residues share a color, so cyclic symmetries become obvious at a glance.

| Control | GUI | TUI |
|---------|-----|-----|
| Change N | slider (2..30) | ↑ / ↓ |
| Toggle modular | switch | `m` |
| Adjust modulus | slider | `[` / `]` |
| Quit | window close | Ctrl+Q |

## The modular twist

`render_modular(n, m)` computes `(i × j) mod m` for `i, j ∈ {0, …, n-1}`. The resulting table is the multiplication table of the ring **Z/MZ**, and its appearance changes dramatically based on whether `M` is prime:

- **Mod prime** (e.g. `mod 7`, `mod 11`): every nonzero row is a permutation of `{1, …, M-1}` — the nonzero residues form a cyclic group under multiplication. Diagonal symmetry, no obvious blocks.
- **Mod composite** (e.g. `mod 12`, `mod 15`): rows of zero divisors hit `0` repeatedly. The non-units carve out visible diagonal stripes and "missing" residues.

This is **Z/MZ** as a multiplicative monoid, and it's the same structure that underlies modular arithmetic cryptography (RSA, Diffie-Hellman) and clock arithmetic.

## Architecture

`mult_table.py` is the pure-rendering core; both UIs import from it:

- `render(n)` — classic table, returns a unicode-bordered string
- `render_modular(n, mod)` — modular version with prime/composite annotation
- `_is_prime(m)` — small primality test, used to label moduli

The GUI and TUI define their own `heatmap_color` / `modular_color` helpers because they target different colorspaces (Tk hex vs Rich `rgb()`), but the math driving them is identical.
