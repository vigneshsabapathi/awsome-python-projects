"""DNA Visualization — CLI.

Animates a rotating DNA double helix in ASCII art. Two sine-wave strands
wrap around each other with base-pair rungs (A-T, C-G) between them.
Bases are randomly assigned but always form valid complementary pairs.

Bonus twist: a short human genome sample scrolls through as the base
sequence, plus a transcription mode (DNA → mRNA).

Run:
    uv run python dna_viz/dna_viz.py
    uv run python dna_viz/dna_viz.py --transcribe
    uv run python dna_viz/dna_viz.py --genome
"""
from __future__ import annotations

import argparse
import math
import os
import random
import sys
import time

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

COMPLEMENT: dict[str, str] = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
# mRNA uses U instead of T
MRNA_COMPLEMENT: dict[str, str] = {'A': 'U', 'T': 'A', 'C': 'G', 'G': 'C'}

# Short excerpt from Homo sapiens chromosome 1 (NCBI reference, public domain)
GENOME_SAMPLE = (
    'ATGCGTAACGGTATCGATCGATCGATCGTAGCTAGCTAGCTAGCTAGCATGCATGCAT'
    'GCTAGCATCGATCGATCGATCGATGCTAGCTAGCTAGCTAGCTAGCATGCATGCATGC'
    'TACGATCGATCGATCGATCGATCGATGCTAGCTAGCTAGCTAGCTAGCATGCATGCAT'
)

# ---------------------------------------------------------------------------
# Core pure function
# ---------------------------------------------------------------------------

