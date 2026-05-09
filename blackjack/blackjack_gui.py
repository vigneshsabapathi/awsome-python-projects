"""Blackjack — CustomTkinter GUI.

A modern dark-themed Blackjack table. Cards are rendered as visual rectangles
showing rank and suit (red for hearts/diamonds, white for spades/clubs).
The dealer's hole card stays face-down until the player stands or busts.

Run:
    uv run python blackjack/blackjack_gui.py

Buttons:
    Hit       — draw another card
    Stand     — end your turn, dealer plays
    Double    — double your bet, draw exactly one card, then stand
    Hint      — show the basic-strategy recommendation
    New Hand  — start the next hand (auto-enabled when current hand ends)
"""
from __future__ import annotations

import customtkinter as ctk

from blackjack import (
    BLACKJACK_PAYOUT,
    DEFAULT_BET,
    STARTING_BANKROLL,
    Card,
    basic_strategy_hint,
    deal_card,
    dealer_should_hit,
    hand_value,
    is_blackjack,
    is_bust,
    is_soft,
    make_deck,
)

# --- Theme ------------------------------------------------------------------

BG = '#0f172a'           # slate-900
PANEL = '#1e293b'        # slate-800
MUTED = '#94a3b8'        # slate-400
FG = '#f8fafc'           # slate-50
ACCENT = '#38bdf8'       # sky-400
GREEN = '#34d399'        # emerald-400
RED = '#f87171'          # red-400
YELLOW = '#fbbf24'       # amber-400

CARD_BG = '#f8fafc'
CARD_BACK = '#1e3a8a'    # blue-900 (face-down card)
CARD_RED = '#dc2626'
CARD_BLACK = '#0f172a'

CARD_WIDTH = 70
CARD_HEIGHT = 100

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 13)
BIG_FONT = ('Segoe UI', 18, 'bold')
CARD_RANK_FONT = ('Segoe UI', 18, 'bold')
CARD_SUIT_FONT = ('Segoe UI', 28, 'bold')
STATUS_FONT = ('Segoe UI', 14, 'bold')


def _suit_color(suit: str) -> str:
    return CARD_RED if suit in ('♥', '♦') else CARD_BLACK


class CardWidget(ctk.CTkFrame):
    """One playing-card rectangle. Can be flipped face-down via show_back()."""

    def __init__(self, master, card: Card | None = None, face_up: bool = True):
        super().__init__(master, width=CARD_WIDTH, height=CARD_HEIGHT,
                         corner_radius=8, fg_color=CARD_BG,
                         border_width=2, border_color='#334155')
        self.pack_propagate(False)
        self._rank_label = ctk.CTkLabel(self, text='', font=CARD_RANK_FONT,
                                        text_color=CARD_BLACK,
                                        fg_color='transparent')
        self._suit_label = ctk.CTkLabel(self, text='', font=CARD_SUIT_FONT,
                                        text_color=CARD_BLACK,
                                        fg_color='transparent')
        self._rank_label.pack(pady=(8, 0))
        self._suit_label.pack(pady=(0, 6))
        if card and face_up:
            self.show_face(card)
        else:
            self.show_back()

    def show_face(self, card: Card) -> None:
        color = _suit_color(card.suit)
        self.configure(fg_color=CARD_BG, border_color='#334155')
        self._rank_label.configure(text=card.rank, text_color=color)
        self._suit_label.configure(text=card.suit, text_color=color)

    def show_back(self) -> None:
        self.configure(fg_color=CARD_BACK, border_color='#1e40af')
        self._rank_label.configure(text='?', text_color='#bfdbfe')
        self._suit_label.configure(text='♠', text_color='#bfdbfe')


class BlackjackApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Blackjack')
        # Generous default size; controls are pinned to the bottom so they
        # remain visible even at 125% Windows DPI scaling.
        self.geometry('820x780')
        self.minsize(720, 700)
        self.configure(fg_color=BG)

        self.bankroll: int = STARTING_BANKROLL
        self.bet: int = DEFAULT_BET
        self.deck: list[Card] = make_deck()
        self.player: list[Card] = []
        self.dealer: list[Card] = []
        self.hand_in_progress: bool = False
        self.doubled: bool = False
        self.hands_played: int = 0
        self.wins: int = 0
        self.losses: int = 0
        self.pushes: int = 0

        self._build_ui()
        self._new_hand()

    # ---- UI construction ---------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='BLACKJACK', font=TITLE_FONT,
                     text_color=FG).pack()
        ctk.CTkLabel(
            header,
            text='Beat the dealer to 21 — Aces are 1 or 11, dealer stands on 17',
            font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Bottom controls (pinned bottom-up so they're always visible).
        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color=FG)
        self.status.pack(side='bottom', pady=(4, 12))

        button_row = ctk.CTkFrame(self, fg_color='transparent')
        button_row.pack(side='bottom', pady=(4, 4), padx=20)

        self.hit_btn = ctk.CTkButton(
            button_row, text='Hit', width=110, height=40,
            font=('Segoe UI', 14, 'bold'),
            fg_color='#0284c7', hover_color='#0369a1',
            command=self._action_hit)
        self.hit_btn.pack(side='left', padx=4)

        self.stand_btn = ctk.CTkButton(
            button_row, text='Stand', width=110, height=40,
            font=('Segoe UI', 14, 'bold'),
            fg_color='#475569', hover_color='#334155',
            command=self._action_stand)
        self.stand_btn.pack(side='left', padx=4)

        self.double_btn = ctk.CTkButton(
            button_row, text='Double', width=110, height=40,
            font=('Segoe UI', 14, 'bold'),
            fg_color='#a855f7', hover_color='#7e22ce',
            command=self._action_double)
        self.double_btn.pack(side='left', padx=4)

        self.hint_btn = ctk.CTkButton(
            button_row, text='Hint', width=90, height=40,
            font=('Segoe UI', 13),
            fg_color='#334155', hover_color='#475569',
            command=self._show_hint)
        self.hint_btn.pack(side='left', padx=4)

        self.new_btn = ctk.CTkButton(
            button_row, text='New Hand', width=130, height=40,
            font=('Segoe UI', 14, 'bold'),
            fg_color='#16a34a', hover_color='#15803d',
            command=self._new_hand)
        self.new_btn.pack(side='left', padx=4)

        # Bankroll panel (also pinned to bottom)
        money_panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        money_panel.pack(side='bottom', padx=20, pady=(4, 4), fill='x')
        money_inner = ctk.CTkFrame(money_panel, fg_color='transparent')
        money_inner.pack(padx=12, pady=10, fill='x')

        self.bankroll_label = ctk.CTkLabel(
            money_inner, text='', font=BIG_FONT, text_color=GREEN)
        self.bankroll_label.pack(side='left')

        self.record_label = ctk.CTkLabel(
            money_inner, text='', font=LABEL_FONT, text_color=MUTED)
        self.record_label.pack(side='right')

        # Table area — dealer above, player below. Fills the middle.
        table = ctk.CTkFrame(self, fg_color=BG)
        table.pack(side='top', fill='both', expand=True,
                   padx=20, pady=(8, 4))

        self.dealer_total_label = ctk.CTkLabel(
            table, text='Dealer', font=BIG_FONT, text_color=FG)
        self.dealer_total_label.pack(pady=(8, 6))
        self.dealer_frame = ctk.CTkFrame(table, fg_color='transparent')
        self.dealer_frame.pack(pady=(0, 12))

        # Felt-style separator
        sep = ctk.CTkFrame(table, fg_color='#1e3a8a', height=2)
        sep.pack(fill='x', padx=40, pady=8)

        self.player_total_label = ctk.CTkLabel(
            table, text='You', font=BIG_FONT, text_color=FG)
        self.player_total_label.pack(pady=(12, 6))
        self.player_frame = ctk.CTkFrame(table, fg_color='transparent')
        self.player_frame.pack(pady=(0, 8))

        self._dealer_widgets: list[CardWidget] = []
        self._player_widgets: list[CardWidget] = []

    # ---- Rendering ---------------------------------------------------------

    def _clear_card_row(self, frame: ctk.CTkFrame,
                        widgets: list[CardWidget]) -> None:
        for w in widgets:
            w.destroy()
        widgets.clear()

    def _render_player(self) -> None:
        self._clear_card_row(self.player_frame, self._player_widgets)
        for card in self.player:
            w = CardWidget(self.player_frame, card=card, face_up=True)
            w.pack(side='left', padx=4)
            self._player_widgets.append(w)
        total = hand_value(self.player)
        soft = ' (soft)' if is_soft(self.player) and total <= 21 else ''
        self.player_total_label.configure(text=f'You — {total}{soft}')

    def _render_dealer(self, hide_hole: bool) -> None:
        self._clear_card_row(self.dealer_frame, self._dealer_widgets)
        for i, card in enumerate(self.dealer):
            face_up = not (hide_hole and i == 0)
            w = CardWidget(self.dealer_frame, card=card, face_up=face_up)
            w.pack(side='left', padx=4)
            self._dealer_widgets.append(w)
        if hide_hole and self.dealer:
            up = self.dealer[1]
            self.dealer_total_label.configure(
                text=f'Dealer — showing {up.rank}{up.suit}')
        else:
            total = hand_value(self.dealer)
            self.dealer_total_label.configure(text=f'Dealer — {total}')

    def _render_money(self) -> None:
        self.bankroll_label.configure(
            text=f'Bankroll: ${self.bankroll}    Bet: ${self.bet}')
        self.record_label.configure(
            text=f'Hands: {self.hands_played}   '
                 f'W {self.wins}  L {self.losses}  P {self.pushes}')

    # ---- Game flow ---------------------------------------------------------

    def _set_status(self, text: str, color: str = FG) -> None:
        self.status.configure(text=text, text_color=color)

    def _set_action_buttons(self, *, can_play: bool,
                            can_double: bool = False) -> None:
        state = 'normal' if can_play else 'disabled'
        self.hit_btn.configure(state=state)
        self.stand_btn.configure(state=state)
        self.hint_btn.configure(state=state)
        self.double_btn.configure(
            state='normal' if (can_play and can_double) else 'disabled')
        self.new_btn.configure(state='disabled' if can_play else 'normal')

    def _new_hand(self) -> None:
        if self.bankroll < self.bet:
            self._set_status(
                f'Out of chips at ${self.bankroll}. Refresh to play again.',
                RED)
            self._set_action_buttons(can_play=False)
            self.new_btn.configure(state='disabled')
            return

        if len(self.deck) < 15:
            self.deck = make_deck()

        self.player = [deal_card(self.deck), deal_card(self.deck)]
        self.dealer = [deal_card(self.deck), deal_card(self.deck)]
        self.doubled = False
        self.hand_in_progress = True

        self._render_player()
        self._render_dealer(hide_hole=True)
        self._render_money()
        self._set_status('Your move.', FG)

        # Natural-blackjack short-circuits.
        p_bj = is_blackjack(self.player)
        d_bj = is_blackjack(self.dealer)
        if p_bj or d_bj:
            self._reveal_dealer()
            if p_bj and d_bj:
                self._settle(0, 'Both blackjack — push.', YELLOW)
            elif p_bj:
                payout = int(self.bet * BLACKJACK_PAYOUT)
                self._settle(payout,
                             f'BLACKJACK! +${payout} (3:2 payout).', GREEN)
            else:
                self._settle(-self.bet,
                             'Dealer blackjack — you lose.', RED)
            return

        can_double = self.bankroll >= self.bet * 2
        self._set_action_buttons(can_play=True, can_double=can_double)

    def _action_hit(self) -> None:
        if not self.hand_in_progress:
            return
        self.player.append(deal_card(self.deck))
        self._render_player()
        if is_bust(self.player):
            self._reveal_dealer()
            stake = self.bet * 2 if self.doubled else self.bet
            self._settle(-stake,
                         f'Bust at {hand_value(self.player)} — -${stake}.',
                         RED)
        else:
            # After a hit you can no longer double.
            self._set_action_buttons(can_play=True, can_double=False)
            self._set_status('Your move.', FG)

    def _action_stand(self) -> None:
        if not self.hand_in_progress:
            return
        self._set_action_buttons(can_play=False)
        self._reveal_dealer()
        self._dealer_play_then_settle()

    def _action_double(self) -> None:
        if not self.hand_in_progress:
            return
        if self.bankroll < self.bet * 2:
            self._set_status('Not enough bankroll to double.', RED)
            return
        self.doubled = True
        self.player.append(deal_card(self.deck))
        self._render_player()
        self._set_action_buttons(can_play=False)
        self._reveal_dealer()
        if is_bust(self.player):
            self._settle(-(self.bet * 2),
                         f'Bust on double at {hand_value(self.player)} — '
                         f'-${self.bet * 2}.', RED)
            return
        self._dealer_play_then_settle()

    def _show_hint(self) -> None:
        if not self.hand_in_progress or len(self.player) < 2:
            return
        hint = basic_strategy_hint(self.player, self.dealer[1])
        label = {'H': 'Hit', 'S': 'Stand', 'D': 'Double'}[hint]
        suffix = ''
        if hint == 'D' and (len(self.player) > 2
                            or self.bankroll < self.bet * 2):
            suffix = ' (double unavailable — hit instead)'
        self._set_status(f'Basic strategy says: {label}{suffix}', YELLOW)

    def _reveal_dealer(self) -> None:
        self._render_dealer(hide_hole=False)

    def _dealer_play_then_settle(self) -> None:
        # Step the dealer once per scheduled tick so the player sees the draw.
        if dealer_should_hit(self.dealer):
            self.dealer.append(deal_card(self.deck))
            self._render_dealer(hide_hole=False)
            self.after(500, self._dealer_play_then_settle)
            return
        # Done — resolve.
        stake = self.bet * 2 if self.doubled else self.bet
        p, d = hand_value(self.player), hand_value(self.dealer)
        if d > 21:
            self._settle(stake, f'Dealer busts at {d}. +${stake}!', GREEN)
        elif p > d:
            self._settle(stake, f'You win {p} vs {d}. +${stake}.', GREEN)
        elif p < d:
            self._settle(-stake, f'Dealer wins {d} vs {p}. -${stake}.', RED)
        else:
            self._settle(0, f'Push at {p}.', YELLOW)

    def _settle(self, delta: int, message: str, color: str) -> None:
        self.bankroll += delta
        self.hands_played += 1
        if delta > 0:
            self.wins += 1
        elif delta < 0:
            self.losses += 1
        else:
            self.pushes += 1
        self.hand_in_progress = False
        self._render_money()
        self._set_status(message, color)
        self._set_action_buttons(can_play=False)


if __name__ == '__main__':
    BlackjackApp().mainloop()
