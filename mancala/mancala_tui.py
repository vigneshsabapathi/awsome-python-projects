"""Mancala — Textual TUI.

A modern terminal UI for Kalah Mancala. Each cell renders as ``[N]``.

Bindings:
    1-6                play pit 1..6 (current player)
    shift+1..shift+6   force a pit for P2 (when in 2P mode and it's P2's turn,
                       just press 1-6; shift bindings are aliases for clarity)
    n                  new game
    m                  cycle mode
    a                  toggle Awari (no extra-turn rule)
    Ctrl+Q             quit

Run:
    uv run python mancala/mancala_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from mancala import (
    DIFFICULTY_DEPTH,
    P1_PITS,
    P1_STORE,
    P2_PITS,
    P2_STORE,
    PLAYER_1,
    PLAYER_2,
    Board,
    ai_move,
    other,
)

MODES = ['2P', 'AI Easy', 'AI Medium', 'AI Hard', 'AI Expert']


class MancalaApp(App):
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

    #awari-chip {
        padding: 0 1;
        margin: 0 1;
        background: #1e293b;
        color: #cbd5e1;
        height: 1;
    }

    .awari-active {
        background: #f59e0b;
        color: #0f172a;
        text-style: bold;
    }

    #board-frame {
        border: tall #7c2d12;
        background: #7c2d12;
        padding: 1 2;
        width: auto;
        height: auto;
    }

    .row {
        height: 1;
        width: auto;
    }

    .cell {
        width: 5;
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: #fde68a;
    }

    .cell-p1 { color: #fca5a5; }
    .cell-p2 { color: #93c5fd; }
    .cell-empty { color: #78350f; }
    .cell-legal { color: #34d399; text-style: bold; }
    .cell-last  { color: #fde68a; background: #422006; text-style: bold; }

    .store {
        width: 8;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: #fcd34d;
        color: #1c1917;
    }

    .store-active { background: #34d399; }

    #pit-labels-top, #pit-labels-bottom {
        text-align: center;
        color: #64748b;
    }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-p1   { color: #fca5a5; text-style: bold; }
    .status-p2   { color: #93c5fd; text-style: bold; }
    .status-info { color: #cbd5e1; }
    .status-win  { color: #34d399; text-style: bold; }
    .status-draw { color: #cbd5e1; text-style: bold; }
    """

    BINDINGS = [
        Binding('1', 'play(1)', 'Pit 1'),
        Binding('2', 'play(2)', 'Pit 2'),
        Binding('3', 'play(3)', 'Pit 3'),
        Binding('4', 'play(4)', 'Pit 4'),
        Binding('5', 'play(5)', 'Pit 5'),
        Binding('6', 'play(6)', 'Pit 6'),
        # Shift+digit aliases (same effect — current player plays).
        Binding('shift+1', 'play(1)', show=False),
        Binding('shift+2', 'play(2)', show=False),
        Binding('shift+3', 'play(3)', show=False),
        Binding('shift+4', 'play(4)', show=False),
        Binding('shift+5', 'play(5)', show=False),
        Binding('shift+6', 'play(6)', show=False),
        Binding('n', 'new_game', 'New'),
        Binding('m', 'cycle_mode', 'Mode'),
        Binding('a', 'toggle_awari', 'Awari'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Mancala'

    def __init__(self) -> None:
        super().__init__()
        self.board = Board()
        self.current: int = PLAYER_1
        self.game_over: bool = False
        self.ai_busy: bool = False
        self.mode_idx: int = 0
        self.awari: bool = False
        self.last_cell: int = -1

    # -- Compose ------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MANCALA', id='title')
        yield Static('1-6 play · n new · m mode · a awari · Ctrl+Q quit',
                     id='subtitle')

        with Horizontal(id='mode-row'):
            for i, name in enumerate(MODES):
                yield Static(name, classes='mode-chip', id=f'mode-{i}')
            yield Static('Awari OFF', id='awari-chip')

        # P2 pits 1..6 from P2's view = internal indices 12..7 left-to-right.
        with Vertical(id='board-frame'):
            yield Static(
                '       ' + '   '.join(str(i + 1) for i in range(6)),
                id='pit-labels-top',
            )
            with Horizontal(classes='row', id='top-row'):
                yield Static('  P2  ', classes='store',
                             id=f'store-{P2_STORE}')
                for pit in reversed(P2_PITS):
                    yield Static('[ 0]', classes='cell',
                                 id=f'cell-{pit}')
                yield Static('      ', classes='cell')  # spacer
            with Horizontal(classes='row', id='bot-row'):
                yield Static('      ', classes='cell')  # spacer
                for pit in P1_PITS:
                    yield Static('[ 0]', classes='cell',
                                 id=f'cell-{pit}')
                yield Static('  P1  ', classes='store',
                             id=f'store-{P1_STORE}')
            yield Static(
                '       ' + '   '.join(str(i + 1) for i in range(6)),
                id='pit-labels-bottom',
            )

        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_mode_chips()
        self._new_game()

    # -- State helpers ------------------------------------------------------

    def _is_ai_mode(self) -> bool:
        return MODES[self.mode_idx].startswith('AI')

    def _ai_depth(self) -> int:
        m = MODES[self.mode_idx].lower()
        if 'easy' in m:
            return DIFFICULTY_DEPTH['easy']
        if 'medium' in m:
            return DIFFICULTY_DEPTH['medium']
        if 'expert' in m:
            return DIFFICULTY_DEPTH['expert']
        return DIFFICULTY_DEPTH['hard']

    def _refresh_mode_chips(self) -> None:
        for i in range(len(MODES)):
            chip = self.query_one(f'#mode-{i}', Static)
            if i == self.mode_idx:
                chip.set_classes('mode-chip mode-active')
            else:
                chip.set_classes('mode-chip')
        awari_chip = self.query_one('#awari-chip', Static)
        awari_chip.update(f'Awari {"ON " if self.awari else "OFF"}')
        awari_chip.set_classes(
            'awari-active' if self.awari else ''
        )

    def _new_game(self) -> None:
        self.board = Board(awari=self.awari)
        self.current = PLAYER_1
        self.game_over = False
        self.ai_busy = False
        self.last_cell = -1
        self._refresh_board()
        self._update_status()

    def _refresh_board(self) -> None:
        legal = set(self.board.legal_moves(self.current)) if not self.game_over else set()
        for pit in (*P1_PITS, *P2_PITS):
            cell = self.query_one(f'#cell-{pit}', Static)
            n = self.board.pits[pit]
            cell.update(f'[{n:>2}]')
            classes = ['cell']
            if pit == self.last_cell:
                classes.append('cell-last')
            elif pit in legal:
                classes.append('cell-legal')
            elif n == 0:
                classes.append('cell-empty')
            elif pit in P1_PITS:
                classes.append('cell-p1')
            else:
                classes.append('cell-p2')
            cell.set_classes(' '.join(classes))
        # Stores.
        s1 = self.query_one(f'#store-{P1_STORE}', Static)
        s1.update(f'P1\n{self.board.pits[P1_STORE]:>2}')
        s2 = self.query_one(f'#store-{P2_STORE}', Static)
        s2.update(f'P2\n{self.board.pits[P2_STORE]:>2}')
        # Highlight active store.
        s1.set_classes('store store-active' if self.current == PLAYER_1
                       and not self.game_over else 'store')
        s2.set_classes('store store-active' if self.current == PLAYER_2
                       and not self.game_over else 'store')

    def _update_status(self) -> None:
        if self.game_over:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            text = 'AI to move...'
            kind = 'info'
        else:
            text = f'Player {self.current} to move'
            kind = f'p{self.current}'
        self._set_status(text, kind)

    def _set_status(self, text: str, kind: str) -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    # -- Actions ------------------------------------------------------------

    def action_new_game(self) -> None:
        self._new_game()

    def action_cycle_mode(self) -> None:
        self.mode_idx = (self.mode_idx + 1) % len(MODES)
        self._refresh_mode_chips()
        self._new_game()

    def action_toggle_awari(self) -> None:
        self.awari = not self.awari
        self._refresh_mode_chips()
        self._new_game()

    def action_play(self, label: int) -> None:
        if self.game_over or self.ai_busy:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        if self.current == PLAYER_1:
            pit = label - 1
        else:
            # P2's pits are mirrored: label 1 -> internal index 12.
            pit = 12 - (label - 1)
        if pit not in self.board.legal_moves(self.current):
            self._set_status(f'Pit {label} is empty — try another.', 'info')
            return
        self._play_move(pit)

    # -- Move logic ---------------------------------------------------------

    def _play_move(self, pit: int) -> None:
        result = self.board.move(pit)
        self.last_cell = result['last']
        self._refresh_board()

        if result['capture']:
            cap = result['capture']
            self._set_status(
                f'Capture! P{result["player"]} +{cap["stones"]} to store.',
                'win' if result['player'] == PLAYER_1 else 'p2',
            )

        if result['game_over']:
            self._end_game(result)
            return

        self.current = result['next_player']
        # Refresh again so legal-move highlighting follows the new player.
        self._refresh_board()

        if result['free_turn'] and not result.get('capture'):
            self._set_status(
                f'Free turn! Player {self.current} again.',
                f'p{self.current}',
            )
        elif not result.get('capture'):
            self._update_status()

        if self._is_ai_mode() and self.current == PLAYER_2:
            self._schedule_ai()

    def _schedule_ai(self) -> None:
        self.ai_busy = True
        self.set_timer(0.18, self._do_ai_move)

    def _do_ai_move(self) -> None:
        if self.game_over:
            self.ai_busy = False
            return
        depth = self._ai_depth()
        pit = ai_move(self.board, PLAYER_2, depth=depth)
        self.ai_busy = False
        self._play_move(pit)

    # -- Endgame ------------------------------------------------------------

    def _end_game(self, result: dict) -> None:
        self.game_over = True
        self._refresh_board()
        winner = result['winner']
        s1 = self.board.score(PLAYER_1)
        s2 = self.board.score(PLAYER_2)
        if winner == 0:
            self._set_status(f"Draw {s1}–{s2}. Press n for new.", 'draw')
        elif self._is_ai_mode() and winner == PLAYER_2:
            self._set_status(f'AI wins {s2}–{s1}. Press n for new.', 'win')
        else:
            self._set_status(
                f'Player {winner} wins {max(s1, s2)}–{min(s1, s2)}. '
                f'Press n for new.',
                'win',
            )


if __name__ == '__main__':
    MancalaApp().run()
