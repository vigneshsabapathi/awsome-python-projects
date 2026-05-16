"""Digital Stream — Textual TUI.

Matrix-style falling green digital rain in the terminal using Rich colour spans.

Bindings:
  space    pause / resume
  +  / -   faster / slower
  c        cycle charset (katakana → digits → latin → …)
  Ctrl+Q   quit

Run:
    uv run python digital_stream/digital_stream_tui.py
"""
from __future__ import annotations

import shutil

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from digital_stream import CHARSETS, Rain

# ---------------------------------------------------------------------------
# Colour palette (Rich colour strings)
# ---------------------------------------------------------------------------
HEAD_COLOR = 'rgb(200,255,200)'
TAIL_COLORS = [
    'rgb(57,255,20)',    # depth 1 — neon green
    'rgb(0,220,0)',      # depth 2
    'rgb(0,185,0)',      # depth 3
    'rgb(0,150,0)',      # depth 4
    'rgb(0,115,0)',      # depth 5
    'rgb(0,80,0)',       # depth 6
    'rgb(0,50,0)',       # depth 7
    'rgb(0,30,0)',       # depth 8+
]

CHARSETS_LIST = list(CHARSETS.keys())


def _rich_color(depth: int) -> str:
    if depth == 0:
        return HEAD_COLOR
    return TAIL_COLORS[min(depth - 1, len(TAIL_COLORS) - 1)]


class StreamDisplay(Static):
    """Full-screen widget that holds the rain frame."""
    DEFAULT_CSS = """
    StreamDisplay {
        width: 100%;
        height: 1fr;
        overflow: hidden hidden;
    }
    """


class DigitalStreamApp(App):
    CSS = """
    Screen {
        background: #000000;
        color: #39ff14;
    }
    #title {
        text-align: center;
        text-style: bold;
        color: #39ff14;
        padding: 0 1;
        height: 1;
    }
    #status {
        text-align: center;
        color: #1a5c1a;
        height: 1;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding('space', 'toggle_pause', 'Pause'),
        Binding('plus,equal', 'faster', 'Faster'),
        Binding('minus', 'slower', 'Slower'),
        Binding('c', 'cycle_charset', 'Charset'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Digital Stream'

    def __init__(self) -> None:
        super().__init__()
        self._fps: float = 15.0
        self._paused: bool = False
        self._charset_idx: int = 0
        self._rain: Rain | None = None
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static('', id='title')
        yield StreamDisplay(id='display')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._init_rain()
        self._update_status()
        self._restart_timer()

    def _init_rain(self) -> None:
        # Query widget size; fall back to terminal size.
        try:
            display = self.query_one('#display', StreamDisplay)
            cols = display.size.width or shutil.get_terminal_size((80, 24)).columns
            rows = display.size.height or (shutil.get_terminal_size((80, 24)).lines - 4)
        except Exception:
            cols, rows = shutil.get_terminal_size((80, 24))
            rows = max(5, rows - 4)
        cols = max(10, cols)
        rows = max(3, rows)
        charset = CHARSETS_LIST[self._charset_idx]
        self._rain = Rain(width=cols, height=rows,
                          density=0.03, charset=charset)

    # ------------------------------------------------------------------
    # Timer / tick
    # ------------------------------------------------------------------
    def _restart_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        interval = 1.0 / max(1.0, self._fps)
        self._timer = self.set_interval(interval, self._tick)

    def _tick(self) -> None:
        if self._paused or self._rain is None:
            return
        self._rain.step()
        self._render_frame()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def _render_frame(self) -> None:
        if self._rain is None:
            return
        rain = self._rain
        rows = rain.height
        cols = rain.width

        # Build depth grid.
        grid: list[list[tuple[str, int] | None]] = [
            [None] * cols for _ in range(rows)
        ]
        for drop in rain.drops:
            head = drop.head_row
            for depth, ch in enumerate(drop.chars):
                row = head - depth
                if 0 <= row < rows and 0 <= drop.col < cols:
                    existing = grid[row][drop.col]
                    if existing is None or depth < existing[1]:
                        grid[row][drop.col] = (ch, depth)

        out = Text()
        for r, row_data in enumerate(grid):
            for cell in row_data:
                if cell is None:
                    out.append(' ')
                else:
                    ch, depth = cell
                    out.append(ch, style=_rich_color(depth))
            if r < rows - 1:
                out.append('\n')

        try:
            self.query_one('#display', StreamDisplay).update(out)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_toggle_pause(self) -> None:
        self._paused = not self._paused
        self._update_status()

    def action_faster(self) -> None:
        self._fps = min(60.0, self._fps + 2.0)
        self._restart_timer()
        self._update_status()

    def action_slower(self) -> None:
        self._fps = max(1.0, self._fps - 2.0)
        self._restart_timer()
        self._update_status()

    def action_cycle_charset(self) -> None:
        self._charset_idx = (self._charset_idx + 1) % len(CHARSETS_LIST)
        name = CHARSETS_LIST[self._charset_idx]
        if self._rain is not None:
            self._rain.set_charset(name)
        self._update_status()
        self._render_frame()

    def _update_status(self) -> None:
        charset = CHARSETS_LIST[self._charset_idx]
        state = 'paused' if self._paused else 'running'
        msg = (f'charset: {charset} | fps: {self._fps:.0f} | {state}  '
               f'[space pause | +/- speed | c charset | ctrl+q quit]')
        try:
            self.query_one('#status', Static).update(msg)
        except Exception:
            pass

    def on_resize(self, event) -> None:  # type: ignore[override]
        # Re-init rain to fit the new terminal size.
        self._init_rain()

    # ------------------------------------------------------------------
    # Title bar
    # ------------------------------------------------------------------
    def on_mount_title(self) -> None:
        pass

    def _set_title(self) -> None:
        try:
            self.query_one('#title', Static).update('DIGITAL STREAM')
        except Exception:
            pass

    def on_ready(self) -> None:
        self._set_title()
        self._render_frame()


if __name__ == '__main__':
    DigitalStreamApp().run()
