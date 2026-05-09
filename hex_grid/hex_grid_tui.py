"""Hex Grid — Textual TUI.

Dark Tailwind palette, Inputs for rows + cols, live ASCII preview.
Cycle the coordinate overlay with Ctrl+O (none / axial / cube / offset).

Bindings:
    Ctrl+O  cycle coordinate overlay
    Ctrl+Q  quit

Run:
    uv run python hex_grid/hex_grid_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from hex_grid import COORD_SYSTEMS, coordinate_overlay, render

MIN_DIM = 1
MAX_DIM = 20
OVERLAYS = ('plain',) + COORD_SYSTEMS  # cycle order


class HexGridApp(App):
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

    #controls {
        height: 3;
        padding: 0 2;
    }
    #controls Static {
        content-align: left middle;
        text-style: bold;
        width: 6;
    }
    #rows-input, #cols-input {
        width: 10;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #rows-input:focus, #cols-input:focus { border: tall #38bdf8; }

    #overlay-label {
        width: 1fr;
        content-align: right middle;
        color: #cbd5e1;
        text-style: bold;
    }

    #preview-wrap {
        height: 1fr;
        padding: 0 2;
    }
    #preview-header {
        height: 1;
        color: #94a3b8;
        text-style: bold;
    }
    #preview {
        height: 1fr;
        background: #1e293b;
        color: #38bdf8;
        padding: 1 2;
        text-style: bold;
        border: tall #334155;
    }

    #status {
        height: 1;
        padding: 0 2;
        background: #1e293b;
        color: #cbd5e1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding('ctrl+o', 'cycle_overlay', 'Cycle overlay', priority=True),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]
    TITLE = 'Hex Grid'

    def __init__(self) -> None:
        super().__init__()
        self.rows_value = 4
        self.cols_value = 6
        self.overlay = 'plain'

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('HEX GRID', id='title')
        yield Static('Type rows + cols, Ctrl+O cycles the coordinate overlay.',
                     id='subtitle')
        with Horizontal(id='controls'):
            yield Static('Rows:')
            yield Input(value=str(self.rows_value), id='rows-input',
                        max_length=2, restrict=r'[0-9]*')
            yield Static('Cols:')
            yield Input(value=str(self.cols_value), id='cols-input',
                        max_length=2, restrict=r'[0-9]*')
            yield Static(self._overlay_label_text(), id='overlay-label')
        with Vertical(id='preview-wrap'):
            yield Static('Preview', id='preview-header')
            yield Static('', id='preview')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.query_one('#rows-input', Input).focus()

    # -------------------------------------------------------- input events

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id not in ('rows-input', 'cols-input'):
            return
        raw = event.value.strip()
        if not raw:
            return
        try:
            n = int(raw)
        except ValueError:
            return
        n = max(MIN_DIM, min(MAX_DIM, n))
        if event.input.id == 'rows-input':
            self.rows_value = n
        else:
            self.cols_value = n
        self._refresh()

    # ----------------------------------------------------------- actions

    def action_cycle_overlay(self) -> None:
        idx = OVERLAYS.index(self.overlay)
        self.overlay = OVERLAYS[(idx + 1) % len(OVERLAYS)]
        self.query_one('#overlay-label', Static).update(
            self._overlay_label_text())
        self._refresh()

    # ----------------------------------------------------------- helpers

    def _overlay_label_text(self) -> str:
        return f'Overlay: [bold cyan]{self.overlay}[/]    (Ctrl+O)'

    def _refresh(self) -> None:
        labels = (None if self.overlay == 'plain'
                  else coordinate_overlay(
                      self.rows_value, self.cols_value, self.overlay))
        text = render(self.rows_value, self.cols_value, labels)
        self.query_one('#preview', Static).update(text)

        line_count = text.count('\n') + 1 if text else 0
        width = max((len(line) for line in text.splitlines()), default=0)
        cells = self.rows_value * self.cols_value
        self.query_one('#status', Static).update(
            f'overlay [bold cyan]{self.overlay}[/]  •  '
            f'{self.rows_value} × {self.cols_value} hexes  •  '
            f'{cells} cells  •  '
            f'{line_count} lines × {width} chars'
        )


if __name__ == '__main__':
    HexGridApp().run()
