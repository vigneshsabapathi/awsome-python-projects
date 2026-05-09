"""Leetspeak — Textual TUI.

Modern dark TUI with live preview and a brute-decode panel.

Bindings:
    Ctrl+S  swap encode / decode
    Ctrl+R  re-roll randomness (encode mode)
    Ctrl+B  toggle brute-decode panel
    Ctrl+Q  quit

Run:
    uv run python leetspeak/leetspeak_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static

from leetspeak import brute_decode, from_leet, to_leet


class LeetApp(App):
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
        border: tall #22d3ee;
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
        background: #22d3ee;
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
        color: #22d3ee;
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
        Binding('ctrl+s', 'toggle_mode', 'Swap mode'),
        Binding('ctrl+r', 'reroll', 'Re-roll'),
        Binding('ctrl+b', 'toggle_brute', 'Brute panel'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Leetspeak'

    mode: reactive[str] = reactive('encode')
    show_brute: reactive[bool] = reactive(True)

    def __init__(self) -> None:
        super().__init__()
        self._seed = 1337

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('LEETSPEAK', id='title')
        yield Static('Probabilistic l337 substitution  '
                     '— Ctrl+S swap mode, Ctrl+R re-roll, Ctrl+B brute panel',
                     id='subtitle')

        with Horizontal(id='mode-bar'):
            yield Static('encode', id='chip-encode',
                         classes='mode-chip mode-chip-active')
            yield Static('decode', id='chip-decode',
                         classes='mode-chip')

        yield Static('Text', classes='section-label')
        yield Input(placeholder='Type text or leet here...',
                    id='text-input', value='Hello, World!')

        yield Static('Intensity  (0..100, percent — encode only)',
                     classes='section-label')
        yield Input(placeholder='intensity 0..100',
                    id='intensity-input', value='50')

        yield Static('Output', classes='section-label')
        with Vertical(id='preview-frame'):
            yield Static('', id='preview')

        yield Static('Brute-decode — common leet patterns ranked by '
                     'English-likelihood (lower chi^2 = more English)',
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
        self.mode = 'decode' if self.mode == 'encode' else 'encode'
        self.query_one('#chip-encode', Static).set_classes(
            'mode-chip mode-chip-active'
            if self.mode == 'encode' else 'mode-chip'
        )
        self.query_one('#chip-decode', Static).set_classes(
            'mode-chip mode-chip-active'
            if self.mode == 'decode' else 'mode-chip'
        )
        self._refresh()

    def action_toggle_brute(self) -> None:
        self.show_brute = not self.show_brute
        self.query_one('#brute-frame').display = self.show_brute
        self._refresh()

    def action_reroll(self) -> None:
        self._seed = random.randint(0, 2**31 - 1)
        self._refresh()

    def on_input_changed(self, _event: Input.Changed) -> None:
        self._refresh()

    # -------------------------------------------------------------- core
    def _current_intensity(self) -> int:
        raw = self.query_one('#intensity-input', Input).value.strip()
        if raw == '':
            return 0
        try:
            n = int(raw)
        except ValueError:
            return 0
        return max(0, min(100, n))

    def _refresh(self) -> None:
        text = self.query_one('#text-input', Input).value
        if self.mode == 'encode':
            p = self._current_intensity() / 100.0
            result = to_leet(text, intensity=p,
                             rng=random.Random(self._seed))
        else:
            result = from_leet(text)
        self.query_one('#preview', Static).update(result or ' ')

        if self.show_brute and text.strip():
            lines = []
            for i, (label, plain, score) in enumerate(brute_decode(text)):
                marker = '*' if i == 0 else ' '
                preview = plain if len(plain) <= 60 else plain[:57] + '...'
                lines.append(
                    f'{marker} chi^2={score:7.2f}  [{label}]  {preview}'
                )
            self.query_one('#brute', Static).update('\n'.join(lines))
        else:
            self.query_one('#brute', Static).update('')

        letters = sum(1 for c in text if c.isalpha())
        intensity = self._current_intensity()
        self.query_one('#status', Static).update(
            f'mode: {self.mode}  intensity: {intensity}%  '
            f'chars: {len(text)}  letters: {letters}'
        )


if __name__ == '__main__':
    LeetApp().run()
