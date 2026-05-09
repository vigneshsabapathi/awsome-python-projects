"""Cho-Han — CustomTkinter GUI.

A traditional-styled Japanese gambling table. The dealer's bamboo cup
(written 丁 cho on one side, 半 han on the other) hides two rolling dice;
when the cup lifts, the parity of the sum decides the round.

Twist: a live bankroll history line chart and a Monte Carlo
"ruin probability" estimate using the current wager and balance.

Run:
    uv run python cho_han/cho_han_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from cho_han import (
    CHO,
    HAN,
    KANJI,
    MIN_WAGER,
    STARTING_BALANCE,
    WAGER_STEP,
    play_round,
    roll_dice,
    ruin_probability,
)

# Tatami / lacquer palette: deep red, gold, charcoal, parchment.
BG = '#1a0f0c'        # near-black lacquer background
PANEL = '#2a1410'     # panel
RED = '#a3142b'       # hanten red
GOLD = '#d4a04c'      # antique gold
GOLD_DIM = '#8a6a30'
PARCH = '#f1e3c2'     # parchment text
MUTED = '#a89578'
GREEN = '#3f8a4a'
LOSE = '#7c1f1f'

CUP_BG = '#0e0807'
CUP_FG = GOLD

TITLE_FONT = ('Yu Mincho', 30, 'bold')
KANJI_FONT = ('Yu Mincho', 64, 'bold')
DICE_FONT = ('Segoe UI Symbol', 60, 'bold')
LABEL_FONT = ('Segoe UI', 13)
BIG_FONT = ('Segoe UI', 26, 'bold')
BTN_FONT = ('Segoe UI', 14, 'bold')

DICE_FACES = {1: '⚀', 2: '⚁', 3: '⚂',
              4: '⚃', 5: '⚄', 6: '⚅'}

ANIM_FRAMES = 5
ANIM_DELAY_MS = 90


class ChoHanApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Cho-Han  丁 半')
        self.geometry('880x720')
        self.minsize(820, 640)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.balance = STARTING_BALANCE
        self.wager = MIN_WAGER * 5
        self.history: list[int] = [self.balance]
        self.animating = False

        self._build_ui()
        self._refresh_balance()
        self._refresh_wager()
        self._update_ruin()
        self._redraw_chart()

    # ----- layout -----------------------------------------------------------

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='丁  CHO-HAN  半',
                     font=TITLE_FONT, text_color=GOLD).pack()
        ctk.CTkLabel(header,
                     text='Bet on the parity of two dice — chō (even) or han (odd)',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # --- Bottom bar (packed first so it's pinned regardless of layout) ---
        self.status = ctk.CTkLabel(self, text='Place your bet.',
                                   font=('Segoe UI', 13),
                                   text_color=PARCH)
        self.status.pack(side='bottom', pady=(2, 10))

        bet_row = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        bet_row.pack(side='bottom', padx=20, pady=(4, 4), fill='x')

        # Wager slider row
        wager_row = ctk.CTkFrame(bet_row, fg_color='transparent')
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
            button_color=GOLD, button_hover_color='#e6b85a',
            progress_color=RED, fg_color='#3a1f1a')
        self.wager_slider.set(self.wager)
        self.wager_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Bet buttons
        btn_row = ctk.CTkFrame(bet_row, fg_color='transparent')
        btn_row.pack(padx=14, pady=(4, 10), fill='x')
        self.cho_btn = ctk.CTkButton(
            btn_row, text='丁  CHO  (even)', font=BTN_FONT,
            fg_color=RED, hover_color='#c61e36', text_color=PARCH,
            height=44, command=lambda: self._place_bet(CHO))
        self.cho_btn.pack(side='left', expand=True, fill='x', padx=(0, 6))
        self.han_btn = ctk.CTkButton(
            btn_row, text='半  HAN  (odd)', font=BTN_FONT,
            fg_color='#1f3a5a', hover_color='#2a4d76', text_color=PARCH,
            height=44, command=lambda: self._place_bet(HAN))
        self.han_btn.pack(side='left', expand=True, fill='x', padx=(0, 6))
        self.reset_btn = ctk.CTkButton(
            btn_row, text='Reset', font=BTN_FONT,
            fg_color='#3a1f1a', hover_color='#5a2f29', text_color=GOLD,
            width=90, height=44, command=self._reset)
        self.reset_btn.pack(side='left')

        # --- Middle: cup + balance/chart side-by-side ---
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=14, pady=(8, 4))

        left = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=14)
        left.pack(side='left', fill='both', expand=False, padx=(0, 7))
        left.configure(width=320)

        ctk.CTkLabel(left, text='Dealer\'s Cup',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(12, 0))

        # Cup: when "down", we show large kanji 丁/半 on its sides.
        # When "up" (revealed), we show the two dice faces.
        self.cup_canvas = ctk.CTkFrame(left, fg_color=CUP_BG, corner_radius=14,
                                       border_color=GOLD_DIM, border_width=2)
        self.cup_canvas.pack(padx=20, pady=12, fill='both', expand=True)

        self.cup_kanji = ctk.CTkLabel(self.cup_canvas, text='丁  半',
                                      font=KANJI_FONT, text_color=GOLD)
        self.cup_kanji.pack(expand=True, pady=(40, 6))

        self.cup_status = ctk.CTkLabel(self.cup_canvas,
                                       text='Cup is down.',
                                       font=('Segoe UI', 12),
                                       text_color=MUTED)
        self.cup_status.pack(pady=(0, 14))

        self.dice_frame = ctk.CTkFrame(self.cup_canvas, fg_color='transparent')
        self.dice_label = ctk.CTkLabel(self.dice_frame, text='',
                                       font=DICE_FONT, text_color=PARCH)
        self.dice_label.pack()
        self.dice_sum = ctk.CTkLabel(self.dice_frame, text='',
                                     font=('Segoe UI', 14, 'bold'),
                                     text_color=GOLD)
        self.dice_sum.pack(pady=(2, 0))

        right = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=14)
        right.pack(side='left', fill='both', expand=True, padx=(7, 0))

        ctk.CTkLabel(right, text='Balance', font=('Segoe UI', 12),
                     text_color=MUTED).pack(pady=(12, 0))
        self.balance_label = ctk.CTkLabel(right, text='', font=BIG_FONT,
                                          text_color=GOLD)
        self.balance_label.pack(pady=(0, 4))

        self.ruin_label = ctk.CTkLabel(
            right, text='', font=('Segoe UI', 11), text_color=MUTED)
        self.ruin_label.pack(pady=(0, 4))

        # Bankroll history chart
        chart_frame = ctk.CTkFrame(right, fg_color=PANEL)
        chart_frame.pack(fill='both', expand=True, padx=10, pady=(4, 12))
        self.fig = Figure(figsize=(5, 3), facecolor=PANEL, dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    def _style_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor(PANEL)
        for spine in ax.spines.values():
            spine.set_color(GOLD_DIM)
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.title.set_color(GOLD)
        ax.grid(True, color='#3a1f1a', linewidth=0.7)

    # ----- state updates ----------------------------------------------------

    def _refresh_balance(self) -> None:
        self.balance_label.configure(text=f'¥ {self.balance:,}')
        # Cap wager slider at current balance to avoid invalid bets.
        upper = max(self.balance, MIN_WAGER)
        self.wager_slider.configure(to=upper)
        if self.wager > self.balance:
            self.wager = max(MIN_WAGER, self.balance)
            self.wager_slider.set(self.wager)
        self._refresh_wager()

    def _refresh_wager(self) -> None:
        self.wager_label.configure(text=f'Wager: ¥ {self.wager:,}')

    def _on_wager_slider(self, value: float) -> None:
        # Snap to WAGER_STEP for tidy values.
        snapped = max(MIN_WAGER,
                      int(round(value / WAGER_STEP) * WAGER_STEP))
        snapped = min(snapped, max(self.balance, MIN_WAGER))
        self.wager = snapped
        self._refresh_wager()
        self._update_ruin()

    def _update_ruin(self) -> None:
        if self.balance <= 0 or self.wager <= 0:
            self.ruin_label.configure(text='')
            return
        # Quick Monte Carlo — small trial count keeps the UI responsive.
        p = ruin_probability(self.balance, self.wager,
                             rounds=200, trials=1500,
                             rng=self.rng)
        self.ruin_label.configure(
            text=(f'Ruin risk @ this wager (200 rounds): {p * 100:.1f}%'))

    def _redraw_chart(self) -> None:
        ax = self.ax
        ax.clear()
        self._style_axes()
        ax.set_title('Bankroll history')
        ax.set_xlabel('Round')
        ax.set_ylabel('¥')
        xs = list(range(len(self.history)))
        ax.plot(xs, self.history, color=GOLD, linewidth=1.6, marker='o',
                markersize=3, markerfacecolor=RED, markeredgecolor=GOLD)
        ax.axhline(STARTING_BALANCE, color=GOLD_DIM, linewidth=0.8,
                   linestyle='--', alpha=0.6)
        ax.set_xlim(0, max(10, len(self.history)))
        lo = min(self.history + [0])
        hi = max(self.history + [STARTING_BALANCE])
        pad = max(200, (hi - lo) * 0.1)
        ax.set_ylim(lo - pad, hi + pad)
        self.fig.tight_layout()
        self.canvas.draw()

    # ----- gameplay ---------------------------------------------------------

    def _set_buttons_enabled(self, enabled: bool) -> None:
        state = 'normal' if enabled else 'disabled'
        self.cho_btn.configure(state=state)
        self.han_btn.configure(state=state)
        self.wager_slider.configure(state=state)
        self.reset_btn.configure(state=state)

    def _show_cup_down(self) -> None:
        self.dice_frame.pack_forget()
        self.cup_kanji.configure(text='丁  半', text_color=GOLD)
        self.cup_status.configure(text='Cup is down. Place your bet.',
                                  text_color=MUTED)

    def _show_dice(self, d1: int, d2: int) -> None:
        # Hide kanji, show dice. cup_kanji frame stays for layout consistency.
        self.cup_kanji.configure(text='')
        self.dice_label.configure(text=f'{DICE_FACES[d1]}   {DICE_FACES[d2]}')
        self.dice_sum.configure(text=f'{d1} + {d2} = {d1 + d2}')
        if not self.dice_frame.winfo_ismapped():
            self.dice_frame.pack(pady=(0, 14))

    def _place_bet(self, bet: str) -> None:
        if self.animating:
            return
        if self.balance <= 0:
            self.status.configure(text='Out of money. Press Reset to play again.',
                                  text_color=LOSE)
            return
        if self.wager > self.balance:
            self.wager = self.balance
            self._refresh_wager()

        self.animating = True
        self._set_buttons_enabled(False)
        self.cup_status.configure(text='The dealer shakes the cup…',
                                  text_color=PARCH)
        self.status.configure(
            text=f'You bet {KANJI[bet]} ({bet}) for ¥ {self.wager:,}',
            text_color=PARCH)
        self._animate_roll(bet, ANIM_FRAMES)

    def _animate_roll(self, bet: str, frames_left: int) -> None:
        if frames_left > 0:
            d1, d2 = roll_dice(self.rng)
            self._show_dice(d1, d2)
            self.cup_kanji.configure(text='')
            self.after(ANIM_DELAY_MS,
                       lambda: self._animate_roll(bet, frames_left - 1))
        else:
            self._reveal(bet)

    def _reveal(self, bet: str) -> None:
        result = play_round(bet, self.wager, self.balance, rng=self.rng)
        d1, d2 = result['dice']
        self._show_dice(d1, d2)
        kanji = KANJI[result['result']]
        if result['win']:
            self.cup_status.configure(
                text=f"Cup lifts → {kanji} ({result['result']})",
                text_color=GREEN)
            self.status.configure(
                text=f"You won ¥ {result['wager']:,}!",
                text_color=GREEN)
        else:
            self.cup_status.configure(
                text=f"Cup lifts → {kanji} ({result['result']})",
                text_color='#ff8a8a')
            self.status.configure(
                text=f"You lost ¥ {result['wager']:,}.",
                text_color='#ff8a8a')

        self.balance = result['balance']
        self.history.append(self.balance)
        self._refresh_balance()
        self._update_ruin()
        self._redraw_chart()
        self.animating = False
        self._set_buttons_enabled(True)
        if self.balance <= 0:
            self.status.configure(
                text='You are out of money. Press Reset to play again.',
                text_color=LOSE)
            self.cho_btn.configure(state='disabled')
            self.han_btn.configure(state='disabled')

    def _reset(self) -> None:
        self.balance = STARTING_BALANCE
        self.wager = MIN_WAGER * 5
        self.history = [self.balance]
        self.wager_slider.set(self.wager)
        self._show_cup_down()
        self._refresh_balance()
        self._update_ruin()
        self._redraw_chart()
        self.status.configure(text='Fresh table. Place your bet.',
                              text_color=PARCH)


if __name__ == '__main__':
    ChoHanApp().mainloop()
