"""Hex Grid — generate hexagonal honeycomb-pattern ASCII grids.

A "hex grid" of `rows` × `cols` hex cells rendered in ASCII using only
slashes, backslashes, underscores and spaces. Adjacent hexes share their
slanted edges so the output forms a clean honeycomb tiling like:

     _____       _____
    /     \\_____/     \\_____
    \\_____/     \\_____/     \\
    /     \\_____/     \\_____/
    \\_____/     \\_____/     \\

Each hex cell is 7 characters wide and 4 character-rows tall. Adjacent
hex columns are offset vertically by 1 character row (every odd column
sits one row lower than its even neighbours).

Pure functions:
    render(rows, cols)          -> str   honeycomb of plain hexes
    render(rows, cols, labels)  -> str   honeycomb with a 5-char label
                                         centred inside each cell
    coordinate_overlay(rows, cols, system) -> dict[(r, c), str]
        Build a label dict for axial / cube / offset coordinate systems
        — pass the dict as `labels` to embed coordinates inside cells.
    to_svg(rows, cols, labels=None) -> str
        Same grid as a standalone SVG document with crisp vector hexes.

Run as a CLI:
    uv run python hex_grid/hex_grid.py                 # default 3 x 5
    uv run python hex_grid/hex_grid.py 4 6
    uv run python hex_grid/hex_grid.py 4 6 axial       # axial coords
    uv run python hex_grid/hex_grid.py 4 6 cube        # cube coords
    uv run python hex_grid/hex_grid.py 4 6 offset      # offset coords
    uv run python hex_grid/hex_grid.py 4 6 plain svg   # write hex.svg
"""
from __future__ import annotations

import math
import sys
from typing import Iterable, Mapping

# Each hex cell is HEX_W chars wide (sharing its left/right edges with
# its neighbour, so the horizontal stride is HEX_STRIDE).
HEX_W = 7
HEX_STRIDE = 6
LABEL_WIDTH = 5  # characters available between '/' and '\' on the mid row

# Coordinate-system labels supported by `coordinate_overlay`.
COORD_SYSTEMS = ('axial', 'cube', 'offset')


def _validate(rows: int, cols: int) -> tuple[int, int]:
    if not isinstance(rows, int) or not isinstance(cols, int):
        raise TypeError('rows and cols must be int')
    if rows < 1 or cols < 1:
        raise ValueError(f'rows and cols must be >= 1, got {rows}, {cols}')
    return rows, cols


def _fit_label(label: str) -> str:
    """Trim/centre `label` into exactly LABEL_WIDTH characters."""
    if len(label) > LABEL_WIDTH:
        label = label[:LABEL_WIDTH]
    return label.center(LABEL_WIDTH)


def render(rows: int, cols: int,
           labels: Mapping[tuple[int, int], str] | None = None) -> str:
    """Render a honeycomb of `rows` × `cols` hex cells as ASCII art.

    `labels` is an optional mapping `{(row, col): "ABCDE"}` — when given,
    the value is centred (and trimmed to 5 chars) inside the matching
    hex cell. Missing entries render as blank cells.

    Output never has trailing whitespace on any line.
    """
    rows, cols = _validate(rows, cols)

    height = 2 * rows + 1
    width = cols * HEX_STRIDE + 1
    grid: list[list[str]] = [[' '] * width for _ in range(height)]

    def stamp_top(line: int, c: int) -> None:
        # Five underscores at chars c*6+1 .. c*6+5
        for i in range(1, 6):
            grid[line][c * HEX_STRIDE + i] = '_'

    def stamp_mid(line: int, c: int, label: str | None) -> None:
        # '/' at left edge, '\' at right edge, optional label between
        grid[line][c * HEX_STRIDE] = '/'
        if c * HEX_STRIDE + HEX_STRIDE < width:
            grid[line][c * HEX_STRIDE + HEX_STRIDE] = '\\'
        if label is not None:
            text = _fit_label(label)
            for i, ch in enumerate(text):
                grid[line][c * HEX_STRIDE + 1 + i] = ch

    def stamp_bot(line: int, c: int) -> None:
        # '\' '_____' '/' bottom cap
        grid[line][c * HEX_STRIDE] = '\\'
        for i in range(1, 6):
            grid[line][c * HEX_STRIDE + i] = '_'
        if c * HEX_STRIDE + HEX_STRIDE < width:
            grid[line][c * HEX_STRIDE + HEX_STRIDE] = '/'

    for r in range(rows):
        for c in range(cols):
            # Even cols start at the very top; odd cols are offset down 1
            top_line = 2 * r if c % 2 == 0 else 2 * r + 1
            mid_line = top_line + 1
            bot_line = top_line + 2
            label = labels.get((r, c)) if labels is not None else None

            if 0 <= top_line < height:
                stamp_top(top_line, c)
            if 0 <= mid_line < height:
                stamp_mid(mid_line, c, label)
            if 0 <= bot_line < height:
                stamp_bot(bot_line, c)

    return '\n'.join(''.join(row).rstrip() for row in grid)


# ------------------------------------------------------------------ TWIST
# Coordinate-system overlay: compute per-cell labels for the three common
# hex coordinate systems, then pass the result to `render(..., labels=)`.

