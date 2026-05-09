"""Sound Mimic — a Simon-says memory game.

Computer plays a sequence of beeps at different pitches; the player
repeats the sequence by pressing keys 1-N (one per pad). Each round
adds one new beep to the end of the sequence.

The pure game state lives in `Game`. The CLI (`main`) wraps it with
ASCII flashes and — on Windows — `winsound.Beep` for actual tones.
On non-Windows platforms it falls back to the terminal bell `\\a`.

Run:
    uv run python sound_mimic/sound_mimic.py
"""
from __future__ import annotations

import platform
import random
import sys
import time
from dataclasses import dataclass, field

# Four distinct musical pitches: C4, E4, G4, C5 (a major triad + octave).
# These match the Simon toy's classic E2/A2/E3/C#3-ish "in-tune" layout
# in spirit: musically harmonious so a long sequence still sounds nice.
PITCHES_4 = (262, 330, 392, 523)
# Six-pad: add D4 and B4 between the above for a wider scale.
PITCHES_6 = (262, 294, 330, 392, 494, 523)
# Eight-pad: a full C-major octave.
PITCHES_8 = (262, 294, 330, 349, 392, 440, 494, 523)

PITCHES = {4: PITCHES_4, 6: PITCHES_6, 8: PITCHES_8}

# ASCII names + colors for CLI rendering. Index = pad number.
PAD_NAMES_4 = ('RED', 'GREEN', 'BLUE', 'YELLOW')
PAD_NAMES_6 = ('RED', 'GREEN', 'BLUE', 'YELLOW', 'PURPLE', 'CYAN')
PAD_NAMES_8 = ('RED', 'GREEN', 'BLUE', 'YELLOW',
               'PURPLE', 'CYAN', 'ORANGE', 'PINK')
PAD_NAMES = {4: PAD_NAMES_4, 6: PAD_NAMES_6, 8: PAD_NAMES_8}

# ANSI background color escapes for CLI flash. Maps pad index → escape.
PAD_ANSI_4 = ('\x1b[41m', '\x1b[42m', '\x1b[44m', '\x1b[43m')
PAD_ANSI_6 = ('\x1b[41m', '\x1b[42m', '\x1b[44m',
              '\x1b[43m', '\x1b[45m', '\x1b[46m')
PAD_ANSI_8 = ('\x1b[41m', '\x1b[42m', '\x1b[44m', '\x1b[43m',
              '\x1b[45m', '\x1b[46m', '\x1b[101m', '\x1b[105m')
PAD_ANSI = {4: PAD_ANSI_4, 6: PAD_ANSI_6, 8: PAD_ANSI_8}
ANSI_RESET = '\x1b[0m'


@dataclass
class Game:
    """Pure game state for Sound Mimic.

    The game holds an internal sequence of pad indices in [0, n_pads).
    Each call to `next_round()` appends one new random pad. The player's
    repeat is checked with `check(player_seq)` which returns True iff
    the player's list matches the internal sequence exactly.

    `rng` is injectable so tests can pin determinism.
    """

    n_pads: int = 4
    rng: random.Random | None = None
    sequence: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.n_pads not in PITCHES:
            raise ValueError(
                f'n_pads must be one of {tuple(PITCHES)}; got {self.n_pads}')
        if self.rng is None:
            self.rng = random.Random()

    @property
    def round(self) -> int:
        """1-indexed round number (= len(sequence))."""
        return len(self.sequence)

    def next_round(self) -> int:
        """Append one random pad to the sequence and return it."""
        # mypy/pyright: rng is guaranteed non-None after __post_init__.
        assert self.rng is not None
        pad = self.rng.randrange(self.n_pads)
        self.sequence.append(pad)
        return pad

    def check(self, player_seq: list[int]) -> bool:
        """Return True iff player_seq matches the internal sequence exactly."""
        return list(player_seq) == self.sequence

    def reset(self) -> None:
        """Clear the sequence — start a new game with the same RNG."""
        self.sequence.clear()

    def state(self) -> dict:
        """Return a snapshot of the current state. Used for tests + UI."""
        return {
            'n_pads': self.n_pads,
            'sequence': list(self.sequence),
            'round': self.round,
        }


def _is_windows() -> bool:
    return platform.system() == 'Windows'


