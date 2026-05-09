"""Hangman — CustomTkinter GUI.

A dark-themed desktop UI:
    - ASCII gallows in a monospaced label
    - Masked word as big tiles
    - On-screen A-Z keyboard (greyed when used, green/red after click)
    - Category dropdown + Evil mode toggle + New Game button

Run:
    uv run python hangman/hangman_gui.py
"""
from __future__ import annotations

import tkinter as tk
from typing import Iterable

import customtkinter as ctk

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

PALETTE = {
    "bg":            "#0f172a",
    "panel":         "#111827",
    "tile_empty":    ("#1f2937", "#6b7280"),
    "tile_revealed": ("#0ea5e9", "#0b1220"),
    "key_idle":      ("#334155", "#e2e8f0"),
    "key_used":      ("#1f2937", "#475569"),
    "key_hit":       ("#16a34a", "#ffffff"),
    "key_miss":      ("#dc2626", "#ffffff"),
    "text_dim":      "#94a3b8",
    "text":          "#f8fafc",
    "win":           "#34d399",
    "lose":          "#f87171",
}

GALLOWS_FONT = ("Consolas", 14)
TILE_FONT = ("Segoe UI", 26, "bold")
TITLE_FONT = ("Segoe UI", 30, "bold")
LABEL_FONT = ("Segoe UI", 13)
KEY_FONT = ("Segoe UI", 13, "bold")
STATUS_FONT = ("Segoe UI", 14, "bold")


class HangmanApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Hangman")
        self.geometry("780x880")
        self.minsize(720, 820)
        self.configure(fg_color=PALETTE["bg"])

        self.category_var = tk.StringVar(value="random")
        self.evil_var = tk.BooleanVar(value=False)

        self.word: str = ""
        self.category: str = ""
        self.guessed: set[str] = set()
        self.wrong: list[str] = []
        self.evil: EvilHangman | None = None
        self.game_over: bool = False
        self.tiles: list[ctk.CTkLabel] = []
        self.key_buttons: dict[str, ctk.CTkButton] = {}

        self._build_ui()
        self._new_game()
        self.bind("<Key>", self._on_key)

    # ------------------------------------------------------------------ UI --
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(side="top", pady=(16, 4), padx=20, fill="x")
        ctk.CTkLabel(header, text="HANGMAN", font=TITLE_FONT,
                     text_color=PALETTE["text"]).pack()
        ctk.CTkLabel(
            header,
            text="Guess the word, one letter at a time. Six strikes and you're out.",
            font=LABEL_FONT, text_color=PALETTE["text_dim"]).pack(pady=(2, 0))

        # Controls (top-aligned).
        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.pack(side="top", padx=20, pady=(8, 4), fill="x")

        ctk.CTkLabel(controls, text="Category:",
                     font=LABEL_FONT,
                     text_color=PALETTE["text_dim"]).pack(side="left",
                                                          padx=(0, 6))
        self.category_menu = ctk.CTkOptionMenu(
            controls,
            variable=self.category_var,
            values=["random", *CATEGORIES.keys()],
            width=130,
            fg_color="#1e293b", button_color="#334155",
            button_hover_color="#475569",
        )
        self.category_menu.pack(side="left")

        self.evil_switch = ctk.CTkSwitch(
            controls, text="Evil mode",
            variable=self.evil_var,
            onvalue=True, offvalue=False,
            progress_color="#dc2626",
        )
        self.evil_switch.pack(side="left", padx=14)

        self.new_btn = ctk.CTkButton(
            controls, text="New Game", width=120,
            fg_color="#334155", hover_color="#475569",
            command=self._new_game)
        self.new_btn.pack(side="right")

        # Gallows + meta side-by-side.
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="top", pady=8, padx=20, fill="x")

        self.gallows_label = ctk.CTkLabel(
            body, text="", font=GALLOWS_FONT, justify="left",
            text_color=PALETTE["text"], anchor="w")
        self.gallows_label.pack(side="left", padx=(0, 24))

        meta = ctk.CTkFrame(body, fg_color="transparent")
        meta.pack(side="left", fill="both", expand=True)

        self.category_label = ctk.CTkLabel(
            meta, text="", font=LABEL_FONT, text_color=PALETTE["text_dim"],
            anchor="w", justify="left")
        self.category_label.pack(anchor="w", pady=(8, 4))

        self.wrong_label = ctk.CTkLabel(
            meta, text="", font=LABEL_FONT, text_color=PALETTE["lose"],
            anchor="w", justify="left", wraplength=320)
        self.wrong_label.pack(anchor="w", pady=4)

        self.status = ctk.CTkLabel(
            meta, text="", font=STATUS_FONT, text_color=PALETTE["text"],
            anchor="w", justify="left", wraplength=320)
        self.status.pack(anchor="w", pady=(12, 0))

        # Tile row for the masked word.
        self.tile_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.tile_frame.pack(side="top", pady=(8, 8))

        # Keyboard.
        kb = ctk.CTkFrame(self, fg_color="transparent")
        kb.pack(side="top", pady=(8, 12))
        rows = ("QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM")
        for row in rows:
            row_frame = ctk.CTkFrame(kb, fg_color="transparent")
            row_frame.pack(pady=3)
            for letter in row:
                btn = ctk.CTkButton(
                    row_frame, text=letter, width=46, height=42,
                    font=KEY_FONT,
                    fg_color=PALETTE["key_idle"][0],
                    text_color=PALETTE["key_idle"][1],
                    hover_color="#475569",
                    command=lambda L=letter: self._guess(L),
                )
                btn.pack(side="left", padx=3)
                self.key_buttons[letter] = btn

    # --------------------------------------------------------------- state --
    def _new_game(self) -> None:
        cat_choice = self.category_var.get()
        category_arg = None if cat_choice == "random" else cat_choice

        self.guessed = set()
        self.wrong = []
        self.game_over = False

        if self.evil_var.get():
            self.evil = EvilHangman(category=category_arg)
            self.category = self.evil.category
            self.word = self.evil.peek_word()  # length only — final word picked at the end
        else:
            self.evil = None
            self.category, self.word = pick_word(category_arg)

        # Rebuild tiles for the (possibly different) word length.
        for tile in self.tiles:
            tile.destroy()
        self.tiles = []
        for ch in self.word:
            if ch.isalpha():
                bg, fg = PALETTE["tile_empty"]
                tile = ctk.CTkLabel(
                    self.tile_frame, text="_", width=44, height=56,
                    fg_color=bg, text_color=fg,
                    corner_radius=8, font=TILE_FONT)
            else:
                tile = ctk.CTkLabel(
                    self.tile_frame, text=ch, width=20, height=56,
                    fg_color="transparent",
                    text_color=PALETTE["text_dim"],
                    font=TILE_FONT)
            tile.pack(side="left", padx=3)
            self.tiles.append(tile)

        for btn in self.key_buttons.values():
            btn.configure(
                state="normal",
                fg_color=PALETTE["key_idle"][0],
                text_color=PALETTE["key_idle"][1])

        evil_tag = "  (Evil)" if self.evil else ""
        self.category_label.configure(
            text=f"Category: {self.category}{evil_tag}\n"
                 f"Length: {sum(c.isalpha() for c in self.word)} letters\n"
                 f"Difficulty: {difficulty(self.word)}")
        self.wrong_label.configure(text=f"Wrong: (none)  0/{MAX_WRONG}")
        self.status.configure(text="Pick a letter — type or click.",
                              text_color=PALETTE["text"])
        self._render()
        self.focus_set()

    def _guess(self, letter: str) -> None:
        if self.game_over or letter in self.guessed:
            return
        self.guessed.add(letter)

        if self.evil is not None:
            hit = self.evil.guess(letter)
            self.word = self.evil.peek_word()  # may have shifted
        else:
            hit = letter in self.word.upper()

        if not hit:
            self.wrong.append(letter)

        # Update the keyboard styling.
        btn = self.key_buttons[letter]
        if hit:
            btn.configure(
                fg_color=PALETTE["key_hit"][0],
                text_color=PALETTE["key_hit"][1],
                state="disabled")
        else:
            btn.configure(
                fg_color=PALETTE["key_miss"][0],
                text_color=PALETTE["key_miss"][1],
                state="disabled")

        self._render()

        if is_won(self.word, self.guessed):
            self._end(f"You won! Word was {self.word}.", PALETTE["win"])
        elif is_lost(len(self.wrong)):
            self._end(f"You lost. Word was {self.word}.", PALETTE["lose"])

    def _render(self) -> None:
        self.gallows_label.configure(
            text=STAGES[min(len(self.wrong), MAX_WRONG)])
        masked = mask(self.word, self.guessed)
        for tile, ch in zip(self.tiles, masked):
            if ch.isalpha():
                tile.configure(text=ch,
                               fg_color=PALETTE["tile_revealed"][0],
                               text_color=PALETTE["tile_revealed"][1])
            elif ch == "_":
                bg, fg = PALETTE["tile_empty"]
                tile.configure(text="_", fg_color=bg, text_color=fg)
        wrong_text = " ".join(self.wrong) if self.wrong else "(none)"
        self.wrong_label.configure(
            text=f"Wrong: {wrong_text}  {len(self.wrong)}/{MAX_WRONG}")

    def _end(self, message: str, color: str) -> None:
        self.game_over = True
        self.status.configure(text=message, text_color=color)
        for btn in self.key_buttons.values():
            btn.configure(state="disabled")

    # ----------------------------------------------------------- events ----
    def _on_key(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if event.keysym.lower() == "return" or event.keysym == "F2":
            self._new_game()
            return
        ch = event.char.upper()
        if len(ch) == 1 and ch.isalpha() and ch in self.key_buttons:
            self._guess(ch)


def _coerce(_: Iterable[str]) -> None:  # pragma: no cover - keeps linters happy
    return None


if __name__ == "__main__":
    HangmanApp().mainloop()
