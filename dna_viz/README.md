# DNA Visualization

Animate a rotating DNA double helix in ASCII art. Two anti-parallel sine-wave
strands wind around each other, linked by complementary base-pair rungs:
**A↔T** and **C↔G**. Bases are color-coded (A red, T orange, C blue, G green).

**Twist:** includes a built-in genome sample sequence and a transcription mode
that replaces the second strand with the mRNA complement (T→U).

## Files

| File | Description |
|------|-------------|
| `dna_viz.py` | Core logic + CLI |
| `dna_viz_gui.py` | CustomTkinter GUI with speed slider |
| `dna_viz_tui.py` | Textual TUI |

## Run

```bash
# CLI
uv run python dna_viz/dna_viz.py
uv run python dna_viz/dna_viz.py --transcribe   # DNA → mRNA
uv run python dna_viz/dna_viz.py --genome        # use genome sample

# GUI
uv run python dna_viz/dna_viz_gui.py

# TUI
uv run python dna_viz/dna_viz_tui.py
```

## CLI options

| Flag | Default | Description |
|------|---------|-------------|
| `--width N` | terminal | Display width in chars |
| `--height N` | terminal - 4 | Display height in rows |
| `--speed F` | 0.12 | Phase increment per frame |
| `--fps F` | 15 | Frames per second |
| `--seed N` | random | RNG seed |
| `--no-color` | off | Disable ANSI colors |
| `--transcribe` | off | Show DNA → mRNA second strand |
| `--genome` | off | Use built-in genome sample |

## TUI bindings

| Key | Action |
|-----|--------|
| Space | Pause / resume |
| `+` / `-` | Speed up / slow down |
| `t` | Toggle transcription mode |
| `g` | Toggle genome sequence |
| Ctrl+Q | Quit |

## Key concepts

- **Double helix geometry:** two sine waves offset by π radians (`sin(θ)` and
  `sin(θ + π)`), so the strands are always on opposite sides of the axis.
- **Complementary pairing:** A↔T, C↔G (or A↔U in transcription mode).
- **Transcription:** DNA → mRNA replaces T with U on the template strand.
- **Genome sample:** a short excerpt of Homo sapiens chromosome 1 drives
  the base sequence instead of random choice.
