"""Gullible — Textual TUI.

A modern terminal UI for the Gullible trick game.
Dark Tailwind-inspired palette: slate-900 background, sky/cyan accents.

Bindings:
    Enter      Submit answer
    Ctrl+N     New round (fresh variant)
    Ctrl+Q     Quit

Run:
    uv run python gullible/gullible_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, Static

from gullible import Game


class GullibleApp(App):
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
        padding-bottom: 0;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #scorebar {
        text-align: center;
        color: #38bdf8;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
    }

    #prompt-box {
        border: tall #334155;
        background: #1e293b;
        padding: 1 2;
        margin: 0 4;
        height: auto;
        min-height: 5;
    }

    #prompt-text {
        color: #f8fafc;
        text-style: bold;
        text-align: center;
    }

    #verdict-box {
        padding: 1 2;
        margin: 1 4;
        height: auto;
        min-height: 2;
        border: tall #334155;
        background: #1e293b;
        display: none;
    }

    #verdict-box.visible {
        display: block;
    }

    #verdict-text {
        text-align: center;
        text-style: bold;
    }

    .verdict-gullible {
        color: #f87171;
    }

    .verdict-escaped {
        color: #34d399;
    }

    .verdict-loop {
        color: #eab308;
    }

    #input {
        margin: 1 4;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }

    #input:focus {
        border: tall #38bdf8;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 1;
        height: 1;
    }
    """

    BINDINGS = [
        Binding("enter", "submit", "Submit", show=False),
        Binding("ctrl+n", "new_round", "New Round"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    TITLE = "Gullible"

    def __init__(self) -> None:
        super().__init__()
        self.game = Game()
        self._answered: bool = False

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("G U L L I B L E", id="title")
        yield Static(
            "Are you the kind of person who falls for this sort of thing?",
            id="subtitle",
        )
        yield Static("", id="scorebar")
        with Vertical(id="prompt-box"):
            yield Static("", id="prompt-text")
        with Vertical(id="verdict-box"):
            yield Static("", id="verdict-text")
        yield Input(placeholder="Type yes or no and press Enter…", id="input")
        yield Static("Ctrl+N new round  |  Ctrl+Q quit", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_round()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_round(self) -> None:
        self.game.new_variant()
        self._answered = False

        self.query_one("#prompt-text", Static).update(
            self.game.variant["prompt"]
        )

        vbox = self.query_one("#verdict-box", Vertical)
        vbox.remove_class("visible")
        vt = self.query_one("#verdict-text", Static)
        vt.update("")
        vt.remove_class("verdict-gullible", "verdict-escaped", "verdict-loop")

        inp = self.query_one("#input", Input)
        inp.value = ""
        inp.disabled = False
        inp.placeholder = "Type yes or no and press Enter…"
        inp.focus()

        self._update_scorebar()

    def _update_scorebar(self) -> None:
        s = self.game.state()
        rate_txt = f"  {s['gullibility_rate'] * 100:.0f}%" if s["rounds"] else ""
        self.query_one("#scorebar", Static).update(
            f"Gullible: {s['gullible_count']}/{s['rounds']}{rate_txt}"
        )

    def _process_answer(self) -> None:
        inp = self.query_one("#input", Input)
        raw = inp.value.strip()
        if not raw:
            return

        result = self.game.ask(raw)
        vbox = self.query_one("#verdict-box", Vertical)
        vt   = self.query_one("#verdict-text", Static)

        vt.remove_class("verdict-gullible", "verdict-escaped", "verdict-loop")

        if result["verdict"] == "loop":
            vbox.add_class("visible")
            vt.update(result["message"])
            vt.add_class("verdict-loop")
            inp.value = ""
            inp.focus()
            return

        self._answered = True
        inp.disabled = True
        inp.placeholder = "Press Ctrl+N for a new round…"
        vbox.add_class("visible")
        vt.update(result["message"])

        if result["verdict"] == "gullible":
            vt.add_class("verdict-gullible")
        else:
            vt.add_class("verdict-escaped")

        self._update_scorebar()

    # ------------------------------------------------------------------
    # Actions / events
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._process_answer()

    def action_submit(self) -> None:
        self._process_answer()

    def action_new_round(self) -> None:
        self._load_round()


if __name__ == "__main__":
    GullibleApp().run()
