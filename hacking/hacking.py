"""Hacking — a Fallout-style password hacking minigame.

The player faces a wall of terminal junk (random ASCII brackets, symbols, and
hex-ish nonsense) with a handful of candidate words hidden inside. One of those
words is the password. Each wrong pick reports its *likeness* — the number of
letter positions that match the secret, like Mastermind. Limited tries.

Pure functions live here so the GUI/TUI can import and reuse them.

Run:
    uv run python hacking/hacking.py
"""
from __future__ import annotations

import math
import random
import string
from collections import Counter
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Tunables — also imported by the GUI/TUI for consistency.
# ---------------------------------------------------------------------------
NUM_WORDS = 15
WORD_LENGTH = 7
MAX_TRIES = 4
JUNK_LINES = 17
JUNK_LINE_WIDTH = 12  # chars of junk on each side of a word slot

# Embedded 7-letter word list. Curated, all uppercase ASCII letters, no
# proper nouns. ~250 entries — plenty of room to sample 15 distinct words.
WORDS_7: tuple[str, ...] = (
    "ABALONE", "ABIDING", "ABREAST", "ABSCESS", "ABSTAIN", "ACCRUAL",
    "ACETATE", "ACIDITY", "ACOLYTE", "ACQUIRE", "ACRONYM", "ACROBAT",
    "ADAMANT", "ADDRESS", "ADJOURN", "ADULATE", "AFFABLE", "AGAINST",
    "AILMENT", "ALCHEMY", "ALIMONY", "ALLERGY", "ALMANAC", "AMBIENT",
    "AMNESTY", "ANCHOVY", "ANCIENT", "ANGUISH", "ANNUITY", "ANTENNA",
    "ANXIETY", "APRICOT", "ARCHIVE", "ARDUOUS", "ARRIVAL", "ARSENAL",
    "ASCETIC", "ASHAMED", "ASPIRIN", "ATELIER", "ATHLETE", "ATTAINS",
    "AUDIBLE", "AUSPICE", "AUTOPSY", "AVERAGE", "AVIATOR", "BALLOON",
    "BANDAGE", "BANKING", "BAPTISM", "BARGAIN", "BARRIER", "BASKETS",
    "BEDROOM", "BELLBOY", "BENEATH", "BENZENE", "BIOLOGY", "BISCUIT",
    "BLEMISH", "BLENDER", "BLINDLY", "BLISTER", "BLOSSOM", "BLOWGUN",
    "BLOWOUT", "BOLSTER", "BOMBARD", "BOOKEND", "BOULDER", "BOUNCED",
    "BOUQUET", "BRACKET", "BRAVERY", "BRIDLED", "BRIGADE", "BRISTLE",
    "BRITTLE", "BROCADE", "BROILER", "BROTHEL", "BROUGHT", "BROWNIE",
    "BRUSHED", "BURROWS", "BUSTLED", "CABINET", "CALCIUM", "CALIBER",
    "CANDIES", "CAPSULE", "CAPTAIN", "CAPTION", "CAPTIVE", "CARBIDE",
    "CARRIER", "CARTOON", "CASCADE", "CASHIER", "CATALOG", "CATTAIL",
    "CAVALRY", "CEILING", "CEMENTS", "CERAMIC", "CERTAIN", "CHAINED",
    "CHALICE", "CHAPTER", "CHARGER", "CHASTEN", "CHEDDAR", "CHEMIST",
    "CHERVIL", "CHIMERA", "CHRONIC", "CIRCUIT", "CITADEL", "CLAIMED",
    "CLAMPED", "CLASPED", "CLASSIC", "CLEAVER", "CLIMATE", "CLIMBER",
    "CLIPPED", "CLOSING", "CLOSURE", "COASTAL", "COBBLER", "COCOONS",
    "COILING", "COMFORT", "COMMAND", "COMPACT", "COMRADE", "CONDEMN",
    "CONDUCT", "CONFESS", "CONIFER", "CONSOLE", "CONSORT", "CONTACT",
    "CONTAIN", "CONTEND", "CONTEST", "CONTORT", "CONTOUR", "CONTROL",
    "CONVERT", "CONVICT", "CONVENE", "CORRECT", "CORRODE", "CORRUPT",
    "COUNCIL", "COUNTRY", "COURIER", "CREVICE", "CRIMSON", "CRINKLE",
    "CROOKED", "CROSSED", "CRUSADE", "CRUSHED", "CUSTODY", "CYCLONE",
    "DACTYLS", "DARKEST", "DAWNING", "DAYLONG", "DAZZLED", "DEALING",
    "DEAREST", "DECANTS", "DECEIVE", "DECIBEL", "DECIDED", "DECODED",
    "DEFECTS", "DEFEATS", "DEFIANT", "DEFICIT", "DEFINED", "DEFROST",
    "DEFUNCT", "DELIGHT", "DEMERIT", "DENSEST", "DENTIST", "DEPARTS",
    "DEPOSIT", "DERIVED", "DESCEND", "DESERVE", "DESPAIR", "DESTROY",
    "DETOURS", "DEVIANT", "DEVIATE", "DEVOTED", "DEVOURS", "DIAGRAM",
    "DIALECT", "DIETING", "DIFFUSE", "DIGNITY", "DILEMMA", "DIMNESS",
    "DIPLOMA", "DISARMS", "DISBAND", "DISCARD", "DISCERN", "DISCORD",
    "DISDAIN", "DISGUST", "DISLIKE", "DISMISS", "DISPLAY", "DISRUPT",
    "DISSENT", "DISTANT", "DISTILL", "DISTORT", "DIURNAL", "DIVERGE",
    "DOGFISH", "DOGGONE", "DOLLOPS", "DOMAINS", "DOORWAY", "DOSSIER",
    "DOTTING", "DRAGOON", "DRAINED", "DRAPERY", "DREADED", "DREAMER",
    "DREDGED", "DRIBBLE", "DRIVING", "DRIZZLE", "DROPLET", "DROUGHT",
    "DRYNESS", "DUCKING", "DURABLE", "DWELLED", "DYNAMIC", "EARLOBE",
    "EARNEST", "EASTERN", "ECLIPSE", "ECSTASY", "EDIFICE", "EDITION",
    "EDUCATE", "ELASTIC", "ELDERLY", "ELEGANT", "ELEMENT", "ELEVATE",
    "ELUSIVE", "EMBARGO", "EMBLEMS", "EMBRACE", "EMPEROR", "EMPLOYS",
    "EMPRESS", "ENCHANT", "ENDLESS", "ENGAGED", "ENGINES", "ENGRAVE",
    "ENHANCE", "ENLARGE", "ENTAILS", "ENTREAT", "ENVELOP", "EPISODE",
    "EQUATOR", "ERRATIC", "ESCAPED", "ESTATES", "EVASION", "EVENING",
    "EVICTED", "EXAMINE", "EXAMPLE", "EXCEEDS", "EXHIBIT", "EXPANSE",
    "EXPLAIN", "EXPLODE", "EXPLORE", "EXPOSED", "EXTINCT", "EXTRACT",
)

