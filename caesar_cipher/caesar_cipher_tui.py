"""Caesar Cipher — Textual TUI.

Modern dark TUI with live preview and a brute-force panel.

Bindings:
    Ctrl+S  swap encrypt/decrypt
    Ctrl+B  toggle brute-force panel
    Ctrl+Q  quit

Run:
    uv run python caesar_cipher/caesar_cipher_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static

from caesar_cipher import brute_force, decrypt, encrypt


class CaesarApp(App):
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

    Input {
        margin: 0 2;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    Input:focus {
        border: tall #38bdf8;
    }

    #mode-bar {
        height: 1;
        margin: 1 2 0 2;
    }

    .mode-chip {
        padding: 0 2;
        margin-right: 1;
        background: #1e293b;
        color: #94a3b8;
    }
    .mode-chip-active {
        background: #38bdf8;
        color: #0f172a;
        text-style: bold;
    }

    #preview-frame {
        margin: 1 2;
        height: 5;
        background: #1e293b;
        border: tall #334155;
        padding: 0 1;
    }

    #preview {
        color: #38bdf8;
        text-style: bold;
    }

    #brute-frame {
        margin: 0 2 1 2;
        background: #1e293b;
        border: tall #334155;
        padding: 0 1;
        height: 1fr;
    }

    #brute {
        color: #cbd5e1;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding('ctrl+s', 'toggle_mode', 'Swap enc/dec'),
        Binding('ctrl+b', 'toggle_brute', 'Brute panel'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Caesar Cipher'

    mode: reactive[str] = reactive('encrypt')
    show_brute: reactive[bool] = reactive(True)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('CAESAR CIPHER', id='title')
        yield Static('Shift each letter N positions in the alphabet  '
                     '— Ctrl+S swap mode, Ctrl+B toggle brute-force',
                     id='subtitle')

        with Horizontal(id='mode-bar'):
            yield Static('encrypt', id='chip-encrypt',
                         classes='mode-chip mode-chip-active')
            yield Static('decrypt', id='chip-decrypt',
                         classes='mode-chip')

        yield Static('Text', classes='section-label')
        yield Input(placeholder='Type plaintext or ciphertext here...',
                    id='text-input', value='Hello, World!')

        yield Static('Shift  (-25..25)', classes='section-label')
        yield Input(placeholder='shift', id='shift-input', value='3')

        yield Static('Output', classes='section-label')
        with Vertical(id='preview-frame'):
            yield Static('', id='preview')

        yield Static('Brute-force — all 26 shifts ranked by '
                     'English-likelihood (lower chi² = more English)',
                     classes='section-label')
        with Vertical(id='brute-frame'):
            yield Static('', id='brute')

        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.query_one('#text-input', Input).focus()

    # ----------------------------------------------------------- actions
    def action_toggle_mode(self) -> None:
        self.mode = 'decrypt' if self.mode == 'encrypt' else 'encrypt'
        self.query_one('#chip-encrypt', Static).set_classes(
            'mode-chip mode-chip-active'
            if self.mode == 'encrypt' else 'mode-chip'
        )
        self.query_one('#chip-decrypt', Static).set_classes(
            'mode-chip mode-chip-active'
            if self.mode == 'decrypt' else 'mode-chip'
        )
        self._refresh()

    def action_toggle_brute(self) -> None:
        self.show_brute = not self.show_brute
        self.query_one('#brute-frame').display = self.show_brute
        self._refresh()

    def on_input_changed(self, _event: Input.Changed) -> None:
        self._refresh()

    # -------------------------------------------------------------- core
    def _current_shift(self) -> int:
        raw = self.query_one('#shift-input', Input).value.strip()
        if raw in ('', '-', '+'):
            return 0
        try:
            n = int(raw)
        except ValueError:
            return 0
        # Clamp display-side; caesar_shift mods anyway.
        return max(-25, min(25, n))

    def _refresh(self) -> None:
        text = self.query_one('#text-input', Input).value
        shift = self._current_shift()
        result = encrypt(text, shift) if self.mode == 'encrypt' \
            else decrypt(text, shift)
        self.query_one('#preview', Static).update(result or ' ')

        if self.show_brute and text.strip():
            lines = []
            for i, (s, plain, score) in enumerate(brute_force(text)):
                marker = '*' if i == 0 else ' '
                preview = plain if len(plain) <= 60 else plain[:57] + '...'
                lines.append(
                    f'{marker} shift={s:>2}  chi2={score:7.2f}  {preview}'
                )
            self.query_one('#brute', Static).update('\n'.join(lines))
        else:
            self.query_one('#brute', Static).update('')

        letters = sum(1 for c in text if c.isalpha())
        self.query_one('#status', Static).update(
            f'mode: {self.mode}  shift: {shift:+d}  '
            f'chars: {len(text)}  letters: {letters}'
        )


if __name__ == '__main__':
    CaesarApp().run()
