"""Cho-Han — CLI.

A traditional Japanese gambling dice game. The dealer rolls two dice
inside a bamboo cup and the player bets:

    丁 cho — even sum
    半 han — odd sum

A fair coin-flip in disguise: with two fair six-sided dice, P(even) = P(odd) = 1/2,
so the house edge in this base form is zero. We expose pure functions that the
GUI/TUI re-use, plus a small Monte Carlo "ruin probability" estimator for the
twist asked for in the project brief.

Run:
    uv run python cho_han/cho_han.py
"""
from __future__ import annotations

import random
from typing import Optional

# Single source of truth for the bet labels — consumed by all three frontends.
CHO = 'cho'  # 丁 — even
HAN = 'han'  # 半 — odd

KANJI = {CHO: '丁', HAN: '半'}
LABEL = {CHO: 'Chō (even)', HAN: 'Han (odd)'}

STARTING_BALANCE = 5000
MIN_WAGER = 100
WAGER_STEP = 100


def roll_dice(rng: Optional[random.Random] = None) -> tuple[int, int]:
    """Roll two fair six-sided dice. `rng` lets tests inject a seeded Random."""
    r = rng if rng is not None else random
    return r.randint(1, 6), r.randint(1, 6)


def outcome(dice: tuple[int, int]) -> str:
    """Return 'cho' if the sum is even, 'han' if odd."""
    return CHO if (dice[0] + dice[1]) % 2 == 0 else HAN


def play_round(bet: str, wager: int, balance: int,
               rng: Optional[random.Random] = None) -> dict:
    """Play one round and return a structured result.

    The return dict is the contract every frontend depends on:
        dice:    (d1, d2)
        result:  'cho' | 'han'
        win:     bool
        delta:   +wager on win, -wager on loss
        balance: balance after delta is applied
        bet, wager: echoed back for convenience
    """
    if bet not in (CHO, HAN):
        raise ValueError(f"bet must be 'cho' or 'han', got {bet!r}")
    if wager <= 0:
        raise ValueError(f'wager must be positive, got {wager}')
    if wager > balance:
        raise ValueError(f'wager {wager} exceeds balance {balance}')

    dice = roll_dice(rng)
    result = outcome(dice)
    win = (bet == result)
    delta = wager if win else -wager
    return {
        'dice': dice,
        'result': result,
        'win': win,
        'delta': delta,
        'balance': balance + delta,
        'bet': bet,
        'wager': wager,
    }


def ruin_probability(starting_balance: int, wager: int, rounds: int = 200,
                     trials: int = 5_000,
                     rng: Optional[random.Random] = None) -> float:
    """Monte Carlo: chance of busting (balance <= 0) within `rounds` flat bets.

    Used by the GUI/TUI to show the gambler's-ruin risk for the current
    bankroll and wager size. Even on a fair 50/50 game, busting becomes
    near-certain as wager/bankroll grows or rounds → ∞ (random walk crosses 0).
    """
    if wager <= 0 or starting_balance <= 0:
        return 1.0
    r = rng if rng is not None else random
    busts = 0
    for _ in range(trials):
        bal = starting_balance
        for _ in range(rounds):
            # Fair 50/50 — sign of step is what matters; equivalent to ±wager.
            bal += wager if r.random() < 0.5 else -wager
            if bal <= 0:
                busts += 1
                break
    return busts / trials


def main() -> None:
    print('Cho-Han  —  丁 (chō, even)  vs  半 (han, odd)')
    print('Two dice are rolled in a cup. Bet on the parity of the sum.\n')

    balance = STARTING_BALANCE
    wager = MIN_WAGER * 5
    rng = random.Random()

    while True:
        if balance <= 0:
            print('You are out of money. The dealer bows. Game over.')
            return

        print(f'Balance: {balance}   Wager: {wager}')
        choice = input("Bet [c]ho 丁 / [h]an 半 / [+/-] wager / [q]uit: ").strip().lower()
        if not choice:
            continue
        if choice in ('q', 'quit', 'exit'):
            print(f'You leave the table with {balance}. Until next time.')
            return
        if choice in ('+', '='):
            wager = min(wager + WAGER_STEP, balance)
            continue
        if choice == '-':
            wager = max(wager - WAGER_STEP, MIN_WAGER)
            continue
        if choice in ('c', 'cho', '丁'):
            bet = CHO
        elif choice in ('h', 'han', '半'):
            bet = HAN
        else:
            print("  ? type 'c', 'h', '+', '-', or 'q'.")
            continue

        wager = min(wager, balance)
        result = play_round(bet, wager, balance, rng=rng)
        d1, d2 = result['dice']
        kanji = KANJI[result['result']]
        verdict = 'WIN' if result['win'] else 'LOSE'
        print(f"  Dealer lifts the cup… {d1} + {d2} = {d1 + d2}  →  {kanji} ({result['result']})")
        print(f"  You bet {KANJI[bet]} ({bet}) for {wager}.  {verdict}  ({result['delta']:+d})\n")
        balance = result['balance']


if __name__ == '__main__':
    main()