# Sanity-check: the curated list must be all 7-letter uppercase ASCII words.
assert all(len(w) == 7 and w.isalpha() and w.isupper() for w in WORDS_7), (
    "WORDS_7 contains malformed entries")
WORDS_7 = tuple(sorted(set(WORDS_7)))

# ---------------------------------------------------------------------------
# Junk-character pool for the Fallout-style terminal wallpaper.
# ---------------------------------------------------------------------------
JUNK_CHARS = "!@#$%^&*()_+-=[]{}<>|/\\:;,.?~`'\""


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------
def _word_pool(length: int) -> tuple[str, ...]:
    """Return the embedded word pool for a given length. Currently only
    WORD_LENGTH is supported; extra lengths fall back to filtering."""
    if length == WORD_LENGTH:
        return WORDS_7
    return tuple(w for w in WORDS_7 if len(w) == length)


def pick_words(n: int = NUM_WORDS, length: int = WORD_LENGTH,
               rng: Optional[random.Random] = None) -> list[str]:
    """Sample `n` distinct uppercase words of the given length.

    `rng` lets tests inject a seeded `random.Random` for determinism.
    """
    if rng is None:
        rng = random.Random()
    pool = _word_pool(length)
    if len(pool) < n:
        raise ValueError(
            f"word pool for length={length} has only {len(pool)} entries; "
            f"need {n}")
    return rng.sample(pool, n)


def likeness(guess: str, secret: str) -> int:
    """Count of positions where guess[i] == secret[i].

    Case-insensitive. Length mismatch raises — both must be the same length
    for the metric to make sense.
    """
    if len(guess) != len(secret):
        raise ValueError(
            f"length mismatch: {len(guess)} vs {len(secret)}")
    g, s = guess.upper(), secret.upper()
    return sum(1 for a, b in zip(g, s) if a == b)


