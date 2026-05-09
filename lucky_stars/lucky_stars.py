"""Lucky Stars - CLI fortune-telling game.

The player rolls three stars from a weighted pool. Each star belongs to a
thematic group (love, work, money, health, fortune). The combination of
stars selects a fortune message from the matching theme bank. Pure
``read_fortune`` is exposed for the GUI/TUI front-ends.

Run:
    uv run python lucky_stars/lucky_stars.py                # one reading
    uv run python lucky_stars/lucky_stars.py --seed 7       # shareable
    uv run python lucky_stars/lucky_stars.py --compat 7 42  # compatibility
    uv run python lucky_stars/lucky_stars.py --history      # show past
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

# --- Star catalog ------------------------------------------------------------
# Ten star symbols, each tagged with a theme. The pool is intentionally
# imbalanced so some themes are slightly rarer (the "lucky" ones).
STARS: tuple[dict[str, str], ...] = (
    {'symbol': '*',  'name': 'Plain Star',     'theme': 'fortune'},
    {'symbol': 'o',  'name': 'Bubble Star',    'theme': 'health'},
    {'symbol': '+',  'name': 'Compass Star',   'theme': 'work'},
    {'symbol': 'x',  'name': 'Crossed Star',   'theme': 'love'},
    {'symbol': '@',  'name': 'Spiral Star',    'theme': 'fortune'},
    {'symbol': '#',  'name': 'Lattice Star',   'theme': 'money'},
    {'symbol': '~',  'name': 'Drifting Star',  'theme': 'health'},
    {'symbol': '%',  'name': 'Echo Star',      'theme': 'love'},
    {'symbol': '$',  'name': 'Coin Star',      'theme': 'money'},
    {'symbol': '!',  'name': 'Beacon Star',    'theme': 'work'},
)

# Unicode glyphs for prettier displays (GUI/TUI). Same order as STARS.
UNICODE_SYMBOLS: tuple[str, ...] = (
    '★', '☆', '✦', '✧', '✨',
    '✩', '✪', '✭', '✮', '✯',
)

THEMES: tuple[str, ...] = ('love', 'work', 'money', 'health', 'fortune')

# Two original fortunes per theme are not enough — author 4 each, 20 total.
FORTUNES: dict[str, tuple[str, ...]] = {
    'love': (
        'A familiar voice will say the thing you needed to hear all year.',
        'Stop rehearsing the apology — write the invitation instead.',
        'Someone is keeping a small gift for you that they keep forgetting to send.',
        'The next honest conversation you have will rearrange a friendship for the better.',
    ),
    'work': (
        'The quiet task you keep postponing is the one that unlocks the next promotion.',
        'A polite no this week buys you back an entire month of focus.',
        'Your half-finished side project is closer to done than your inner critic admits.',
        'A meeting you dread will end thirty minutes early and resolve in your favor.',
    ),
    'money': (
        'Check an old account — there is something small and forgotten waiting there.',
        'A subscription you forgot about is about to renew. Cancel it today and reclaim it.',
        'A boring, slow investment is quietly outperforming the loud one you keep watching.',
        'Be generous this week with something cheap; a return shows up in an unrelated place.',
    ),
    'health': (
        'Sleep an extra hour tonight. The work you would have done is not the work that matters.',
        'Drink a glass of water before your next decision; the version of you that is hydrated is wiser.',
        'A walk after dinner this week will quiet a thought you cannot argue your way out of.',
        'Your body has been asking for one specific change. You already know which one.',
    ),
    'fortune': (
        'A small coincidence on Thursday is not random. Follow it one step further than feels reasonable.',
        'You are exactly three brave sentences away from a doorway you cannot currently see.',
        'The next stranger who laughs at your joke is worth befriending.',
        'A door you assumed was locked is only stuck. Push, do not knock.',
    ),
}

assert sum(len(v) for v in FORTUNES.values()) == 20, 'should be 20 fortunes'

DEFAULT_HISTORY_PATH = Path.home() / '.lucky_stars_history.json'
ROLL_COUNT = 3


# --- Pure logic --------------------------------------------------------------
def _coerce_rng(rng: random.Random | None) -> random.Random:
    return rng if rng is not None else random.Random()


def roll_stars(rng: random.Random | None = None,
               n: int = ROLL_COUNT) -> list[dict[str, str]]:
    """Draw ``n`` stars (with replacement) from ``STARS``."""
    if n < 1:
        raise ValueError('n must be at least 1')
    r = _coerce_rng(rng)
    return [r.choice(STARS) for _ in range(n)]


def dominant_theme(stars: Iterable[dict[str, str]]) -> str:
    """Return the most common theme among ``stars``.

    Ties are broken by the order in ``THEMES`` so seeded readings are
    reproducible regardless of dict iteration order.
    """
    counts = Counter(s['theme'] for s in stars)
    if not counts:
        return THEMES[-1]
    top = max(counts.values())
    for theme in THEMES:
        if counts.get(theme, 0) == top:
            return theme
    return THEMES[-1]  # unreachable


def read_fortune(rng: random.Random | None = None) -> dict:
    """Roll stars and return ``{stars, symbols, theme, message}``.

    ``stars``    -- list of star *names* (stable for human reading)
    ``symbols``  -- ASCII symbols matching the names (CLI-safe)
    ``theme``    -- dominant theme (see :data:`THEMES`)
    ``message``  -- one fortune drawn from that theme's bank
    """
    r = _coerce_rng(rng)
    drawn = roll_stars(r)
    theme = dominant_theme(drawn)
    message = r.choice(FORTUNES[theme])
    return {
        'stars': [s['name'] for s in drawn],
        'symbols': [s['symbol'] for s in drawn],
        'theme': theme,
        'message': message,
    }


# --- Compatibility check (twist) --------------------------------------------
def compatibility(seed_a: int, seed_b: int) -> dict:
    """Compare two seeded readings and produce a compatibility report.

    Score is the count of shared *themes* between the two rolls (0..3),
    scaled to a 0..100 percentage. Works on themes, not exact stars, so
    two readings from different stars but the same vibe still match.
    """
    a = read_fortune(random.Random(seed_a))
    b = read_fortune(random.Random(seed_b))

    a_themes = Counter(_theme_for_name(n) for n in a['stars'])
    b_themes = Counter(_theme_for_name(n) for n in b['stars'])

    overlap = 0
    for theme, count in a_themes.items():
        overlap += min(count, b_themes.get(theme, 0))

    score = int(round(overlap / ROLL_COUNT * 100))
    verdict = _verdict(score)
    return {
        'seed_a': seed_a, 'seed_b': seed_b,
        'reading_a': a, 'reading_b': b,
        'shared_themes': sorted(set(a_themes) & set(b_themes)),
        'score': score, 'verdict': verdict,
    }


def _theme_for_name(name: str) -> str:
    for star in STARS:
        if star['name'] == name:
            return star['theme']
    raise KeyError(f'unknown star name: {name!r}')


def _verdict(score: int) -> str:
    if score >= 90:
        return 'celestial twins'
    if score >= 60:
        return 'aligned constellations'
    if score >= 30:
        return 'crossing orbits'
    return 'distant skies'


# --- History (twist) ---------------------------------------------------------
def save_reading(reading: dict,
                 path: Path = DEFAULT_HISTORY_PATH,
                 seed: int | None = None) -> Path:
    """Append ``reading`` (with timestamp) to a JSON history file."""
    history = load_history(path)
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'seed': seed,
        **reading,
    }
    history.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2, ensure_ascii=False),
                    encoding='utf-8')
    return path


def load_history(path: Path = DEFAULT_HISTORY_PATH) -> list[dict]:
    """Return saved readings, or ``[]`` if the file is missing/corrupt."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


