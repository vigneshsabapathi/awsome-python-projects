"""Pig Latin — Textual TUI.

Modern dark terminal UI with two stacked panes (input + output) and live
update on every keystroke. Switch direction (encode / decode) with Ctrl+S
and cycle through modes (``pig`` -> ``greek`` -> ``ubbi``) with Ctrl+M.

Bindings:
    Ctrl+S  swap encode/decode
    Ctrl+M  cycle mode
    Ctrl+Q  quit

Run:
    uv run python pig_latin/pig_latin_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Static, TextArea

from pig_latin import MODES, translate, untranslate


class PigLatinApp(App):
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
        padding: 0 2;
    }

    #mode-bar {
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

    TextArea {
        margin: 0 2 1 2;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
        height: 1fr;
    }
    TextArea:focus {
        border: tall #38bdf8;
    }

    #output {
        color: #38bdf8;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding('ctrl+s', 'swap_direction', 'Swap enc/dec'),
        Binding('ctrl+m', 'cycle_mode', 'Cycle mode'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Pig Latin'

    direction: reactive[str] = reactive('encode')
    mode: reactive[str] = reactive('pig')

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('PIG LATIN', id='title')
        yield Static('Move leading consonants + "ay"  •  Vowel start + "way"'
                     '  —  Ctrl+S swap, Ctrl+M cycle mode, Ctrl+Q quit',
                     id='subtitle')

        with Horizontal(id='mode-bar'):
            yield Static('encode', id='chip-encode',
                         classes='chip chip-active')
            yield Static('decode', id='chip-decode', classes='chip')
            yield Static('  mode:', classes='chip')
            yield Static('pig', id='chip-pig', classes='chip chip-active')
            yield Static('greek', id='chip-greek', classes='chip')
            yield Static('ubbi', id='chip-ubbi', classes='chip')

        yield Static('Input', classes='section-label', id='input-label')
        yield TextArea('The quick brown fox jumps over the lazy dog.',
                       id='input', show_line_numbers=False)

        yield Static('Output', classes='section-label', id='output-label')
        yield TextArea('', id='output', show_line_numbers=False, read_only=True)

        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.query_one('#input', TextArea).focus()

    # ------------------------------------------------------------- actions
    def action_swap_direction(self) -> None:
        self.direction = 'decode' if self.direction == 'encode' else 'encode'
        self._update_chips()
        self._update_labels()
        self._refresh()

    def action_cycle_mode(self) -> None:
        i = MODES.index(self.mode)
        self.mode = MODES[(i + 1) % len(MODES)]
        self._update_chips()
        self._refresh()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == 'input':
            self._refresh()

    # ---------------------------------------------------------------- core
    def _update_chips(self) -> None:
        for direction in ('encode', 'decode'):
            chip = self.query_one(f'#chip-{direction}', Static)
            chip.set_classes('chip chip-active' if self.direction == direction
                             else 'chip')
        for mode in MODES:
            chip = self.query_one(f'#chip-{mode}', Static)
            chip.set_classes('chip chip-active' if self.mode == mode
                             else 'chip')

    def _update_labels(self) -> None:
        if self.direction == 'encode':
            self.query_one('#input-label', Static).update('Input  (English)')
            self.query_one('#output-label',
                           Static).update('Output  (Pig Latin)')
        else:
            self.query_one('#input-label',
                           Static).update('Input  (Pig Latin)')
            self.query_one('#output-label', Static).update('Output  (English)')

    def _refresh(self) -> None:
        text = self.query_one('#input', TextArea).text
        if self.direction == 'encode':
            result = translate(text, mode=self.mode)
        else:
            result = untranslate(text, mode=self.mode)

        out = self.query_one('#output', TextArea)
        out.text = result

        letters = sum(1 for c in text if c.isalpha())
        self.query_one('#status', Static).update(
            f'direction: {self.direction}  mode: {self.mode}  '
            f'chars: {len(text)}  letters: {letters}'
        )


if __name__ == '__main__':
    PigLatinApp().run()
