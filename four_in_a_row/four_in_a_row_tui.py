"""Four in a Row — Textual TUI.

A modern terminal UI for Connect Four. Drop discs by pressing 1-7, toggle
between human-vs-human and human-vs-AI mode, and start a fresh game with N.

Run:
    uv run python four_in_a_row/four_in_a_row_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from four_in_a_row import (
    COLS,
    DIFFICULTY_DEPTH,
    PLAYER_1,
    PLAYER_2,
    ROWS,
    Board,
    ai_move,
    other,
)

EMPTY_GLYPH = '·'
P1_GLYPH = '●'
P2_GLYPH = '○'

MODES = ['2P', 'AI Easy', 'AI Medium', 'AI Hard']


class FourInARowApp(App):
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

    #col-numbers {
        text-align: center;
        color: #64748b;
        padding-bottom: 1;
    }

    #board-frame {
        border: tall #1e3a8a;
        background: #1e3a8a;
        padding: 1 2;
        width: auto;
        height: auto;
    }

    .board-row {
        height: 1;
        width: auto;
    }

    .cell {
        width: 3;
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: #475569;
    }

    .cell-p1 { color: #ef4444; }
    .cell-p2 { color: #facc15; }
    .cell-win-p1 { color: #ef4444; background: #422006; text-style: bold; }
    .cell-win-p2 { color: #facc15; background: #422006; text-style: bold; }
    .cell-preview-p1 { color: #ef4444; text-style: bold; }
    .cell-preview-p2 { color: #facc15; text-style: bold; }

    #status {
        text-align: center;
        padding: 1;
    }

    .status-p1   { color: #ef4444; text-style: bold; }
    .status-p2   { color: #facc15; text-style: bold; }
    .status-info { color: #cbd5e1; }
    .status-win  { color: #34d399; text-style: bold; }
    .status-draw { color: #cbd5e1; text-style: bold; }
    """

    BINDINGS = [
        Binding('1', 'drop(1)', 'Col 1'),
        Binding('2', 'drop(2)', 'Col 2'),
        Binding('3', 'drop(3)', 'Col 3'),
        Binding('4', 'drop(4)', 'Col 4'),
        Binding('5', 'drop(5)', 'Col 5'),
        Binding('6', 'drop(6)', 'Col 6'),
        Binding('7', 'drop(7)', 'Col 7'),
        Binding('n', 'new_game', 'New'),
        Binding('m', 'cycle_mode', 'Mode'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Four in a Row'

    def __init__(self) -> None:
        super().__init__()
        self.board = Board()
        self.current: int = PLAYER_1
        self.game_over: bool = False
        self.ai_busy: bool = False
        self.mode_idx: int = 0  # index into MODES
        self._win_cells: list[tuple[int, int]] = []

    # -- Compose -------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('FOUR IN A ROW', id='title')
        yield Static('Press 1-7 to drop · n: new · m: mode · Ctrl+Q: quit',
                     id='subtitle')
        with Horizontal(id='mode-row'):
            for i, name in enumerate(MODES):
                yield Static(name, classes='mode-chip', id=f'mode-{i}')
        yield Static(' '.join(f' {c + 1} ' for c in range(COLS)),
                     id='col-numbers')
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

    # -- State helpers -------------------------------------------------------

    def _is_ai_mode(self) -> bool:
        return MODES[self.mode_idx].startswith('AI')

    def _ai_depth(self) -> int:
        m = MODES[self.mode_idx].lower()
        if 'easy' in m:
            return DIFFICULTY_DEPTH['easy']
        if 'medium' in m:
            return DIFFICULTY_DEPTH['medium']
        return DIFFICULTY_DEPTH['hard']

    def _refresh_mode_chips(self) -> None:
        for i in range(len(MODES)):
            chip = self.query_one(f'#mode-{i}', Static)
            if i == self.mode_idx:
                chip.set_classes('mode-chip mode-active')
            else:
                chip.set_classes('mode-chip')

    def _new_game(self) -> None:
        self.board = Board()
        self.current = PLAYER_1
        self.game_over = False
        self.ai_busy = False
        self._win_cells = []
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.query_one(f'#cell-{r}-{c}', Static)
                cell.update(EMPTY_GLYPH)
                cell.set_classes('cell')
        self._update_status()

    def _update_status(self) -> None:
        if self.game_over:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            text = 'AI to move...'
            kind = 'info'
        else:
            text = f'Player {self.current} to move'
            kind = f'p{self.current}'
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def _set_status(self, text: str, kind: str) -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    def _glyph_for(self, player: int) -> str:
        return P1_GLYPH if player == PLAYER_1 else P2_GLYPH

    def _render_disc(self, row: int, col: int, player: int) -> None:
        cell = self.query_one(f'#cell-{row}-{col}', Static)
        cell.update(self._glyph_for(player))
        cell.set_classes(f'cell cell-p{player}')

    def _highlight_win(self) -> None:
        line = self.board.winning_line()
        if not line:
            return
        winner = self.board.winner()
        for r, c in line:
            cell = self.query_one(f'#cell-{r}-{c}', Static)
            cell.set_classes(f'cell cell-win-p{winner}')

    # -- Actions -------------------------------------------------------------

    def action_new_game(self) -> None:
        self._new_game()

    def action_cycle_mode(self) -> None:
        self.mode_idx = (self.mode_idx + 1) % len(MODES)
        self._refresh_mode_chips()
        self._new_game()

    def action_drop(self, col_1based: int) -> None:
        if self.game_over or self.ai_busy:
            return
        if self._is_ai_mode() and self.current == PLAYER_2:
            return
        self._play_move(col_1based - 1)

    # -- Move logic ----------------------------------------------------------

    def _play_move(self, col: int) -> None:
        row = self.board.next_open_row(col)
        if row is None:
            self._set_status('Column is full — try another.', 'info')
            return
        self.board.drop(col, self.current)
        self._render_disc(row, col, self.current)

        win = self.board.winner()
        if win is not None:
            self._end_game_win(win)
            return
        if self.board.is_full():
            self._end_game_draw()
            return

        self.current = other(self.current)
        self._update_status()

        if self._is_ai_mode() and self.current == PLAYER_2:
            self._schedule_ai()

    def _schedule_ai(self) -> None:
        self.ai_busy = True
        # Defer so the UI repaints between the human move and the AI move.
        self.set_timer(0.15, self._do_ai_move)

    def _do_ai_move(self) -> None:
        if self.game_over:
            self.ai_busy = False
            return
        depth = self._ai_depth()
        col = ai_move(self.board, PLAYER_2, depth=depth)
        self.ai_busy = False
        self._play_move(col)

    # -- Endgame -------------------------------------------------------------

    def _end_game_win(self, winner: int) -> None:
        self.game_over = True
        self._highlight_win()
        if self._is_ai_mode() and winner == PLAYER_2:
            text = 'AI wins! Press n for a new game.'
        else:
            text = f'Player {winner} wins! Press n for a new game.'
        self._set_status(text, 'win')

    def _end_game_draw(self) -> None:
        self.game_over = True
        self._set_status("It's a draw. Press n for a new game.", 'draw')


if __name__ == '__main__':
    FourInARowApp().run()
