"""Blackjack — Textual TUI.

A keyboard-driven dark-themed terminal Blackjack table. Cards render as
boxed rank+suit tiles. The dealer's hole card stays hidden until the player
stands or busts.

Run:
    uv run python blackjack/blackjack_tui.py

Bindings:
    h        — Hit
    s        — Stand
    d        — Double (when legal)
    n        — New hand
    ?        — Basic strategy hint
    Ctrl+Q   — Quit
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

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


def _suit_class(suit: str) -> str:
    return 'red' if suit in ('♥', '♦') else 'black'


def _card_text(card: Card | None, face_up: bool = True) -> str:
    """Two-line card glyph rendered in monospace.

    Hidden cards show a uniform '? ?' pattern. Face-up cards show rank and
    suit on two centered lines. We pad rank to width 2 so '10' aligns with
    'A'/'K'/'Q'/'J'.
    """
    if card is None or not face_up:
        return '┌────┐\n│ ?? │\n└────┘'
    rank = card.rank.ljust(2)
    return f'┌────┐\n│{rank}{card.suit} │\n└────┘'


class BlackjackTUI(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #money {
        text-align: center;
        text-style: bold;
        color: #34d399;
        padding-bottom: 1;
    }

    #record {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    .label {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 0 0 0;
    }

    .hand-row {
        height: 5;
        align-horizontal: center;
        width: 100%;
        padding: 0 0 1 0;
    }

    .card {
        width: 8;
        height: 3;
        margin: 0 1;
        background: #f8fafc;
        color: #0f172a;
        text-style: bold;
        content-align: center middle;
    }

    .card-red   { background: #f8fafc; color: #dc2626; }
    .card-black { background: #f8fafc; color: #0f172a; }
    .card-back  { background: #1e3a8a; color: #bfdbfe; }

    #separator {
        height: 1;
        background: #1e3a8a;
        margin: 1 8;
    }

    #status {
        text-align: center;
        text-style: bold;
        padding: 1;
    }

    .status-info  { color: #f8fafc; }
    .status-win   { color: #34d399; }
    .status-lose  { color: #f87171; }
    .status-push  { color: #fbbf24; }
    .status-hint  { color: #fbbf24; text-style: italic bold; }
    """

    BINDINGS = [
        Binding('h', 'hit', 'Hit'),
        Binding('s', 'stand', 'Stand'),
        Binding('d', 'double', 'Double'),
        Binding('n', 'new_hand', 'New Hand'),
        Binding('question_mark', 'hint', 'Hint'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Blackjack'

    MAX_CARDS_PER_HAND = 8  # enough for any realistic hand

    def __init__(self) -> None:
        super().__init__()
        self.bankroll: int = STARTING_BANKROLL
        self.bet: int = DEFAULT_BET
        self.deck: list[Card] = make_deck()
        self.player: list[Card] = []
        self.dealer: list[Card] = []
        self.doubled: bool = False
        self.hand_in_progress: bool = False
        self.hide_hole: bool = True
        self.hands_played: int = 0
        self.wins: int = 0
        self.losses: int = 0
        self.pushes: int = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('BLACKJACK', id='title')
        yield Static(
            'h Hit  •  s Stand  •  d Double  •  n New  •  ? Hint  •  Ctrl+Q Quit',
            id='subtitle')
        yield Static('', id='money')
        yield Static('', id='record')

        yield Static('Dealer', id='dealer-label', classes='label')
        with Horizontal(classes='hand-row', id='dealer-row'):
            for i in range(self.MAX_CARDS_PER_HAND):
                yield Static('', id=f'dealer-{i}', classes='card')

        yield Static(' ', id='separator')

        yield Static('You', id='player-label', classes='label')
        with Horizontal(classes='hand-row', id='player-row'):
            for i in range(self.MAX_CARDS_PER_HAND):
                yield Static('', id=f'player-{i}', classes='card')

        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._new_hand()

    # ---- rendering ---------------------------------------------------------

    def _render_card_slot(self, slot_id: str,
                          card: Card | None, face_up: bool) -> None:
        slot = self.query_one(f'#{slot_id}', Static)
        if card is None:
            slot.update('')
            slot.set_classes('card')
            slot.styles.background = '#0f172a'
            return
        slot.update(_card_text(card, face_up=face_up))
        slot.styles.background = None  # reset
        if face_up:
            klass = f'card card-{_suit_class(card.suit)}'
        else:
            klass = 'card card-back'
        slot.set_classes(klass)

    def _render_hand(self, prefix: str, cards: list[Card],
                     hide_first: bool) -> None:
        for i in range(self.MAX_CARDS_PER_HAND):
            if i < len(cards):
                self._render_card_slot(
                    f'{prefix}-{i}', cards[i],
                    face_up=not (hide_first and i == 0))
            else:
                self._render_card_slot(f'{prefix}-{i}', None, face_up=True)

    def _render_player(self) -> None:
        self._render_hand('player', self.player, hide_first=False)
        total = hand_value(self.player)
        soft = ' (soft)' if is_soft(self.player) and total <= 21 else ''
        self.query_one('#player-label', Static).update(
            f'You — {total}{soft}')

    def _render_dealer(self) -> None:
        self._render_hand('dealer', self.dealer, hide_first=self.hide_hole)
        if self.hide_hole and self.dealer:
            up = self.dealer[1]
            self.query_one('#dealer-label', Static).update(
                f'Dealer — showing {up.rank}{up.suit}')
        else:
            self.query_one('#dealer-label', Static).update(
                f'Dealer — {hand_value(self.dealer)}')

    def _render_money(self) -> None:
        self.query_one('#money', Static).update(
            f'Bankroll ${self.bankroll}    Bet ${self.bet}')
        self.query_one('#record', Static).update(
            f'Hands {self.hands_played}   '
            f'W {self.wins}  L {self.losses}  P {self.pushes}')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    # ---- game flow ---------------------------------------------------------

    def _new_hand(self) -> None:
        if self.bankroll < self.bet:
            self._render_money()
            self._set_status(
                f'Out of chips at ${self.bankroll}. Press Ctrl+Q to quit.',
                'lose')
            self.hand_in_progress = False
            return

        if len(self.deck) < 15:
            self.deck = make_deck()

        self.player = [deal_card(self.deck), deal_card(self.deck)]
        self.dealer = [deal_card(self.deck), deal_card(self.deck)]
        self.doubled = False
        self.hide_hole = True
        self.hand_in_progress = True

        self._render_player()
        self._render_dealer()
        self._render_money()
        self._set_status('Your move — h Hit, s Stand, d Double, ? Hint',
                         'info')

        # Natural blackjacks resolve immediately.
        p_bj = is_blackjack(self.player)
        d_bj = is_blackjack(self.dealer)
        if p_bj or d_bj:
            self.hide_hole = False
            self._render_dealer()
            if p_bj and d_bj:
                self._settle(0, 'Both blackjack — push.', 'push')
            elif p_bj:
                payout = int(self.bet * BLACKJACK_PAYOUT)
                self._settle(payout,
                             f'BLACKJACK! +${payout} (3:2 payout)', 'win')
            else:
                self._settle(-self.bet,
                             'Dealer blackjack — you lose.', 'lose')

    def action_hit(self) -> None:
        if not self.hand_in_progress:
            return
        self.player.append(deal_card(self.deck))
        self._render_player()
        if is_bust(self.player):
            self.hide_hole = False
            self._render_dealer()
            stake = self.bet * 2 if self.doubled else self.bet
            self._settle(-stake,
                         f'Bust at {hand_value(self.player)} — -${stake}',
                         'lose')

    def action_stand(self) -> None:
        if not self.hand_in_progress:
            return
        self.hide_hole = False
        self._render_dealer()
        self._dealer_play_step()

    def action_double(self) -> None:
        if not self.hand_in_progress:
            return
        if len(self.player) != 2 or self.bankroll < self.bet * 2:
            self._set_status(
                'Double not allowed — must be your first decision and have '
                f'${self.bet * 2}+ bankroll.', 'lose')
            return
        self.doubled = True
        self.player.append(deal_card(self.deck))
        self._render_player()
        self.hide_hole = False
        self._render_dealer()
        if is_bust(self.player):
            self._settle(-(self.bet * 2),
                         f'Bust on double at {hand_value(self.player)} — '
                         f'-${self.bet * 2}', 'lose')
            return
        self._dealer_play_step()

    def action_new_hand(self) -> None:
        if self.hand_in_progress:
            self._set_status('Finish the current hand first.', 'lose')
            return
        self._new_hand()

    def action_hint(self) -> None:
        if not self.hand_in_progress or len(self.player) < 2:
            return
        hint = basic_strategy_hint(self.player, self.dealer[1])
        label = {'H': 'Hit', 'S': 'Stand', 'D': 'Double'}[hint]
        suffix = ''
        if hint == 'D' and (len(self.player) > 2
                            or self.bankroll < self.bet * 2):
            suffix = ' (double unavailable — hit instead)'
        self._set_status(f'Basic strategy: {label}{suffix}', 'hint')

    def _dealer_play_step(self) -> None:
        """Step the dealer one card at a time so the user sees the action."""
        if dealer_should_hit(self.dealer):
            self.dealer.append(deal_card(self.deck))
            self._render_dealer()
            self.set_timer(0.45, self._dealer_play_step)
            return
        # Resolve.
        stake = self.bet * 2 if self.doubled else self.bet
        p, d = hand_value(self.player), hand_value(self.dealer)
        if d > 21:
            self._settle(stake, f'Dealer busts at {d}. +${stake}!', 'win')
        elif p > d:
            self._settle(stake, f'You win {p} vs {d}. +${stake}', 'win')
        elif p < d:
            self._settle(-stake, f'Dealer wins {d} vs {p}. -${stake}', 'lose')
        else:
            self._settle(0, f'Push at {p}.', 'push')

    def _settle(self, delta: int, message: str, kind: str) -> None:
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
        self._set_status(message + '   Press n for a new hand.', kind)


if __name__ == '__main__':
    BlackjackTUI().run()
