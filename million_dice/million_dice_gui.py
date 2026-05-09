"""Million Dice Statistics — CustomTkinter GUI.

Roll N dice many times, plot the empirical frequency histogram, and overlay
the Normal approximation predicted by the Central Limit Theorem.

Twist: a "CLT side-by-side" toggle that runs N=1, 2, 3, 5 in one shot so you
can watch the distribution morph from uniform → triangular → bell.

Run:
    uv run python million_dice/million_dice_gui.py
"""
from __future__ import annotations

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from million_dice import normal_pdf, simulate

# Theme palette
BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
WARN = '#f59e0b'
GOOD = '#34d399'

DICE_OPTIONS = list(range(1, 11))               # 1..10
SIDES_OPTIONS = (4, 6, 8, 10, 12, 20)
ROLLS_LOG_MIN, ROLLS_LOG_MAX = 3.0, 7.0          # 1k → 10M
DEFAULT_DICE = 2
DEFAULT_SIDES = 6
DEFAULT_ROLLS_LOG = 5.0                          # 100,000

# CLT side-by-side panels
CLT_DICE_VALUES = (1, 2, 3, 5)


def rolls_from_log(value: float) -> int:
    """Map slider position (log10 rolls) to a clean rolls count."""
    n = int(round(10 ** value))
    # Snap to a 1/2/5 × 10^k grid for readability
    if n < 1000:
        return 1000
    exp = int(np.floor(np.log10(n)))
    base = 10 ** exp
    for m in (1, 2, 5, 10):
        if n <= m * base:
            return m * base
    return 10 * base


def fmt_rolls(n: int) -> str:
    if n >= 1_000_000:
        return f'{n / 1_000_000:g}M'
    if n >= 1_000:
        return f'{n // 1000}k'
    return str(n)


class MillionDiceApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Million Dice Statistics')
        self.geometry('960x780')
        self.minsize(820, 680)
        self.configure(fg_color=BG)

        self.current_dice = DEFAULT_DICE
        self.current_sides = DEFAULT_SIDES
        self.current_rolls = rolls_from_log(DEFAULT_ROLLS_LOG)
        self.current_result: dict | None = None
        self.show_clt = ctk.BooleanVar(value=False)

        self._build_ui()
        self._run_simulation()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='MILLION DICE STATISTICS',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(header,
                     text='Roll N dice millions of times — watch the CLT '
                          'turn the sum distribution into a bell curve',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(2, 0))

        # Bottom: status
        self.status = ctk.CTkLabel(self, text='', font=('Consolas', 12),
                                   text_color=MUTED, justify='center')
        self.status.pack(side='bottom', pady=(2, 10))

        # Bottom: controls
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='bottom', padx=20, pady=(4, 4), fill='x')

        # --- Row 1: Dice count slider
        dice_row = ctk.CTkFrame(controls, fg_color='transparent')
        dice_row.pack(padx=14, pady=(10, 4), fill='x')
        self.dice_label = ctk.CTkLabel(
            dice_row, text=f'Dice (N): {DEFAULT_DICE}',
            font=('Segoe UI', 13, 'bold'), text_color=FG,
            width=150, anchor='w')
        self.dice_label.pack(side='left')
        self.dice_slider = ctk.CTkSlider(
            dice_row, from_=DICE_OPTIONS[0], to=DICE_OPTIONS[-1],
            number_of_steps=DICE_OPTIONS[-1] - DICE_OPTIONS[0],
            command=self._on_dice_slider)
        self.dice_slider.set(DEFAULT_DICE)
        self.dice_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # --- Row 2: Rolls slider (log scale)
        rolls_row = ctk.CTkFrame(controls, fg_color='transparent')
        rolls_row.pack(padx=14, pady=(4, 4), fill='x')
        self.rolls_label = ctk.CTkLabel(
            rolls_row, text=f'Rolls: {fmt_rolls(self.current_rolls)}',
            font=('Segoe UI', 13, 'bold'), text_color=FG,
            width=150, anchor='w')
        self.rolls_label.pack(side='left')
        self.rolls_slider = ctk.CTkSlider(
            rolls_row, from_=ROLLS_LOG_MIN, to=ROLLS_LOG_MAX,
            number_of_steps=80, command=self._on_rolls_slider)
        self.rolls_slider.set(DEFAULT_ROLLS_LOG)
        self.rolls_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # --- Row 3: Sides + CLT toggle + Run button
        bottom_row = ctk.CTkFrame(controls, fg_color='transparent')
        bottom_row.pack(padx=14, pady=(4, 10), fill='x')
        ctk.CTkLabel(bottom_row, text='Sides:',
                     font=('Segoe UI', 13), text_color=FG,
                     width=60, anchor='w').pack(side='left')
        self.sides_var = ctk.StringVar(value=str(DEFAULT_SIDES))
        for s in SIDES_OPTIONS:
            ctk.CTkRadioButton(bottom_row, text=f'd{s}',
                               variable=self.sides_var, value=str(s),
                               font=('Segoe UI', 12),
                               command=self._on_sides).pack(side='left',
                                                            padx=(4, 0))

        ctk.CTkSwitch(bottom_row, text='CLT panels',
                      variable=self.show_clt, onvalue=True, offvalue=False,
                      command=self._on_clt_toggle,
                      font=('Segoe UI', 12)).pack(side='left', padx=(20, 0))

        self.run_btn = ctk.CTkButton(bottom_row, text='Run simulation',
                                     width=160,
                                     font=('Segoe UI', 13, 'bold'),
                                     command=self._run_simulation)
        self.run_btn.pack(side='right')

        # --- Chart
        chart_frame = ctk.CTkFrame(self, fg_color=BG)
        chart_frame.pack(side='top', fill='both', expand=True,
                         padx=12, pady=(8, 4))
        self.fig = Figure(figsize=(8, 5), facecolor=BG, dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

    # ------------------------------------------------------------ axes style

    def _style_ax(self, ax, title: str = '') -> None:
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_color('#334155')
        ax.tick_params(colors=MUTED, labelsize=8)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.title.set_color(FG)
        ax.grid(True, color='#1e293b', linewidth=0.7, alpha=0.7)
        if title:
            ax.set_title(title, fontsize=11)

    # ----------------------------------------------------------- callbacks

    def _on_dice_slider(self, value: float) -> None:
        self.current_dice = int(round(value))
        self.dice_label.configure(text=f'Dice (N): {self.current_dice}')

    def _on_rolls_slider(self, value: float) -> None:
        self.current_rolls = rolls_from_log(value)
        self.rolls_label.configure(
            text=f'Rolls: {fmt_rolls(self.current_rolls)}')

    def _on_sides(self) -> None:
        self.current_sides = int(self.sides_var.get())

    def _on_clt_toggle(self) -> None:
        if self.current_result is not None:
            self._redraw()

    # ---------------------------------------------------------- simulation

    def _run_simulation(self) -> None:
        self.run_btn.configure(state='disabled', text='Rolling…')
        self.status.configure(
            text=f'Rolling {self.current_dice}d{self.current_sides} × '
                 f'{self.current_rolls:,}…')
        self.update_idletasks()

        rng = np.random.default_rng()
        self.current_result = simulate(
            self.current_dice, self.current_rolls,
            self.current_sides, rng=rng)
        self._redraw()
        self.run_btn.configure(state='normal', text='Run simulation')

    # ------------------------------------------------------------- drawing

    def _redraw(self) -> None:
        self.fig.clear()
        if self.show_clt.get():
            self._draw_clt_panels()
        else:
            self._draw_main_chart()
        self.fig.tight_layout()
        self.canvas.draw()
        self._update_status()

    def _draw_main_chart(self) -> None:
        r = self.current_result
        if r is None:
            return
        ax = self.fig.add_subplot(111)
        self._style_ax(ax)
        self._plot_dist(ax, r,
                        title=f'{r["num_dice"]}d{r["sides"]} sums  '
                              f'(× {r["num_rolls"]:,} rolls)')

    def _draw_clt_panels(self) -> None:
        """Side-by-side N=1, 2, 3, 5 to show the CLT in action."""
        r0 = self.current_result
        if r0 is None:
            return
        rolls = r0['num_rolls']
        sides = r0['sides']
        rng = np.random.default_rng()
        results = []
        for n in CLT_DICE_VALUES:
            if n == r0['num_dice']:
                results.append(r0)
            else:
                results.append(simulate(n, rolls, sides, rng=rng))

        for idx, r in enumerate(results):
            ax = self.fig.add_subplot(2, 2, idx + 1)
            self._style_ax(ax)
            shape = {1: 'uniform', 2: 'triangular',
                     3: '≈ normal', 5: 'normal'}.get(r['num_dice'],
                                                      'normal')
            self._plot_dist(ax, r,
                            title=f'N = {r["num_dice"]}  →  {shape}',
                            compact=True)

    def _plot_dist(self, ax, r: dict, title: str = '',
                   compact: bool = False) -> None:
        counts = r['counts']
        keys = np.array(sorted(counts.keys()))
        vals = np.array([counts[int(k)] for k in keys])
        probs = vals / r['num_rolls']

        # Empirical histogram (bar = probability mass)
        ax.bar(keys, probs, width=0.85, color=ACCENT, alpha=0.85,
               edgecolor=BG, linewidth=0.5,
               label='Empirical' if not compact else None)

        # Normal approximation overlay (CLT)
        mean = r['theoretical_mean']
        std = r['theoretical_std']
        if std > 0:
            xs = np.linspace(keys.min() - 0.5, keys.max() + 0.5, 400)
            # PDF * 1 because bar width = 1 (each integer sum is one mass point)
            pdf = normal_pdf(xs, mean, std)
            ax.plot(xs, pdf, color=WARN, linewidth=2,
                    label='Normal (CLT)' if not compact else None)
            # ±1σ and ±2σ guides
            for k, alpha in ((1, 0.55), (2, 0.30)):
                ax.axvspan(mean - k * std, mean + k * std,
                           color=GOOD, alpha=0.06)
            ax.axvline(mean, color=GOOD, linewidth=1.0,
                       linestyle='--', alpha=0.7)

        if title:
            ax.set_title(title, fontsize=11 if not compact else 10,
                         color=FG)
        ax.set_xlabel('Sum')
        ax.set_ylabel('Probability')

        if not compact:
            legend = ax.legend(loc='upper right', frameon=False,
                               labelcolor=FG, fontsize=10)
            for text in legend.get_texts():
                text.set_color(FG)

    def _update_status(self) -> None:
        r = self.current_result
        if r is None:
            return
        dm = r['mean'] - r['theoretical_mean']
        ds = r['std'] - r['theoretical_std']
        self.status.configure(
            text=(f'mean {r["mean"]:.4f} (theory {r["theoretical_mean"]:.4f}, '
                  f'Δ{dm:+.4f})    '
                  f'std {r["std"]:.4f} (theory {r["theoretical_std"]:.4f}, '
                  f'Δ{ds:+.4f})    '
                  f'min {r["min"]}  max {r["max"]}'))


if __name__ == '__main__':
    MillionDiceApp().mainloop()
