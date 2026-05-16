"""Carrot in a Box — CustomTkinter GUI.

Hot-seat 2-player bluffing game with a peek phase, a swap-or-keep
decision, and a reveal animation that lifts the lid on whichever box
holds the carrot.

Run:
    uv run python carrot_box/carrot_box_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from carrot_box import Game, ai_decision


# Colours — same dark-slate palette as bagels_gui.
BG = '#0f172a'
PANEL = '#1f2937'
BORDER = '#334155'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
GREEN = '#16a34a'
ORANGE = '#f97316'
RED = '#f87171'
YELLOW = '#eab308'

TITLE_FONT = ('Segoe UI', 30, 'bold')
SUB_FONT = ('Segoe UI', 13)
LABEL_FONT = ('Segoe UI', 16, 'bold')
BOX_FONT = ('Segoe UI Emoji', 64)
STATUS_FONT = ('Segoe UI', 14)
BTN_FONT = ('Segoe UI', 14, 'bold')


class CarrotBoxApp(ctk.CTk):
    """States: 'peek1' -> 'peek2' (hot-seat) -> 'decide' -> 'revealed'.
    In vs-AI mode: 'peek2' (you) -> 'ai_acts' -> 'revealed'."""

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Carrot in a Box')
        self.geometry('640x680')
        self.minsize(560, 600)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.score = {1: 0, 2: 0}
        self.vs_ai = False
        self.game: Game | None = None
        self.state: str = 'menu'

        self._build_ui()
        self._show_menu()

    # ---- layout ------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='CARROT IN A BOX', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header, text='2-player bluffing — one box, one carrot',
                     font=SUB_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Score row.
        self.score_label = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                        text_color=MUTED)
        self.score_label.pack(side='top', pady=(4, 0))

        # Boxes row.
        boxes_frame = ctk.CTkFrame(self, fg_color='transparent')
        boxes_frame.pack(side='top', pady=20, padx=20)

        self.box_widgets: dict[int, dict] = {}
        for player in (1, 2):
            col = ctk.CTkFrame(boxes_frame, fg_color='transparent')
            col.pack(side='left', padx=24)
            label = ctk.CTkLabel(col, text=f'Player {player}',
                                 font=LABEL_FONT, text_color=TEXT)
            label.pack(pady=(0, 8))
            box = ctk.CTkLabel(col, text='[ ? ]', width=180, height=160,
                               fg_color=PANEL, text_color=TEXT,
                               corner_radius=14, font=BOX_FONT)
            box.pack()
            content = ctk.CTkLabel(col, text='', font=SUB_FONT,
                                   text_color=MUTED)
            content.pack(pady=(8, 0))
            self.box_widgets[player] = {
                'label': label, 'box': box, 'content': content,
            }

        # Status.
        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color=TEXT, wraplength=560,
                                   justify='center')
        self.status.pack(side='top', pady=(8, 8))

        # Buttons row.
        self.button_row = ctk.CTkFrame(self, fg_color='transparent')
        self.button_row.pack(side='top', pady=10)

        self.btn_a = ctk.CTkButton(self.button_row, text='', width=140,
                                   height=44, font=BTN_FONT,
                                   command=self._on_a)
        self.btn_b = ctk.CTkButton(self.button_row, text='', width=140,
                                   height=44, font=BTN_FONT,
                                   command=self._on_b)
        self.btn_c = ctk.CTkButton(self.button_row, text='', width=140,
                                   height=44, font=BTN_FONT,
                                   command=self._on_c)

        # Footer — mode toggle + new round.
        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.pack(side='bottom', pady=(4, 12))
        self.mode_btn = ctk.CTkButton(footer, text='Mode: 2 humans',
                                      width=160, height=36,
                                      fg_color=BORDER, hover_color='#475569',
                                      command=self._toggle_mode)
        self.mode_btn.pack(side='left', padx=6)
        self.new_btn = ctk.CTkButton(footer, text='New Round', width=140,
                                     height=36, fg_color=BORDER,
                                     hover_color='#475569',
                                     command=self._new_round)
        self.new_btn.pack(side='left', padx=6)

    # ---- helpers -----------------------------------------------------

    def _set_status(self, text: str, color: str = TEXT) -> None:
        self.status.configure(text=text, text_color=color)

    def _set_buttons(self, *specs: tuple[str, str, str] | None) -> None:
        """Configure up to 3 action buttons. Each spec is
        (text, color, slot) where slot in {'a', 'b', 'c'} — or None to hide."""
        for btn in (self.btn_a, self.btn_b, self.btn_c):
            btn.pack_forget()
        for spec in specs:
            if spec is None:
                continue
            text, color, slot = spec
            btn = {'a': self.btn_a, 'b': self.btn_b, 'c': self.btn_c}[slot]
            btn.configure(text=text, fg_color=color, hover_color=color,
                          state='normal')
            btn.pack(side='left', padx=8)

    def _refresh_score(self) -> None:
        if self.vs_ai:
            self.score_label.configure(
                text=f'AI: {self.score[1]}   |   You: {self.score[2]}')
        else:
            self.score_label.configure(
                text=f'Player 1: {self.score[1]}   |   '
                     f'Player 2: {self.score[2]}')

    def _set_box(self, player: int, *, text: str, fg_color: str,
                 caption: str = '') -> None:
        w = self.box_widgets[player]
        w['box'].configure(text=text, fg_color=fg_color)
        w['content'].configure(text=caption)

    def _hide_box_contents(self) -> None:
        for p in (1, 2):
            self._set_box(p, text='[ ? ]', fg_color=PANEL, caption='')

    # ---- state transitions ------------------------------------------

    def _show_menu(self) -> None:
        self.state = 'menu'
        self._hide_box_contents()
        self._refresh_score()
        self._set_status(
            'Press Start to begin. Toggle mode at the bottom for vs-AI.',
            MUTED)
        self._set_buttons(('Start', GREEN, 'a'))

    def _toggle_mode(self) -> None:
        if self.state not in ('menu', 'revealed'):
            return
        self.vs_ai = not self.vs_ai
        self.mode_btn.configure(
            text='Mode: vs AI' if self.vs_ai else 'Mode: 2 humans')
        self.score = {1: 0, 2: 0}
        self._show_menu()

    def _new_round(self) -> None:
        # Allowed from any state — abandons the current round.
        self._show_menu()

    def _start_round(self) -> None:
        self.game = Game(rng=self.rng)
        self._hide_box_contents()
        if self.vs_ai:
            # Skip player-1 peek (AI peeks invisibly).
            self.game.peek(1)
            self.state = 'peek2'
            self._set_status(
                'Your turn (player 2). Press Peek to look in your box.',
                ACCENT)
            self._set_buttons(('Peek my box', ACCENT, 'a'))
        else:
            self.state = 'peek1'
            self._set_status(
                'Player 1, press Peek to privately look in your box. '
                'Player 2 — look away!', ACCENT)
            self._set_buttons(('Peek (P1)', ACCENT, 'a'))

    def _do_peek(self, player: int) -> None:
        assert self.game is not None
        has = self.game.peek(player)
        text = '🥕' if has else '·'
        color = ORANGE if has else PANEL
        caption = 'CARROT!' if has else 'empty'
        self._set_box(player, text=text, fg_color=color, caption=caption)
        self._set_buttons(('Hide & continue', BORDER, 'a'))
        self.state = f'after_peek{player}'

    def _hide_after_peek(self, player: int) -> None:
        # Hide the peeked box again.
        self._set_box(player, text='[ ? ]', fg_color=PANEL, caption='')

        if self.vs_ai:
            # Player 2 peeked. AI now decides.
            self._ai_acts()
        elif player == 1:
            self.state = 'peek2'
            self._set_status(
                'Player 2, press Peek to privately look in your box. '
                'Player 1 — look away!', ACCENT)
            self._set_buttons(('Peek (P2)', ACCENT, 'a'))
        else:
            # Both peeked, decision time.
            self.state = 'decide'
            self._set_status(
                'Talk it out. Player 1, swap or keep?', YELLOW)
            self._set_buttons(
                ('Swap (P1)', ORANGE, 'a'),
                ('Keep (P1)', GREEN, 'b'),
            )

    def _ai_acts(self) -> None:
        assert self.game is not None
        ai_has = self.game.has_carrot(1)
        bluffs = [
            '"I definitely have the carrot. You should keep your box."',
            '"Ugh, mine is empty. Want to swap?"',
            '"Hmm, I am not sure what to do."',
            '"Trust me. You do not want to swap."',
        ]
        bluff = self.rng.choice(bluffs)
        swap = ai_decision(ai_has, self.rng)
        self.game.decide(1, swap)
        self._set_status(f'AI says: {bluff}\n'
                         f'AI {"SWAPPED" if swap else "KEPT"} the boxes.',
                         YELLOW)
        self._set_buttons(('Reveal!', RED, 'a'))
        self.state = 'reveal_pending'

    def _do_decide(self, swap: bool) -> None:
        assert self.game is not None
        self.game.decide(1, swap)
        verb = 'SWAPPED' if swap else 'KEPT'
        self._set_status(f'Player 1 {verb} the boxes. Reveal!', YELLOW)
        self._set_buttons(('Reveal!', RED, 'a'))
        self.state = 'reveal_pending'

    def _reveal(self) -> None:
        assert self.game is not None
        winner = self.game.reveal()
        # Show both boxes.
        for p in (1, 2):
            has = self.game.has_carrot(p)
            self._set_box(p, text='🥕' if has else '·',
                          fg_color=ORANGE if has else PANEL,
                          caption='CARROT!' if has else 'empty')
        self.score[winner] += 1
        if self.vs_ai:
            msg = ('You win the carrot!' if winner == 2
                   else 'AI wins the carrot.')
            color = GREEN if winner == 2 else RED
        else:
            msg = f'Player {winner} wins the carrot!'
            color = GREEN
        self._set_status(msg, color)
        self._refresh_score()
        self._set_buttons(('New Round', GREEN, 'a'))
        self.state = 'revealed'

    # ---- button slot dispatch ---------------------------------------

    def _on_a(self) -> None:
        s = self.state
        if s == 'menu':
            self._start_round()
        elif s == 'peek1':
            self._do_peek(1)
        elif s == 'peek2':
            self._do_peek(2)
        elif s == 'after_peek1':
            self._hide_after_peek(1)
        elif s == 'after_peek2':
            self._hide_after_peek(2)
        elif s == 'decide':
            self._do_decide(swap=True)
        elif s == 'reveal_pending':
            self._reveal()
        elif s == 'revealed':
            self._show_menu()

    def _on_b(self) -> None:
        if self.state == 'decide':
            self._do_decide(swap=False)

    def _on_c(self) -> None:
        # Reserved for future use.
        pass


if __name__ == '__main__':
    CarrotBoxApp().mainloop()
