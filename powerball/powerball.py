"""Powerball Lottery — pure simulation core + CLI.

Models US Powerball: pick 5 unique white balls from 1..69 plus 1 red Powerball
from 1..26. The grand prize requires matching all 5 whites AND the Powerball.

Public API (used by GUI/TUI):
    draw(rng=None)             -> {'whites': sorted tuple of 5, 'powerball': int}
    score(ticket, drawing)     -> tier label string
    prize_for(tier, jackpot)   -> integer dollar prize for that tier
    THEORETICAL_PROBS          -> dict {tier: probability}
    TIERS                      -> ordered tuple of tier labels (low to high)
    quick_pick(rng=None)       -> draw() (alias for clarity)
    expected_value(jackpot, ...) -> float (per ticket)
    simulate(n, rng=None, ticket=None, jackpot=...) -> dict with hit counts/rates

Run:
    uv run python powerball/powerball.py
"""
from __future__ import annotations

import argparse
import random
from math import comb
from typing import Iterable

# ---- game constants --------------------------------------------------------

WHITE_POOL = 69          # whites are 1..WHITE_POOL
WHITE_PICK = 5
RED_POOL = 26            # powerball is 1..RED_POOL
TICKET_COST = 2          # USD per play

# Prize tiers, ordered worst -> best. None means no prize.
TIERS: tuple[str, ...] = (
    'None',
    'PB only',
    '1+PB',
    '2+PB',
    '3',
    '3+PB',
    '4',
    '4+PB',
    '5',
    '5+PB',  # jackpot
)

# Fixed cash prizes (USD) for non-jackpot tiers.
FIXED_PRIZES: dict[str, int] = {
    'None': 0,
    'PB only': 4,
    '1+PB': 4,
    '2+PB': 7,
    '3': 7,
    '3+PB': 100,
    '4': 100,
    '4+PB': 50_000,
    '5': 1_000_000,
}


# ---- combinatorics ---------------------------------------------------------

def _combos_for(white_match: int, red_match: bool) -> int:
    """Number of (white_set, powerball) outcomes producing exactly
    `white_match` whites correct and `red_match` matching the powerball."""
    # Choose `white_match` of the 5 winning whites, plus (5-white_match)
    # of the 64 losing whites.
    white_combos = comb(WHITE_PICK, white_match) * comb(
        WHITE_POOL - WHITE_PICK, WHITE_PICK - white_match
    )
    red_combos = 1 if red_match else (RED_POOL - 1)
    return white_combos * red_combos


_TOTAL_OUTCOMES = comb(WHITE_POOL, WHITE_PICK) * RED_POOL


def _probability(white_match: int, red_match: bool) -> float:
    return _combos_for(white_match, red_match) / _TOTAL_OUTCOMES


# Precomputed theoretical probability for every named tier.
# 'None' covers every losing combo: 0 whites no PB, 1 white no PB, 2 whites
# no PB. (1 or 2 whites without the PB don't pay, so they fall under 'None'.)
THEORETICAL_PROBS: dict[str, float] = {
    'None':    (_probability(0, False)
                + _probability(1, False)
                + _probability(2, False)),
    'PB only': _probability(0, True),
    '1+PB':    _probability(1, True),
    '2+PB':    _probability(2, True),
    '3':       _probability(3, False),
    '3+PB':    _probability(3, True),
    '4':       _probability(4, False),
    '4+PB':    _probability(4, True),
    '5':       _probability(5, False),
    '5+PB':    _probability(5, True),
}

# Odds shown on the official Powerball ticket are 1-in-X for the WIN tiers
# (everything but 'None'). Useful for display.
ODDS_ONE_IN: dict[str, float] = {
    tier: 1.0 / p for tier, p in THEORETICAL_PROBS.items() if p > 0 and tier != 'None'
}


# ---- core game functions ---------------------------------------------------

