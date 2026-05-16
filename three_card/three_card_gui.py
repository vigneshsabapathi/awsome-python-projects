"""Three-Card Monte — CustomTkinter desktop GUI.

A dark-themed window with three face-down cards on a tk.Canvas. The dealer
flips the queen, then performs an animated shuffle of pairwise swaps. Click
a card at the end to make your pick.

Features:
  - Tracking-difficulty slider — number of swaps (3..40)
  - Speed slider — milliseconds per swap (60..600 ms)
  - Track-eye mode — keeps the queen highlighted through the shuffle
  - Cheat-off mode — backs face down (the actual game)
  - Stats panel — wins/losses/streak/accuracy across rounds
  - Show solution — animates the trace replay revealing the queen

Run:
    uv run python three_card/three_card_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from three_card import NUM_CARDS, QUEEN, Game

# ---- Layout & colors ------------------------------------------------------
BG = '#0f172a'
CARD_BG = '#1e293b'
CARD_BORDER = '#334155'
CARD_FACE = '#f8fafc'
CARD_BACK_PATTERN = '#475569'
QUEEN_COLOR = '#dc2626'
QUEEN_GLOW = '#fbbf24'
BLANK_COLOR = '#94a3b8'
TEXT = '#f8fafc'
DIM = '#94a3b8'
WIN = '#34d399'
LOSE = '#f87171'

CARD_W = 130
CARD_H = 190
CARD_GAP = 30
TOP_PAD = 30
LEFT_PAD = 30
CANVAS_W = LEFT_PAD * 2 + NUM_CARDS * CARD_W + (NUM_CARDS - 1) * CARD_GAP
CANVAS_H = TOP_PAD * 2 + CARD_H

TITLE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 12)
STATUS_FONT = ('Segoe UI', 14, 'bold')
CARD_FONT = ('Segoe UI', 64, 'bold')


def _slot_x(idx: int) -> float:
    """Center x of card slot `idx`."""
    return LEFT_PAD + idx * (CARD_W + CARD_GAP) + CARD_W / 2


def _slot_y() -> float:
    return TOP_PAD + CARD_H / 2


class CardWidget:
    """A single card on the canvas. Tracks slot index, face value, face-up flag."""

    def __init__(self, canvas: 'ctk.CTkCanvas', slot: int, value: str) -> None:
        self.canvas = canvas
        self.slot = slot
        self.value = value
        self.face_up = False
        self.highlight = False
        x, y = _slot_x(slot), _slot_y()
        self.body = canvas.create_rectangle(
            x - CARD_W / 2, y - CARD_H / 2, x + CARD_W / 2, y + CARD_H / 2,
            fill=CARD_BG, outline=CARD_BORDER, width=3,
        )
        self.text = canvas.create_text(x, y, text='', font=CARD_FONT, fill=CARD_FACE)
        self._draw()

    def _draw(self) -> None:
        if self.face_up:
            self.canvas.itemconfig(
                self.body,
                fill=CARD_FACE,
                outline=QUEEN_GLOW if (self.value == QUEEN or self.highlight) else CARD_BORDER,
                width=4 if (self.value == QUEEN or self.highlight) else 3,
            )
            self.canvas.itemconfig(
                self.text,
                text=self.value if self.value == QUEEN else '·',
                fill=QUEEN_COLOR if self.value == QUEEN else BLANK_COLOR,
            )
        else:
            self.canvas.itemconfig(
                self.body,
                fill=CARD_BG,
                outline=QUEEN_GLOW if self.highlight else CARD_BORDER,
                width=4 if self.highlight else 3,
            )
            self.canvas.itemconfig(self.text, text='✦', fill=CARD_BACK_PATTERN)

    def set_face_up(self, up: bool) -> None:
        self.face_up = up
        self._draw()

    def set_highlight(self, on: bool) -> None:
        self.highlight = on
        self._draw()

    def move_to_slot(self, slot: int) -> None:
        """Snap to a slot (used after animation completes)."""
        self.slot = slot
        x, y = _slot_x(slot), _slot_y()
        self.canvas.coords(
            self.body,
            x - CARD_W / 2, y - CARD_H / 2, x + CARD_W / 2, y + CARD_H / 2,
        )
        self.canvas.coords(self.text, x, y)


class ThreeCardApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Three-Card Monte')
        self.geometry(f'{CANVAS_W + 60}x{CANVAS_H + 380}')
        self.configure(fg_color=BG)
        self.resizable(False, False)

        # Engine state
        self.rng = random.Random()
        self.game: Game | None = None
        self.cards: list[CardWidget] = []
        self.shuffling = False
        self.round_active = False

        # Stats
        self.wins = 0
        self.losses = 0
        self.streak = 0  # positive = win streak, negative = loss streak

        # Settings
        self.num_swaps = 10
        self.swap_ms = 280  # ms per swap
        self.track_eye = False  # if True, queen highlight stays on through shuffle

        self._build_ui()
        self._new_round()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        ctk.CTkLabel(
            self, text='THREE-CARD MONTE', font=TITLE_FONT, text_color=TEXT,
        ).pack(pady=(16, 2))
        ctk.CTkLabel(
            self, text='Find the queen.', font=LABEL_FONT, text_color=DIM,
        ).pack(pady=(0, 10))

        # Canvas with cards
        self.canvas = ctk.CTkCanvas(
            self, width=CANVAS_W, height=CANVAS_H,
            bg=BG, highlightthickness=0,
        )
        self.canvas.pack(pady=4)
        self.canvas.bind('<Button-1>', self._on_canvas_click)

        # Status
        self.status = ctk.CTkLabel(
            self, text='', font=STATUS_FONT, text_color=DIM,
        )
        self.status.pack(pady=(8, 4))

        # Controls
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(pady=(2, 4), padx=18, fill='x')

        # Swaps slider
        row1 = ctk.CTkFrame(controls, fg_color='transparent')
        row1.pack(fill='x', pady=4)
        self.swaps_label = ctk.CTkLabel(
            row1, text=f'Difficulty (swaps): {self.num_swaps}',
            font=LABEL_FONT, text_color=TEXT, width=200, anchor='w',
        )
        self.swaps_label.pack(side='left')
        self.swaps_slider = ctk.CTkSlider(
            row1, from_=3, to=40, number_of_steps=37,
            command=self._on_swaps_change,
        )
        self.swaps_slider.set(self.num_swaps)
        self.swaps_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Speed slider
        row2 = ctk.CTkFrame(controls, fg_color='transparent')
        row2.pack(fill='x', pady=4)
        self.speed_label = ctk.CTkLabel(
            row2, text=f'Speed: {self.swap_ms} ms/swap',
            font=LABEL_FONT, text_color=TEXT, width=200, anchor='w',
        )
        self.speed_label.pack(side='left')
        self.speed_slider = ctk.CTkSlider(
            row2, from_=60, to=600, number_of_steps=27,
            command=self._on_speed_change,
        )
        self.speed_slider.set(self.swap_ms)
        self.speed_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Track-eye toggle
        row3 = ctk.CTkFrame(controls, fg_color='transparent')
        row3.pack(fill='x', pady=4)
        self.track_var = ctk.BooleanVar(value=False)
        self.track_check = ctk.CTkCheckBox(
            row3, text='Track-eye (keep queen highlighted during shuffle)',
            variable=self.track_var, command=self._on_track_toggle,
            text_color=TEXT,
        )
        self.track_check.pack(side='left')

        # Buttons
        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(pady=(6, 4))
        self.shuffle_btn = ctk.CTkButton(
            btns, text='Shuffle', width=110, fg_color='#2563eb',
            hover_color='#1d4ed8', command=self._start_shuffle,
        )
        self.shuffle_btn.pack(side='left', padx=4)
        self.solution_btn = ctk.CTkButton(
            btns, text='Show solution', width=130, fg_color='#475569',
            hover_color='#334155', command=self._replay_solution,
        )
        self.solution_btn.pack(side='left', padx=4)
        self.new_btn = ctk.CTkButton(
            btns, text='New round', width=110, fg_color='#334155',
            hover_color='#475569', command=self._new_round,
        )
        self.new_btn.pack(side='left', padx=4)

        # Stats
        self.stats_label = ctk.CTkLabel(
            self, text='Wins: 0   Losses: 0   Streak: 0   Accuracy: —',
            font=LABEL_FONT, text_color=DIM,
        )
        self.stats_label.pack(pady=(6, 12))

    # ---------------- Settings handlers ----------------
    def _on_swaps_change(self, v: float) -> None:
        self.num_swaps = int(round(v))
        self.swaps_label.configure(text=f'Difficulty (swaps): {self.num_swaps}')

    def _on_speed_change(self, v: float) -> None:
        self.swap_ms = int(round(v))
        self.speed_label.configure(text=f'Speed: {self.swap_ms} ms/swap')

    def _on_track_toggle(self) -> None:
        self.track_eye = bool(self.track_var.get())

    # ---------------- Round lifecycle ----------------
    def _new_round(self) -> None:
        if self.shuffling:
            return
        self.round_active = False
        self.canvas.delete('all')
        self.game = Game(num_swaps=self.num_swaps, rng=self.rng)
        self.game.setup()
        # Build cards in their *initial* slots, queen face up.
        initial = ['_'] * NUM_CARDS
        initial[self.game.initial_queen_index] = QUEEN
        self.cards = [CardWidget(self.canvas, i, initial[i]) for i in range(NUM_CARDS)]
        for c in self.cards:
            c.set_face_up(True)
        self._set_status(
            'Memorize the queen. Press Shuffle when ready.', DIM,
        )
        self.shuffle_btn.configure(state='normal')
        self.solution_btn.configure(state='disabled')

    def _start_shuffle(self) -> None:
        if self.shuffling or self.game is None:
            return
        # Flip face down. If track-eye, light up the queen card.
        for c in self.cards:
            c.set_face_up(False)
        if self.track_eye:
            self._highlight_queen_card(True)

        self.shuffling = True
        self.round_active = False
        self.shuffle_btn.configure(state='disabled')
        self.solution_btn.configure(state='disabled')
        self._set_status('Shuffling...', DIM)
        # Schedule the swaps based on `history` recorded in game.setup().
        self._pending_swaps = list(self.game.history)
        self.after(self.swap_ms // 2, self._next_swap_step)

    def _next_swap_step(self) -> None:
        if not self._pending_swaps:
            self._end_shuffle()
            return
        i, j = self._pending_swaps.pop(0)
        if i == j:
            self.after(self.swap_ms, self._next_swap_step)
            return
        # Find which CardWidget is currently at slot i and at slot j.
        a = next(c for c in self.cards if c.slot == i)
        b = next(c for c in self.cards if c.slot == j)
        self._animate_swap(a, b, on_done=self._next_swap_step)

    def _animate_swap(self, a: CardWidget, b: CardWidget, on_done) -> None:
        """Animate a card swap by lerping their positions over `swap_ms` ms.
        `slot` attributes are updated AFTER the animation finishes."""
        steps = max(6, self.swap_ms // 30)
        x_a0, x_b0 = _slot_x(a.slot), _slot_x(b.slot)
        # Curve y a bit so swaps feel more dynamic — opposite arcs avoid collision.
        y_mid_a = _slot_y() - 28
        y_mid_b = _slot_y() + 28

        def step(n: int) -> None:
            t = n / steps
            xa = x_a0 + (x_b0 - x_a0) * t
            xb = x_b0 + (x_a0 - x_b0) * t
            # Parabolic arc peaking at t=0.5
            arc = 4 * t * (1 - t)
            ya = _slot_y() + (y_mid_a - _slot_y()) * arc
            yb = _slot_y() + (y_mid_b - _slot_y()) * arc
            self.canvas.coords(
                a.body, xa - CARD_W / 2, ya - CARD_H / 2,
                xa + CARD_W / 2, ya + CARD_H / 2,
            )
            self.canvas.coords(a.text, xa, ya)
            self.canvas.coords(
                b.body, xb - CARD_W / 2, yb - CARD_H / 2,
                xb + CARD_W / 2, yb + CARD_H / 2,
            )
            self.canvas.coords(b.text, xb, yb)
            if n < steps:
                self.after(self.swap_ms // steps, lambda: step(n + 1))
            else:
                a_slot, b_slot = a.slot, b.slot
                a.move_to_slot(b_slot)
                b.move_to_slot(a_slot)
                on_done()

        step(1)

    def _end_shuffle(self) -> None:
        self.shuffling = False
        self.round_active = True
        if self.track_eye:
            self._highlight_queen_card(False)
        self._set_status('Click the queen.', TEXT)
        self.shuffle_btn.configure(state='disabled')
        self.solution_btn.configure(state='normal')

    def _highlight_queen_card(self, on: bool) -> None:
        if self.game is None:
            return
        for c in self.cards:
            c.set_highlight(on and c.value == QUEEN)

    # ---------------- Picking ----------------
    def _on_canvas_click(self, event) -> None:
        if not self.round_active or self.shuffling or self.game is None:
            return
        # Determine which slot was clicked.
        for slot in range(NUM_CARDS):
            cx = _slot_x(slot)
            cy = _slot_y()
            if abs(event.x - cx) <= CARD_W / 2 and abs(event.y - cy) <= CARD_H / 2:
                self._pick(slot)
                return

    def _pick(self, slot: int) -> None:
        if self.game is None or not self.round_active:
            return
        won = self.game.pick(slot)
        # Reveal all cards.
        for c in self.cards:
            c.set_face_up(True)
        self.cards[slot].set_highlight(True)
        if won:
            self.wins += 1
            self.streak = self.streak + 1 if self.streak >= 0 else 1
            self._set_status('You win! You tracked the queen.', WIN)
        else:
            self.losses += 1
            self.streak = self.streak - 1 if self.streak <= 0 else -1
            self._set_status(
                f'House wins. Queen was at position {self.game.queen_index + 1}.',
                LOSE,
            )
        self.round_active = False
        self.solution_btn.configure(state='normal')
        self._update_stats()

    def _update_stats(self) -> None:
        total = self.wins + self.losses
        acc = f'{(self.wins / total * 100):.0f}%' if total else '—'
        streak_txt = (f'+{self.streak}' if self.streak > 0
                      else (str(self.streak) if self.streak < 0 else '0'))
        self.stats_label.configure(
            text=(f'Wins: {self.wins}   Losses: {self.losses}   '
                  f'Streak: {streak_txt}   Accuracy: {acc}'),
        )

    # ---------------- Solution replay ----------------
    def _replay_solution(self) -> None:
        """Re-run the shuffle from the initial state with the queen visible
        the whole time, so the player can see how they were misdirected."""
        if self.shuffling or self.game is None:
            return
        # Reset card widgets back to initial positions, queen face up.
        self.canvas.delete('all')
        initial = ['_'] * NUM_CARDS
        initial[self.game.initial_queen_index] = QUEEN
        self.cards = [CardWidget(self.canvas, i, initial[i]) for i in range(NUM_CARDS)]
        for c in self.cards:
            c.set_face_up(True)
        self._highlight_queen_card(True)
        self.shuffling = True
        self.round_active = False
        self.shuffle_btn.configure(state='disabled')
        self.solution_btn.configure(state='disabled')
        self._set_status('Replay — watch the queen.', DIM)
        self._pending_swaps = list(self.game.history)
        self.after(self.swap_ms // 2, self._next_swap_step_replay)

    def _next_swap_step_replay(self) -> None:
        if not self._pending_swaps:
            self.shuffling = False
            self._set_status(
                f'Queen ended at position {self.game.queen_index + 1}.', DIM,
            )
            self.solution_btn.configure(state='normal')
            return
        i, j = self._pending_swaps.pop(0)
        if i == j:
            self.after(self.swap_ms, self._next_swap_step_replay)
            return
        a = next(c for c in self.cards if c.slot == i)
        b = next(c for c in self.cards if c.slot == j)
        self._animate_swap(a, b, on_done=self._next_swap_step_replay)

    # ---------------- Helpers ----------------
    def _set_status(self, text: str, color: str = TEXT) -> None:
        self.status.configure(text=text, text_color=color)


if __name__ == '__main__':
    ThreeCardApp().mainloop()
