"""Trick Questions — Textual TUI.

A modern terminal UI for the Trick Questions quiz.
Dark Tailwind-inspired palette: slate-900 background, sky/cyan accents.

Run:
    uv run python trick_questions/trick_questions_tui.py
    uv run python trick_questions/trick_questions_tui.py --seed 42
    uv run python trick_questions/trick_questions_tui.py --rounds 5
"""
from __future__ import annotations

import argparse
import random
import sys

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, Static

from trick_questions import Quiz


class TrickQuestionsApp(App):
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

    #question-box {
        border: tall #334155;
        background: #1e293b;
        padding: 1 2;
        margin: 0 4;
        height: auto;
        min-height: 5;
    }

    #difficulty-label {
        color: #94a3b8;
        text-style: italic;
        margin-bottom: 1;
    }

    #question-text {
        color: #f8fafc;
        text-style: bold;
    }

    #hint-box {
        background: #1c3a4a;
        border: tall #0e7490;
        color: #67e8f9;
        padding: 1 2;
        margin: 1 4;
        height: auto;
        display: none;
    }

    #hint-box.visible {
        display: block;
    }

    #feedback-box {
        padding: 1 2;
        margin: 0 4;
        height: auto;
        min-height: 3;
        border: tall #334155;
        background: #1e293b;
        display: none;
    }

    #feedback-box.visible {
        display: block;
    }

    .feedback-correct {
        color: #34d399;
        text-style: bold;
    }

    .feedback-wrong {
        color: #f87171;
        text-style: bold;
    }

    #explanation-text {
        color: #cbd5e1;
        margin-top: 1;
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
        Binding("ctrl+h", "hint", "Hint"),
        Binding("ctrl+n", "next_q", "Next", show=False),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    TITLE = "Trick Questions"

    def __init__(self, rounds: int = 10, seed: int | None = None) -> None:
        super().__init__()
        self.rounds = rounds
        self.rng = random.Random(seed)
        self.quiz = Quiz(rng=self.rng)
        self._current_item: dict = {}
        self._answered: bool = False
        self._asked: int = 0

    # ------------------------------------------------------------------
    # Compose
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("TRICK QUESTIONS", id="title")
        yield Static(
            "Read carefully — the obvious answer is rarely right.",
            id="subtitle",
        )
        yield Static("", id="scorebar")
        with Vertical(id="question-box"):
            yield Static("", id="difficulty-label")
            yield Static("", id="question-text")
        yield Static("", id="hint-box")
        with Vertical(id="feedback-box"):
            yield Static("", id="feedback-result")
            yield Static("", id="explanation-text")
        yield Input(placeholder="Type your answer and press Enter…", id="input")
        yield Static("Ctrl+H hint  |  Ctrl+Q quit", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_question()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_question(self) -> None:
        """Pull the next question and reset the UI."""
        self._current_item = self.quiz.next_question()
        self._answered = False

        diff = self._current_item["difficulty"].upper()
        diff_colors = {"EASY": "#34d399", "MEDIUM": "#fbbf24", "HARD": "#f87171"}
        color = diff_colors.get(diff, "#94a3b8")

        self.query_one("#difficulty-label", Static).update(
            f"[{color}]{diff}[/{color}]  —  Q{self._asked + 1} of {self.rounds}"
        )
        self.query_one("#question-text", Static).update(
            self._current_item["question"]
        )

        # Reset hint
        hint_box = self.query_one("#hint-box", Static)
        hint_box.remove_class("visible")
        hint_box.update("")

        # Reset feedback
        fb = self.query_one("#feedback-box", Vertical)
        fb.remove_class("visible")
        self.query_one("#feedback-result", Static).update("")
        self.query_one("#explanation-text", Static).update("")

        # Reset input
        inp = self.query_one("#input", Input)
        inp.value = ""
        inp.disabled = False
        inp.placeholder = "Type your answer and press Enter…"
        inp.focus()

        self._update_scorebar()

    def _update_scorebar(self) -> None:
        s = self.quiz.state()
        streak_txt = f"  streak {s['streak']}" if s["streak"] else ""
        acc = f"  {s['accuracy'] * 100:.0f}%" if s["rounds"] else ""
        tier = s["difficulty"].upper()
        self.query_one("#scorebar", Static).update(
            f"Score: {s['score']}/{s['rounds']}{acc}  |  Tier: {tier}{streak_txt}"
        )

    def _show_hint(self) -> None:
        hint_text = self.quiz.use_hint()
        hint_box = self.query_one("#hint-box", Static)
        hint_box.update(f"Hint: {hint_text}")
        hint_box.add_class("visible")

    def _submit_answer(self) -> None:
        if self._answered:
            # Already answered — move to next question on Enter
            self._asked += 1
            if self._asked >= self.rounds:
                self._show_final()
            else:
                self._load_question()
            return

        inp = self.query_one("#input", Input)
        raw = inp.value.strip()
        if not raw:
            return

        result = self.quiz.check(raw)
        self._answered = True
        inp.disabled = True
        inp.placeholder = "Press Enter for next question…"

        fb = self.query_one("#feedback-box", Vertical)
        fb.add_class("visible")

        result_widget = self.query_one("#feedback-result", Static)
        if result["correct"]:
            msg = "Correct!"
            if result["escalated"]:
                msg += f"  Difficulty escalated to {self.quiz.difficulty.upper()}!"
            result_widget.update(f"[#34d399]{msg}[/#34d399]")
        else:
            result_widget.update("[#f87171]Nope — not quite.[/#f87171]")

        self.query_one("#explanation-text", Static).update(
            result["explanation"]
        )
        self._update_scorebar()

    def _show_final(self) -> None:
        """Replace question box content with end-of-game summary."""
        s = self.quiz.state()
        acc = s["accuracy"] * 100
        self.query_one("#difficulty-label", Static).update(
            "— Game Over —"
        )
        self.query_one("#question-text", Static).update(
            f"Final score: {s['score']}/{s['rounds']}  ({acc:.0f}%)\n"
            f"Final tier: {s['difficulty'].upper()}\n\n"
            "Press Ctrl+Q to quit."
        )
        self.query_one("#input", Input).disabled = True
        hint_box = self.query_one("#hint-box", Static)
        hint_box.remove_class("visible")
        fb = self.query_one("#feedback-box", Vertical)
        fb.remove_class("visible")

    # ------------------------------------------------------------------
    # Actions / events
    # ------------------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._submit_answer()

    def action_submit(self) -> None:
        self._submit_answer()

    def action_hint(self) -> None:
        if not self._answered:
            self._show_hint()

    def action_next_q(self) -> None:
        if self._answered:
            self._asked += 1
            if self._asked >= self.rounds:
                self._show_final()
            else:
                self._load_question()


# --- Entry point -------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trick Questions — Textual TUI."
    )
    parser.add_argument("-r", "--rounds", type=int, default=10,
                        help="number of questions (default: 10)")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="random seed for reproducible order")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args()
    app = TrickQuestionsApp(rounds=args.rounds, seed=args.seed)
    app.run()
