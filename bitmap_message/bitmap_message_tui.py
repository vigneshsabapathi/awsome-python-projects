"""Bitmap Message — Textual TUI.

Type a message and watch the bitmap render live in the terminal.
Press Ctrl+E to toggle the bitmap editor pane.

Run:
    uv run python bitmap_message/bitmap_message_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static, TextArea

from bitmap_message import PRESETS, render

DEFAULT_PRESET = 'Diamond'
PRESET_NAMES = list(PRESETS.keys())


class BitmapMessageApp(App):
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

    #message-row {
        height: 3;
        padding: 0 2;
    }

    #message-row Static {
        width: 10;
        content-align: left middle;
        text-style: bold;
    }

    #message-input {
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #message-input:focus { border: tall #38bdf8; }

    #panes {
        height: 1fr;
        padding: 0 2;
    }

    #editor {
        width: 1fr;
        background: #1e293b;
        border: tall #334155;
        margin-right: 1;
    }
    #editor.hidden { display: none; }

    #preview {
        width: 1fr;
        background: #1e293b;
        color: #38bdf8;
        padding: 1;
        text-style: bold;
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
        Binding('ctrl+p', 'cycle_preset', 'Next preset', priority=True),
        Binding('ctrl+b', 'toggle_editor', 'Edit bitmap', priority=True),
        Binding('ctrl+r', 'reset', 'Reset', priority=True),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]
    TITLE = 'Bitmap Message'

    def __init__(self) -> None:
        super().__init__()
        self.preset_name = DEFAULT_PRESET
        self.bitmap_text = PRESETS[DEFAULT_PRESET].lstrip('\n')
        self.editor_visible = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('BITMAP MESSAGE', id='title')
        yield Static('Type a message — bitmap fills with cycled characters',
                     id='subtitle')
        with Horizontal(id='message-row'):
            yield Static('Message:')
            yield Input(value='Hello!', id='message-input')
        with Horizontal(id='panes'):
            yield TextArea(self.bitmap_text, id='editor', classes='hidden')
            yield Static('', id='preview')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.query_one('#message-input', Input).focus()

    def action_toggle_editor(self) -> None:
        self.editor_visible = not self.editor_visible
        editor = self.query_one('#editor', TextArea)
        if self.editor_visible:
            editor.remove_class('hidden')
            editor.focus()
        else:
            editor.add_class('hidden')
            self.query_one('#message-input', Input).focus()

    def action_reset(self) -> None:
        self.bitmap_text = PRESETS[self.preset_name].lstrip('\n')
        editor = self.query_one('#editor', TextArea)
        editor.text = self.bitmap_text
        self._refresh()

    def action_cycle_preset(self) -> None:
        idx = PRESET_NAMES.index(self.preset_name)
        self.preset_name = PRESET_NAMES[(idx + 1) % len(PRESET_NAMES)]
        self.bitmap_text = PRESETS[self.preset_name].lstrip('\n')
        editor = self.query_one('#editor', TextArea)
        editor.text = self.bitmap_text
        self._refresh()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'message-input':
            self._refresh()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == 'editor':
            self.bitmap_text = event.text_area.text
            self._refresh()

    def _refresh(self) -> None:
        message = self.query_one('#message-input', Input).value
        if not message:
            rendered = '(type a message above)'
        else:
            rendered = render(self.bitmap_text, message)
        self.query_one('#preview', Static).update(rendered)

        lines = self.bitmap_text.splitlines()
        rows = len(lines)
        cols = max((len(line) for line in lines), default=0)
        filled = sum(1 for line in lines for c in line if c != ' ')
        self.query_one('#status', Static).update(
            f'preset [bold cyan]{self.preset_name}[/]  •  '
            f'bitmap {rows}×{cols}  •  {filled} filled pixels  •  '
            f'message length {len(message)}'
        )


if __name__ == '__main__':
    BitmapMessageApp().run()
