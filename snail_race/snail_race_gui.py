"""Snail Race — CustomTkinter GUI.

A Tk Canvas race-track with one horizontal lane per snail. Each snail is
drawn as a coloured pill with the snail emoji 🐌 at its leading edge; on
every animation tick the engine advances the field, the canvas redraws,
and a sportsbook-style odds panel updates the implied win probability
for each runner. The bet panel mirrors the cho_han GUI: bankroll +
wager slider, lock-in bet, race button, winner reveal banner.

Twist: each snail has a personality (mean speed + variance). The odds
panel shows live decimal odds and pays out at those odds on a win.

Run:
    uv run python snail_race/snail_race_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from snail_race import (
    MIN_WAGER,
    SNAILS,
    STARTING_BALANCE,
    WAGER_STEP,
    Race,
    implied_odds,
    settle_bet,
)

# Palette — dark "track at dusk" with bright lane stripes.
BG = '#0b1220'
PANEL = '#111a2e'
PANEL_2 = '#1b2542'
ACCENT = '#38bdf8'   # sky-400
ACCENT_DIM = '#1d4ed8'
GOLD = '#f59e0b'
TEXT = '#e2e8f0'
MUTED = '#94a3b8'
GREEN = '#22c55e'
RED = '#ef4444'

TRACK_BG = '#0f172a'
TRACK_LINE = '#475569'
LANE_BG = '#1e293b'
FINISH_LINE = '#fbbf24'

TITLE_FONT = ('Segoe UI', 24, 'bold')
SUB_FONT = ('Segoe UI', 12)
BIG_FONT = ('Segoe UI', 22, 'bold')
LABEL_FONT = ('Segoe UI', 13)
BTN_FONT = ('Segoe UI', 13, 'bold')
SNAIL_FONT = ('Segoe UI Emoji', 18)

NUM_SNAILS = 4
TRACK_LENGTH = 40

LANE_HEIGHT = 48
LANE_PAD = 8
TRACK_LEFT = 110     # space for the snail name on the left
TRACK_RIGHT_PAD = 24

DEFAULT_TICK_MS = 130


class SnailRaceApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Snail Race  🐌')
        self.geometry('960x720')
        self.minsize(880, 660)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.balance = STARTING_BALANCE
        self.wager = MIN_WAGER * 5
        self.bet_snail: int | None = None
        self.race: Race | None = None
        self.odds: list[float] = []
        self.tick_ms = DEFAULT_TICK_MS
        self.animating = False

        # Keep the canvas item ids per lane so we can move them every frame.
        self._lane_items: list[dict] = []  # [{'pill': id, 'emoji': id}, ...]

        self._build_ui()
        self._new_race()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        # Header.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='🐌  SNAIL RACE  🐌',
                     font=TITLE_FONT, text_color=ACCENT).pack()
        ctk.CTkLabel(header,
                     text=('Pick a snail. Place a wager. '
                           'Pay out at live implied odds.'),
                     font=SUB_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Bottom status bar (packed first so it pins).
        self.status = ctk.CTkLabel(self, text='Pick a snail to bet on.',
                                   font=('Segoe UI', 13), text_color=TEXT)
        self.status.pack(side='bottom', pady=(2, 10))

        # Bottom controls.
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='bottom', padx=20, pady=(4, 4), fill='x')

        # Wager slider row.
        wager_row = ctk.CTkFrame(controls, fg_color='transparent')
        wager_row.pack(padx=14, pady=(10, 4), fill='x')
        self.wager_label = ctk.CTkLabel(wager_row, text='Wager: 0',
                                        font=('Segoe UI', 14, 'bold'),
                                        text_color=GOLD,
                                        width=160, anchor='w')
        self.wager_label.pack(side='left')
        self.wager_slider = ctk.CTkSlider(
            wager_row,
            from_=MIN_WAGER, to=max(STARTING_BALANCE, MIN_WAGER * 2),
            number_of_steps=max(
                1, (STARTING_BALANCE - MIN_WAGER) // WAGER_STEP),
            command=self._on_wager_slider,
            button_color=ACCENT, button_hover_color='#7dd3fc',
            progress_color=ACCENT_DIM, fg_color='#1e293b')
        self.wager_slider.set(self.wager)
        self.wager_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Speed slider row.
        speed_row = ctk.CTkFrame(controls, fg_color='transparent')
        speed_row.pack(padx=14, pady=(0, 4), fill='x')
        ctk.CTkLabel(speed_row, text='Speed', font=('Segoe UI', 12),
                     text_color=MUTED, width=160, anchor='w').pack(side='left')
        self.speed_slider = ctk.CTkSlider(
            speed_row, from_=30, to=300,
            command=self._on_speed_slider,
            button_color=GOLD, button_hover_color='#fcd34d',
            progress_color='#7c2d12', fg_color='#1e293b')
        self.speed_slider.set(DEFAULT_TICK_MS)
        self.speed_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Action buttons.
        btn_row = ctk.CTkFrame(controls, fg_color='transparent')
        btn_row.pack(padx=14, pady=(4, 10), fill='x')
        self.start_btn = ctk.CTkButton(
            btn_row, text='Start race', font=BTN_FONT,
            fg_color=GREEN, hover_color='#16a34a', text_color='#0b1220',
            height=42, command=self._start_race)
        self.start_btn.pack(side='left', expand=True, fill='x', padx=(0, 6))
        self.reset_btn = ctk.CTkButton(
            btn_row, text='Reset bankroll', font=BTN_FONT,
            fg_color=PANEL_2, hover_color='#334155', text_color=TEXT,
            width=140, height=42, command=self._reset_bankroll)
        self.reset_btn.pack(side='left')

        # Body: track on the left, odds + bankroll on the right.
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=14, pady=(8, 4))

        # Race-track canvas.
        track_frame = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=14)
        track_frame.pack(side='left', fill='both', expand=True, padx=(0, 7))

        ctk.CTkLabel(track_frame, text='Race track',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(10, 0))

        canvas_h = NUM_SNAILS * (LANE_HEIGHT + LANE_PAD) + LANE_PAD * 2 + 30
        self.canvas = tk.Canvas(track_frame, height=canvas_h,
                                bg=TRACK_BG, highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=12, pady=(8, 12))
        # Re-draw lanes on resize so the track scales with the window.
        self.canvas.bind('<Configure>', lambda e: self._draw_track_static())

        # Odds + bankroll panel.
        right = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=14)
        right.pack(side='left', fill='both', expand=False, padx=(7, 0))
        right.configure(width=280)

        ctk.CTkLabel(right, text='Bankroll', font=('Segoe UI', 12),
                     text_color=MUTED).pack(pady=(12, 0))
        self.balance_label = ctk.CTkLabel(right, text='', font=BIG_FONT,
                                          text_color=GOLD)
        self.balance_label.pack(pady=(0, 8))

        ctk.CTkLabel(right, text='Live odds — pick your snail',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(8, 4))

        self.odds_frame = ctk.CTkFrame(right, fg_color='transparent')
        self.odds_frame.pack(fill='x', expand=False, padx=10)
        self.snail_buttons: list[ctk.CTkButton] = []

        ctk.CTkLabel(right,
                     text='Higher odds = riskier pick, bigger payout.',
                     font=('Segoe UI', 10), text_color=MUTED,
                     wraplength=240, justify='left').pack(pady=(8, 6),
                                                          padx=10, anchor='w')

        self.bet_label = ctk.CTkLabel(right, text='No bet placed.',
                                      font=('Segoe UI', 12), text_color=TEXT)
        self.bet_label.pack(pady=(2, 12), padx=10)

    # ------------------------------------------------------------- track

    def _draw_track_static(self) -> None:
        """Re-draw lane backgrounds, labels, and finish line. Called on
        every resize and at the start of each race."""
        c = self.canvas
        c.delete('static')
        # Snake lane stripes.
        w = c.winfo_width() or 600
        h = c.winfo_height() or 360
        track_w = max(120, w - TRACK_LEFT - TRACK_RIGHT_PAD)
        for i in range(NUM_SNAILS):
            y0 = LANE_PAD + i * (LANE_HEIGHT + LANE_PAD)
            y1 = y0 + LANE_HEIGHT
            # Lane background.
            c.create_rectangle(TRACK_LEFT, y0,
                               TRACK_LEFT + track_w, y1,
                               fill=LANE_BG, outline=TRACK_LINE,
                               width=1, tags='static')
            # Snail name on left.
            if self.race is not None and i < len(self.race.personalities):
                p = self.race.personalities[i]
                c.create_text(TRACK_LEFT - 10, (y0 + y1) // 2,
                              text=p.name, fill=TEXT, anchor='e',
                              font=('Segoe UI', 11, 'bold'),
                              tags='static')
                c.create_text(20, (y0 + y1) // 2,
                              text=str(i + 1), fill=p.color, anchor='w',
                              font=('Segoe UI', 18, 'bold'),
                              tags='static')
        # Finish line (vertical dashed).
        finish_x = TRACK_LEFT + track_w
        c.create_line(finish_x, LANE_PAD,
                      finish_x, h - LANE_PAD,
                      fill=FINISH_LINE, dash=(4, 3), width=2,
                      tags='static')
        c.create_text(finish_x, h - 10, text='FINISH',
                      fill=FINISH_LINE, anchor='s',
                      font=('Segoe UI', 9, 'bold'),
                      tags='static')

        # Re-draw the moving snails on top.
        self._draw_snails()

    def _draw_snails(self) -> None:
        """Place / refresh the snail glyphs at their current positions."""
        c = self.canvas
        c.delete('snail')
        if self.race is None:
            self._lane_items = []
            return
        w = c.winfo_width() or 600
        track_w = max(120, w - TRACK_LEFT - TRACK_RIGHT_PAD)
        self._lane_items = []
        for i, p in enumerate(self.race.personalities):
            y0 = LANE_PAD + i * (LANE_HEIGHT + LANE_PAD)
            y1 = y0 + LANE_HEIGHT
            yc = (y0 + y1) // 2
            # 0..1 progress.
            frac = self.race.positions[i] / self.race.track_length
            x_lead = TRACK_LEFT + frac * track_w
            x_tail = max(TRACK_LEFT + 4, x_lead - 28)
            # Pill behind the snail.
            pill = c.create_rectangle(x_tail, yc - 10, x_lead, yc + 10,
                                      fill=p.color, outline='',
                                      tags=('snail',))
            emoji = c.create_text(x_lead - 14, yc, text='🐌',
                                  font=SNAIL_FONT, anchor='c',
                                  tags=('snail',))
            self._lane_items.append({'pill': pill, 'emoji': emoji})

    # --------------------------------------------------------- state utils

    def _refresh_balance(self) -> None:
        self.balance_label.configure(text=f'$ {self.balance:,}')
        upper = max(self.balance, MIN_WAGER)
        self.wager_slider.configure(to=upper)
        if self.wager > self.balance:
            self.wager = max(MIN_WAGER, self.balance)
            self.wager_slider.set(self.wager)
        self._refresh_wager()

    def _refresh_wager(self) -> None:
        self.wager_label.configure(text=f'Wager: $ {self.wager:,}')

    def _refresh_bet_label(self) -> None:
        if self.bet_snail is None or self.race is None:
            self.bet_label.configure(text='No bet placed.')
        else:
            p = self.race.personalities[self.bet_snail]
            o = self.odds[self.bet_snail]
            self.bet_label.configure(
                text=f'Bet: {p.name}  @ {o:.2f}x  (${self.wager:,})')

    def _on_wager_slider(self, value: float) -> None:
        snapped = max(MIN_WAGER,
                      int(round(value / WAGER_STEP) * WAGER_STEP))
        snapped = min(snapped, max(self.balance, MIN_WAGER))
        self.wager = snapped
        self._refresh_wager()
        self._refresh_bet_label()

    def _on_speed_slider(self, value: float) -> None:
        # Slider value is "ms per tick" — lower = faster.
        self.tick_ms = int(value)

    def _build_odds_buttons(self) -> None:
        for child in self.odds_frame.winfo_children():
            child.destroy()
        self.snail_buttons = []
        if self.race is None:
            return
        for i, p in enumerate(self.race.personalities):
            o = self.odds[i]
            btn = ctk.CTkButton(
                self.odds_frame,
                text=f'{i + 1}.  {p.name:<10}  {o:5.2f}x',
                font=('Segoe UI', 12, 'bold'),
                fg_color=p.color, hover_color=p.color,
                text_color='#0b1220', anchor='w',
                height=32,
                command=lambda i=i: self._pick_snail(i))
            btn.pack(fill='x', expand=False, pady=2)
            self.snail_buttons.append(btn)

    # ----------------------------------------------------------- gameplay

    def _new_race(self) -> None:
        self.race = Race(num_snails=NUM_SNAILS,
                         track_length=TRACK_LENGTH,
                         rng=self.rng)
        self.odds = implied_odds(self.race.personalities,
                                 self.race.track_length)
        self.bet_snail = None
        self._build_odds_buttons()
        self._refresh_balance()
        self._refresh_bet_label()
        self._draw_track_static()
        self.start_btn.configure(state='normal', text='Start race')
        self.status.configure(
            text='Pick a snail and press Start race.', text_color=TEXT)

    def _pick_snail(self, idx: int) -> None:
        if self.animating:
            return
        if self.balance <= 0:
            self.status.configure(
                text='Out of money. Reset bankroll to play again.',
                text_color=RED)
            return
        self.bet_snail = idx
        # Highlight the picked button.
        for j, btn in enumerate(self.snail_buttons):
            if j == idx:
                btn.configure(border_width=3, border_color=GOLD)
            else:
                btn.configure(border_width=0)
        self._refresh_bet_label()
        self.status.configure(
            text=f'Locked in: {self.race.personalities[idx].name}.',
            text_color=ACCENT)

    def _start_race(self) -> None:
        if self.animating:
            return
        if self.bet_snail is None:
            self.status.configure(text='Pick a snail first.',
                                  text_color=RED)
            return
        if self.balance <= 0:
            self.status.configure(text='Out of money — reset bankroll.',
                                  text_color=RED)
            return
        if self.wager > self.balance:
            self.wager = self.balance
            self._refresh_wager()

        self.animating = True
        self.start_btn.configure(state='disabled')
        for btn in self.snail_buttons:
            btn.configure(state='disabled')
        self.status.configure(text='They\'re off!', text_color=ACCENT)
        self._tick_race()

    def _tick_race(self) -> None:
        assert self.race is not None
        self.race.step()
        self._draw_snails()
        if self.race.is_done():
            self._finish_race()
        else:
            self.after(self.tick_ms, self._tick_race)

    def _finish_race(self) -> None:
        assert self.race is not None
        winner = self.race.winner()
        wp = self.race.personalities[winner]
        result = settle_bet(self.bet_snail, self.wager, self.balance,
                            winner, self.odds[self.bet_snail])
        self.balance = result['balance']
        self._refresh_balance()
        if result['win']:
            self.status.configure(
                text=(f"{wp.name} wins! You took home "
                      f"${result['delta']:+,} @ {self.odds[self.bet_snail]:.2f}x."),
                text_color=GREEN)
        else:
            self.status.configure(
                text=(f"{wp.name} wins. You lost ${self.wager:,}. "
                      f"Your pick finished "
                      f"{self.race.positions[self.bet_snail]}/{self.race.track_length}."),
                text_color=RED)
        self.animating = False
        # Re-enable controls; queue up a fresh race.
        for btn in self.snail_buttons:
            btn.configure(state='normal')
        self.start_btn.configure(state='normal', text='Race again')
        self.start_btn.configure(command=self._restart)

    def _restart(self) -> None:
        if self.balance <= 0:
            self.status.configure(
                text='Out of money — reset bankroll to play again.',
                text_color=RED)
            return
        self.start_btn.configure(command=self._start_race)
        self._new_race()

    def _reset_bankroll(self) -> None:
        if self.animating:
            return
        self.balance = STARTING_BALANCE
        self.wager = MIN_WAGER * 5
        self.wager_slider.set(self.wager)
        self._refresh_balance()
        self.start_btn.configure(command=self._start_race)
        self._new_race()
        self.status.configure(text='Bankroll reset. Pick a snail.',
                              text_color=TEXT)


if __name__ == '__main__':
    SnailRaceApp().mainloop()
