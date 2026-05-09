"""Diamonds — ASCII-art diamond pattern generator.

Pure functions:
    outlined(size)       -> str   single outlined diamond
    filled(size)         -> str   single solid-filled diamond
    row_of_diamonds(...) -> str   several diamonds side-by-side, baseline-aligned

The diamond is built from `/`, `\\`, `_` characters. Size N produces a diamond
that is `2*N` columns wide and `2*N` rows tall. Each line is space-padded on the
left so the shape stays centered.

Run as a CLI:
    uv run python diamonds/diamonds.py            # default demo
    uv run python diamonds/diamonds.py 6 outlined
    uv run python diamonds/diamonds.py 6 filled
    uv run python diamonds/diamonds.py row 1 2 3 4 5
"""
from __future__ import annotations

import sys


def _validate(size: int) -> int:
    if not isinstance(size, int):
        raise TypeError(f'size must be int, got {type(size).__name__}')
    if size < 0:
        raise ValueError(f'size must be >= 0, got {size}')
    return size


def outlined(size: int) -> str:
    """Return a multi-line string of an outlined diamond of given `size`.

    For size 0 the output is a single `_` character (a degenerate point).
    For size N the diamond spans 2*N rows and 2*N columns.

        outlined(3) ->
              /\\
             /  \\
            /    \\
            \\    /
             \\  /
              \\/
    """
    size = _validate(size)
    if size == 0:
        return ''
    width = size * 2
    lines: list[str] = []

    # Top half: rows 0 .. size-1
    for row in range(size):
        spaces = ' ' * (size - row - 1)
        inner = ' ' * (row * 2)
        lines.append(f'{spaces}/{inner}\\')

    # Bottom half: mirror of the top
    for row in range(size):
        spaces = ' ' * row
        inner = ' ' * ((size - row - 1) * 2)
        lines.append(f'{spaces}\\{inner}/')

    # Sanity: every line has total visible width <= 2*size
    assert all(len(line.rstrip()) <= width for line in lines)
    return '\n'.join(lines)


def filled(size: int) -> str:
    """Return a multi-line string of a solid-filled diamond of given `size`.

    The diamond is filled with extra `/` and `\\` characters so the interior
    is dense rather than hollow.

        filled(3) ->
              /\\
             //\\\\
            ///\\\\\\
            \\\\\\///
             \\\\//
              \\/
    """
    size = _validate(size)
    if size == 0:
        return ''
    lines: list[str] = []

    # Top half
    for row in range(size):
        spaces = ' ' * (size - row - 1)
        slashes = '/' * (row + 1)
        backs = '\\' * (row + 1)
        lines.append(f'{spaces}{slashes}{backs}')

    # Bottom half (mirror)
    for row in range(size):
        spaces = ' ' * row
        backs = '\\' * (size - row)
        slashes = '/' * (size - row)
        lines.append(f'{spaces}{backs}{slashes}')

    return '\n'.join(lines)


def row_of_diamonds(sizes: list[int], style: str = 'outlined',
                    gap: int = 1) -> str:
    """Render multiple diamonds in a single horizontal row, baseline-aligned.

    The tallest diamond defines the row height; smaller diamonds are padded
    on top with blank rows so all bottoms sit on the same line. Each diamond
    is separated by `gap` spaces.
    """
    if not sizes:
        return ''
    if style not in ('outlined', 'filled'):
        raise ValueError(f"style must be 'outlined' or 'filled', got {style!r}")
    renderer = outlined if style == 'outlined' else filled

    # Render each diamond as a list of fixed-width lines.
    blocks: list[list[str]] = []
    widths: list[int] = []
    max_height = 0
    for s in sizes:
        s = _validate(s)
        width = s * 2 if s > 0 else 0
        if s == 0:
            block = ['']
        else:
            block = renderer(s).split('\n')
        # Right-pad each line to the diamond's full width
        block = [line.ljust(width) for line in block]
        blocks.append(block)
        widths.append(width)
        max_height = max(max_height, len(block))

    # Top-pad shorter diamonds so baselines align
    padded: list[list[str]] = []
    for block, width in zip(blocks, widths):
        pad_top = max_height - len(block)
        padding = [' ' * width] * pad_top
        padded.append(padding + block)

    sep = ' ' * gap
    out_lines: list[str] = []
    for row in range(max_height):
        parts = [block[row] for block in padded]
        out_lines.append(sep.join(parts).rstrip())
    return '\n'.join(out_lines)


def _print_usage() -> None:
    print(__doc__)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)

    if not args:
        # Default demo: a row of growing outlined diamonds, then a filled one
        print('Outlined row, sizes 1..5:')
        print(row_of_diamonds([1, 2, 3, 4, 5], style='outlined'))
        print()
        print('Filled diamond, size 5:')
        print(filled(5))
        return 0

    if args[0] in {'-h', '--help', 'help'}:
        _print_usage()
        return 0

    cmd = args[0]
    try:
        if cmd == 'row':
            if len(args) < 2:
                print('row requires at least one size, e.g. `row 1 2 3`',
                      file=sys.stderr)
                return 2
            # Optional 'filled'/'outlined' as 2nd token before sizes
            style = 'outlined'
            rest = args[1:]
            if rest and rest[0] in {'outlined', 'filled'}:
                style = rest[0]
                rest = rest[1:]
            sizes = [int(x) for x in rest]
            print(row_of_diamonds(sizes, style=style))
            return 0

        # `<size>` or `<size> <style>` form
        size = int(cmd)
        style = args[1] if len(args) > 1 else 'outlined'
        if style == 'filled':
            print(filled(size))
        elif style == 'outlined':
            print(outlined(size))
        else:
            print(f'unknown style {style!r}; expected outlined or filled',
                  file=sys.stderr)
            return 2
        return 0
    except ValueError as e:
        print(f'error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