def draw(rng: random.Random | None = None) -> dict:
    """Produce one Powerball drawing.

    Returns {'whites': tuple of 5 sorted unique ints in 1..69,
             'powerball': int in 1..26}.
    """
    if rng is None:
        rng = random
    whites = tuple(sorted(rng.sample(range(1, WHITE_POOL + 1), WHITE_PICK)))
    powerball = rng.randint(1, RED_POOL)
    return {'whites': whites, 'powerball': powerball}


def quick_pick(rng: random.Random | None = None) -> dict:
    """Alias of draw() — generates a random ticket."""
    return draw(rng)


def _validate_ticket(ticket: dict) -> None:
    whites = ticket.get('whites')
    pb = ticket.get('powerball')
    if whites is None or pb is None:
        raise ValueError('ticket must have "whites" and "powerball"')
    if len(set(whites)) != WHITE_PICK:
        raise ValueError(f'whites must be {WHITE_PICK} unique ints')
    for w in whites:
        if not (1 <= int(w) <= WHITE_POOL):
            raise ValueError(f'white {w} out of range 1..{WHITE_POOL}')
    if not (1 <= int(pb) <= RED_POOL):
        raise ValueError(f'powerball {pb} out of range 1..{RED_POOL}')


def score(ticket: dict, drawing: dict) -> str:
    """Score a ticket vs a drawing. Returns a tier label from TIERS.

    'None'    : no prize
    'PB only' : 0 whites, powerball matches
    '1+PB'    : 1 white + powerball
    '2+PB'    : 2 whites + powerball
    '3'       : 3 whites, no powerball
    '3+PB'    : 3 whites + powerball
    '4'       : 4 whites, no powerball
    '4+PB'    : 4 whites + powerball
    '5'       : 5 whites, no powerball ($1M)
    '5+PB'    : jackpot
    """
    _validate_ticket(ticket)
    _validate_ticket(drawing)
    whites_match = len(set(ticket['whites']) & set(drawing['whites']))
    pb_match = ticket['powerball'] == drawing['powerball']

    if whites_match == 5 and pb_match:
        return '5+PB'
    if whites_match == 5:
        return '5'
    if whites_match == 4 and pb_match:
        return '4+PB'
    if whites_match == 4:
        return '4'
    if whites_match == 3 and pb_match:
        return '3+PB'
    if whites_match == 3:
        return '3'
    if whites_match == 2 and pb_match:
        return '2+PB'
    if whites_match == 1 and pb_match:
        return '1+PB'
    if whites_match == 0 and pb_match:
        return 'PB only'
    return 'None'


def prize_for(tier: str, jackpot: int = 100_000_000) -> int:
    """Return the dollar prize for a tier. Jackpot fills in for '5+PB'."""
    if tier == '5+PB':
        return int(jackpot)
    return int(FIXED_PRIZES.get(tier, 0))


# ---- expected value & long-run analysis ------------------------------------

def expected_value(jackpot: int = 100_000_000,
                   *, tax_rate: float = 0.37,
                   share_factor: float = 1.0) -> float:
    """Theoretical expected value of one ticket, in dollars.

    `tax_rate` shaves the jackpot for a rough after-tax view (federal top
    bracket ~37%). `share_factor` < 1.0 represents jackpot dilution from
    multiple winners (e.g. 0.7 if you expect to share with another winner).
    Non-jackpot prizes are treated as pre-tax for simplicity (most are small).
    """
    ev = 0.0
    for tier, p in THEORETICAL_PROBS.items():
        if tier == '5+PB':
            net_jackpot = jackpot * (1.0 - tax_rate) * share_factor
            ev += p * net_jackpot
        else:
            ev += p * FIXED_PRIZES.get(tier, 0)
    return ev


