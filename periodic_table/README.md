# Periodic Table

An interactive reference for all 118 chemical elements, with three frontends sharing one pure-Python data core.

| Version | File | Stack |
|---------|------|-------|
| CLI | `periodic_table.py` | stdlib (ANSI colors when TTY) |
| Desktop GUI | `periodic_table_gui.py` | CustomTkinter |
| Terminal UI | `periodic_table_tui.py` | Textual |

## What it shows

For every element: atomic number, symbol, full name, standard atomic weight, category (alkali, alkaline-earth, transition, post-transition, metalloid, nonmetal, halogen, noble-gas, lanthanide, actinide, unknown), period, group, and condensed electron configuration.

The layout matches the standard periodic-table grid - 7 main rows + 18 columns, plus the lanthanide and actinide series rendered as their own rows below the main block (the modern IUPAC convention).

## Run

```bash
# CLI - colored grid in your terminal
uv run python periodic_table/periodic_table.py

# Look up a single element (number, symbol, or name)
uv run python periodic_table/periodic_table.py Fe
uv run python periodic_table/periodic_table.py 79
uv run python periodic_table/periodic_table.py oganesson

# Filter by category, name fragment, etc.
uv run python periodic_table/periodic_table.py --search noble
uv run python periodic_table/periodic_table.py -s halogen

# 10-round identification quiz (the twist)
uv run python periodic_table/periodic_table.py --quiz

# Desktop GUI - color-coded clickable tiles + details panel
uv run python periodic_table/periodic_table_gui.py

# Terminal UI - arrow-key navigation with details panel
uv run python periodic_table/periodic_table_tui.py
```

## GUI controls

- **Click any tile** to select; the right-hand panel shows full details.
- **Search box** filters tiles in place - non-matching tiles dim to slate. A direct hit (number / exact symbol / exact name) auto-selects.
- Tile color encodes category; legend below the table.

## TUI controls

| Key | Action |
|-----|--------|
| arrow keys | Move cursor between tiles (skips empty cells) |
| Enter | Pin the current selection |
| `/` | Open search box; type, Enter to jump, Esc to cancel |
| Ctrl+Q | Quit |

## Twist - quiz mode

`--quiz` shows you `#26 (period 4, transition metal) - what element?` and accepts the symbol or full name. 10 rounds, scored at the end. Type `q` mid-quiz to bail. It's a fast way to drill recall before a chemistry exam.

## Architecture

`periodic_table.py` is the shared core; everything else imports from it:

| Symbol | Purpose |
|--------|---------|
| `Element` | Frozen dataclass: `number`, `symbol`, `name`, `weight`, `category`, `group`, `period`, `config` |
| `ELEMENTS` | List of all 118 in atomic-number order |
| `CATEGORIES` | `{key: human-readable label}` for the 11 category buckets |
| `lookup(query)` | Pure: accepts int / digit string / symbol / full name; raises `KeyError` |
| `search(term)` | Substring match across symbol, name, and category |
| `build_grid()` | 10x18 list-of-lists with elements placed at their (period, group); lanthanides on row 9, actinides on row 10 |
| `grid_position(e)` | `(row, col)` cell for an element - used to drive both UIs |
| `render_grid(color)` | ASCII / ANSI grid for the CLI |
| `quiz()` | Identification game |

The pure-data core means the CLI, GUI, and TUI all show exactly the same information - changes to the data flow everywhere automatically.

## Data sources

Atomic weights are IUPAC 2021 standard atomic weights, rounded to 4-5 significant figures. Elements without a stable isotope (Tc, Pm, Po, At, Rn, Fr, Ra, and all transuranics) use the most-stable mass number (the IUPAC convention for radioactive elements). Categories follow the modern IUPAC + common-textbook scheme. All data is in the public domain.

## Notes

- **Group 0 = f-block.** The lanthanides (57-70) and actinides (89-102) are stored with `group=0` because they don't fit a single group on the standard table. Lutetium (71) and Lawrencium (103) are placed in group 3 by IUPAC, matching their position on the rendered grid.
- **Hydrogen lives in group 1** structurally, even though it's a nonmetal. This is the conventional rendering.
- **Helium in group 18** - electron configuration is `1s2`, but it sits with the noble gases by chemical behavior.
- The CLI auto-detects whether stdout is a TTY before emitting ANSI escape codes; pipe to `cat` or pass `--no-color` to get plain output.
