"""Diamonds — Textual TUI.

Dark Tailwind palette, size input, style toggle, live preview.
Bindings:
    Ctrl+T  toggle style (Outlined ↔ Filled)
    Ctrl+G  toggle Grow animation (4 fps from 1 → size)
    Ctrl+Q  quit

Run:
    uv run python diamonds/diamonds_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Static

from diamonds import filled, outlined

MIN_SIZE = 1
MAX_SIZE = 30
ANIMATION_INTERVAL_S = 0.25      # 4 fps


class DiamondsApp(App):
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
        width: 8;
    }
    #size-input {
        width: 12;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
    }
    #size-input:focus { border: tall #38bdf8; }

    #style-label {
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
        Binding('ctrl+t', 'toggle_style', 'Toggle style', priority=True),
        Binding('ctrl+g', 'toggle_grow', 'Grow', priority=True),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]
    TITLE = 'Diamonds'

    def __init__(self) -> None:
        super().__init__()
        self.size_value = 6
        self.style_value = 'outlined'
        self._growing = False
        self._grow_step = 1
        self._grow_timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('DIAMONDS', id='title')
        yield Static('Type a size, hit Ctrl+T to flip style, Ctrl+G to grow.',
                     id='subtitle')
        with Horizontal(id='controls'):
            yield Static('Size:')
            yield Input(value=str(self.size_value), id='size-input',
                        max_length=2, restrict=r'[0-9]*')
            yield Static(self._style_label_text(), id='style-label')
        with Vertical(id='preview-wrap'):
            yield Static('Preview', id='preview-header')
            yield Static('', id='preview')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self.query_one('#size-input', Input).focus()

    # -------------------------------------------------------- input events

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != 'size-input':
            return
        raw = event.value.strip()
        if not raw:
            return
        try:
            n = int(raw)
        except ValueError:
            return
        n = max(0, min(MAX_SIZE, n))
        self.size_value = n
        if self._growing:
            self._stop_grow()
        self._refresh()

    # ----------------------------------------------------------- actions

    def action_toggle_style(self) -> None:
        self.style_value = 'filled' if self.style_value == 'outlined' \
            else 'outlined'
        self.query_one('#style-label', Static).update(self._style_label_text())
        self._refresh()

    def action_toggle_grow(self) -> None:
        if self._growing:
            self._stop_grow()
        else:
            self._start_grow()

    # ----------------------------------------------------------- helpers

    def _style_label_text(self) -> str:
        flag = '[bold cyan]Outlined[/]  ·  Filled' \
            if self.style_value == 'outlined' \
            else 'Outlined  ·  [bold magenta]Filled[/]'
        return f'Style: {flag}    (Ctrl+T)'

    def _start_grow(self) -> None:
        if self.size_value < MIN_SIZE:
            return
        self._growing = True
        self._grow_step = 1
        self._grow_timer = self.set_interval(
            ANIMATION_INTERVAL_S, self._tick_grow)
        self._refresh_preview(self._grow_step)

    def _stop_grow(self) -> None:
        self._growing = False
        if self._grow_timer is not None:
            self._grow_timer.stop()
            self._grow_timer = None
        self._refresh()

    def _tick_grow(self) -> None:
        if not self._growing:
            return
        self._refresh_preview(self._grow_step)
        if self._grow_step >= self.size_value:
            self._grow_step = 1
        else:
            self._grow_step += 1

    def _refresh(self) -> None:
        self._refresh_preview(self.size_value)

    def _refresh_preview(self, size: int) -> None:
        renderer = filled if self.style_value == 'filled' else outlined
        text = renderer(size)
        self.query_one('#preview', Static).update(text)

        line_count = text.count('\n') + 1 if text else 0
        width = max((len(line) for line in text.splitlines()), default=0)
        anim = '  •  [bold magenta]growing[/]' if self._growing else ''
        self.query_one('#status', Static).update(
            f'style [bold cyan]{self.style_value}[/]  •  '
            f'size {size}  •  {line_count} rows × {width} cols  •  '
            f'{len(text)} chars{anim}'
        )


if __name__ == '__main__':
    DiamondsApp().run()
