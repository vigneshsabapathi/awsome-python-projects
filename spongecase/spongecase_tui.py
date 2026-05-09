"""sPoNgEcAsE — Textual TUI.

Modern dark TUI with live preview. Two text inputs (text + seed),
intensity input, mode toggle.

Bindings:
    Ctrl+M  cycle mode (random -> strict -> random)
    Ctrl+R  re-roll randomness (random mode)
    Ctrl+Q  quit

Run:
    uv run python spongecase/spongecase_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Static

from spongecase import to_sponge, to_sponge_strict

MODES = ('random', 'strict')


class SpongeApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #facc15;
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
        border: tall #facc15;
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
        background: #facc15;
        color: #0f172a;
        text-style: bold;
    }

    #preview-frame {
        margin: 1 2;
        height: 1fr;
        background: #1e293b;
        border: tall #334155;
        padding: 0 1;
    }

    #preview {
        color: #facc15;
        text-style: bold;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
    }
    """

    BINDINGS = [
        Binding('ctrl+m', 'cycle_mode', 'Cycle mode'),
        Binding('ctrl+r', 'reroll', 'Re-roll'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'sPoNgEcAsE'

    mode: reactive[str] = reactive('random')

    def __init__(self) -> None:
        super().__init__()
        self._seed = 1337

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('sPoNgEcAsE', id='title')
        yield Static('ThE mOcKiNg-SpOnGeBoB cAsE mEmE  '
                     '— Ctrl+M cycle mode, Ctrl+R re-roll, Ctrl+Q quit',
                     id='subtitle')

        with Horizontal(id='mode-bar'):
            yield Static('random', id='chip-random',
                         classes='mode-chip mode-chip-active')
            yield Static('strict', id='chip-strict',
                         classes='mode-chip')

        yield Static('Text', classes='section-label')
        yield Input(placeholder='Type text here...',
                    id='text-input', value='Hello, World!')

        yield Static('Intensity  (0..100, percent — random mode only)',
                     classes='section-label')
        yield Input(placeholder='intensity 0..100',
                    id='intensity-input', value='50')

        yield Static('Seed  (integer — same seed + intensity = same output)',
                     classes='section-label')
        yield Input(placeholder='seed integer',
                    id='seed-input', value='1337')

        yield Static('Output', classes='section-label')
        with Vertical(id='preview-frame'):
            yield Static('', id='preview')

        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.query_one('#text-input', Input).focus()

    # ----------------------------------------------------------- actions
    def action_cycle_mode(self) -> None:
        idx = MODES.index(self.mode)
        self.mode = MODES[(idx + 1) % len(MODES)]
        self.query_one('#chip-random', Static).set_classes(
            'mode-chip mode-chip-active'
            if self.mode == 'random' else 'mode-chip'
        )
        self.query_one('#chip-strict', Static).set_classes(
            'mode-chip mode-chip-active'
            if self.mode == 'strict' else 'mode-chip'
        )
        self._refresh()

    def action_reroll(self) -> None:
        self._seed = random.randint(0, 2**31 - 1)
        seed_input = self.query_one('#seed-input', Input)
        seed_input.value = str(self._seed)
        self._refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        # Sync the seed state if the user types into the seed box.
        if event.input.id == 'seed-input':
            raw = event.value.strip()
            try:
                self._seed = int(raw) if raw else 0
            except ValueError:
                self._seed = abs(hash(raw)) % (2**31 - 1)
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
        if self.mode == 'random':
            p = self._current_intensity() / 100.0
            result = to_sponge(text, intensity=p,
                               rng=random.Random(self._seed))
        else:
            result = to_sponge_strict(text)
        self.query_one('#preview', Static).update(result or ' ')

        letters = sum(1 for c in text if c.isalpha())
        intensity = self._current_intensity()
        self.query_one('#status', Static).update(
            f'mode: {self.mode}  intensity: {intensity}%  '
            f'seed: {self._seed}  chars: {len(text)}  letters: {letters}'
        )


if __name__ == '__main__':
    SpongeApp().run()
