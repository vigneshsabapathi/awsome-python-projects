"""Blackjack — CLI implementation.

A classic Blackjack (21) card game against the dealer. The player tries to
get a hand total as close to 21 as possible without going over. Aces count
as either 1 or 11 — whichever is best for the hand. The dealer hits until
their total is 17 or higher (stands on all 17s, including soft 17).

Implemented from scratch from the rules of Blackjack — no source from any
particular book was consulted.

Inspired by Al Sweigart's Blackjack from "The Big Book of Small Python
Projects" (we read its description, not its code).

Run:
    uv run python blackjack/blackjack.py

This module also exposes pure functions importable by the GUI/TUI front-ends:
    - Card                     namedtuple (rank, suit)
    - SUITS, RANKS             constants
    - make_deck()              fresh shuffled 52-card deck
    - deal_card(deck)          pop a card off the top of the deck
    - hand_value(cards)        best total <= 21 with Ace soft/hard
    - is_soft(cards)           True if any Ace is still counted as 11
    - is_blackjack(cards)      True for a 2-card 21 (natural)
    - is_bust(cards)           total > 21
    - dealer_should_hit(cards) dealer rule: hit while total < 17
    - basic_strategy_hint(...) returns 'H' (hit), 'S' (stand), or 'D' (double)
    - render_card(card)        '[A♠]' style string for terminals
"""
from __future__ import annotations

import random
from collections import namedtuple
from typing import List, Optional

# --- Card model -------------------------------------------------------------

Card = namedtuple('Card', ['rank', 'suit'])

SUITS = ('♠', '♥', '♦', '♣')
RANKS = ('A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K')

# Base point values. Aces are special-cased in hand_value().
RANK_VALUES = {
    'A': 11,
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 10, 'Q': 10, 'K': 10,
}

DEALER_STAND_TOTAL = 17  # Dealer hits while total < this
BLACKJACK_PAYOUT = 1.5   # Natural pays 3:2
STARTING_BANKROLL = 100
DEFAULT_BET = 10


# --- Deck handling ----------------------------------------------------------

def make_deck() -> List[Card]:
    """Return a fresh, shuffled standard 52-card deck."""
    deck = [Card(rank, suit) for suit in SUITS for rank in RANKS]
    random.shuffle(deck)
    return deck


def deal_card(deck: List[Card]) -> Card:
    """Pop one card off the top of the deck. Reshuffles a new deck if empty."""
    if not deck:
        # Defensive: should never run out in a single hand, but keep the
        # invariant simple for the GUI/TUI.
        deck.extend(make_deck())
    return deck.pop()


# --- Hand evaluation --------------------------------------------------------

def _rank_of(card) -> str:
    """Accept either a Card namedtuple or a bare rank string (the smoke test
    passes ['A', '7']). Returns the rank string."""
    if isinstance(card, str):
        return card
    return card.rank


def hand_value(cards) -> int:
    """Return the best (highest <= 21 if possible) total for the hand.

    Aces start counted as 11; we demote them to 1 one at a time while the
    total is over 21. This always returns the canonical "best" score:
    if a soft total <= 21 exists, that's returned; otherwise the hard total
    (which may be > 21, i.e. a bust) is returned.
    """
    total = 0
    aces = 0
    for card in cards:
        r = _rank_of(card)
        total += RANK_VALUES[r]
        if r == 'A':
            aces += 1
    # Demote Aces from 11 -> 1 while we're over 21 and have an Ace to demote.
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def is_soft(cards) -> bool:
    """True if at least one Ace is still counted as 11 in the best total.

    A 'soft' hand can't bust on a single hit, which matters for strategy.
    """
    raw = sum(RANK_VALUES[_rank_of(c)] for c in cards)
    aces = sum(1 for c in cards if _rank_of(c) == 'A')
    # Number of Aces we had to demote to keep total <= 21:
    demoted = 0
    total = raw
    while total > 21 and demoted < aces:
        total -= 10
        demoted += 1
    # Soft iff total <= 21 AND we still have at least one un-demoted Ace.
    return total <= 21 and aces - demoted > 0


def is_blackjack(cards) -> bool:
    """A 'natural' — exactly two cards totalling 21."""
    return len(cards) == 2 and hand_value(cards) == 21


def is_bust(cards) -> bool:
    return hand_value(cards) > 21


