"""Bagels — Textual TUI.

A modern terminal UI for the Bagels deductive logic game.
Tiles light up green (Fermi), yellow (Pico), or gray (Bagels) for each guess.

Run:
    uv run python bagels/bagels_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from bagels import MAX_GUESSES, NUM_DIGITS, getCluesPerPosition, getSecretNum


class BagelsApp(App):
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

    #legend {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .chip {
        padding: 0 1;
        margin: 0 1;
        height: 1;
    }

    .chip-fermi  { background: #16a34a; color: white; }
    .chip-pico   { background: #eab308; color: black; }
    .chip-bagels { background: #374151; color: #9ca3af; }

    #board {
        align-horizontal: center;
        height: auto;
        width: 100%;
    }

    .row {
        height: 3;
        align-horizontal: center;
        width: 100%;
    }

    .tile {
        width: 5;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: #1f2937;
        color: #6b7280;
        margin: 0 1;
    }

    .tile-fermi  { background: #16a34a; color: white; }
    .tile-pico   { background: #eab308; color: black; }
    .tile-bagels { background: #374151; color: #9ca3af; }

    #input {
        margin: 1 6;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus {
        border: tall #38bdf8;
    }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-win   { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('ctrl+n', 'new_game', 'New Game'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Bagels'

    def __init__(self) -> None:
        super().__init__()
        self.secret: str = ''
        self.current_row: int = 0
        self.game_over: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('BAGELS', id='title')
        yield Static(f'Guess the {NUM_DIGITS}-digit number — no repeats',
                     id='subtitle')
        with Horizontal(id='legend'):
            yield Static('Fermi: right + place', classes='chip chip-fermi')
            yield Static('Pico: right, wrong place', classes='chip chip-pico')
            yield Static('Bagels: no match', classes='chip chip-bagels')
        with Vertical(id='board'):
            for r in range(MAX_GUESSES):
                with Horizontal(classes='row'):
                    for c in range(NUM_DIGITS):
                        yield Static(' ', classes='tile',
                                     id=f'tile-{r}-{c}')
        yield Input(placeholder=f'{NUM_DIGITS} digits, press Enter',
                    id='input', max_length=NUM_DIGITS)
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._new_game()

    def _new_game(self) -> None:
        self.secret = getSecretNum()
        self.current_row = 0
        self.game_over = False
        for r in range(MAX_GUESSES):
            for c in range(NUM_DIGITS):
                tile = self.query_one(f'#tile-{r}-{c}', Static)
                tile.update(' ')
                tile.set_classes('tile')
        self._set_status(f'Guess 1 of {MAX_GUESSES}', 'info')
        input_widget = self.query_one('#input', Input)
        input_widget.value = ''
        input_widget.disabled = False
        input_widget.focus()

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def action_new_game(self) -> None:
        self._new_game()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if self.game_over:
            return
        guess = event.value.strip()
        if len(guess) != NUM_DIGITS or not guess.isdecimal():
            self._set_status(f'Enter exactly {NUM_DIGITS} digits.', 'error')
            return
        if len(set(guess)) != NUM_DIGITS:
            self._set_status('Digits must not repeat.', 'error')
            return

        clues = getCluesPerPosition(guess, self.secret)
        for col, (digit, clue) in enumerate(zip(guess, clues)):
            tile = self.query_one(f'#tile-{self.current_row}-{col}', Static)
            tile.update(digit)
            tile.set_classes(f'tile tile-{clue.lower()}')

        self.current_row += 1
        event.input.value = ''

        if guess == self.secret:
            self._end_game(f'You got it in {self.current_row}!', 'win')
        elif self.current_row >= MAX_GUESSES:
            self._end_game(
                f'Out of guesses — answer was {self.secret}', 'error')
        else:
            self._set_status(
                f'Guess {self.current_row + 1} of {MAX_GUESSES}', 'info')

    def _end_game(self, message: str, kind: str) -> None:
        self.game_over = True
        self._set_status(message, kind)
        self.query_one('#input', Input).disabled = True


if __name__ == '__main__':
    BagelsApp().run()
