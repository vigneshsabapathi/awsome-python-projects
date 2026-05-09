"""Hacking — CustomTkinter GUI.

A green-on-black "Fallout terminal" desktop UI for the password hacking
minigame. The wall of pseudo-code is rendered into a Text widget; each
candidate password is a clickable hot-zone. Click to attempt; the log on the
right shows ATTEMPT results, likeness scores, and remaining tries.

Run:
    uv run python hacking/hacking_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from hacking import (
    JUNK_LINES,
    MAX_TRIES,
    NUM_WORDS,
    WORD_LENGTH,
    Game,
    render_junk_wall,
)

# Palette — classic Fallout terminal: phosphor-green text on near-black.
BG = "#040a04"
FG = "#33ff66"
FG_DIM = "#1a8033"
FG_HOT = "#7fff9f"      # hovered/active word
FG_TRIED = "#ff5555"    # rejected attempt
FG_WIN = "#ffff66"
ACCENT = "#0c1f0c"

MONO = ("Consolas", 13)
MONO_BIG = ("Consolas", 14, "bold")
TITLE_FONT = ("Consolas", 18, "bold")


class HackingApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title("ROBCO TERMLINK")
        self.geometry("980x620")
        self.minsize(820, 520)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.game: Game | None = None
        # Map of (line_idx, col_start, col_end, word) used to wire clicks.
        self._slots: list[tuple[int, int, int, str]] = []
        # Word -> result: 'wrong' | 'win'. Rejected words turn red and disable.
        self._word_state: dict[str, str] = {}

        self._build_ui()
        self._new_game()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(side="top", fill="x", padx=14, pady=(10, 4))
        ctk.CTkLabel(header, text="ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL",
                     font=TITLE_FONT, text_color=FG).pack(anchor="w")
        ctk.CTkLabel(header, text="ENTER PASSWORD NOW",
                     font=MONO, text_color=FG_DIM).pack(anchor="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="top", fill="both", expand=True, padx=14, pady=8)

        # Use grid so left/right share height cleanly.
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)

        # --- Left: junk wall ----------------------------------------------
        wall_frame = ctk.CTkFrame(body, fg_color=ACCENT,
                                  border_color=FG_DIM, border_width=1)
        wall_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        # Tk Text rather than CTkTextbox so we can tag-bind individual
        # word ranges. Looks fine without ctk styling on a fixed bg.
        import tkinter as tk
        self.wall = tk.Text(wall_frame, bg=BG, fg=FG, font=MONO,
                            insertbackground=FG, relief="flat", bd=0,
                            padx=10, pady=8, wrap="none",
                            cursor="arrow",
                            selectbackground=FG_DIM,
                            selectforeground=BG)
        self.wall.pack(fill="both", expand=True, padx=2, pady=2)
        self.wall.configure(state="disabled")

        # Pre-create the static tags. Per-word tags are created/configured
        # at render time (each gets its own tag so we can disable them
        # individually).
        self.wall.tag_configure("addr", foreground=FG_DIM)

        # --- Right: status + log ------------------------------------------
        side = ctk.CTkFrame(body, fg_color="transparent")
        side.grid(row=0, column=1, sticky="nsew")
        side.grid_rowconfigure(2, weight=1)
        side.grid_columnconfigure(0, weight=1)

        # Status block.
        status_frame = ctk.CTkFrame(side, fg_color=ACCENT,
                                    border_color=FG_DIM, border_width=1)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        self.tries_lbl = ctk.CTkLabel(status_frame, text="",
                                      font=MONO_BIG, text_color=FG)
        self.tries_lbl.pack(anchor="w", padx=10, pady=(8, 0))
        self.bar_lbl = ctk.CTkLabel(status_frame, text="",
                                    font=MONO_BIG, text_color=FG)
        self.bar_lbl.pack(anchor="w", padx=10, pady=(0, 8))

        # Buttons row.
        btn_row = ctk.CTkFrame(side, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.new_btn = ctk.CTkButton(
            btn_row, text="NEW GAME", font=MONO_BIG,
            fg_color=ACCENT, hover_color=FG_DIM, border_color=FG_DIM,
            border_width=1, text_color=FG, command=self._new_game)
        self.new_btn.pack(side="left", padx=(0, 6))
        self.hint_btn = ctk.CTkButton(
            btn_row, text="OPTIMAL HINT", font=MONO_BIG,
            fg_color=ACCENT, hover_color=FG_DIM, border_color=FG_DIM,
            border_width=1, text_color=FG, command=self._show_hint)
        self.hint_btn.pack(side="left")

        # Attempt log.
        log_frame = ctk.CTkFrame(side, fg_color=ACCENT,
                                 border_color=FG_DIM, border_width=1)
        log_frame.grid(row=2, column=0, sticky="nsew")
        ctk.CTkLabel(log_frame, text="> ATTEMPT LOG", font=MONO_BIG,
                     text_color=FG_DIM).pack(anchor="w", padx=10,
                                             pady=(6, 2))
        import tkinter as tk
        self.log = tk.Text(log_frame, bg=BG, fg=FG, font=MONO,
                           insertbackground=FG, relief="flat", bd=0,
                           padx=10, pady=4, wrap="word",
                           selectbackground=FG_DIM, selectforeground=BG,
                           height=14)
        self.log.pack(fill="both", expand=True, padx=2, pady=(0, 2))
        self.log.tag_configure("win", foreground=FG_WIN)
        self.log.tag_configure("err", foreground=FG_TRIED)
        self.log.tag_configure("dim", foreground=FG_DIM)
        self.log.configure(state="disabled")

    # ----------------------------------------------------------- new game
    def _new_game(self) -> None:
        self.game = Game.new(n=NUM_WORDS, length=WORD_LENGTH,
                             max_tries=MAX_TRIES, rng=self.rng)
        self._word_state.clear()
        self._render_wall()
        self._refresh_status()
        self._reset_log()
        self._log("> CONNECTING...", "dim")
        self._log(f"> {NUM_WORDS} CANDIDATES IDENTIFIED", "dim")
        self._log("> CLICK A WORD TO ATTEMPT", "dim")

    def _render_wall(self) -> None:
        assert self.game is not None
        lines, placements = render_junk_wall(
            self.game.words, lines=JUNK_LINES, rng=self.rng)
        self.wall.configure(state="normal")
        self.wall.delete("1.0", "end")

        # Drop existing word-tags from previous round.
        for tag in self.wall.tag_names():
            if tag.startswith("word-"):
                self.wall.tag_delete(tag)

        for i, ln in enumerate(lines):
            self.wall.insert("end", ln + "\n")
            # Tag the leading address ("0xF000  ") in dim.
            self.wall.tag_add("addr", f"{i + 1}.0", f"{i + 1}.8")

        # Now tag + bind each word slot.
        self._slots.clear()
        for line_idx, col, word in placements:
            # Address prefix is exactly 8 chars ("0x????  ") so the column
            # index inside the text widget needs that offset.
            start = f"{line_idx + 1}.{col + 8}"
            end = f"{line_idx + 1}.{col + 8 + len(word)}"
            tag = f"word-{word}"
            self.wall.tag_add(tag, start, end)
            self.wall.tag_configure(
                tag, foreground=FG, background=ACCENT,
                font=MONO_BIG)
            self.wall.tag_bind(
                tag, "<Enter>",
                lambda _e, t=tag: self._on_hover(t, True))
            self.wall.tag_bind(
                tag, "<Leave>",
                lambda _e, t=tag: self._on_hover(t, False))
            self.wall.tag_bind(
                tag, "<Button-1>",
                lambda _e, w=word: self._attempt(w))
            self._slots.append((line_idx, col, col + len(word), word))

        self.wall.configure(state="disabled")

    def _on_hover(self, tag: str, entering: bool) -> None:
        word = tag[len("word-"):]
        if self._word_state.get(word) == "wrong":
            return  # Already tried — leave red, no hover effect.
        if entering:
            self.wall.tag_configure(tag, foreground=FG_HOT)
            self.wall.configure(cursor="hand2")
        else:
            state = self._word_state.get(word)
            color = FG_TRIED if state == "wrong" else FG
            self.wall.tag_configure(tag, foreground=color)
            self.wall.configure(cursor="arrow")

    # ----------------------------------------------------------- gameplay
    def _attempt(self, word: str) -> None:
        assert self.game is not None
        if self.game.finished:
            return
        if self._word_state.get(word) == "wrong":
            return  # Already rejected — don't burn a try.
        result = self.game.try_word(word)
        outcome = result["result"]
        if outcome == "invalid":
            return
        if outcome == "win":
            self._word_state[word] = "win"
            self.wall.tag_configure(
                f"word-{word}", foreground=FG_WIN, background=FG_DIM)
            self._log(f"> ATTEMPT: {word}", "win")
            self._log("> EXACT MATCH — ACCESS GRANTED", "win")
        elif outcome == "wrong":
            self._word_state[word] = "wrong"
            self.wall.tag_configure(
                f"word-{word}", foreground=FG_TRIED, background=ACCENT)
            self._log(f"> ATTEMPT: {word}", "err")
            self._log(
                f">   ENTRY DENIED  |  LIKENESS = {result['likeness']}/"
                f"{WORD_LENGTH}", "err")
        elif outcome == "lose":
            self._word_state[word] = "wrong"
            self.wall.tag_configure(
                f"word-{word}", foreground=FG_TRIED, background=ACCENT)
            self._log(f"> ATTEMPT: {word}", "err")
            self._log(
                f">   LIKENESS = {result['likeness']}/{WORD_LENGTH}", "err")
            self._log(">   LOCKOUT — TERMINAL DISABLED", "err")
            self._log(f">   PASSWORD WAS: {self.game.secret}", "err")
        self._refresh_status()

    def _show_hint(self) -> None:
        assert self.game is not None
        if self.game.finished:
            return
        pick = self.game.hint()
        if pick is None:
            self._log("> HINT: NO CONSISTENT CANDIDATES", "err")
            return
        self._log(f"> HINT: TRY '{pick}' (max info gain)", "win")

    def _refresh_status(self) -> None:
        assert self.game is not None
        left = self.game.tries_left
        total = self.game.max_tries
        bar = "[" + "#" * left + "." * (total - left) + "]"
        self.tries_lbl.configure(
            text=f"ATTEMPTS LEFT: {left} / {total}")
        color = FG_TRIED if left <= 1 else FG
        self.bar_lbl.configure(text=bar, text_color=color)

    # ----------------------------------------------------------------- log
    def _reset_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _log(self, text: str, tag: str | None = None) -> None:
        self.log.configure(state="normal")
        if tag:
            self.log.insert("end", text + "\n", tag)
        else:
            self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


if __name__ == "__main__":
    HackingApp().mainloop()
