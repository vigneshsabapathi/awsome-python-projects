"""Periodic Table - Textual TUI.

A modern terminal UI rendering the standard periodic-table grid. Arrow
keys move the cursor between elements, Enter pins the selection in the
details panel, ``/`` opens search, and Ctrl+Q quits.

Run:
    uv run python periodic_table/periodic_table_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from periodic_table import (
    CATEGORIES,
    Element,
    build_grid,
    lookup,
    search,
)


# Category colors, hex (background); foreground is white/black for contrast.
CAT_COLORS: dict[str, tuple[str, str]] = {
    'alkali':            ('#dc2626', 'white'),
    'alkaline-earth':    ('#ea580c', 'white'),
    'transition':        ('#0284c7', 'white'),
    'post-transition':   ('#475569', 'white'),
    'metalloid':         ('#0d9488', 'white'),
    'nonmetal':          ('#16a34a', 'white'),
    'halogen':           ('#0891b2', 'white'),
    'noble-gas':         ('#7c3aed', 'white'),
    'lanthanide':        ('#db2777', 'white'),
    'actinide':          ('#be185d', 'white'),
    'unknown':           ('#52525b', 'white'),
}


# A 10x18 grid; row 7 (0-indexed) is the spacer band.
GRID = build_grid()
ROWS = len(GRID)         # 10
COLS = len(GRID[0])      # 18


def _cell_id(r: int, c: int) -> str:
    return f'cell-{r}-{c}'


class PeriodicTableApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
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

    #body {
        height: 1fr;
        width: 100%;
    }

    #table {
        width: auto;
        height: auto;
        padding: 1 2;
    }

    .tablerow {
        height: 3;
        width: auto;
    }

    .cell {
        width: 5;
        height: 3;
        margin: 0 0;
        content-align: center middle;
        text-align: center;
        background: #0f172a;
        color: #f8fafc;
        border: tall #1f2937;
    }

    .cell-empty {
        background: #0f172a;
        border: blank #0f172a;
    }

    .cell-cursor {
        border: tall #f8fafc;
    }

    /* Detail panel */
    #detail {
        width: 38;
        background: #111827;
        padding: 1 2;
        border-left: tall #1f2937;
    }

    #d-chip { padding: 0 1; height: 1; margin-bottom: 1; }
    #d-symbol { text-align: center; text-style: bold; padding: 1; }
    #d-name { text-align: center; text-style: bold; }
    #d-number { text-align: center; color: #94a3b8; padding-bottom: 1; }
    .drow { height: 1; padding: 0 1; }
    .drow-key { color: #94a3b8; width: 13; }
    .drow-val { color: #f8fafc; }

    #search {
        display: none;
        margin: 0 2;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #search.visible { display: block; }
    #search:focus { border: tall #38bdf8; }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 0 1;
        height: 1;
    }
    """

    BINDINGS = [
        Binding('up', 'move(-1, 0)', 'Up', show=False),
        Binding('down', 'move(1, 0)', 'Down', show=False),
        Binding('left', 'move(0, -1)', 'Left', show=False),
        Binding('right', 'move(0, 1)', 'Right', show=False),
        Binding('enter', 'pin', 'Pin'),
        Binding('slash', 'search', 'Search'),
        Binding('escape', 'cancel_search', 'Cancel', show=False),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Periodic Table'

    def __init__(self) -> None:
        super().__init__()
        # Find Hydrogen's grid coords as the initial cursor position.
        self.cur_r = 0
        self.cur_c = 0
        self.pinned: Element | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('PERIODIC TABLE', id='title')
        yield Static('arrows: navigate  |  enter: pin  |  /: search  |  ctrl+q: quit',
                     id='subtitle')
        yield Input(placeholder='Search by name, symbol, number, or category...',
                    id='search')
        with Horizontal(id='body'):
            with Vertical(id='table'):
                for r in range(ROWS):
                    with Horizontal(classes='tablerow'):
                        for c in range(COLS):
                            e = GRID[r][c]
                            if e is None:
                                yield Static('', id=_cell_id(r, c),
                                             classes='cell cell-empty')
                            else:
                                bg, fg = CAT_COLORS.get(
                                    e.category, CAT_COLORS['unknown'])
                                yield Static(
                                    f'[b]{e.symbol}[/b]',
                                    id=_cell_id(r, c),
                                    classes='cell')
            with Vertical(id='detail'):
                yield Static('', id='d-chip')
                yield Static('--', id='d-symbol')
                yield Static('--', id='d-name')
                yield Static('Atomic #--', id='d-number')
                for key in ('Number', 'Weight', 'Period',
                            'Group', 'Category', 'Config'):
                    with Horizontal(classes='drow'):
                        yield Static(key, classes='drow-key',
                                     id=f'k-{key.lower()}')
                        yield Static('--', classes='drow-val',
                                     id=f'v-{key.lower()}')
        yield Static('', id='status')
        yield Footer()

    # --------------------------------------------------------- lifecycle

    def on_mount(self) -> None:
        # Apply per-cell background colors via inline styles (more reliable
        # than dynamic class generation for arbitrary categories).
        for r in range(ROWS):
            for c in range(COLS):
                e = GRID[r][c]
                if e is None:
                    continue
                bg, fg = CAT_COLORS.get(e.category, CAT_COLORS['unknown'])
                cell = self.query_one(f'#{_cell_id(r, c)}', Static)
                cell.styles.background = bg
                cell.styles.color = fg
        self._update_cursor()
        self._show_element(GRID[self.cur_r][self.cur_c])

    # ------------------------------------------------------------ utils

    def _update_cursor(self) -> None:
        for r in range(ROWS):
            for c in range(COLS):
                cell = self.query_one(f'#{_cell_id(r, c)}', Static)
                cell.remove_class('cell-cursor')
        cell = self.query_one(
            f'#{_cell_id(self.cur_r, self.cur_c)}', Static)
        cell.add_class('cell-cursor')

    def _show_element(self, e: Element | None) -> None:
        chip = self.query_one('#d-chip', Static)
        sym = self.query_one('#d-symbol', Static)
        name = self.query_one('#d-name', Static)
        number = self.query_one('#d-number', Static)
        if e is None:
            chip.update('')
            chip.styles.background = '#1f2937'
            sym.update('--')
            name.update('--')
            number.update('Atomic #--')
            for key in ('number', 'weight', 'period', 'group',
                        'category', 'config'):
                self.query_one(f'#v-{key}', Static).update('--')
            return
        bg, fg = CAT_COLORS.get(e.category, CAT_COLORS['unknown'])
        chip.update(f' {CATEGORIES[e.category]} ')
        chip.styles.background = bg
        chip.styles.color = fg
        sym.update(f'[b]{e.symbol}[/b]')
        name.update(e.name)
        number.update(f'Atomic #{e.number}')
        self.query_one('#v-number', Static).update(str(e.number))
        self.query_one('#v-weight', Static).update(f'{e.weight} u')
        self.query_one('#v-period', Static).update(str(e.period))
        self.query_one('#v-group', Static).update(
            str(e.group) if e.group else '- (f-block)')
        self.query_one('#v-category', Static).update(CATEGORIES[e.category])
        self.query_one('#v-config', Static).update(e.config)

    def _set_status(self, text: str) -> None:
        self.query_one('#status', Static).update(text)

    # ---------------------------------------------------------- actions

    def action_move(self, dr: int, dc: int) -> None:
        # Find the next non-empty cell in the requested direction. If there's
        # no element along the row/col, do nothing (instead of stopping in an
        # empty cell) so navigation feels stable.
        r, c = self.cur_r, self.cur_c
        for _ in range(max(ROWS, COLS)):
            r += dr
            c += dc
            if not (0 <= r < ROWS and 0 <= c < COLS):
                return
            if GRID[r][c] is not None:
                self.cur_r, self.cur_c = r, c
                self._update_cursor()
                self._show_element(GRID[r][c])
                return

    def action_pin(self) -> None:
        e = GRID[self.cur_r][self.cur_c]
        if e is None:
            return
        self.pinned = e
        self._set_status(f'Pinned: {e.symbol} {e.name}')

    def action_search(self) -> None:
        box = self.query_one('#search', Input)
        box.add_class('visible')
        box.focus()
        self._set_status('Type a query, Enter to jump, Esc to cancel.')

    def action_cancel_search(self) -> None:
        box = self.query_one('#search', Input)
        box.remove_class('visible')
        box.value = ''
        self._set_status('')
        # Refocus the body so arrow keys work again.
        self.set_focus(None)

    # -------------------------------------------------- input handlers

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != 'search':
            return
        term = event.value.strip()
        event.input.value = ''
        if not term:
            self.action_cancel_search()
            return
        try:
            e = lookup(term)
            self._jump_to(e)
            self._set_status(f'Jumped to {e.symbol} {e.name}')
        except KeyError:
            results = search(term)
            if not results:
                self._set_status(f'No match for {term!r}')
            else:
                e = results[0]
                self._jump_to(e)
                self._set_status(
                    f'{len(results)} match(es); showing {e.symbol} {e.name}')
        self.action_cancel_search()

    def _jump_to(self, e: Element) -> None:
        from periodic_table import grid_position
        r, c = grid_position(e)
        self.cur_r, self.cur_c = r - 1, c - 1
        self._update_cursor()
        self._show_element(e)


if __name__ == '__main__':
    PeriodicTableApp().run()
