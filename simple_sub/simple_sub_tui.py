"""Simple Substitution Cipher — Textual TUI.

Modern dark TUI: key entry, input + output panes, ASCII frequency
chart. Supports encrypt/decrypt and an auto-crack action that runs
the simulated-annealing attack on a worker thread.

Bindings:
    Ctrl+S   swap encrypt/decrypt
    Ctrl+A   auto-crack the input as ciphertext
    Ctrl+R   randomise the key
    Ctrl+Q   quit

Run:
    uv run python simple_sub/simple_sub_tui.py
"""
from __future__ import annotations

import string

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static, TextArea

from simple_sub import (
    ALPHABET,
    ALPHABET_SIZE,
    ENGLISH_FREQ,
    crack_with_key,
    decrypt,
    encrypt,
    letter_frequencies,
    random_key,
)


def _ascii_freq_chart(text: str, height: int = 8) -> str:
    """Render a tiny ASCII bar chart of input vs English letter freq.

    Each column is one letter A-Z. The bar uses `█` for input, with a
    `·` marker showing where the English baseline would land.
    """
    freqs = letter_frequencies(text)
    labels = list(string.ascii_uppercase)
    obs = [freqs[ch] for ch in labels]
    base = [ENGLISH_FREQ[ch] for ch in labels]
    top = max(15.0, max(obs + [0.0]) + 2.0, max(base) + 1.0)

    rows: list[str] = []
    for h in range(height, 0, -1):
        threshold = h / height * top
        line = []
        for o, b in zip(obs, base):
            cell = ' '
            if o >= threshold:
                cell = '█'
            elif b >= threshold and b < threshold + (top / height):
                cell = '·'
            line.append(cell)
        rows.append(''.join(line))
    rows.append(''.join(labels))
    return '\n'.join(rows)


