"""Numeral Systems — Textual TUI.

Multi-base entry panel with live cross-update + Roman numeral row.
Dark Tailwind palette to match the rest of the project.

Bindings:
    Ctrl+Q   quit

Run:
    uv run python numeral_systems/numeral_systems_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from numeral_systems import (
    from_base,
    from_base_fractional,
    from_roman,
    from_twos_complement,
    to_base,
    to_base_fractional,
    to_roman,
    to_twos_complement,
)

# Each numeric base gets a labelled Input. The arbitrary base sits at the
# bottom and is driven by a small "base N" indicator updated via the
# Ctrl+Up / Ctrl+Down bindings.
FIXED_BASES = [
    ('Binary  (2)',   2,  'in-2'),
    ('Octal   (8)',   8,  'in-8'),
    ('Decimal (10)', 10,  'in-10'),
    ('Hex     (16)', 16,  'in-16'),
]


class NumeralApp(App):
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

    .row {
        height: 3;
        margin: 0 2;
    }

    .lbl {
        width: 16;
        color: #94a3b8;
        padding-top: 1;
    }

    Input {
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    Input:focus {
        border: tall #38bdf8;
    }

    #arb-row {
        height: 3;
        margin: 1 2 0 2;
    }

    #arb-label {
        width: 16;
        color: #38bdf8;
        text-style: bold;
        padding-top: 1;
    }

    #roman-row, #twos-row {
        height: 3;
        margin: 0 2;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
        height: 1;
    }

    #status.error {
        color: #f87171;
    }

    #status.ok {
        color: #4ade80;
    }

    #hint {
        text-align: center;
        color: #64748b;
        padding: 1 2 0 2;
        height: 1;
    }
    """

    BINDINGS = [
        Binding('ctrl+q', 'quit', 'Quit'),
        Binding('ctrl+up', 'arb_up', 'Arb base +1'),
        Binding('ctrl+down', 'arb_down', 'Arb base -1'),
    ]

    TITLE = 'Numeral Systems'

    def __init__(self) -> None:
        super().__init__()
        # Source of truth — value typed into one field, projected to all.
        self._value: float | None = 0.0
        self._fractional = False
        self._arb_base = 12
        self._bits = 8
        self._suspend = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('NUMERAL SYSTEMS', id='title')
        yield Static('Type in any base — all the others update live  '
                     '(Ctrl+Up/Down moves arbitrary base, Ctrl+Q quits)',
                     id='subtitle')

        for label, _base, eid in FIXED_BASES:
            with Horizontal(classes='row'):
                yield Static(label, classes='lbl')
                yield Input(value='', id=eid)

        # Arbitrary base
        with Horizontal(id='arb-row'):
            yield Static(f'Base {self._arb_base:>3}', id='arb-label')
            yield Input(value='', id='in-arb')

        # Roman numeral
        with Horizontal(id='roman-row'):
            yield Static('Roman    ', classes='lbl')
            yield Input(value='', id='in-roman')

        # Two's complement
        with Horizontal(id='twos-row'):
            yield Static(f"2's ({self._bits}b)", classes='lbl', id='twos-lbl')
            yield Input(value='', id='in-twos')

        yield Static('', id='status')
        yield Static("Tip: '0.625' in decimal = '0.101' in binary  "
                     "•  Roman accepts 1..3999  •  2's complement: 8 bits",
                     id='hint')
        yield Footer()

    def on_mount(self) -> None:
        # Seed with a recognisable demo value so all fields show something.
        self._value = 255.0
        self._fractional = False
        self._refresh_all(source=None)
        self.query_one('#in-10', Input).focus()

    # --------------------------------------------------------------- events
    def on_input_changed(self, event: Input.Changed) -> None:
        if self._suspend:
            return
        eid = event.input.id
        text = event.value.strip()

        if eid == 'in-roman':
            self._handle_roman(text)
        elif eid == 'in-twos':
            self._handle_twos(text)
        elif eid == 'in-arb':
            self._handle_numeric(text, self._arb_base, source=eid)
        else:
            # in-2, in-8, in-10, in-16
            base = int(eid.split('-')[1])
            self._handle_numeric(text, base, source=eid)

    def action_arb_up(self) -> None:
        self._set_arb(min(36, self._arb_base + 1))

    def action_arb_down(self) -> None:
        self._set_arb(max(2, self._arb_base - 1))

    # ----------------------------------------------------------------- core
    def _handle_numeric(self, text: str, base: int, *, source: str) -> None:
        if not text:
            self._value = 0.0
            self._fractional = False
            self._set_status('', kind='ok')
            self._refresh_all(source=source)
            return
        try:
            if '.' in text:
                v = from_base_fractional(text, base)
                self._value = v
                self._fractional = v != int(v)
            else:
                self._value = float(from_base(text, base))
                self._fractional = False
            self._set_status(f'parsed {text!r} in base {base}', kind='ok')
            self._refresh_all(source=source)
        except ValueError as exc:
            self._value = None
            self._set_status(str(exc), kind='error')
            self._refresh_all(source=source)

    def _handle_roman(self, text: str) -> None:
        if not text:
            self._value = 0.0
            self._fractional = False
            self._set_status('', kind='ok')
            self._refresh_all(source='in-roman')
            return
        try:
            n = from_roman(text)
            self._value = float(n)
            self._fractional = False
            self._set_status(f'roman {text.upper()} = {n}', kind='ok')
            self._refresh_all(source='in-roman')
        except ValueError as exc:
            self._value = None
            self._set_status(str(exc), kind='error')
            self._refresh_all(source='in-roman')

    def _handle_twos(self, text: str) -> None:
        text = text.replace(' ', '')
        if not text:
            return
        try:
            n = from_twos_complement(text)
            self._value = float(n)
            self._fractional = False
            self._bits = max(self._bits, len(text))
            self._set_status(f"two's complement {text} = {n}", kind='ok')
            self._refresh_all(source='in-twos')
        except ValueError as exc:
            self._set_status(str(exc), kind='error')

    def _set_arb(self, b: int) -> None:
        self._arb_base = b
        self.query_one('#arb-label', Static).update(f'Base {b:>3}')
        self._refresh_all(source=None)

    def _refresh_all(self, *, source: str | None) -> None:
        self._suspend = True
        try:
            for _label, base, eid in FIXED_BASES:
                if eid != source:
                    self._set_input(eid, self._render_base(base))
            if source != 'in-arb':
                self._set_input('in-arb', self._render_base(self._arb_base))
            if source != 'in-roman':
                self._set_input('in-roman', self._render_roman())
            if source != 'in-twos':
                self._set_input('in-twos', self._render_twos())
        finally:
            self._suspend = False

    def _set_input(self, widget_id: str, value: str) -> None:
        widget = self.query_one(f'#{widget_id}', Input)
        if widget.value != value:
            widget.value = value

    def _render_base(self, base: int) -> str:
        if self._value is None:
            return ''
        if self._fractional:
            return to_base_fractional(self._value, base)
        return to_base(int(self._value), base)

    def _render_roman(self) -> str:
        if self._value is None or self._fractional:
            return ''
        n = int(self._value)
        if not 1 <= n <= 3999:
            return ''
        try:
            return to_roman(n)
        except ValueError:
            return ''

    def _render_twos(self) -> str:
        if self._value is None or self._fractional:
            return ''
        try:
            return to_twos_complement(int(self._value), self._bits)
        except ValueError:
            return f'(out of {self._bits}-bit range)'

    def _set_status(self, msg: str, *, kind: str) -> None:
        status = self.query_one('#status', Static)
        status.update(msg)
        status.set_classes(kind)


if __name__ == '__main__':
    NumeralApp().run()
