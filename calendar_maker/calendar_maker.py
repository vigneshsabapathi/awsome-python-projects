"""Calendar Maker — CLI.

Generates a formatted text calendar for any month/year with Sun..Sat
columns and a properly aligned grid of days. Marks weekends and US
federal holidays as a fun twist.

Run:
    uv run python calendar_maker/calendar_maker.py            # current month
    uv run python calendar_maker/calendar_maker.py 2024 2     # Feb 2024
    uv run python calendar_maker/calendar_maker.py 2024       # full year
"""
from __future__ import annotations

import sys
from datetime import date

MONTH_NAMES = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]

# Sunday-first weekday header (matches Sweigart's original layout).
WEEKDAY_HEADERS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

CELL_WIDTH = 4   # ' DD '   — three chars + separator
GRID_WIDTH = CELL_WIDTH * 7 - 1  # 27 chars wide (no trailing pipe spacing)


# ---------------------------------------------------------------------------
# Date math (no stdlib `calendar` — built from scratch via Zeller's congruence)
# ---------------------------------------------------------------------------

def is_leap_year(year: int) -> bool:
    """Gregorian leap-year rule: divisible by 4, but not by 100 unless by 400."""
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    """Return the number of days in (year, month). 1 <= month <= 12."""
    if not 1 <= month <= 12:
        raise ValueError(f'month must be 1..12, got {month}')
    if month == 2:
        return 29 if is_leap_year(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def zeller_weekday(year: int, month: int, day: int) -> int:
    """Day-of-week via Zeller's congruence.

    Returns 0=Sunday, 1=Monday, ..., 6=Saturday.

    Zeller treats January and February as months 13 and 14 of the prior year:
        h = (q + floor(13(m+1)/5) + K + floor(K/4) + floor(J/4) - 2J) mod 7
    where h: 0=Saturday, 1=Sunday, ..., 6=Friday — we re-shift to Sunday-first.
    """
    if month < 3:
        month += 12
        year -= 1
    K = year % 100
    J = year // 100
    h = (day + (13 * (month + 1)) // 5 + K + K // 4 + J // 4 - 2 * J) % 7
    # h: 0=Sat, 1=Sun, 2=Mon, ..., 6=Fri  →  shift to 0=Sun..6=Sat
    return (h + 6) % 7


# ---------------------------------------------------------------------------
# US federal holidays (fixed-date + nth-weekday rules)
# ---------------------------------------------------------------------------

def _nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
    """Return day-of-month for the nth occurrence of weekday (0=Sun..6=Sat).

    n = 1 → first, 2 → second, etc. n = -1 → last occurrence.
    """
    if n > 0:
        first_wd = zeller_weekday(year, month, 1)
        offset = (weekday - first_wd) % 7
        return 1 + offset + 7 * (n - 1)
    # n < 0: count back from last day
    last = days_in_month(year, month)
    last_wd = zeller_weekday(year, month, last)
    offset = (last_wd - weekday) % 7
    return last - offset - 7 * (-n - 1)


def us_federal_holidays(year: int) -> dict[tuple[int, int], str]:
    """Return {(month, day): name} for US federal holidays in `year`."""
    holidays: dict[tuple[int, int], str] = {
        (1, 1):   "New Year's Day",
        (6, 19):  'Juneteenth',
        (7, 4):   'Independence Day',
        (11, 11): 'Veterans Day',
        (12, 25): 'Christmas Day',
    }
    # MLK Day — 3rd Monday of January
    holidays[(1, _nth_weekday(year, 1, 1, 3))] = 'MLK Jr. Day'
    # Presidents' Day — 3rd Monday of February
    holidays[(2, _nth_weekday(year, 2, 1, 3))] = "Presidents' Day"
    # Memorial Day — last Monday of May
    holidays[(5, _nth_weekday(year, 5, 1, -1))] = 'Memorial Day'
    # Labor Day — 1st Monday of September
    holidays[(9, _nth_weekday(year, 9, 1, 1))] = 'Labor Day'
    # Columbus Day — 2nd Monday of October
    holidays[(10, _nth_weekday(year, 10, 1, 2))] = 'Columbus Day'
    # Thanksgiving — 4th Thursday of November (Thursday = 4 in Sun-first)
    holidays[(11, _nth_weekday(year, 11, 4, 4))] = 'Thanksgiving'
    return holidays


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_month(year: int, month: int, *, today: date | None = None,
                 mark_holidays: bool = True) -> str:
    """Render a single month as a Sun..Sat aligned text grid.

    - Today's date is wrapped in brackets: `[15]`.
    - US federal holidays are wrapped in parens: `(25)`.
    - Otherwise days are right-aligned 2-digit numbers.

    Each cell is 3 characters wide ('DD ' or ' DD'), separated by a space,
    so columns line up regardless of which day of week the month begins on.
    """
    if not 1 <= month <= 12:
        raise ValueError(f'month must be 1..12, got {month}')

    title = f'{MONTH_NAMES[month - 1]} {year}'
    header = f'{title:^{GRID_WIDTH}}'
    weekdays_line = ' '.join(f'{w:>3}' for w in WEEKDAY_HEADERS)
    separator = '-' * GRID_WIDTH

    holidays = us_federal_holidays(year) if mark_holidays else {}
    today = today or date.today()

    n_days = days_in_month(year, month)
    first_col = zeller_weekday(year, month, 1)  # 0=Sun..6=Sat

    cells: list[str] = []
    # Leading blanks before day 1 — each cell is 3 chars wide
    for _ in range(first_col):
        cells.append('   ')
    for day in range(1, n_days + 1):
        is_today = (today.year == year and today.month == month
                    and today.day == day)
        is_holiday = (month, day) in holidays
        # Each cell is exactly 3 characters wide.
        if is_today:
            # Today: '*15' or ' *5' — leading asterisk marker.
            cells.append(f'*{day:>2}')
        elif is_holiday:
            # Holiday: trailing '.' marker — keeps width at 3.
            cells.append(f'{day:>2}.')
        else:
            cells.append(f'{day:>3}')
    # Trailing blanks to complete the last week
    while len(cells) % 7 != 0:
        cells.append('   ')

    rows: list[str] = []
    for week_start in range(0, len(cells), 7):
        rows.append(' '.join(cells[week_start:week_start + 7]))

    parts = [header, weekdays_line, separator, *rows]

    if mark_holidays and holidays:
        month_holidays = sorted(
            (day, name) for (m, day), name in holidays.items() if m == month)
        if month_holidays:
            parts.append('')
            parts.append('Holidays (.):')
            for day, name in month_holidays:
                parts.append(f'  {day:>2} - {name}')
        if any(d.year == year and d.month == month
               for d in (today,) if d):
            if today.year == year and today.month == month:
                parts.append(f'Today (*): {today.isoformat()}')

    return '\n'.join(parts)


def render_year(year: int, *, today: date | None = None,
                mark_holidays: bool = True) -> str:
    """Render all 12 months of a year stacked vertically."""
    months = [render_month(year, m, today=today, mark_holidays=mark_holidays)
              for m in range(1, 13)]
    banner = f'{"=" * GRID_WIDTH}\n{year:^{GRID_WIDTH}}\n{"=" * GRID_WIDTH}'
    return banner + '\n\n' + '\n\n'.join(months)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str]) -> tuple[int, int | None]:
    """Parse: [year [month]]. Defaults to today's year/month."""
    today = date.today()
    if len(argv) == 0:
        return today.year, today.month
    if len(argv) == 1:
        return int(argv[0]), None  # full-year render
    if len(argv) == 2:
        year, month = int(argv[0]), int(argv[1])
        if not 1 <= month <= 12:
            raise SystemExit(f'month must be 1..12, got {month}')
        return year, month
    raise SystemExit('Usage: calendar_maker.py [year [month]]')


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    year, month = _parse_args(argv)
    if month is None:
        print(render_year(year))
    else:
        print(render_month(year, month))


if __name__ == '__main__':
    main()
