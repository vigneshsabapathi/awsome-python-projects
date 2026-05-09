"""Lucky Stars - Textual TUI.

Dark palette with an animated rolling-stars line and a styled fortune
panel. Saves to the same JSON history file used by the CLI.

Bindings:
    Space    Roll the stars
    s        Save the current reading
    Ctrl+Q   Quit

Run:
    uv run python lucky_stars/lucky_stars_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from lucky_stars import (
    STARS,
    UNICODE_SYMBOLS,
    read_fortune,
    save_reading,
)

ROLL_FRAMES = 14
ROLL_INTERVAL = 0.08  # seconds

THEME_STYLE = {
    'love':    'bold #f472b6',
    'work':    'bold #60a5fa',
    'money':   'bold #34d399',
    'health':  'bold #a3e635',
    'fortune': 'bold #c084fc',
}


class LuckyStarsApp(App):
    CSS = """
    Screen {
        background: #06070d;
        color: #f8fafc;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #fde68a;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #8b93b3;
        padding-bottom: 1;
    }

    #panel {
        width: 90%;
        height: auto;
        min-height: 16;
        margin: 1 2;
        padding: 2 4;
        background: #13162a;
        border: tall #262a47;
        align: center middle;
    }

    #stars {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 2;
    }

    #names {
        text-align: center;
        color: #8b93b3;
        text-style: italic;
        padding-bottom: 1;
    }

    #theme {
        text-align: center;
        text-style: bold;
        color: #fde68a;
        padding-top: 1;
    }

    #message {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 2;
    }

    #status {
        text-align: center;
        color: #8b93b3;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding('space', 'roll', 'Roll'),
        Binding('s', 'save', 'Save'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Lucky Stars'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.current_reading: dict | None = None
        self._roll_timer = None
        self._roll_counter = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('LUCKY  STARS', id='title')
        yield Static(
            'SPACE = roll  -  S = save  -  Ctrl+Q = quit',
            id='subtitle',
        )
        yield Vertical(
            Static('✦   ✧   ✦', id='stars'),
            Static('Press SPACE to roll your stars.', id='names'),
            Static('', id='theme'),
            Static('', id='message'),
            id='panel',
        )
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        # Initial roll so the panel is never empty.
        self.action_roll()

    # ----- actions ---------------------------------------------------------
    def action_roll(self) -> None:
        if self._roll_timer is not None:
            return  # already rolling
        self.query_one('#theme', Static).update('')
        self.query_one('#message', Static).update('')
        self.query_one('#names', Static).update('Rolling...')
        self.query_one('#status', Static).update(' ')
        self._roll_counter = 0
        self._roll_timer = self.set_interval(ROLL_INTERVAL, self._tick_roll)

    def _tick_roll(self) -> None:
        self._roll_counter += 1
        spin = '   '.join(self.rng.choice(UNICODE_SYMBOLS) for _ in range(3))
        self.query_one('#stars', Static).update(spin)
        if self._roll_counter >= ROLL_FRAMES:
            assert self._roll_timer is not None
            self._roll_timer.stop()
            self._roll_timer = None
            self._reveal()

    def _reveal(self) -> None:
        reading = read_fortune(self.rng)
        self.current_reading = reading
        symbols_unicode = [
            UNICODE_SYMBOLS[next(i for i, s in enumerate(STARS)
                                 if s['name'] == name)]
            for name in reading['stars']
        ]
        self.query_one('#stars', Static).update(
            '   '.join(symbols_unicode)
        )
        self.query_one('#names', Static).update(
            ', '.join(reading['stars'])
        )
        theme = reading['theme']
        style = THEME_STYLE.get(theme, 'bold #fde68a')
        self.query_one('#theme', Static).update(
            f'[{style}]{theme.upper()}[/]'
        )
        self.query_one('#message', Static).update(reading['message'])
        self.query_one('#status', Static).update(
            'SPACE = roll again  -  S = save'
        )

    def action_save(self) -> None:
        if self.current_reading is None:
            self.query_one('#status', Static).update(
                '[#f87171]Roll first, then save.[/]'
            )
            return
        path = save_reading(self.current_reading)
        self.query_one('#status', Static).update(
            f'[#34d399]Saved to {path}[/]'
        )


if __name__ == '__main__':
    LuckyStarsApp().run()
