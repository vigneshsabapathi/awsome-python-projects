"""Calendar Maker — CustomTkinter GUI.

A dark-themed desktop calendar viewer. Year + month selectors at top,
calendar grid as colored cells (today = highlighted, weekends = tinted,
US federal holidays = accent), Prev/Next buttons, and a Year View toggle
showing a 4x3 mini-month grid.

Run:
    uv run python calendar_maker/calendar_maker_gui.py
"""
from __future__ import annotations

from datetime import date

import customtkinter as ctk

from calendar_maker import (
    MONTH_NAMES,
    WEEKDAY_HEADERS,
    days_in_month,
    us_federal_holidays,
    zeller_weekday,
)

# ---- Theme ----------------------------------------------------------------
BG          = '#0f172a'   # slate-950
PANEL       = '#1e293b'   # slate-800
HEADER_FG   = '#f8fafc'   # slate-50
MUTED_FG    = '#94a3b8'   # slate-400

DAY_BG      = '#1f2937'   # gray-800
DAY_FG      = '#e5e7eb'   # gray-200
WEEKEND_BG  = '#334155'   # slate-700
WEEKEND_FG  = '#cbd5e1'   # slate-300
TODAY_BG    = '#16a34a'   # green-600
TODAY_FG    = '#ffffff'
HOLIDAY_BG  = '#7c3aed'   # violet-600
HOLIDAY_FG  = '#ffffff'
EMPTY_BG    = '#0f172a'   # match window bg

TITLE_FONT  = ('Segoe UI', 24, 'bold')
HEADER_FONT = ('Segoe UI', 12, 'bold')
DAY_FONT    = ('Segoe UI', 14, 'bold')
MINI_FONT   = ('Consolas', 9)
MINI_TITLE  = ('Segoe UI', 11, 'bold')


class CalendarApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Calendar Maker')
        self.geometry('760x640')
        self.minsize(700, 560)
        self.configure(fg_color=BG)

        today = date.today()
        self.year = today.year
        self.month = today.month
        self.year_view = False

        self._build_controls()
        self._content = ctk.CTkFrame(self, fg_color='transparent')
        self._content.pack(side='top', fill='both', expand=True,
                           padx=16, pady=(4, 12))
        self._render()

        self.bind('<Left>',  lambda _e: self._step_month(-1))
        self.bind('<Right>', lambda _e: self._step_month(+1))
        self.bind('<Up>',    lambda _e: self._step_year(+1))
        self.bind('<Down>',  lambda _e: self._step_year(-1))
        self.bind('<Control-t>', lambda _e: self._jump_today())

    # -- Top control bar ----------------------------------------------------
    def _build_controls(self) -> None:
        bar = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        bar.pack(side='top', fill='x', padx=16, pady=(16, 8))

        ctk.CTkLabel(bar, text='Calendar Maker', font=TITLE_FONT,
                     text_color=HEADER_FG).pack(side='left', padx=(16, 24),
                                                pady=10)

        self.month_var = ctk.StringVar(value=MONTH_NAMES[self.month - 1])
        self.month_menu = ctk.CTkOptionMenu(
            bar, values=list(MONTH_NAMES), variable=self.month_var,
            command=self._on_month_select, width=130,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b')
        self.month_menu.pack(side='left', padx=4, pady=10)

        self.year_var = ctk.StringVar(value=str(self.year))
        self.year_entry = ctk.CTkEntry(bar, textvariable=self.year_var,
                                       width=80, justify='center')
        self.year_entry.pack(side='left', padx=4, pady=10)
        self.year_entry.bind('<Return>', lambda _e: self._on_year_entry())
        self.year_entry.bind('<FocusOut>', lambda _e: self._on_year_entry())

        ctk.CTkButton(bar, text='<', width=36, command=lambda: self._step_month(-1),
                      fg_color='#334155', hover_color='#475569'
                      ).pack(side='left', padx=(12, 2), pady=10)
        ctk.CTkButton(bar, text='>', width=36, command=lambda: self._step_month(+1),
                      fg_color='#334155', hover_color='#475569'
                      ).pack(side='left', padx=2, pady=10)

        ctk.CTkButton(bar, text='Today', width=70,
                      command=self._jump_today,
                      fg_color='#0ea5e9', hover_color='#0284c7'
                      ).pack(side='left', padx=(12, 4), pady=10)

        self.toggle_btn = ctk.CTkButton(bar, text='Year View', width=100,
                                        command=self._toggle_view,
                                        fg_color='#7c3aed',
                                        hover_color='#6d28d9')
        self.toggle_btn.pack(side='right', padx=(4, 16), pady=10)

    # -- State updates ------------------------------------------------------
    def _on_month_select(self, value: str) -> None:
        self.month = MONTH_NAMES.index(value) + 1
        self._render()

    def _on_year_entry(self) -> None:
        try:
            y = int(self.year_var.get())
            if 1 <= y <= 9999:
                self.year = y
        except ValueError:
            pass
        self.year_var.set(str(self.year))
        self._render()

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
        self._sync_controls()
        self._render()

    def _step_year(self, delta: int) -> None:
        self.year = max(1, min(9999, self.year + delta))
        self._sync_controls()
        self._render()

    def _jump_today(self) -> None:
        today = date.today()
        self.year, self.month = today.year, today.month
        self._sync_controls()
        self._render()

    def _toggle_view(self) -> None:
        self.year_view = not self.year_view
        self.toggle_btn.configure(
            text='Month View' if self.year_view else 'Year View')
        self._render()

    def _sync_controls(self) -> None:
        self.month_var.set(MONTH_NAMES[self.month - 1])
        self.year_var.set(str(self.year))

    # -- Rendering ----------------------------------------------------------
    def _clear_content(self) -> None:
        for child in self._content.winfo_children():
            child.destroy()

    def _render(self) -> None:
        self._clear_content()
        if self.year_view:
            self._render_year_grid()
        else:
            self._render_month_grid()

    def _render_month_grid(self) -> None:
        today = date.today()
        holidays = us_federal_holidays(self.year)

        title = ctk.CTkLabel(
            self._content,
            text=f'{MONTH_NAMES[self.month - 1]} {self.year}',
            font=('Segoe UI', 20, 'bold'), text_color=HEADER_FG)
        title.pack(pady=(0, 8))

        grid = ctk.CTkFrame(self._content, fg_color='transparent')
        grid.pack(expand=True)

        # Weekday headers
        for col, name in enumerate(WEEKDAY_HEADERS):
            fg = '#fb7185' if col in (0, 6) else MUTED_FG  # weekend tint
            ctk.CTkLabel(grid, text=name, font=HEADER_FONT,
                         text_color=fg, width=88
                         ).grid(row=0, column=col, padx=4, pady=(0, 6))

        first_col = zeller_weekday(self.year, self.month, 1)
        n_days = days_in_month(self.year, self.month)

        row = 1
        col = first_col
        for day in range(1, n_days + 1):
            is_today = (today.year == self.year and today.month == self.month
                        and today.day == day)
            is_weekend = col in (0, 6)
            is_holiday = (self.month, day) in holidays

            if is_today:
                bg, fg = TODAY_BG, TODAY_FG
            elif is_holiday:
                bg, fg = HOLIDAY_BG, HOLIDAY_FG
            elif is_weekend:
                bg, fg = WEEKEND_BG, WEEKEND_FG
            else:
                bg, fg = DAY_BG, DAY_FG

            tooltip = holidays.get((self.month, day), '')
            text = f'{day}\n{tooltip}' if is_holiday else str(day)

            cell = ctk.CTkLabel(
                grid, text=text, width=88, height=64,
                fg_color=bg, text_color=fg,
                corner_radius=8, font=DAY_FONT)
            cell.grid(row=row, column=col, padx=4, pady=4)

            col += 1
            if col == 7:
                col = 0
                row += 1

        # Legend
        legend = ctk.CTkFrame(self._content, fg_color='transparent')
        legend.pack(pady=(12, 0))
        for label, bg, fg in (('Today', TODAY_BG, TODAY_FG),
                              ('Holiday', HOLIDAY_BG, HOLIDAY_FG),
                              ('Weekend', WEEKEND_BG, WEEKEND_FG)):
            chip = ctk.CTkLabel(legend, text=f'  {label}  ',
                                fg_color=bg, text_color=fg,
                                corner_radius=10,
                                font=('Segoe UI', 11, 'bold'))
            chip.pack(side='left', padx=6)

    def _render_year_grid(self) -> None:
        today = date.today()
        holidays = us_federal_holidays(self.year)

        title = ctk.CTkLabel(
            self._content, text=str(self.year),
            font=('Segoe UI', 22, 'bold'), text_color=HEADER_FG)
        title.pack(pady=(0, 6))

        grid = ctk.CTkFrame(self._content, fg_color='transparent')
        grid.pack(expand=True, fill='both')
        for r in range(4):
            grid.grid_rowconfigure(r, weight=1)
        for c in range(3):
            grid.grid_columnconfigure(c, weight=1)

        for idx, m in enumerate(range(1, 13)):
            r, c = divmod(idx, 3)
            self._build_mini_month(grid, m, today, holidays).grid(
                row=r, column=c, padx=6, pady=6, sticky='nsew')

    def _build_mini_month(self, parent: ctk.CTkFrame, month: int,
                          today: date,
                          holidays: dict[tuple[int, int], str]
                          ) -> ctk.CTkFrame:
        frame = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=10)
        ctk.CTkLabel(frame, text=MONTH_NAMES[month - 1],
                     font=MINI_TITLE, text_color=HEADER_FG
                     ).pack(pady=(8, 2))

        # Build mini grid as text rows for compactness.
        first_col = zeller_weekday(self.year, month, 1)
        n_days = days_in_month(self.year, month)

        cells: list[tuple[str, str]] = []
        for _ in range(first_col):
            cells.append(('  ', None))
        for day in range(1, n_days + 1):
            is_today = (today.year == self.year and today.month == month
                        and today.day == day)
            is_holiday = (month, day) in holidays
            tag = 'today' if is_today else ('holiday' if is_holiday else None)
            cells.append((f'{day:>2}', tag))
        while len(cells) % 7 != 0:
            cells.append(('  ', None))

        body = ctk.CTkFrame(frame, fg_color='transparent')
        body.pack(padx=8, pady=(0, 8))

        # Header row
        for c, name in enumerate(['S', 'M', 'T', 'W', 'T', 'F', 'S']):
            fg = '#fb7185' if c in (0, 6) else MUTED_FG
            ctk.CTkLabel(body, text=name, font=MINI_FONT,
                         text_color=fg, width=22
                         ).grid(row=0, column=c, padx=1)

        for i, (text, tag) in enumerate(cells):
            r, c = divmod(i, 7)
            r += 1
            if tag == 'today':
                fg, bg = TODAY_FG, TODAY_BG
            elif tag == 'holiday':
                fg, bg = HOLIDAY_FG, HOLIDAY_BG
            elif c in (0, 6) and text.strip():
                fg, bg = WEEKEND_FG, WEEKEND_BG
            else:
                fg, bg = DAY_FG, 'transparent'
            ctk.CTkLabel(body, text=text, font=MINI_FONT,
                         text_color=fg, fg_color=bg,
                         width=22, corner_radius=4
                         ).grid(row=r, column=c, padx=1, pady=1)
        return frame


if __name__ == '__main__':
    CalendarApp().mainloop()
