"""Guess the Number — Textual TUI.

Dark-palette terminal UI for the classic higher/lower number game.

Bindings:
    Enter   - submit guess
    Ctrl+H  - show binary-search hint
    Ctrl+N  - new game (uses current settings)
    Ctrl+Q  - quit

Run:
    uv run python guess_number/guess_number_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, Static

from guess_number import (
    DEFAULT_HIGH,
    DEFAULT_LOW,
    DEFAULT_MAX_GUESSES,
    Game,
    bits_remaining,
)


class GuessNumberApp(App):
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

    #settings {
        height: 3;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .small {
        color: #94a3b8;
        padding: 1 1 0 1;
    }

    .setting {
        width: 8;
        margin: 0 1;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    .setting:focus { border: tall #38bdf8; }

    #info {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
        color: #cbd5e1;
    }

    #info-bits {
        color: #94a3b8;
    }

    #history-wrap {
        background: #1e293b;
        border: round #334155;
        margin: 0 4;
        height: 1fr;
        padding: 0 1;
    }

    #history-title {
        color: #94a3b8;
        padding: 0 1;
    }

    #history {
        height: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    .h-low  { color: #fbbf24; }
    .h-high { color: #fbbf24; }
    .h-win  { color: #34d399; text-style: bold; }
    .h-lose { color: #f87171; text-style: bold; }

    #input {
        margin: 1 4;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus { border: tall #38bdf8; }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-hint  { color: #38bdf8; text-style: bold; }
    .status-error { color: #f87171; text-style: bold; }
    .status-win   { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('ctrl+h', 'hint', 'Hint'),
        Binding('ctrl+n', 'new_game', 'New Game'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Guess the Number'

    def __init__(self) -> None:
        super().__init__()
        self.game: Game | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('GUESS THE NUMBER', id='title')
        yield Static(
            f'Pick a number between {DEFAULT_LOW} and {DEFAULT_HIGH}',
            id='subtitle')
        with Horizontal(id='settings'):
            yield Label('Low', classes='small')
            yield Input(value=str(DEFAULT_LOW), classes='setting',
                        id='low')
            yield Label('High', classes='small')
            yield Input(value=str(DEFAULT_HIGH), classes='setting',
                        id='high')
            yield Label('Lives', classes='small')
            yield Input(value=str(DEFAULT_MAX_GUESSES),
                        classes='setting', id='lives')
        with Horizontal(id='info'):
            yield Static('Lives: -/-', id='info-lives')
            yield Static('  -  ', classes='small')
            yield Static('- candidates ~ - bits', id='info-bits')
        with Vertical(id='history-wrap'):
            yield Static('History', id='history-title')
            yield Vertical(id='history')
        yield Input(placeholder='Enter your guess and press Enter',
                    id='input')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._new_game()

    # ------------------------------------------------------------------
    # Game lifecycle
    # ------------------------------------------------------------------

    def _parse_settings(self) -> tuple[int, int, int] | None:
        try:
            low = int(self.query_one('#low', Input).value)
            high = int(self.query_one('#high', Input).value)
            lives = int(self.query_one('#lives', Input).value)
        except ValueError:
            self._set_status('Settings must be integers.', 'error')
            return None
        if low >= high:
            self._set_status('Low must be < high.', 'error')
            return None
        if lives < 1:
            self._set_status('Lives must be >= 1.', 'error')
            return None
        return low, high, lives

    def _new_game(self) -> None:
        parsed = self._parse_settings()
        if parsed is None:
            return
        low, high, lives = parsed

        self.game = Game(low=low, high=high, max_guesses=lives)
        self.query_one('#subtitle', Static).update(
            f'Pick a number between {low} and {high}')

        history = self.query_one('#history', Vertical)
        for child in list(history.children):
            child.remove()

        input_widget = self.query_one('#input', Input)
        input_widget.value = ''
        input_widget.disabled = False
        input_widget.focus()
        self._refresh_meter()
        self._set_status('Game on.', 'info')

    def action_new_game(self) -> None:
        self._new_game()

    def action_hint(self) -> None:
        if self.game is None or self.game.over:
            return
        hint = self.game.hint()
        bits = self.game.bits_left()
        self._set_status(
            f'Try {hint} (splits {bits:.2f} bits).', 'hint')

    def _refresh_meter(self) -> None:
        assert self.game is not None
        self.query_one('#info-lives', Static).update(
            f'Lives: {self.game.guesses_left}/{self.game.max_guesses}')
        bits = bits_remaining(
            self.game.candidate_low, self.game.candidate_high)
        span = self.game.candidate_high - self.game.candidate_low + 1
        self.query_one('#info-bits', Static).update(
            f'{span} candidates ~ {bits:.2f} bits')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def _add_history(self, n: int, kind: str) -> None:
        # kind: 'low' (guess too low, secret is higher), 'high', 'win', 'lose'
        glyph_text = {
            'low':  f'{n:>6}  up    higher',
            'high': f'{n:>6}  down  lower',
            'win':  f'{n:>6}  star  correct!',
            'lose': f'{n:>6}  X     out of lives',
        }[kind]
        history = self.query_one('#history', Vertical)
        history.mount(Static(glyph_text, classes=f'h-{kind}'))

    # ------------------------------------------------------------------
    # Input handler
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        # Only process Enter on the main guess input — settings ignore it.
        if event.input.id != 'input':
            return
        if self.game is None or self.game.over:
            return
        raw = event.value.strip()
        try:
            n = int(raw)
        except ValueError:
            self._set_status('Enter an integer.', 'error')
            return

        verdict = self.game.guess(n)
        result = verdict['result']
        event.input.value = ''

        if result == 'invalid':
            self._set_status(
                f'Out of [{self.game.low}, {self.game.high}].', 'error')
            return
        if result == 'too_low':
            self._add_history(n, 'low')
            self._set_status('Too low - go higher.', 'info')
        elif result == 'too_high':
            self._add_history(n, 'high')
            self._set_status('Too high - go lower.', 'info')
        elif result == 'win':
            self._add_history(n, 'win')
            self._set_status(
                f'You got it in {len(self.game.history)}!', 'win')
            event.input.disabled = True
        elif result == 'lose':
            self._add_history(n, 'lose')
            self._set_status(
                f'Out of lives - secret was {verdict["secret"]}.', 'error')
            event.input.disabled = True

        self._refresh_meter()


if __name__ == '__main__':
    GuessNumberApp().run()
