"""Monty Hall — CLI + shared logic.

The classic puzzle: N doors, 1 hides a car, the others hide goats. The player
picks a door. Monty (the host) — who knows where the car is — opens ONE other
door that hides a goat. The player can then switch to one of the other unopened
doors, or stay with the original pick.

Closed-form win probabilities (Monty opens exactly one goat door):

    P(win | stay)   = 1 / N
    P(win | switch) = (N - 1) / (N * (N - 2))   for N >= 3

For N = 3 the switch probability is 2/3, the famous result. As N grows, both
strategies' win rates fall toward 0, but switching always beats staying by a
factor of (N - 1) / (N - 2) (about 2x for N = 3, ~9/8 for N = 10).

Run:
    uv run python monty_hall/monty_hall.py
"""
from __future__ import annotations

import random
from typing import Optional


def play_round(strategy: str, num_doors: int = 3, rng: Optional[random.Random] = None) -> bool:
    """Play one round of Monty Hall. Returns True iff the player wins the car.

    Rules:
      - `num_doors` >= 3 (need at least 3 to play the standard puzzle).
      - Car is uniformly hidden behind one of the doors.
      - Player picks uniformly at random.
      - Monty opens ONE door that is (a) not the player's pick and (b) hides a goat.
      - If `strategy == 'switch'`, the player switches to a uniformly chosen
        unopened, non-original door.
      - If `strategy == 'stay'`, the player keeps the original pick.
    """
    if strategy not in ('switch', 'stay'):
        raise ValueError("strategy must be 'switch' or 'stay'")
    if num_doors < 3:
        raise ValueError('num_doors must be >= 3')

    r = rng if rng is not None else random

    car_door = r.randrange(num_doors)
    pick = r.randrange(num_doors)

    if strategy == 'stay':
        return pick == car_door

    # Switch: Monty opens one goat door (not the pick, not the car).
    candidates = [d for d in range(num_doors) if d != pick and d != car_door]
    monty_opens = r.choice(candidates)

    # Player switches to a uniformly random unopened, non-original door.
    remaining = [d for d in range(num_doors) if d != pick and d != monty_opens]
    new_pick = r.choice(remaining)
    return new_pick == car_door


def simulate(strategy: str, trials: int, num_doors: int = 3,
             rng: Optional[random.Random] = None) -> dict:
    """Run `trials` rounds with the given strategy.

    Returns {'wins': int, 'trials': int, 'p_win': float}.
    """
    if trials <= 0:
        raise ValueError('trials must be > 0')
    wins = 0
    for _ in range(trials):
        if play_round(strategy, num_doors=num_doors, rng=rng):
            wins += 1
    return {'wins': wins, 'trials': trials, 'p_win': wins / trials}


def theoretical(strategy: str, num_doors: int = 3) -> float:
    """Closed-form win probability for the given strategy and door count."""
    if num_doors < 3:
        raise ValueError('num_doors must be >= 3')
    if strategy == 'stay':
        return 1.0 / num_doors
    if strategy == 'switch':
        return (num_doors - 1) / (num_doors * (num_doors - 2))
    raise ValueError("strategy must be 'switch' or 'stay'")


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score 95% confidence interval (default z = 1.96)."""
    if trials <= 0:
        return (0.0, 1.0)
    p = successes / trials
    n = trials
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    half = z * ((p * (1.0 - p) / n + z * z / (4.0 * n * n)) ** 0.5) / denom
    return (max(0.0, center - half), min(1.0, center + half))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _prompt_int(prompt: str, lo: int, hi: int, default: int) -> int:
    while True:
        raw = input(f'{prompt} [{lo}-{hi}, default {default}]: ').strip()
        if raw == '':
            return default
        if raw.isdigit():
            v = int(raw)
            if lo <= v <= hi:
                return v
        print(f'  Please enter an integer between {lo} and {hi}.')


def _prompt_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    opts = '/'.join(choices)
    while True:
        raw = input(f'{prompt} ({opts}, default {default}): ').strip().lower()
        if raw == '':
            return default
        for c in choices:
            if c.startswith(raw):
                return c
        print(f'  Please answer one of: {opts}')


def _interactive_round(num_doors: int, rng: random.Random) -> None:
    """Walk a single round with prompts."""
    car_door = rng.randrange(num_doors)
    print(f'\nThere are {num_doors} doors numbered 1..{num_doors}.')
    pick = _prompt_int('Pick a door', 1, num_doors, 1) - 1

    candidates = [d for d in range(num_doors) if d != pick and d != car_door]
    monty_opens = rng.choice(candidates)
    print(f'\nMonty opens door {monty_opens + 1}... GOAT!')

    remaining = [d for d in range(num_doors) if d != pick and d != monty_opens]
    others = ', '.join(str(d + 1) for d in remaining)
    print(f'You can stay with door {pick + 1} or switch to one of: {others}.')
    decision = _prompt_choice('Switch or stay', ('switch', 'stay'), 'switch')

    if decision == 'stay':
        final = pick
    else:
        final = rng.choice(remaining) if len(remaining) > 1 else remaining[0]

    print(f'\nYou open door {final + 1}...')
    if final == car_door:
        print('  >>> CAR! You win!')
    else:
        print('  >>> Goat. Better luck next time.')
    print(f'  (Car was behind door {car_door + 1}.)')


def main() -> None:
    print('Monty Hall — pick a door, switch or stay, win a car.\n')
    rng = random.Random()

    while True:
        mode = _prompt_choice('Mode', ('play', 'simulate', 'quit'), 'play')
        if mode == 'quit':
            print('Bye!')
            return

        num_doors = _prompt_int('Number of doors', 3, 100, 3)

        if mode == 'play':
            _interactive_round(num_doors, rng)
        else:
            trials = _prompt_int('Number of trials', 100, 1_000_000, 10_000)
            print(f'\nSimulating {trials:,} rounds with {num_doors} doors...')
            sw = simulate('switch', trials, num_doors=num_doors, rng=rng)
            st = simulate('stay', trials, num_doors=num_doors, rng=rng)
            t_sw = theoretical('switch', num_doors)
            t_st = theoretical('stay', num_doors)
            print(f'\n  switch: {sw["wins"]:,}/{sw["trials"]:,} = '
                  f'{sw["p_win"] * 100:6.2f}%   (theoretical {t_sw * 100:6.2f}%)')
            print(f'  stay  : {st["wins"]:,}/{st["trials"]:,} = '
                  f'{st["p_win"] * 100:6.2f}%   (theoretical {t_st * 100:6.2f}%)')
            ratio = sw['p_win'] / st['p_win'] if st['p_win'] > 0 else float('inf')
            print(f'\n  Switching wins {ratio:.2f}x as often as staying.')

        print()


if __name__ == '__main__':
    main()
