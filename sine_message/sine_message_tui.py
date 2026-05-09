"""Sine Message — Textual TUI.

Live animated sine-wave text in your terminal. Type a message, tweak amp /
freq / speed with key bindings, toggle a rainbow color cycle, and watch the
phase scroll forever.

Run:
    uv run python sine_message/sine_message_tui.py

Bindings:
    space          pause / resume
    + / =          amplitude up
    -              amplitude down
    ] / [          frequency up / down
    > / <          speed up / down
    c              toggle color cycle
    m              cycle render mode (sine / overlay / lissajous)
    r              reset phase
    Ctrl+Q         quit
"""
from __future__ import annotations

import colorsys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, Static

from sine_message import render, render_lissajous, render_overlay

MODES = ('sine', 'overlay', 'lissajous')
RENDERERS = {
    'sine': render,
    'overlay': render_overlay,
    'lissajous': render_lissajous,
}


class SineMessageApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
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

    #message-row {
        height: 3;
        padding: 0 2;
    }

    #message-row Static {
        width: 10;
        content-align: left middle;
        text-style: bold;
    }

    #message-input {
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #message-input:focus { border: tall #38bdf8; }

    #canvas {
        height: 1fr;
        background: #1e293b;
        color: #38bdf8;
        padding: 1 2;
        text-style: bold;
    }

    #status {
        height: 1;
        padding: 0 2;
        background: #1e293b;
        color: #cbd5e1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding('space', 'toggle_pause', 'Pause', priority=True),
        Binding('plus,equals_sign,equal', 'amp_up', 'Amp +', priority=True),
        Binding('minus', 'amp_down', 'Amp -', priority=True),
        Binding('right_square_bracket', 'freq_up', 'Freq +', priority=True),
        Binding('left_square_bracket', 'freq_down', 'Freq -', priority=True),
        Binding('greater_than_sign', 'speed_up', 'Speed +', priority=True),
        Binding('less_than_sign', 'speed_down', 'Speed -', priority=True),
        Binding('c', 'toggle_color', 'Color', priority=True),
        Binding('m', 'cycle_mode', 'Mode', priority=True),
        Binding('r', 'reset_phase', 'Reset φ', priority=True),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]
    TITLE = 'Sine Message'

    def __init__(self) -> None:
        super().__init__()
        self.message = 'Sine wave scrolling forever ~ '
        self.amplitude = 6.0
        self.frequency = 0.25
        self.speed = 0.1
        self.phase = 0.0
        self.running = True
        self.color_cycle = False
        self.mode = 'sine'

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('SINE MESSAGE', id='title')
        yield Static(
            'Each char sits at y = round(amp · sin(freq·x + phase))',
            id='subtitle')
        with Horizontal(id='message-row'):
            yield Static('Message:')
            yield Input(value=self.message, id='message-input')
        yield Static('', id='canvas', markup=True)
        yield Static('', id='status', markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.set_interval(1 / 20, self._tick)
        self.query_one('#message-input', Input).focus()

    # ---------- input ----------
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'message-input':
            self.message = event.value or 'Sine wave!'
            self._refresh()

    # ---------- bindings ----------
    def action_toggle_pause(self) -> None:
        self.running = not self.running
        self._refresh()

    def action_amp_up(self) -> None:
        self.amplitude = min(20.0, self.amplitude + 1.0)
        self._refresh()

    def action_amp_down(self) -> None:
        self.amplitude = max(1.0, self.amplitude - 1.0)
        self._refresh()

    def action_freq_up(self) -> None:
        self.frequency = min(1.5, self.frequency + 0.05)
        self._refresh()

    def action_freq_down(self) -> None:
        self.frequency = max(0.05, self.frequency - 0.05)
        self._refresh()

    def action_speed_up(self) -> None:
        self.speed = min(0.6, self.speed + 0.02)
        self._refresh()

    def action_speed_down(self) -> None:
        self.speed = max(0.0, self.speed - 0.02)
        self._refresh()

    def action_toggle_color(self) -> None:
        self.color_cycle = not self.color_cycle
        self._refresh()

    def action_cycle_mode(self) -> None:
        idx = MODES.index(self.mode)
        self.mode = MODES[(idx + 1) % len(MODES)]
        self._refresh()

    def action_reset_phase(self) -> None:
        self.phase = 0.0
        self._refresh()

    # ---------- animation ----------
    def _tick(self) -> None:
        if self.running:
            self.phase += self.speed
        self._refresh()

    def _refresh(self) -> None:
        try:
            canvas_widget = self.query_one('#canvas', Static)
        except Exception:
            return
        width = max(40, canvas_widget.size.width - 2)
        renderer = RENDERERS[self.mode]
        try:
            frame = renderer(self.message, width=width,
                             amplitude=self.amplitude,
                             frequency=self.frequency,
                             phase=self.phase)
        except ValueError:
            frame = '(empty message)'

        if self.color_cycle:
            frame = self._colorize(frame)

        canvas_widget.update(frame)
        self.query_one('#status', Static).update(
            f'mode [bold cyan]{self.mode}[/]  •  '
            f'amp [bold]{self.amplitude:.1f}[/]  •  '
            f'freq [bold]{self.frequency:.2f}[/]  •  '
            f'speed [bold]{self.speed:.2f}[/]  •  '
            f'phase [bold]{self.phase:.2f}[/]  •  '
            f'[{"green" if self.running else "yellow"}]'
            f'{"running" if self.running else "paused"}[/]')

    def _colorize(self, frame: str) -> str:
        """Wrap each non-space char with Rich markup using a hue gradient."""
        lines = frame.split('\n')
        width = max((len(ln) for ln in lines), default=1)
        out: list[str] = []
        for line in lines:
            buf: list[str] = []
            for col_idx, ch in enumerate(line):
                if ch == ' ':
                    buf.append(' ')
                    continue
                hue = ((col_idx / max(1, width)) + self.phase * 0.05) % 1.0
                r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
                color = f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
                # Escape any markup-significant chars in the source character.
                safe = ch.replace('[', r'\[')
                buf.append(f'[{color}]{safe}[/]')
            out.append(''.join(buf))
        return '\n'.join(out)


if __name__ == '__main__':
    SineMessageApp().run()
