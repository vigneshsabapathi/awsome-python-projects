"""Ducklings — Textual TUI.

Dark Tailwind palette. Animated row of ASCII ducks waddling across the screen.

Bindings
--------
- space     play / pause
- +         increase speed
- -         decrease speed
- n         add a duck (up to 10)
- ctrl+q    quit

Run:
    uv run python ducklings/ducklings_tui.py
"""
from __future__ import annotations

import random

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from ducklings import Pond

# ---------------------------------------------------------------------------
# Tailwind dark palette
# ---------------------------------------------------------------------------
BG = "#0f172a"
PANEL = "#1e293b"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
DUCK_COLOR = "#fde68a"   # amber-200 — duck yellow

WIDTH = 80


class PondView(Static):
    """Renders the pond render string with duck-yellow colouring."""

    def render_pond(self, pond: Pond) -> Text:
        raw = pond.render()
        text = Text(no_wrap=True, overflow="ellipsis")
        for i, line in enumerate(raw.splitlines()):
            text.append(line, style=DUCK_COLOR)
            if i < len(raw.splitlines()) - 1:
                text.append("\n")
        return text


class DucklingsApp(App):
    CSS = f"""
    Screen {{
        background: {BG};
        color: {TEXT};
        align: center top;
    }}

    #title {{
        text-align: center;
        text-style: bold;
        color: {TEXT};
        padding-top: 1;
    }}

    #subtitle {{
        text-align: center;
        color: {MUTED};
        padding-bottom: 1;
    }}

    #pond_panel {{
        align: center middle;
        background: {PANEL};
        border: tall #334155;
        padding: 0 1;
        margin: 1 2;
    }}

    #pond_view {{
        width: auto;
        height: auto;
        background: {PANEL};
    }}

    #stats {{
        text-align: center;
        color: {MUTED};
        padding: 0 2;
    }}
    """

    BINDINGS = [
        Binding("space", "toggle_play", "Play/Pause"),
        Binding("+", "speed_up", "Faster"),
        Binding("-", "speed_down", "Slower"),
        Binding("n", "add_duck", "Add Duck"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    TITLE = "Ducklings"

    def __init__(self) -> None:
        super().__init__()
        self._num_ducks = 5
        self._fps = 10
        self._running = True
        self._pond = Pond(width=WIDTH, num_ducks=self._num_ducks, rng=random.Random())
        self._timer = None

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("🦆  DUCKLINGS  🦆", id="title")
        yield Static(
            "space play/pause  •  +/- speed  •  n add duck  •  ctrl+q quit",
            id="subtitle",
        )
        with Vertical(id="pond_panel"):
            yield PondView(id="pond_view")
        yield Static("", id="stats")
        yield Footer()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self._refresh()
        self._timer = self.set_interval(1.0 / self._fps, self._tick)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        view = self.query_one("#pond_view", PondView)
        view.update(view.render_pond(self._pond))
        self._update_stats()

    def _update_stats(self) -> None:
        status = "PLAYING" if self._running else "PAUSED "
        stats = (
            f"[{ACCENT}]{status}[/]   "
            f"ducks [{TEXT}]{self._num_ducks}[/]   "
            f"fps [{TEXT}]{self._fps}[/]   "
            f"species: mallard leads, regular & mandarin follow"
        )
        self.query_one("#stats", Static).update(stats)

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if not self._running:
            return
        self._pond.step()
        self._refresh()

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(1.0 / max(self._fps, 1), self._tick)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_toggle_play(self) -> None:
        self._running = not self._running
        self._update_stats()

    def action_speed_up(self) -> None:
        self._fps = min(30, self._fps + 2)
        self._reset_timer()
        self._update_stats()

    def action_speed_down(self) -> None:
        self._fps = max(1, self._fps - 2)
        self._reset_timer()
        self._update_stats()

    def action_add_duck(self) -> None:
        if self._num_ducks >= 10:
            return
        self._num_ducks += 1
        self._pond = Pond(width=WIDTH, num_ducks=self._num_ducks, rng=random.Random())
        self._refresh()


if __name__ == "__main__":
    DucklingsApp().run()
