"""Clickbait Headline Generator — Textual TUI.

Dark Tailwind palette. Big centered headline panel.

Bindings:
    Space    Generate a new headline
    B        Show a batch of 10
    C        Cycle category
    Ctrl+Q   Quit

Run:
    uv run python clickbait/clickbait_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, Static

from clickbait import (
    CATEGORIES,
    generate_batch,
    generate_headline,
    outrage_score,
)

CATEGORY_ORDER = sorted(CATEGORIES.keys())


class BatchScreen(ModalScreen[None]):
    """Modal that shows ten fresh headlines."""

    BINDINGS = [Binding('escape', 'dismiss', 'Close')]

    DEFAULT_CSS = """
    BatchScreen {
        align: center middle;
    }

    #batch-card {
        width: 80%;
        max-width: 100;
        height: 80%;
        background: #1e293b;
        border: tall #334155;
        padding: 1 2;
    }

    #batch-title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding-bottom: 1;
    }

    .batch-line {
        padding: 0 1;
        color: #f8fafc;
    }

    .batch-line-alt {
        padding: 0 1;
        color: #cbd5e1;
        background: #0f172a;
    }

    #batch-hint {
        text-align: center;
        color: #94a3b8;
        padding-top: 1;
    }
    """

    def __init__(self, headlines: list[str], category: str) -> None:
        super().__init__()
        self._headlines = headlines
        self._category = category

    def compose(self) -> ComposeResult:
        with Vertical(id='batch-card'):
            yield Static(f'10 fresh headlines  -  {self._category}',
                         id='batch-title')
            with VerticalScroll():
                for i, headline in enumerate(self._headlines, 1):
                    score = outrage_score(headline)
                    cls = 'batch-line' if i % 2 else 'batch-line-alt'
                    yield Static(
                        f'{i:2d}.  [{score:3d}]  {headline}',
                        classes=cls,
                    )
            yield Static('Press Esc to close', id='batch-hint')

    def action_dismiss(self) -> None:
        self.dismiss()


class ClickbaitApp(App):
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

    #headline-panel {
        width: 90%;
        height: auto;
        min-height: 14;
        margin: 1 2;
        padding: 2 4;
        background: #1e293b;
        border: tall #334155;
        align: center middle;
    }

    #headline {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding: 1 2;
    }

    #meta {
        text-align: center;
        color: #38bdf8;
        padding-top: 1;
    }

    #category-row {
        align-horizontal: center;
        height: 1;
        padding: 0 1;
    }

    .chip {
        padding: 0 2;
        margin: 0 1;
        height: 1;
        background: #334155;
        color: #cbd5e1;
    }

    .chip-active {
        background: #38bdf8;
        color: #0f172a;
        text-style: bold;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding('space', 'generate', 'Generate'),
        Binding('b', 'batch', 'Batch x10'),
        Binding('c', 'cycle_category', 'Cycle category'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Clickbait Headline Generator'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.category_index = CATEGORY_ORDER.index('general')
        self.current_headline: str = ''

    @property
    def category(self) -> str:
        return CATEGORY_ORDER[self.category_index]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('CLICKBAIT', id='title')
        yield Static('Press SPACE for a fresh headline  -  '
                     'B for a batch  -  C to cycle category',
                     id='subtitle')
        with Horizontal(id='category-row'):
            for cat in CATEGORY_ORDER:
                yield Static(
                    f' {cat} ',
                    classes='chip',
                    id=f'chip-{cat}',
                )
        yield Vertical(
            Static('', id='headline'),
            Static('', id='meta'),
            id='headline-panel',
        )
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_chips()
        self.action_generate()

    # ----- actions ---------------------------------------------------------
    def action_generate(self) -> None:
        self.current_headline = generate_headline(self.rng, self.category)
        score = outrage_score(self.current_headline)
        bar = '#' * (score // 10) + '.' * (10 - score // 10)
        self.query_one('#headline', Static).update(self.current_headline)
        self.query_one('#meta', Static).update(
            f'Outrage [{bar}] {score}/100'
        )
        self.query_one('#status', Static).update(
            'SPACE = new  -  B = batch  -  C = cycle category'
        )

    def action_cycle_category(self) -> None:
        self.category_index = (self.category_index + 1) % len(CATEGORY_ORDER)
        self._refresh_chips()
        self.action_generate()

    def action_batch(self) -> None:
        batch = generate_batch(10, rng=self.rng, category=self.category)
        self.push_screen(BatchScreen(batch, self.category))

    # ----- helpers ---------------------------------------------------------
    def _refresh_chips(self) -> None:
        for cat in CATEGORY_ORDER:
            chip = self.query_one(f'#chip-{cat}', Static)
            classes = 'chip chip-active' if cat == self.category else 'chip'
            chip.set_classes(classes)


if __name__ == '__main__':
    ClickbaitApp().run()