# --- Dealer logic -----------------------------------------------------------

def dealer_should_hit(cards) -> bool:
    """Dealer hits while total < 17. Stands on all 17s (including soft 17).

    This is the 'S17' rule, more player-friendly than 'H17'. Many casino
    tables use H17; switch the soft-17 branch if you want that variant.
    """
    return hand_value(cards) < DEALER_STAND_TOTAL


# --- Basic strategy hint ----------------------------------------------------

def basic_strategy_hint(player_cards, dealer_upcard) -> str:
    """Return a basic-strategy recommendation: 'H' hit, 'S' stand, 'D' double.

    This is a simplified S17 chart for hard/soft totals, no pair-splitting
    (we don't implement splits). Returns the canonical hint a beginner
    should follow. Doubling collapses to 'H' if the player already took
    a hit (caller decides whether double is still legal).
    """
    p_total = hand_value(player_cards)
    soft = is_soft(player_cards)
    up = _rank_of(dealer_upcard)
    up_val = 11 if up == 'A' else RANK_VALUES[up]

    # --- Soft totals (one Ace counted as 11) ---
    if soft:
        if p_total >= 19:
            return 'S'
        if p_total == 18:
            # Soft 18: stand vs 2-8, hit vs 9/10/A; double vs 3-6 if allowed.
            if up_val in (3, 4, 5, 6):
                return 'D'
            if up_val in (9, 10, 11):
                return 'H'
            return 'S'
        if p_total == 17:
            return 'D' if up_val in (3, 4, 5, 6) else 'H'
        if p_total in (15, 16):
            return 'D' if up_val in (4, 5, 6) else 'H'
        if p_total in (13, 14):
            return 'D' if up_val in (5, 6) else 'H'
        return 'H'  # soft 12 or less

    # --- Hard totals ---
    if p_total >= 17:
        return 'S'
    if p_total >= 13:
        return 'S' if up_val in (2, 3, 4, 5, 6) else 'H'
    if p_total == 12:
        return 'S' if up_val in (4, 5, 6) else 'H'
    if p_total == 11:
        return 'D'  # always double 11 (S17)
    if p_total == 10:
        return 'D' if up_val in (2, 3, 4, 5, 6, 7, 8, 9) else 'H'
    if p_total == 9:
        return 'D' if up_val in (3, 4, 5, 6) else 'H'
    return 'H'  # 8 or less


# --- Pretty printing --------------------------------------------------------

def render_card(card) -> str:
    """Compact card label for terminal display, e.g. '[10♥]' or '[??]'."""
    if card is None:
        return '[??]'
    return f'[{card.rank}{card.suit}]'


def render_hand(cards, hide_first: bool = False) -> str:
    """Stringify a hand, optionally hiding the first card (dealer hole card)."""
    if hide_first and cards:
        parts = ['[??]'] + [render_card(c) for c in cards[1:]]
    else:
        parts = [render_card(c) for c in cards]
    return ' '.join(parts)


# --- CLI game loop ----------------------------------------------------------

def _prompt_action(player_cards, can_double: bool) -> str:
    """Ask the player for their move. Returns one of {'H','S','D'}."""
    options = '(H)it, (S)tand'
    if can_double:
        options += ', (D)ouble'
    options += ', (?)hint, (Q)uit'
    while True:
        choice = input(f'{options} > ').strip().lower()
        if choice in ('h', 'hit'):
            return 'H'
        if choice in ('s', 'stand'):
            return 'S'
        if choice in ('d', 'double') and can_double:
            return 'D'
        if choice in ('?', 'hint'):
            # Hint uses the dealer's visible upcard (index 1 = upcard,
            # since the hole card is hidden at index 0 in casino dealing.
            # In our code we store [hole, up] for the dealer.
            return 'HINT'
        if choice in ('q', 'quit'):
            return 'Q'
        print("Type 'h', 's', 'd' (if available), '?' for a hint, or 'q' to quit.")


