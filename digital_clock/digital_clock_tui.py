"""Digital Clock — Textual TUI.

Dark Tailwind-palette terminal clock. Bindings: c cycle color, t toggle 12/24h,
d toggle date, Ctrl+Q quit.

Run:
    uv run python digital_clock/digital_clock_tui.py
"""
from __future__ import annotations

from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Static

from digital_clock import format_time, _ampm_indicator, DIGIT_HEIGHT, _digit_art

# ---------------------------------------------------------------------------
# Color palettes (Tailwind-inspired)
# ---------------------------------------------------------------------------
_PALETTES = [
    {'name': 'LCD Green', 'clock': '#39ff14', 'dim': '#166534', 'bg': '#0a0f0a'},
    {'name': 'LED Red',   'clock': '#f87171', 'dim': '#7f1d1d', 'bg': '#0f0000'},
    {'name': 'Amber',     'clock': '#fbbf24', 'dim': '#78350f', 'bg': '#0f0a00'},
    {'name': 'Sky Blue',  'clock': '#38bdf8', 'dim': '#075985', 'bg': '#000f1a'},
]


def _render_no_seconds(dt: datetime, *, twelve_hour: bool = False) -> str:
    """Render HH:MM without seconds."""
    time_str = format_time(dt, twelve_hour=twelve_hour).rsplit(':', 1)[0]
    rows = ['' for _ in range(DIGIT_HEIGHT)]
    for i, ch in enumerate(time_str):
        art = _digit_art(ch)
        gutter = '' if i == 0 else ' '
        for r in range(DIGIT_HEIGHT):
            rows[r] += gutter + art[r]
    return '\n'.join(rows)


class DigitalClockApp(App):
    CSS = """
    Screen {
        background: #0a0f0a;
        align: center middle;
    }

    #wrapper {
        align: center middle;
        width: auto;
        height: auto;
        border: round #166534;
        padding: 1 3;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #4ade80;
        padding-bottom: 1;
    }

    #clock {
        text-align: left;
        color: #39ff14;
        text-style: bold;
    }

    #indicator {
        text-align: center;
        color: #39ff14;
        padding-top: 1;
        height: 2;
    }

    #date {
        text-align: center;
        color: #166534;
        padding-top: 1;
    }

    #palette-label {
        text-align: center;
        color: #374151;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding('c', 'cycle_color', 'Color'),
        Binding('t', 'toggle_hour', '12/24h'),
        Binding('d', 'toggle_date', 'Date'),
        Binding('s', 'toggle_seconds', 'Seconds'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Digital Clock'

    def __init__(self) -> None:
        super().__init__()
        self._palette_idx = 0
        self._twelve_hour = False
        self._show_date = True
        self._show_seconds = True

    def compose(self) -> ComposeResult:
        from textual.containers import Vertical
        with Vertical(id='wrapper'):
            yield Static('DIGITAL CLOCK', id='title')
            yield Static('', id='clock')
            yield Static('', id='indicator')
            yield Static('', id='date')
            yield Static('', id='palette-label')
        yield Footer()

    def on_mount(self) -> None:
        self._apply_palette()
        self.set_interval(1, self._tick)
        self._tick()

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        now = datetime.now()
        if self._show_seconds:
            from digital_clock import render_clock
            clock_str = render_clock(now, twelve_hour=self._twelve_hour)
        else:
            clock_str = _render_no_seconds(now, twelve_hour=self._twelve_hour)

        self.query_one('#clock', Static).update(clock_str)

        if self._twelve_hour:
            self.query_one('#indicator', Static).update(
                _ampm_indicator(now))
        else:
            self.query_one('#indicator', Static).update('')

        if self._show_date:
            self.query_one('#date', Static).update(
                now.strftime('%A, %d %B %Y'))
        else:
            self.query_one('#date', Static).update('')

    def _apply_palette(self) -> None:
        p = _PALETTES[self._palette_idx]
        self.query_one('#clock', Static).styles.color = p['clock']
        self.query_one('#indicator', Static).styles.color = p['clock']
        self.query_one('#date', Static).styles.color = p['dim']
        self.query_one('#wrapper').styles.border = ('round', p['dim'])
        self.query_one('#palette-label', Static).update(
            f'[{p["name"]}]  c=color  t=12/24h  d=date  s=secs')
        self.app.stylesheet.reparse()

    # ------------------------------------------------------------------
    def action_cycle_color(self) -> None:
        self._palette_idx = (self._palette_idx + 1) % len(_PALETTES)
        self._apply_palette()

    def action_toggle_hour(self) -> None:
        self._twelve_hour = not self._twelve_hour
        self._tick()

    def action_toggle_date(self) -> None:
        self._show_date = not self._show_date
        self._tick()

    def action_toggle_seconds(self) -> None:
        self._show_seconds = not self._show_seconds
        self._tick()


def main() -> None:
    DigitalClockApp().run()


if __name__ == '__main__':
    main()
