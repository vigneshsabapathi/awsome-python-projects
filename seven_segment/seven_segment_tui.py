"""Seven-Segment Display — Textual TUI.

A dark Tailwind-themed terminal UI: type into the input, watch the text
render live in giant seven-segment ASCII. Press 'c' to cycle through
LCD/LED color presets; Ctrl+Q to quit.

Run:
    uv run python seven_segment/seven_segment_tui.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, Static

# Allow ``from seven_segment import …`` whether launched from repo root
# or from inside the ``seven_segment/`` folder.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from seven_segment import render  # noqa: E402

# Color presets: (label, foreground/segment color, background panel color).
PRESETS: list[tuple[str, str, str]] = [
    ('LCD green', '#22c55e', '#0a0f0a'),
    ('LED red',   '#ef4444', '#120606'),
    ('LED amber', '#f59e0b', '#120c02'),
    ('Cyan',      '#22d3ee', '#04181c'),
    ('Magenta',   '#ec4899', '#1a0612'),
]


class SevenSegApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
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

    #panel {
        height: 1fr;
        margin: 1 2;
        padding: 2 4;
        border: round #334155;
        background: #0a0f0a;
    }

    #display {
        text-style: bold;
        color: #22c55e;
        background: #0a0f0a;
        content-align: center middle;
        height: 1fr;
        width: 100%;
    }

    #input {
        margin: 0 2 1 2;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus { border: tall #38bdf8; }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 0 1 0;
    }
    """

    BINDINGS = [
        Binding('c', 'cycle_color', 'Cycle color'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Seven-Segment Display'

    def __init__(self) -> None:
        super().__init__()
        self._preset_idx: int = 0
        self._initial_text: str = 'PI = 3.14'

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('SEVEN-SEGMENT DISPLAY', id='title')
        yield Static('LCD / LED ASCII renderer — press c to cycle colors',
                     id='subtitle')
        with Vertical(id='panel'):
            yield Static('', id='display')
        yield Input(placeholder='Type anything…', id='input',
                    value=self._initial_text)
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._apply_preset()
        self._refresh_display(self._initial_text)
        self.query_one('#input', Input).focus()

    # ---------------------------------------------------------- handlers
    def on_input_changed(self, event: Input.Changed) -> None:
        self._refresh_display(event.value)

    def action_cycle_color(self) -> None:
        self._preset_idx = (self._preset_idx + 1) % len(PRESETS)
        self._apply_preset()

    # ---------------------------------------------------------- helpers
    def _apply_preset(self) -> None:
        name, fg, bg = PRESETS[self._preset_idx]
        display = self.query_one('#display', Static)
        panel = self.query_one('#panel', Vertical)
        display.styles.color = fg
        display.styles.background = bg
        panel.styles.background = bg
        self.query_one('#status', Static).update(
            f'Preset: {name}   ({self._preset_idx + 1}/{len(PRESETS)})')

    def _refresh_display(self, text: str) -> None:
        art = render(text) if text else render(' ')
        self.query_one('#display', Static).update(art)


if __name__ == '__main__':
    SevenSegApp().run()
