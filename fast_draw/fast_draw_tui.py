"""Fast Draw — Textual TUI quick-reaction game.

Press SPACE when you see DRAW! Pressing SPACE during WAIT counts as a false
start. Press N to start a new round, Ctrl+Q to quit.

Run:
    uv run python fast_draw/fast_draw_tui.py
"""
from __future__ import annotations

import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static
from textual.worker import Worker, WorkerState

from fast_draw import Game

# ---------------------------------------------------------------------------
# CSS (Tailwind dark palette)
# ---------------------------------------------------------------------------
CSS = """
Screen {
    background: #0f172a;
    color: #f8fafc;
    align: center top;
}

#title {
    text-align: center;
    text-style: bold;
    color: #38bdf8;
    padding: 1 0 0 0;
}

#subtitle {
    text-align: center;
    color: #94a3b8;
    padding-bottom: 1;
}

#signal-box {
    align: center middle;
    height: 7;
    width: 100%;
}

#signal {
    text-align: center;
    text-style: bold;
    width: 26;
    height: 5;
    content-align: center middle;
    background: #1e293b;
    color: #64748b;
    border: tall #334155;
}

#signal.state-wait {
    color: #eab308;
    border: tall #eab308;
}

#signal.state-draw {
    color: #22c55e;
    border: tall #22c55e;
    text-style: bold;
}

#signal.state-false {
    color: #ef4444;
    border: tall #ef4444;
}

#signal.state-result {
    color: #38bdf8;
    border: tall #38bdf8;
}

#msg {
    text-align: center;
    color: #94a3b8;
    padding: 1 0;
}

#stats-panel {
    width: 100%;
    height: auto;
    align-horizontal: center;
    padding: 0 4;
}

.stat-box {
    width: 16;
    height: 5;
    content-align: center middle;
    background: #1e293b;
    border: tall #334155;
    margin: 0 1;
    text-align: center;
}

.stat-title {
    color: #94a3b8;
}

.stat-value {
    text-style: bold;
    color: #f8fafc;
}

#hint {
    text-align: center;
    color: #475569;
    padding: 1 0;
}
"""


class StatBox(Static):
    """A small named stats tile."""

    def __init__(self, title: str, widget_id: str) -> None:
        super().__init__(id=widget_id, classes='stat-box')
        self._title = title
        self._value = '—'

    def compose(self) -> ComposeResult:
        yield Static(self._title, classes='stat-title')
        yield Static(self._value, id=f'{self.id}-val', classes='stat-value')

    def set_value(self, text: str) -> None:
        self.query_one(f'#{self.id}-val', Static).update(text)


class FastDrawTUI(App):
    CSS = CSS
    TITLE = 'Fast Draw'

    BINDINGS = [
        Binding('space', 'trigger', 'React / False-start', show=True),
        Binding('n', 'new_round', 'New Round', show=True),
        Binding('ctrl+q', 'quit', 'Quit', show=True),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._game = Game()
        self._active = False
        self._draw_ts: float | None = None
        self._worker: Worker | None = None

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('FAST DRAW', id='title')
        yield Static('React when you see DRAW!', id='subtitle')

        with Vertical(id='signal-box'):
            yield Static('—', id='signal')

        yield Static('Press N to start a round', id='msg')

        with Horizontal(id='stats-panel'):
            yield StatBox('Last', 'stat-last')
            yield StatBox('Best', 'stat-best')
            yield StatBox('Avg 10', 'stat-avg')
            yield StatBox('False\nStarts', 'stat-fails')

        yield Static('SPACE to react  •  N new round  •  Ctrl+Q quit', id='hint')
        yield Footer()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_new_round(self) -> None:
        if self._active:
            return
        self._start_round()

    def action_trigger(self) -> None:
        if not self._active:
            return
        phase = self._game.phase

        if phase == 'waiting':
            # False start — cancel background worker
            if self._worker:
                self._worker.cancel()
            result = self._game.false_start_now()
            self._active = False
            self._set_signal('FALSE\nSTART', 'false')
            self._set_msg('False start! Press N for a new round.')
            self._update_stats(result, false_start=True)

        elif phase == 'draw' and self._draw_ts is not None:
            elapsed_ms = (time.perf_counter() - self._draw_ts) * 1000
            result = self._game.react(elapsed_ms)
            self._active = False
            self._set_signal(f'{elapsed_ms:.0f}\nms', 'result')
            self._set_msg(f'Reaction: {elapsed_ms:.0f} ms — press N for next round')
            self._update_stats(result, false_start=False)

    # ------------------------------------------------------------------
    # Round flow
    # ------------------------------------------------------------------

    def _start_round(self) -> None:
        self._active = True
        self._draw_ts = None
        self._game.start_round()
        self._set_signal('WAIT', 'wait')
        self._set_msg('Hold on...')
        # Run the wait sleep in a background worker
        self._worker = self.run_worker(self._wait_worker, exclusive=True)

    async def _wait_worker(self) -> None:
        """Async worker: sleep the wait time then fire the DRAW signal."""
        import asyncio
        wait = self._game._wait_secs  # type: ignore[attr-defined]
        await asyncio.sleep(wait)
        # Post back to main thread
        self.call_from_thread(self._fire_draw)

    def _fire_draw(self) -> None:
        if not self._active:
            return
        self._game.draw_now()
        self._draw_ts = time.perf_counter()
        self._set_signal('DRAW!', 'draw')
        self._set_msg('PRESS SPACE NOW!')

    # ------------------------------------------------------------------
    # Widget helpers
    # ------------------------------------------------------------------

    def _set_signal(self, text: str, state: str) -> None:
        sig = self.query_one('#signal', Static)
        sig.update(text)
        sig.set_classes(f'state-{state}')

    def _set_msg(self, text: str) -> None:
        self.query_one('#msg', Static).update(text)

    def _update_stats(self, result: dict, false_start: bool) -> None:
        last_box = self.query_one('#stat-last', StatBox)
        best_box = self.query_one('#stat-best', StatBox)
        avg_box  = self.query_one('#stat-avg',  StatBox)
        fail_box = self.query_one('#stat-fails', StatBox)

        if false_start:
            last_box.set_value('FAIL')
        else:
            last_box.set_value(f'{result["ms"]:.0f} ms')

        best = result['best_ms']
        best_box.set_value(f'{best:.0f} ms' if best is not None else '—')

        valid = [e['ms'] for e in self._game.history[-10:]
                 if not e['false_start']]
        if valid:
            avg_box.set_value(f'{sum(valid)/len(valid):.0f} ms')
        else:
            avg_box.set_value('—')

        fails = sum(1 for e in self._game.history if e['false_start'])
        fail_box.set_value(str(fails))

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        # Worker cancelled (false-start) — nothing extra needed.
        if event.state == WorkerState.CANCELLED:
            pass


if __name__ == '__main__':
    FastDrawTUI().run()
