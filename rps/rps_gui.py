"""Rock Paper Scissors — CustomTkinter GUI.

Three modes selectable from a dropdown:
  fair    — uniform random
  markov  — 1st-order Markov predictor (the twist)
  cheat   — always-win opponent (Sweigart #60)

Run:
    uv run python rps/rps_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from rps import EMOJI, Game

TITLE_FONT = ('Segoe UI', 30, 'bold')
LABEL_FONT = ('Segoe UI', 13)
BUTTON_FONT = ('Segoe UI', 22, 'bold')
SCORE_FONT = ('Segoe UI', 22, 'bold')
SCORE_LABEL_FONT = ('Segoe UI', 11)
REVEAL_FONT = ('Segoe UI', 56)
STATUS_FONT = ('Segoe UI', 16, 'bold')

# Slate-900 / blue accent colour palette, mirroring bagels_gui.
BG = '#0f172a'
PANEL = '#1e293b'
SUBTLE = '#94a3b8'
TEXT = '#f8fafc'
WIN_COLOR = '#34d399'
LOSE_COLOR = '#f87171'
TIE_COLOR = '#fbbf24'

MODE_LABELS = {
    'fair':   'fair  (random)',
    'markov': 'markov  (learns you)',
    'cheat':  'cheat  (always wins)',
}
LABEL_TO_MODE = {v: k for k, v in MODE_LABELS.items()}


class RPSApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Rock Paper Scissors')
        self.geometry('520x680')
        self.minsize(460, 620)
        self.configure(fg_color=BG)

        self.game = Game(mode='fair')
        self._reveal_after: str | None = None

        self._build_ui()
        self._refresh_score()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='ROCK · PAPER · SCISSORS',
                     font=TITLE_FONT, text_color=TEXT).pack()
        ctk.CTkLabel(
            header,
            text='Sweigart #59 + #60 — fair, markov-predictor, or cheat',
            font=LABEL_FONT, text_color=SUBTLE,
        ).pack(pady=(2, 0))

        # Mode dropdown.
        mode_row = ctk.CTkFrame(self, fg_color='transparent')
        mode_row.pack(side='top', pady=(10, 4))
        ctk.CTkLabel(mode_row, text='Mode:', font=LABEL_FONT,
                     text_color=SUBTLE).pack(side='left', padx=(0, 8))
        self.mode_var = ctk.StringVar(value=MODE_LABELS['fair'])
        self.mode_menu = ctk.CTkOptionMenu(
            mode_row,
            values=list(MODE_LABELS.values()),
            variable=self.mode_var,
            command=self._on_mode_change,
            fg_color=PANEL, button_color='#334155',
            button_hover_color='#475569', text_color=TEXT,
            width=200,
        )
        self.mode_menu.pack(side='left')

        # Reveal area — large emoji vs emoji.
        reveal = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=14)
        reveal.pack(side='top', pady=(14, 8), padx=24, fill='x')

        cols = ctk.CTkFrame(reveal, fg_color='transparent')
        cols.pack(pady=14)

        you_col = ctk.CTkFrame(cols, fg_color='transparent')
        you_col.pack(side='left', padx=22)
        ctk.CTkLabel(you_col, text='YOU', font=LABEL_FONT,
                     text_color=SUBTLE).pack()
        self.you_label = ctk.CTkLabel(you_col, text='·', font=REVEAL_FONT,
                                      text_color=TEXT)
        self.you_label.pack()

        ctk.CTkLabel(cols, text='vs', font=LABEL_FONT,
                     text_color=SUBTLE).pack(side='left', padx=8)

        cpu_col = ctk.CTkFrame(cols, fg_color='transparent')
        cpu_col.pack(side='left', padx=22)
        ctk.CTkLabel(cpu_col, text='CPU', font=LABEL_FONT,
                     text_color=SUBTLE).pack()
        self.cpu_label = ctk.CTkLabel(cpu_col, text='·', font=REVEAL_FONT,
                                      text_color=TEXT)
        self.cpu_label.pack()

        self.status = ctk.CTkLabel(reveal, text='Pick a move',
                                   font=STATUS_FONT, text_color=SUBTLE)
        self.status.pack(pady=(0, 14))

        # Move buttons.
        moves = ctk.CTkFrame(self, fg_color='transparent')
        moves.pack(side='top', pady=(4, 6))
        for move in ('rock', 'paper', 'scissors'):
            btn = ctk.CTkButton(
                moves,
                text=f'{EMOJI[move]}\n{move}',
                font=BUTTON_FONT,
                width=120, height=110,
                fg_color='#334155', hover_color='#475569',
                text_color=TEXT, corner_radius=14,
                command=lambda m=move: self._play(m),
            )
            btn.pack(side='left', padx=8)

        # Score panel.
        score_panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        score_panel.pack(side='top', pady=(14, 6), padx=24, fill='x')
        cells = ctk.CTkFrame(score_panel, fg_color='transparent')
        cells.pack(pady=10)
        self.win_label = self._score_cell(cells, 'WINS', WIN_COLOR)
        self.lose_label = self._score_cell(cells, 'LOSSES', LOSE_COLOR)
        self.tie_label = self._score_cell(cells, 'TIES', TIE_COLOR)

        # Reset button.
        ctk.CTkButton(self, text='Reset Score', fg_color='#334155',
                      hover_color='#475569', command=self._reset
                      ).pack(side='bottom', pady=(4, 14))

    def _score_cell(self, parent, label: str, color: str) -> ctk.CTkLabel:
        col = ctk.CTkFrame(parent, fg_color='transparent')
        col.pack(side='left', padx=18)
        ctk.CTkLabel(col, text=label, font=SCORE_LABEL_FONT,
                     text_color=SUBTLE).pack()
        value = ctk.CTkLabel(col, text='0', font=SCORE_FONT,
                             text_color=color)
        value.pack()
        return value

    # ------------------------------------------------------------------ logic
    def _on_mode_change(self, label: str) -> None:
        new_mode = LABEL_TO_MODE[label]
        # Re-create the game in the new mode (carry no learned state).
        self.game = Game(mode=new_mode)
        self._refresh_score()
        self.you_label.configure(text='·', text_color=TEXT)
        self.cpu_label.configure(text='·', text_color=TEXT)
        self.status.configure(text=f'Mode: {new_mode}', text_color=SUBTLE)

    def _play(self, move: str) -> None:
        # Cancel any pending reveal animation.
        if self._reveal_after is not None:
            try:
                self.after_cancel(self._reveal_after)
            except Exception:
                pass
            self._reveal_after = None

        # Show the player's move immediately, computer reveal after a beat.
        self.you_label.configure(text=EMOJI[move], text_color=TEXT)
        self.cpu_label.configure(text='?', text_color=SUBTLE)
        self.status.configure(text='...', text_color=SUBTLE)

        # 320 ms suspense so the player feels the reveal.
        self._reveal_after = self.after(320, lambda: self._resolve(move))

    def _resolve(self, move: str) -> None:
        self._reveal_after = None
        result = self.game.play(move)
        cm = result['computer_move']
        self.cpu_label.configure(text=EMOJI[cm], text_color=TEXT)

        if result['result'] == 'win':
            self.status.configure(text='YOU WIN', text_color=WIN_COLOR)
        elif result['result'] == 'lose':
            self.status.configure(text='CPU WINS', text_color=LOSE_COLOR)
        else:
            self.status.configure(text='TIE', text_color=TIE_COLOR)
        self._refresh_score()

    def _refresh_score(self) -> None:
        s = self.game.score
        self.win_label.configure(text=str(s['wins']))
        self.lose_label.configure(text=str(s['losses']))
        self.tie_label.configure(text=str(s['ties']))

    def _reset(self) -> None:
        self.game.reset()
        self._refresh_score()
        self.you_label.configure(text='·', text_color=TEXT)
        self.cpu_label.configure(text='·', text_color=TEXT)
        self.status.configure(text='Pick a move', text_color=SUBTLE)


if __name__ == '__main__':
    RPSApp().mainloop()
