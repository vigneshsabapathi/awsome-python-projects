"""Hungry Robots — CLI.

A grid-chase game. The player (``@``) moves one cell at a time across an
``WIDTH x HEIGHT`` board. Every robot (``R``) responds with a single step
that minimises its Chebyshev distance to the player (``dx, dy ∈ {-1, 0, 1}``).
When two or more robots end the turn on the same cell they crumple into a
wreck (``#``). Any robot that walks onto an existing wreck dies the same way.

The player wins by surviving until every robot is dead, and loses if a
robot ever ends a turn on the player's cell.

Tools:

- ``Game(width, height, n_robots)`` — pure logic class, GUI/TUI agnostic.
- ``move_player(dx, dy)`` — apply one player move + one robot step.
- ``teleport()`` — random reposition (may be unsafe).
- ``safe_teleport()`` — TWIST: rare power-up; lands in an empty cell with
  no adjacent robots, or returns ``False`` if no such cell exists.
- ``wait_until_safe_or_dead()`` — fast-forward; player stands still while
  robots advance until either every robot is dead or the player is caught.

Run:
    uv run python hungry_robots/hungry_robots.py
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

# Glyphs used by all three frontends so the encoding stays consistent.
EMPTY = '.'
PLAYER = '@'
ROBOT = 'R'
WRECK = '#'

# Default level scaling — classic "robots" progression.
DEFAULT_WIDTH = 45
DEFAULT_HEIGHT = 20
START_ROBOTS = 5
ROBOTS_PER_LEVEL = 3
START_TELEPORTS = 2
START_SAFE_TELEPORTS = 1


@dataclass
class Game:
    """Pure-logic Hungry Robots board.

    The class owns the grid + entity bookkeeping but knows nothing about
    rendering — every front-end (CLI/GUI/TUI) reads ``self.player``,
    ``self.robots`` and ``self.wrecks`` to draw a frame.
    """

    width: int = DEFAULT_WIDTH
    height: int = DEFAULT_HEIGHT
    n_robots: int = START_ROBOTS
    level: int = 1
    teleports: int = START_TELEPORTS
    safe_teleports: int = START_SAFE_TELEPORTS
    player: tuple[int, int] = (0, 0)
    robots: set[tuple[int, int]] = field(default_factory=set)
    wrecks: set[tuple[int, int]] = field(default_factory=set)
    won: bool = False
    lost: bool = False
    last_event: str = ''

    def __post_init__(self) -> None:
        if self.width < 5 or self.height < 5:
            raise ValueError('grid must be at least 5x5')
        if self.n_robots < 1:
            raise ValueError('need at least one robot')
        self._reset_board(self.n_robots)

    # ------------------------------------------------------------------ setup

    def _reset_board(self, n_robots: int) -> None:
        """Place the player in the centre and scatter ``n_robots`` randomly."""
        self.robots = set()
        self.wrecks = set()
        self.won = False
        self.lost = False
        self.last_event = ''
        self.player = (self.width // 2, self.height // 2)

        max_robots = self.width * self.height - 1
        n_robots = min(n_robots, max_robots)
        while len(self.robots) < n_robots:
            pos = (random.randrange(self.width), random.randrange(self.height))
            if pos == self.player:
                continue
            self.robots.add(pos)
        self.n_robots = n_robots

    def next_level(self) -> None:
        """Advance to the next level — TWIST: more robots each round."""
        self.level += 1
        self.teleports += 1
        # Award a safe teleport every other level so it stays rare.
        if self.level % 2 == 0:
            self.safe_teleports += 1
        self._reset_board(START_ROBOTS + (self.level - 1) * ROBOTS_PER_LEVEL)

    # ------------------------------------------------------------------ helpers

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def cell(self, x: int, y: int) -> str:
        """Return the glyph occupying ``(x, y)`` — used by renderers."""
        pos = (x, y)
        if pos == self.player:
            return PLAYER
        if pos in self.robots:
            return ROBOT
        if pos in self.wrecks:
            return WRECK
        return EMPTY

    def render(self) -> str:
        """ASCII snapshot of the board — used by the CLI and tests."""
        rows = []
        for y in range(self.height):
            rows.append(''.join(self.cell(x, y) for x in range(self.width)))
        return '\n'.join(rows)

    # ------------------------------------------------------------------ moves

    def move_player(self, dx: int, dy: int) -> dict:
        """Apply one player move (``dx, dy ∈ {-1, 0, 1}``) + one robot step.

        Returns a small event dict so callers can show feedback:

            {'ok': bool, 'message': str, 'killed': int,
             'won': bool, 'lost': bool}
        """
        if self.won or self.lost:
            return self._event(False, 'game over', 0)
        if dx not in (-1, 0, 1) or dy not in (-1, 0, 1):
            return self._event(False, 'invalid direction', 0)

        target = (self.player[0] + dx, self.player[1] + dy)
        if not self.in_bounds(*target):
            return self._event(False, 'edge of grid', 0)
        if target in self.wrecks:
            return self._event(False, 'wreck blocks the way', 0)
        # NOTE: stepping into a robot is suicide — we still allow it so the
        # rules stay symmetrical, but the robot phase will then mark a loss.

        self.player = target
        killed = self._step_robots()
        return self._event(True, '', killed)

    def teleport(self) -> dict:
        """Spend one teleport charge, land at a random in-bounds cell.

        The destination may be unsafe — that's what makes the safe
        teleport TWIST a meaningful resource.
        """
        if self.won or self.lost:
            return self._event(False, 'game over', 0)
        if self.teleports <= 0:
            return self._event(False, 'no teleports left', 0)
        self.teleports -= 1
        self.player = self._random_empty_cell(allow_robot_neighbours=True)
        killed = self._step_robots()
        return self._event(True, 'teleported', killed)

    def safe_teleport(self) -> dict:
        """TWIST: rare 'safe teleport' — empty cell with no adjacent robots.

        Falls back to a regular teleport if no such cell exists. The robots
        still take their turn afterwards, so 'safe' guarantees only the
        landing square, not perpetual immunity.
        """
        if self.won or self.lost:
            return self._event(False, 'game over', 0)
        if self.safe_teleports <= 0:
            return self._event(False, 'no safe teleports left', 0)
        self.safe_teleports -= 1
        landing = self._random_empty_cell(allow_robot_neighbours=False)
        if landing is None:
            # Refund a regular teleport instead so the charge isn't wasted.
            self.player = self._random_empty_cell(allow_robot_neighbours=True)
            killed = self._step_robots()
            return self._event(True, 'no safe cell — regular teleport', killed)
        self.player = landing
        killed = self._step_robots()
        return self._event(True, 'safe teleport', killed)

    def wait_until_safe_or_dead(self) -> dict:
        """Stand still while robots advance until the round resolves.

        Each iteration the robots take one step toward the player; the
        loop stops when every robot is dead (win) or the player dies
        (lost). Bounded by ``width * height`` to guarantee termination.
        """
        if self.won or self.lost:
            return self._event(False, 'game over', 0)
        total_killed = 0
        for _ in range(self.width * self.height):
            killed = self._step_robots()
            total_killed += killed
            if self.won or self.lost or not self.robots:
                break
        return self._event(True, 'waited', total_killed)

    # ------------------------------------------------------------------ robots

    def _step_robots(self) -> int:
        """Move every robot one step toward the player, resolve collisions."""
        if self.won or self.lost:
            return 0
        # Each robot independently chooses sign(dx) and sign(dy) — Chebyshev
        # pursuit in one turn. Multiple robots can target the same cell;
        # those collisions are resolved after the move.
        intended: dict[tuple[int, int], int] = {}
        px, py = self.player
        for rx, ry in self.robots:
            ndx = (px > rx) - (px < rx)  # sign(px - rx) without math.copysign
            ndy = (py > ry) - (py < ry)
            new_pos = (rx + ndx, ry + ndy)
            intended[new_pos] = intended.get(new_pos, 0) + 1

        new_robots: set[tuple[int, int]] = set()
        new_wrecks: set[tuple[int, int]] = set(self.wrecks)
        killed = 0
        for pos, count in intended.items():
            if pos in self.wrecks:
                # Walk into a wreck → all incoming robots are pulverised.
                killed += count
                continue
            if count >= 2:
                # Multi-robot pile-up becomes a wreck.
                new_wrecks.add(pos)
                killed += count
                continue
            new_robots.add(pos)

        self.robots = new_robots
        self.wrecks = new_wrecks

        if self.player in self.robots:
            self.lost = True
        elif not self.robots:
            self.won = True
        return killed

    # ------------------------------------------------------------------ misc

    def _random_empty_cell(
        self, allow_robot_neighbours: bool
    ) -> tuple[int, int] | None:
        """Pick a random empty cell. Optionally avoid adjacent robots."""
        candidates = []
        for x in range(self.width):
            for y in range(self.height):
                pos = (x, y)
                if pos in self.robots or pos in self.wrecks:
                    continue
                if not allow_robot_neighbours and self._has_robot_neighbour(pos):
                    continue
                candidates.append(pos)
        if not candidates:
            # Allow the empty-cell fallback for the unsafe path so we always
            # produce a destination; safe path gets None and falls back.
            if allow_robot_neighbours:
                # Very pathological — board is full. Keep player put.
                return self.player
            return None
        return random.choice(candidates)

    def _has_robot_neighbour(self, pos: tuple[int, int]) -> bool:
        x, y = pos
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                if (x + dx, y + dy) in self.robots:
                    return True
        return False

    def _event(self, ok: bool, message: str, killed: int) -> dict:
        self.last_event = message
        return {
            'ok': ok,
            'message': message,
            'killed': killed,
            'won': self.won,
            'lost': self.lost,
        }

    def is_won(self) -> bool:
        return self.won

    def is_lost(self) -> bool:
        return self.lost


# ----------------------------------------------------------------------- CLI

# Numpad-style direction map shared with the GUI/TUI.
DIRECTIONS = {
    'q': (-1, -1), 'w': (0, -1), 'e': (1, -1),
    'a': (-1,  0),                 'd': (1,  0),
    'z': (-1,  1), 'x': (0,  1), 'c': (1,  1),
    's': (0, 0),  # wait one tick
}


def main() -> None:
    print('Hungry Robots — chase grid (CLI)')
    print('Move: q w e / a d / z x c   |   s wait one step')
    print('t = teleport   T = safe teleport   W = wait until resolved')
    print('n = new game   Q = quit\n')

    game = Game()
    while True:
        print(game.render())
        print(
            f'Level {game.level}  '
            f'robots={len(game.robots)}  wrecks={len(game.wrecks)}  '
            f'teleports={game.teleports}  safe={game.safe_teleports}'
        )
        if game.is_won():
            print('All robots are scrap! Press n for next level, Q to quit.')
        elif game.is_lost():
            print('A robot caught you. Press n to restart, Q to quit.')

        try:
            cmd = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not cmd:
            continue
        first = cmd[0]

        if first == 'Q':
            break
        if first == 'n':
            if game.is_won():
                game.next_level()
            else:
                game = Game()
            continue
        if game.is_won() or game.is_lost():
            continue
        if first == 't':
            print(game.teleport()['message'] or 'teleported')
            continue
        if first == 'T':
            print(game.safe_teleport()['message'] or 'safe teleport')
            continue
        if first == 'W':
            print(game.wait_until_safe_or_dead()['message'] or 'waited')
            continue
        if first in DIRECTIONS:
            dx, dy = DIRECTIONS[first]
            ev = game.move_player(dx, dy)
            if not ev['ok']:
                print(ev['message'])
            continue
        print('unknown command')


if __name__ == '__main__':
    main()
