"""Birthday Paradox — CustomTkinter GUI.

Sweeps N from 2 to 80 with a NumPy-vectorized Monte Carlo, then plots:
- theoretical curve (closed form)
- empirical probability with 95% Wilson CI band
- 50% reference line and a marker at the user-selected N

Run:
    uv run python birthday_paradox/birthday_paradox_gui.py
"""
from __future__ import annotations

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from birthday_paradox import theoretical, wilson_ci

N_MIN, N_MAX = 2, 80
DEFAULT_N = 23
TRIALS_OPTIONS = (1_000, 10_000, 100_000)
DEFAULT_TRIALS = 10_000

BG = '#0f172a'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'


def simulate_sweep(trials: int, n_values: np.ndarray,
                   rng: np.random.Generator) -> np.ndarray:
    """Vectorized: for each N, run `trials` simulations and return match counts.
    Sort each row of (trials x N) random days and check adjacent equality."""
    counts = np.empty(len(n_values), dtype=np.int64)
    for i, n in enumerate(n_values):
        bdays = rng.integers(0, 365, size=(trials, int(n)))
        bdays.sort(axis=1)
        has_dup = (np.diff(bdays, axis=1) == 0).any(axis=1)
        counts[i] = int(has_dup.sum())
    return counts


class BirthdayParadoxApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Birthday Paradox')
        self.geometry('820x720')
        self.minsize(700, 600)
        self.configure(fg_color=BG)

        self.n_values = np.arange(N_MIN, N_MAX + 1)
        self.theory = np.array([theoretical(int(n)) for n in self.n_values])
        self.matches: np.ndarray | None = None
        self.trials_used = 0
        self.current_trials = DEFAULT_TRIALS
        self.current_n = DEFAULT_N

        self._build_ui()
        self._run_simulation()

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='BIRTHDAY PARADOX',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(header,
                     text='Probability that any 2 of N people share a birthday',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(2, 0))

        # Bottom controls (packed first so they're always visible)
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 12),
                                   text_color=MUTED, justify='center')
        self.status.pack(side='bottom', pady=(2, 10))

        controls = ctk.CTkFrame(self, fg_color='#1e293b', corner_radius=10)
        controls.pack(side='bottom', padx=20, pady=(4, 4), fill='x')

        slider_row = ctk.CTkFrame(controls, fg_color='transparent')
        slider_row.pack(padx=14, pady=(10, 4), fill='x')
        self.n_label = ctk.CTkLabel(slider_row, text=f'Group size N: {DEFAULT_N}',
                                    font=('Segoe UI', 13, 'bold'),
                                    text_color=FG, width=140, anchor='w')
        self.n_label.pack(side='left')
        self.n_slider = ctk.CTkSlider(slider_row, from_=N_MIN, to=N_MAX,
                                      number_of_steps=N_MAX - N_MIN,
                                      command=self._on_slider)
        self.n_slider.set(DEFAULT_N)
        self.n_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        trials_row = ctk.CTkFrame(controls, fg_color='transparent')
        trials_row.pack(padx=14, pady=(4, 10), fill='x')
        ctk.CTkLabel(trials_row, text='Trials per N:',
                     font=('Segoe UI', 13), text_color=FG,
                     width=140, anchor='w').pack(side='left')
        self.trials_var = ctk.StringVar(value=str(DEFAULT_TRIALS))
        for t in TRIALS_OPTIONS:
            label = f'{t // 1000}k' if t >= 1000 else str(t)
            ctk.CTkRadioButton(trials_row, text=label,
                               variable=self.trials_var, value=str(t),
                               font=('Segoe UI', 12)).pack(side='left',
                                                            padx=(8, 0))
        self.run_btn = ctk.CTkButton(trials_row, text='Run simulation',
                                     width=140,
                                     font=('Segoe UI', 13, 'bold'),
                                     command=self._run_simulation)
        self.run_btn.pack(side='right')

        # Chart area fills the middle
        chart_frame = ctk.CTkFrame(self, fg_color=BG)
        chart_frame.pack(side='top', fill='both', expand=True,
                         padx=12, pady=(8, 4))
        self.fig = Figure(figsize=(7, 4), facecolor=BG, dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
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
        ax.grid(True, color='#1e293b', linewidth=0.8)

    def _on_slider(self, value: float) -> None:
        self.current_n = int(round(value))
        self.n_label.configure(text=f'Group size N: {self.current_n}')
        self._redraw()

    def _run_simulation(self) -> None:
        trials = int(self.trials_var.get())
        self.run_btn.configure(state='disabled', text='Running…')
        self.status.configure(text=f'Running {trials:,} trials × '
                                   f'{len(self.n_values)} group sizes…')
        self.update_idletasks()

        rng = np.random.default_rng()
        self.matches = simulate_sweep(trials, self.n_values, rng)
        self.trials_used = trials

        self.run_btn.configure(state='normal', text='Run simulation')
        self._redraw()

    def _redraw(self) -> None:
        ax = self.ax
        ax.clear()
        self._style_axes()
        ax.set_xlim(N_MIN, N_MAX)
        ax.set_ylim(0, 1.02)
        ax.set_xlabel('Group size (N)')
        ax.set_ylabel('P(at least one shared birthday)')
        ax.set_title('Birthday Paradox — empirical vs theoretical')

        # Theoretical curve
        ax.plot(self.n_values, self.theory, color=ACCENT, linewidth=2,
                label='Theoretical', zorder=3)

        # Empirical with 95% CI band
        if self.matches is not None:
            emp = self.matches / self.trials_used
            ci = np.array([wilson_ci(int(m), self.trials_used)
                           for m in self.matches])
            ax.fill_between(self.n_values, ci[:, 0], ci[:, 1],
                            color='#f59e0b', alpha=0.25,
                            label='95% CI', zorder=2)
            ax.scatter(self.n_values, emp, color='#f59e0b', s=12,
                       label=f'Empirical ({self.trials_used:,} trials)',
                       zorder=4)

        # 50% reference + N marker
        ax.axhline(0.5, color='#64748b', linewidth=0.8, linestyle='--',
                   alpha=0.7)
        ax.axvline(self.current_n, color='#34d399', linewidth=1.2,
                   linestyle=':', alpha=0.8)

        legend = ax.legend(loc='lower right', frameon=False,
                           labelcolor=FG, fontsize=9)
        for text in legend.get_texts():
            text.set_color(FG)

        self.fig.tight_layout()
        self.canvas.draw()

        # Status with theoretical/empirical/CI for current N
        n = self.current_n
        th = theoretical(n)
        idx = n - N_MIN
        if self.matches is not None and 0 <= idx < len(self.matches):
            m = int(self.matches[idx])
            emp = m / self.trials_used
            lo, hi = wilson_ci(m, self.trials_used)
            self.status.configure(
                text=(f'N={n}   theoretical {th * 100:.2f}%   '
                      f'empirical {emp * 100:.2f}%   '
                      f'95% CI [{lo * 100:.2f}%, {hi * 100:.2f}%]'))
        else:
            self.status.configure(text=f'N={n}   theoretical {th * 100:.2f}%')


if __name__ == '__main__':
    BirthdayParadoxApp().mainloop()
