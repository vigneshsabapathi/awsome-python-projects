"""Trick Questions — CustomTkinter GUI.

Dark-themed desktop UI for the trick-question quiz.

Layout:
    - Big question label (centered, wraps)
    - Difficulty + score chip row
    - Answer entry with Submit button (Enter binding)
    - Hint button (reveals the hint inline)
    - Explanation reveal panel after each answer

Bindings:
    Enter        Submit answer (or advance to next question after a result)
    Ctrl+H       Reveal hint
    Ctrl+N       New question (skip)
    Ctrl+Q       Quit

Run:
    uv run python trick_questions/trick_questions_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from trick_questions import Quiz

# Dark Tailwind palette — matches clickbait_gui / bagels_gui.
BG = "#0f172a"
PANEL = "#1e293b"
BORDER = "#334155"
ACCENT = "#38bdf8"
ACCENT_HOVER = "#0ea5e9"
MUTED = "#94a3b8"
TEXT = "#f8fafc"
WARN = "#f87171"
OK = "#34d399"
HINT = "#eab308"

DIFFICULTY_COLOR = {
    "easy": "#22c55e",
    "medium": "#eab308",
    "hard": "#ef4444",
}

TITLE_FONT = ("Segoe UI", 28, "bold")
QUESTION_FONT = ("Segoe UI", 20, "bold")
LABEL_FONT = ("Segoe UI", 13)
META_FONT = ("Segoe UI", 12, "italic")
BTN_FONT = ("Segoe UI", 14, "bold")
EXPLAIN_FONT = ("Segoe UI", 13)


class TrickQuestionsApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.title("Trick Questions")
        self.geometry("780x640")
        self.minsize(640, 540)
        self.configure(fg_color=BG)

        self.quiz = Quiz(rng=random.Random())
        # awaiting_next: True between "submitted answer" and "next question",
        # so Enter advances to the next question without re-checking.
        self.awaiting_next = False

        self._build_ui()
        self._load_question()

        # Global key bindings.
        self.bind("<Return>", lambda _e: self._on_enter())
        self.bind("<Control-h>", lambda _e: self._on_hint())
        self.bind("<Control-n>", lambda _e: self._skip())
        self.bind("<Control-q>", lambda _e: self.destroy())
        self.after(100, self._focus_entry)

    def _focus_entry(self) -> None:
        try:
            self.entry.focus_force()
        except Exception:
            pass

    # ----- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(side="top", pady=(18, 4), padx=24, fill="x")
        ctk.CTkLabel(header, text="TRICK QUESTIONS", font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text="Read carefully — the obvious answer is rarely right.",
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Status row: difficulty + score chips.
        chips = ctk.CTkFrame(self, fg_color="transparent")
        chips.pack(side="top", pady=(8, 4), padx=24, fill="x")

        self.difficulty_chip = ctk.CTkLabel(
            chips, text=" EASY ", font=("Segoe UI", 12, "bold"),
            fg_color=DIFFICULTY_COLOR["easy"], text_color="#0f172a",
            corner_radius=12, width=80,
        )
        self.difficulty_chip.pack(side="left", padx=(0, 8))

        self.score_chip = ctk.CTkLabel(
            chips, text="Score 0/0", font=("Segoe UI", 12, "bold"),
            fg_color=PANEL, text_color=TEXT, corner_radius=12, width=120,
        )
        self.score_chip.pack(side="left", padx=4)

        self.streak_chip = ctk.CTkLabel(
            chips, text="Streak 0", font=("Segoe UI", 12, "bold"),
            fg_color=PANEL, text_color=ACCENT, corner_radius=12, width=100,
        )
        self.streak_chip.pack(side="left", padx=4)

        # Question panel — the centerpiece.
        panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=18,
                             border_color=BORDER, border_width=1)
        panel.pack(side="top", expand=True, fill="both",
                   padx=24, pady=(12, 8))

        self.question_label = ctk.CTkLabel(
            panel, text="", font=QUESTION_FONT, text_color=TEXT,
            wraplength=680, justify="center",
        )
        self.question_label.pack(expand=True, padx=24, pady=(28, 8))

        # Hint / explanation reveal area lives inside the panel.
        self.reveal_label = ctk.CTkLabel(
            panel, text="", font=EXPLAIN_FONT, text_color=MUTED,
            wraplength=680, justify="center",
        )
        self.reveal_label.pack(pady=(0, 24), padx=24)

        # Answer input row.
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(side="top", pady=(8, 4), padx=24, fill="x")
        self.entry = ctk.CTkEntry(
            input_frame, font=("Segoe UI", 16), height=44,
            placeholder_text="Type your answer and press Enter",
            fg_color=PANEL, border_color=BORDER, text_color=TEXT,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.entry.bind("<Return>", lambda _e: self._on_enter())

        self.submit_btn = ctk.CTkButton(
            input_frame, text="Submit", width=100, height=44,
            font=BTN_FONT, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#0f172a", command=self._on_enter,
        )
        self.submit_btn.pack(side="left")

        # Action row.
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(side="top", pady=(8, 4), padx=24, fill="x")
        self.hint_btn = ctk.CTkButton(
            actions, text="Hint (Ctrl+H)", font=BTN_FONT,
            fg_color=BORDER, hover_color="#475569", text_color=TEXT,
            command=self._on_hint,
        )
        self.hint_btn.pack(side="left", expand=True, fill="x", padx=(0, 6))

        self.skip_btn = ctk.CTkButton(
            actions, text="Skip (Ctrl+N)", font=BTN_FONT,
            fg_color=BORDER, hover_color="#475569", text_color=TEXT,
            command=self._skip,
        )
        self.skip_btn.pack(side="left", expand=True, fill="x", padx=(6, 0))

        self.status_label = ctk.CTkLabel(self, text=" ", font=LABEL_FONT,
                                         text_color=MUTED)
        self.status_label.pack(side="bottom", pady=(0, 12))

    # ----- behaviour -------------------------------------------------------
    def _load_question(self) -> None:
        self.current = self.quiz.next_question()
        self.question_label.configure(text=self.current["question"])
        self.reveal_label.configure(text="", text_color=MUTED)
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.submit_btn.configure(text="Submit", state="normal")
        self.hint_btn.configure(state="normal")
        self.awaiting_next = False
        self._refresh_chips()
        self._set_status("Press Enter to submit, or use the Hint button.",
                          MUTED)
        self.entry.focus()

    def _refresh_chips(self) -> None:
        s = self.quiz.state()
        diff = s["difficulty"]
        self.difficulty_chip.configure(
            text=f" {diff.upper()} ",
            fg_color=DIFFICULTY_COLOR.get(diff, ACCENT),
        )
        self.score_chip.configure(text=f"Score {s['score']}/{s['rounds']}")
        self.streak_chip.configure(text=f"Streak {s['streak']}")

    def _on_enter(self) -> None:
        if self.awaiting_next:
            self._load_question()
        else:
            self._submit()

    def _submit(self) -> None:
        guess = self.entry.get().strip()
        if not guess:
            self._set_status("Type an answer first.", WARN)
            return
        result = self.quiz.check(guess)
        self.awaiting_next = True
        self.entry.configure(state="disabled")
        self.submit_btn.configure(text="Next  >", state="normal")
        self.hint_btn.configure(state="disabled")

        if result["correct"]:
            verdict = "Correct!"
            color = OK
        else:
            verdict = "Not quite."
            color = WARN

        self.reveal_label.configure(
            text=f"{verdict}  {result['explanation']}",
            text_color=color,
        )
        if result["escalated"]:
            self._set_status(
                f"** Escalated to {self.quiz.difficulty.upper()} ** "
                "Press Enter for next question.",
                ACCENT,
            )
        else:
            self._set_status("Press Enter for the next question.", MUTED)
        self._refresh_chips()

    def _on_hint(self) -> None:
        if self.awaiting_next:
            return
        hint = self.quiz.use_hint()
        self.reveal_label.configure(text=f"Hint: {hint}", text_color=HINT)
        self._set_status("Hint revealed.", HINT)

    def _skip(self) -> None:
        # Skip behaves like a wrong answer: no score change, just reveal
        # the explanation and move on.
        if self.awaiting_next:
            self._load_question()
            return
        # Force a "wrong" check by submitting an obviously-wrong sentinel
        # that won't match any regex (single non-word character).
        result = self.quiz.check("​")  # zero-width space, never matches
        self.awaiting_next = True
        self.entry.configure(state="disabled")
        self.submit_btn.configure(text="Next  >", state="normal")
        self.hint_btn.configure(state="disabled")
        self.reveal_label.configure(
            text=f"Skipped.  {result['explanation']}",
            text_color=MUTED,
        )
        self._set_status("Press Enter for the next question.", MUTED)
        self._refresh_chips()

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, text_color=color)


if __name__ == "__main__":
    TrickQuestionsApp().mainloop()
