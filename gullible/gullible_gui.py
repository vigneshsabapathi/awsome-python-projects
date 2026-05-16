"""Gullible — CustomTkinter GUI.

Dark-themed desktop UI for the Gullible trick game.

Layout:
    - Big prompt label (centered, wraps)
    - Answer entry with Submit button (Enter binding)
    - Verdict display with colour feedback
    - Gullibility score chip

Bindings:
    Enter     Submit answer
    Ctrl+N    New round (pick a fresh variant)
    Ctrl+Q    Quit

Run:
    uv run python gullible/gullible_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from gullible import Game

# Dark Tailwind palette — consistent with trick_questions_gui.
BG = "#0f172a"
PANEL = "#1e293b"
BORDER = "#334155"
ACCENT = "#38bdf8"
ACCENT_HOVER = "#0ea5e9"
MUTED = "#94a3b8"
TEXT = "#f8fafc"
WARN = "#f87171"
OK = "#34d399"
GOLD = "#eab308"

TITLE_FONT = ("Segoe UI", 28, "bold")
PROMPT_FONT = ("Segoe UI", 20, "bold")
LABEL_FONT = ("Segoe UI", 13)
BTN_FONT = ("Segoe UI", 14, "bold")
VERDICT_FONT = ("Segoe UI", 15, "bold")


class GullibleApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Gullible")
        self.geometry("740x560")
        self.minsize(580, 460)
        self.configure(fg_color=BG)

        self.game = Game()
        self.awaiting_next = False   # True after verdict shown

        self._build_ui()
        self._load_round()

        self.bind("<Return>",    lambda _e: self._on_enter())
        self.bind("<Control-n>", lambda _e: self._new_round())
        self.bind("<Control-q>", lambda _e: self.destroy())
        self.after(100, self._focus_entry)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Title row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(side="top", pady=(18, 4), padx=24, fill="x")
        ctk.CTkLabel(header, text="GULLIBLE", font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(
            header,
            text="Are you the kind of person who falls for this sort of thing?",
            font=LABEL_FONT, text_color=MUTED,
        ).pack(pady=(2, 0))

        # Score chip
        chips = ctk.CTkFrame(self, fg_color="transparent")
        chips.pack(side="top", pady=(8, 4), padx=24, fill="x")
        self.score_chip = ctk.CTkLabel(
            chips, text="Gullible 0/0", font=("Segoe UI", 12, "bold"),
            fg_color=PANEL, text_color=TEXT, corner_radius=12, width=160,
        )
        self.score_chip.pack(side="left", padx=4)

        self.rate_chip = ctk.CTkLabel(
            chips, text="Rate 0%", font=("Segoe UI", 12, "bold"),
            fg_color=PANEL, text_color=ACCENT, corner_radius=12, width=100,
        )
        self.rate_chip.pack(side="left", padx=4)

        # Question panel
        panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=18,
                             border_color=BORDER, border_width=1)
        panel.pack(side="top", expand=True, fill="both", padx=24, pady=(12, 8))

        self.prompt_label = ctk.CTkLabel(
            panel, text="", font=PROMPT_FONT, text_color=TEXT,
            wraplength=640, justify="center",
        )
        self.prompt_label.pack(expand=True, padx=24, pady=(28, 8))

        self.verdict_label = ctk.CTkLabel(
            panel, text="", font=VERDICT_FONT, text_color=MUTED,
            wraplength=640, justify="center",
        )
        self.verdict_label.pack(pady=(0, 24), padx=24)

        # Input row
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(side="top", pady=(8, 4), padx=24, fill="x")
        self.entry = ctk.CTkEntry(
            input_frame, font=("Segoe UI", 16), height=44,
            placeholder_text="Type yes or no and press Enter",
            fg_color=PANEL, border_color=BORDER, text_color=TEXT,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry.bind("<Return>", lambda _e: self._on_enter())

        self.submit_btn = ctk.CTkButton(
            input_frame, text="Submit", width=110, height=44,
            font=BTN_FONT, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#0f172a", command=self._on_enter,
        )
        self.submit_btn.pack(side="left")

        # Action row
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="top", pady=(8, 4), padx=24, fill="x")
        self.new_btn = ctk.CTkButton(
            actions, text="New Round (Ctrl+N)", font=BTN_FONT,
            fg_color=BORDER, hover_color="#475569", text_color=TEXT,
            command=self._new_round,
        )
        self.new_btn.pack(side="left", expand=True, fill="x")

        self.status_label = ctk.CTkLabel(
            self, text=" ", font=LABEL_FONT, text_color=MUTED,
        )
        self.status_label.pack(side="bottom", pady=(0, 12))

    # ------------------------------------------------------------------
    # Behaviour
    # ------------------------------------------------------------------

    def _load_round(self) -> None:
        self.game.new_variant()
        self.prompt_label.configure(text=self.game.variant["prompt"])
        self.verdict_label.configure(text="", text_color=MUTED)
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.submit_btn.configure(text="Submit", state="normal")
        self.awaiting_next = False
        self._refresh_chips()
        self._set_status("Press Enter to submit your answer.", MUTED)
        self.entry.focus()

    def _refresh_chips(self) -> None:
        s = self.game.state()
        rounds = s["rounds"]
        g = s["gullible_count"]
        rate = s["gullibility_rate"]
        self.score_chip.configure(text=f"Gullible {g}/{rounds}")
        color = WARN if rate > 0.5 else (OK if rounds > 0 else ACCENT)
        self.rate_chip.configure(
            text=f"Rate {rate * 100:.0f}%",
            text_color=color,
        )

    def _on_enter(self) -> None:
        if self.awaiting_next:
            self._load_round()
        else:
            self._submit()

    def _submit(self) -> None:
        raw = self.entry.get().strip()
        if not raw:
            self._set_status("Please type an answer first.", WARN)
            return

        result = self.game.ask(raw)

        if result["verdict"] == "loop":
            self.verdict_label.configure(
                text=result["message"], text_color=GOLD,
            )
            self._set_status("Keep going — yes or no only.", GOLD)
            self.entry.delete(0, "end")
            return

        # Round over — show verdict.
        self.awaiting_next = True
        self.entry.configure(state="disabled")
        self.submit_btn.configure(text="Next  >", state="normal")

        if result["verdict"] == "gullible":
            color = WARN
        else:
            color = OK

        self.verdict_label.configure(
            text=result["message"], text_color=color,
        )
        self._set_status("Press Enter for a new round.", MUTED)
        self._refresh_chips()

    def _new_round(self) -> None:
        self._load_round()

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, text_color=color)

    def _focus_entry(self) -> None:
        try:
            self.entry.focus_force()
        except Exception:
            pass


if __name__ == "__main__":
    GullibleApp().mainloop()
