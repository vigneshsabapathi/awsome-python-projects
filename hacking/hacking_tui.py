"""Hacking — Textual TUI.

Same gameplay as the CLI/GUI rendered with a Textual dark-terminal palette.
Press 1-9, 0, or a-e to attempt the word at that tag; n for a new game; h for
the optimal-info-gain hint; Ctrl+Q to quit.

Run:
    uv run python hacking/hacking_tui.py
"""
from __future__ import annotations

import random
import string

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, RichLog, Static

from hacking import (
    JUNK_LINES,
    MAX_TRIES,
    NUM_WORDS,
    WORD_LENGTH,
    Game,
    render_junk_wall,
)

# Tag characters mapped to candidate-word indexes.
TAGS = "1234567890" + string.ascii_lowercase[:max(0, NUM_WORDS - 10)]


def _tag_for(idx: int) -> str:
    """Return the keypress tag for candidate index `idx`."""
    if 0 <= idx < len(TAGS):
        return TAGS[idx]
    return "?"


class HackingApp(App):
    CSS = """
    Screen {
        background: #040a04;
        color: #33ff66;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #33ff66;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #1a8033;
        padding-bottom: 1;
    }

    #body {
        height: 1fr;
        width: 100%;
    }

    #wall {
        width: 3fr;
        height: 1fr;
        border: round #1a8033;
        background: #040a04;
        color: #33ff66;
        padding: 1 2;
        content-align: left top;
    }

    #side {
        width: 2fr;
        height: 1fr;
    }

    #status {
        height: 4;
        border: round #1a8033;
        background: #040a04;
        color: #33ff66;
        padding: 1 2;
        margin-bottom: 1;
        text-style: bold;
    }

    #log {
        height: 1fr;
        border: round #1a8033;
        background: #040a04;
        color: #33ff66;
    }

    .status-low {
        color: #ff5555;
    }
    """

    BINDINGS = [
        Binding("n", "new_game", "New"),
        Binding("h", "hint", "Hint"),
        Binding("ctrl+q", "quit", "Quit"),
    ] + [
        Binding(t, f"try_idx({i})", f"try {t}")
        for i, t in enumerate(TAGS) if i < NUM_WORDS
    ]

    TITLE = "ROBCO TERMLINK"

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.game: Game | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL", id="title")
        yield Static("ENTER PASSWORD NOW", id="subtitle")
        with Horizontal(id="body"):
            yield Static("", id="wall", expand=True)
            with Vertical(id="side"):
                yield Static("", id="status")
                yield RichLog(id="log", highlight=False, markup=True,
                              wrap=True)
        yield Footer()

    def on_mount(self) -> None:
        self._new_game()

    # ----------------------------------------------------------- game ops
    def action_new_game(self) -> None:
        self._new_game()

    def action_hint(self) -> None:
        if self.game is None or self.game.finished:
            return
        pick = self.game.hint()
        log = self.query_one("#log", RichLog)
        if pick is None:
            log.write("[red]> HINT: NO CONSISTENT CANDIDATES[/red]")
        else:
            log.write(
                f"[bold yellow]> HINT: TRY '{pick}'[/bold yellow]"
                " [dim](max info gain)[/dim]")

    def action_try_idx(self, idx: int) -> None:
        if self.game is None or self.game.finished:
            return
        if not (0 <= idx < len(self.game.words)):
            return
        self._attempt(self.game.words[idx])

    # ----------------------------------------------------------- internal
    def _new_game(self) -> None:
        self.game = Game.new(n=NUM_WORDS, length=WORD_LENGTH,
                             max_tries=MAX_TRIES, rng=self.rng)
        self._render_wall()
        self._refresh_status()
        log = self.query_one("#log", RichLog)
        log.clear()
        log.write("[dim]> CONNECTING...[/dim]")
        log.write(f"[dim]> {NUM_WORDS} CANDIDATES IDENTIFIED[/dim]")
        log.write("[dim]> PRESS A TAG (1-9, 0, a-e) TO ATTEMPT[/dim]")

    def _render_wall(self) -> None:
        assert self.game is not None
        # Junk wall on top, then a tagged candidate-word menu.
        lines, _ = render_junk_wall(
            self.game.words, lines=JUNK_LINES, rng=self.rng)
        wall_text = "\n".join(lines)

        menu_lines = ["", "[dim]>> CANDIDATES <<[/dim]"]
        for i, w in enumerate(self.game.words):
            tag = _tag_for(i)
            menu_lines.append(f"[bold yellow][{tag}][/bold yellow] {w}")
        wall = self.query_one("#wall", Static)
        wall.update(wall_text + "\n" + "\n".join(menu_lines))

    def _attempt(self, word: str) -> None:
        assert self.game is not None
        log = self.query_one("#log", RichLog)
        before = self.game.tries_left
        result = self.game.try_word(word)
        outcome = result["result"]
        if outcome == "invalid":
            log.write(f"[red]> {word!r} not a candidate[/red]")
            return
        if outcome == "win":
            log.write(f"[bold yellow]> ATTEMPT: {word}[/bold yellow]")
            log.write("[bold yellow]> EXACT MATCH — ACCESS GRANTED[/bold yellow]")
        elif outcome == "wrong":
            log.write(f"[red]> ATTEMPT: {word}[/red]")
            log.write(
                f"[red]>   ENTRY DENIED  |  LIKENESS = "
                f"{result['likeness']}/{WORD_LENGTH}[/red]")
        elif outcome == "lose":
            log.write(f"[red]> ATTEMPT: {word}[/red]")
            log.write(
                f"[red]>   LIKENESS = {result['likeness']}/"
                f"{WORD_LENGTH}[/red]")
            log.write("[red]>   LOCKOUT — TERMINAL DISABLED[/red]")
            log.write(f"[red]>   PASSWORD WAS: {self.game.secret}[/red]")
        # Touch `before` so static analysers don't complain about unused.
        _ = before
        self._refresh_status()

    def _refresh_status(self) -> None:
        assert self.game is not None
        left = self.game.tries_left
        total = self.game.max_tries
        bar = "[" + "#" * left + "." * (total - left) + "]"
        status = self.query_one("#status", Static)
        status.update(f"ATTEMPTS LEFT: {left} / {total}\n{bar}")
        if left <= 1:
            status.set_classes("status-low")
        else:
            status.set_classes("")


if __name__ == "__main__":
    HackingApp().run()
