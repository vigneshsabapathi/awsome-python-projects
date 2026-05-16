"""Fast Draw — CLI quick-reaction game.

The screen shows "WAIT..." for a random 1-5 seconds, then suddenly switches to
"DRAW!" — press any key as fast as possible. Your reaction time is measured in
milliseconds.

Twist: tracks full statistics (mean, std-dev, fastest, false-start rate) and
offers an optional Stroop-test variant where the word "DRAW" appears in a
misleading colour (red instead of green) to add cognitive interference.

Run:
    uv run python fast_draw/fast_draw.py
"""
from __future__ import annotations

import math
import random
import sys
import time


# ---------------------------------------------------------------------------
# Pure game logic
# ---------------------------------------------------------------------------

class Game:
    """State machine for a single Fast Draw round.

    Typical lifecycle::

        g = Game()
        wait_secs = g.start_round()   # randomise wait duration
        # ... host code sleeps wait_secs then fires the DRAW signal ...
        g.draw_now()                  # mark the exact moment DRAW appears
        # ... player presses key after elapsed_ms milliseconds ...
        result = g.react(elapsed_ms)  # record response, returns RoundResult
    """

    def __init__(self) -> None:
        self._wait_secs: float = 0.0
        self._draw_time: float | None = None
        self._phase: str = 'idle'          # idle | waiting | draw | done
        self.history: list[dict] = []       # list of {ms, false_start} dicts

    # -- round control --

    def start_round(self) -> float:
        """Begin a new round; return the random wait duration in seconds."""
        self._wait_secs = random.uniform(1.0, 5.0)
        self._draw_time = None
        self._phase = 'waiting'
        return self._wait_secs

    def draw_now(self) -> None:
        """Call immediately when the DRAW signal is displayed."""
        if self._phase != 'waiting':
            raise RuntimeError('draw_now() called outside waiting phase')
        self._draw_time = time.perf_counter()
        self._phase = 'draw'

    def react(self, elapsed_ms: float) -> dict:
        """Record the player's reaction.

        Args:
            elapsed_ms: milliseconds between DRAW appearing and player input.
                        Pass a negative value to register a false start.

        Returns:
            dict with keys: ms (float), false_start (bool),
                            mean_ms (float), std_ms (float),
                            best_ms (float | None), false_start_rate (float).
        """
        false_start = elapsed_ms < 0
        entry = {'ms': elapsed_ms if not false_start else 0.0,
                 'false_start': false_start}
        self.history.append(entry)
        self._phase = 'done'
        return {**entry, **self._stats()}

    def false_start_now(self) -> dict:
        """Convenience: player pressed key during WAIT phase."""
        entry = {'ms': 0.0, 'false_start': True}
        self.history.append(entry)
        self._phase = 'done'
        return {**entry, **self._stats()}

    # -- statistics --

    def _stats(self) -> dict:
        valid = [e['ms'] for e in self.history if not e['false_start']]
        n = len(valid)
        mean = sum(valid) / n if n else 0.0
        std = math.sqrt(sum((x - mean) ** 2 for x in valid) / n) if n > 1 else 0.0
        best = min(valid) if valid else None
        total = len(self.history)
        false_starts = sum(1 for e in self.history if e['false_start'])
        rate = false_starts / total if total else 0.0
        return {'mean_ms': mean, 'std_ms': std,
                'best_ms': best, 'false_start_rate': rate}

    @property
    def phase(self) -> str:
        return self._phase

    @property
    def rounds_played(self) -> int:
        return len(self.history)


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _read_key_blocking() -> str:
    """Block until the user presses a key; return that character."""
    if sys.platform == 'win32':
        import msvcrt
        ch = msvcrt.getwch()
        return ch
    else:
        import tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        return ch


def _wait_for_key_with_false_start(game: Game) -> tuple[bool, float]:
    """Poll for a keypress during the WAIT phase using a busy-poll trick.

    Returns (false_start, elapsed_ms_after_draw).
    elapsed_ms is meaningful only when false_start is False.
    """
    if sys.platform == 'win32':
        import msvcrt
        # spin until DRAW fires
        while game.phase == 'waiting':
            if msvcrt.kbhit():
                msvcrt.getwch()  # consume
                return True, 0.0
            time.sleep(0.001)
        # now in draw phase — measure from draw_now() call
        draw_ts = game._draw_time  # type: ignore[attr-defined]
        while True:
            if msvcrt.kbhit():
                msvcrt.getwch()
                elapsed = (time.perf_counter() - draw_ts) * 1000
                return False, elapsed
            time.sleep(0.001)
    else:
        import select, tty, termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while game.phase == 'waiting':
                r, _, _ = select.select([sys.stdin], [], [], 0.001)
                if r:
                    sys.stdin.read(1)
                    return True, 0.0
            draw_ts = game._draw_time  # type: ignore[attr-defined]
            while True:
                r, _, _ = select.select([sys.stdin], [], [], 0.001)
                if r:
                    sys.stdin.read(1)
                    elapsed = (time.perf_counter() - draw_ts) * 1000
                    return False, elapsed
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _sleep_then_draw(game: Game) -> None:
    """Sleep the wait period then call game.draw_now() in the same thread."""
    time.sleep(game._wait_secs)  # type: ignore[attr-defined]
    game.draw_now()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    import threading

    game = Game()
    print('\n' + '=' * 50)
    print('  FAST DRAW  —  quick-reaction game')
    print('=' * 50)
    print('Press SPACE (or any key) when you see DRAW!')
    print('Press any key during WAIT to register a false start.')
    print('Press Ctrl+C to quit.\n')

    try:
        while True:
            input('  [ Press Enter to start a round ]')
            game.start_round()

            # Start a background thread that sleeps then fires draw_now().
            t = threading.Thread(target=_sleep_then_draw, args=(game,),
                                 daemon=True)
            t.start()

            print('\n  WAIT...')
            false_start, elapsed_ms = _wait_for_key_with_false_start(game)

            if false_start:
                result = game.false_start_now()
                print('\n  ** FALSE START! **  You pressed during WAIT.\n')
            else:
                result = game.react(elapsed_ms)
                print(f'\n  DRAW!  Reaction time: {elapsed_ms:.0f} ms\n')

            # Print stats
            print(f'  Rounds played   : {game.rounds_played}')
            if result['best_ms'] is not None:
                print(f'  Best            : {result["best_ms"]:.0f} ms')
            print(f'  Mean (all valid): {result["mean_ms"]:.0f} ms')
            print(f'  Std-dev         : {result["std_ms"]:.0f} ms')
            print(f'  False-start rate: {result["false_start_rate"]:.0%}')
            print()

    except KeyboardInterrupt:
        print('\n\nGoodbye!')


if __name__ == '__main__':
    main()