def break_even_jackpot(*, tax_rate: float = 0.37,
                       share_factor: float = 1.0,
                       ticket_cost: int = TICKET_COST) -> float:
    """Solve for the jackpot at which EV(ticket) == ticket_cost."""
    p_jackpot = THEORETICAL_PROBS['5+PB']
    p_other = sum(p * FIXED_PRIZES.get(tier, 0)
                  for tier, p in THEORETICAL_PROBS.items()
                  if tier != '5+PB')
    needed = ticket_cost - p_other
    return needed / (p_jackpot * (1.0 - tax_rate) * share_factor)


def simulate(n: int,
             rng: random.Random | None = None,
             ticket: dict | None = None,
             jackpot: int = 100_000_000) -> dict:
    """Simulate `n` independent drawings against a ticket.

    If `ticket` is None, every drawing uses a fresh quick-pick (so each
    simulated play is itself random). Returns dict with:
        counts:     {tier: int}
        rates:      {tier: empirical probability}
        spent:      n * TICKET_COST
        winnings:   total dollars won (jackpot used for '5+PB')
        net:        winnings - spent
    """
    if rng is None:
        rng = random.Random()
    counts = {t: 0 for t in TIERS}
    winnings = 0
    fixed_ticket = ticket
    for _ in range(n):
        play = fixed_ticket if fixed_ticket is not None else draw(rng)
        drawing = draw(rng)
        tier = score(play, drawing)
        counts[tier] += 1
        winnings += prize_for(tier, jackpot)
    spent = n * TICKET_COST
    rates = {t: (c / n if n else 0.0) for t, c in counts.items()}
    return {
        'counts': counts,
        'rates': rates,
        'spent': spent,
        'winnings': winnings,
        'net': winnings - spent,
    }


def lifetime_loss(years: int = 50,
                  per_week: int = 1,
                  jackpot: int = 100_000_000,
                  rng: random.Random | None = None) -> dict:
    """Simulate buying `per_week` tickets every week for `years`.
    Returns dict with spent, winnings, net (typically a big loss)."""
    n = years * 52 * per_week
    return simulate(n, rng=rng, jackpot=jackpot)


# ---- formatting helpers ----------------------------------------------------

def format_drawing(d: dict) -> str:
    whites = '  '.join(f'{w:2d}' for w in d['whites'])
    return f'[ {whites} ]  PB {d["powerball"]:2d}'


# ---- CLI -------------------------------------------------------------------

def _parse_numbers(raw: str, *, count: int, lo: int, hi: int,
                   unique: bool) -> tuple[int, ...]:
    parts = [p for p in raw.replace(',', ' ').split() if p]
    if len(parts) != count:
        raise ValueError(f'expected {count} numbers, got {len(parts)}')
    nums = tuple(int(p) for p in parts)
    for n in nums:
        if not (lo <= n <= hi):
            raise ValueError(f'{n} out of range {lo}..{hi}')
    if unique and len(set(nums)) != count:
        raise ValueError('numbers must be unique')
    return nums


def _interactive_ticket(rng: random.Random) -> dict:
    print(f'Enter your 5 whites (1..{WHITE_POOL}), space-separated, '
          f'or blank for quick-pick:')
    raw = input('> ').strip()
    if not raw:
        return quick_pick(rng)
    whites = _parse_numbers(raw, count=WHITE_PICK, lo=1, hi=WHITE_POOL,
                            unique=True)
    print(f'Enter your Powerball (1..{RED_POOL}):')
    pb_raw = input('> ').strip()
    if not pb_raw:
        return {'whites': tuple(sorted(whites)),
                'powerball': rng.randint(1, RED_POOL)}
    pb = int(pb_raw)
    if not (1 <= pb <= RED_POOL):
        raise ValueError(f'powerball {pb} out of range 1..{RED_POOL}')
    return {'whites': tuple(sorted(whites)), 'powerball': pb}


