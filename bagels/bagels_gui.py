"""Bagels — CustomTkinter GUI.

A Wordle-style desktop UI for the Bagels deductive logic game.
Tiles light up green (Fermi), yellow (Pico), or gray (Bagels) for each guess.

Run:
    uv run python bagels/bagels_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from bagels import MAX_GUESSES, NUM_DIGITS, getCluesPerPosition, getSecretNum

CLUE_COLORS = {
    'Fermi':  ('#16a34a', '#ffffff'),  # green:  digit + position correct
    'Pico':   ('#eab308', '#1f2937'),  # yellow: digit correct, wrong place
    'Bagels': ('#374151', '#9ca3af'),  # gray:   digit absent
    'empty':  ('#1f2937', '#6b7280'),
}

TILE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 32, 'bold')
STATUS_FONT = ('Segoe UI', 14)


class BagelsApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Bagels')
        self.geometry('420x780')
        self.minsize(420, 600)
        self.configure(fg_color='#0f172a')

        self.secret: str = ''
        self.current_row: int = 0
        self.game_over: bool = False
        self.tiles: list[list[ctk.CTkLabel]] = []

        self._build_ui()
        self._new_game()
        # App-level Enter fallback so submit fires even if entry loses focus.
        self.bind('<Return>', lambda _e: self._submit_guess())
        # Defer focus until the window is actually mapped on screen.
        self.after(100, self._focus_entry)

    def _focus_entry(self) -> None:
        try:
            self.entry.focus_force()
        except Exception:
            pass

    def _build_ui(self) -> None:
        # Header — packed top-down.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='BAGELS', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header,
                     text=f'Guess the {NUM_DIGITS}-digit number — no repeats',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Bottom controls — packed bottom-up so they're always visible
        # regardless of board height.
        self.new_btn = ctk.CTkButton(self, text='New Game',
                                     fg_color='#334155', hover_color='#475569',
                                     command=self._new_game)
        self.new_btn.pack(side='bottom', pady=(4, 12))

        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='bottom', pady=(4, 0))

        input_frame = ctk.CTkFrame(self, fg_color='transparent')
        input_frame.pack(side='bottom', pady=(8, 4), padx=20, fill='x')
        self.entry = ctk.CTkEntry(input_frame, font=('Segoe UI', 18),
                                  height=42, justify='center',
                                  placeholder_text=f'{NUM_DIGITS} digits')
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.entry.bind('<Return>', lambda _e: self._submit_guess())

        self.guess_btn = ctk.CTkButton(input_frame, text='Guess',
                                       width=80, height=42,
                                       font=('Segoe UI', 14, 'bold'),
                                       command=self._submit_guess)
        self.guess_btn.pack(side='left')

        # Middle — legend + board (fills whatever space is left).
        legend = ctk.CTkFrame(self, fg_color='transparent')
        legend.pack(side='top', pady=(6, 6))
        for clue, label in (('Fermi', 'right + place'),
                            ('Pico', 'right, wrong place'),
                            ('Bagels', 'no match')):
            bg, fg = CLUE_COLORS[clue]
            chip = ctk.CTkLabel(legend, text=f'  {clue}: {label}  ',
                                fg_color=bg, text_color=fg,
                                corner_radius=12,
                                font=('Segoe UI', 11, 'bold'))
            chip.pack(side='left', padx=4)

        board = ctk.CTkFrame(self, fg_color='transparent')
        board.pack(side='top', pady=8)
        for r in range(MAX_GUESSES):
            row_tiles: list[ctk.CTkLabel] = []
            row_frame = ctk.CTkFrame(board, fg_color='transparent')
            row_frame.pack(pady=2)
            for c in range(NUM_DIGITS):
                bg, fg = CLUE_COLORS['empty']
                tile = ctk.CTkLabel(row_frame, text='', width=48, height=48,
                                    fg_color=bg, text_color=fg,
                                    corner_radius=8, font=TILE_FONT)
                tile.pack(side='left', padx=4)
                row_tiles.append(tile)
            self.tiles.append(row_tiles)

    def _new_game(self) -> None:
        self.secret = getSecretNum()
        self.current_row = 0
        self.game_over = False
        for row in self.tiles:
            bg, fg = CLUE_COLORS['empty']
            for tile in row:
                tile.configure(text='', fg_color=bg, text_color=fg)
        self.entry.configure(state='normal')
        self.guess_btn.configure(state='normal')
        self.entry.delete(0, 'end')
        self._set_status(f'Guess 1 of {MAX_GUESSES}', '#cbd5e1')
        self.entry.focus()

    def _set_status(self, text: str, color: str = '#cbd5e1') -> None:
        self.status.configure(text=text, text_color=color)

    def _submit_guess(self) -> None:
        if self.game_over:
            return

        guess = self.entry.get().strip()
        if len(guess) != NUM_DIGITS or not guess.isdecimal():
            self._set_status(f'Enter exactly {NUM_DIGITS} digits.', '#f87171')
            return
        if len(set(guess)) != NUM_DIGITS:
            self._set_status('Digits must not repeat.', '#f87171')
            return

        clues = getCluesPerPosition(guess, self.secret)
        for col, (digit, clue) in enumerate(zip(guess, clues)):
            bg, fg = CLUE_COLORS[clue]
            self.tiles[self.current_row][col].configure(
                text=digit, fg_color=bg, text_color=fg)

        self.current_row += 1
        self.entry.delete(0, 'end')

        if guess == self.secret:
            self._end_game(f'You got it in {self.current_row}!', '#34d399')
        elif self.current_row >= MAX_GUESSES:
            self._end_game(f'Out of guesses — answer was {self.secret}',
                           '#f87171')
        else:
            self._set_status(
                f'Guess {self.current_row + 1} of {MAX_GUESSES}', '#cbd5e1')

    def _end_game(self, message: str, color: str) -> None:
        self.game_over = True
        self._set_status(message, color)
        self.entry.configure(state='disabled')
        self.guess_btn.configure(state='disabled')


if __name__ == '__main__':
    BagelsApp().mainloop()