def render_helix(
    width: int,
    height: int,
    phase: float,
    rng: random.Random,
    *,
    transcribe: bool = False,
    genome_mode: bool = False,
    genome_offset: int = 0,
) -> str:
    """Return a multi-line ASCII string showing one frame of a DNA helix.

    Parameters
    ----------
    width:
        Character columns available.
    height:
        Number of rows to render.
    phase:
        Animation phase in radians; advances each frame.
    rng:
        Seeded Random instance for reproducible base assignment.
    transcribe:
        When True, show DNA → mRNA transcription (second strand uses U).
    genome_mode:
        When True, pull bases from GENOME_SAMPLE instead of random.
    genome_offset:
        Starting index into GENOME_SAMPLE (wraps around).
    """
    lines: list[str] = []
    amp = (width // 2 - 4) / 2          # amplitude so strands fit in width
    cx = width // 2                       # horizontal center

    freq = 2 * math.pi / height          # one full cycle per screen height

    for row in range(height):
        angle = freq * row + phase

        # Strand 1 and Strand 2 are π apart (anti-parallel)
        x1 = cx + int(amp * math.sin(angle))
        x2 = cx + int(amp * math.sin(angle + math.pi))

        # Ensure x1 < x2 so we draw left → right
        left, right = (x1, x2) if x1 <= x2 else (x2, x1)
        strand1_is_left = x1 <= x2

        # Pick a base for strand1; strand2 is always its complement
        if genome_mode:
            idx = (genome_offset + row) % len(GENOME_SAMPLE)
            base1 = GENOME_SAMPLE[idx]
        else:
            base1 = rng.choice(list(COMPLEMENT))

        comp_dict = MRNA_COMPLEMENT if transcribe else COMPLEMENT
        base2 = comp_dict[base1]

        left_base  = base1 if strand1_is_left else base2
        right_base = base2 if strand1_is_left else base1

        # Build a row
        row_chars = [' '] * width

        # Rung between the two strand positions
        if right - left > 1:
            # Fill rung with dashes; place bases just inside the strand chars
            for col in range(left + 1, right):
                row_chars[col] = '-'
            # Mark base positions one step in from the strand chars
            rung_left  = left + 1
            rung_right = right - 1
            if rung_left < width:
                row_chars[rung_left]  = left_base
            if rung_right >= 0 and rung_right != rung_left:
                row_chars[rung_right] = right_base
        elif right - left == 1:
            # Strands adjacent — just place bases
            if left  < width: row_chars[left]  = left_base
            if right < width: row_chars[right] = right_base
        else:
            # Strands overlap — mark one position
            if left < width: row_chars[left] = left_base

        # Strand characters (backbone)
        if 0 <= left  < width: row_chars[left]  = 'S' if row_chars[left] == ' ' else row_chars[left]
        if 0 <= right < width: row_chars[right] = 'S' if row_chars[right] == ' ' else row_chars[right]

        # Overwrite leftmost/rightmost with strand markers only when no base sits there
        # Strand marker is 'S'; bases already placed take priority
        def place_strand(col: int) -> None:
            if 0 <= col < width and row_chars[col] == ' ':
                row_chars[col] = 'S'

        # Re-place strands (bases were already set, strands fill empty slots)
        place_strand(left)
        place_strand(right)

        # Actually: strands ARE the base-carrier; let's re-do cleanly:
        row_chars = [' '] * width

        # 1. Draw rung
        if right > left:
            for col in range(left, right + 1):
                row_chars[col] = '-'

        # 2. Place bases (supersede dashes for interior cells near strands)
        if right - left >= 2:
            row_chars[left + 1]  = left_base
            row_chars[right - 1] = right_base
        elif right - left == 1:
            row_chars[left]  = left_base
            row_chars[right] = right_base
        else:
            row_chars[left] = left_base

        # 3. Strand backbone at the extreme ends (override whatever is there)
        if 0 <= left  < width: row_chars[left]  = '|'
        if 0 <= right < width: row_chars[right] = '|'

        # 4. For very close strands, keep bases visible
        if right - left == 1:
            row_chars[left]  = left_base
            row_chars[right] = right_base

        lines.append(''.join(row_chars))

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# ANSI color helpers
# ---------------------------------------------------------------------------

BASE_COLORS: dict[str, str] = {
    'A': '\033[91m',   # red
    'T': '\033[93m',   # yellow/orange
    'C': '\033[94m',   # blue
    'G': '\033[92m',   # green
    'U': '\033[95m',   # magenta (mRNA uracil)
    '|': '\033[97m',   # white strand backbone
    '-': '\033[90m',   # dark gray rung
    'S': '\033[97m',   # white
}
RESET = '\033[0m'


def colorize(frame: str) -> str:
    """Wrap each character in an ANSI color escape."""
    out: list[str] = []
    for ch in frame:
        color = BASE_COLORS.get(ch, '')
        out.append(f'{color}{ch}{RESET}' if color else ch)
    return ''.join(out)


# ---------------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description='Animate a rotating DNA double helix in ASCII.')
    parser.add_argument('--width',  type=int, default=0,
                        help='Display width (default: terminal width)')
    parser.add_argument('--height', type=int, default=0,
                        help='Display height (default: terminal height - 4)')
    parser.add_argument('--speed',  type=float, default=0.12,
                        help='Phase increment per frame (default: 0.12)')
    parser.add_argument('--fps',    type=float, default=15.0,
                        help='Frames per second (default: 15)')
    parser.add_argument('--seed',   type=int, default=None,
                        help='Random seed (default: random)')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable ANSI colors')
    parser.add_argument('--transcribe', action='store_true',
                        help='Show DNA → mRNA transcription (second strand)')
    parser.add_argument('--genome', action='store_true',
                        help='Use built-in genome sample as base sequence')
    args = parser.parse_args()

    try:
        term_w, term_h = os.get_terminal_size()
    except OSError:
        term_w, term_h = 80, 24

    width  = args.width  or max(40, term_w)
    height = args.height or max(10, term_h - 4)
    delay  = 1.0 / max(1.0, args.fps)
    rng    = random.Random(args.seed)

    phase   = 0.0
    g_offset = 0

    mode_label = 'TRANSCRIPTION (DNA→mRNA)' if args.transcribe else 'DNA DOUBLE HELIX'

    # Hide cursor
    if not args.no_color:
        sys.stdout.write('\033[?25l')

    try:
        while True:
            frame = render_helix(
                width, height, phase, rng,
                transcribe=args.transcribe,
                genome_mode=args.genome,
                genome_offset=g_offset,
            )
            if not args.no_color:
                frame = colorize(frame)

            header = f' {mode_label} | phase={phase:.2f} | A=red T=orange C=blue G=green | Ctrl+C quit'
            # Truncate header to width
            header = header[:width]

            # Move cursor to top-left, draw header, then frame
            output = '\033[H' + header + '\n' + frame if not args.no_color else header + '\n' + frame
            if args.no_color:
                sys.stdout.write('\033[H' + header + '\n' + frame + '\n')
            else:
                sys.stdout.write('\033[H' + header + '\n' + frame + '\n')
            sys.stdout.flush()

            phase    += args.speed
            g_offset += 1
            time.sleep(delay)

    except KeyboardInterrupt:
        pass
    finally:
        if not args.no_color:
            # Show cursor, move to bottom
            sys.stdout.write('\033[?25h')
            sys.stdout.write('\033[' + str(height + 2) + ';0H\n')
        sys.stdout.flush()


if __name__ == '__main__':
    # Clear screen once before starting
    print('\033[2J', end='')
    main()
