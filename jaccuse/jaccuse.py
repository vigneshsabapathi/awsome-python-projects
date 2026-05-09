"""J'Accuse! — a mystery deduction game.

The player visits witnesses across rounds. Each visit reveals one true clue
about the culprit's appearance. With a small chance, a witness lies and gives
a *false* clue — the player must reason under uncertainty.

After exhausting their visit budget (or whenever they're confident), the player
accuses one suspect. A correct accusation wins the case.

Run:
    uv run python jaccuse/jaccuse.py
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------
# Game constants
# ---------------------------------------------------------------------------

NUM_SUSPECTS = 6
NUM_WITNESSES = 5
MAX_ROUNDS = 8
LIE_PROBABILITY = 0.10  # Each witness lies ~10% of the time.

ATTRIBUTES = ('hair', 'clothing', 'accessory')

HAIR_OPTIONS = ('black', 'blonde', 'red', 'brown', 'silver', 'auburn')
CLOTHING_OPTIONS = ('a red coat', 'a navy suit', 'a green dress',
                    'a black trenchcoat', 'a beige raincoat', 'a tweed jacket')
ACCESSORY_OPTIONS = ('a pocket watch', 'a silver cane', 'pearl earrings',
                     'a fedora', 'horn-rimmed glasses', 'a leather satchel')

WITNESS_NAMES = (
    'Mme. Beaumont', 'Inspector Gallois', 'Le Vieux Pierre',
    'Sister Agathe', 'Capitaine Morel', 'Dr. Vaillant',
    'Marie the florist', 'M. Lefevre', 'The bartender',
    'Henriette Dubois', 'Old Jean-Luc', 'The night porter',
)

SUSPECT_NAMES = (
    'Lord Ashworth', 'Comtesse Marchand', 'Dr. Renard',
    'Vivienne Cole', 'Capt. Holloway', 'Sebastian Vance',
    'Lady Pemberton', 'Felix Drummond',
)


# ---------------------------------------------------------------------------
# Pure data
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Suspect:
    name: str
    hair: str
    clothing: str
    accessory: str

    def attribute(self, key: str) -> str:
        return getattr(self, key)

    def initial(self) -> str:
        # First letter of last name (or full name if no spaces).
        parts = self.name.split()
        return (parts[-1][0] if parts else self.name[:1]).upper()


@dataclass(frozen=True)
class Clue:
    """One witness statement about an attribute of the culprit."""
    round_no: int
    witness: str
    attribute: str
    value: str
    truthful: bool  # Hidden from the player; useful for tests/debug.

    def sentence(self) -> str:
        verbs = {
            'hair': 'had {} hair',
            'clothing': 'was wearing {}',
            'accessory': 'was carrying {}',
        }
        clause = verbs[self.attribute].format(self.value)
        return f'{self.witness}: "The culprit {clause}."'


@dataclass
class AccusationResult:
    correct: bool
    accused: str
    culprit: str

    def verdict(self) -> str:
        if self.correct:
            return f'CASE CLOSED — {self.accused} confesses. Justice is served.'
        return (f'WRONG! {self.accused} is innocent. '
                f'The real culprit, {self.culprit}, has fled.')


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def _sample(pool: tuple[str, ...], n: int, rng: random.Random) -> list[str]:
    """Sample n distinct values from pool — repeats if pool is too small."""
    if n <= len(pool):
        return rng.sample(pool, n)
    # Fall back to choices with replacement (shouldn't happen with defaults).
    return [rng.choice(pool) for _ in range(n)]


def generate_suspects(n: int, rng: random.Random) -> list[Suspect]:
    """Build n suspects with distinct names but possibly overlapping attrs.

    Attributes are sampled independently — collisions are intentional, since
    that's what makes deduction non-trivial (e.g. two suspects with red hair).
    """
    names = _sample(SUSPECT_NAMES, n, rng)
    suspects: list[Suspect] = []
    for name in names:
        suspects.append(Suspect(
            name=name,
            hair=rng.choice(HAIR_OPTIONS),
            clothing=rng.choice(CLOTHING_OPTIONS),
            accessory=rng.choice(ACCESSORY_OPTIONS),
        ))
    return suspects


def generate_witnesses(n: int, rng: random.Random) -> list[str]:
    return _sample(WITNESS_NAMES, n, rng)


# ---------------------------------------------------------------------------
# Deduction helpers
# ---------------------------------------------------------------------------

def filter_candidates(suspects: list[Suspect],
                      clues: list[Clue]) -> list[Suspect]:
    """Return suspects consistent with *every* clue, treating each as truth.

    This is the naive filter — when witnesses can lie, a suspect may be
    eliminated unfairly. The GUI/TUI surface that count as a hint, with a
    caveat about reliability.
    """
    survivors = list(suspects)
    for clue in clues:
        survivors = [s for s in survivors
                     if s.attribute(clue.attribute) == clue.value]
    return survivors


def candidates_majority(suspects: list[Suspect],
                        clues: list[Clue]) -> list[Suspect]:
    """Return suspects matching the *most* clues (lie-tolerant hint).

    Each suspect scores +1 per clue whose attribute they match. Suspects with
    the highest score survive. When the strict filter is empty (a witness
    must have lied) this falls back to the closest matches.
    """
    if not clues:
        return list(suspects)
    best_score = -1
    scored: list[tuple[int, Suspect]] = []
    for s in suspects:
        score = sum(1 for c in clues if s.attribute(c.attribute) == c.value)
        scored.append((score, s))
        best_score = max(best_score, score)
    return [s for score, s in scored if score == best_score]


# ---------------------------------------------------------------------------
# Game state
# ---------------------------------------------------------------------------

@dataclass
class Game:
    """Mystery deduction game.

    `rng` is injected so tests/CI can pin a seed. The game owns a list of
    suspects, a list of witness names, the chosen culprit, the set of
    witnesses already visited this case, and the history of clues collected.
    """
    suspects: list[Suspect] = field(default_factory=list)
    witnesses: list[str] = field(default_factory=list)
    max_rounds: int = MAX_ROUNDS
    rng: random.Random = field(default_factory=random.Random)
    lie_probability: float = LIE_PROBABILITY

    culprit: Suspect = field(init=False)
    visited: set[str] = field(init=False, default_factory=set)
    clues: list[Clue] = field(init=False, default_factory=list)
    round_no: int = field(init=False, default=0)
    finished: bool = field(init=False, default=False)
    result: Optional[AccusationResult] = field(init=False, default=None)

    def __post_init__(self) -> None:
        if not self.suspects:
            self.suspects = generate_suspects(NUM_SUSPECTS, self.rng)
        if not self.witnesses:
            self.witnesses = generate_witnesses(NUM_WITNESSES, self.rng)
        self.culprit = self.rng.choice(self.suspects)

    # -- queries -----------------------------------------------------------

    @property
    def rounds_remaining(self) -> int:
        return max(0, self.max_rounds - self.round_no)

    def available_witnesses(self) -> list[str]:
        return [w for w in self.witnesses if w not in self.visited]

    def suspect_by_name(self, name: str) -> Optional[Suspect]:
        target = name.strip().lower()
        for s in self.suspects:
            if s.name.lower() == target:
                return s
        return None

    # -- actions -----------------------------------------------------------

    def visit(self, witness: str) -> Clue:
        """Visit one witness; consume one round; return their clue."""
        if self.finished:
            raise RuntimeError('game is over')
        if witness not in self.witnesses:
            raise ValueError(f'unknown witness: {witness!r}')
        if witness in self.visited:
            raise ValueError(f'already spoke to {witness}')
        if self.rounds_remaining <= 0:
            raise RuntimeError('no rounds left — you must accuse')

        self.round_no += 1
        self.visited.add(witness)

        attribute = self.rng.choice(ATTRIBUTES)
        truthful_value = self.culprit.attribute(attribute)
        truthful = self.rng.random() >= self.lie_probability
        if truthful:
            value = truthful_value
        else:
            # Pick a *different* value drawn from the pool of options.
            pool = self._pool_for(attribute)
            alternatives = [v for v in pool if v != truthful_value]
            value = self.rng.choice(alternatives) if alternatives else truthful_value

        clue = Clue(round_no=self.round_no, witness=witness,
                    attribute=attribute, value=value, truthful=truthful)
        self.clues.append(clue)
        return clue

    def accuse(self, name: str) -> AccusationResult:
        """Name your culprit. Ends the game either way."""
        if self.finished:
            assert self.result is not None
            return self.result
        suspect = self.suspect_by_name(name)
        if suspect is None:
            raise ValueError(f'no such suspect: {name!r}')
        self.finished = True
        self.result = AccusationResult(
            correct=(suspect.name == self.culprit.name),
            accused=suspect.name,
            culprit=self.culprit.name,
        )
        return self.result

    # -- hints -------------------------------------------------------------

    def deduce_strict(self) -> list[Suspect]:
        """Suspects consistent with every clue (assumes no lies)."""
        return filter_candidates(self.suspects, self.clues)

    def deduce_tolerant(self) -> list[Suspect]:
        """Suspects matching the most clues (lie-tolerant)."""
        return candidates_majority(self.suspects, self.clues)

    # -- internals ---------------------------------------------------------

    def _pool_for(self, attribute: str) -> tuple[str, ...]:
        if attribute == 'hair':
            return HAIR_OPTIONS
        if attribute == 'clothing':
            return CLOTHING_OPTIONS
        if attribute == 'accessory':
            return ACCESSORY_OPTIONS
        raise ValueError(f'unknown attribute: {attribute!r}')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

INTRO = """\
J'ACCUSE! — a mystery of the Belle Epoque.