def consistent_candidates(words: Iterable[str],
                          history: Iterable[tuple[str, int]]) -> list[str]:
    """Return words still consistent with all observed (guess, likeness) pairs.

    A word `w` is consistent iff `likeness(g, w) == k` for every (g, k) in
    history.
    """
    out: list[str] = []
    for w in words:
        if all(likeness(g, w) == k for g, k in history):
            out.append(w)
    return out


def expected_info_gain(candidate: str, remaining: list[str]) -> float:
    """Shannon entropy (bits) of the likeness-distribution of `candidate`
    against `remaining`. Higher = more discriminating guess.
    """
    if not remaining:
        return 0.0
    bucket: Counter[int] = Counter()
    for w in remaining:
        bucket[likeness(candidate, w)] += 1
    total = len(remaining)
    h = 0.0
    for count in bucket.values():
        p = count / total
        h -= p * math.log2(p)
    return h


def best_next_guess(words: list[str],
                    history: list[tuple[str, int]]) -> Optional[str]:
    """Suggest the candidate that maximizes expected information gain
    (in bits) among words still consistent with history.

    Returns None if no consistent candidates remain.
    """
    remaining = consistent_candidates(words, history)
    if not remaining:
        return None
    if len(remaining) == 1:
        return remaining[0]

    # Score every still-listed (and consistent) candidate against the
    # remaining set; tie-break by alphabetical order for reproducibility.
    best_word = remaining[0]
    best_score = -1.0
    for cand in remaining:
        score = expected_info_gain(cand, remaining)
        if score > best_score or (score == best_score and cand < best_word):
            best_score = score
            best_word = cand
    return best_word


# ---------------------------------------------------------------------------
# Junk-wall rendering — pure, deterministic given an rng.
# ---------------------------------------------------------------------------
def render_junk_wall(words: list[str],
                     lines: int = JUNK_LINES,
                     side_width: int = JUNK_LINE_WIDTH,
                     rng: Optional[random.Random] = None
                     ) -> tuple[list[str], list[tuple[int, int, str]]]:
    """Build a Fallout-style junk wall and embed each word inside it.

    Returns (lines, placements) where placements is a list of
    (line_index, col_index, word) so a UI can re-highlight word slices.
    """
    if rng is None:
        rng = random.Random()

    # Each word lands on its own line; if there are more lines than words,
    # the extras are pure junk.
    n = len(words)
    if lines < n:
        lines = n
    line_indexes = rng.sample(range(lines), n)
    placements: list[tuple[int, int, str]] = []
    rendered: list[str] = []

    word_iter = dict(zip(line_indexes, words))
    for i in range(lines):
        left = ''.join(rng.choice(JUNK_CHARS) for _ in range(side_width))
        right = ''.join(rng.choice(JUNK_CHARS) for _ in range(side_width))
        if i in word_iter:
            w = word_iter[i]
            text = f"{left} {w} {right}"
            placements.append((i, len(left) + 1, w))
        else:
            mid = ''.join(rng.choice(JUNK_CHARS)
                          for _ in range(len(words[0]) + 2))
            text = f"{left}{mid}{right}"
        # Prefix with a fake hex address for atmosphere.
        addr = 0xF000 + i * 12
        rendered.append(f"0x{addr:04X}  {text}")
    return rendered, placements


