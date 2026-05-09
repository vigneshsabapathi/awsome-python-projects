"""Dice Roller — Textual TUI.

Modern terminal UI for tabletop dice notation. Dark Tailwind palette,
single-key bindings, scrollable history.

Run:
    uv run python dice_roller/dice_roller_tui.py

Bindings:
    Enter      — roll the current notation
    Ctrl+H     — toggle the history pane
    Ctrl+L     — clear history
    Ctrl+Q     — quit
"""
from __future__ import annotations

from collections import deque

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from dice_roller import DiceNotationError, roll, split_expressions

HISTORY_LIMIT = 10
QUICK_ROLLS = ['1d6', '1d20', '2d6', '4d6kh3']


class DiceApp(App):
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

    #quick {
        height: 1;
        align-horizontal: center;
        margin-bottom: 1;
    }

    .chip {
        padding: 0 1;
        margin: 0 1;
        height: 1;
        background: #334155;
        color: #e2e8f0;
    }

    #input {
        margin: 0 4;
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
        height: 1;
    }
    .status-info  { color: #cbd5e1; }
    .status-error { color: #f87171; text-style: bold; }

    #total-box {
        align-horizontal: center;
        height: 5;
        background: #1e293b;
        margin: 1 4;
    }

    #total {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        height: 3;
    }

    #total-caption {
        text-align: center;
        color: #94a3b8;
        height: 1;
    }

    #results {
        background: #0b1220;
        color: #e2e8f0;
        margin: 1 4;
        padding: 1 2;
        height: auto;
        min-height: 6;
        border: round #334155;
    }

    #history-pane {
        margin: 1 4;
        height: 1fr;
    }

    #history-title {
        color: #cbd5e1;
        text-style: bold;
        padding-left: 1;
    }

    #history {
        background: #0b1220;
        color: #e2e8f0;
        padding: 1 2;
        border: round #334155;
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding('ctrl+h', 'toggle_history', 'History'),
        Binding('ctrl+l', 'clear_history', 'Clear'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Dice Roller'

    def __init__(self) -> None:
        super().__init__()
        self.history: deque[str] = deque(maxlen=HISTORY_LIMIT)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('DICE ROLLER', id='title')
        yield Static('Notation: 2d6+3, 1d20, 4d6kh3 — comma-separate batches',
                     id='subtitle')
        with Horizontal(id='quick'):
            yield Static('Quick:', classes='chip')
            for preset in QUICK_ROLLS:
                yield Static(preset, classes='chip')
        yield Input(placeholder='Type notation and press Enter…',
                    id='input')
        yield Static('', id='status', classes='status-info')
        with Vertical(id='total-box'):
            yield Static('—', id='total')
            yield Static('Roll something to begin.', id='total-caption')
        yield Static('Awaiting first roll.', id='results')
        with Vertical(id='history-pane'):
            yield Static(f'History (last {HISTORY_LIMIT}) — Ctrl+H to toggle',
                         id='history-title')
            yield Static('(empty)', id='history')
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#input', Input).focus()

    # ---- bindings -------------------------------------------------------

    def action_toggle_history(self) -> None:
        pane = self.query_one('#history-pane')
        pane.display = not pane.display

    def action_clear_history(self) -> None:
        self.history.clear()
        self._render_history()
        self._set_status('History cleared.', 'info')

    # ---- input ----------------------------------------------------------

    def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value.strip()
        if not line:
            self._set_status('Enter dice notation, e.g. 2d6+3.', 'error')
            return
        try:
            parts = split_expressions(line)
            if not parts:
                raise DiceNotationError('No expressions found.')
            results = [roll(p) for p in parts]
        except DiceNotationError as exc:
            self._set_status(str(exc), 'error')
            return

        self._set_status('', 'info')
        grand_total = sum(r['total'] for r in results)
        self.query_one('#total', Static).update(str(grand_total))

        if len(results) == 1:
            self.query_one('#total-caption', Static).update(
                self._caption_for(results[0]))
        else:
            self.query_one('#total-caption', Static).update(
                f'{len(results)} expressions, grand total')

        self.query_one('#results', Static).update(self._format_results(results))
        self._push_history(results, grand_total)

    # ---- helpers --------------------------------------------------------

    def _caption_for(self, r: dict) -> str:
        mod = r['modifier']
        kept_sum = sum(r['kept'])
        base = (f"{r['notation']}: kept sum={kept_sum}"
                if 'keep' in r
                else f"{r['notation']}: dice sum={kept_sum}")
        if mod:
            base += f' {"+" if mod >= 0 else "-"} {abs(mod)}'
        return base

    def _format_results(self, results: list[dict]) -> str:
        lines: list[str] = []
        for r in results:
            kept_set = list(r['kept'])
            chips: list[str] = []
            for value in r['rolls']:
                if value in kept_set:
                    kept_set.remove(value)
                    chips.append(f'[b]{value}[/]')
                else:
                    chips.append(f'[dim strike]{value}[/]')
            chips_str = ' '.join(chips)
            mod = r['modifier']
            mod_str = (f' {"+" if mod >= 0 else "-"} {abs(mod)}' if mod else '')
            kept_note = (f'  [italic dim]({r["keep"]}{r["keep_n"]})[/]'
                         if 'keep' in r else '')
            lines.append(
                f'[bold cyan]{r["notation"]}[/]  {chips_str}{mod_str}'
                f'  [bold]= {r["total"]}[/]{kept_note}'
            )
        return '\n'.join(lines)

    def _push_history(self, results: list[dict], grand_total: int) -> None:
        parts = []
        for r in results:
            rolls_str = ','.join(str(x) for x in r['rolls'])
            if 'keep' in r:
                kept = ','.join(str(x) for x in r['kept'])
                parts.append(
                    f'{r["notation"]} [{rolls_str}] -> [{kept}] = {r["total"]}')
            else:
                parts.append(f'{r["notation"]} [{rolls_str}] = {r["total"]}')
        prefix = f'[{grand_total:>4}] ' if len(results) > 1 else ''
        self.history.appendleft(prefix + ' ; '.join(parts))
        self._render_history()

    def _render_history(self) -> None:
        widget = self.query_one('#history', Static)
        if not self.history:
            widget.update('(empty)')
            return
        widget.update('\n'.join(self.history))

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')


if __name__ == '__main__':
    DiceApp().run()
