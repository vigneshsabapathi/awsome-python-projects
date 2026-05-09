"""Guess the Number — CustomTkinter GUI.

A dark-themed desktop UI for the classic higher/lower number game.

Features:
- Range entry (low/high) + max guesses + reseed button
- Big centered guess entry with Submit
- Scrollable history with up/down arrows per past guess
- "Hint" button reveals the binary-search optimal next guess
- Lives counter + bits-of-uncertainty display (information theory twist)

Run:
    uv run python guess_number/guess_number_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from guess_number import (
    DEFAULT_HIGH,
    DEFAULT_LOW,
    DEFAULT_MAX_GUESSES,
    Game,
    bits_remaining,
)

# Palette — same family as bagels_gui for visual consistency.
BG = '#0f172a'
PANEL = '#1e293b'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
ACCENT = '#38bdf8'
GREEN = '#34d399'
YELLOW = '#eab308'
RED = '#f87171'
GRAY = '#334155'
HOVER = '#475569'

TITLE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 12)
SMALL_FONT = ('Segoe UI', 11)
ENTRY_FONT = ('Segoe UI', 22, 'bold')
BUTTON_FONT = ('Segoe UI', 13, 'bold')
HISTORY_FONT = ('Consolas', 13)


class GuessNumberApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Guess the Number')
        self.geometry('480x720')
        self.minsize(440, 600)
        self.configure(fg_color=BG)

        self.game: Game | None = None
        self._build_ui()
        self._new_game()
        self.bind('<Return>', lambda _e: self._submit_guess())
        self.after(100, lambda: self.entry.focus_force())

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Header.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='GUESS THE NUMBER', font=TITLE_FONT,
                     text_color=TEXT).pack()
        self.subtitle = ctk.CTkLabel(
            header, text='', font=LABEL_FONT, text_color=MUTED)
        self.subtitle.pack(pady=(2, 0))

        # Range / settings strip.
        settings = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        settings.pack(side='top', pady=(8, 4), padx=20, fill='x')

        row = ctk.CTkFrame(settings, fg_color='transparent')
        row.pack(pady=8, padx=10, fill='x')

        ctk.CTkLabel(row, text='Low', font=SMALL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 4))
        self.low_entry = ctk.CTkEntry(row, width=60, justify='center',
                                       font=SMALL_FONT)
        self.low_entry.insert(0, str(DEFAULT_LOW))
        self.low_entry.pack(side='left', padx=(0, 10))

        ctk.CTkLabel(row, text='High', font=SMALL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 4))
        self.high_entry = ctk.CTkEntry(row, width=60, justify='center',
                                        font=SMALL_FONT)
        self.high_entry.insert(0, str(DEFAULT_HIGH))
        self.high_entry.pack(side='left', padx=(0, 10))

        ctk.CTkLabel(row, text='Lives', font=SMALL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 4))
        self.lives_entry = ctk.CTkEntry(row, width=50, justify='center',
                                         font=SMALL_FONT)
        self.lives_entry.insert(0, str(DEFAULT_MAX_GUESSES))
        self.lives_entry.pack(side='left', padx=(0, 10))

        ctk.CTkButton(row, text='New Game', font=BUTTON_FONT,
                      width=90, height=28,
                      fg_color=GRAY, hover_color=HOVER,
                      command=self._new_game).pack(side='right')

        # Lives + bits panel.
        info = ctk.CTkFrame(self, fg_color='transparent')
        info.pack(side='top', pady=(6, 4), padx=20, fill='x')
        self.lives_label = ctk.CTkLabel(
            info, text='', font=('Segoe UI', 14, 'bold'), text_color=TEXT)
        self.lives_label.pack(side='left')
        self.bits_label = ctk.CTkLabel(
            info, text='', font=SMALL_FONT, text_color=MUTED)
        self.bits_label.pack(side='right')

        # History panel (scrollable, fills remaining space).
        history_wrap = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        history_wrap.pack(side='top', pady=(6, 6), padx=20,
                          fill='both', expand=True)
        ctk.CTkLabel(history_wrap, text='History', font=SMALL_FONT,
                     text_color=MUTED).pack(anchor='w', padx=10, pady=(8, 0))
        self.history = ctk.CTkScrollableFrame(
            history_wrap, fg_color='transparent', corner_radius=0)
        self.history.pack(fill='both', expand=True, padx=6, pady=(2, 8))

        # Guess input.
        input_frame = ctk.CTkFrame(self, fg_color='transparent')
        input_frame.pack(side='top', pady=(4, 4), padx=20, fill='x')
        self.entry = ctk.CTkEntry(input_frame, font=ENTRY_FONT,
                                   height=48, justify='center',
                                   placeholder_text='your guess')
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.entry.bind('<Return>', lambda _e: self._submit_guess())
        self.guess_btn = ctk.CTkButton(
            input_frame, text='Submit', width=88, height=48,
            font=BUTTON_FONT, command=self._submit_guess)
        self.guess_btn.pack(side='left')

        # Hint button + status.
        action = ctk.CTkFrame(self, fg_color='transparent')
        action.pack(side='top', pady=(4, 12), padx=20, fill='x')
        self.hint_btn = ctk.CTkButton(
            action, text='Hint (binary search)', font=BUTTON_FONT,
            fg_color=GRAY, hover_color=HOVER,
            command=self._show_hint)
        self.hint_btn.pack(side='left')
        self.status = ctk.CTkLabel(
            action, text='', font=LABEL_FONT, text_color=MUTED)
        self.status.pack(side='right')

    # ------------------------------------------------------------------
    # Game wiring
    # ------------------------------------------------------------------

    def _parse_settings(self) -> tuple[int, int, int] | None:
        try:
            low = int(self.low_entry.get())
            high = int(self.high_entry.get())
            lives = int(self.lives_entry.get())
        except ValueError:
            self._set_status('Settings must be integers.', RED)
            return None
        if low >= high:
            self._set_status('Low must be < high.', RED)
            return None
        if lives < 1:
            self._set_status('Lives must be >= 1.', RED)
            return None
        return low, high, lives

    def _new_game(self) -> None:
        parsed = self._parse_settings()
        if parsed is None:
            return
        low, high, lives = parsed

        self.game = Game(low=low, high=high, max_guesses=lives)
        self.subtitle.configure(
            text=f'Pick a number between {low} and {high}')

        for child in self.history.winfo_children():
            child.destroy()

        self.entry.configure(state='normal')
        self.guess_btn.configure(state='normal')
        self.hint_btn.configure(state='normal')
        self.entry.delete(0, 'end')
        self._refresh_meter()
        self._set_status('Game on.', MUTED)
        self.entry.focus()

    def _refresh_meter(self) -> None:
        assert self.game is not None
        self.lives_label.configure(
            text=f'Lives: {self.game.guesses_left}/{self.game.max_guesses}')
        bits = bits_remaining(
            self.game.candidate_low, self.game.candidate_high)
        span = self.game.candidate_high - self.game.candidate_low + 1
        self.bits_label.configure(
            text=f'{span} candidates left ~ {bits:.2f} bits')

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, text_color=color)

    def _add_history_row(self, n: int, arrow: str, color: str) -> None:
        # arrow: 'up' (too_low — secret is higher), 'down' (too_high), '*' win.
        arrow_char = {'up': '↑', 'down': '↓', '*': '★'}[arrow]
        text = {
            'up': f'{n:>5}   {arrow_char}  higher',
            'down': f'{n:>5}   {arrow_char}  lower',
            '*': f'{n:>5}   {arrow_char}  correct',
        }[arrow]
        row = ctk.CTkLabel(self.history, text=text, font=HISTORY_FONT,
                            text_color=color, anchor='w')
        row.pack(fill='x', padx=8, pady=1)

    def _submit_guess(self) -> None:
        if self.game is None or self.game.over:
            return
        raw = self.entry.get().strip()
        try:
            n = int(raw)
        except ValueError:
            self._set_status('Enter an integer.', RED)
            return

        verdict = self.game.guess(n)
        result = verdict['result']
        self.entry.delete(0, 'end')

        if result == 'invalid':
            self._set_status(
                f'Out of [{self.game.low}, {self.game.high}].', RED)
            return

        if result == 'too_low':
            self._add_history_row(n, 'up', YELLOW)
            self._set_status('Too low — go higher.', ACCENT)
        elif result == 'too_high':
            self._add_history_row(n, 'down', YELLOW)
            self._set_status('Too high — go lower.', ACCENT)
        elif result == 'win':
            self._add_history_row(n, '*', GREEN)
            self._set_status(
                f'You got it in {len(self.game.history)}!', GREEN)
            self._lock_inputs()
        elif result == 'lose':
            arrow = 'up' if n < verdict['secret'] else 'down'
            self._add_history_row(n, arrow, RED)
            self._set_status(
                f'Out of lives — secret was {verdict["secret"]}.', RED)
            self._lock_inputs()

        self._refresh_meter()

    def _show_hint(self) -> None:
        if self.game is None or self.game.over:
            return
        hint = self.game.hint()
        bits = self.game.bits_left()
        self._set_status(
            f'Try {hint} (splits {bits:.2f} bits).', ACCENT)

    def _lock_inputs(self) -> None:
        self.entry.configure(state='disabled')
        self.guess_btn.configure(state='disabled')
        self.hint_btn.configure(state='disabled')


if __name__ == '__main__':
    GuessNumberApp().mainloop()