A crime has been committed. {n_suspects} suspects, {n_witnesses} witnesses,
and only {max_rounds} rounds before the trail goes cold. Each witness will
share one detail about the culprit — but {lie_pct}% of them are unreliable.

When you are ready, accuse a suspect by name.
"""


def _format_suspect(s: Suspect) -> str:
    return (f'  [{s.initial()}] {s.name:<22} hair: {s.hair:<8} '
            f'clothing: {s.clothing:<22} accessory: {s.accessory}')


def main() -> None:  # pragma: no cover - interactive
    rng = random.Random()
    game = Game(rng=rng)
    print(INTRO.format(n_suspects=len(game.suspects),
                       n_witnesses=len(game.witnesses),
                       max_rounds=game.max_rounds,
                       lie_pct=int(game.lie_probability * 100)))
    print('SUSPECTS:')
    for s in game.suspects:
        print(_format_suspect(s))
    print()

    while not game.finished:
        print(f'-- Round {game.round_no + 1} of {game.max_rounds} '
              f'({game.rounds_remaining} left) --')
        available = game.available_witnesses()
        if not available or game.rounds_remaining == 0:
            print('No more witnesses available — you must accuse.')
        else:
            print('Witnesses you can still visit:')
            for i, w in enumerate(available, 1):
                print(f'  {i}. {w}')
        print('Commands: number to visit a witness, '
              '`hint` for remaining candidates, '
              '`accuse <name>` to make an accusation, `quit`.')
        choice = input('> ').strip()
        if not choice:
            continue
        if choice.lower() in ('q', 'quit', 'exit'):
            print('You walk away from the case. The culprit was '
                  f'{game.culprit.name}.')
            return
        if choice.lower() == 'hint':
            strict = game.deduce_strict()
            tolerant = game.deduce_tolerant()
            print(f'  Strict filter: {len(strict)} candidate(s) — '
                  f'{", ".join(s.name for s in strict) or "(none — a witness lied)"}')
            print(f'  Lie-tolerant:  {len(tolerant)} candidate(s) — '
                  f'{", ".join(s.name for s in tolerant)}')
            continue
        if choice.lower().startswith('accuse'):
            _, _, name = choice.partition(' ')
            if not name.strip():
                print('  Usage: accuse <suspect name>')
                continue
            try:
                result = game.accuse(name)
            except ValueError as e:
                print(f'  {e}')
                continue
            print(result.verdict())
            return
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(available):
                clue = game.visit(available[idx])
                print(f'  {clue.sentence()}')
                continue
            print('  Out of range.')
            continue
        print('  Did not understand that. Try a number, `hint`, or `accuse <name>`.')

    if game.result is not None:
        print(game.result.verdict())


if __name__ == '__main__':
    main()
