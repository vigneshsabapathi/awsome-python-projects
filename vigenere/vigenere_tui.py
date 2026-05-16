"""Vigenère Cipher — Textual TUI.

Modern dark TUI with live encrypt/decrypt and an auto-crack panel showing
IC, Kasiski candidates, and the recovered keyword.

Bindings:
    Ctrl+S  swap encrypt/decrypt
    Ctrl+A  auto-crack
    Ctrl+Q  quit

Run:
    uv run python vigenere/vigenere_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static

from vigenere import (
    ENGLISH_IC,
    RANDOM_IC,
    candidate_key_lengths,
    crack,
    decrypt,
    encrypt,
    friedman_estimate,
    friedman_ic,
    kasiski,
)


class VigenereApp(App):
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

    #body {
        height: 1fr;
    }

    #left-col {
        width: 3fr;
    }

    #right-col {
        width: 2fr;
        margin: 1 2 1 0;
        background: #1e293b;
        border: tall #334155;
        padding: 0 1;
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

    #crack-panel-label {
        color: #94a3b8;
        padding: 1 1 0 1;
        text-style: bold;
    }

    #crack-info {
        color: #cbd5e1;
        padding: 0 1;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
    }

    #key-status {
        color: #34d399;
        padding: 0 2;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding('ctrl+s', 'toggle_mode', 'Swap enc/dec'),
        Binding('ctrl+a', 'auto_crack', 'Auto-crack'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Vigenère Cipher'

    mode: reactive[str] = reactive('encrypt')

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('VIGENÈRE CIPHER', id='title')
        yield Static(
            'Polyalphabetic Caesar cipher — Ctrl+S swap mode, Ctrl+A crack',
            id='subtitle',
        )

        with Horizontal(id='mode-bar'):
            yield Static('encrypt', id='chip-encrypt',
                         classes='mode-chip mode-chip-active')
            yield Static('decrypt', id='chip-decrypt',
                         classes='mode-chip')

        yield Static('Text (input)', classes='section-label')
        yield Input(placeholder='Type plaintext or ciphertext here...',
                    id='text-input',
                    value='Hello, World! This is a Vigenere cipher demo.')

        yield Static('Key (letters only)', classes='section-label')
        yield Input(placeholder='keyword', id='key-input', value='KEY')

        yield Static('Output', classes='section-label')
        with Vertical(id='preview-frame'):
            yield Static('', id='preview')

        with Horizontal(id='body'):
            with Vertical(id='left-col'):
                yield Static('', id='status')
                yield Static('', id='key-status')

            with Vertical(id='right-col'):
                yield Static('Crack analysis', id='crack-panel-label')
                yield Static('', id='crack-info')

        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.query_one('#text-input', Input).focus()

    # ----------------------------------------------------------- actions
    def action_toggle_mode(self) -> None:
        self.mode = 'decrypt' if self.mode == 'encrypt' else 'encrypt'
        self.query_one('#chip-encrypt', Static).set_classes(
            'mode-chip mode-chip-active' if self.mode == 'encrypt' else 'mode-chip'
        )
        self.query_one('#chip-decrypt', Static).set_classes(
            'mode-chip mode-chip-active' if self.mode == 'decrypt' else 'mode-chip'
        )
        self._refresh()

    def action_auto_crack(self) -> None:
        text = self.query_one('#text-input', Input).value
        if not text.strip():
            self.query_one('#key-status', Static).update(
                '[yellow]No text to crack.[/yellow]'
            )
            return
        self.query_one('#key-status', Static).update(
            '[cyan]Cracking…[/cyan]'
        )
        try:
            key, _plain = crack(text)
        except Exception as e:
            self.query_one('#key-status', Static).update(
                f'[red]Crack failed: {e}[/red]'
            )
            return
        if key:
            self.query_one('#key-input', Input).value = key
            self.mode = 'decrypt'
            self.query_one('#chip-encrypt', Static).set_classes('mode-chip')
            self.query_one('#chip-decrypt', Static).set_classes(
                'mode-chip mode-chip-active'
            )
            self.query_one('#key-status', Static).update(
                f'[green]Recovered key: {key}[/green]'
            )
        else:
            self.query_one('#key-status', Static).update(
                '[yellow]No key found (text too short?)[/yellow]'
            )
        self._refresh()

    def on_input_changed(self, _event: Input.Changed) -> None:
        self._refresh()

    # -------------------------------------------------------------- core
    def _get_key(self) -> str:
        raw = self.query_one('#key-input', Input).value
        return ''.join(c for c in raw.upper() if c.isalpha())

    def _refresh(self) -> None:
        text = self.query_one('#text-input', Input).value
        key = self._get_key()

        result = ''
        if key:
            try:
                result = (encrypt(text, key) if self.mode == 'encrypt'
                          else decrypt(text, key))
            except ValueError:
                result = ''
        self.query_one('#preview', Static).update(result or ' ')

        letters = sum(1 for c in text if c.isalpha())
        self.query_one('#status', Static).update(
            f'mode: {self.mode}  key: {key or "(none)"}  '
            f'chars: {len(text)}  letters: {letters}'
        )

        self._refresh_crack_panel(text)

    def _refresh_crack_panel(self, text: str) -> None:
        widget = self.query_one('#crack-info', Static)
        alpha_count = sum(1 for c in text if c.isalpha())
        if alpha_count < 6:
            widget.update('(need more text)')
            return

        ic = friedman_ic(text)
        est = friedman_estimate(text)
        ks = kasiski(text)
        top_ks = ks[:5] if ks else []

        lines: list[str] = [
            f'IC = {ic:.4f}',
            f'  Eng≈{ENGLISH_IC:.4f} rnd≈{RANDOM_IC:.4f}',
            f'Friedman: {est:.2f}',
            '',
            f'Kasiski: {top_ks if top_ks else "—"}',
            '',
            'Col-IC top 6:',
        ]
        for length, ic_l, votes in candidate_key_lengths(text)[:6]:
            tag = '*' if votes else ' '
            lines.append(f' {tag} L={length:>2} IC={ic_l:.4f} k={votes}')

        widget.update('\n'.join(lines))


if __name__ == '__main__':
    VigenereApp().run()
