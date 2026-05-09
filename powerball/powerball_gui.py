"""Powerball — CustomTkinter GUI.

Pick-your-numbers panel (5 whites + 1 red), Quick-pick / Draw / Simulate
controls, embedded matplotlib bar chart comparing empirical vs theoretical
hit rates over N simulated tickets. Includes an EV-vs-jackpot mini-readout.

Run:
    uv run python powerball/powerball_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from powerball import (
    RED_POOL,
    THEORETICAL_PROBS,
    TICKET_COST,
    TIERS,
    WHITE_POOL,
    WHITE_PICK,
    break_even_jackpot,
    draw,
    expected_value,
    format_drawing,
    prize_for,
    quick_pick,
    score,
    simulate,
)

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
WHITE_BTN = '#e2e8f0'
RED_BTN = '#ef4444'
GOLD = '#f59e0b'

TRIALS_OPTIONS = (1_000, 10_000, 100_000)
DEFAULT_TRIALS = 10_000
DEFAULT_JACKPOT = 100_000_000

# Tiers we plot (skip 'None' — it dominates everything else by 70x).
PLOT_TIERS = tuple(t for t in TIERS if t != 'None')


class PowerballApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Powerball Lottery')
        self.geometry('960x780')
        self.minsize(820, 700)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.selected_whites: set[int] = set()
        self.selected_pb: int | None = None
        self.last_drawing: dict | None = None
        self.last_tier: str | None = None
        self.sim_counts: dict[str, int] | None = None
        self.sim_total = 0
        self.jackpot = DEFAULT_JACKPOT
        self.trials = DEFAULT_TRIALS

        self.white_buttons: dict[int, ctk.CTkButton] = {}
        self.red_buttons: dict[int, ctk.CTkButton] = {}

        self._build_ui()
        self._update_ticket_display()
        self._update_ev_label()
        self._redraw_chart()

    # ---- UI construction ---------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='POWERBALL LOTTERY',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(
            header,
            text=(f'Pick {WHITE_PICK} whites (1..{WHITE_POOL}) + '
                  f'1 red (1..{RED_POOL}). Jackpot odds: 1 in 292,201,338.'),
            font=('Segoe UI', 12), text_color=MUTED).pack(pady=(2, 0))

        # Two-column main area: numbers panel (left), chart (right).
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=12, pady=(8, 4))

        left = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=10)
        left.pack(side='left', fill='y', padx=(0, 6))

        right = ctk.CTkFrame(body, fg_color=BG)
        right.pack(side='left', fill='both', expand=True, padx=(6, 0))

        self._build_picker(left)
        self._build_chart(right)
        self._build_controls()
        self._build_status()

    def _build_picker(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text='Your ticket',
                     font=('Segoe UI', 14, 'bold'),
                     text_color=FG).pack(pady=(10, 4), padx=12, anchor='w')

        self.ticket_label = ctk.CTkLabel(
            parent, text='', font=('Consolas', 13), text_color=ACCENT,
            justify='left', anchor='w')
        self.ticket_label.pack(padx=12, pady=(0, 8), anchor='w')

        ctk.CTkLabel(parent, text=f'White balls (pick {WHITE_PICK})',
                     font=('Segoe UI', 11, 'bold'),
                     text_color=MUTED).pack(padx=12, anchor='w')
        white_grid = ctk.CTkFrame(parent, fg_color='transparent')
        white_grid.pack(padx=10, pady=(2, 8))
        cols = 7
        for i, n in enumerate(range(1, WHITE_POOL + 1)):
            r, c = divmod(i, cols)
            btn = ctk.CTkButton(
                white_grid, text=f'{n:2d}', width=36, height=28,
                fg_color=PANEL, hover_color='#334155',
                text_color=WHITE_BTN, border_width=1, border_color='#334155',
                font=('Consolas', 11, 'bold'),
                command=lambda x=n: self._toggle_white(x))
            btn.grid(row=r, column=c, padx=2, pady=2)
            self.white_buttons[n] = btn

        ctk.CTkLabel(parent, text='Powerball (pick 1)',
                     font=('Segoe UI', 11, 'bold'),
                     text_color=MUTED).pack(padx=12, anchor='w')
        red_grid = ctk.CTkFrame(parent, fg_color='transparent')
        red_grid.pack(padx=10, pady=(2, 8))
        for i, n in enumerate(range(1, RED_POOL + 1)):
            r, c = divmod(i, cols)
            btn = ctk.CTkButton(
                red_grid, text=f'{n:2d}', width=36, height=28,
                fg_color=PANEL, hover_color='#7f1d1d',
                text_color=WHITE_BTN, border_width=1, border_color='#334155',
                font=('Consolas', 11, 'bold'),
                command=lambda x=n: self._select_pb(x))
            btn.grid(row=r, column=c, padx=2, pady=2)
            self.red_buttons[n] = btn

        # Action buttons row.
        actions = ctk.CTkFrame(parent, fg_color='transparent')
        actions.pack(padx=10, pady=(4, 12), fill='x')
        ctk.CTkButton(actions, text='Quick pick', command=self._quick_pick,
                      font=('Segoe UI', 12, 'bold')).pack(
            side='left', padx=2, fill='x', expand=True)
        ctk.CTkButton(actions, text='Clear', command=self._clear,
                      fg_color='#475569', hover_color='#334155',
                      font=('Segoe UI', 12)).pack(
            side='left', padx=2, fill='x', expand=True)

    def _build_chart(self, parent: ctk.CTkFrame) -> None:
        self.fig = Figure(figsize=(6, 4.5), facecolor=BG, dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    def _style_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_color('#334155')
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.title.set_color(FG)
        ax.grid(True, color='#1e293b', linewidth=0.8, axis='y')

    def _build_controls(self) -> None:
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='top', padx=12, pady=(4, 4), fill='x')

        row1 = ctk.CTkFrame(controls, fg_color='transparent')
        row1.pack(padx=14, pady=(10, 4), fill='x')

        ctk.CTkLabel(row1, text='Jackpot $:',
                     font=('Segoe UI', 12), text_color=FG).pack(side='left')
        self.jackpot_var = ctk.StringVar(value=f'{DEFAULT_JACKPOT:,}')
        self.jackpot_entry = ctk.CTkEntry(
            row1, width=130, textvariable=self.jackpot_var,
            font=('Consolas', 12))
        self.jackpot_entry.pack(side='left', padx=(6, 12))
        self.jackpot_entry.bind('<KeyRelease>', lambda _e: self._on_jackpot())
        self.jackpot_entry.bind('<FocusOut>', lambda _e: self._on_jackpot())

        ctk.CTkLabel(row1, text='Trials:',
                     font=('Segoe UI', 12), text_color=FG).pack(side='left')
        self.trials_var = ctk.StringVar(value=str(DEFAULT_TRIALS))
        for t in TRIALS_OPTIONS:
            label = f'{t // 1000}k' if t >= 1000 else str(t)
            ctk.CTkRadioButton(row1, text=label,
                               variable=self.trials_var, value=str(t),
                               font=('Segoe UI', 12)).pack(
                side='left', padx=(8, 0))

        self.draw_btn = ctk.CTkButton(
            row1, text='Draw', width=90, command=self._draw_one,
            fg_color=ACCENT, hover_color='#0ea5e9',
            text_color='#0f172a',
            font=('Segoe UI', 12, 'bold'))
        self.draw_btn.pack(side='right', padx=(8, 0))
        self.sim_btn = ctk.CTkButton(
            row1, text='Simulate', width=110, command=self._simulate,
            font=('Segoe UI', 12, 'bold'))
        self.sim_btn.pack(side='right', padx=(8, 0))

        row2 = ctk.CTkFrame(controls, fg_color='transparent')
        row2.pack(padx=14, pady=(2, 10), fill='x')
        self.ev_label = ctk.CTkLabel(
            row2, text='', font=('Consolas', 11),
            text_color=GOLD, justify='left', anchor='w')
        self.ev_label.pack(side='left', fill='x', expand=True)

    def _build_status(self) -> None:
        self.status = ctk.CTkLabel(
            self, text='Pick numbers (or Quick pick), then press Draw.',
            font=('Segoe UI', 12), text_color=MUTED, justify='center')
        self.status.pack(side='bottom', pady=(2, 10))

    # ---- ticket interaction ------------------------------------------------

    def _toggle_white(self, n: int) -> None:
        if n in self.selected_whites:
            self.selected_whites.remove(n)
        elif len(self.selected_whites) < WHITE_PICK:
            self.selected_whites.add(n)
        else:
            self.status.configure(text=f'You can only pick {WHITE_PICK} whites.')
            return
        self._refresh_white_buttons()
        self._update_ticket_display()

    def _select_pb(self, n: int) -> None:
        self.selected_pb = None if self.selected_pb == n else n
        self._refresh_red_buttons()
        self._update_ticket_display()

    def _refresh_white_buttons(self) -> None:
        for n, btn in self.white_buttons.items():
            if n in self.selected_whites:
                btn.configure(fg_color=WHITE_BTN, text_color='#0f172a',
                              border_color=WHITE_BTN)
            else:
                btn.configure(fg_color=PANEL, text_color=WHITE_BTN,
                              border_color='#334155')

    def _refresh_red_buttons(self) -> None:
        for n, btn in self.red_buttons.items():
            if n == self.selected_pb:
                btn.configure(fg_color=RED_BTN, text_color=FG,
                              border_color=RED_BTN)
            else:
                btn.configure(fg_color=PANEL, text_color=WHITE_BTN,
                              border_color='#334155')

    def _quick_pick(self) -> None:
        t = quick_pick(self.rng)
        self.selected_whites = set(t['whites'])
        self.selected_pb = t['powerball']
        self._refresh_white_buttons()
        self._refresh_red_buttons()
        self._update_ticket_display()
        self.status.configure(text='Quick-pick generated. Press Draw.')

    def _clear(self) -> None:
        self.selected_whites.clear()
        self.selected_pb = None
        self.last_drawing = None
        self.last_tier = None
        self._refresh_white_buttons()
        self._refresh_red_buttons()
        self._update_ticket_display()
        self.status.configure(text='Cleared.')

    def _ticket(self) -> dict | None:
        if len(self.selected_whites) != WHITE_PICK or self.selected_pb is None:
            return None
        return {'whites': tuple(sorted(self.selected_whites)),
                'powerball': self.selected_pb}

    def _update_ticket_display(self) -> None:
        whites_part = '  '.join(
            f'{n:2d}' for n in sorted(self.selected_whites)
        ) if self.selected_whites else '  ·  · · · ·'
        pb_part = f'{self.selected_pb:2d}' if self.selected_pb else ' ·'
        line1 = f'whites: [ {whites_part:<24} ]'
        line2 = f'PB:     {pb_part}'
        if self.last_tier and self.last_drawing is not None:
            prize = prize_for(self.last_tier, self.jackpot)
            line3 = f'\nLast: {format_drawing(self.last_drawing)}'
            line4 = f'\nResult: {self.last_tier}   prize ${prize:,}'
            self.ticket_label.configure(text=line1 + '\n' + line2 + line3 + line4)
        else:
            self.ticket_label.configure(text=line1 + '\n' + line2)

    # ---- jackpot / EV ------------------------------------------------------

    def _on_jackpot(self) -> None:
        raw = self.jackpot_var.get().replace(',', '').replace('$', '').strip()
        try:
            self.jackpot = max(0, int(raw)) if raw else 0
        except ValueError:
            return
        self._update_ev_label()
        self._update_ticket_display()

    def _update_ev_label(self) -> None:
        ev = expected_value(self.jackpot)
        ev_pre = expected_value(self.jackpot, tax_rate=0.0)
        be = break_even_jackpot()
        verdict = 'EV > cost ✓' if ev > TICKET_COST else 'EV < cost ✗'
        self.ev_label.configure(
            text=(f'EV/ticket: ${ev:6.3f} (after tax) | '
                  f'${ev_pre:6.3f} (pre-tax) | '
                  f'cost ${TICKET_COST}  [{verdict}]   '
                  f'Break-even jackpot: ${be:,.0f}'))

    # ---- draw / simulate ---------------------------------------------------

    def _draw_one(self) -> None:
        ticket = self._ticket()
        if ticket is None:
            self.status.configure(
                text=f'Pick {WHITE_PICK} whites and 1 powerball first '
                     f'(or use Quick pick).')
            return
        drawing = draw(self.rng)
        tier = score(ticket, drawing)
        self.last_drawing = drawing
        self.last_tier = tier
        prize = prize_for(tier, self.jackpot)
        self._update_ticket_display()
        if tier == '5+PB':
            self.status.configure(
                text=f'JACKPOT! ${prize:,}.  (1 in 292,201,338.)')
        elif tier == 'None':
            self.status.configure(text=f'No match. Drawn: {format_drawing(drawing)}')
        else:
            self.status.configure(
                text=f'Tier {tier}: ${prize:,}.  '
                     f'Drawn: {format_drawing(drawing)}')

    def _simulate(self) -> None:
        try:
            trials = int(self.trials_var.get())
        except ValueError:
            trials = DEFAULT_TRIALS
        ticket = self._ticket()  # may be None — that means quick-pick each play
        self.sim_btn.configure(state='disabled', text='Running…')
        self.update_idletasks()
        result = simulate(trials, rng=self.rng, ticket=ticket,
                          jackpot=self.jackpot)
        self.sim_btn.configure(state='normal', text='Simulate')
        self.sim_counts = result['counts']
        self.sim_total = trials
        self._redraw_chart()
        won = result['winnings']
        spent = result['spent']
        net = result['net']
        mode = 'fixed ticket' if ticket else 'fresh quick-pick each draw'
        self.status.configure(
            text=(f'Simulated {trials:,} draws ({mode}).  '
                  f'Spent ${spent:,}, won ${won:,}, net ${net:,}.'))

    # ---- chart -------------------------------------------------------------

    def _redraw_chart(self) -> None:
        ax = self.ax
        ax.clear()
        self._style_axes()

        labels = list(PLOT_TIERS)
        x = np.arange(len(labels))
        width = 0.4

        theory = np.array([THEORETICAL_PROBS[t] for t in labels])
        if self.sim_counts is not None and self.sim_total:
            empirical = np.array(
                [self.sim_counts[t] / self.sim_total for t in labels])
        else:
            empirical = np.zeros(len(labels))

        ax.bar(x - width / 2, theory, width=width, color=ACCENT,
               label='Theoretical', zorder=3)
        ax.bar(x + width / 2, empirical, width=width, color=GOLD,
               label=(f'Empirical ({self.sim_total:,} draws)'
                      if self.sim_total else 'Empirical (run sim)'),
               zorder=3)

        ax.set_yscale('log')
        ax.set_ylim(1e-9, 1)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right', color=MUTED,
                           fontsize=9)
        ax.set_ylabel('Probability per draw (log scale)')
        ax.set_title('Powerball — empirical vs theoretical hit rates')

        legend = ax.legend(loc='upper right', frameon=False, fontsize=9)
        for text in legend.get_texts():
            text.set_color(FG)

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == '__main__':
    PowerballApp().mainloop()