class SimpleSubApp(App):
    """Textual TUI for the simple substitution cipher."""

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

    .panel {
        margin: 0 2;
        background: #1e293b;
        border: tall #334155;
        padding: 0 1;
    }

    #panes {
        height: 1fr;
        margin: 1 2;
    }

    #left-col {
        width: 3fr;
    }
    #right-col {
        width: 2fr;
    }

    #input-area, #output-area {
        height: 1fr;
        background: #1e293b;
        border: tall #334155;
        margin: 0 0 1 0;
    }
    #input-area:focus, #input-area:focus-within {
        border: tall #38bdf8;
    }
    TextArea {
        background: #1e293b;
        color: #f8fafc;
    }

    #chart {
        color: #38bdf8;
        padding: 1 1 0 1;
        height: 10;
    }

    #key-status {
        color: #34d399;
        padding: 0 2;
    }
    .status-warn { color: #f87171; text-style: bold; }
    .status-good { color: #34d399; text-style: bold; }
    .status-info { color: #94a3b8; }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding('ctrl+s', 'toggle_mode', 'Swap enc/dec'),
        Binding('ctrl+a', 'auto_crack', 'Auto-crack'),
        Binding('ctrl+r', 'random_key', 'Random key'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Simple Substitution Cipher'

    mode: reactive[str] = reactive('encrypt')

    def __init__(self) -> None:
        super().__init__()
        self._cracking = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('SIMPLE SUBSTITUTION CIPHER', id='title')
        yield Static(
            'Each letter mapped via a 26-character permutation key — '
            'Ctrl+S swap, Ctrl+A auto-crack, Ctrl+R random key, Ctrl+Q quit',
            id='subtitle',
        )

        with Horizontal(id='mode-bar'):
            yield Static('encrypt', id='chip-encrypt',
                         classes='mode-chip mode-chip-active')
            yield Static('decrypt', id='chip-decrypt', classes='mode-chip')

        yield Static('Reference: ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                     classes='section-label')
        yield Static('Key (26 letters)', classes='section-label')
        yield Input(value=ALPHABET, id='key-input',
                    placeholder='ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        yield Static('valid permutation', id='key-status',
                     classes='status-good')

        with Horizontal(id='panes'):
            with Vertical(id='left-col'):
                yield Static('Input', classes='section-label')
                yield TextArea.code_editor(
                    'Hello, World! This is a substitution cipher demo.',
                    id='input-area', show_line_numbers=False,
                )
                yield Static('Output', classes='section-label')
                yield TextArea.code_editor(
                    '', id='output-area', show_line_numbers=False,
                    read_only=True,
                )
            with Vertical(id='right-col'):
                yield Static('Letter-frequency chart  '
                             '(█ input, · English baseline)',
                             classes='section-label')
                yield Static('', id='chart', classes='panel')
                yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#input-area', TextArea).language = None
        self.query_one('#output-area', TextArea).language = None
        self._refresh()
        self.query_one('#input-area', TextArea).focus()

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

    def action_random_key(self) -> None:
        self.query_one('#key-input', Input).value = random_key()
        # Triggers on_input_changed -> _refresh.

    def action_auto_crack(self) -> None:
        if self._cracking:
            return
        text = self.query_one('#input-area', TextArea).text
        if not text.strip():
            self._set_status('Nothing to crack — type ciphertext into the input.',
                             'warn')
            return
        self._cracking = True
        self._set_status('Annealing — please wait (a few seconds)...', 'info')
        # Run on a worker so the UI stays responsive.
        self.run_worker(self._crack_worker(text), exclusive=True, thread=True)

    async def _crack_worker(self, text: str) -> None:  # type: ignore[override]
        # Note: `crack_with_key` is sync + CPU-bound, so we rely on the
        # `thread=True` flag to hop off the event loop.
        try:
            plain, key, score = crack_with_key(text)
        except Exception as e:  # pragma: no cover
            self.call_from_thread(self._crack_failed, str(e))
            return
        self.call_from_thread(self._crack_done, plain, key, score)

    def _crack_done(self, plain: str, key: str, score: float) -> None:
        # Switch to decrypt mode and put the discovered key into the
        # key field. _refresh will fill the output pane.
        self.mode = 'decrypt'
        self.query_one('#chip-encrypt', Static).set_classes('mode-chip')
        self.query_one('#chip-decrypt', Static).set_classes(
            'mode-chip mode-chip-active')
        self.query_one('#key-input', Input).value = key
        self._set_status(
            f'Cracked: score={score:+.1f}  preview: {plain[:60]}',
            'good',
        )
        self._cracking = False

    def _crack_failed(self, msg: str) -> None:
        self._set_status(f'Crack failed: {msg}', 'warn')
        self._cracking = False

    # --------------------------------------------------------------- ui glue
    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'key-input':
            # Force-uppercase echo so the user can type either case.
            up = event.value.upper()
            if up != event.value:
                event.input.value = up
                return
        self._refresh()

    def on_text_area_changed(self, _event: TextArea.Changed) -> None:
        self._refresh()

    # ------------------------------------------------------------------ core
    def _validate_key(self, key: str) -> tuple[bool, str]:
        if len(key) != ALPHABET_SIZE:
            return False, f'{len(key)}/26 chars'
        if any(c not in ALPHABET for c in key):
            return False, 'non-letter chars'
        if sorted(key) != list(ALPHABET):
            return False, 'not a permutation'
        return True, 'valid permutation'

    def _refresh(self) -> None:
        text = self.query_one('#input-area', TextArea).text
        key = self.query_one('#key-input', Input).value.upper()
        ok, msg = self._validate_key(key)
        status = self.query_one('#key-status', Static)
        status.update(msg)
        status.set_classes(f'status-{"good" if ok else "warn"}')

        out = self.query_one('#output-area', TextArea)
        if ok:
            try:
                result = (encrypt(text, key) if self.mode == 'encrypt'
                          else decrypt(text, key))
            except ValueError:
                result = ''
            out.text = result
        # Chart is always informative even on invalid keys.
        self.query_one('#chart', Static).update(_ascii_freq_chart(text))

        letters = sum(1 for c in text if c.isalpha())
        self.query_one('#status', Static).update(
            f'mode: {self.mode}  •  {len(text)} chars  •  {letters} letters'
        )

    def _set_status(self, msg: str, kind: str = 'info') -> None:
        # Repurpose the bottom status line for transient messages.
        s = self.query_one('#status', Static)
        s.update(msg)


if __name__ == '__main__':
    SimpleSubApp().run()