def coordinate_overlay(rows: int, cols: int,
                       system: str = 'axial') -> dict[tuple[int, int], str]:
    """Return a `{(row, col): "label"}` dict for `system`.

    Conventions follow Red Blob Games' "Hexagonal Grids" tutorial:
        - offset:  printed as `r,c`     (row,col, "odd-q" offset)
        - axial:   printed as `q,r`     (q = col, r = row - col//2)
        - cube:    printed as `x,y,z`   constraint x+y+z = 0

    Labels are pre-trimmed to <= 5 chars so every cell renders cleanly.
    """
    rows, cols = _validate(rows, cols)
    if system not in COORD_SYSTEMS:
        raise ValueError(
            f'system must be one of {COORD_SYSTEMS}, got {system!r}')

    out: dict[tuple[int, int], str] = {}
    for r in range(rows):
        for c in range(cols):
            if system == 'offset':
                out[(r, c)] = _fit_label(f'{r},{c}')
            elif system == 'axial':
                q = c
                r_ax = r - (c // 2)
                out[(r, c)] = _fit_label(f'{q},{r_ax}')
            else:  # cube
                x = c
                z = r - (c // 2)
                y = -x - z
                # Cube coords are 3 numbers — squeeze into 5 chars by
                # showing each axis with 1-2 digit precision.
                label = f'{x}{_sign(y)}{_sign(z)}'
                out[(r, c)] = _fit_label(label)
    return out


def _sign(n: int) -> str:
    return f'+{n}' if n >= 0 else str(n)


# -------------------------------------------------------------- SVG export
# Optional vector-graphics export — same hex grid, crisp pointy-top hexes.

def to_svg(rows: int, cols: int,
           labels: Mapping[tuple[int, int], str] | None = None,
           hex_radius: float = 26.0,
           stroke: str = '#38bdf8',
           fill: str = '#0f172a',
           bg: str = '#020617',
           text_color: str = '#f8fafc') -> str:
    """Return a standalone SVG document drawing the same honeycomb.

    Hexes are flat-top so `cols` and `rows` map to columns and rows of
    cells. Coordinate labels (if provided) are drawn at each cell centre.
    """
    rows, cols = _validate(rows, cols)

    # Flat-top hex geometry: width = 2r, height = sqrt(3)*r
    r = hex_radius
    hex_w = 2 * r
    hex_h = math.sqrt(3) * r
    x_step = 1.5 * r           # horizontal distance between centres
    y_step = hex_h             # vertical distance between centres

    margin = r
    svg_w = margin * 2 + (cols - 1) * x_step + hex_w
    svg_h = margin * 2 + rows * y_step + hex_h / 2

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{svg_w:.1f}" height="{svg_h:.1f}" '
        f'viewBox="0 0 {svg_w:.1f} {svg_h:.1f}">',
        f'<rect width="100%" height="100%" fill="{bg}"/>',
        f'<g fill="{fill}" stroke="{stroke}" stroke-width="1.5" '
        f'stroke-linejoin="round">',
    ]

    text_parts: list[str] = []

    for row in range(rows):
        for col in range(cols):
            cx = margin + r + col * x_step
            cy = margin + hex_h / 2 + row * y_step
            if col % 2 == 1:
                cy += hex_h / 2
            points = _flat_top_hex_points(cx, cy, r)
            pts_str = ' '.join(f'{x:.1f},{y:.1f}' for x, y in points)
            parts.append(f'<polygon points="{pts_str}"/>')

            if labels is not None and (row, col) in labels:
                label = labels[(row, col)].strip()
                if label:
                    text_parts.append(
                        f'<text x="{cx:.1f}" y="{cy + 4:.1f}" '
                        f'fill="{text_color}" font-family="Consolas,monospace"'
                        f' font-size="{r * 0.45:.1f}" text-anchor="middle">'
                        f'{_xml_escape(label)}</text>'
                    )

    parts.append('</g>')
    parts.extend(text_parts)
    parts.append('</svg>')
    return '\n'.join(parts)


def _flat_top_hex_points(cx: float, cy: float,
                         r: float) -> list[tuple[float, float]]:
    """Return six (x, y) corners of a flat-top hexagon."""
    pts: list[tuple[float, float]] = []
    for i in range(6):
        angle = math.pi / 3 * i  # 0, 60, 120, ... degrees
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def _xml_escape(s: str) -> str:
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;'))


# ---------------------------------------------------------------------- CLI

def main(argv: Iterable[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if args and args[0] in {'-h', '--help', 'help'}:
        print(__doc__)
        return 0

    rows = 3
    cols = 5
    overlay: str | None = None
    write_svg = False
    svg_path = 'hex.svg'

    try:
        if len(args) >= 2:
            rows = int(args[0])
            cols = int(args[1])
        if len(args) >= 3:
            overlay = args[2].lower()
            if overlay == 'plain':
                overlay = None
            elif overlay not in COORD_SYSTEMS:
                print(f"unknown overlay {args[2]!r}; expected one of "
                      f"{('plain',) + COORD_SYSTEMS}", file=sys.stderr)
                return 2
        if len(args) >= 4 and args[3].lower() == 'svg':
            write_svg = True
        if len(args) >= 5:
            svg_path = args[4]
    except ValueError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2

    labels = (coordinate_overlay(rows, cols, overlay)
              if overlay is not None else None)

    print(render(rows, cols, labels))

    if write_svg:
        svg = to_svg(rows, cols, labels)
        with open(svg_path, 'w', encoding='utf-8') as fh:
            fh.write(svg)
        print(f'\nWrote SVG to {svg_path}', file=sys.stderr)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
