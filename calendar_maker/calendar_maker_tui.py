"""Calendar Maker — Textual TUI.

Modern terminal UI for the Calendar Maker. Dark Tailwind palette.

Navigation:
    Left/Right  : prev / next month
    Up/Down     : next / prev year
    Ctrl+T      : jump to today
    Ctrl+Q      : quit

Run:
    uv run python calendar_maker/calendar_maker_tui.py
"""
from __future__ import annotations

from datetime import date

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from calendar_maker import (
    MONTH_NAMES,
    days_in_month,
    render_month,
    us_federal_holidays,
    zeller_weekday,
)


class CalendarApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 0 0 0;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #controls {
        height: 3;
        align-horizontal: center;
        margin-bottom: 1;
    }

    #controls Input {
        width: 12;
        margin: 0 1;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #controls Input:focus {
        border: tall #38bdf8;
    }

    #grid_container {
        align-horizontal: center;
        width: 100%;
    }

    #grid {
        background: #1e293b;
        color: #e5e7eb;
        padding: 1 2;
        border: tall #334155;
        width: auto;
        height: auto;
    }

    #legend {
        height: 1;
        align-horizontal: center;
        margin-top: 1;
    }

    .chip {
        padding: 0 1;
        margin: 0 1;
        height: 1;
    }

    .chip-today   { background: #16a34a; color: white; }
    .chip-holiday { background: #7c3aed; color: white; }
    .chip-weekend { background: #334155; color: #cbd5e1; }

    #status {
        text-align: center;
        padding: 1 0;
        color: #cbd5e1;
    }
    """

    BINDINGS = [
        Binding('left',     'prev_month', 'Prev Month'),
        Binding('right',    'next_month', 'Next Month'),
        Binding('up',       'next_year',  'Next Year'),
        Binding('down',     'prev_year',  'Prev Year'),
        Binding('ctrl+t',   'today',      'Today'),
        Binding('ctrl+q',   'quit',       'Quit'),
    ]

    TITLE = 'Calendar Maker'

    def __init__(self) -> None:
        super().__init__()
        today = date.today()
        self.year = today.year
        self.month = today.month

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('CALENDAR MAKER', id='title')
        yield Static('Left/Right: month  Up/Down: year  Ctrl+T: today  Ctrl+Q: quit',
                     id='subtitle')
        with Horizontal(id='controls'):
            yield Input(value=str(self.year), id='year_input',
                        placeholder='year')
            yield Input(value=str(self.month), id='month_input',
                        placeholder='month')
        with Vertical(id='grid_container'):
            yield Static('', id='grid')
        with Horizontal(id='legend'):
            yield Static('* = today', classes='chip chip-today')
            yield Static('. = holiday', classes='chip chip-holiday')
            yield Static('weekend', classes='chip chip-weekend')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    # ---- rendering --------------------------------------------------------
    def _refresh(self) -> None:
        text = render_month(self.year, self.month)
        # Highlight using Rich markup for the rendered text.
        text = self._stylize(text)
        grid = self.query_one('#grid', Static)
        grid.update(text)

        # Sync inputs without triggering submit handlers.
        year_in = self.query_one('#year_input', Input)
        month_in = self.query_one('#month_input', Input)
        if year_in.value != str(self.year):
            year_in.value = str(self.year)
        if month_in.value != str(self.month):
            month_in.value = str(self.month)

        holidays_this_month = sorted(
            (d, name) for (m, d), name in us_federal_holidays(self.year).items()
            if m == self.month)
        if holidays_this_month:
            holiday_str = ', '.join(f'{d} {n}' for d, n in holidays_this_month)
            self._set_status(f'Holidays: {holiday_str}')
        else:
            self._set_status('')

    def _stylize(self, text: str) -> str:
        """Apply Rich markup to title, header, weekends, today, holidays."""
        lines = text.split('\n')
        if not lines:
            return text

        styled: list[str] = []
        # Line 0: month/year title
        styled.append(f'[bold #f8fafc]{lines[0]}[/]')
        # Line 1: weekday headers — tint Sun/Sat
        if len(lines) > 1:
            hdr = lines[1]
            # Sun is at cols 0-2, Sat at cols 24-26
            styled.append(
                f'[#fb7185]{hdr[0:3]}[/]'
                f'[#94a3b8]{hdr[3:24]}[/]'
                f'[#fb7185]{hdr[24:]}[/]'
            )
        # Line 2: separator
        if len(lines) > 2:
            styled.append(f'[#475569]{lines[2]}[/]')

        # Day rows: lines 3..n until blank line
        i = 3
        while i < len(lines) and lines[i].strip():
            row = lines[i]
            styled.append(self._stylize_day_row(row))
            i += 1

        # Remaining lines (holidays footer)
        while i < len(lines):
            styled.append(f'[#94a3b8]{lines[i]}[/]')
            i += 1
        return '\n'.join(styled)

    def _stylize_day_row(self, row: str) -> str:
        """Color individual day cells. Each cell is 3 chars + 1 space."""
        out: list[str] = []
        for col in range(7):
            start = col * 4
            cell = row[start:start + 3]
            sep = row[start + 3:start + 4] if col < 6 else ''
            if not cell.strip():
                out.append(cell + sep)
                continue
            # Today marker: leading '*'
            if cell.startswith('*') or '*' in cell:
                out.append(f'[bold white on #16a34a]{cell}[/]' + sep)
            elif cell.endswith('.'):
                out.append(f'[bold white on #7c3aed]{cell}[/]' + sep)
            elif col in (0, 6):
                out.append(f'[#cbd5e1 on #334155]{cell}[/]' + sep)
            else:
                out.append(f'[#e5e7eb]{cell}[/]' + sep)
        return ''.join(out)

    def _set_status(self, text: str) -> None:
        self.query_one('#status', Static).update(text)

    # ---- actions ----------------------------------------------------------
    def _step_month(self, delta: int) -> None:
        m = self.month + delta
        y = self.year
        while m < 1:
            m += 12
            y -= 1
        while m > 12:
            m -= 12
            y += 1
        self.year, self.month = y, m
        self._refresh()

    def action_prev_month(self) -> None:
        self._step_month(-1)

    def action_next_month(self) -> None:
        self._step_month(+1)

    def action_next_year(self) -> None:
        self.year = min(9999, self.year + 1)
        self._refresh()

    def action_prev_year(self) -> None:
        self.year = max(1, self.year - 1)
        self._refresh()

    def action_today(self) -> None:
        today = date.today()
        self.year, self.month = today.year, today.month
        self._refresh()

    # ---- input handlers ---------------------------------------------------
    def on_input_submitted(self, event: Input.Submitted) -> None:
        try:
            value = int(event.value)
        except ValueError:
            self._set_status(f'Invalid {event.input.id}: {event.value}')
            return
        if event.input.id == 'year_input':
            if 1 <= value <= 9999:
                self.year = value
                self._refresh()
        elif event.input.id == 'month_input':
            if 1 <= value <= 12:
                self.month = value
                self._refresh()
            else:
                self._set_status(f'Month must be 1..12, got {value}')


if __name__ == '__main__':
    CalendarApp().run()
