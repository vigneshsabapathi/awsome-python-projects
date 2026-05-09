"""Snail Race — CLI.

A pari-mutuel-style snail race. Each tick, every snail crawls forward by
0..max_step centimetres along a horizontal track of length `track_length`.
First snail past the finish line wins. The player can place a flat bet
on a snail, and the payout uses the *implied odds* from each snail's
expected step (so betting on the slow steady snail pays bigger than
betting the favourite).

Twist: each snail has a distinct *personality* — different mean speed
and different variance. Some are sprinters (fast on average, very
streaky); some are tortoises (low mean, low variance). The implied
odds are computed live from the personalities, mirroring how a
sportsbook would price the field.

Pure API (re-used by the GUI/TUI frontends):

    SNAILS              tuple of Personality (name, emoji, max_step, color)
    Race(num_snails, track_length, rng)
        .step()              -> dict (per-tick state)
        .step_until_done()   -> dict (final state)
        .is_done()           -> bool
        .winner()            -> int | None
        .positions           -> list[int]
        .tick                -> int
        .personalities       -> list[Personality]
    implied_odds(personalities, track_length) -> list[float]
    payout_multiplier(odds: float) -> float
    settle_bet(bet_snail, wager, balance, race_result, odds) -> dict

Run:
    uv run python snail_race/snail_race.py
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Optional


# ---------------------------------------------------------------------------
# Personalities — the twist. Each snail has its own (max_step) ceiling and
# weighting. We model each step as `randint(0, max_step)` where higher
# max_step ⇒ higher mean *and* higher variance. The "steady" type
# is given a tighter floor so it shuffles forward rather than stalling.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Personality:
    name: str
    emoji: str
    max_step: int   # upper bound on per-tick advance
    min_step: int   # lower bound (steady snails never fully stall)
    color: str      # hex, used by the GUI lanes

    @property
    def mean_step(self) -> float:
        return (self.min_step + self.max_step) / 2


# Order matters: first 4 are the default field. The CLI/GUI/TUI all index
# into this list, so re-ordering will change which snails appear in 4-lane
# mode.
SNAILS: tuple[Personality, ...] = (
    Personality('Sprinter',  'S', max_step=4, min_step=0, color='#ef4444'),
    Personality('Steady',    'T', max_step=2, min_step=1, color='#22c55e'),
    Personality('Average',   'A', max_step=3, min_step=0, color='#3b82f6'),
    Personality('Wild Card', 'W', max_step=5, min_step=0, color='#a855f7'),
    Personality('Plodder',   'P', max_step=2, min_step=0, color='#eab308'),
    Personality('Speedy',    'X', max_step=4, min_step=1, color='#06b6d4'),
)

STARTING_BALANCE = 1000
MIN_WAGER = 10
WAGER_STEP = 10


# ---------------------------------------------------------------------------
# Race engine
# ---------------------------------------------------------------------------

class Race:
    """A snail race. Pure-Python, deterministic given an `rng`.

    The engine keeps `positions[i]` = how far each snail has crawled.
    Once any snail reaches `track_length`, `is_done()` is True and the
    earliest finisher (lowest tick at which it crossed) is the winner.
    Ties (same tick) are broken by farthest position, then lowest index.
    """

    def __init__(self, num_snails: int = 4, track_length: int = 40,
                 rng: Optional[random.Random] = None) -> None:
        if num_snails < 2:
            raise ValueError(f'num_snails must be >= 2, got {num_snails}')
        if num_snails > len(SNAILS):
            raise ValueError(
                f'num_snails {num_snails} exceeds {len(SNAILS)} personalities')
        if track_length < 5:
            raise ValueError(f'track_length must be >= 5, got {track_length}')

        self.num_snails = num_snails
        self.track_length = track_length
        self.rng = rng if rng is not None else random.Random()

        self.personalities: list[Personality] = list(SNAILS[:num_snails])
        self.positions: list[int] = [0] * num_snails
        self.tick: int = 0
        self._winner: Optional[int] = None
        # Per-snail finishing tick — used for tie-breaking visualisation.
        self.finish_tick: list[Optional[int]] = [None] * num_snails

    # ----- queries ----------------------------------------------------------

    def is_done(self) -> bool:
        """True once any snail has crossed the finish line."""
        return self._winner is not None

    def winner(self) -> Optional[int]:
        """Index of the winning snail, or None if the race is still in progress."""
        return self._winner

    def state(self) -> dict:
        """Snapshot suitable for rendering. Frontends call this each tick."""
        return {
            'tick': self.tick,
            'positions': list(self.positions),
            'done': self.is_done(),
            'winner': self._winner,
            'track_length': self.track_length,
            'personalities': self.personalities,
        }

    # ----- mutation ---------------------------------------------------------

    def step(self) -> dict:
        """Advance every snail by 0..max_step (clamped at min_step). Returns
        the new state. Idempotent once `is_done()` becomes True."""
        if self.is_done():
            return self.state()

        self.tick += 1
        for i, p in enumerate(self.personalities):
            advance = self.rng.randint(p.min_step, p.max_step)
            self.positions[i] = min(self.track_length,
                                    self.positions[i] + advance)

        # Detect finishers this tick. If two crossed simultaneously, pick the
        # one farther past the line, then lowest index.
        crossed = [i for i, pos in enumerate(self.positions)
                   if pos >= self.track_length and self.finish_tick[i] is None]
        for i in crossed:
            self.finish_tick[i] = self.tick
        if crossed:
            crossed.sort(key=lambda i: (-self.positions[i], i))
            self._winner = crossed[0]

        return self.state()

    def step_until_done(self) -> dict:
        """Step the race forward until a snail crosses the finish line."""
        # Hard upper bound so a degenerate seed can't loop forever.
        max_ticks = self.track_length * 50
        while not self.is_done() and self.tick < max_ticks:
            self.step()
        return self.state()


# ---------------------------------------------------------------------------
# Odds & payouts — twist (live implied probability per snail)
# ---------------------------------------------------------------------------

def implied_odds(personalities: list[Personality],
                 track_length: int) -> list[float]:
    """Return decimal-odds (e.g. 3.50 means win pays 3.5x stake) for each
    snail, computed from the *expected number of ticks to finish*.

    A snail's expected ticks = track_length / mean_step. We invert that to
    get a "speed score", normalise across the field to get implied
    win-probability, then convert to decimal odds. We add a tiny vig (5%)
    so the house has a small edge — same flavour as a real sportsbook.
    """
    if not personalities:
        return []
    speeds = [p.mean_step for p in personalities]  # higher = more likely
    total = sum(speeds)
    if total <= 0:
        # Degenerate field — all equal odds.
        n = len(personalities)
        return [n + 0.0] * n
    probs = [s / total for s in speeds]
    # Apply 5% overround: each implied probability is inflated so the field
    # sums to 1.05. Decimal odds = 1 / inflated_prob, which gives the house
    # a small edge (a real sportsbook does the same).
    overround = 1.05
    return [1.0 / (p * overround) if p > 0 else 999.0 for p in probs]


def payout_multiplier(odds: float) -> float:
    """Net winnings as a multiple of the stake. odds=3.0 => +2x stake."""
    return max(0.0, odds - 1.0)


def settle_bet(bet_snail: int, wager: int, balance: int,
               winning_snail: int, odds: float) -> dict:
    """Apply the result of one race to the player's bankroll.

    Returns a dict mirroring the cho_han `play_round` shape so the frontends
    can stay symmetric:
        win:     bool
        delta:   +floor(wager * (odds-1)) on win, -wager on loss
        balance: balance after delta
        odds, wager, bet: echoed back
    """
    if wager <= 0:
        raise ValueError(f'wager must be positive, got {wager}')
    if wager > balance:
        raise ValueError(f'wager {wager} exceeds balance {balance}')
    win = (bet_snail == winning_snail)
    if win:
        delta = int(wager * payout_multiplier(odds))
    else:
        delta = -wager
    return {
        'win': win,
        'delta': delta,
        'balance': balance + delta,
        'wager': wager,
        'bet': bet_snail,
        'odds': odds,
        'winner': winning_snail,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _render_track(race: Race) -> str:
    """Return a multi-line ASCII view of the race state."""
    lines = []
    width = race.track_length
    for i, p in enumerate(race.personalities):
        pos = race.positions[i]
        # Cap pos to the visible track for the cursor so '@' doesn't
        # overshoot when pos == track_length.
        cursor = min(pos, width - 1)
        track = ['.'] * width
        track[cursor] = '@'
        lane = ''.join(track)
        marker = '*' if race.winner() == i else ' '
        lines.append(f' {marker} {p.emoji} {p.name:<9} |{lane}| {pos:>3}/{width}')
    lines.append('   ' + ' ' * 12 + '+' + '-' * width + '+')
    return '\n'.join(lines)


def _prompt_int(prompt: str, lo: int, hi: int, default: int) -> int:
    while True:
        raw = input(f'{prompt} [{lo}-{hi}, default {default}]: ').strip()
        if not raw:
            return default
        if raw.isdecimal() and lo <= int(raw) <= hi:
            return int(raw)
        print(f'  ? enter a number between {lo} and {hi}.')


def main() -> None:
    print('Snail Race  —  bet on the slowest creatures in show business.\n')

    num = _prompt_int('How many snails?', 2, len(SNAILS), 4)
    length = _prompt_int('Track length',  10, 80, 40)

    rng = random.Random()
    balance = STARTING_BALANCE
    wager = MIN_WAGER * 5

    while balance > 0:
        race = Race(num_snails=num, track_length=length, rng=rng)
        odds = implied_odds(race.personalities, race.track_length)

        print('\nToday\'s field:')
        for i, p in enumerate(race.personalities):
            print(f'  {i + 1}. {p.emoji} {p.name:<10} '
                  f'mean step {p.mean_step:.1f}   odds {odds[i]:5.2f}x')
        print(f'\nBalance: {balance}    Wager: {wager}')

        choice = input(
            'Pick a snail [1-N], [+/-] wager, [Enter] to start with prior bet, [q]uit: '
        ).strip().lower()

        if choice in ('q', 'quit', 'exit'):
            print(f'You leave with {balance}.')
            return
        if choice in ('+', '='):
            wager = min(wager + WAGER_STEP, balance)
            continue
        if choice == '-':
            wager = max(wager - WAGER_STEP, MIN_WAGER)
            continue
        if not choice:
            print('  ? pick a snail first.')
            continue
        if not (choice.isdecimal() and 1 <= int(choice) <= num):
            print(f'  ? pick a number 1..{num}, or +/- to adjust wager.')
            continue
        bet_snail = int(choice) - 1
        wager = min(wager, balance)

        print(f'\nBetting {wager} on {race.personalities[bet_snail].name}.')
        print('They\'re off!\n')

        # Animate.
        while not race.is_done():
            race.step()
            print('\033[2J\033[H', end='')  # clear + home (works on most terms)
            print(f'Tick {race.tick}')
            print(_render_track(race))
            time.sleep(0.08)

        winner = race.winner()
        wp = race.personalities[winner]
        print(f'\n{wp.emoji} {wp.name} wins in {race.tick} ticks!')

        result = settle_bet(bet_snail, wager, balance, winner, odds[bet_snail])
        balance = result['balance']
        if result['win']:
            print(f'  You won {result["delta"]:+d} '
                  f'({odds[bet_snail]:.2f}x odds).')
        else:
            print(f'  You lost {-result["delta"]}. '
                  f'{race.personalities[bet_snail].name} came {race.positions[bet_snail]}/{length}.')
        print(f'  Balance: {balance}\n')

    print('You are out of money. The snails celebrate. Game over.')


if __name__ == '__main__':
    main()
