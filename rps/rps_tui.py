"""Rock Paper Scissors — Textual TUI.

Bindings:
  r / p / s   play that move
  m           cycle mode (fair → markov → cheat → fair ...)
  n           reset score
  ctrl+q      quit

Run:
    uv run python rps/rps_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from rps import EMOJI, Game

MODE_CYCLE = ('fair', 'markov', 'cheat')


class RPSApp(App):
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

    #mode-row {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .mode-chip {
        padding: 0 2;
        background: #1e293b;
        color: #cbd5e1;
        text-style: bold;
    }

    #reveal {
        height: auto;
        align-horizontal: center;
        background: #1e293b;
        margin: 1 4;
        padding: 1 2;
    }

    .pane {
        width: 16;
        content-align: center middle;
        text-align: center;
    }

    .pane-label {
        color: #94a3b8;
        text-align: center;
    }

    .pane-glyph {
        color: #f8fafc;
        text-align: center;
        text-style: bold;
        height: 3;
    }

    #vs {
        color: #94a3b8;
        content-align: center middle;
        width: 4;
    }

    #status {
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-win   { color: #34d399; }
    .status-lose  { color: #f87171; }
    .status-tie   { color: #fbbf24; }

    #score {
        height: auto;
        align-horizontal: center;
        background: #1e293b;
        margin: 0 4;
        padding: 1 2;
    }

    .score-cell {
        width: 12;
        content-align: center middle;
        text-align: center;
    }

    .score-cell-label { color: #94a3b8; text-align: center; }

    .wins-value   { color: #34d399; text-style: bold; text-align: center; }
    .losses-value { color: #f87171; text-style: bold; text-align: center; }
    .ties-value   { color: #fbbf24; text-style: bold; text-align: center; }

    #help {
        text-align: center;
        color: #64748b;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding('r', 'play_rock', 'Rock'),
        Binding('p', 'play_paper', 'Paper'),
        Binding('s', 'play_scissors', 'Scissors'),
        Binding('m', 'cycle_mode', 'Mode'),
        Binding('n', 'reset', 'Reset'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Rock Paper Scissors'

    def __init__(self) -> None:
        super().__init__()
        self.game = Game(mode='fair')

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('ROCK · PAPER · SCISSORS', id='title')
        yield Static('Sweigart #59 + #60 — fair, markov-predictor, or cheat',
                     id='subtitle')
        with Horizontal(id='mode-row'):
            yield Static('mode: fair', id='mode-chip', classes='mode-chip')

        with Horizontal(id='reveal'):
            with Vertical(classes='pane'):
                yield Static('YOU', classes='pane-label')
                yield Static('·', id='you-glyph', classes='pane-glyph')
            yield Static('vs', id='vs')
            with Vertical(classes='pane'):
                yield Static('CPU', classes='pane-label')
                yield Static('·', id='cpu-glyph', classes='pane-glyph')

        yield Static('Press r / p / s to play', id='status',
                     classes='status-info')

        with Horizontal(id='score'):
            with Vertical(classes='score-cell'):
                yield Static('WINS', classes='score-cell-label')
                yield Static('0', id='wins-value', classes='wins-value')
            with Vertical(classes='score-cell'):
                yield Static('LOSSES', classes='score-cell-label')
                yield Static('0', id='losses-value', classes='losses-value')
            with Vertical(classes='score-cell'):
                yield Static('TIES', classes='score-cell-label')
                yield Static('0', id='ties-value', classes='ties-value')

        yield Static(
            'r/p/s = play   m = cycle mode   n = reset   Ctrl+Q = quit',
            id='help')
        yield Footer()

    # -------- actions --------
    def action_play_rock(self) -> None:
        self._play('rock')

    def action_play_paper(self) -> None:
        self._play('paper')

    def action_play_scissors(self) -> None:
        self._play('scissors')

    def action_cycle_mode(self) -> None:
        idx = MODE_CYCLE.index(self.game.mode)
        new_mode = MODE_CYCLE[(idx + 1) % len(MODE_CYCLE)]
        self.game = Game(mode=new_mode)
        self.query_one('#mode-chip', Static).update(f'mode: {new_mode}')
        self.query_one('#you-glyph', Static).update('·')
        self.query_one('#cpu-glyph', Static).update('·')
        self._set_status(f'Mode: {new_mode}', 'info')
        self._refresh_score()

    def action_reset(self) -> None:
        self.game.reset()
        self.query_one('#you-glyph', Static).update('·')
        self.query_one('#cpu-glyph', Static).update('·')
        self._set_status('Score reset', 'info')
        self._refresh_score()

    # -------- helpers --------
    def _play(self, move: str) -> None:
        self.query_one('#you-glyph', Static).update(EMOJI[move])
        result = self.game.play(move)
        cm = result['computer_move']
        self.query_one('#cpu-glyph', Static).update(EMOJI[cm])

        if result['result'] == 'win':
            self._set_status('YOU WIN', 'win')
        elif result['result'] == 'lose':
            self._set_status('CPU WINS', 'lose')
        else:
            self._set_status('TIE', 'tie')
        self._refresh_score()

    def _set_status(self, text: str, kind: str) -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def _refresh_score(self) -> None:
        s = self.game.score
        self.query_one('#wins-value', Static).update(str(s['wins']))
        self.query_one('#losses-value', Static).update(str(s['losses']))
        self.query_one('#ties-value', Static).update(str(s['ties']))


if __name__ == '__main__':
    RPSApp().run()
