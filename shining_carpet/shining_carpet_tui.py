"""Shining Carpet — Textual TUI.

Dark Tailwind palette, animated tessellated carpet rendered as Rich color
spans. The animation runs on Textual's interval timer; the carpet fills
whatever terminal width/height is available.

Bindings:
    space     pause / resume animation
    p         cycle palette (shining → persian → bauhaus → …)
    ctrl+q    quit

Run:
    uv run python shining_carpet/shining_carpet_tui.py
"""
from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static

from shining_carpet import (PALETTE_GLYPHS, PALETTE_NAMES, PALETTES,
                            glyph_to_slot, render, tile)

FPS = 8


class CarpetCanvas(Static):
    """A Static that knows its own size and renders the carpet on demand."""

    def render_carpet(self, palette_name: str, frame: int) -> str:
        # Use the live widget size; fall back to sensible defaults so we
        # never hand `render` a zero-dimension canvas.
        width = max(8, self.size.width or 80)
        height = max(4, self.size.height or 20)
        tile_data = tile(palette_name)
        palette = PALETTES[palette_name]
        plain = render(width, height, tile_data, offset=frame)

        out_lines: list[str] = []
        for line in plain.splitlines():
            buf: list[str] = []
            last_slot = -2
            for ch in line:
                slot = glyph_to_slot(ch)
                if slot == -1:
                    if last_slot != -1:
                        buf.append('[/]')
                        last_slot = -1
                    buf.append(' ')
                    continue
                if slot != last_slot:
                    if last_slot >= 0:
                        buf.append('[/]')
                    colour = palette[slot % len(palette)]
                    buf.append(f'[{colour}]')
                    last_slot = slot
                buf.append(ch)
            if last_slot >= 0:
                buf.append('[/]')
            out_lines.append(''.join(buf))
        return '\n'.join(out_lines)


class ShiningCarpetApp(App):
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

    #carpet {
        height: 1fr;
        width: 100%;
        background: #000000;
        padding: 0;
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
        Binding('space', 'toggle_pause', 'Pause/Resume', priority=True),
        Binding('p', 'cycle_palette', 'Next palette', priority=True),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]
    TITLE = 'Shining Carpet'

    def __init__(self) -> None:
        super().__init__()
        self.palette_name: str = 'shining'
        self.frame: int = 0
        self.paused: bool = False
        self._timer = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('SHINING CARPET', id='title')
        yield Static('Tessellated tile + cycling colour phase  •  '
                     'space pause  •  p palette  •  Ctrl+Q quit',
                     id='subtitle')
        yield CarpetCanvas('', id='carpet')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._timer = self.set_interval(1.0 / FPS, self._tick)
        self._redraw()

    # -------- bindings ---------------------------------------------------

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._update_status()

    def action_cycle_palette(self) -> None:
        idx = PALETTE_NAMES.index(self.palette_name)
        self.palette_name = PALETTE_NAMES[(idx + 1) % len(PALETTE_NAMES)]
        self._redraw()

    # -------- animation loop --------------------------------------------

    def _tick(self) -> None:
        if self.paused:
            return
        self.frame += 1
        # Slow auto-cycle every 24 frames so the carpet drifts through all
        # three palettes if the user just sits and watches.
        if self.frame % 24 == 0:
            idx = PALETTE_NAMES.index(self.palette_name)
            self.palette_name = PALETTE_NAMES[
                (idx + 1) % len(PALETTE_NAMES)]
        self._redraw()

    def _redraw(self) -> None:
        canvas = self.query_one('#carpet', CarpetCanvas)
        canvas.update(canvas.render_carpet(self.palette_name, self.frame))
        self._update_status()

    def _update_status(self) -> None:
        state = 'paused' if self.paused else 'running'
        canvas = self.query_one('#carpet', CarpetCanvas)
        w = canvas.size.width or 0
        h = canvas.size.height or 0
        self.query_one('#status', Static).update(
            f'palette [bold cyan]{self.palette_name}[/]  •  '
            f'grid {w}×{h}  •  '
            f'frame {self.frame}  •  '
            f'{state}  •  '
            f'{len(PALETTE_GLYPHS)} glyph slots')


if __name__ == '__main__':
    ShiningCarpetApp().run()
