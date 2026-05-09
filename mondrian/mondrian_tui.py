"""Mondrian Art Generator — Textual TUI.

Renders generated paintings into the terminal using Unicode upper-half-block
characters (U+2580 ``▀``). Each character cell encodes two pixels:
foreground = top half, background = bottom half. Colored ANSI spans give a
faithful (if low-res) rendering of the canvas.

Bindings:
    g       Generate a new painting (random seed)
    r       Re-render with the same seed but new depth/style
    s       Save the current painting as PNG in the working directory
    p       Cycle to the next style preset
    +/-     Increase / decrease depth (clamped to 2..8)
    Ctrl+Q  Quit

Run:
    uv run python mondrian/mondrian_tui.py
"""
from __future__ import annotations

import random
from datetime import datetime
from typing import Sequence

from rich.console import RenderableType
from rich.style import Style
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Footer, Header, Static

from mondrian import PALETTES, Rect, generate, render_image

DEFAULT_DEPTH = 5
DEFAULT_STYLE = 'mondrian'
STYLE_NAMES = sorted(PALETTES.keys())

# Logical (rect) canvas size — keep aspect ratio close to a typical terminal
# pane. Rendering is downsampled to fit the widget's actual cell grid.
LOGICAL_WIDTH = 240
LOGICAL_HEIGHT = 180

BORDER_RGB = (15, 15, 15)


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


def _rasterize(
    rects: Sequence[Rect],
    width: int,
    height: int,
    border_thickness: int = 2,
) -> list[list[tuple[int, int, int]]]:
    """Rasterize ``rects`` into a width×height pixel grid (list of rows).

    A black border of ``border_thickness`` cells is painted around each rect
    before its fill, mimicking the Pillow render. Background defaults to
    border color so any uncovered cell shows as black.
    """
    grid = [[BORDER_RGB] * width for _ in range(height)]
    for r in rects:
        # Scale rect from logical canvas to grid coordinates.
        sx = r.x * width // LOGICAL_WIDTH
        sy = r.y * height // LOGICAL_HEIGHT
        ex = (r.x + r.w) * width // LOGICAL_WIDTH
        ey = (r.y + r.h) * height // LOGICAL_HEIGHT
        sx = max(0, min(width, sx))
        sy = max(0, min(height, sy))
        ex = max(0, min(width, ex))
        ey = max(0, min(height, ey))
        if ex <= sx or ey <= sy:
            continue
        # Outer black border (2 cells); interior fill.
        bt = border_thickness
        for yy in range(sy, ey):
            for xx in range(sx, ex):
                in_border = (
                    xx - sx < bt or ex - 1 - xx < bt
                    or yy - sy < bt or ey - 1 - yy < bt
                )
                grid[yy][xx] = BORDER_RGB if in_border else r.color
    return grid


def _grid_to_text(grid: list[list[tuple[int, int, int]]]) -> Text:
    """Convert pixel grid to Rich Text using upper-half-block characters.

    Each character cell shows two stacked pixels: ``foreground`` color = top
    half, ``background`` color = bottom half. Doubles vertical resolution.
    """
    text = Text()
    height = len(grid)
    width = len(grid[0]) if grid else 0
    for y in range(0, height - 1, 2):
        top_row = grid[y]
        bot_row = grid[y + 1]
        # Collapse consecutive (top, bot) pairs into a single styled segment.
        run_start = 0
        run_top = top_row[0]
        run_bot = bot_row[0]
        for x in range(1, width):
            if top_row[x] == run_top and bot_row[x] == run_bot:
                continue
            text.append(
                '▀' * (x - run_start),
                style=Style(color=_rgb_hex(run_top), bgcolor=_rgb_hex(run_bot)),
            )
            run_start = x
            run_top = top_row[x]
            run_bot = bot_row[x]
        text.append(
            '▀' * (width - run_start),
            style=Style(color=_rgb_hex(run_top), bgcolor=_rgb_hex(run_bot)),
        )
        text.append('\n')
    return text


