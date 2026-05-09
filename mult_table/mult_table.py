"""Multiplication Table.

Render multiplication tables (1..N x 1..N) with proper alignment, headers,
and unicode box-drawing borders. A modular variant computes (i*j) mod M and
reveals the patterns of the cyclic group Z/MZ.

Run:
    uv run python mult_table/mult_table.py            # default N=12
    uv run python mult_table/mult_table.py 10
    uv run python mult_table/mult_table.py 12 --mod 7
"""
from __future__ import annotations

import argparse

DEFAULT_N = 12
MIN_N, MAX_N = 1, 30


def _cell_width(n: int, mod: int | None) -> int:
    """Width for each cell — wide enough for the biggest number plus padding."""
    if mod is not None:
        biggest = max(0, mod - 1)
    else:
        biggest = n * n
    return max(2, len(str(biggest))) + 1  # 1 char of padding on the left


def render(n: int) -> str:
    """Return a unicode-bordered multiplication table for 1..n x 1..n.

    Uses box-drawing characters: ┌ ┬ ┐ ├ ┼ ┤ └ ┴ ┘ ─ │.
    The header row and header column are separated from the body by a heavy
    double rule (═ and ║) so the structure is easy to scan.
    """
    if not (MIN_N <= n <= MAX_N):
        raise ValueError(f'n must be in [{MIN_N}, {MAX_N}], got {n}')

    w = _cell_width(n, None)
    cells = [[i * j for j in range(1, n + 1)] for i in range(1, n + 1)]

    def hline(left: str, mid: str, right: str, fill: str = '─') -> str:
        # corner-cell + n body-cells (header column + n columns)
        segs = [fill * w] + [fill * w for _ in range(n)]
        return left + mid.join(segs) + right

    def header_row() -> str:
        # Top label cell is blank; remaining cells are 1..n
        cells_text = [' ' * w] + [f'{j:>{w - 1}d} ' for j in range(1, n + 1)]
        return '║' + '│'.join(cells_text) + '║'

    def body_row(i: int) -> str:
        row = cells[i - 1]
        first = f'{i:>{w - 1}d} '
        rest = [f'{v:>{w - 1}d} ' for v in row]
        return '║' + first + '║' + '│'.join(rest) + '║'

    # Top border: ╔══╤══╤══╗ but with a thicker spine after the header column
    def heavy_top() -> str:
        segs = ['═' * w] + ['═' * w for _ in range(n)]
        # join header-col / first-body-col with ╦ (heavy down to body),
        # remaining joins with ╤
        joiners = ['╦'] + ['╤'] * (n - 1)
        out = '╔' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╗'

    def heavy_sep() -> str:
        # Below header row: ╠══╪══╪══╣ with ╬ after the header column
        segs = ['═' * w] + ['═' * w for _ in range(n)]
        joiners = ['╬'] + ['╪'] * (n - 1)
        out = '╠' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╣'

    def body_sep() -> str:
        # Between body rows: ╟──┼──┼──╢ with ╫ after the header column
        segs = ['─' * w] + ['─' * w for _ in range(n)]
        joiners = ['╫'] + ['┼'] * (n - 1)
        out = '╟' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╢'

    def heavy_bottom() -> str:
        segs = ['═' * w] + ['═' * w for _ in range(n)]
        joiners = ['╩'] + ['╧'] * (n - 1)
        out = '╚' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╝'

    lines = [heavy_top(), header_row(), heavy_sep()]
    for i in range(1, n + 1):
        lines.append(body_row(i))
        if i != n:
            lines.append(body_sep())
    lines.append(heavy_bottom())
    return '\n'.join(lines)


def render_modular(n: int, mod: int) -> str:
    """Render the multiplication table reduced modulo M.

    Cell (i, j) = (i * j) mod M for i, j in 0..n-1. Headers run 0..n-1
    because the additive identity (and the orbit through 0) is part of the
    structure; this is what makes the pattern visible.
    """
    if not (MIN_N <= n <= MAX_N):
        raise ValueError(f'n must be in [{MIN_N}, {MAX_N}], got {n}')
    if mod < 2:
        raise ValueError('mod must be >= 2')

    w = _cell_width(n, mod)
    cells = [[(i * j) % mod for j in range(n)] for i in range(n)]

    def header_row() -> str:
        cells_text = [' ' * w] + [f'{j:>{w - 1}d} ' for j in range(n)]
        return '║' + '│'.join(cells_text) + '║'

    def body_row(i: int) -> str:
        row = cells[i]
        first = f'{i:>{w - 1}d} '
        rest = [f'{v:>{w - 1}d} ' for v in row]
        return '║' + first + '║' + '│'.join(rest) + '║'

    def heavy_top() -> str:
        segs = ['═' * w] + ['═' * w for _ in range(n)]
        joiners = ['╦'] + ['╤'] * (n - 1)
        out = '╔' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╗'

    def heavy_sep() -> str:
        segs = ['═' * w] + ['═' * w for _ in range(n)]
        joiners = ['╬'] + ['╪'] * (n - 1)
        out = '╠' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╣'

    def body_sep() -> str:
        segs = ['─' * w] + ['─' * w for _ in range(n)]
        joiners = ['╫'] + ['┼'] * (n - 1)
        out = '╟' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╢'

    def heavy_bottom() -> str:
        segs = ['═' * w] + ['═' * w for _ in range(n)]
        joiners = ['╩'] + ['╧'] * (n - 1)
        out = '╚' + segs[0]
        for joiner, seg in zip(joiners, segs[1:]):
            out += joiner + seg
        return out + '╝'

    title = f'(i × j) mod {mod}    (mod {mod} is '
    title += 'prime' if _is_prime(mod) else 'composite'
    title += ')'

    lines = [title, heavy_top(), header_row(), heavy_sep()]
    for i in range(n):
        lines.append(body_row(i))
        if i != n - 1:
            lines.append(body_sep())
    lines.append(heavy_bottom())
    return '\n'.join(lines)


def _is_prime(m: int) -> bool:
    if m < 2:
        return False
    if m % 2 == 0:
        return m == 2
    i = 3
    while i * i <= m:
        if m % i == 0:
            return False
        i += 2
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Render a multiplication table with unicode borders.')
    parser.add_argument('n', nargs='?', type=int, default=DEFAULT_N,
                        help=f'table size, {MIN_N}..{MAX_N} (default {DEFAULT_N})')
    parser.add_argument('--mod', type=int, default=None,
                        help='render (i*j) mod M to expose patterns (M >= 2)')
    args = parser.parse_args()

    if not (MIN_N <= args.n <= MAX_N):
        parser.error(f'n must be in [{MIN_N}, {MAX_N}]')

    if args.mod is not None:
        if args.mod < 2:
            parser.error('--mod must be >= 2')
        print(render_modular(args.n, args.mod))
    else:
        print(render(args.n))


if __name__ == '__main__':
    main()
