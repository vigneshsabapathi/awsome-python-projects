"""Digital Clock — CustomTkinter GUI.

Dark-themed desktop clock with large seven-segment ASCII font displayed in a
monospace label. Supports 12/24-hour toggle, color themes (LCD green, LED red,
amber), show/hide seconds, and an optional date label.

Run:
    uv run python digital_clock/digital_clock_gui.py
"""
from __future__ import annotations

import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from digital_clock import format_time, render_clock, _ampm_indicator

# ---------------------------------------------------------------------------
# Color themes
# ---------------------------------------------------------------------------
THEMES: dict[str, dict[str, str]] = {
    'LCD Green': {
        'clock_fg': '#39ff14',
        'bg': '#0a0f0a',
        'date_fg': '#228B22',
        'indicator_fg': '#39ff14',
    },
    'LED Red': {
        'clock_fg': '#ff3030',
        'bg': '#0f0000',
        'date_fg': '#8B0000',
        'indicator_fg': '#ff3030',
    },
    'Amber': {
        'clock_fg': '#ffb300',
        'bg': '#0f0a00',
        'date_fg': '#b8860b',
        'indicator_fg': '#ffb300',
    },
}

CLOCK_FONT = ('Courier New', 16, 'bold')
DATE_FONT = ('Segoe UI', 13)
INDICATOR_FONT = ('Segoe UI', 14)
CONTROL_FONT = ('Segoe UI', 12)


class DigitalClockApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Digital Clock')
        self.resizable(False, False)
        self.configure(fg_color='#0a0f0a')

        self._twelve_hour = tk.BooleanVar(value=False)
        self._show_seconds = tk.BooleanVar(value=True)
        self._show_date = tk.BooleanVar(value=True)
        self._theme_name = tk.StringVar(value='LCD Green')

        self._build_ui()
        self._tick()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text='DIGITAL CLOCK', font=('Segoe UI', 18, 'bold'),
                     text_color='#94a3b8').pack(pady=(14, 2))

        # Clock display
        self._clock_frame = ctk.CTkFrame(self, fg_color='#0a0f0a',
                                         corner_radius=10, border_width=1,
                                         border_color='#1f2937')
        self._clock_frame.pack(padx=20, pady=6)

        self._clock_label = ctk.CTkLabel(
            self._clock_frame, text='', font=CLOCK_FONT,
            text_color='#39ff14', justify='left')
        self._clock_label.pack(padx=16, pady=(10, 2))

        self._indicator_label = ctk.CTkLabel(
            self._clock_frame, text='', font=INDICATOR_FONT,
            text_color='#39ff14')
        self._indicator_label.pack(pady=(0, 4))

        self._date_label = ctk.CTkLabel(
            self._clock_frame, text='', font=DATE_FONT,
            text_color='#228B22')
        self._date_label.pack(pady=(0, 10))

        # Controls
        ctrl = ctk.CTkFrame(self, fg_color='transparent')
        ctrl.pack(padx=20, pady=8, fill='x')

        ctk.CTkCheckBox(ctrl, text='12-hour', variable=self._twelve_hour,
                        font=CONTROL_FONT, checkbox_width=18, checkbox_height=18
                        ).grid(row=0, column=0, padx=8, pady=4, sticky='w')

        ctk.CTkCheckBox(ctrl, text='Seconds', variable=self._show_seconds,
                        font=CONTROL_FONT, checkbox_width=18, checkbox_height=18
                        ).grid(row=0, column=1, padx=8, pady=4, sticky='w')

        ctk.CTkCheckBox(ctrl, text='Date', variable=self._show_date,
                        font=CONTROL_FONT, checkbox_width=18, checkbox_height=18
                        ).grid(row=0, column=2, padx=8, pady=4, sticky='w')

        ctk.CTkLabel(ctrl, text='Color:', font=CONTROL_FONT,
                     text_color='#94a3b8').grid(row=1, column=0, padx=8, pady=4,
                                                sticky='w')

        ctk.CTkOptionMenu(ctrl, values=list(THEMES.keys()),
                          variable=self._theme_name,
                          command=self._apply_theme,
                          font=CONTROL_FONT, width=130,
                          fg_color='#1e293b', button_color='#334155',
                          button_hover_color='#475569'
                          ).grid(row=1, column=1, columnspan=2, padx=8, pady=4,
                                 sticky='w')

        self._apply_theme(self._theme_name.get())

    # ------------------------------------------------------------------
    def _apply_theme(self, theme_name: str) -> None:
        t = THEMES.get(theme_name, THEMES['LCD Green'])
        self.configure(fg_color=t['bg'])
        self._clock_frame.configure(fg_color=t['bg'])
        self._clock_label.configure(text_color=t['clock_fg'])
        self._indicator_label.configure(text_color=t['indicator_fg'])
        self._date_label.configure(text_color=t['date_fg'])

    def _tick(self) -> None:
        now = datetime.now()
        twelve = self._twelve_hour.get()
        show_sec = self._show_seconds.get()

        # Build time string then render
        if show_sec:
            clock_str = render_clock(now, twelve_hour=twelve)
        else:
            # Render without seconds — just HH:MM
            time_str = format_time(now, twelve_hour=twelve)
            time_str = time_str.rsplit(':', 1)[0]  # drop :SS
            from digital_clock import _digit_art, DIGIT_HEIGHT
            rows = ['' for _ in range(DIGIT_HEIGHT)]
            for i, ch in enumerate(time_str):
                art = _digit_art(ch)
                gutter = '' if i == 0 else ' '
                for r in range(DIGIT_HEIGHT):
                    rows[r] += gutter + art[r]
            clock_str = '\n'.join(rows)

        self._clock_label.configure(text=clock_str)

        # AM/PM indicator
        if twelve:
            self._indicator_label.configure(text=_ampm_indicator(now))
        else:
            self._indicator_label.configure(text='')

        # Date
        if self._show_date.get():
            self._date_label.configure(
                text=now.strftime('%A, %d %B %Y'))
        else:
            self._date_label.configure(text='')

        self.after(1000, self._tick)


def main() -> None:
    app = DigitalClockApp()
    app.mainloop()


if __name__ == '__main__':
    main()