# ---------------------------------------------------------------------------
# Game class — UI-agnostic state machine.
# ---------------------------------------------------------------------------
class Game:
    """Stateful container around `words`, the secret, and remaining tries.

    Construction:
        Game(words, secret_idx, max_tries)
    """

    def __init__(self, words: list[str], secret_idx: int,
                 max_tries: int = MAX_TRIES) -> None:
        if not (0 <= secret_idx < len(words)):
            raise ValueError(f"secret_idx {secret_idx} out of range")
        self.words: list[str] = list(words)
        self.secret_idx: int = secret_idx
        self.secret: str = self.words[secret_idx]
        self.max_tries: int = max_tries
        self.tries_left: int = max_tries
        self.history: list[tuple[str, int]] = []
        self.finished: bool = False
        self.won: bool = False

    @classmethod
    def new(cls, n: int = NUM_WORDS, length: int = WORD_LENGTH,
            max_tries: int = MAX_TRIES,
            rng: Optional[random.Random] = None) -> "Game":
        """Convenience factory: pick fresh words + a random secret."""
        if rng is None:
            rng = random.Random()
        words = pick_words(n=n, length=length, rng=rng)
        secret_idx = rng.randrange(len(words))
        return cls(words, secret_idx, max_tries=max_tries)

    def try_word(self, word: str) -> dict:
        """Attempt a guess. Returns a dict:
            {result: 'win'|'wrong'|'lose'|'invalid'|'over',
             tries_left: int,
             likeness: int}
        """
        if self.finished:
            return {"result": "over", "tries_left": self.tries_left,
                    "likeness": 0}

        guess = word.strip().upper()
        if guess not in self.words:
            return {"result": "invalid", "tries_left": self.tries_left,
                    "likeness": 0}

        k = likeness(guess, self.secret)
        self.history.append((guess, k))
        self.tries_left -= 1

        if guess == self.secret:
            self.finished = True
            self.won = True
            return {"result": "win", "tries_left": self.tries_left,
                    "likeness": k}

        if self.tries_left <= 0:
            self.finished = True
            self.won = False
            return {"result": "lose", "tries_left": 0, "likeness": k}

        return {"result": "wrong", "tries_left": self.tries_left,
                "likeness": k}

    def remaining_candidates(self) -> list[str]:
        """Words still consistent with all observed clues."""
        return consistent_candidates(self.words, self.history)

    def hint(self) -> Optional[str]:
        """Optimal next-pick suggestion (max expected info gain)."""
        return best_next_guess(self.words, self.history)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _print_wall(rendered_lines: list[str]) -> None:
    print()
    print("=" * 60)
    for ln in rendered_lines:
        print(ln)
    print("=" * 60)


def _print_word_menu(words: list[str]) -> None:
    print()
    print("CANDIDATE PASSWORDS:")
    for i, w in enumerate(words):
        tag = str(i + 1) if i < 9 else (
            "0" if i == 9 else string.ascii_lowercase[i - 10])
        print(f"  [{tag}] {w}")


def _resolve_choice(raw: str, words: list[str]) -> Optional[int]:
    raw = raw.strip().lower()
    if not raw:
        return None
    # By tag (1..9, 0, a..e for 11..15).
    if len(raw) == 1:
        if raw.isdigit():
            n = int(raw)
            if n == 0 and len(words) >= 10:
                return 9
            if 1 <= n <= 9 and n - 1 < len(words):
                return n - 1
        elif raw in string.ascii_lowercase:
            idx = 10 + (string.ascii_lowercase.index(raw))
            if idx < len(words):
                return idx
    # By literal word.
    upper = raw.upper()
    if upper in words:
        return words.index(upper)
    return None


def main() -> None:
    print("ROBCO INDUSTRIES (TM) TERMLINK PROTOCOL")
    print("PASSWORD REQUIRED")
    print()

    rng = random.Random()
    while True:
        game = Game.new(rng=rng)
        wall, _ = render_junk_wall(game.words, rng=rng)
        _print_wall(wall)

        print(f"\n!! {game.max_tries} ATTEMPT(S) LEFT: "
              f"{'#' * game.max_tries}")
        while not game.finished:
            _print_word_menu(game.words)
            print(f"\nAttempts left: {game.tries_left}.  "
                  f"Type a tag, the WORD, 'hint', or 'quit'.")
            raw = input("> ").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                print("Connection terminated.")
                return
            if raw.lower() in {"h", "hint"}:
                pick = game.hint()
                if pick is None:
                    print(">>> NO CONSISTENT CANDIDATES — PUZZLE BROKEN")
                else:
                    print(f">>> SUGGESTED PICK: {pick}")
                continue

            idx = _resolve_choice(raw, game.words)
            if idx is None:
                print(">>> ENTRY DENIED — UNRECOGNISED")
                continue

            outcome = game.try_word(game.words[idx])
            res = outcome["result"]
            if res == "win":
                print(f">>> {game.words[idx]}")
                print(">>> EXACT MATCH!")
                print(">>> ACCESS GRANTED")
                break
            if res == "wrong":
                print(f">>> {game.words[idx]}")
                print(f">>> ENTRY DENIED")
                print(f">>> LIKENESS = {outcome['likeness']}")
                continue
            if res == "lose":
                print(f">>> {game.words[idx]}")
                print(f">>> LIKENESS = {outcome['likeness']}")
                print(">>> LOCKOUT — TERMINAL DISABLED")
                print(f">>> PASSWORD WAS: {game.secret}")
                break

        print("\nPlay again? (y/N)")
        if not input("> ").strip().lower().startswith("y"):
            break

    print("Goodbye.")


if __name__ == "__main__":
    main()