def _play_hand(deck: List[Card], bankroll: int, bet: int) -> int:
    """Play a single hand. Returns the bankroll delta (signed integer)."""
    player: List[Card] = [deal_card(deck), deal_card(deck)]
    dealer: List[Card] = [deal_card(deck), deal_card(deck)]  # [hole, up]
    doubled = False

    print()
    print(f'  Dealer:  [??] {render_card(dealer[1])}')
    print(f'  You:     {render_hand(player)}  (total {hand_value(player)})')

    # Natural blackjack check.
    player_bj = is_blackjack(player)
    dealer_bj = is_blackjack(dealer)
    if player_bj or dealer_bj:
        print(f'  Dealer:  {render_hand(dealer)}  (total {hand_value(dealer)})')
        if player_bj and dealer_bj:
            print('  Both blackjack — push.')
            return 0
        if player_bj:
            payout = int(bet * BLACKJACK_PAYOUT)
            print(f'  BLACKJACK! You win {payout} (3:2 payout).')
            return payout
        print('  Dealer blackjack — you lose.')
        return -bet

    # Player turn
    while True:
        if is_bust(player):
            print(f'  Bust! ({hand_value(player)})')
            return -(bet * 2 if doubled else bet)

        can_double = (len(player) == 2 and bankroll >= bet * 2)
        action = _prompt_action(player, can_double)

        if action == 'Q':
            return 0  # bail without resolving — bankroll unchanged
        if action == 'HINT':
            hint = basic_strategy_hint(player, dealer[1])
            label = {'H': 'Hit', 'S': 'Stand', 'D': 'Double'}[hint]
            note = '' if (hint != 'D' or can_double) else ' (double not allowed — hit instead)'
            print(f'  Basic strategy: {label}{note}')
            continue
        if action == 'D':
            doubled = True
            player.append(deal_card(deck))
            print(f'  Double! You draw: {render_card(player[-1])}  '
                  f'(total {hand_value(player)})')
            break
        if action == 'H':
            player.append(deal_card(deck))
            print(f'  You draw: {render_card(player[-1])}  '
                  f'(total {hand_value(player)})')
            continue
        # action == 'S'
        break

    if is_bust(player):
        print(f'  Bust on double! ({hand_value(player)})')
        return -(bet * 2)

    # Dealer turn — flip hole card and play it out.
    print(f'  Dealer flips: {render_hand(dealer)}  (total {hand_value(dealer)})')
    while dealer_should_hit(dealer):
        dealer.append(deal_card(deck))
        print(f'  Dealer draws: {render_card(dealer[-1])}  '
              f'(total {hand_value(dealer)})')

    final_bet = bet * 2 if doubled else bet
    p_total = hand_value(player)
    d_total = hand_value(dealer)

    if d_total > 21:
        print(f'  Dealer busts at {d_total}. You win {final_bet}!')
        return final_bet
    if p_total > d_total:
        print(f'  You win, {p_total} vs {d_total}. +{final_bet}')
        return final_bet
    if p_total < d_total:
        print(f'  Dealer wins, {d_total} vs {p_total}. -{final_bet}')
        return -final_bet
    print(f'  Push at {p_total}.')
    return 0


def main() -> None:
    print('Blackjack — try to beat the dealer to 21 without busting.\n')
    print(f'You start with ${STARTING_BANKROLL}. Each hand bets ${DEFAULT_BET}.')
    print('Aces count as 1 or 11. Dealer stands on 17. Blackjack pays 3:2.')
    print('Type ? for a basic-strategy hint at any decision point.\n')

    bankroll = STARTING_BANKROLL
    bet = DEFAULT_BET
    deck = make_deck()
    hands_played = 0

    while bankroll >= bet:
        # Reshuffle when half the deck is gone — keeps the count from getting
        # too deep in a single shoe and avoids late-deck weirdness.
        if len(deck) < 26:
            deck = make_deck()
            print('  (Shuffled a fresh deck.)')

        delta = _play_hand(deck, bankroll, bet)
        bankroll += delta
        hands_played += 1
        print(f'  Bankroll: ${bankroll}  (hand #{hands_played}, '
              f'{"won" if delta > 0 else "lost" if delta < 0 else "pushed"} '
              f'${abs(delta)})\n')

        if bankroll < bet:
            print(f'  You\'re out of chips. Final bankroll: ${bankroll}.')
            break

        again = input('Another hand? (Y/n) > ').strip().lower()
        if again.startswith('n'):
            break

    print(f'\nThanks for playing! You played {hands_played} hand(s) '
          f'and walked away with ${bankroll}.')


if __name__ == '__main__':
    main()