def _summarize_simulation(result: dict, jackpot: int, n: int) -> None:
    print()
    print(f'Simulated {n:,} drawings (jackpot ${jackpot:,}, '
          f'ticket cost ${TICKET_COST}).')
    print()
    print(f'  {"Tier":<8}  {"hits":>9}  {"emp %":>9}  {"theory %":>10}  '
          f'{"odds (1 in)":>14}')
    print('  ' + '-' * 60)
    for tier in TIERS:
        hits = result['counts'][tier]
        emp = result['rates'][tier] * 100
        th = THEORETICAL_PROBS[tier] * 100
        odds = ODDS_ONE_IN.get(tier)
        odds_str = f'{odds:>14,.0f}' if odds else f'{"-":>14}'
        print(f'  {tier:<8}  {hits:>9,}  {emp:>9.4f}  {th:>10.6f}  {odds_str}')
    print()
    print(f'  Spent:    ${result["spent"]:>14,}')
    print(f'  Won:      ${result["winnings"]:>14,}')
    print(f'  Net:      ${result["net"]:>14,}')


def _print_ev_table(jackpot: int) -> None:
    print()
    print('Expected value analysis')
    print('-' * 60)
    raw_ev = expected_value(jackpot, tax_rate=0.0, share_factor=1.0)
    tax_ev = expected_value(jackpot, tax_rate=0.37, share_factor=1.0)
    share_ev = expected_value(jackpot, tax_rate=0.37, share_factor=0.5)
    be = break_even_jackpot(tax_rate=0.37, share_factor=1.0)
    print(f'  Pre-tax EV per ${TICKET_COST} ticket:        ${raw_ev:8.3f}')
    print(f'  After 37% tax on jackpot:           ${tax_ev:8.3f}')
    print(f'  After tax + 50% jackpot sharing:    ${share_ev:8.3f}')
    print(f'  Break-even jackpot (after-tax):     ${be:,.0f}')
    if tax_ev > TICKET_COST:
        print(f'  EV > ticket cost  -> this jackpot beats break-even.')
    else:
        print(f'  EV <= ticket cost -> negative expectation.')


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog='powerball',
        description='Powerball lottery simulator: tickets, draws, EV analysis.',
    )
    parser.add_argument('--seed', type=int, default=None,
                        help='Seed the RNG for reproducibility.')
    parser.add_argument('--simulate', type=int, default=None, metavar='N',
                        help='Simulate N drawings (uses quick-pick tickets).')
    parser.add_argument('--jackpot', type=int, default=100_000_000,
                        help='Jackpot in dollars (default $100M).')
    parser.add_argument('--lifetime', action='store_true',
                        help='Simulate buying 1 ticket/week for 50 years.')
    parser.add_argument('--ev', action='store_true',
                        help='Just print the expected-value analysis.')
    args = parser.parse_args(argv)

    rng = random.Random(args.seed)

    print('Powerball Lottery: pick 5 of 69 whites + 1 of 26 reds.')
    print()

    if args.ev:
        _print_ev_table(args.jackpot)
        return

    if args.lifetime:
        years = 50
        n = years * 52
        print(f'Lifetime simulation: 1 ticket/week for {years} years '
              f'({n:,} draws), jackpot ${args.jackpot:,}.')
        result = lifetime_loss(years=years, jackpot=args.jackpot, rng=rng)
        _summarize_simulation(result, args.jackpot, n)
        return

    if args.simulate is not None:
        result = simulate(args.simulate, rng=rng, jackpot=args.jackpot)
        _summarize_simulation(result, args.jackpot, args.simulate)
        _print_ev_table(args.jackpot)
        return

    # Interactive single-draw mode.
    try:
        ticket = _interactive_ticket(rng)
    except ValueError as exc:
        print(f'Bad input: {exc}')
        return

    drawing = draw(rng)
    tier = score(ticket, drawing)
    prize = prize_for(tier, args.jackpot)

    print()
    print(f'Your ticket: {format_drawing(ticket)}')
    print(f'Drawing:     {format_drawing(drawing)}')
    print(f'Result:      {tier}   (prize ${prize:,})')
    print()
    _print_ev_table(args.jackpot)


if __name__ == '__main__':
    main()
