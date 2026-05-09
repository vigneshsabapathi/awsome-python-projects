"""Sound Mimic — Textual TUI.

A Simon-says memory game in the terminal. Four colored panels light up
in sequence; press 1-4 to repeat. Each round adds one new pad.

Run:
    uv run python sound_mimic/sound_mimic_tui.py

Bindings:
    space    Start a new round
    n        New game
    1-4      Press the matching pad
    Ctrl+Q   Quit
"""
from __future__ import annotations

import asyncio
import platform
import threading

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from sound_mimic import PITCHES, Game


def _is_windows() -> bool:
    return platform.system() == 'Windows'


def _play_tone_async(pad: int, n_pads: int, ms: int) -> None:
    """Fire-and-forget: play the tone on a daemon thread so the event
    loop never blocks. winsound.Beep is blocking, so it MUST run on a
    background thread when called from the Textual event loop."""
    pitches = PITCHES[n_pads]
    freq = pitches[pad]

    def runner() -> None:
        if _is_windows():
            try:
                import winsound
                winsound.Beep(freq, ms)
                return
            except Exception:
                pass
        import sys
        import time
        sys.stdout.write('\a')
        sys.stdout.flush()
        time.sleep(ms / 1000.0)

    threading.Thread(target=runner, daemon=True).start()


PAD_THEMES = (
    {'class': 'pad-red', 'name': 'RED', 'key': '1'},
    {'class': 'pad-green', 'name': 'GREEN', 'key': '2'},
    {'class': 'pad-blue', 'name': 'BLUE', 'key': '3'},
    {'class': 'pad-yellow', 'name': 'YELLOW', 'key': '4'},
)


class SoundMimicApp(App):
    N_PADS = 4

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

    #scoreboard {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .score {
        padding: 0 2;
        text-style: bold;
    }

    .score-round { color: #f8fafc; }
    .score-best  { color: #facc15; }

    #board {
        align-horizontal: center;
        height: auto;
        width: 100%;
        margin: 1 0;
    }

    .pad-row {
        height: 7;
        align-horizontal: center;
        width: 100%;
    }

    .pad {
        width: 22;
        height: 7;
        content-align: center middle;
        text-style: bold;
        margin: 0 1;
        border: tall #1e293b;
    }

    .pad-red    { background: #7f1d1d; color: #fca5a5; }
    .pad-green  { background: #14532d; color: #86efac; }
    .pad-blue   { background: #1e3a8a; color: #93c5fd; }
    .pad-yellow { background: #854d0e; color: #fde68a; }

    .pad-flash-red    { background: #ef4444; color: #ffffff; border: tall #fecaca; }
    .pad-flash-green  { background: #22c55e; color: #ffffff; border: tall #bbf7d0; }
    .pad-flash-blue   { background: #3b82f6; color: #ffffff; border: tall #bfdbfe; }
    .pad-flash-yellow { background: #facc15; color: #1f2937; border: tall #fef9c3; }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-win   { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('space', 'start', 'Start'),
        Binding('n', 'new_game', 'New Game'),
        Binding('1', 'press_pad(0)', 'Pad 1'),
        Binding('2', 'press_pad(1)', 'Pad 2'),
        Binding('3', 'press_pad(2)', 'Pad 3'),
        Binding('4', 'press_pad(3)', 'Pad 4'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Sound Mimic'

    def __init__(self) -> None:
        super().__init__()
        self.game = Game(n_pads=self.N_PADS)
        self.high_score: int = 0
        self.busy: bool = False
        self.input_index: int = 0
        self._round_started: bool = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('SOUND MIMIC', id='title')
        yield Static('Press space to start • 1-4 to play pads', id='subtitle')
        with Horizontal(id='scoreboard'):
            yield Static('Round 0', id='round-label', classes='score score-round')
            yield Static('Best 0', id='best-label', classes='score score-best')
        with Vertical(id='board'):
            with Horizontal(classes='pad-row'):
                for i in range(2):
                    theme = PAD_THEMES[i]
                    yield Static(
                        f"[{theme['key']}]\n{theme['name']}",
                        id=f"pad-{i}",
                        classes=f"pad {theme['class']}")
            with Horizontal(classes='pad-row'):
                for i in range(2, 4):
                    theme = PAD_THEMES[i]
                    yield Static(
                        f"[{theme['key']}]\n{theme['name']}",
                        id=f"pad-{i}",
                        classes=f"pad {theme['class']}")
        yield Static('Press space to start.', id='status', classes='status-info')
        yield Footer()

    # --- helpers ---------------------------------------------------------

    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    def _refresh_score(self) -> None:
        self.query_one('#round-label', Static).update(
            f'Round {self.game.round}')
        self.query_one('#best-label', Static).update(
            f'Best {self.high_score}')

    def _flash_pad(self, pad: int, ms: int) -> None:
        """Toggle the pad's class to its flash variant for `ms` ms."""
        theme = PAD_THEMES[pad]
        widget = self.query_one(f'#pad-{pad}', Static)
        flash_class = f"pad-flash-{theme['class'].split('-')[1]}"
        widget.set_classes(f'pad {flash_class}')

        def restore() -> None:
            widget.set_classes(f"pad {theme['class']}")

        self.set_timer(ms / 1000.0, restore)

    # --- actions ---------------------------------------------------------

    def action_start(self) -> None:
        if self.busy:
            return
        if self._round_started:
            # Already in a round — space is a no-op once started.
            return
        self._round_started = True
        self._begin_round()

    def action_new_game(self) -> None:
        self.game.reset()
        self.input_index = 0
        self.busy = False
        self._round_started = False
        self._refresh_score()
        self._set_status('Press space to start.', 'info')

    def action_press_pad(self, pad: int) -> None:
        if self.busy:
            return
        if self.game.round == 0:
            self._set_status('Press space to start.', 'info')
            return

        self._flash_pad(pad, 200)
        _play_tone_async(pad, self.N_PADS, 200)

        expected = self.game.sequence[self.input_index]
        if pad != expected:
            self._game_over()
            return

        self.input_index += 1
        if self.input_index >= len(self.game.sequence):
            if self.game.round > self.high_score:
                self.high_score = self.game.round
                self._refresh_score()
            self._set_status('Nice! Next round…', 'win')
            self.set_timer(0.7, self._begin_round)

    # --- round flow ------------------------------------------------------

    def _begin_round(self) -> None:
        self.game.next_round()
        self.input_index = 0
        self._refresh_score()
        self._set_status(f'Watch — {self.game.round} note(s)…', 'info')
        self.busy = True

        round_n = self.game.round
        tone_ms = max(140, 380 - 18 * (round_n - 1))
        gap_ms = max(80, 220 - 18 * (round_n - 1))
        sequence = list(self.game.sequence)

        # Run playback on the Textual event loop as an async task so we
        # don't block input handling. winsound.Beep itself runs on a
        # background thread (see _play_tone_async).
        async def play() -> None:
            for pad in sequence:
                self._flash_pad(pad, tone_ms)
                _play_tone_async(pad, self.N_PADS, tone_ms)
                # Wait for the tone + gap before the next note.
                await asyncio.sleep((tone_ms + gap_ms) / 1000.0)
            self.busy = False
            self._set_status(
                f'Your turn — repeat {self.game.round} note(s).', 'win')

        self.run_worker(play(), exclusive=True)

    def _game_over(self) -> None:
        self.busy = True
        self._round_started = False
        score = self.game.round - 1
        self._refresh_score()
        self._set_status(
            f'Wrong note! Final score: {score}. Press n for a new game.',
            'error')


if __name__ == '__main__':
    SoundMimicApp().run()
