# Calendar Maker

A formatted text calendar generator for any month/year. Inspired by the
Calendar Maker project from Al Sweigart's *The Big Book of Small Python
Projects*, but implemented from scratch using **Zeller's congruence** for
day-of-week calculations rather than the stdlib `calendar` module.

## What it does

- Renders any month as a Sun..Sat aligned text grid
- Renders an entire year as 12 stacked months
- Marks today's date with `*` and US federal holidays with `.`
- Three frontends: CLI, CustomTkinter desktop GUI, Textual TUI

## Run

```sh
# CLI — current month
uv run python calendar_maker/calendar_maker.py

# CLI — specific month
uv run python calendar_maker/calendar_maker.py 2024 2

# CLI — full year
uv run python calendar_maker/calendar_maker.py 2024

# Desktop GUI (CustomTkinter)
uv run python calendar_maker/calendar_maker_gui.py

# Terminal UI (Textual)
uv run python calendar_maker/calendar_maker_tui.py
```

## Architecture

| File | Role |
|---|---|
| `calendar_maker.py` | Pure date math + rendering. `render_month`, `render_year`, `zeller_weekday`, `days_in_month`, `is_leap_year`, `us_federal_holidays`. |
| `calendar_maker_gui.py` | CustomTkinter dark-theme desktop app. Month/year selector, Prev/Next, Today, Year View toggle (4x3 mini-month grid). |
| `calendar_maker_tui.py` | Textual TUI with arrow-key month/year navigation, Ctrl+T jump to today, Ctrl+Q quit. |

The GUI and TUI both import the pure functions from `calendar_maker.py` —
all date logic lives in one place.

## Date math

**Zeller's congruence** computes the day of week for any Gregorian date
in O(1) without a lookup table:

```
h = (q + floor(13(m+1)/5) + K + floor(K/4) + floor(J/4) - 2J) mod 7
```

where `q` is day-of-month, `m` is month (with Jan/Feb treated as months
13/14 of the prior year), `K = year mod 100`, and `J = year div 100`.

Leap years follow the standard Gregorian rule: divisible by 4, but not
100, unless also by 400.

## Creative twist

US federal holidays are highlighted in violet (GUI), with chip badges
listing them under each month (CLI/TUI). Holiday rules include both
fixed-date (Independence Day, Christmas) and nth-weekday (Thanksgiving =
4th Thursday of November, Memorial Day = last Monday of May).

## Keyboard shortcuts

### GUI

- `Left` / `Right` — previous / next month
- `Up` / `Down` — next / previous year
- `Ctrl+T` — jump to today

### TUI

- `Left` / `Right` — previous / next month
- `Up` / `Down` — next / previous year
- `Ctrl+T` — jump to today
- `Ctrl+Q` — quit
