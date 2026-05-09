"""Dice Math — CustomTkinter GUI.

A dark-themed desktop UI for the Dice Math drill. Big rendered ASCII dice
faces, answer entry, Submit button (Enter binding), score, timer, difficulty
slider (2..6 dice), streak counter, and a mode selector.

Run:
    uv run python dice_math/dice_math_gui.py
"""
from __future__ import annotations

import random
import time

import customtkinter as ctk

from dice_math import (
    MODES,
    correct_answer,
    format_dice,
    roll,
    save_high_score,
    score_round,
)

DICE_FONT = ('Cascadia Mono', 22, 'bold')
TITLE_FONT = ('Segoe UI', 30, 'bold')
LABEL_FONT = ('Segoe UI', 13)
STATUS_FONT = ('Segoe UI', 14, 'bold')
SCORE_FONT = ('Segoe UI', 16, 'bold')

BG = '#0f172a'
CARD = '#1e293b'
ACCENT = '#38bdf8'
GOOD = '#34d399'
BAD = '#f87171'
MUTED = '#94a3b8'


class DiceMathApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Dice Math')
        self.geometry('640x720')
        self.minsize(560, 680)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.num_dice = 3
        self.mode = 'sum'
        self.values: list[int] = []
        self.target: int | str = 0
        self.score = 0
        self.streak = 0
        self.best_streak = 0
        self.round_num = 0
        self.start_time: float | None = None
        self._timer_job: str | None = None

        self._build_ui()
        self._new_round()

        self.bind('<Return>', lambda _e: self._submit())
        self.after(100, lambda: self.entry.focus_force())

    # --- UI --------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='DICE MATH', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header, text='Roll. Compute. Beat the clock.',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Bottom controls (packed first so they stay visible)
        self.new_btn = ctk.CTkButton(self, text='New Round',
                                     fg_color='#334155', hover_color='#475569',
                                     command=self._new_round)
        self.new_btn.pack(side='bottom', pady=(4, 12))

        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(0, 4))

        input_frame = ctk.CTkFrame(self, fg_color='transparent')
        input_frame.pack(side='bottom', pady=(8, 4), padx=20, fill='x')
        self.entry = ctk.CTkEntry(input_frame, font=('Segoe UI', 18),
                                  height=44, justify='center',
                                  placeholder_text='answer')
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.entry.bind('<Return>', lambda _e: self._submit())
        self.submit_btn = ctk.CTkButton(input_frame, text='Submit',
                                        width=92, height=44,
                                        font=('Segoe UI', 14, 'bold'),
                                        command=self._submit)
        self.submit_btn.pack(side='left')

        # Settings row: mode + difficulty slider
        settings = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        settings.pack(side='top', pady=(10, 6), padx=20, fill='x')

        mode_row = ctk.CTkFrame(settings, fg_color='transparent')
        mode_row.pack(side='top', pady=(8, 4), padx=12, fill='x')
        ctk.CTkLabel(mode_row, text='Mode:', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 8))
        self.mode_var = ctk.StringVar(value=self.mode)
        self.mode_menu = ctk.CTkOptionMenu(
            mode_row, values=list(MODES), variable=self.mode_var,
            command=self._on_mode_change,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b', width=120)
        self.mode_menu.pack(side='left')

        diff_row = ctk.CTkFrame(settings, fg_color='transparent')
        diff_row.pack(side='top', pady=(4, 10), padx=12, fill='x')
        self.diff_label = ctk.CTkLabel(
            diff_row, text=f'Difficulty: {self.num_dice} dice',
            font=LABEL_FONT, text_color=MUTED)
        self.diff_label.pack(side='left', padx=(0, 8))
        self.diff_slider = ctk.CTkSlider(
            diff_row, from_=2, to=6, number_of_steps=4,
            command=self._on_difficulty_change)
        self.diff_slider.set(self.num_dice)
        self.diff_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Score / streak / timer row
        scoreboard = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        scoreboard.pack(side='top', pady=(4, 8), padx=20, fill='x')
        self.score_label = ctk.CTkLabel(scoreboard, text='Score: 0',
                                        font=SCORE_FONT, text_color='#f8fafc')
        self.score_label.pack(side='left', padx=14, pady=8)
        self.streak_label = ctk.CTkLabel(scoreboard, text='Streak: 0',
                                         font=SCORE_FONT, text_color=ACCENT)
        self.streak_label.pack(side='left', padx=14, pady=8)
        self.timer_label = ctk.CTkLabel(scoreboard, text='Time: 0.0s',
                                        font=SCORE_FONT, text_color=GOOD)
        self.timer_label.pack(side='right', padx=14, pady=8)

        # Dice display
        dice_frame = ctk.CTkFrame(self, fg_color=CARD, corner_radius=10)
        dice_frame.pack(side='top', pady=(4, 8), padx=20, fill='both',
                        expand=True)
        self.dice_label = ctk.CTkLabel(
            dice_frame, text='', font=DICE_FONT, text_color='#f8fafc',
            justify='left')
        self.dice_label.pack(expand=True, padx=10, pady=10)

    # --- Game flow -------------------------------------------------------

    def _on_mode_change(self, value: str) -> None:
        self.mode = value
        self._new_round()

    def _on_difficulty_change(self, value: float) -> None:
        new_n = int(round(value))
        if new_n != self.num_dice:
            self.num_dice = new_n
            self.diff_label.configure(text=f'Difficulty: {self.num_dice} dice')
            self._new_round()
        else:
            self.diff_label.configure(text=f'Difficulty: {self.num_dice} dice')

    def _new_round(self) -> None:
        self._cancel_timer()
        self.values = roll(self.num_dice, self.rng)
        self.target = correct_answer(self.values, self.mode)
        self.dice_label.configure(text=format_dice(self.values))
        self.entry.configure(state='normal')
        self.submit_btn.configure(state='normal')
        self.entry.delete(0, 'end')
        self.entry.focus()

        self.round_num += 1
        prompt = self._prompt_for_mode()
        self._set_status(f'Round {self.round_num}: {prompt}', MUTED)

        self.start_time = time.perf_counter()
        self._tick_timer()

    def _prompt_for_mode(self) -> str:
        return {
            'sum':     'enter the sum',
            'product': 'enter the product',
            'max':     'enter the largest face',
            'pair':    "type 'y' if any two match, else 'n'",
        }[self.mode]

    def _tick_timer(self) -> None:
        if self.start_time is None:
            return
        elapsed = time.perf_counter() - self.start_time
        self.timer_label.configure(text=f'Time: {elapsed:.1f}s')
        self._timer_job = self.after(100, self._tick_timer)

    def _cancel_timer(self) -> None:
        if self._timer_job is not None:
            try:
                self.after_cancel(self._timer_job)
            except Exception:
                pass
            self._timer_job = None

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, text_color=color)

    def _submit(self) -> None:
        if self.start_time is None:
            return
        elapsed = time.perf_counter() - self.start_time
        self._cancel_timer()
        answer = self.entry.get()
        points = score_round(answer, self.target, elapsed)

        if points > 0:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
            self.score += points
            self._set_status(
                f'Correct! +{points} pts in {elapsed:.2f}s', GOOD)
        else:
            self.streak = 0
            self._set_status(
                f'Wrong. Answer was {self.target} ({elapsed:.2f}s)', BAD)

        self.score_label.configure(text=f'Score: {self.score}')
        self.streak_label.configure(text=f'Streak: {self.streak}')
        self.timer_label.configure(text=f'Time: {elapsed:.2f}s')
        self.entry.configure(state='disabled')
        self.submit_btn.configure(state='disabled')
        self.start_time = None
        # Auto-advance after a short pause so the player sees the result.
        self.after(900, self._new_round)

    # --- Cleanup ---------------------------------------------------------

    def destroy(self) -> None:  # type: ignore[override]
        self._cancel_timer()
        if self.score > 0:
            try:
                save_high_score('player', self.score, self.mode)
            except Exception:
                pass
        super().destroy()


if __name__ == '__main__':
    DiceMathApp().mainloop()
