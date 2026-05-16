"""Tic-Tac-Toe — Textual TUI.

A modern dark Tailwind-styled terminal UI for tic-tac-toe. Press 1-9 (numpad
layout) to play a cell, n for a new game, m to cycle mode, Ctrl+Q to quit.

Run:
    uv run python tic_tac_toe/tic_tac_toe_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from tic_tac_toe import (
    COLS,
    O,
    ROWS,
    X,
    Board,
    ai_move,
    other,
)

EMPTY_GLYPH = '·'
X_GLYPH = 'X'
O_GLYPH = 'O'

MODES = [
    '2P',
    'AI Easy',
    'AI Medium',
    'AI Hard',
    'AI vs AI',
    'AI Hard misère',
]


def _difficulty_for(mode: str) -> str:
    m = mode.lower()
    if 'easy' in m:
        return 'easy'
    if 'medium' in m:
        return 'medium'
    return 'hard'


def _is_misere(mode: str) -> bool:
    return 'misère' in mode or 'misere' in mode.lower()


# Numpad → (row, col): 7=top-left, 9=top-right, 1=bottom-left, 3=bottom-right.
NUMPAD: dict[int, tuple[int, int]] = {
    7: (0, 0), 8: (0, 1), 9: (0, 2),
    4: (1, 0), 5: (1, 1), 6: (1, 2),
    1: (2, 0), 2: (2, 1), 3: (2, 2),
}


class TicTacToeApp(App):
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

    #numpad-hint {
        text-align: center;
        color: #64748b;
        padding-bottom: 1;
    }

    #board-frame {
        border: tall #1e293b;
        background: #0b1220;
        padding: 1 2;
        width: auto;
        height: auto;
    }

    .board-row {
        height: 1;
        width: auto;
    }

    .cell {
        width: 5;
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: #475569;
    }

    .cell-x { color: #38bdf8; }
    .cell-o { color: #f97316; }
    .cell-win { background: #16a34a; color: #0f172a; text-style: bold; }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-x    { color: #38bdf8; text-style: bold; }
    .status-o    { color: #f97316; text-style: bold; }
    .status-info { color: #cbd5e1; }
    .status-win  { color: #34d399; text-style: bold; }
    .status-draw { color: #cbd5e1; text-style: bold; }
    """

    BINDINGS = [
        Binding('1', 'cell(1)', 'BL'),
        Binding('2', 'cell(2)', 'B'),
        Binding('3', 'cell(3)', 'BR'),
        Binding('4', 'cell(4)', 'L'),
        Binding('5', 'cell(5)', 'C'),
        Binding('6', 'cell(6)', 'R'),
        Binding('7', 'cell(7)', 'TL'),
        Binding('8', 'cell(8)', 'T'),
        Binding('9', 'cell(9)', 'TR'),
        Binding('n', 'new_game', 'New'),
        Binding('m', 'cycle_mode', 'Mode'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Tic-Tac-Toe'

    def __init__(self) -> None:
        super().__init__()
        self.board = Board()
        self.current: int = X
        self.game_over: bool = False
        self.ai_busy: bool = False
        self.mode_idx: int = 0

    # -- Compose -------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('TIC-TAC-TOE', id='title')
        yield Static(
            'Numpad: 7 8 9 / 4 5 6 / 1 2 3  ·  n: new  ·  m: mode  ·  Ctrl+Q: quit',
            id='subtitle',
        )
        with Horizontal(id='mode-row'):
            for i, name in enumerate(MODES):
                yield Static(name, classes='mode-chip', id=f'mode-{i}')
        yield Static('Three in a row wins. Perfect play always draws.',
                     id='numpad-hint')
        with Vertical(id='board-frame'):
            for r in range(ROWS):
                with Horizontal(classes='board-row', id=f'row-{r}'):
                    for c in range(COLS):
                        yield Static(EMPTY_GLYPH, classes='cell',
                                     id=f'cell-{r}-{c}')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_mode_chips()
        self._new_game()

    # -- Mode helpers --------------------------------------------------------

    def _mode(self) -> str:
        return MODES[self.mode_idx]

    def _is_ai_mode(self) -> bool:
        m = self._mode()
        return m.startswith('AI') and m != 'AI vs AI'

    def _is_ai_demo(self) -> bool:
        return self._mode() == 'AI vs AI'

    def _refresh_mode_chips(self) -> None:
        for i in range(len(MODES)):
            chip = self.query_one(f'#mode-{i}', Static)
            if i == self.mode_idx:
                chip.set_classes('mode-chip mode-active')
            else:
                chip.set_classes('mode-chip')

    def _new_game(self) -> None:
        self.board = Board()
        self.current = X
        self.game_over = False
        self.ai_busy = False
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.query_one(f'#cell-{r}-{c}', Static)
                cell.update(EMPTY_GLYPH)
                cell.set_classes('cell')
        self._update_status()

        if self._is_ai_demo():
            self.set_timer(0.4, self._do_ai_move)

    # -- Status / rendering --------------------------------------------------

    def _glyph(self, p: int) -> str:
        return X_GLYPH if p == X else O_GLYPH

    def _update_status(self) -> None:
        if self.game_over:
            return
        misere_suffix = '  [misère]' if _is_misere(self._mode()) else ''
        if self._is_ai_demo():
            text = f'AI ({self._glyph(self.current)}) to move{misere_suffix}'
            kind = 'x' if self.current == X else 'o'
        elif self._is_ai_mode() and self.current == O:
            text = f'AI to move{misere_suffix}'
            kind = 'info'
        else:
            text = f'Player {self.current} ({self._glyph(self.current)}) to move{misere_suffix}'
            kind = 'x' if self.current == X else 'o'
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def _set_status(self, text: str, kind: str) -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def _render_mark(self, row: int, col: int, player: int) -> None:
        cell = self.query_one(f'#cell-{row}-{col}', Static)
        cell.update(self._glyph(player))
        cell.set_classes('cell cell-x' if player == X else 'cell cell-o')

    def _highlight_win(self) -> None:
        line = self.board.winning_line()
        if not line:
            return
        for r, c in line:
            cell = self.query_one(f'#cell-{r}-{c}', Static)
            cell.set_classes('cell cell-win')

    # -- Actions -------------------------------------------------------------

    def action_new_game(self) -> None:
        self._new_game()

    def action_cycle_mode(self) -> None:
        self.mode_idx = (self.mode_idx + 1) % len(MODES)
        self._refresh_mode_chips()
        self._new_game()

    def action_cell(self, n: int) -> None:
        if self.game_over or self.ai_busy:
            return
        if self._is_ai_demo():
            return
        if self._is_ai_mode() and self.current == O:
            return
        rc = NUMPAD.get(n)
        if rc is None:
            return
        row, col = rc
        if self.board.grid[row][col] != 0:
            self._set_status('Cell taken — try another.', 'info')
            return
        self._play_move(row, col, self.current)

    # -- Move logic ----------------------------------------------------------

    def _play_move(self, row: int, col: int, player: int) -> None:
        if not self.board.play(row, col, player):
            return
        self._render_mark(row, col, player)

        state = self.board.state()
        if state != 'in_progress':
            self._end_game(state)
            return
        self.current = other(self.current)
        self._update_status()

        if self._is_ai_demo():
            self.set_timer(0.4, self._do_ai_move)
        elif self._is_ai_mode() and self.current == O:
            self._schedule_ai()

    def _schedule_ai(self) -> None:
        self.ai_busy = True
        self.set_timer(0.15, self._do_ai_move)

    def _do_ai_move(self) -> None:
        if self.game_over:
            self.ai_busy = False
            return
        mode = self._mode()
        difficulty = _difficulty_for(mode)
        misere = _is_misere(mode)
        ai_player = self.current
        row, col = ai_move(self.board, ai_player,
                           difficulty=difficulty, misere=misere)
        self.ai_busy = False
        self._play_move(row, col, ai_player)

    # -- Endgame -------------------------------------------------------------

    def _end_game(self, state: str) -> None:
        self.game_over = True
        if state == 'draw':
            self._set_status("It's a draw. Press n for a new game.", 'draw')
            return

        line_player = X if state == 'x_wins' else O
        self._highlight_win()
        misere = _is_misere(self._mode())
        winner_eff = other(line_player) if misere else line_player
        glyph = self._glyph(winner_eff)
        if self._is_ai_demo():
            text = f'AI ({glyph}) wins!'
        elif self._is_ai_mode() and winner_eff == O:
            text = 'AI wins!'
        else:
            text = f'Player {winner_eff} ({glyph}) wins!'
        if misere:
            text += ' (misère)'
        self._set_status(text + ' Press n for a new game.', 'win')


if __name__ == '__main__':
    TicTacToeApp().run()
