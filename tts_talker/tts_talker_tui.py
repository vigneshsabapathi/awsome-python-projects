"""TTS Talker — Textual TUI.

A dark Tailwind-flavoured terminal UI for the offline pyttsx3 engine.
Same controls as the desktop GUI: voice picker, rate slider (50–400 wpm),
volume slider, Speak / Stop / Save WAV.

Bindings:
    Ctrl+Enter — speak
    Ctrl+S     — stop
    Ctrl+W     — save WAV (next to this file as out.wav)
    Ctrl+Q     — quit

Run:
    uv run python tts_talker/tts_talker_tui.py
"""
from __future__ import annotations

import os
import threading

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (Button, Footer, Header, Label, Select, Static,
                             TextArea)

# Textual versions differ on slider availability; we use plain buttons
# stepping a numeric label, which works on every release.
import pyttsx3

from tts_talker import (DEFAULT_RATE, DEFAULT_VOLUME, MAX_RATE, MIN_RATE,
                        list_voices, save_to_wav)


class TTSTalkerApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
    }

    #title {
        text-align: left;
        text-style: bold;
        color: #f8fafc;
        padding: 1 2 0 2;
    }
    #subtitle {
        text-align: left;
        color: #94a3b8;
        padding: 0 2 1 2;
    }

    #text-label, .field-label {
        color: #94a3b8;
        padding: 0 2;
    }

    #text {
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
        margin: 0 2;
        height: 1fr;
    }
    #text:focus {
        border: tall #38bdf8;
    }

    #controls {
        background: #1e293b;
        margin: 1 2 0 2;
        padding: 1 2;
        height: auto;
    }

    .row {
        height: 3;
        align: left middle;
        width: 100%;
    }
    .row Label {
        width: 18;
        color: #f8fafc;
    }
    .row Select {
        width: 1fr;
    }

    .stepper {
        width: 5;
        min-width: 5;
        background: #334155;
        color: #f8fafc;
        border: none;
        margin: 0 1;
    }
    .stepper:hover { background: #475569; }
    .value {
        width: 16;
        color: #f8fafc;
        content-align: center middle;
    }

    #actions {
        height: 3;
        align: center middle;
        margin: 1 2;
    }
    #actions Button {
        margin: 0 1;
        min-width: 14;
    }
    #speak  { background: #38bdf8; color: #0b1220; }
    #speak:hover  { background: #0ea5e9; }
    #stop   { background: #7f1d1d; color: #fef2f2; }
    #stop:hover   { background: #991b1b; }
    #save   { background: #1f2937; color: #f8fafc; }
    #save:hover   { background: #374151; }

    #status {
        text-align: center;
        padding: 0 2 1 2;
    }
    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }
    .status-ok    { color: #34d399; text-style: bold; }
    """

    BINDINGS = [
        Binding('ctrl+j', 'speak', 'Speak'),  # ctrl+enter ≡ ctrl+j on most terms
        Binding('ctrl+s', 'stop', 'Stop'),
        Binding('ctrl+w', 'save', 'Save WAV'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'TTS Talker'

    DEFAULT_TEXT = ('Hello! This is the TTS Talker terminal UI. '
                    'Press Ctrl+Enter to speak.')

    def __init__(self) -> None:
        super().__init__()
        self.voices = list_voices()
        self._voice_options = [
            (f'[{i}] {v["name"]}', v['id']) for i, v in enumerate(self.voices)
        ] or [('(no voices found)', '')]
        self._rate = DEFAULT_RATE
        self._volume = DEFAULT_VOLUME
        self._engine: pyttsx3.Engine | None = None
        self._speech_thread: threading.Thread | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield Static('TTS TALKER', id='title')
        yield Static('Offline text-to-speech via pyttsx3 — Ctrl+Enter speaks',
                     id='subtitle')
        yield Label('Text', id='text-label')
        yield TextArea(self.DEFAULT_TEXT, id='text')

        with Vertical(id='controls'):
            with Horizontal(classes='row'):
                yield Label('Voice')
                yield Select(self._voice_options,
                             value=self._voice_options[0][1],
                             allow_blank=False, id='voice')
            with Horizontal(classes='row'):
                yield Label('Rate (wpm)')
                yield Button('-', id='rate-down', classes='stepper')
                yield Static(str(self._rate), id='rate-value',
                             classes='value')
                yield Button('+', id='rate-up', classes='stepper')
                yield Label(f'  {MIN_RATE}–{MAX_RATE}',
                            classes='field-label')
            with Horizontal(classes='row'):
                yield Label('Volume (%)')
                yield Button('-', id='vol-down', classes='stepper')
                yield Static(f'{int(self._volume * 100)}', id='vol-value',
                             classes='value')
                yield Button('+', id='vol-up', classes='stepper')
                yield Label('  0–100', classes='field-label')

        with Horizontal(id='actions'):
            yield Button('Speak  (Ctrl+Enter)', id='speak', variant='primary')
            yield Button('Stop  (Ctrl+S)', id='stop')
            yield Button('Save WAV  (Ctrl+W)', id='save')

        yield Static('Ready.', id='status', classes='status-info')
        yield Footer()

    # ---------------------------------------------------------- helpers
    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    def _selected_voice_id(self) -> str | None:
        select = self.query_one('#voice', Select)
        value = select.value
        return value or None

    def _current_text(self) -> str:
        return self.query_one('#text', TextArea).text.strip()

    # ------------------------------------------------------ stepper btns
    @on(Button.Pressed, '#rate-up')
    def _rate_up(self) -> None:
        self._rate = min(MAX_RATE, self._rate + 10)
        self.query_one('#rate-value', Static).update(str(self._rate))

    @on(Button.Pressed, '#rate-down')
    def _rate_down(self) -> None:
        self._rate = max(MIN_RATE, self._rate - 10)
        self.query_one('#rate-value', Static).update(str(self._rate))

    @on(Button.Pressed, '#vol-up')
    def _vol_up(self) -> None:
        self._volume = min(1.0, round(self._volume + 0.05, 2))
        self.query_one('#vol-value', Static).update(
            str(int(round(self._volume * 100))))

    @on(Button.Pressed, '#vol-down')
    def _vol_down(self) -> None:
        self._volume = max(0.0, round(self._volume - 0.05, 2))
        self.query_one('#vol-value', Static).update(
            str(int(round(self._volume * 100))))

    @on(Button.Pressed, '#speak')
    def _btn_speak(self) -> None:
        self.action_speak()

    @on(Button.Pressed, '#stop')
    def _btn_stop(self) -> None:
        self.action_stop()

    @on(Button.Pressed, '#save')
    def _btn_save(self) -> None:
        self.action_save()

    # ------------------------------------------------------------ actions
    def action_speak(self) -> None:
        if self._speech_thread and self._speech_thread.is_alive():
            self._set_status('Already speaking — press Stop first.', 'error')
            return
        text = self._current_text()
        if not text:
            self._set_status('Nothing to speak.', 'error')
            return

        voice_id = self._selected_voice_id()
        rate = self._rate
        volume = self._volume
        self._set_status('Speaking…', 'info')

        def worker() -> None:
            try:
                engine = pyttsx3.init()
                self._engine = engine
                if voice_id:
                    engine.setProperty('voice', voice_id)
                engine.setProperty('rate', rate)
                engine.setProperty('volume', volume)
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:  # noqa: BLE001
                self.call_from_thread(self._set_status,
                                      f'Error: {exc}', 'error')
                return
            finally:
                try:
                    if self._engine is not None:
                        self._engine.stop()
                except Exception:
                    pass
                self._engine = None
            self.call_from_thread(self._set_status, 'Done.', 'ok')

        self._speech_thread = threading.Thread(target=worker, daemon=True)
        self._speech_thread.start()

    def action_stop(self) -> None:
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._set_status('Stopped.', 'info')

    def action_save(self) -> None:
        text = self._current_text()
        if not text:
            self._set_status('Nothing to save.', 'error')
            return
        path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                            'out.wav'))
        try:
            self._set_status('Rendering…', 'info')
            save_to_wav(text, path,
                        voice=self._selected_voice_id(),
                        rate=self._rate, volume=self._volume)
            self._set_status(f'Saved → {path}', 'ok')
        except Exception as exc:  # noqa: BLE001
            self._set_status(f'Save failed: {exc}', 'error')


if __name__ == '__main__':
    TTSTalkerApp().run()
