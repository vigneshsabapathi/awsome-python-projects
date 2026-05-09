"""Countdown — Textual TUI.

Big seven-segment ASCII display, time input, Start/Pause/Reset bindings.
Color shifts red when fewer than 10 seconds remain. Optional Pomodoro
(25m / 5m × 4) toggle as the spec twist.

Run:
    uv run python countdown/countdown_tui.py

Bindings:
    s      Start
    p      Pause
    r      Reset
    t      Toggle Pomodoro
    Ctrl+Q Quit
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from countdown import render_clock


class CountdownApp(App):
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

    #display {
        content-align: center middle;
        text-align: center;
        text-style: bold;
        color: #38bdf8;
        background: #111827;
        height: 7;
        margin: 1 4;
        padding: 1;
    }

    .display-warn { color: #f87171; }
    .display-done { color: #34d399; }

    #controls {
        align-horizontal: center;
        height: auto;
        padding: 0 4;
    }

    #input {
        width: 28;
        margin: 0 2;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus {
        border: tall #38bdf8;
    }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-warn  { color: #fbbf24; text-style: bold; }
    .status-error { color: #f87171; text-style: bold; }
    .status-done  { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('s', 'start', 'Start'),
        Binding('p', 'pause', 'Pause'),
        Binding('r', 'reset', 'Reset'),
        Binding('t', 'toggle_pomodoro', 'Pomodoro'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Countdown'

    def __init__(self) -> None:
        super().__init__()
        self.total_seconds: int = 60
        self.remaining: int = 60
        self.running: bool = False
        self.pomodoro: bool = False
        self.pomo_phase: str = 'work'
        self.pomo_cycle: int = 1
        self.pomo_total: int = 4
        self._timer = None  # type: ignore[var-annotated]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('COUNTDOWN', id='title')
        yield Static('Seven-segment ASCII timer (s/p/r, t for Pomodoro)',
                     id='subtitle')
        yield Static(render_clock(self.remaining), id='display')
        with Horizontal(id='controls'):
            yield Input(placeholder='MM:SS or seconds', id='input',
                        value='01:00')
        yield Static('Ready.', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_display()

    # -------------------------------------------------------- helpers
    def _refresh_display(self) -> None:
        display = self.query_one('#display', Static)
        display.update(render_clock(self.remaining))
        if self.remaining <= 0:
            display.set_classes('display-done')
        elif self.remaining < 10:
            display.set_classes('display-warn')
        else:
            display.set_classes('')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def _parse(self, raw: str) -> int | None:
        raw = raw.strip()
        if not raw:
            return None
        try:
            if ':' in raw:
                m, s = raw.split(':', 1)
                total = int(m) * 60 + int(s)
            else:
                total = int(raw)
        except ValueError:
            return None
        return total if total > 0 else None

    def _phase_label(self) -> str:
        if not self.pomodoro:
            return 'Countdown'
        return (f'Pomodoro {self.pomo_phase} '
                f'({self.pomo_cycle}/{self.pomo_total})')

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None

    def _start_timer(self) -> None:
        self._stop_timer()
        self._timer = self.set_interval(1.0, self._tick)

    # -------------------------------------------------------- pomodoro
    def _advance_pomodoro(self) -> bool:
        if self.pomo_phase == 'work':
            self.pomo_phase = 'break'
            self.total_seconds = 5 * 60
        else:
            self.pomo_phase = 'work'
            self.pomo_cycle += 1
            if self.pomo_cycle > self.pomo_total:
                return False
            self.total_seconds = 25 * 60
        self.remaining = self.total_seconds
        return True

    # ------------------------------------------------------------ tick
    def _tick(self) -> None:
        if not self.running:
            return
        self.remaining -= 1
        self._refresh_display()
        if self.remaining <= 0:
            self.bell()
            if self.pomodoro and self._advance_pomodoro():
                self._refresh_display()
                self._set_status(self._phase_label() + ' — running…')
                return
            self.running = False
            self._stop_timer()
            self._set_status('Time is up!', 'done')

    # --------------------------------------------------------- actions
    def action_start(self) -> None:
        if self.running:
            return
        if self.remaining <= 0:
            raw = self.query_one('#input', Input).value
            total = self._parse(raw)
            if total is None:
                self._set_status('Enter MM:SS or a positive integer.', 'error')
                return
            self.total_seconds = total
            self.remaining = total
            if self.pomodoro:
                self.pomo_phase = 'work'
                self.pomo_cycle = 1
                self.total_seconds = 25 * 60
                self.remaining = self.total_seconds
        self.running = True
        self._set_status(self._phase_label() + ' — running…')
        self._refresh_display()
        self._start_timer()

    def action_pause(self) -> None:
        if not self.running:
            return
        self.running = False
        self._stop_timer()
        self._set_status('Paused.', 'warn')

    def action_reset(self) -> None:
        self.running = False
        self._stop_timer()
        raw = self.query_one('#input', Input).value
        total = self._parse(raw) or 60
        self.total_seconds = total
        self.remaining = total
        if self.pomodoro:
            self.pomo_phase = 'work'
            self.pomo_cycle = 1
            self.total_seconds = 25 * 60
            self.remaining = self.total_seconds
        self._refresh_display()
        self._set_status('Reset.')

    def action_toggle_pomodoro(self) -> None:
        self.pomodoro = not self.pomodoro
        if self.pomodoro:
            self.pomo_phase = 'work'
            self.pomo_cycle = 1
            self.total_seconds = 25 * 60
            self.remaining = self.total_seconds
            self._set_status('Pomodoro: 25m / 5m × 4 enabled.')
        else:
            self._set_status('Manual mode.')
        self._refresh_display()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        total = self._parse(event.value)
        if total is None:
            self._set_status('Enter MM:SS or a positive integer.', 'error')
            return
        self.total_seconds = total
        self.remaining = total
        self._refresh_display()
        self._set_status(f'Set to {total // 60:02d}:{total % 60:02d}.')


if __name__ == '__main__':
    CountdownApp().run()
