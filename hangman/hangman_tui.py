"""Hangman — Textual TUI.

Modern terminal UI with Tailwind-ish dark palette.

    - ASCII gallows in a monospaced panel
    - Masked word tile row
    - On-screen QWERTY keyboard, recoloured per guess
    - Type any letter directly, or click

Bindings:
    Ctrl+N — New game
    Ctrl+C — Cycle category
    Ctrl+E — Toggle Evil mode
    Ctrl+Q — Quit

Run:
    uv run python hangman/hangman_tui.py
"""
from __future__ import annotations

from itertools import cycle

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.widgets import Footer, Header, Static

from hangman import (
    CATEGORIES,
    MAX_WRONG,
    STAGES,
    difficulty,
    is_lost,
    is_won,
    mask,
    pick_word,
)
from hangman_evil import EvilHangman

CATEGORY_CYCLE = ["random", *CATEGORIES.keys()]
KEYBOARD_ROWS = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")


class HangmanApp(App):
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

    #meta-row {
        height: auto;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .meta-chip {
        padding: 0 2;
        margin: 0 1;
        background: #1e293b;
        color: #cbd5e1;
        height: 1;
    }

    .meta-chip-evil {
        background: #7f1d1d;
        color: #fee2e2;
    }

    #body {
        height: auto;
        align-horizontal: center;
    }

    #gallows {
        width: 28;
        height: auto;
        padding: 1 2;
        background: #111827;
        color: #e2e8f0;
        margin: 0 2;
    }

    #info {
        width: 40;
        padding: 1 2;
        background: #111827;
        color: #cbd5e1;
        margin: 0 2;
        height: auto;
    }

    .info-line { padding: 0; }
    .info-wrong { color: #f87171; }
    .info-status { color: #f8fafc; text-style: bold; padding-top: 1; }
    .info-status-win  { color: #34d399; text-style: bold; padding-top: 1; }
    .info-status-lose { color: #f87171; text-style: bold; padding-top: 1; }

    #word-row {
        height: 3;
        align-horizontal: center;
        padding: 1 0;
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
    .tile-revealed { background: #0ea5e9; color: #0b1220; }
    .tile-space    { background: transparent; color: #94a3b8; }

    #keyboard {
        height: auto;
        align-horizontal: center;
        margin-top: 1;
    }

    .key-row {
        height: 3;
        align-horizontal: center;
    }

    .key {
        width: 5;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: #334155;
        color: #e2e8f0;
        margin: 0 1;
    }
    .key-used { background: #1f2937; color: #475569; }
    .key-hit  { background: #16a34a; color: white; }
    .key-miss { background: #dc2626; color: white; }
    """

    BINDINGS = [
        Binding("ctrl+n", "new_game", "New Game"),
        Binding("ctrl+c", "cycle_category", "Cycle Category"),
        Binding("ctrl+e", "toggle_evil", "Toggle Evil"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    TITLE = "Hangman"

    def __init__(self) -> None:
        super().__init__()
        self._cat_iter = cycle(CATEGORY_CYCLE)
        self.category_choice: str = next(self._cat_iter)
        self.evil_mode: bool = False
        self.word: str = ""
        self.category: str = ""
        self.guessed: set[str] = set()
        self.wrong: list[str] = []
        self.evil: EvilHangman | None = None
        self.game_over: bool = False
        self.tiles: list[Static] = []

    # ------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("HANGMAN", id="title")
        yield Static("Type a letter — six wrong guesses and you're done.",
                     id="subtitle")
        with Horizontal(id="meta-row"):
            yield Static("", classes="meta-chip", id="chip-category")
            yield Static("", classes="meta-chip", id="chip-difficulty")
            yield Static("", classes="meta-chip", id="chip-evil")
        with Horizontal(id="body"):
            yield Static("", id="gallows")
            with Vertical(id="info"):
                yield Static("", classes="info-line", id="info-length")
                yield Static("", classes="info-line info-wrong",
                             id="info-wrong")
                yield Static("", classes="info-line", id="info-used")
                yield Static("", classes="info-status", id="info-status")
        with Horizontal(id="word-row"):
            # tiles are added on new game when length is known
            pass
        with Vertical(id="keyboard"):
            for row in KEYBOARD_ROWS:
                with Horizontal(classes="key-row"):
                    for letter in row:
                        yield Static(letter, classes="key", id=f"key-{letter}")
        yield Footer()

    def on_mount(self) -> None:
        self._new_game()

    # ----------------------------------------------------------- actions --
    def action_new_game(self) -> None:
        self._new_game()

    def action_cycle_category(self) -> None:
        self.category_choice = next(self._cat_iter)
        self._new_game()

    def action_toggle_evil(self) -> None:
        self.evil_mode = not self.evil_mode
        self._new_game()

    # ----------------------------------------------------------- events ---
    def on_key(self, event: Key) -> None:
        if self.game_over:
            return
        ch = (event.character or "").upper()
        if len(ch) == 1 and "A" <= ch <= "Z":
            self._guess(ch)

    # --------------------------------------------------------- internals --
    def _new_game(self) -> None:
        self.guessed = set()
        self.wrong = []
        self.game_over = False

        cat_arg = (None if self.category_choice == "random"
                   else self.category_choice)
        if self.evil_mode:
            self.evil = EvilHangman(category=cat_arg)
            self.category = self.evil.category
            self.word = self.evil.peek_word()
        else:
            self.evil = None
            self.category, self.word = pick_word(cat_arg)

        self._build_tiles()
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            key = self.query_one(f"#key-{letter}", Static)
            key.set_classes("key")

        evil_chip = self.query_one("#chip-evil", Static)
        if self.evil_mode:
            evil_chip.update(" Evil mode ")
            evil_chip.set_classes("meta-chip meta-chip-evil")
        else:
            evil_chip.update(" Fair mode ")
            evil_chip.set_classes("meta-chip")

        self.query_one("#chip-category", Static).update(
            f" Category: {self.category} ")
        self.query_one("#chip-difficulty", Static).update(
            f" Difficulty: {difficulty(self.word)} ")

        length = sum(c.isalpha() for c in self.word)
        self.query_one("#info-length", Static).update(
            f"Word length: {length} letters")
        status = self.query_one("#info-status", Static)
        status.update("Pick a letter.")
        status.set_classes("info-status")

        self._render()

    def _build_tiles(self) -> None:
        row = self.query_one("#word-row", Horizontal)
        for tile in self.tiles:
            tile.remove()
        self.tiles = []
        for idx, ch in enumerate(self.word):
            if ch.isalpha():
                tile = Static("_", classes="tile",
                              id=f"tile-{idx}")
            else:
                tile = Static(ch, classes="tile tile-space",
                              id=f"tile-{idx}")
            row.mount(tile)
            self.tiles.append(tile)

    def _guess(self, letter: str) -> None:
        if letter in self.guessed:
            return
        self.guessed.add(letter)

        if self.evil is not None:
            hit = self.evil.guess(letter)
            self.word = self.evil.peek_word()
        else:
            hit = letter in self.word.upper()

        if not hit:
            self.wrong.append(letter)

        key = self.query_one(f"#key-{letter}", Static)
        key.set_classes("key " + ("key-hit" if hit else "key-miss"))
        self._render()

        if is_won(self.word, self.guessed):
            self._end_game(f"You won! Word was {self.word}.", "win")
        elif is_lost(len(self.wrong)):
            self._end_game(f"You lost. Word was {self.word}.", "lose")

    def _render(self) -> None:
        self.query_one("#gallows", Static).update(
            STAGES[min(len(self.wrong), MAX_WRONG)])
        masked = mask(self.word, self.guessed)
        for tile, ch in zip(self.tiles, masked):
            if ch == "_":
                tile.update("_")
                tile.set_classes("tile")
            elif ch.isalpha():
                tile.update(ch)
                tile.set_classes("tile tile-revealed")
            # punctuation/space tiles already styled at build time

        wrong_text = " ".join(self.wrong) if self.wrong else "(none)"
        self.query_one("#info-wrong", Static).update(
            f"Wrong: {wrong_text}  ({len(self.wrong)}/{MAX_WRONG})")
        used_text = " ".join(sorted(self.guessed)) if self.guessed else "(none)"
        self.query_one("#info-used", Static).update(f"Used:  {used_text}")

    def _end_game(self, message: str, kind: str) -> None:
        self.game_over = True
        status = self.query_one("#info-status", Static)
        status.update(message)
        status.set_classes(f"info-status info-status-{kind}")
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in self.guessed:
                key = self.query_one(f"#key-{letter}", Static)
                key.set_classes("key key-used")


if __name__ == "__main__":
    HangmanApp().run()