def play_tone(pad: int, n_pads: int = 4, ms: int = 350) -> None:
    """Play the tone for `pad`. Best-effort cross-platform.

    On Windows uses winsound.Beep (actual sound). Elsewhere falls back to
    the terminal bell + a short sleep so timing still feels right.
    """
    pitches = PITCHES[n_pads]
    freq = pitches[pad]
    if _is_windows():
        try:
            import winsound  # stdlib on Windows
            winsound.Beep(freq, ms)
            return
        except Exception:
            pass
    # Fallback: terminal bell + sleep. Not pitched, but keeps timing.
    sys.stdout.write('\a')
    sys.stdout.flush()
    time.sleep(ms / 1000.0)


def _flash_pad(pad: int, n_pads: int) -> None:
    """Print a colored ASCII block for the given pad."""
    name = PAD_NAMES[n_pads][pad]
    color = PAD_ANSI[n_pads][pad]
    bar = '█' * 12
    print(f'  {color} {bar} {ANSI_RESET}  [{pad + 1}] {name}')


def _show_pads(n_pads: int) -> None:
    """Print the legend of available pads."""
    print('\nPads:')
    for i in range(n_pads):
        color = PAD_ANSI[n_pads][i]
        name = PAD_NAMES[n_pads][i]
        print(f'  [{i + 1}] {color}  {ANSI_RESET} {name}')
    print()


def _play_sequence(game: Game, gap_ms: int, tone_ms: int) -> None:
    """Play out the full current sequence with visual flashes."""
    print(f'\nWatch & listen — sequence of {game.round}:')
    for pad in game.sequence:
        _flash_pad(pad, game.n_pads)
        play_tone(pad, game.n_pads, ms=tone_ms)
        time.sleep(gap_ms / 1000.0)
    print()


def _read_player_sequence(game: Game) -> list[int] | None:
    """Read player input. Accepts a single string of digits 1-N (e.g. '1324').

    Returns None on empty input (treated as a forfeit/quit).
    """
    while True:
        prompt = f'Repeat the sequence ({game.round} keys, 1-{game.n_pads}): '
        try:
            raw = input(prompt).strip()
        except EOFError:
            return None
        if not raw:
            return None
        # Accept optional whitespace/separators between digits.
        cleaned = ''.join(ch for ch in raw if not ch.isspace())
        if not cleaned.isdecimal():
            print('  Use digits only. Try again.')
            continue
        if any(int(ch) < 1 or int(ch) > game.n_pads for ch in cleaned):
            print(f'  Digits must be in 1-{game.n_pads}.')
            continue
        return [int(ch) - 1 for ch in cleaned]


def main() -> None:
    print('=== SOUND MIMIC ===')
    print('Watch the colored pads flash and listen to the tones,')
    print('then repeat the sequence by typing the pad numbers.')
    print('Each round adds one new pad. Keep up as long as you can!')
    print()
    print('Difficulty:  [1] easy (4 pads)  [2] normal (6 pads)  [3] hard (8 pads)')
    raw = input('Choose [1/2/3, default 1]: ').strip()
    n_pads = {'1': 4, '2': 6, '3': 8}.get(raw, 4)

    game = Game(n_pads=n_pads)
    _show_pads(n_pads)

    # TWIST: speed-up rounds. Tone & gap shrink as the sequence grows,
    # bottoming out so it stays playable.
    base_tone_ms, base_gap_ms = 380, 220
    min_tone_ms, min_gap_ms = 140, 80

    while True:
        game.next_round()
        # Each subsequent round trims 18ms off both tone and gap.
        tone_ms = max(min_tone_ms, base_tone_ms - 18 * (game.round - 1))
        gap_ms = max(min_gap_ms, base_gap_ms - 18 * (game.round - 1))

        _play_sequence(game, gap_ms=gap_ms, tone_ms=tone_ms)
        player = _read_player_sequence(game)
        if player is None:
            print(f'\nForfeit. Final score: {game.round - 1} round(s).')
            break
        if not game.check(player):
            # Show the correct sequence as 1-indexed digits.
            correct = ''.join(str(p + 1) for p in game.sequence)
            print(f'\nWrong! Sequence was: {correct}')
            print(f'Final score: {game.round - 1} round(s).')
            break
        print(f'  Correct! On to round {game.round + 1}.')
        time.sleep(0.5)


if __name__ == '__main__':
    main()
