# Hungry Robots

A grid-chase game. You are `@` on a `45 x 20` grid surrounded by hungry robots (`R`) that step toward you one cell per turn (Chebyshev pursuit — eight directions, including diagonals). Two robots that step onto the same cell flatten each other into a wreck (`#`); any robot that walks onto an existing wreck dies the same way. You win by surviving until every robot is scrap.

| Version | File | Stack |
|---------|------|-------|
| CLI | `hungry_robots.py` | stdlib |
| Desktop GUI | `hungry_robots_gui.py` | CustomTkinter + tk.Canvas |
| Terminal UI | `hungry_robots_tui.py` | Textual |

## Run

```bash
uv run python hungry_robots/hungry_robots.py
uv run python hungry_robots/hungry_robots_gui.py
uv run python hungry_robots/hungry_robots_tui.py
```

## Controls

Numpad / vim-style 8-direction movement is shared across all three frontends.

| Action | TUI / GUI | CLI |
|--------|-----------|-----|
| Move NW / N / NE | `y u` / `q w e` (or `k` for N) | `q w e` |
| Move W / E       | `h l` / `a d` | `a d` |
| Move SW / S / SE | `b j n` / `z x c` | `z x c` |
| Stand still      | `s` | `s` |
| Wait out the round | `w` | `W` |
| Teleport (random) | `t` | `t` |
| Safe teleport     | `T` | `T` |
| New / next level  | `N` (TUI), New button (GUI) | `n` |
| Quit              | `Ctrl+Q` (TUI) | `Q` |

## Twists

Two extras layered on top of the classic rules:

1. **Safe teleport** — a rare power-up that lands you in an empty cell with no adjacent robots. If no such cell exists it falls back to an unsafe teleport (rather than wasting the charge entirely). Starts with one charge; an extra is granted every other level.
2. **Level progression** — clearing a board advances you to the next level with three more robots and one more teleport charge. Press *New / Next* (or `N`) to advance.

## Architecture

`hungry_robots.py` owns all game logic — both `Game` and a small CLI loop. The GUI and TUI import:

- `Game(width, height, n_robots)` — board state + entity bookkeeping
- `Game.move_player(dx, dy)` — one player step plus one robot turn
- `Game.teleport()` / `Game.safe_teleport()` — random repositioning
- `Game.wait_until_safe_or_dead()` — fast-forward the robot phase
- `Game.is_won()` / `Game.is_lost()` — terminal-state checks
- `Game.cell(x, y)` — glyph at a position, used by every renderer

Each call returns a small `dict` (`{'ok', 'message', 'killed', 'won', 'lost'}`) so the frontends can flash status without re-deriving it.

## Notes

- Robots use **Chebyshev distance** (one step closes both axes simultaneously), so corner play matters: a robot directly NE of the player closes the gap in a single diagonal move.
- Wrecks are static — they kill any robot that steps onto them and they also block the player. That makes them strategic terrain: lure two robots into the same cell, or one robot into an existing wreck, to thin the herd without spending a teleport.
- The `wait_until_safe_or_dead` loop is bounded by `width * height` to guarantee termination even in pathological configurations.
