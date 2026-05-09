"""J'Accuse! — Textual TUI.

A terminal mystery game with a noir-sepia palette.

Bindings:
    1..9     visit witness #N
    a        open the accusation modal
    h        toggle the auto-deduce hint
    n        new case
    ctrl+q   quit
"""
from __future__ import annotations

import random
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    Button, Footer, Header, Label, RadioButton, RadioSet, Static,
)

from jaccuse import LIE_PROBABILITY, Game


class AccusationModal(ModalScreen[Optional[str]]):
    """A modal that lets the player pick a suspect to accuse."""

    DEFAULT_CSS = """
    AccusationModal {
        align: center middle;
    }
    #modal-frame {
        width: 64;
        height: auto;
        padding: 1 2;
        background: #171411;
        border: heavy #c9a063;
    }
    #modal-title {
        text-style: bold;
        color: #c9a063;
        text-align: center;
        padding-bottom: 1;
    }
    #modal-buttons {
        height: 3;
        align-horizontal: right;
        padding-top: 1;
    }
    #modal-buttons Button {
        margin-left: 1;
    }
    Button#confirm {
        background: #a23f3f;
        color: #e8d8b6;
    }
    """

    def __init__(self, suspects) -> None:
        super().__init__()
        self.suspects = suspects

    def compose(self) -> ComposeResult:
        with Vertical(id='modal-frame'):
            yield Static("J'ACCUSE !", id='modal-title')
            yield Static('Name the guilty party:')
            with RadioSet(id='accuse-set'):
                for s in self.suspects:
                    yield RadioButton(
                        f'{s.name}  ({s.hair} hair, {s.clothing})',
                        id=f'pick-{s.name.replace(" ", "_").replace(".", "")}',
                    )
            with Horizontal(id='modal-buttons'):
                yield Button('Cancel', id='cancel')
                yield Button('Accuse', id='confirm', variant='error')

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == 'cancel':
            self.dismiss(None)
            return
        if event.button.id == 'confirm':
            radio_set = self.query_one('#accuse-set', RadioSet)
            pressed = radio_set.pressed_button
            if pressed is None:
                return
            label = str(pressed.label).strip()
            name = label.split('  (')[0]
            self.dismiss(name)


