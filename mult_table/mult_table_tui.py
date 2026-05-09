"""Multiplication Table — Textual TUI.

Modern terminal UI rendering an N x N multiplication table with colored
heatmap cells. Up/Down arrow keys change N (2..30), `m` toggles modular
multiplication (where the cyclic group structure becomes visible), `[`/`]`
adjust the modulus.

Run:
    uv run python mult_table/mult_table_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from mult_table import _is_prime

N_MIN, N_MAX = 2, 30
DEFAULT_N = 12
MOD_MIN, MOD_MAX = 2, 30
DEFAULT_MOD = 12

# Tailwind-aligned 12-stop palette, cool to warm.
HEATMAP = (
    'rgb(30,58,138)',   'rgb(29,78,216)',   'rgb(37,99,235)',
    'rgb(59,130,246)',  'rgb(6,182,212)',   'rgb(13,148,136)',
    'rgb(16,185,129)',  'rgb(132,204,22)',  'rgb(234,179,8)',
    'rgb(245,158,11)',  'rgb(249,115,22)',  'rgb(220,38,38)',
)


def heatmap_color(value: float, vmin: float, vmax: float) -> str:
    if vmax <= vmin:
        return HEATMAP[0]
    t = (value - vmin) / (vmax - vmin)
    t = max(0.0, min(1.0, t))
    idx = min(int(t * len(HEATMAP)), len(HEATMAP) - 1)
    return HEATMAP[idx]


def modular_color(value: int, mod: int) -> str:
    if mod <= 1:
        return HEATMAP[0]
    idx = int(value % mod / mod * len(HEATMAP))
    idx = min(idx, len(HEATMAP) - 1)
    return HEATMAP[idx]


def _is_light_rgb(rgb: str) -> bool:
    # rgb string like "rgb(30,58,138)"
    inner = rgb[rgb.index('(') + 1:rgb.rindex(')')]
    r, g, b = [int(x) for x in inner.split(',')]
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.55


def render_grid(n: int, mod: int | None) -> str:
    """Build a colored Rich-markup grid for Textual to display."""
    if mod is not None:
        cells = [[(i * j) % mod for j in range(n)] for i in range(n)]
        row_labels = list(range(n))
        col_labels = list(range(n))
        vmin, vmax = 0, max(0, mod - 1)
        digits = max(2, len(str(vmax)))
    else:
        cells = [[i * j for j in range(1, n + 1)] for i in range(n)]
        row_labels = list(range(1, n + 1))
        col_labels = list(range(1, n + 1))
        vmin, vmax = 1, n * n
        digits = max(2, len(str(vmax)))

    cell_w = digits + 2  # padding around the number

    def fmt_cell(text: str, bg: str, fg: str) -> str:
        # Pad text to cell_w and wrap with Rich style.
        padded = f'{text:^{cell_w}}'
        return f'[{fg} on {bg}]{padded}[/]'

    lines: list[str] = []

    # Header row
    header_cells = [fmt_cell('×', 'rgb(51,65,85)', 'white')]
    for label in col_labels:
        header_cells.append(fmt_cell(str(label),
                                     'rgb(51,65,85)', 'rgb(226,232,240)'))
    lines.append(''.join(header_cells))

    # Body rows
    for r in range(n):
        row_cells = [fmt_cell(str(row_labels[r]),
                              'rgb(51,65,85)', 'rgb(226,232,240)')]
        for c in range(n):
            v = cells[r][c]
            if mod is not None:
                bg = modular_color(v, mod)
            else:
                bg = heatmap_color(v, vmin, vmax)
            fg = 'rgb(15,23,42)' if _is_light_rgb(bg) else 'rgb(248,250,252)'
            row_cells.append(fmt_cell(str(v), bg, fg))
        lines.append(''.join(row_cells))

    return '\n'.join(lines)


class MultTableApp(App):
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

    #grid-wrap {
        align: center top;
        padding: 1 2;
    }

    #grid {
        width: auto;
        height: auto;
    }

    #status {
        background: #1e293b;
        color: #cbd5e1;
        padding: 1 2;
        margin: 1 2 0 2;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding('up', 'inc_n', 'N+1'),
        Binding('down', 'dec_n', 'N-1'),
        Binding('m', 'toggle_mod', 'Modular'),
        Binding('left_square_bracket', 'dec_mod', 'Mod-'),
        Binding('right_square_bracket', 'inc_mod', 'Mod+'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Multiplication Table'

    def __init__(self) -> None:
        super().__init__()
        self.n = DEFAULT_N
        self.mod_enabled = False
        self.mod_value = DEFAULT_MOD

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MULTIPLICATION TABLE', id='title')
        yield Static('↑/↓ change N · m toggles modular · [ ] adjust modulus',
                     id='subtitle')
        yield Static('', id='grid', markup=True)
        yield Static('', id='status', markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self._redraw()

    def action_inc_n(self) -> None:
        if self.n < N_MAX:
            self.n += 1
            self._redraw()

    def action_dec_n(self) -> None:
        if self.n > N_MIN:
            self.n -= 1
            self._redraw()

    def action_toggle_mod(self) -> None:
        self.mod_enabled = not self.mod_enabled
        self._redraw()

    def action_inc_mod(self) -> None:
        if self.mod_value < MOD_MAX:
            self.mod_value += 1
            if self.mod_enabled:
                self._redraw()
            else:
                self._refresh_status()

    def action_dec_mod(self) -> None:
        if self.mod_value > MOD_MIN:
            self.mod_value -= 1
            if self.mod_enabled:
                self._redraw()
            else:
                self._refresh_status()

    def _redraw(self) -> None:
        grid = self.query_one('#grid', Static)
        mod = self.mod_value if self.mod_enabled else None
        grid.update(render_grid(self.n, mod))
        self._refresh_status()

    def _refresh_status(self) -> None:
        status = self.query_one('#status', Static)
        if self.mod_enabled:
            kind = 'prime' if _is_prime(self.mod_value) else 'composite'
            status.update(
                f'[bold]N={self.n}[/]   '
                f'modular [cyan]mod {self.mod_value}[/] '
                f'([yellow]{kind}[/])   '
                f'cells: {self.n * self.n}'
            )
        else:
            status.update(
                f'[bold]N={self.n}[/]   '
                f'standard table   '
                f'max value [cyan]{self.n * self.n}[/]   '
                f'(press [bold]m[/] for modular [dim]mod {self.mod_value}[/])'
            )


if __name__ == '__main__':
    MultTableApp().run()
