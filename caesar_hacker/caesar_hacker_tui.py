"""Caesar Hacker — Textual TUI.

Paste ciphertext into the input, hit Enter, and watch all 26 candidate
decryptions appear in a ranked DataTable. The best row (lowest score)
sits at the top.

Bindings:
    Enter   — crack the current input
    Ctrl+C  — copy the top result to the clipboard
    Ctrl+Q  — quit

Run:
    uv run python caesar_hacker/caesar_hacker_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Input, Static

from caesar_hacker import crack, letter_overlap


class CaesarHackerApp(App):
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

    #input {
        margin: 1 4;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #input:focus {
        border: tall #38bdf8;
    }

    #status {
        text-align: center;
        padding: 0 1;
    }
    .status-info  { color: #cbd5e1; }
    .status-good  { color: #34d399; text-style: bold; }
    .status-error { color: #f87171; text-style: bold; }

    DataTable {
        margin: 1 4;
        background: #0b1220;
        color: #f8fafc;
        border: tall #334155;
    }
    DataTable > .datatable--header {
        background: #1e293b;
        color: #94a3b8;
        text-style: bold;
    }
    DataTable > .datatable--cursor {
        background: #14532d;
        color: #bbf7d0;
    }
    DataTable > .datatable--hover {
        background: #1e293b;
    }
    """

    BINDINGS = [
        Binding('ctrl+c', 'copy_best', 'Copy Best'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Caesar Hacker'

    def __init__(self) -> None:
        super().__init__()
        self.ciphertext: str = ''
        self.candidates: list[tuple[int, float, str]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('CAESAR HACKER', id='title')
        yield Static(
            'Paste ciphertext below and press Enter — all 26 shifts ranked '
            'by English-likelihood',
            id='subtitle')
        yield Input(placeholder='Ciphertext (Enter to crack)', id='input')
        yield Static('', id='status', classes='status-info')
        with Vertical():
            yield DataTable(id='table', cursor_type='row', zebra_stripes=True)
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one('#table', DataTable)
        table.add_columns('#', 'shift', 'score', 'overlap', 'plaintext')
        # Seed the input with the canonical example so first-run shows real data.
        seed = 'Khoor, Zruog! Wklv lv d whvw.'
        input_widget = self.query_one('#input', Input)
        input_widget.value = seed
        self._crack(seed)
        input_widget.focus()

    # -------------------------------------------------------------- Actions
    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            self._set_status('Enter ciphertext to crack.', 'error')
            return
        self._crack(text)

    def action_copy_best(self) -> None:
        if not self.candidates:
            self._set_status('Nothing to copy yet.', 'error')
            return
        best_plain = self.candidates[0][2]
        # Textual's clipboard helper falls back to OSC-52 sequences in
        # terminals that lack a native clipboard.
        try:
            self.copy_to_clipboard(best_plain)
            self._set_status(
                f'Copied: {best_plain[:50]}'
                f'{"..." if len(best_plain) > 50 else ""}',
                'good')
        except Exception as e:  # pragma: no cover
            self._set_status(f'Copy failed: {e}', 'error')

    # ----------------------------------------------------------- Internals
    def _crack(self, text: str) -> None:
        self.ciphertext = text
        self.candidates = crack(text)
        table = self.query_one('#table', DataTable)
        table.clear()
        for i, (shift, score, plaintext) in enumerate(self.candidates,
                                                      start=1):
            overlap = letter_overlap(self.ciphertext, plaintext)
            snippet = plaintext if len(plaintext) <= 70 else plaintext[:69] + '…'
            table.add_row(
                str(i),
                str(shift),
                f'{score:.2f}',
                f'{overlap * 100:.1f}%',
                snippet,
            )
        best_shift, best_score, _ = self.candidates[0]
        self._set_status(
            f'Best guess: shift={best_shift}  score={best_score:.2f}',
            'good')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')


if __name__ == '__main__':
    CaesarHackerApp().run()
