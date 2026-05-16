"""Flooder — Textual TUI.

Dark Tailwind-palette terminal UI for the flood-fill puzzle game.

Bindings
--------
1-6     Pick color / flood
H       Greedy hint
N       New game
Ctrl+Q  Quit

Run:
    uv run python flooder/flooder_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from flooder import DEFAULT_COLORS, DEFAULT_HEIGHT, DEFAULT_MOVES, DEFAULT_WIDTH, Game

COLOR_HEX = [
    '#ef4444',  # 0 red
    '#22c55e',  # 1 green
    '#eab308',  # 2 yellow
    '#3b82f6',  # 3 blue
    '#a855f7',  # 4 purple
    '#06b6d4',  # 5 cyan
]
COLOR_TEXT = [
    '#ffffff',  # red
    '#ffffff',  # green
    '#1f2937',  # yellow
    '#ffffff',  # blue
    '#ffffff',  # purple
    '#1f2937',  # cyan
]
COLOR_NAMES = ['Red', 'Green', 'Yellow', 'Blue', 'Purple', 'Cyan']

# CSS uses 2-char wide cells to keep the grid proportional in the terminal
CELL_COLS = DEFAULT_WIDTH
CELL_ROWS = DEFAULT_HEIGHT


class FlooderApp(App):
    CSS = f"""
    Screen {{
        background: #0f172a;
        color: #f8fafc;
        align: center top;
        overflow: auto;
    }}

    #title {{
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 0 0 0;
    }}

    #subtitle {{
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }}

    #grid-container {{
        align-horizontal: center;
        height: auto;
        width: 100%;
        padding: 0 2;
    }}

    .grid-row {{
        height: 1;
        width: {CELL_COLS * 2};
        align-horizontal: center;
    }}

    .cell {{
        width: 2;
        height: 1;
        content-align: center middle;
    }}

    #color-buttons {{
        align-horizontal: center;
        height: 3;
        margin-top: 1;
    }}

    .color-btn {{
        width: 12;
        height: 3;
        content-align: center middle;
        margin: 0 1;
        text-style: bold;
        border: tall transparent;
    }}

    .color-btn-active {{
        border: tall white;
    }}

    #status {{
        text-align: center;
        padding: 1;
        color: #94a3b8;
        height: 3;
    }}

    .status-win   {{ color: #34d399; text-style: bold; }}
    .status-lose  {{ color: #f87171; text-style: bold; }}
    .status-hint  {{ color: #38bdf8; }}
    .status-info  {{ color: #94a3b8; }}

    #stats {{
        text-align: center;
        color: #cbd5e1;
        padding: 0 0 1 0;
    }}
    """

    BINDINGS = [
        Binding('1', 'pick(0)', 'Red'),
        Binding('2', 'pick(1)', 'Green'),
        Binding('3', 'pick(2)', 'Yellow'),
        Binding('4', 'pick(3)', 'Blue'),
        Binding('5', 'pick(4)', 'Purple'),
        Binding('6', 'pick(5)', 'Cyan'),
        Binding('h', 'hint', 'Hint'),
        Binding('n', 'new_game', 'New Game'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Flooder'

    def __init__(self) -> None:
        super().__init__()
        self._game = Game(DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_COLORS,
                          max_moves=DEFAULT_MOVES)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('FLOODER', id='title')
        yield Static('Flood the grid — capture all cells within the move limit',
                     id='subtitle')

        with Vertical(id='grid-container'):
            for r in range(CELL_ROWS):
                with Horizontal(classes='grid-row'):
                    for c in range(CELL_COLS):
                        yield Static('  ', classes='cell', id=f'cell-{r}-{c}')

        yield Static('', id='stats')

        with Horizontal(id='color-buttons'):
            for i in range(DEFAULT_COLORS):
                yield Static(
                    f'{i + 1} {COLOR_NAMES[i]}',
                    classes='color-btn',
                    id=f'cbtn-{i}',
                )

        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._apply_colors()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_pick(self, color: int) -> None:  # type: ignore[override]
        st = self._game.state()
        if st['is_won'] or st['is_lost']:
            return
        self._game.flood(color)
        self._apply_colors()

    def action_hint(self) -> None:
        hint = self._game.greedy_hint()
        self._set_status(
            f'Hint: try {hint + 1} {COLOR_NAMES[hint]}', 'hint')

    def action_new_game(self) -> None:
        self._game = Game(DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_COLORS,
                          max_moves=DEFAULT_MOVES)
        self._apply_colors()
        self._set_status('New game — pick a color!', 'info')

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _apply_colors(self) -> None:
        st = self._game.state()
        grid = st['grid']
        total = DEFAULT_WIDTH * DEFAULT_HEIGHT
        current_color = grid[0][0]

        # Update cells
        for r in range(CELL_ROWS):
            for c in range(CELL_COLS):
                widget = self.query_one(f'#cell-{r}-{c}', Static)
                ci = grid[r][c]
                widget.styles.background = COLOR_HEX[ci]

        # Highlight active color button
        for i in range(DEFAULT_COLORS):
            btn = self.query_one(f'#cbtn-{i}', Static)
            btn.styles.background = COLOR_HEX[i]
            btn.styles.color = COLOR_TEXT[i]
            if i == current_color:
                btn.add_class('color-btn-active')
            else:
                btn.remove_class('color-btn-active')

        # Stats
        self.query_one('#stats', Static).update(
            f'Moves left: {st["moves_left"]} / {self._game.max_moves}  '
            f'|  Region: {st["region_size"]}/{total} cells'
        )

        # Win/lose
        if st['is_won']:
            self._set_status(
                f'YOU WIN!  Completed in {self._game._moves_used} moves', 'win')
        elif st['is_lost']:
            self._set_status('OUT OF MOVES — press N for new game', 'lose')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')


if __name__ == '__main__':
    FlooderApp().run()
