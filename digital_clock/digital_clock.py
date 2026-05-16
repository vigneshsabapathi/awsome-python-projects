"""Digital Clock — real-time ASCII seven-segment clock.

Displays HH:MM:SS (or 12-hour format) as large three-line seven-segment digit
art, updating every second in-place. Twist: world-clock mode shows multiple
timezones simultaneously, and an AM/PM sun/moon indicator appears in 12h mode.

Run:
    uv run python digital_clock/digital_clock.py
    uv run python digital_clock/digital_clock.py --12h
    uv run python digital_clock/digital_clock.py --world
"""
from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Seven-segment digit art — 3 lines × fixed width, hand-authored from scratch.
# ---------------------------------------------------------------------------
_DIGITS: dict[str, list[str]] = {
    '0': [' ___ ', '|   |', '|___|'],
    '1': ['     ', '    |', '    |'],
    '2': [' ___ ', ' ___|', '|___ '],
    '3': [' ___ ', ' ___|', ' ___|'],
    '4': ['     ', '|___|', '    |'],
    '5': [' ___ ', '|___ ', ' ___|'],
    '6': [' ___ ', '|___ ', '|___|'],
    '7': [' ___ ', '    |', '    |'],
    '8': [' ___ ', '|___|', '|___|'],
    '9': [' ___ ', '|___|', ' ___|'],
    ':': [' ', '.', '.'],
    ' ': ['   ', '   ', '   '],
}

DIGIT_HEIGHT = 3

# World-clock timezone presets: (label, IANA zone)
WORLD_ZONES: list[tuple[str, str]] = [
    ('New York', 'America/New_York'),
    ('London', 'Europe/London'),
    ('Dubai', 'Asia/Dubai'),
    ('Tokyo', 'Asia/Tokyo'),
    ('Sydney', 'Australia/Sydney'),
]


def _digit_art(ch: str) -> list[str]:
    """Return the 3-line art for a single character ('0'-'9' or ':')."""
    return list(_DIGITS[ch])


def format_time(dt: datetime, *, twelve_hour: bool = False) -> str:
    """Return time string 'HH:MM:SS' (24h) or 'H:MM:SS' (12h, no leading zero).

    >>> format_time(datetime(2024, 1, 1, 14, 30, 45))
    '14:30:45'
    >>> format_time(datetime(2024, 1, 1, 9, 5, 3), twelve_hour=True)
    '9:05:03'
    """
    if twelve_hour:
        h = dt.hour % 12 or 12
        return f'{h}:{dt.minute:02d}:{dt.second:02d}'
    return f'{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}'


def render_clock(dt: datetime, *, twelve_hour: bool = False) -> str:
    """Render a datetime as a multi-line ASCII seven-segment clock string.

    Returns a '\\n'-joined string of DIGIT_HEIGHT (3) lines.
    """
    text = format_time(dt, twelve_hour=twelve_hour)
    rows = ['' for _ in range(DIGIT_HEIGHT)]
    for i, ch in enumerate(text):
        art = _digit_art(ch)
        gutter = '' if i == 0 else ' '
        for r in range(DIGIT_HEIGHT):
            rows[r] += gutter + art[r]
    return '\n'.join(rows)


def _ampm_indicator(dt: datetime) -> str:
    """Return sun/moon AM/PM indicator line."""
    return '☀  AM' if dt.hour < 12 else '🌙  PM'


def _clear_lines(n: int) -> None:
    """Move cursor up n lines and erase each — for in-place redraw."""
    sys.stdout.write('\033[F\033[2K' * n)


def _run_clock(*, twelve_hour: bool = False) -> None:
    """Main loop: display a single live clock, updating every second."""
    drawn_lines = 0
    while True:
        now = datetime.now()
        clock = render_clock(now, twelve_hour=twelve_hour)
        indicator = _ampm_indicator(now) if twelve_hour else ''
        date_str = now.strftime('%A, %d %B %Y')

        lines: list[str] = [date_str] + clock.split('\n')
        if indicator:
            lines.append(indicator)

        if drawn_lines:
            _clear_lines(drawn_lines)

        sys.stdout.write('\n'.join(lines) + '\n')
        sys.stdout.flush()
        drawn_lines = len(lines)
        time.sleep(1)


def _run_world_clock(*, twelve_hour: bool = False) -> None:
    """Twist: show a grid of clocks for several world timezones."""
    if ZoneInfo is None:
        print('zoneinfo not available (Python < 3.9 or missing tzdata). '
              'Install: uv pip install tzdata')
        return

    drawn_lines = 0
    while True:
        blocks: list[list[str]] = []
        for label, tz_name in WORLD_ZONES:
            try:
                tz = ZoneInfo(tz_name)
                local = datetime.now(tz)
            except Exception:
                local = datetime.now()
            clock_lines = render_clock(local, twelve_hour=twelve_hour).split('\n')
            indicator = _ampm_indicator(local) if twelve_hour else ''
            header = f' {label} '.center(len(clock_lines[0]))
            block = [header] + clock_lines
            if indicator:
                block.append(indicator.center(len(clock_lines[0])))
            blocks.append(block)

        # Arrange in two rows of up to 3 clocks
        rows_output: list[str] = []
        col_gap = '   '
        for start in range(0, len(blocks), 3):
            group = blocks[start:start + 3]
            height = max(len(b) for b in group)
            # Pad shorter blocks
            for b in group:
                while len(b) < height:
                    b.append(' ' * len(b[0]))
            for line_i in range(height):
                rows_output.append(col_gap.join(b[line_i] for b in group))
            rows_output.append('')  # blank separator between rows

        if drawn_lines:
            _clear_lines(drawn_lines)

        sys.stdout.write('\n'.join(rows_output) + '\n')
        sys.stdout.flush()
        drawn_lines = len(rows_output)
        time.sleep(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Real-time ASCII seven-segment digital clock.')
    parser.add_argument('--12h', dest='twelve_hour', action='store_true',
                        help='12-hour format with AM/PM sun/moon indicator')
    parser.add_argument('--world', action='store_true',
                        help='world-clock mode: show multiple timezones')
    args = parser.parse_args()

    try:
        if args.world:
            _run_world_clock(twelve_hour=args.twelve_hour)
        else:
            _run_clock(twelve_hour=args.twelve_hour)
    except KeyboardInterrupt:
        print('\nStopped.')


if __name__ == '__main__':
    main()
