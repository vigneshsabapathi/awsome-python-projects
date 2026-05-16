"""Three-Card Monte — Textual TUI.

A dark-Tailwind-themed terminal UI for Three-Card Monte.

Bindings:
  1 / 2 / 3       pick that card
  s               start the shuffle
  r               show solution / replay
  n               new round
  Ctrl+Q          quit

Run:
    uv run python three_card/three_card_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from three_card import NUM_CARDS, QUEEN, Game


CARD_BACK_FRAME = (
    '┌───────┐\n'
    '│ ✦ ✦ ✦ │\n'
    '│ ✦   ✦ │\n'
    '│ ✦ ✦ ✦ │\n'
    '└───────┘'
)
CARD_QUEEN_FRAME = (
    '┌───────┐\n'
    '│   Q   │\n'
    '│   ♥   │\n'
    '│       │\n'
    '└───────┘'
)
CARD_BLANK_FRAME = (
    '┌───────┐\n'
    '│       │\n'
    '│   ·   │\n'
    '│       │\n'
    '└───────┘'
)


class ThreeCardApp(App):
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

    #board {
        align-horizontal: center;
        height: 7;
        width: auto;
    }

    .card {
        width: 11;
        height: 5;
        margin: 0 2;
        background: #1e293b;
        color: #94a3b8;
        border: tall #334155;
        content-align: center middle;
        text-style: bold;
    }

    .card-back   { background: #1e293b; color: #475569; border: tall #334155; }
    .card-blank  { background: #f8fafc; color: #94a3b8; border: tall #334155; }
    .card-queen  { background: #f8fafc; color: #dc2626; border: tall #fbbf24; }
    .card-pick   { border: tall #38bdf8; }

    #status {
        text-align: center;
        padding: 1;
    }
    .status-info  { color: #cbd5e1; }
    .status-dim   { color: #94a3b8; }
    .status-win   { color: #34d399; text-style: bold; }
    .status-lose  { color: #f87171; text-style: bold; }

    #stats {
        text-align: center;
        color: #94a3b8;
    }

    #hint {
        text-align: center;
        color: #64748b;
        padding-top: 1;
    }
    """

    BINDINGS = [
        Binding('1', 'pick(0)', 'Card 1'),
        Binding('2', 'pick(1)', 'Card 2'),
        Binding('3', 'pick(2)', 'Card 3'),
        Binding('s', 'shuffle', 'Shuffle'),
        Binding('r', 'replay', 'Replay'),
        Binding('n', 'new_round', 'New round'),
        Binding('plus', 'more_swaps', 'More swaps'),
        Binding('minus', 'fewer_swaps', 'Fewer swaps'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]

    TITLE = 'Three-Card Monte'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.game: Game | None = None
        self.num_swaps = 10
        self.swap_interval = 0.30  # seconds between visual swaps
        # Round phase: 'reveal' | 'shuffling' | 'pick' | 'done'
        self.phase: str = 'reveal'
        self.card_slots: list[str] = ['_'] * NUM_CARDS
        self.queen_slot: int = 0
        self._swap_iter = None
        self._swap_timer = None
        self._replay_mode = False
        # Stats
        self.wins = 0
        self.losses = 0
        self.streak = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('THREE-CARD MONTE', id='title')
        yield Static('Find the queen — keys 1 / 2 / 3 to pick.', id='subtitle')
        with Horizontal(id='board'):
            for i in range(NUM_CARDS):
                yield Static(CARD_BLANK_FRAME, classes='card', id=f'card-{i}')
        yield Static('', id='status', classes='status-info')
        yield Static('', id='stats')
        yield Static(
            'Keys: [s]huffle  [r]eplay  [n]ew  [+/-] swaps  [Ctrl+Q] quit',
            id='hint',
        )
        yield Footer()

    def on_mount(self) -> None:
        self._new_round()

    # ---------------- Round lifecycle ----------------
    def _new_round(self) -> None:
        self._cancel_timer()
        self._replay_mode = False
        self.game = Game(num_swaps=self.num_swaps, rng=self.rng)
        self.game.setup()
        self.queen_slot = self.game.initial_queen_index
        self.card_slots = ['_'] * NUM_CARDS
        self.card_slots[self.queen_slot] = QUEEN
        self._render_cards(face_up=True)
        self.phase = 'reveal'
        self._set_status(
            f'Memorize the queen at position {self.queen_slot + 1}. '
            f'[s] to shuffle ({self.num_swaps} swaps).',
            'info',
        )
        self._update_stats()

    def action_new_round(self) -> None:
        self._new_round()

    def action_shuffle(self) -> None:
        if self.game is None or self.phase == 'shuffling':
            return
        if self.phase != 'reveal':
            self._new_round()
        self._render_cards(face_up=False)
        self.phase = 'shuffling'
        self._set_status('Shuffling...', 'dim')
        self._swap_iter = iter(self.game.history)
        self._swap_timer = self.set_timer(self.swap_interval, self._do_next_swap)

    def _do_next_swap(self) -> None:
        if self._swap_iter is None or self.game is None:
            return
        try:
            i, j = next(self._swap_iter)
        except StopIteration:
            self._end_shuffle()
            return
        # Apply swap to our local slot view.
        self.card_slots[i], self.card_slots[j] = self.card_slots[j], self.card_slots[i]
        if self.queen_slot == i:
            self.queen_slot = j
        elif self.queen_slot == j:
            self.queen_slot = i
        # Brief flash on the swapped slots so the eye can follow.
        self._render_cards(face_up=self._replay_mode, flash=(i, j))
        self._swap_timer = self.set_timer(self.swap_interval, self._do_next_swap)

    def _end_shuffle(self) -> None:
        self._cancel_timer()
        if self._replay_mode:
            self._replay_mode = False
            self.phase = 'done'
            self._render_cards(face_up=True)
            self._set_status(
                f'Replay complete — queen at position {self.queen_slot + 1}.',
                'dim',
            )
            return
        self.phase = 'pick'
        self._render_cards(face_up=False)
        self._set_status('Pick the queen — press 1, 2, or 3.', 'info')

    def action_pick(self, slot: int) -> None:
        if self.phase != 'pick' or self.game is None:
            return
        won = self.game.pick(slot)
        self.phase = 'done'
        self._render_cards(face_up=True, picked=slot)
        if won:
            self.wins += 1
            self.streak = self.streak + 1 if self.streak >= 0 else 1
            self._set_status('You win! You tracked the queen.', 'win')
        else:
            self.losses += 1
            self.streak = self.streak - 1 if self.streak <= 0 else -1
            self._set_status(
                f'House wins. Queen was at position {self.queen_slot + 1}. '
                f'[r] to replay  [n] new round.',
                'lose',
            )
        self._update_stats()

    def action_replay(self) -> None:
        """Re-run the shuffle with all cards face up so the player can see
        how the queen moved."""
        if self.game is None or self.phase == 'shuffling':
            return
        # Reset slots to initial state, queen face up.
        self._cancel_timer()
        self.queen_slot = self.game.initial_queen_index
        self.card_slots = ['_'] * NUM_CARDS
        self.card_slots[self.queen_slot] = QUEEN
        self._render_cards(face_up=True)
        self.phase = 'shuffling'
        self._replay_mode = True
        self._set_status('Replay — watch the queen.', 'dim')
        self._swap_iter = iter(self.game.history)
        self._swap_timer = self.set_timer(self.swap_interval, self._do_next_swap)

    def action_more_swaps(self) -> None:
        if self.phase == 'shuffling':
            return
        self.num_swaps = min(40, self.num_swaps + 1)
        self._new_round()

    def action_fewer_swaps(self) -> None:
        if self.phase == 'shuffling':
            return
        self.num_swaps = max(1, self.num_swaps - 1)
        self._new_round()

    # ---------------- Render helpers ----------------
    def _render_cards(
        self, face_up: bool, picked: int | None = None, flash: tuple[int, int] | None = None,
    ) -> None:
        for slot in range(NUM_CARDS):
            tile = self.query_one(f'#card-{slot}', Static)
            classes = ['card']
            if face_up:
                value = self.card_slots[slot]
                if value == QUEEN:
                    tile.update(CARD_QUEEN_FRAME)
                    classes.append('card-queen')
                else:
                    tile.update(CARD_BLANK_FRAME)
                    classes.append('card-blank')
            else:
                tile.update(CARD_BACK_FRAME)
                classes.append('card-back')
            if picked is not None and slot == picked:
                classes.append('card-pick')
            if flash is not None and slot in flash:
                classes.append('card-pick')
            tile.set_classes(' '.join(classes))

    def _set_status(self, text: str, kind: str = 'info') -> None:
        s = self.query_one('#status', Static)
        s.update(text)
        s.set_classes(f'status-{kind}')

    def _update_stats(self) -> None:
        total = self.wins + self.losses
        acc = f'{(self.wins / total * 100):.0f}%' if total else '—'
        streak_txt = (f'+{self.streak}' if self.streak > 0
                      else (str(self.streak) if self.streak < 0 else '0'))
        self.query_one('#stats', Static).update(
            f'Wins: {self.wins}   Losses: {self.losses}   '
            f'Streak: {streak_txt}   Accuracy: {acc}   '
            f'Swaps: {self.num_swaps}',
        )

    def _cancel_timer(self) -> None:
        if self._swap_timer is not None:
            try:
                self._swap_timer.stop()
            except Exception:
                pass
            self._swap_timer = None
        self._swap_iter = None


if __name__ == '__main__':
    ThreeCardApp().run()
