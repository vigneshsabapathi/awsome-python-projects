"""99 Bottles of Beer — Textual TUI.

Dark Tailwind palette. Lyrics in a big centered panel.

Bindings:
    Space   Next verse
    R       Toggle remix mode
    Enter   Reset to start
    Ctrl+Q  Quit

Run:
    uv run python bottles/bottles_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from bottles import _bottles_phrase, render_verse


class BottlesApp(App):
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
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #lyrics-panel {
        width: 90%;
        height: auto;
        min-height: 14;
        margin: 1 2;
        padding: 2 4;
        background: #1e293b;
        border: tall #334155;
        align: center middle;
    }

    #lyrics {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 2;
    }

    #meta {
        text-align: center;
        color: #38bdf8;
        padding-top: 1;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding('space', 'next_verse', 'Next verse'),
        Binding('r', 'toggle_remix', 'Remix'),
        Binding('enter', 'reset', 'Reset'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = '99 Bottles of Beer'

    def __init__(self, start: int = 99) -> None:
        super().__init__()
        if start < 1:
            start = 1
        self.start_count = start
        self.current = start
        self.remix = False
        self.rng = random.Random()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('99 BOTTLES OF BEER', id='title')
        yield Static(
            'SPACE = next  -  R = remix  -  Enter = reset  -  Ctrl+Q = quit',
            id='subtitle',
        )
        yield Vertical(
            Static('', id='lyrics'),
            Static('', id='meta'),
            id='lyrics-panel',
        )
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    # ----- actions ---------------------------------------------------------
    def action_next_verse(self) -> None:
        if self.current <= 0:
            self.current = self.start_count
        else:
            self.current -= 1
        self._refresh()

    def action_toggle_remix(self) -> None:
        self.remix = not self.remix
        self._refresh()
        mode = 'remix (niNety nniinE BoOttels)' if self.remix else 'classic'
        self.query_one('#status', Static).update(f'Mode: {mode}')

    def action_reset(self) -> None:
        self.current = self.start_count
        self._refresh()
        self.query_one('#status', Static).update(
            f'Reset to {_bottles_phrase(self.start_count)}.'
        )

    # ----- helpers ---------------------------------------------------------
    def _refresh(self) -> None:
        n = max(0, self.current)
        text = render_verse(n, remix=self.remix, rng=self.rng)
        self.query_one('#lyrics', Static).update(text)
        if n == 0:
            label = 'wraparound verse'
        else:
            label = f'verse {self.start_count - n + 1} of {self.start_count + 1}'
        mode = 'remix' if self.remix else 'classic'
        self.query_one('#meta', Static).update(
            f'{label}  -  bottles left: {n}  -  mode: {mode}'
        )


if __name__ == '__main__':
    BottlesApp().run()
