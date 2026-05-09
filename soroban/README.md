# Soroban

Render integers as a **Japanese soroban** (abacus). Each digit becomes a
column with one **5-bead** in the top deck and four **1-beads** in the
bottom deck, separated by the *reckoning bar*. Active beads (those touching
the bar) sum to the digit in that column.

| Version | File | Stack |
|---------|------|-------|
| CLI / animation | `soroban.py` | stdlib |
| Desktop GUI | `soroban_gui.py` | CustomTkinter + tk.Canvas |
| Terminal UI | `soroban_tui.py` | Textual |

## How a soroban encodes a digit

Each column has 1 heaven bead (worth 5) and 4 earth beads (worth 1). A bead
is **active** when it's pushed against the reckoning bar in the middle:

```
digit = (top bead lowered ? 5 : 0) + (number of bottom beads raised)
```

```
+-+   <- top frame
|O|   ^ heaven bead resting (digit < 5)
 |    |
+=+   <- reckoning bar
 |    v
|O|   <- earth bead raised (touches bar)
|O|   <- earth bead raised
 |    <- gap (the slot left empty as beads slide)
|O|   ^ earth beads resting at bottom (digit & 4 unset)
|O|   |
+-+   <- bottom frame
```

So `9` = top bead lowered + all 4 earth beads raised; `0` = top bead at top,
all 4 earth beads at bottom.

## Run

```bash
# CLI: render a number
uv run python soroban/soroban.py 1234

# Animation: bead-by-bead addition (the "twist")
uv run python soroban/soroban.py --animate 123 456

# Round-trip: render then parse
uv run python soroban/soroban.py 42 --roundtrip

# Desktop GUI (CustomTkinter on tk.Canvas)
uv run python soroban/soroban_gui.py

# Terminal UI (Textual)
uv run python soroban/soroban_tui.py
```

In the GUI:
- **Click a bead** to slide it toward / away from the bar.
- **Type a number** in the entry box — beads update live.
- **+1 / +10** buttons step the value.

In the TUI:
- Type a number, **Enter** to render it.
- Type `+N` then **Enter** (or press **Ctrl+A**) to animate addition.
- **Ctrl+L** clear, **Ctrl+Q** quit.

## Architecture

`soroban.py` is the pure module — no UI, just functions:

- `render(n, columns=8) -> str` — ASCII soroban for non-negative integer `n`.
- `parse(rendered) -> int` — inverse: read the digits back out.
- `animate_addition(a, b, ...)` — the twist, step-by-step bead movement.

Both UIs `from soroban import render, parse, ...` so the rendering logic
lives in exactly one place.

## Notes

- The bottom deck has **5 slots** for **4 beads** so there's always a
  visible gap that moves as beads slide. Without that gap, digit 0 and
  digit 4 would render identically (all 4 beads stacked).
- Decimal places run **left → right** (most significant → least), so
  reading a soroban is the same direction as reading the number itself.
- The CLI footer shows place values (`1, 10, 100, 1k, ...`) and the
  decoded digit per column for debugging / teaching.
- `parse(render(n)) == n` for every `0 ≤ n < 10**columns`.