class PaintingView(Widget):
    """A widget that renders a list of Mondrian rects as half-block art."""

    DEFAULT_CSS = """
    PaintingView {
        background: #0f172a;
        color: #f8fafc;
        padding: 0;
        content-align: center middle;
    }
    """

    rects: reactive[list[Rect]] = reactive(list, layout=True)

    def render(self) -> RenderableType:
        if not self.rects:
            return Text('Press g to generate a painting',
                        style='italic #94a3b8')
        # Map widget cells to a pixel grid: 1 cell wide = 1 px, 1 cell tall
        # = 2 px (half-block trick). Round to even rows for clean pairing.
        cw = max(20, self.size.width)
        ch = max(10, self.size.height) * 2
        if ch % 2:
            ch -= 1
        grid = _rasterize(self.rects, cw, ch)
        return _grid_to_text(grid)


class MondrianTUI(App):
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

    #painting {
        height: 1fr;
        margin: 0 2;
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
        Binding('g', 'generate', 'Generate', priority=True),
        Binding('r', 'rerender', 'Re-render', priority=True),
        Binding('p', 'cycle_style', 'Style', priority=True),
        Binding('s', 'save', 'Save PNG', priority=True),
        Binding('plus,equals_sign,equal,kp_plus', 'depth_up', 'Depth+'),
        Binding('minus,kp_minus', 'depth_down', 'Depth-'),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]
    TITLE = 'Mondrian Art Generator'

    def __init__(self) -> None:
        super().__init__()
        self.depth = DEFAULT_DEPTH
        self.style = DEFAULT_STYLE
        self.seed = random.randrange(2 ** 31)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MONDRIAN ART GENERATOR', id='title')
        yield Static('g generate · r re-render · p style · +/- depth · '
                     's save PNG · Ctrl+Q quit',
                     id='subtitle')
        with Vertical():
            yield PaintingView(id='painting')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._regenerate()

    # ------------------------------------------------------------- actions
    def action_generate(self) -> None:
        self.seed = random.randrange(2 ** 31)
        self._regenerate()

    def action_rerender(self) -> None:
        self._regenerate()

    def action_cycle_style(self) -> None:
        idx = STYLE_NAMES.index(self.style)
        self.style = STYLE_NAMES[(idx + 1) % len(STYLE_NAMES)]
        self._regenerate()

    def action_depth_up(self) -> None:
        self.depth = min(8, self.depth + 1)
        self._regenerate()

    def action_depth_down(self) -> None:
        self.depth = max(2, self.depth - 1)
        self._regenerate()

    def action_save(self) -> None:
        view = self.query_one('#painting', PaintingView)
        if not view.rects:
            self._set_status('Nothing to save — press g first.')
            return
        try:
            img = render_image(view.rects, LOGICAL_WIDTH * 5,
                               LOGICAL_HEIGHT * 5)
            ts = datetime.now().strftime('%Y%m%d-%H%M%S')
            path = f'mondrian-{self.style}-seed{self.seed}-{ts}.png'
            img.save(path)
            self._set_status(f'Saved -> {path}')
        except Exception as exc:  # noqa: BLE001
            self._set_status(f'Save failed: {exc}')

    # ------------------------------------------------------------- helpers
    def _regenerate(self) -> None:
        rng = random.Random(self.seed)
        rects = generate(LOGICAL_WIDTH, LOGICAL_HEIGHT, rng,
                         depth=self.depth, style=self.style)
        view = self.query_one('#painting', PaintingView)
        view.rects = rects
        view.refresh()
        self._set_status(
            f'style [bold cyan]{self.style}[/]  •  '
            f'depth [bold]{self.depth}[/]  •  '
            f'rects [bold]{len(rects)}[/]  •  seed {self.seed}'
        )

    def _set_status(self, message: str) -> None:
        self.query_one('#status', Static).update(message)


if __name__ == '__main__':
    MondrianTUI().run()
