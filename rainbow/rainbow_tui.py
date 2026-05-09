"""Rainbow — Textual TUI.

Live rainbow animation in the terminal using Rich color spans.

Modes (cycle with `m`):
  gradient — per-character HSV cycling text
  arc      — multi-line ASCII rainbow arc, hues scroll
  bands    — stacked solid-color horizontal bands
  lolcat   — text scroll with a per-line phase shift

Bindings:
  space   pause / resume
  m       next mode
  +  / -  faster / slower
  Ctrl+Q  quit

Run:
    uv run python rainbow/rainbow_tui.py
"""
from __future__ import annotations

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, Static

from rainbow import _strip_ansi, hsv_to_rgb, rainbow_arc

MODES = ('gradient', 'arc', 'bands', 'lolcat')


def _rgb(h: float) -> str:
    r, g, b = hsv_to_rgb(h, 1.0, 1.0)
    return f'rgb({r},{g},{b})'


class RainbowApp(App):
    CSS = """
    Screen {
        background: #0b0f1a;
        color: #f8fafc;
    }
    #title {
        text-align: center;
        text-style: bold;
        padding: 1 0 0 0;
    }
    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }
    #stage {
        height: 1fr;
        align: center middle;
        padding: 1 2;
    }
    #display {
        text-align: center;
        height: 1fr;
        width: 100%;
    }
    #input {
        margin: 1 6;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus { border: tall #38bdf8; }
    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 1 1 1;
    }
    """

    BINDINGS = [
        Binding('space', 'toggle_pause', 'Pause'),
        Binding('m', 'cycle_mode', 'Mode'),
        Binding('plus,equals_sign,equal', 'faster', 'Faster'),
        Binding('minus', 'slower', 'Slower'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]
    TITLE = 'Rainbow'

    def __init__(self) -> None:
        super().__init__()
        self.text: str = 'RAINBOW'
        self.mode_idx: int = 0
        self.fps: float = 15.0
        self.offset: float = 0.0
        self.paused: bool = False
        self._timer = None
        self._arc = _strip_ansi(rainbow_arc(width=72)).splitlines()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('RAINBOW', id='title')
        yield Static('space pause | m mode | +/- speed | ctrl+q quit',
                     id='subtitle')
        with Vertical(id='stage'):
            yield Static('', id='display')
        yield Input(placeholder='Type text and press Enter…',
                    id='input', value=self.text)
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._update_status()
        self._render_frame()
        self._restart_timer()

    # ---- timer -------------------------------------------------------------
    def _restart_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        interval = 1.0 / max(1.0, self.fps)
        self._timer = self.set_interval(interval, self._tick)

    def _tick(self) -> None:
        if not self.paused:
            self.offset = (self.offset + 1.0 / 30.0) % 1.0
        self._render_frame()

    # ---- rendering ---------------------------------------------------------
    def _render_frame(self) -> None:
        mode = MODES[self.mode_idx]
        if mode == 'gradient':
            content = self._render_gradient(self.text)
        elif mode == 'arc':
            content = self._render_arc()
        elif mode == 'bands':
            content = self._render_bands()
        else:
            content = self._render_lolcat(self.text)
        try:
            self.query_one('#display', Static).update(content)
        except Exception:
            pass

    def _render_gradient(self, text: str) -> Text:
        out = Text()
        for i, ch in enumerate(text):
            hue = self.offset + i / 14.0
            if ch == '\n':
                out.append('\n')
            else:
                out.append(ch, style=_rgb(hue))
        return out

    def _render_lolcat(self, text: str) -> Text:
        out = Text()
        # Repeat the text vertically for visual fill.
        lines = (text + ' ').splitlines() if '\n' in text else [text] * 5
        for r, line in enumerate(lines):
            for c, ch in enumerate(line):
                hue = self.offset + (c + r * 3) / 18.0
                out.append(ch, style=_rgb(hue))
            out.append('\n')
        return out

    def _render_arc(self) -> Text:
        out = Text()
        for r, row in enumerate(self._arc):
            for c, ch in enumerate(row):
                if ch == ' ':
                    out.append(' ')
                else:
                    hue = self.offset + (r + c) / 28.0
                    out.append(ch, style=_rgb(hue))
            out.append('\n')
        return out

    def _render_bands(self) -> Text:
        out = Text()
        width = 72
        for r in range(10):
            hue = self.offset + r / 10.0
            out.append('█' * width, style=_rgb(hue))
            out.append('\n')
        return out

    # ---- actions -----------------------------------------------------------
    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._update_status()

    def action_cycle_mode(self) -> None:
        self.mode_idx = (self.mode_idx + 1) % len(MODES)
        self._update_status()
        self._render_frame()

    def action_faster(self) -> None:
        self.fps = min(60.0, self.fps + 2.0)
        self._restart_timer()
        self._update_status()

    def action_slower(self) -> None:
        self.fps = max(1.0, self.fps - 2.0)
        self._restart_timer()
        self._update_status()

    def _update_status(self) -> None:
        try:
            self.query_one('#status', Static).update(
                f'mode: {MODES[self.mode_idx]} | fps: {self.fps:.0f} | '
                f'{"paused" if self.paused else "running"}')
        except Exception:
            pass

    # ---- input -------------------------------------------------------------
    def on_input_submitted(self, event: Input.Submitted) -> None:
        value = event.value.strip()
        if value:
            self.text = value
        event.input.value = ''
        self._render_frame()


if __name__ == '__main__':
    RainbowApp().run()
