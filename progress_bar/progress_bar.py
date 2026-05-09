"""Progress Bar — animated terminal progress bar library + showcase.

A pure-stdlib library and CLI demo of multiple bar styles:
    blocks   — sub-cell eighth-block resolution (▏▎▍▌▋▊▉█)
    simple   — classic ``[===>   ]``
    dots     — Braille-pattern dots (⠁⠃⠇⠧⠷⠿)
    gradient — 256-color ANSI heatmap gradient
    spinner  — rotating spinner ⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏ + plain bar

Run:
    uv run python progress_bar/progress_bar.py            # full showcase
    uv run python progress_bar/progress_bar.py blocks     # one style
    uv run python progress_bar/progress_bar.py --iter 50  # iterator demo
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from typing import Iterable, Iterator, Sequence

# --------------------------------------------------------------------------- #
# Pure rendering — these functions return a string. No I/O.                   #
# --------------------------------------------------------------------------- #

# Eighth blocks for sub-cell resolution. Index 0 = empty, 8 = full cell.
_EIGHTHS = ' ▏▎▍▌▋▊▉█'

# Braille dot patterns — each successive glyph adds one more dot.
_DOTS = ' ⠁⠃⠇⠧⠷⠿'

# Spinner frames — one cell only; library users tick this each frame.
_SPINNER_FRAMES = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

# Gradient palette — 256-color ANSI codes from cool blue → warm red.
# Picked from xterm 256 cube to read well on dark terminals.
_GRADIENT_COLORS = (33, 39, 45, 51, 87, 123, 159, 195, 226, 220, 214, 208, 202, 196)

_RESET = '\x1b[0m'


def _clamp(progress: float) -> float:
    """Clamp to [0.0, 1.0]; tolerate slightly-out-of-range floats."""
    if progress < 0.0:
        return 0.0
    if progress > 1.0:
        return 1.0
    return progress


def bar(progress: float, width: int = 40, style: str = 'blocks') -> str:
    """Render a progress bar to a string.

    Args:
        progress: completion ratio in [0.0, 1.0].
        width: total inner width (number of cells used by the bar body).
        style: one of 'blocks', 'simple', 'dots', 'gradient', 'spinner'.

    Returns:
        A string at least ``width`` characters wide (excluding ANSI escapes
        and the surrounding brackets used by ``simple``). The ``gradient``
        style returns a string padded with reset codes — its visible width
        is still ``width``.
    """
    progress = _clamp(progress)
    style = style.lower()
    if style == 'blocks':
        return _bar_blocks(progress, width)
    if style == 'simple':
        return _bar_simple(progress, width)
    if style == 'dots':
        return _bar_dots(progress, width)
    if style == 'gradient':
        return _bar_gradient(progress, width)
    if style == 'spinner':
        return _bar_spinner(progress, width)
    raise ValueError(f'Unknown style: {style!r}')


def _bar_blocks(progress: float, width: int) -> str:
    """Eighth-block bar — each cell represents 1/8 of itself for smoothness."""
    total_eighths = int(round(progress * width * 8))
    full_cells, remainder = divmod(total_eighths, 8)
    bar_str = _EIGHTHS[8] * full_cells
    if remainder:
        bar_str += _EIGHTHS[remainder]
    return bar_str.ljust(width)


def _bar_simple(progress: float, width: int) -> str:
    """Plain ASCII ``[====>   ]`` bar — works on any terminal."""
    inner = max(1, width - 2)  # account for [] brackets
    filled = int(round(progress * inner))
    if 0 < filled < inner:
        body = '=' * (filled - 1) + '>'
    elif filled == inner:
        body = '=' * inner
    else:
        body = ''
    return '[' + body.ljust(inner) + ']'


def _bar_dots(progress: float, width: int) -> str:
    """Braille-dot bar — 6 levels per cell using ⠁⠃⠇⠧⠷⠿."""
    levels = len(_DOTS) - 1  # 6
    total = int(round(progress * width * levels))
    full_cells, remainder = divmod(total, levels)
    bar_str = _DOTS[-1] * full_cells
    if remainder:
        bar_str += _DOTS[remainder]
    return bar_str.ljust(width)


def _bar_gradient(progress: float, width: int) -> str:
    """Color-gradient bar — each filled cell is colored by its column index."""
    filled = int(round(progress * width))
    out: list[str] = []
    palette = _GRADIENT_COLORS
    for i in range(filled):
        # Map column → palette index so the gradient is column-stable
        # (cells don't change color as the bar grows, only new ones appear).
        color = palette[int(i / max(1, width - 1) * (len(palette) - 1))]
        out.append(f'\x1b[38;5;{color}m█')
    out.append(_RESET)
    out.append(' ' * (width - filled))
    return ''.join(out)


def _bar_spinner(progress: float, width: int) -> str:
    """Spinner glyph + simple bar. Spinner advances with progress."""
    frame_idx = int(progress * len(_SPINNER_FRAMES) * 4) % len(_SPINNER_FRAMES)
    spinner = _SPINNER_FRAMES[frame_idx]
    body = _bar_blocks(progress, max(1, width - 2))
    return f'{spinner} {body}'


def spinner_frame(tick: int) -> str:
    """Return the spinner glyph for a given tick — useful for indeterminate UI."""
    return _SPINNER_FRAMES[tick % len(_SPINNER_FRAMES)]


# --------------------------------------------------------------------------- #
# ProgressBar class — iterator wrapper with EMA-smoothed rate + ETA.          #
# --------------------------------------------------------------------------- #

STYLES: tuple[str, ...] = ('blocks', 'simple', 'dots', 'gradient', 'spinner')


def format_eta(seconds: float) -> str:
    """Human-friendly time string. ``--`` if unknown/infinite."""
    if not math.isfinite(seconds) or seconds < 0:
        return '--:--'
    seconds = int(seconds)
    if seconds < 60:
        return f'{seconds:02d}s'
    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f'{minutes:02d}:{secs:02d}'
    hours, minutes = divmod(minutes, 60)
    return f'{hours:d}:{minutes:02d}:{secs:02d}'


def format_rate(rate: float) -> str:
    """Format an items-per-second rate compactly."""
    if not math.isfinite(rate) or rate <= 0:
        return '?/s'
    if rate >= 1000:
        return f'{rate / 1000:.1f}k/s'
    if rate >= 100:
        return f'{rate:.0f}/s'
    if rate >= 10:
        return f'{rate:.1f}/s'
    return f'{rate:.2f}/s'


class ProgressBar:
    """Iterator-style progress bar with ETA and EMA-smoothed throughput.

    Two ways to use it:

    1. As an iterator wrapper::

           for item in ProgressBar(items, total=len(items)):
               ...

    2. Manually::

           pb = ProgressBar(total=100)
           for chunk in work():
               pb.update(len(chunk))
           pb.close()

    The displayed rate is exponentially-smoothed (EMA, alpha=0.3) to avoid
    flicker when chunk sizes vary. ETA is derived from the smoothed rate.
    """

    def __init__(
        self,
        iterable: Iterable | None = None,
        total: int | None = None,
        *,
        width: int = 30,
        style: str = 'blocks',
        prefix: str = '',
        stream=sys.stdout,
        ema_alpha: float = 0.3,
        min_interval: float = 0.05,
    ) -> None:
        if total is None and iterable is not None:
            try:
                total = len(iterable)  # type: ignore[arg-type]
            except TypeError:
                total = None
        if total is None:
            raise ValueError('ProgressBar needs total= when iterable has no len()')
        if style not in STYLES:
            raise ValueError(f'style must be one of {STYLES}, got {style!r}')

        self.iterable = iterable
        self.total = total
        self.width = width
        self.style = style
        self.prefix = prefix
        self.stream = stream
        self.ema_alpha = ema_alpha
        self.min_interval = min_interval

        self.n: int = 0
        self._start: float = 0.0
        self._last_time: float = 0.0
        self._last_n: int = 0
        self._rate: float = 0.0  # EMA items/sec
        self._closed: bool = False

    # ---- iterator protocol --------------------------------------------------

    def __iter__(self) -> Iterator:
        if self.iterable is None:
            raise TypeError('ProgressBar has no iterable to iterate over')
        self._begin()
        try:
            for item in self.iterable:
                yield item
                self.update(1)
        finally:
            self.close()

    # ---- public API ---------------------------------------------------------

    def update(self, n: int = 1) -> None:
        """Advance progress by ``n`` and possibly redraw."""
        if self._closed:
            return
        if self._start == 0.0:
            self._begin()
        self.n += n
        now = time.monotonic()
        # Throttle redraws so we don't drown the terminal in escape codes.
        if now - self._last_time < self.min_interval and self.n < self.total:
            return
        self._refresh_rate(now)
        self._draw()
        self._last_time = now
        self._last_n = self.n

    def close(self) -> None:
        """Force a final draw + newline. Safe to call twice."""
        if self._closed:
            return
        if self._start == 0.0:
            self._begin()
        self._refresh_rate(time.monotonic())
        self._draw()
        self.stream.write('\n')
        self.stream.flush()
        self._closed = True

    # context manager — handy for ``with ProgressBar(total=N) as pb:``
    def __enter__(self) -> 'ProgressBar':
        self._begin()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ---- internals ----------------------------------------------------------

    def _begin(self) -> None:
        if self._start != 0.0:
            return
        self._start = time.monotonic()
        self._last_time = self._start

    def _refresh_rate(self, now: float) -> None:
        """Update EMA-smoothed rate. Falls back to overall mean early on."""
        elapsed = now - self._last_time
        if elapsed <= 0:
            return
        instant = (self.n - self._last_n) / elapsed
        if self._rate == 0.0:
            # First sample — use overall mean to avoid a slow start cliff.
            total_elapsed = now - self._start
            self._rate = self.n / total_elapsed if total_elapsed > 0 else instant
        else:
            a = self.ema_alpha
            self._rate = a * instant + (1 - a) * self._rate

    def _draw(self) -> None:
        progress = self.n / self.total if self.total else 1.0
        body = bar(progress, self.width, self.style)
        eta = format_eta((self.total - self.n) / self._rate
                         if self._rate > 0 else float('inf'))
        rate = format_rate(self._rate)
        pct = f'{progress * 100:5.1f}%'
        prefix = f'{self.prefix} ' if self.prefix else ''
        line = (f'\r{prefix}{body} {pct} '
                f'[{self.n}/{self.total}] {rate} ETA {eta}')
        self.stream.write(line)
        self.stream.flush()


# --------------------------------------------------------------------------- #
# CLI showcase                                                                #
# --------------------------------------------------------------------------- #


def _demo_static_gallery(width: int = 30) -> None:
    """Print every style at a few progress points — no animation, just shape."""
    print('Static gallery — each style at 0%, 25%, 50%, 75%, 100%:')
    print()
    for style in STYLES:
        print(f'  {style:9}', end='')
        for p in (0.0, 0.25, 0.5, 0.75, 1.0):
            print(f'  {bar(p, width, style)}', end='')
        print()
    print()


def _demo_animated(style: str, total: int = 80, width: int = 30) -> None:
    """Animate one style by ticking up to ``total`` with random-ish chunks."""
    label = f'{style:9}'
    pb = ProgressBar(total=total, width=width, style=style, prefix=label)
    with pb:
        for i in range(total):
            # Vary work time so EMA smoothing has something to do.
            time.sleep(0.02 + 0.01 * (i % 3))
            pb.update(1)


def _demo_iterator(n: int = 50) -> None:
    """Show the ``for x in ProgressBar(items)`` pattern."""
    items = list(range(n))
    print(f'Iterator demo — wrapping a list of {n} items:')
    total = 0
    for v in ProgressBar(items, width=30, style='blocks', prefix='iter     '):
        time.sleep(0.03)
        total += v
    print(f'sum = {total}')


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        'style', nargs='?', default=None,
        choices=(*STYLES, 'all', 'static'),
        help='Animate one style, run the static gallery, or all (default: all).',
    )
    parser.add_argument('--total', type=int, default=80,
                        help='Frames per animated bar (default: 80).')
    parser.add_argument('--width', type=int, default=30,
                        help='Bar width in cells (default: 30).')
    parser.add_argument('--iter', action='store_true',
                        help='Also run the iterator-wrap demo.')
    args = parser.parse_args(argv)

    target = args.style or 'all'

    if target == 'static':
        _demo_static_gallery(args.width)
        return 0

    if target == 'all':
        _demo_static_gallery(args.width)
        print('Animated, one after the other:')
        print()
        for style in STYLES:
            _demo_animated(style, total=args.total, width=args.width)
        if args.iter:
            print()
            _demo_iterator()
        return 0

    _demo_animated(target, total=args.total, width=args.width)
    if args.iter:
        print()
        _demo_iterator()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
