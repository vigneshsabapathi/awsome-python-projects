"""Dice Math — fast-paced math drill with rolled dice.

Show N dice (rendered as 3x3 ASCII pip faces), the player types the answer
quickly. Score depends on correctness AND speed.

Multiple modes are supported:

- ``sum``     — sum of all dice
- ``product`` — product of all dice
- ``max``     — largest pip value shown
- ``pair``    — yes/no whether any two dice match (answer 'y' or 'n')

A simple JSON high-score leaderboard is persisted at
``dice_math_scores.json`` next to this file.

Run:
    uv run python dice_math/dice_math.py
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path
from typing import Iterable

# --- Constants --------------------------------------------------------------

DEFAULT_NUM_DICE = 3
DEFAULT_ROUNDS = 10
DEFAULT_MODE = 'sum'
MODES = ('sum', 'product', 'max', 'pair')

# Scoring: a perfect, instant answer maxes out at BASE_POINTS. Points decay
# linearly with elapsed seconds, but a correct slow answer still beats zero.
BASE_POINTS = 100
TIME_DECAY_PER_SEC = 8         # points/sec subtracted from BASE_POINTS
MIN_POINTS_ON_CORRECT = 10     # never give less than this for a correct answer

SCORES_PATH = Path(__file__).with_name('dice_math_scores.json')

# Pip patterns — each face is a 3x3 grid of pip positions (rows top→bottom,
# columns left→right). 'o' = pip, '.' = empty. Faces 1..6 follow the standard
# Western dice convention.
_PIP_PATTERNS: dict[int, tuple[str, str, str]] = {
    1: (
        '.....',
        '..o..',
        '.....',
    ),
    2: (
        'o....',
        '.....',
        '....o',
    ),
    3: (
        'o....',
        '..o..',
        '....o',
    ),
    4: (
        'o...o',
        '.....',
        'o...o',
    ),
    5: (
        'o...o',
        '..o..',
        'o...o',
    ),
    6: (
        'o...o',
        'o...o',
        'o...o',
    ),
}


# --- Pure functions ---------------------------------------------------------


def roll(num_dice: int, rng: random.Random | None = None) -> list[int]:
    """Roll ``num_dice`` six-sided dice and return the results as a list.

    A custom ``rng`` (e.g. ``random.Random(seed)``) makes rolls reproducible —
    useful for tests.
    """
    if num_dice < 1:
        raise ValueError(f'num_dice must be >= 1 (got {num_dice})')
    r = rng if rng is not None else random
    return [r.randint(1, 6) for _ in range(num_dice)]


def dice_face(value: int) -> str:
    """Return a 5-line 3x3 ASCII pip face for ``value`` (1..6).

    Output is exactly 5 lines tall and 7 chars wide:

        +-----+
        |o...o|
        |..o..|
        |o...o|
        +-----+
    """
    if value not in _PIP_PATTERNS:
        raise ValueError(f'dice value must be 1..6 (got {value})')
    pips = _PIP_PATTERNS[value]
    border = '+-----+'
    return '\n'.join([
        border,
        f'|{pips[0]}|',
        f'|{pips[1]}|',
        f'|{pips[2]}|',
        border,
    ])


def format_dice(values: Iterable[int]) -> str:
    """Render multiple dice horizontally, separated by single spaces.

    Returns a 5-line string. Each die is 7 chars wide; with a 1-char gap,
    N dice produce a string ``8N - 1`` chars wide.
    """
    faces = [dice_face(v).split('\n') for v in values]
    if not faces:
        return ''
    rows = []
    for line_idx in range(5):
        rows.append(' '.join(face[line_idx] for face in faces))
    return '\n'.join(rows)


def correct_answer(values: list[int], mode: str) -> int | str:
    """Compute the correct answer for a given mode.

    Returns int for numeric modes, 'y'/'n' for ``pair`` mode.
    """
    if mode == 'sum':
        return sum(values)
    if mode == 'product':
        result = 1
        for v in values:
            result *= v
        return result
    if mode == 'max':
        return max(values)
    if mode == 'pair':
        return 'y' if len(set(values)) < len(values) else 'n'
    raise ValueError(f'unknown mode: {mode!r}')


def score_round(answer: str, correct: int | str, elapsed_s: float) -> int:
    """Compute points awarded for a single round.

    Faster correct answers earn more, slower ones earn less but never below
    ``MIN_POINTS_ON_CORRECT``. Wrong (or unparseable) answers earn 0.
    """
    if not _matches(answer, correct):
        return 0
    raw = BASE_POINTS - int(TIME_DECAY_PER_SEC * max(0.0, elapsed_s))
    return max(MIN_POINTS_ON_CORRECT, raw)


def _matches(answer: str, correct: int | str) -> bool:
    """Tolerant comparison: trim whitespace, case-insensitive for y/n."""
    a = (answer or '').strip().lower()
    if isinstance(correct, str):
        return a == correct.lower()
    if not a:
        return False
    try:
        return int(a) == int(correct)
    except ValueError:
        return False


# --- High score persistence -------------------------------------------------


def load_high_scores(path: Path = SCORES_PATH) -> list[dict]:
    """Load the JSON leaderboard, or [] if the file is missing/corrupt."""
    try:
        with path.open('r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return []


def save_high_score(name: str, score: int, mode: str,
                    path: Path = SCORES_PATH, top_n: int = 10) -> list[dict]:
    """Append ``(name, score, mode)`` to the leaderboard and keep top N."""
    scores = load_high_scores(path)
    scores.append({'name': name, 'score': int(score), 'mode': mode})
    scores.sort(key=lambda e: e.get('score', 0), reverse=True)
    scores = scores[:top_n]
    try:
        with path.open('w', encoding='utf-8') as f:
            json.dump(scores, f, indent=2)
    except OSError:
        pass
    return scores


# --- CLI entry --------------------------------------------------------------


def _prompt_for_answer(mode: str) -> tuple[str, float]:
    """Block on input and return ``(answer, elapsed_seconds)``."""
    suffix = "(y/n) " if mode == 'pair' else ''
    start = time.perf_counter()
    try:
        answer = input(f'Your answer {suffix}> ')
    except EOFError:
        answer = ''
    elapsed = time.perf_counter() - start
    return answer, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Dice Math — fast-paced math drill.')
    parser.add_argument('-n', '--num-dice', type=int, default=DEFAULT_NUM_DICE,
                        help=f'dice per round (2..6, default {DEFAULT_NUM_DICE})')
    parser.add_argument('-r', '--rounds', type=int, default=DEFAULT_ROUNDS,
                        help=f'rounds to play (default {DEFAULT_ROUNDS})')
    parser.add_argument('-m', '--mode', choices=MODES, default=DEFAULT_MODE,
                        help='math mode (default sum)')
    parser.add_argument('--seed', type=int, default=None,
                        help='RNG seed for reproducible rolls')
    args = parser.parse_args()

    num_dice = max(2, min(6, args.num_dice))
    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    print('Dice Math — answer fast for more points!')
    print(f'Mode: {args.mode}   Dice/round: {num_dice}   Rounds: {args.rounds}')
    if args.mode == 'pair':
        print("(answer 'y' or 'n' — do any two dice match?)")
    print()

    total = 0
    streak = 0
    best_streak = 0

    for round_num in range(1, args.rounds + 1):
        values = roll(num_dice, rng)
        target = correct_answer(values, args.mode)

        print(f'--- Round {round_num}/{args.rounds} ---')
        print(format_dice(values))
        answer, elapsed = _prompt_for_answer(args.mode)
        points = score_round(answer, target, elapsed)

        if points > 0:
            streak += 1
            best_streak = max(best_streak, streak)
            print(f'Correct! +{points} points  ({elapsed:.2f}s, streak {streak})')
        else:
            streak = 0
            print(f'Wrong. Answer was {target}  ({elapsed:.2f}s)')

        total += points
        print(f'Score: {total}\n')

    print('=' * 32)
    print(f'Final score: {total}')
    print(f'Best streak: {best_streak}')

    if total > 0:
        try:
            name = (input('Save score as (blank to skip)> ') or '').strip()
        except EOFError:
            name = ''
        if name:
            board = save_high_score(name, total, args.mode)
            print('\nLeaderboard:')
            for i, entry in enumerate(board, 1):
                print(f'  {i:>2}. {entry["name"]:<12} {entry["score"]:>5}'
                      f'   [{entry.get("mode", "?")}]')


if __name__ == '__main__':
    main()
