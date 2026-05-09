"""Royal Game of Ur — Textual TUI.

A modern terminal UI for the Royal Game of Ur. The board renders as a
3-row H-shape with `[N]` cells, rosettes marked with ``*``, and pieces
drawn as letters X/O.

Bindings:
    r              roll dice
    1-7            select piece (after rolling)
    n              new game
    m              cycle mode (2P / AI Easy / AI Medium / AI Hard)
    f              toggle Finkel rules
    Ctrl+Q         quit

Run:
    uv run python ur/ur_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from ur import (
    DIFFICULTY_DEPTH,
    FINISH,
    PIECES_PER_PLAYER,
    PLAYER_1,
    PLAYER_2,
    ROSETTES,
    SHARED_RANGE,
    START,
    Board,
    ai_move,
    other,
    roll,
)

MODES = ['2P', 'AI Easy', 'AI Medium', 'AI Hard']

# Visual layout: each player path 1..14 mapped to (row, col) tuples.
# We use the same H-shape as the GUI (3 rows, 8 cols).
PRIVATE_TOP_COLS = {4: 0, 3: 1, 2: 2, 1: 3, 14: 6, 13: 7}
SHARED_COLS = {5: 0, 6: 1, 7: 2, 8: 3, 9: 4, 10: 5, 11: 6, 12: 7}


class UrApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #mode-row {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .mode-chip {
        padding: 0 1;
        margin: 0 1;
        background: #1e293b;
        color: #cbd5e1;
        height: 1;
    }

    .mode-active {
        background: #38bdf8;
        color: #0f172a;
        text-style: bold;
    }

    #finkel-chip {
        padding: 0 1;
        margin: 0 1;
        background: #1e293b;
        color: #cbd5e1;
        height: 1;
    }

    .finkel-active {
        background: #f59e0b;
        color: #0f172a;
        text-style: bold;
    }

    #board-frame {
        border: tall #7c2d12;
        background: #1c1917;
        padding: 1 2;
        width: auto;
        height: auto;
    }

    .row {
        height: 1;
        width: auto;
    }

    .cell {
        width: 6;
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: #fde68a;
    }

    .cell-rosette { color: #fb923c; text-style: bold; }
    .cell-shared  { color: #fcd34d; }
    .cell-empty   { color: #57534e; }
    .cell-p1      { color: #fca5a5; text-style: bold; }
    .cell-p2      { color: #93c5fd; text-style: bold; }
    .cell-last    { color: #fde68a; background: #422006; text-style: bold; }
    .cell-legal   { color: #34d399; text-style: bold; }

    .pile {
        width: 24;
        height: 1;
        text-style: bold;
    }

    .pile-p1 { color: #fca5a5; }
    .pile-p2 { color: #93c5fd; }

    #dice-row {
        height: 1;
        align-horizontal: center;
        margin-top: 1;
    }

    #dice {
        text-align: center;
        text-style: bold;
        color: #fde68a;
        width: auto;
    }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-p1   { color: #fca5a5; text-style: bold; }
    .status-p2   { color: #93c5fd; text-style: bold; }
    .status-info { color: #cbd5e1; }
    .status-win  { color: #34d399; text-style: bold; }
    .status-warn { color: #fbbf24; }
    """

    BINDINGS = [
        Binding('r', 'roll_dice', 'Roll'),
        Binding('1', 'select(1)', 'P1'),
        Binding('2', 'select(2)', 'P2'),
        Binding('3', 'select(3)', 'P3'),
        Binding('4', 'select(4)', 'P4'),
        Binding('5', 'select(5)', 'P5'),
        Binding('6', 'select(6)', 'P6'),
        Binding('7', 'select(7)', 'P7'),
        Binding('n', 'new_game', 'New'),
        Binding('m', 'cycle_mode', 'Mode'),
        Binding('f', 'toggle_finkel', 'Finkel'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Royal Game of Ur'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.board = Board()
        self.current: int = PLAYER_1
        self.current_dice: int | None = None
        self.has_rolled: bool = False
        self.game_over: bool = False
        self.ai_busy: bool = False
        self.mode_idx: int = 0
        self.finkel: bool = True
        self.last_to: int = -1

    # -- Compose ----------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('ROYAL GAME OF UR', id='title')
        yield Static('r roll · 1-7 select · n new · m mode · f Finkel · Ctrl+Q quit',
                     id='subtitle')

        with Horizontal(id='mode-row'):
            for i, name in enumerate(MODES):
                yield Static(name, classes='mode-chip', id=f'mode-{i}')
            yield Static('Finkel ON', id='finkel-chip')

        with Vertical(id='board-frame'):
            # P2 start pile
            yield Static('P2 start: -------', classes='pile pile-p2',
                         id='pile-p2-start')
            # P2 row (top): squares 4 3 2 1 _ _ 14 13
            with Horizontal(classes='row'):
                yield from self._make_top_row(PLAYER_2)
            # Shared row
            with Horizontal(classes='row'):
                yield from self._make_shared_row()
            # P1 row (bottom): squares 4 3 2 1 _ _ 14 13
            with Horizontal(classes='row'):
                yield from self._make_top_row(PLAYER_1)
            yield Static('P1 start: -------', classes='pile pile-p1',
                         id='pile-p1-start')
            # Finish counts.
            yield Static('P1 finish: 0/7   P2 finish: 0/7',
                         classes='pile pile-p1',
                         id='finish-line')

        with Horizontal(id='dice-row'):
            yield Static('Dice: -', id='dice')

        yield Static('', id='status', classes='status-info')
        yield Footer()

    def _make_top_row(self, player: int):
        # Squares ordered visually left-to-right: 4 3 2 1 (gap) (gap) 14 13
        for col in range(8):
            sq = None
            for s, c in PRIVATE_TOP_COLS.items():
                if c == col:
                    sq = s
                    break
            if sq is None:
                yield Static('      ', classes='cell cell-empty')
            else:
                yield Static('[ ]', classes='cell',
                             id=f'cell-p{player}-{sq}')

    def _make_shared_row(self):
        for col in range(8):
            sq = None
            for s, c in SHARED_COLS.items():
                if c == col:
                    sq = s
                    break
            if sq is None:
                yield Static('      ', classes='cell cell-empty')
            else:
                yield Static('[ ]', classes='cell',
                             id=f'cell-shared-{sq}')

    # -- Mount ------------------------------------------------------------

    def on_mount(self) -> None:
        self._refresh_chips()
        self._new_game()

    # -- Helpers ----------------------------------------------------------

    def _is_ai_mode(self) -> bool:
        return MODES[self.mode_idx].startswith('AI')

    def _ai_depth(self) -> int:
        m = MODES[self.mode_idx].lower()
        if 'easy' in m:
            return DIFFICULTY_DEPTH['easy']
        if 'hard' in m:
            return DIFFICULTY_DEPTH['hard']
        return DIFFICULTY_DEPTH['medium']

    def _refresh_chips(self) -> None:
        for i in range(len(MODES)):
            chip = self.query_one(f'#mode-{i}', Static)
            if i == self.mode_idx:
                chip.set_classes('mode-chip mode-active')
            else:
                chip.set_classes('mode-chip')
        f = self.query_one('#finkel-chip', Static)
        f.update(f'Finkel {"ON " if self.finkel else "OFF"}')
        f.set_classes('finkel-active' if self.finkel else '')

    def _new_game(self) -> None:
        self.board = Board(finkel=self.finkel)
        self.current = PLAYER_1
        self.current_dice = None
        self.has_rolled = False
        self.game_over = False
        self.ai_busy = False
        self.last_to = -1
        self._refresh_board()
        self._update_dice_display()
        self._update_status()

    def _refresh_board(self) -> None:
        legal = (set(self.board.legal_moves(self.current, self.current_dice))
                 if (self.has_rolled and self.current_dice
                     and not self.game_over) else set())
        # Player rows: each cell only renders the *current* player's pieces
        # on private squares.
        for player in (PLAYER_1, PLAYER_2):
            for sq in (1, 2, 3, 4, 13, 14):
                cell = self.query_one(f'#cell-p{player}-{sq}', Static)
                pieces = self.board.at_square_pieces(player, sq)
                self._set_cell(cell, player, sq, pieces, legal)
        # Shared row: piece can be either player's.
        for sq in range(5, 13):
            cell = self.query_one(f'#cell-shared-{sq}', Static)
            p1_at = self.board.at_square_pieces(PLAYER_1, sq)
            p2_at = self.board.at_square_pieces(PLAYER_2, sq)
            if p1_at:
                self._set_cell(cell, PLAYER_1, sq, p1_at, legal)
            elif p2_at:
                self._set_cell(cell, PLAYER_2, sq, p2_at, legal)
            else:
                self._set_cell(cell, None, sq, [], legal)
        # Piles.
        p1_start = sum(1 for p in self.board.pieces[PLAYER_1] if p == START)
        p2_start = sum(1 for p in self.board.pieces[PLAYER_2] if p == START)
        # Show piece-index labels for legal moves so user knows which keys.
        p1_pile = self.query_one('#pile-p1-start', Static)
        p2_pile = self.query_one('#pile-p2-start', Static)
        p1_pile.update(self._render_pile(PLAYER_1, legal))
        p2_pile.update(self._render_pile(PLAYER_2, legal))
        # Finish line.
        s1 = self.board.finished_count(PLAYER_1)
        s2 = self.board.finished_count(PLAYER_2)
        self.query_one('#finish-line', Static).update(
            f'P1 finish: {s1}/{PIECES_PER_PLAYER}   '
            f'P2 finish: {s2}/{PIECES_PER_PLAYER}'
        )

    def _set_cell(self, cell: Static, player: int | None, sq: int,
                  pieces: list[int], legal: set[int]) -> None:
        ros_marker = '*' if sq in ROSETTES else ' '
        if pieces:
            piece_idx = pieces[0]
            label = 'X' if player == PLAYER_1 else 'O'
            text = f'[{label}{piece_idx + 1}{ros_marker}]'
        else:
            text = f'[ {sq:>2}{ros_marker}]'
        cell.update(text)
        # Class.
        classes = ['cell']
        is_current_legal_target = (
            self.has_rolled and self.current_dice
            and not self.game_over
            and player == self.current
            and pieces
            and pieces[0] in legal
        )
        if sq == self.last_to:
            classes.append('cell-last')
        elif is_current_legal_target:
            classes.append('cell-legal')
        elif sq in ROSETTES and not pieces:
            classes.append('cell-rosette')
        elif sq in SHARED_RANGE and not pieces:
            classes.append('cell-shared')
        elif not pieces:
            classes.append('cell-empty')
        elif player == PLAYER_1:
            classes.append('cell-p1')
        else:
            classes.append('cell-p2')
        cell.set_classes(' '.join(classes))

    def _render_pile(self, player: int, legal: set[int]) -> str:
        pieces = self.board.pieces[player]
        parts = []
        for i, p in enumerate(pieces):
            if p == START:
                marker = 'X' if player == PLAYER_1 else 'O'
                if i in legal and player == self.current:
                    parts.append(f'[{marker}{i + 1}]')
                else:
                    parts.append(f' {marker}{i + 1} ')
            elif p == FINISH:
                parts.append(' ** ')
            else:
                parts.append(f'   ')
        prefix = f'P{player} pieces: '
        return prefix + ''.join(parts)

    def _update_dice_display(self) -> None:
        d = self.query_one('#dice', Static)
        if self.current_dice is None:
            d.update('Dice: -      [ ][ ][ ][ ]')
        else:
            slots = self._dice_pattern(self.current_dice)
            dots = ''.join('[*]' if s else '[ ]' for s in slots)
            d.update(f'Dice: {self.current_dice}      {dots}')

    def _dice_pattern(self, value: int) -> list[int]:
        slots = [0, 0, 0, 0]
        idxs = list(range(4))
        self.rng.shuffle(idxs)
        for i in idxs[:value]:
            slots[i] = 1
        return slots

    def _update_status(self) -> None:
        if self.game_over:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            who = 'AI'
            kind = 'p2'
        else:
            who = f'Player {self.current}'
            kind = f'p{self.current}'
        if not self.has_rolled:
            self._set_status(f"{who}'s turn — press r to roll", kind)
        else:
            self._set_status(
                f"{who} rolled {self.current_dice} — press 1-7 to move",
                kind,
            )

    def _set_status(self, text: str, kind: str) -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    # -- Actions ----------------------------------------------------------

    def action_new_game(self) -> None:
        self._new_game()

    def action_cycle_mode(self) -> None:
        self.mode_idx = (self.mode_idx + 1) % len(MODES)
        self._refresh_chips()
        self._new_game()

    def action_toggle_finkel(self) -> None:
        self.finkel = not self.finkel
        self._refresh_chips()
        self._new_game()

    def action_roll_dice(self) -> None:
        if self.game_over or self.ai_busy:
            return
        if self.has_rolled:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        self._do_roll()

    def _do_roll(self) -> None:
        self.current_dice = roll(self.rng)
        self.has_rolled = True
        self._update_dice_display()
        if (self.current_dice == 0
                or not self.board.has_any_legal_move(self.current,
                                                    self.current_dice)):
            self._set_status(
                f"Player {self.current} rolled {self.current_dice} — "
                f"no moves, turn forfeit. (press r/n to continue)",
                'warn',
            )
            self.set_timer(0.9, self._end_turn_no_move)
            return
        self._refresh_board()
        self._update_status()

    def _end_turn_no_move(self) -> None:
        self.current = other(self.current)
        self.has_rolled = False
        self.current_dice = None
        self._update_dice_display()
        self._refresh_board()
        self._update_status()
        if (not self.game_over and self._is_ai_mode()
                and self.current == PLAYER_2):
            self._schedule_ai()

    def action_select(self, label: int) -> None:
        if self.game_over or self.ai_busy:
            return
        if not self.has_rolled or self.current_dice is None:
            self._set_status('Roll the dice first (r).', 'warn')
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        idx = label - 1
        if not (0 <= idx < PIECES_PER_PLAYER):
            return
        legal = self.board.legal_moves(self.current, self.current_dice)
        if idx not in legal:
            self._set_status(f'Piece {label} cannot move with this roll.',
                             'warn')
            return
        self._play_move(idx)

    def _play_move(self, piece_idx: int) -> None:
        result = self.board.move(self.current, piece_idx, self.current_dice)
        self.last_to = result['to']

        if result['game_over']:
            self._refresh_board()
            self.game_over = True
            w = result['winner']
            if self._is_ai_mode() and w == PLAYER_2:
                self._set_status(
                    f'AI wins! Press n for a new game.', 'win')
            else:
                self._set_status(
                    f'Player {w} wins! Press n for a new game.', 'win')
            return

        if result['free_turn']:
            self.has_rolled = False
            self.current_dice = None
            self._update_dice_display()
            self._refresh_board()
            self._set_status('Rosette! Bonus turn — press r.', 'win')
            if self._is_ai_mode() and self.current == PLAYER_2:
                self._schedule_ai()
            return

        # Pass turn.
        self.current = result['next_player']
        self.has_rolled = False
        self.current_dice = None
        self._update_dice_display()
        self._refresh_board()
        self._update_status()
        if self._is_ai_mode() and self.current == PLAYER_2:
            self._schedule_ai()

    # -- AI ---------------------------------------------------------------

    def _schedule_ai(self) -> None:
        self.ai_busy = True
        self.set_timer(0.25, self._do_ai_turn)

    def _do_ai_turn(self) -> None:
        if self.game_over:
            self.ai_busy = False
            return
        # Roll for AI.
        self.current_dice = roll(self.rng)
        self.has_rolled = True
        self._update_dice_display()
        if (self.current_dice == 0
                or not self.board.has_any_legal_move(self.current,
                                                    self.current_dice)):
            self._set_status(
                f'AI rolled {self.current_dice} — no moves, forfeit.', 'warn')
            self.ai_busy = False
            self.set_timer(0.9, self._end_turn_no_move)
            return
        depth = self._ai_depth()
        idx = ai_move(self.board, PLAYER_2, self.current_dice, depth=depth)
        self.ai_busy = False
        if idx < 0:
            self.set_timer(0.5, self._end_turn_no_move)
            return
        self._play_move(idx)


if __name__ == '__main__':
    UrApp().run()
