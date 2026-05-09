"""ROT13 Cipher — Textual TUI.

Two-pane terminal editor with live ROT13 preview and a self-inverse demo.

Bindings:
    Ctrl+R   re-apply rot13 to the current INPUT (input ← output)
    Ctrl+T   toggle rot13 / rot47 variant
    Ctrl+D   self-inverse demo (apply twice → original)
    Ctrl+Q   quit

Run:
    uv run python rot13/rot13_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static, TextArea

from rot13 import rot13, rot47


class Rot13App(App):
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

    .section-label {
        color: #94a3b8;
        padding: 1 2 0 2;
    }

    TextArea {
        margin: 0 2;
        height: 1fr;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    TextArea:focus {
        border: tall #38bdf8;
    }

    #output {
        color: #38bdf8;
    }

    #variant-bar {
        height: 1;
        margin: 1 2 0 2;
    }

    .chip {
        padding: 0 2;
        margin-right: 1;
        background: #1e293b;
        color: #94a3b8;
    }
    .chip-active {
        background: #38bdf8;
        color: #0f172a;
        text-style: bold;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding('ctrl+r', 're_apply', 'Re-apply'),
        Binding('ctrl+t', 'toggle_variant', 'rot13/rot47'),
        Binding('ctrl+d', 'self_inverse', 'Self-inverse demo'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'ROT13 Cipher'

    variant: reactive[str] = reactive('rot13')

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('ROT13 CIPHER', id='title')
        yield Static('Shift letters by 13 — encrypt = decrypt (self-inverse)  '
                     '· Ctrl+R re-apply · Ctrl+T toggle variant · '
                     'Ctrl+D demo · Ctrl+Q quit',
                     id='subtitle')

        with Vertical(id='variant-bar'):
            # Filled in compose so we can update class lists on toggle.
            pass

        yield Static('Input', classes='section-label')
        yield TextArea('Hello, World!', id='input')

        yield Static('Output (live)', classes='section-label')
        yield TextArea('', id='output', read_only=True)

        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        # Build the variant chips — Static widgets, since SegmentedButton
        # isn't a native Textual primitive.
        bar = self.query_one('#variant-bar', Vertical)
        bar.remove_children()
        bar.mount(Static('rot13', id='chip-rot13', classes='chip chip-active'))
        bar.mount(Static('  rot47', id='chip-rot47', classes='chip'))

        self._refresh()
        self.query_one('#input', TextArea).focus()

    # ----------------------------------------------------------- actions
    def action_toggle_variant(self) -> None:
        self.variant = 'rot47' if self.variant == 'rot13' else 'rot13'
        self.query_one('#chip-rot13', Static).set_classes(
            'chip chip-active' if self.variant == 'rot13' else 'chip'
        )
        self.query_one('#chip-rot47', Static).set_classes(
            'chip chip-active' if self.variant == 'rot47' else 'chip'
        )
        self._refresh()

    def action_re_apply(self) -> None:
        """Move output back into input — applying again returns the original."""
        out_widget = self.query_one('#output', TextArea)
        in_widget = self.query_one('#input', TextArea)
        in_widget.load_text(out_widget.text)
        self._refresh()

    def action_self_inverse(self) -> None:
        text = self.query_one('#input', TextArea).text
        fn = rot13 if self.variant == 'rot13' else rot47
        ok = fn(fn(text)) == text
        self.query_one('#status', Static).update(
            f'self-inverse demo: apply twice → {"IDENTITY ✓" if ok else "MISMATCH"}    '
            f'(input is unchanged after a round-trip through {self.variant})'
        )

    # -------------------------------------------------------- input wiring
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == 'input':
            self._refresh()

    # -------------------------------------------------------------- core
    def _refresh(self) -> None:
        text = self.query_one('#input', TextArea).text
        fn = rot13 if self.variant == 'rot13' else rot47
        result = fn(text)
        out = self.query_one('#output', TextArea)
        out.load_text(result)

        letters = sum(1 for c in text if c.isalpha())
        self.query_one('#status', Static).update(
            f'variant: {self.variant}  ·  '
            f'chars: {len(text)}  letters: {letters}  ·  '
            f'apply twice → original (involution)'
        )


if __name__ == '__main__':
    Rot13App().run()