# --- CLI animation -----------------------------------------------------------
SPINNER_FRAMES: tuple[str, ...] = (
    '*  .  .', '.  *  .', '.  .  *', '.  *  .',
    '*  *  .', '.  *  *', '*  .  *', '*  *  *',
)


def _animate_roll(seconds: float = 1.5, fps: int = 12,
                  out=sys.stdout) -> None:
    """Print a rolling-stars spinner. No-op if stdout is not a TTY."""
    if not getattr(out, 'isatty', lambda: False)():
        return
    end = time.monotonic() + seconds
    i = 0
    out.write('  Rolling the stars...  ')
    out.flush()
    while time.monotonic() < end:
        frame = SPINNER_FRAMES[i % len(SPINNER_FRAMES)]
        out.write('\r  Rolling the stars...  ' + frame + '   ')
        out.flush()
        time.sleep(1.0 / fps)
        i += 1
    out.write('\r' + ' ' * 60 + '\r')
    out.flush()


def render_reading(reading: dict) -> str:
    """Multi-line, monospace-friendly rendering of a fortune."""
    line = '  '.join(reading['symbols'])
    names = ', '.join(reading['stars'])
    return (
        f'\n  Your stars: {line}\n'
        f'  ({names})\n'
        f'  Theme: {reading["theme"]}\n\n'
        f'  {reading["message"]}\n'
    )


# --- CLI ---------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Lucky Stars - roll a fortune from the night sky.'
    )
    parser.add_argument('-s', '--seed', type=int, default=None,
                        help='reproducible / shareable seed')
    parser.add_argument('--save', action='store_true',
                        help='append the reading to the history file')
    parser.add_argument('--history', action='store_true',
                        help='print saved readings and exit')
    parser.add_argument('--compat', nargs=2, metavar=('SEED_A', 'SEED_B'),
                        type=int, default=None,
                        help='compare two seeded readings')
    parser.add_argument('--no-animation', action='store_true',
                        help='skip the rolling-stars animation')
    return parser.parse_args(argv)


def _print_history(path: Path = DEFAULT_HISTORY_PATH) -> None:
    history = load_history(path)
    if not history:
        print('  (no readings saved yet)')
        return
    print(f'  {len(history)} saved reading(s) at {path}:')
    for i, entry in enumerate(history, 1):
        ts = entry.get('timestamp', '?')
        theme = entry.get('theme', '?')
        msg = entry.get('message', '')
        print(f'  {i:2d}. [{ts}] ({theme}) {msg}')


def _print_compat(report: dict) -> None:
    print(f'\n  Compatibility check: seed {report["seed_a"]} '
          f'vs seed {report["seed_b"]}')
    print(f'  Score: {report["score"]}/100  ->  {report["verdict"]}')
    print(f'  Shared themes: '
          f'{", ".join(report["shared_themes"]) or "(none)"}\n')
    print('  --- Reading A ---')
    print(render_reading(report['reading_a']))
    print('  --- Reading B ---')
    print(render_reading(report['reading_b']))


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    if args.history:
        _print_history()
        return

    if args.compat is not None:
        report = compatibility(args.compat[0], args.compat[1])
        _print_compat(report)
        return

    rng = random.Random(args.seed)
    if not args.no_animation:
        _animate_roll()
    reading = read_fortune(rng)
    print(render_reading(reading))
    if args.seed is not None:
        print(f'  (seed: {args.seed} - share to reproduce)')
    if args.save:
        path = save_reading(reading, seed=args.seed)
        print(f'  Saved to {path}')


if __name__ == '__main__':
    main()
