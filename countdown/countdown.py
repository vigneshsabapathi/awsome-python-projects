"""Countdown — visual countdown timer with seven-segment ASCII digits.

Renders MM:SS as large 3-line seven-segment digit art and counts down in
the terminal, redrawing each second. Includes a Pomodoro twist: cycle
between 25-min work and 5-min break sessions with the --pomodoro flag.

Run:
    uv run python countdown/countdown.py 60
    uv run python countdown/countdown.py --pomodoro
    uv run python countdown/countdown.py --stopwatch
"""
from __future__ import annotations

import argparse
import sys
import time

# Each digit (and ":") is rendered as exactly 3 lines of fixed width.
# Hand-authored from scratch — no reference to any existing implementation.
# Width is 5 columns per digit, 1 column per ":" (rendered as two stacked dots).
_DIGITS: dict[str, list[str]] = {
    '0': [
        ' ___ ',
        '|   |',
        '|___|',
    ],
    '1': [
        '     ',
        '    |',
        '    |',
    ],
    '2': [
        ' ___ ',
        ' ___|',
        '|___ ',
    ],
    '3': [
        ' ___ ',
        ' ___|',
        ' ___|',
    ],
    '4': [
        '     ',
        '|___|',
        '    |',
    ],
    '5': [
        ' ___ ',
        '|___ ',
        ' ___|',
    ],
    '6': [
        ' ___ ',
        '|___ ',
        '|___|',
    ],
    '7': [
        ' ___ ',
        '    |',
        '    |',
    ],
    '8': [
        ' ___ ',
        '|___|',
        '|___|',
    ],
    '9': [
        ' ___ ',
        '|___|',
        ' ___|',
    ],
    ':': [
        ' ',
        '.',
        '.',
    ],
}

DIGIT_HEIGHT = 3


def format_time(seconds: int) -> str:
    """Format a non-negative int seconds count as 'MM:SS'.

    Minutes can exceed 99 — this just zero-pads to at least 2 digits.
    Negative inputs are clamped to 0.
    """
    if seconds < 0:
        seconds = 0
    minutes, secs = divmod(int(seconds), 60)
    return f'{minutes:02d}:{secs:02d}'


def digit_art(digit_str: str) -> list[str]:
    """Return the 3-line seven-segment ASCII art for a single character.

    Accepts '0'-'9' and ':'. Raises KeyError for anything else.
    """
    if len(digit_str) != 1:
        raise ValueError(f'digit_art expects one char, got {digit_str!r}')
    return list(_DIGITS[digit_str])


def render_clock(seconds: int) -> str:
    """Render the full multi-line clock for a seconds count.

    Joins each character's 3-line art horizontally with single-space gutters,
    returning one '\\n'-separated string ready to print.
    """
    text = format_time(seconds)
    rows = ['' for _ in range(DIGIT_HEIGHT)]
    for i, ch in enumerate(text):
        art = digit_art(ch)
        gutter = '' if i == 0 else ' '
        for r in range(DIGIT_HEIGHT):
            rows[r] += gutter + art[r]
    return '\n'.join(rows)


def render_progress_bar(elapsed: int, total: int, width: int = 30) -> str:
    """Render a [#####-----] style progress bar. total may be 0."""
    if total <= 0:
        return '[' + '-' * width + ']'
    ratio = max(0.0, min(1.0, elapsed / total))
    filled = int(round(ratio * width))
    return '[' + '#' * filled + '-' * (width - filled) + ']'


def _clear_lines(n: int) -> None:
    """Move cursor up n lines and clear them — used for in-place redraw."""
    # \033[F = up one line; \033[2K = erase entire line.
    sys.stdout.write('\033[F\033[2K' * n)


def _run_countdown(total: int, *, label: str = '', show_bar: bool = True) -> None:
    """Count down from `total` seconds to zero, redrawing in place each second."""
    start = time.monotonic()
    drawn_lines = 0
    while True:
        elapsed = int(time.monotonic() - start)
        remaining = max(0, total - elapsed)

        if drawn_lines:
            _clear_lines(drawn_lines)

        clock = render_clock(remaining)
        out_lines = []
        if label:
            out_lines.append(label)
        out_lines.extend(clock.split('\n'))
        if show_bar:
            out_lines.append(render_progress_bar(elapsed, total))

        sys.stdout.write('\n'.join(out_lines) + '\n')
        sys.stdout.flush()
        drawn_lines = len(out_lines)

        if remaining <= 0:
            break
        time.sleep(1)


def _run_stopwatch(limit: int = 3600) -> None:
    """Count up from 0 until `limit` (or Ctrl+C). Twist: stopwatch toggle."""
    start = time.monotonic()
    drawn_lines = 0
    while True:
        elapsed = int(time.monotonic() - start)
        if elapsed > limit:
            break
        if drawn_lines:
            _clear_lines(drawn_lines)
        clock = render_clock(elapsed)
        out_lines = ['Stopwatch (Ctrl+C to stop)'] + clock.split('\n')
        sys.stdout.write('\n'.join(out_lines) + '\n')
        sys.stdout.flush()
        drawn_lines = len(out_lines)
        time.sleep(1)


def _run_pomodoro(work: int = 25 * 60, brk: int = 5 * 60,
                  cycles: int = 4) -> None:
    """Run a Pomodoro: alternating work/break for the given number of cycles.

    Twist: this is the spec's suggested twist (25/5 cycle).
    """
    print(f'Pomodoro: {cycles} cycles of {work // 60}m work + {brk // 60}m break.')
    for c in range(1, cycles + 1):
        _run_countdown(work, label=f'\nCycle {c}/{cycles} — WORK')
        try:
            print('\a', end='', flush=True)  # bell at zero
        except Exception:
            pass
        if c < cycles:
            _run_countdown(brk, label=f'\nCycle {c}/{cycles} — BREAK')
            try:
                print('\a', end='', flush=True)
            except Exception:
                pass
    print('\nPomodoro complete!')


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Visual countdown timer with seven-segment ASCII digits.')
    parser.add_argument('seconds', nargs='?', type=int, default=60,
                        help='seconds to count down (default: 60)')
    parser.add_argument('--stopwatch', action='store_true',
                        help='count up instead of down')
    parser.add_argument('--pomodoro', action='store_true',
                        help='run a 4-cycle 25/5 Pomodoro session')
    parser.add_argument('--no-bar', action='store_true',
                        help='hide the progress bar')
    args = parser.parse_args()

    try:
        if args.pomodoro:
            _run_pomodoro()
        elif args.stopwatch:
            _run_stopwatch()
        else:
            if args.seconds < 0:
                parser.error('seconds must be non-negative')
            _run_countdown(args.seconds, show_bar=not args.no_bar)
            print('\a', end='', flush=True)  # terminal bell at zero
            print('Time is up!')
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