class JaccuseTUI(App):
    CSS = """
    Screen {
        background: #0b0a08;
        color: #e8d8b6;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #c9a063;
        padding-top: 1;
    }
    #subtitle {
        text-align: center;
        color: #9a8f7a;
        padding-bottom: 1;
    }

    #body {
        height: 1fr;
        padding: 0 1;
    }

    .panel {
        background: #171411;
        border: round #5d5547;
        padding: 1;
        margin: 0 1;
    }
    .panel-title {
        text-style: bold;
        color: #c9a063;
        padding-bottom: 1;
    }

    #suspects {
        width: 36;
    }
    #witnesses {
        width: 36;
    }
    #notes {
        width: 1fr;
    }

    .suspect-card {
        background: #22201d;
        color: #e8d8b6;
        padding: 0 1;
        margin-bottom: 1;
    }
    .suspect-card.dim {
        background: #181614;
        color: #5d5547;
    }
    .suspect-card.flagged {
        background: #22201d;
        color: #c9a063;
        text-style: bold;
    }

    .witness {
        padding: 0 1;
        margin-bottom: 1;
        background: #22201d;
        color: #e8d8b6;
    }
    .witness.visited {
        background: #181614;
        color: #5d5547;
    }

    #log {
        height: 1fr;
        background: #181614;
        color: #e8d8b6;
        padding: 1;
    }

    #hint {
        color: #9a8f7a;
        padding-top: 1;
    }

    #status {
        height: 1;
        text-align: center;
        color: #e8d8b6;
        padding: 1;
    }
    .status-info  { color: #9a8f7a; }
    .status-good  { color: #6b8a4a; text-style: bold; }
    .status-bad   { color: #a23f3f; text-style: bold; }
    .status-hint  { color: #c9a063; }
    """

    BINDINGS = [
        Binding('1', 'visit(0)', 'Witness 1', show=False),
        Binding('2', 'visit(1)', 'Witness 2', show=False),
        Binding('3', 'visit(2)', 'Witness 3', show=False),
        Binding('4', 'visit(3)', 'Witness 4', show=False),
        Binding('5', 'visit(4)', 'Witness 5', show=False),
        Binding('6', 'visit(5)', 'Witness 6', show=False),
        Binding('7', 'visit(6)', 'Witness 7', show=False),
        Binding('8', 'visit(7)', 'Witness 8', show=False),
        Binding('9', 'visit(8)', 'Witness 9', show=False),
        Binding('a', 'accuse', 'Accuse'),
        Binding('h', 'hint', 'Hint'),
        Binding('n', 'new_game', 'New case'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = "J'Accuse!"

    def __init__(self) -> None:
        super().__init__()
        self.game: Game = Game(rng=random.Random())
        self.show_hint: bool = False
        self.flagged: set[str] = set()

    # ---------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("J'ACCUSE !", id='title')
        yield Static(
            'Visit witnesses, sift truth from lies, accuse the guilty. '
            f'~{int(LIE_PROBABILITY*100)}% of witnesses lie.',
            id='subtitle')
        with Horizontal(id='body'):
            with Vertical(id='suspects', classes='panel'):
                yield Static('SUSPECTS', classes='panel-title')
                yield VerticalScroll(id='suspects-list')
            with Vertical(id='witnesses', classes='panel'):
                yield Static('WITNESSES', classes='panel-title')
                yield VerticalScroll(id='witnesses-list')
            with Vertical(id='notes', classes='panel'):
                yield Static('CASE NOTES', classes='panel-title')
                yield VerticalScroll(id='log')
                yield Label('', id='hint')
        yield Static('', id='status', classes='status-info')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()

    # ----------------------------------------------------------------- render
    def _refresh(self) -> None:
        self.sub_title = (
            f'Round {min(self.game.round_no + 1, self.game.max_rounds)}/'
            f'{self.game.max_rounds}  •  visits left: '
            f'{self.game.rounds_remaining}')
        self._render_suspects()
        self._render_witnesses()
        self._render_log()
        self._render_hint()
        if self.game.finished and self.game.result is not None:
            kind = 'good' if self.game.result.correct else 'bad'
            self._set_status(self.game.result.verdict(), kind)
        else:
            self._set_status(
                'Press a number to visit a witness, [a] to accuse, [h] for hint.',
                'info')

    def _render_suspects(self) -> None:
        container = self.query_one('#suspects-list', VerticalScroll)
        container.remove_children()
        for s in self.game.suspects:
            classes = ['suspect-card']
            if self.flagged and s.name not in self.flagged:
                classes.append('dim')
            elif s.name in self.flagged:
                classes.append('flagged')
            text = (f'[{s.initial()}] {s.name}\n'
                    f'  hair: {s.hair}\n'
                    f'  wears: {s.clothing}\n'
                    f'  has: {s.accessory}')
            container.mount(Static(text, classes=' '.join(classes)))

    def _render_witnesses(self) -> None:
        container = self.query_one('#witnesses-list', VerticalScroll)
        container.remove_children()
        if self.game.finished:
            container.mount(Static('Case closed.', classes='witness visited'))
            return
        for i, w in enumerate(self.game.witnesses, 1):
            visited = w in self.game.visited
            classes = 'witness' + (' visited' if visited else '')
            suffix = '  (spoken to)' if visited else ''
            container.mount(Static(f'[{i}] {w}{suffix}', classes=classes))

    def _render_log(self) -> None:
        log = self.query_one('#log', VerticalScroll)
        log.remove_children()
        if not self.game.clues:
            log.mount(Static('No clues yet — the case is fresh.'))
            return
        for c in self.game.clues:
            log.mount(Static(f'Round {c.round_no} — {c.sentence()}'))
        log.scroll_end(animate=False)

    def _render_hint(self) -> None:
        hint = self.query_one('#hint', Label)
        if not self.show_hint or not self.game.clues:
            hint.update('Press [h] to auto-deduce.')
            return
        strict = self.game.deduce_strict()
        tolerant = self.game.deduce_tolerant()
        strict_names = ', '.join(s.name for s in strict) or '(none — a lie!)'
        tolerant_names = ', '.join(s.name for s in tolerant)
        hint.update(
            f'Strict ({len(strict)}): {strict_names}\n'
            f'Lie-tolerant ({len(tolerant)}): {tolerant_names}')

    def _set_status(self, text: str, kind: str = 'info') -> None:
        status = self.query_one('#status', Static)
        status.update(text)
        status.set_classes(f'status-{kind}')

    # ----------------------------------------------------------------- actions
    def action_visit(self, idx: int) -> None:
        if self.game.finished:
            return
        if idx >= len(self.game.witnesses):
            return
        witness = self.game.witnesses[idx]
        if witness in self.game.visited:
            self._set_status(f'You already spoke to {witness}.', 'bad')
            return
        if self.game.rounds_remaining <= 0:
            self._set_status('No rounds left — you must accuse.', 'bad')
            return
        self.game.visit(witness)
        self._refresh()

    def action_hint(self) -> None:
        self.show_hint = not self.show_hint
        if self.show_hint and self.game.clues:
            self.flagged = {s.name for s in self.game.deduce_tolerant()}
        else:
            self.flagged = set()
        self._refresh()
        if self.show_hint:
            self._set_status(
                f'Auto-deduce: {len(self.flagged)} candidate(s) flagged.',
                'hint')

    def action_accuse(self) -> None:
        if self.game.finished:
            return

        def _on_close(name: Optional[str]) -> None:
            if name is None:
                return
            try:
                self.game.accuse(name)
            except ValueError as e:
                self._set_status(str(e), 'bad')
                return
            self._refresh()

        self.push_screen(AccusationModal(self.game.suspects), _on_close)

    def action_new_game(self) -> None:
        self.game = Game(rng=random.Random())
        self.show_hint = False
        self.flagged = set()
        self._refresh()


if __name__ == '__main__':
    JaccuseTUI().run()
