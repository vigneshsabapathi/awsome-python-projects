"""Soroban — Textual TUI.

A modern terminal abacus. Type a number and press Enter — the soroban
re-renders. Press Ctrl+A to start an addition animation; Ctrl+Q to quit.

Run:
    uv run python soroban/soroban_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from soroban import DEFAULT_COLUMNS, parse, render

DARK_BG = '#0f172a'
PANEL = '#1e293b'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
ACTIVE = '#f97316'


class SorobanApp(App):
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

    #board {
        align-horizontal: center;
        width: auto;
        height: auto;
        background: #1e293b;
        border: tall #334155;
        padding: 1 2;
        margin: 1 2;
    }

    #soroban {
        width: auto;
        height: auto;
        color: #f5deb3;
        text-style: bold;
    }

    #input-row {
        height: 3;
        align-horizontal: center;
        margin: 1 2;
    }

    #number {
        width: 40;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #number:focus { border: tall #38bdf8; }

    #parsed-back {
        height: 3;
        align-horizontal: center;
        margin: 0 2;
    }

    #status {
        text-align: center;
        padding: 1;
        color: #38bdf8;
        text-style: bold;
    }

    .err { color: #f87171; }
    .ok  { color: #34d399; }
    """

    BINDINGS = [
        Binding('ctrl+q', 'quit', 'Quit'),
        Binding('ctrl+a', 'animate', 'Animate +'),
        Binding('ctrl+l', 'clear', 'Clear'),
    ]

    TITLE = 'Soroban'

    def __init__(self, columns: int = DEFAULT_COLUMNS) -> None:
        super().__init__()
        self.columns = columns
        self.value: int = 0
        self._anim_pending: list[int] = []  # remaining digit-place addends

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('SOROBAN', id='title')
        yield Static('Japanese abacus — type a number, Enter to render. '
                     'Ctrl+A: animate +N. Ctrl+Q: quit.',
                     id='subtitle')
        with Vertical(id='board'):
            yield Static(render(0, self.columns), id='soroban')
        with Horizontal(id='input-row'):
            yield Input(placeholder='enter number (or "+N" to animate)',
                        id='number')
        yield Static('parsed back: 0', id='parsed-back')
        yield Static('value: 0', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#number', Input).focus()
        self._refresh()

    # ------------------------------------------------------------------
    def _refresh(self, message: str | None = None,
                 kind: str = 'ok') -> None:
        soroban_widget = self.query_one('#soroban', Static)
        soroban_widget.update(render(self.value, self.columns))
        # roundtrip for confidence
        try:
            back = parse(render(self.value, self.columns))
        except Exception:
            back = -1
        self.query_one('#parsed-back', Static).update(
            f'parsed back: {back}  (matches: {back == self.value})')
        status = self.query_one('#status', Static)
        if message is None:
            message = f'value: {self.value}'
        status.update(message)
        status.set_classes('' if kind == 'ok' else 'err')

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        if text.startswith('+'):
            # Treat "+N" as: animate adding N to current value
            try:
                addend = int(text[1:])
            except ValueError:
                self._refresh('not a number after +', kind='err')
                return
            if addend < 0:
                self._refresh('addend must be non-negative', kind='err')
                return
            self._begin_animation(addend)
            event.input.value = ''
            return
        if not text.lstrip('-').isdecimal() or text.startswith('-'):
            self._refresh('non-negative integers only', kind='err')
            return
        n = int(text)
        if len(str(n)) > self.columns:
            self._refresh(f'too many digits — max {self.columns}', kind='err')
            return
        self.value = n
        event.input.value = ''
        self._refresh()

    # ------------------------------------------------------------------
    # Animation: "+N" steps through digit places
    # ------------------------------------------------------------------
    def action_animate(self) -> None:
        # Default: animate +123 if the user hasn't typed anything special.
        # If the input contains "+N" we already handle on submit.
        self._begin_animation(123)

    def _begin_animation(self, addend: int) -> None:
        if addend == 0:
            return
        # Build the list of place-by-place addends from least significant
        s = str(addend).rjust(self.columns, '0')
        self._anim_pending = []
        for place_index, ch in enumerate(reversed(s)):
            d = int(ch)
            if d:
                self._anim_pending.append(d * (10 ** place_index))
        self._anim_total_target = self.value + addend
        self._refresh(
            f'animating + {addend} → {self._anim_total_target}', kind='ok')
        self.set_timer(0.55, self._animation_step)

    def _animation_step(self) -> None:
        if not self._anim_pending:
            self._refresh(
                f'value: {self.value}  (animation complete)', kind='ok')
            return
        delta = self._anim_pending.pop(0)
        self.value += delta
        if len(str(self.value)) > self.columns:
            # Overflow → cap and stop
            self.value = 10 ** self.columns - 1
            self._refresh('overflow — animation stopped', kind='err')
            self._anim_pending = []
            return
        self._refresh(f'+ {delta}  →  {self.value}', kind='ok')
        if self._anim_pending:
            self.set_timer(0.55, self._animation_step)
        else:
            self.set_timer(0.55,
                           lambda: self._refresh(
                               f'value: {self.value}  '
                               '(animation complete)', kind='ok'))

    def action_clear(self) -> None:
        self.value = 0
        self.query_one('#number', Input).value = ''
        self._refresh('cleared', kind='ok')


def main() -> None:
    SorobanApp().run()


if __name__ == '__main__':
    main()
