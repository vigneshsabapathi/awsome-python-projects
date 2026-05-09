"""Monty Hall — CustomTkinter desktop GUI.

Two modes:
  - Play: pick a door, watch Monty open a goat, switch or stay.
  - Simulate: Monte Carlo bar chart (switch vs stay) with N-door slider showing
    how the switching advantage scales as the number of doors grows.

Run:
    uv run python monty_hall/monty_hall_gui.py
"""
from __future__ import annotations

import random
from typing import Optional

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from monty_hall import simulate, theoretical, wilson_ci

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
SWITCH_C = '#38bdf8'
STAY_C = '#f59e0b'
GOOD = '#34d399'
BAD = '#ef4444'

DOOR_CLOSED = '\U0001F6AA'   # door
GOAT = '\U0001F410'          # goat
CAR = '\U0001F697'           # car

TRIALS_OPTIONS = (1_000, 10_000, 100_000)
DEFAULT_TRIALS = 10_000
N_MIN_PLAY, N_MAX_PLAY = 3, 8
N_MIN_SIM, N_MAX_SIM = 3, 20
DEFAULT_N = 3


class MontyHallApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Monty Hall')
        self.geometry('960x760')
        self.minsize(820, 680)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.num_doors = DEFAULT_N

        # Play-mode state
        self.car_door: int = 0
        self.pick: Optional[int] = None
        self.opened: Optional[int] = None
        self.final_pick: Optional[int] = None
        self.phase: str = 'pick'  # 'pick' | 'decide' | 'reveal'
        self.play_stats = {'switch_wins': 0, 'switch_n': 0,
                           'stay_wins': 0, 'stay_n': 0}

        # Sim-mode state
        self.sim_n = DEFAULT_N
        self.sim_trials = DEFAULT_TRIALS
        self.sim_switch_p: Optional[float] = None
        self.sim_stay_p: Optional[float] = None
        self.sim_switch_ci: tuple[float, float] = (0.0, 0.0)
        self.sim_stay_ci: tuple[float, float] = (0.0, 0.0)

        self._build_ui()
        self._new_round()
        self._run_sim()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='MONTY HALL',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(header,
                     text='Pick a door. Monty reveals a goat. Switch or stay?',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(2, 0))

        self.tabs = ctk.CTkTabview(self, fg_color=PANEL,
                                   segmented_button_fg_color=BG,
                                   segmented_button_selected_color=SWITCH_C,
                                   segmented_button_selected_hover_color='#0ea5e9')
        self.tabs.pack(side='top', fill='both', expand=True,
                       padx=12, pady=(8, 12))
        self.tabs.add('Play')
        self.tabs.add('Simulate')
        self.tabs.add('Bayes')
        self._build_play_tab(self.tabs.tab('Play'))
        self._build_sim_tab(self.tabs.tab('Simulate'))
        self._build_bayes_tab(self.tabs.tab('Bayes'))

    # --- Play tab --------------------------------------------------------
    def _build_play_tab(self, parent) -> None:
        # Top control row
        ctrl = ctk.CTkFrame(parent, fg_color='transparent')
        ctrl.pack(side='top', fill='x', padx=16, pady=(12, 4))
        ctk.CTkLabel(ctrl, text='Doors:', font=('Segoe UI', 13),
                     text_color=FG).pack(side='left')
        self.play_n_var = ctk.IntVar(value=DEFAULT_N)
        self.play_n_label = ctk.CTkLabel(ctrl, text=str(DEFAULT_N), width=24,
                                         font=('Segoe UI', 13, 'bold'),
                                         text_color=SWITCH_C)
        self.play_n_label.pack(side='left', padx=(6, 8))
        self.play_n_slider = ctk.CTkSlider(
            ctrl, from_=N_MIN_PLAY, to=N_MAX_PLAY,
            number_of_steps=N_MAX_PLAY - N_MIN_PLAY,
            command=self._on_play_n_change, width=160)
        self.play_n_slider.set(DEFAULT_N)
        self.play_n_slider.pack(side='left', padx=(0, 16))

        ctk.CTkButton(ctrl, text='New round', width=110,
                      font=('Segoe UI', 12, 'bold'),
                      command=self._new_round).pack(side='left')
        ctk.CTkButton(ctrl, text='Reset stats', width=110,
                      fg_color=PANEL, hover_color='#334155',
                      font=('Segoe UI', 12),
                      command=self._reset_play_stats).pack(side='left',
                                                            padx=(8, 0))

        # Doors row
        self.doors_frame = ctk.CTkFrame(parent, fg_color='transparent')
        self.doors_frame.pack(side='top', pady=(20, 8), padx=16, fill='x')
        self.door_buttons: list[ctk.CTkButton] = []
        self._build_door_buttons()

        # Decide row (switch / stay)
        self.decide_frame = ctk.CTkFrame(parent, fg_color='transparent')
        self.decide_frame.pack(side='top', pady=(8, 8))
        self.switch_btn = ctk.CTkButton(
            self.decide_frame, text='SWITCH', width=140, height=42,
            font=('Segoe UI', 14, 'bold'),
            fg_color=SWITCH_C, text_color=BG,
            hover_color='#0ea5e9',
            command=lambda: self._decide('switch'))
        self.switch_btn.pack(side='left', padx=8)
        self.stay_btn = ctk.CTkButton(
            self.decide_frame, text='STAY', width=140, height=42,
            font=('Segoe UI', 14, 'bold'),
            fg_color=STAY_C, text_color=BG,
            hover_color='#d97706',
            command=lambda: self._decide('stay'))
        self.stay_btn.pack(side='left', padx=8)

        # Status label
        self.status = ctk.CTkLabel(parent, text='', font=('Segoe UI', 13),
                                   text_color=FG, justify='center',
                                   wraplength=720)
        self.status.pack(side='top', pady=(8, 4), padx=16, fill='x')

        # Stats
        self.stats_label = ctk.CTkLabel(parent, text='', font=('Segoe UI', 12),
                                        text_color=MUTED, justify='center')
        self.stats_label.pack(side='top', pady=(0, 16))

    def _build_door_buttons(self) -> None:
        for b in self.door_buttons:
            b.destroy()
        self.door_buttons = []
        # Center the doors
        inner = ctk.CTkFrame(self.doors_frame, fg_color='transparent')
        inner.pack(anchor='center')
        for i in range(self.num_doors):
            btn = ctk.CTkButton(
                inner, text=f'{DOOR_CLOSED}\n{i + 1}', width=90, height=130,
                font=('Segoe UI Emoji', 28),
                fg_color=PANEL, hover_color='#334155',
                text_color=FG, corner_radius=10,
                command=lambda d=i: self._on_door_click(d))
            btn.pack(side='left', padx=6)
            self.door_buttons.append(btn)

    def _on_play_n_change(self, value: float) -> None:
        n = int(round(value))
        if n != self.num_doors:
            self.num_doors = n
            self.play_n_label.configure(text=str(n))
            self._build_door_buttons()
            self._new_round()

    def _new_round(self) -> None:
        self.car_door = self.rng.randrange(self.num_doors)
        self.pick = None
        self.opened = None
        self.final_pick = None
        self.phase = 'pick'
        self._refresh_doors()
        self.status.configure(
            text=f'Pick one of the {self.num_doors} doors.', text_color=FG)
        self._set_decide_enabled(False)
        self._update_stats_label()

    def _reset_play_stats(self) -> None:
        self.play_stats = {'switch_wins': 0, 'switch_n': 0,
                           'stay_wins': 0, 'stay_n': 0}
        self._update_stats_label()

    def _on_door_click(self, door: int) -> None:
        if self.phase != 'pick':
            return
        self.pick = door
        # Monty opens a goat door (not pick, not car).
        candidates = [d for d in range(self.num_doors)
                      if d != self.pick and d != self.car_door]
        self.opened = self.rng.choice(candidates)
        self.phase = 'decide'
        self._refresh_doors()
        self.status.configure(
            text=(f'You picked door {door + 1}. Monty opens door '
                  f'{self.opened + 1} — a goat! Switch or stay?'),
            text_color=FG)
        self._set_decide_enabled(True)

    def _decide(self, choice: str) -> None:
        if self.phase != 'decide' or self.pick is None or self.opened is None:
            return
        if choice == 'stay':
            self.final_pick = self.pick
        else:
            remaining = [d for d in range(self.num_doors)
                         if d != self.pick and d != self.opened]
            self.final_pick = self.rng.choice(remaining)
        won = self.final_pick == self.car_door
        if choice == 'switch':
            self.play_stats['switch_n'] += 1
            self.play_stats['switch_wins'] += int(won)
        else:
            self.play_stats['stay_n'] += 1
            self.play_stats['stay_wins'] += int(won)
        self.phase = 'reveal'
        self._refresh_doors()
        msg = (f'You {"SWITCHED" if choice == "switch" else "STAYED"} → '
               f'door {self.final_pick + 1}. ')
        if won:
            msg += 'It\'s the CAR! You win!'
            self.status.configure(text=msg, text_color=GOOD)
        else:
            msg += f'Goat. The car was behind door {self.car_door + 1}.'
            self.status.configure(text=msg, text_color=BAD)
        self._set_decide_enabled(False)
        self._update_stats_label()

    def _refresh_doors(self) -> None:
        for i, btn in enumerate(self.door_buttons):
            label = f'{DOOR_CLOSED}\n{i + 1}'
            fg = PANEL
            txt = FG
            if self.phase == 'decide' and i == self.opened:
                label = f'{GOAT}\n{i + 1}'
                fg = '#475569'
            elif self.phase == 'reveal':
                if i == self.opened:
                    label = f'{GOAT}\n{i + 1}'
                    fg = '#475569'
                elif i == self.car_door:
                    label = f'{CAR}\n{i + 1}'
                    fg = GOOD
                    txt = BG
                else:
                    label = f'{GOAT}\n{i + 1}'
                    fg = '#475569'
                if i == self.final_pick and i != self.car_door:
                    fg = BAD
                    txt = FG
            elif self.phase == 'pick':
                label = f'{DOOR_CLOSED}\n{i + 1}'
            btn.configure(text=label, fg_color=fg, text_color=txt)

    def _set_decide_enabled(self, enabled: bool) -> None:
        state = 'normal' if enabled else 'disabled'
        self.switch_btn.configure(state=state)
        self.stay_btn.configure(state=state)

    def _update_stats_label(self) -> None:
        s = self.play_stats
        sw_p = s['switch_wins'] / s['switch_n'] if s['switch_n'] else 0.0
        st_p = s['stay_wins'] / s['stay_n'] if s['stay_n'] else 0.0
        self.stats_label.configure(text=(
            f'Session — switch: {s["switch_wins"]}/{s["switch_n"]} '
            f'({sw_p * 100:.1f}%)   |   '
            f'stay: {s["stay_wins"]}/{s["stay_n"]} ({st_p * 100:.1f}%)'))

    # --- Simulate tab ----------------------------------------------------
    def _build_sim_tab(self, parent) -> None:
        ctrl = ctk.CTkFrame(parent, fg_color='transparent')
        ctrl.pack(side='top', fill='x', padx=16, pady=(12, 6))

        ctk.CTkLabel(ctrl, text='Doors (N):', font=('Segoe UI', 13),
                     text_color=FG).pack(side='left')
        self.sim_n_label = ctk.CTkLabel(ctrl, text=str(DEFAULT_N), width=28,
                                        font=('Segoe UI', 13, 'bold'),
                                        text_color=SWITCH_C)
        self.sim_n_label.pack(side='left', padx=(6, 8))
        self.sim_n_slider = ctk.CTkSlider(
            ctrl, from_=N_MIN_SIM, to=N_MAX_SIM,
            number_of_steps=N_MAX_SIM - N_MIN_SIM,
            command=self._on_sim_n_change, width=180)
        self.sim_n_slider.set(DEFAULT_N)
        self.sim_n_slider.pack(side='left', padx=(0, 16))

        ctk.CTkLabel(ctrl, text='Trials:', font=('Segoe UI', 13),
                     text_color=FG).pack(side='left')
        self.sim_trials_var = ctk.StringVar(value=str(DEFAULT_TRIALS))
        for t in TRIALS_OPTIONS:
            label = f'{t // 1000}k' if t >= 1000 else str(t)
            ctk.CTkRadioButton(ctrl, text=label, variable=self.sim_trials_var,
                               value=str(t),
                               font=('Segoe UI', 12)).pack(side='left',
                                                            padx=(6, 0))

        self.run_btn = ctk.CTkButton(ctrl, text='Run', width=100,
                                     font=('Segoe UI', 13, 'bold'),
                                     command=self._run_sim)
        self.run_btn.pack(side='right')

        # Chart
        chart_frame = ctk.CTkFrame(parent, fg_color=BG)
        chart_frame.pack(side='top', fill='both', expand=True,
                         padx=12, pady=(8, 4))
        self.fig = Figure(figsize=(7, 4.5), facecolor=BG, dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        self.sim_status = ctk.CTkLabel(parent, text='', font=('Segoe UI', 12),
                                       text_color=MUTED, justify='center')
        self.sim_status.pack(side='top', pady=(4, 12))

    def _style_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_color('#334155')
        ax.tick_params(colors=MUTED, labelsize=10)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.title.set_color(FG)
        ax.grid(True, axis='y', color='#1e293b', linewidth=0.8)

    def _on_sim_n_change(self, value: float) -> None:
        n = int(round(value))
        if n != self.sim_n:
            self.sim_n = n
            self.sim_n_label.configure(text=str(n))
            self._run_sim()

    def _run_sim(self) -> None:
        trials = int(self.sim_trials_var.get())
        self.sim_trials = trials
        self.run_btn.configure(state='disabled', text='Running...')
        self.sim_status.configure(text=f'Simulating {trials:,} rounds × 2 strategies...')
        self.update_idletasks()

        sw = simulate('switch', trials, num_doors=self.sim_n, rng=self.rng)
        st = simulate('stay', trials, num_doors=self.sim_n, rng=self.rng)
        self.sim_switch_p = sw['p_win']
        self.sim_stay_p = st['p_win']
        self.sim_switch_ci = wilson_ci(sw['wins'], trials)
        self.sim_stay_ci = wilson_ci(st['wins'], trials)

        self.run_btn.configure(state='normal', text='Run')
        self._redraw_sim()

    def _redraw_sim(self) -> None:
        ax = self.ax
        ax.clear()
        self._style_axes()

        labels = ['Switch', 'Stay']
        empirical = [self.sim_switch_p or 0.0, self.sim_stay_p or 0.0]
        theory = [theoretical('switch', self.sim_n),
                  theoretical('stay', self.sim_n)]
        colors = [SWITCH_C, STAY_C]

        x = [0, 1]
        width = 0.35
        bars_emp = ax.bar([xi - width / 2 for xi in x], empirical, width,
                          color=colors, label='Empirical', edgecolor=BG,
                          zorder=3)
        bars_th = ax.bar([xi + width / 2 for xi in x], theory, width,
                         color=colors, alpha=0.45, label='Theoretical',
                         edgecolor=BG, zorder=3, hatch='//')

        # CI error bars on empirical
        cis = [self.sim_switch_ci, self.sim_stay_ci]
        lo_err = [empirical[i] - cis[i][0] for i in range(2)]
        hi_err = [cis[i][1] - empirical[i] for i in range(2)]
        ax.errorbar([xi - width / 2 for xi in x], empirical,
                    yerr=[lo_err, hi_err], fmt='none',
                    ecolor=FG, elinewidth=1.2, capsize=5, zorder=4)

        for bar, val in zip(bars_emp, empirical):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.015,
                    f'{val * 100:.1f}%', ha='center', color=FG,
                    fontsize=10, fontweight='bold')
        for bar, val in zip(bars_th, theory):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.015,
                    f'{val * 100:.1f}%', ha='center', color=MUTED,
                    fontsize=9)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, color=FG, fontsize=12)
        max_y = max(max(empirical), max(theory), 0.75)
        ax.set_ylim(0, min(1.0, max_y * 1.25))
        ax.set_ylabel('P(win car)')
        ax.set_title(
            f'Monty Hall — N={self.sim_n} doors, {self.sim_trials:,} trials')

        legend = ax.legend(loc='upper right', frameon=False,
                           labelcolor=FG, fontsize=10)
        for text in legend.get_texts():
            text.set_color(FG)

        self.fig.tight_layout()
        self.canvas.draw()

        ratio = (theoretical('switch', self.sim_n)
                 / theoretical('stay', self.sim_n))
        self.sim_status.configure(text=(
            f'Switch theoretical: {theory[0] * 100:.2f}%   |   '
            f'Stay theoretical: {theory[1] * 100:.2f}%   |   '
            f'Switch beats stay by {ratio:.2f}x'))

    # --- Bayes tab -------------------------------------------------------
    def _build_bayes_tab(self, parent) -> None:
        scroll = ctk.CTkScrollableFrame(parent, fg_color=BG)
        scroll.pack(fill='both', expand=True, padx=12, pady=12)

        ctk.CTkLabel(scroll, text='Why switching wins 2/3 of the time',
                     font=('Segoe UI', 18, 'bold'),
                     text_color=FG, justify='left').pack(anchor='w',
                                                          pady=(4, 12))

        steps = [
            ('1.  Set up the prior',
             'Three doors, one car. Before you choose, the car is equally\n'
             'likely behind any door:\n'
             '   P(car=A) = P(car=B) = P(car=C) = 1/3'),
            ('2.  You pick door A (WLOG)',
             'Your initial pick is uniform too — it does not change the prior.\n'
             '   P(car=A) = 1/3      (the "stay" probability)\n'
             '   P(car ∈ {B, C}) = 2/3'),
            ('3.  Monty opens a goat door',
             'Monty knows where the car is and ALWAYS opens a different door\n'
             'that hides a goat. Crucially:\n'
             '  • If the car is at A, Monty picks B or C uniformly.\n'
             '  • If the car is at B, Monty MUST open C.\n'
             '  • If the car is at B, Monty MUST open C.\n'
             'His choice carries information about where the car is NOT.'),
            ('4.  Apply Bayes after seeing Monty open C',
             'Likelihoods of "Monty opens C":\n'
             '   P(open=C | car=A) = 1/2   (he picks B or C)\n'
             '   P(open=C | car=B) = 1     (forced)\n'
             '   P(open=C | car=C) = 0     (would reveal the car)\n'
             '\n'
             'Posterior ∝ prior × likelihood:\n'
             '   car=A: (1/3)(1/2) = 1/6\n'
             '   car=B: (1/3)(1)   = 2/6\n'
             '   car=C: 0\n'
             '\n'
             'Normalize → P(car=A | open=C) = 1/3,\n'
             '            P(car=B | open=C) = 2/3.'),
            ('5.  Therefore: switch!',
             'Staying with A wins 1/3 of the time.\n'
             'Switching to B wins 2/3 of the time.\n'
             '\n'
             'The 2/3 mass that started on {B, C} did NOT vanish when Monty\n'
             'opened C — it all collapsed onto B. That is why switching is\n'
             'twice as good.'),
            ('Generalization to N doors',
             'With N doors and Monty opening exactly one goat door:\n'
             '   P(stay)   = 1 / N\n'
             '   P(switch) = (N - 1) / (N · (N - 2))\n'
             '\n'
             'For N=3 → 2/3. For N=10 → 9/80 ≈ 11.25% (vs 10% staying).\n'
             'Switching always beats staying by a factor of (N-1)/(N-2).'),
        ]
        for title, body in steps:
            ctk.CTkLabel(scroll, text=title, font=('Segoe UI', 14, 'bold'),
                         text_color=SWITCH_C, justify='left',
                         anchor='w').pack(anchor='w', pady=(8, 2), padx=4)
            ctk.CTkLabel(scroll, text=body, font=('Consolas', 12),
                         text_color=FG, justify='left',
                         anchor='w').pack(anchor='w', padx=20)


if __name__ == '__main__':
    MontyHallApp().mainloop()
