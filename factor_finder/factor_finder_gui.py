"""Factor Finder — CustomTkinter GUI.

Compute the divisors and prime factorization of an integer N, with a
matplotlib bar chart of the prime-factor multiplicities.

Run:
    uv run python factor_finder/factor_finder_gui.py
"""
from __future__ import annotations

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from factor_finder import (
    classify,
    divisor_sum,
    euler_totient,
    factors,
    pretty_factorization,
    prime_factorization,
    proper_divisor_sum,
)

BG = '#0f172a'
PANEL = '#1e293b'
SUNKEN = '#0b1220'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
GOOD = '#34d399'
WARN = '#f59e0b'
BAD = '#f87171'
GRID = '#334155'

CLASS_COLOR = {
    'prime':     '#a78bfa',  # purple
    'perfect':   '#34d399',  # green
    'abundant':  '#f59e0b',  # amber
    'deficient': '#38bdf8',  # cyan
}

DEFAULT_N = 360


class FactorFinderApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Factor Finder')
        self.geometry('900x760')
        self.minsize(760, 640)
        self.configure(fg_color=BG)

        self._build_ui()
        # Run an initial computation so the window has something to show.
        self.entry.insert(0, str(DEFAULT_N))
        self._compute()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # ---------- Header ----------
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='FACTOR FINDER',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(header,
                     text='Divisors, prime factorization, and number-theory tags',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(2, 0))

        # ---------- Input row ----------
        input_row = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        input_row.pack(side='top', padx=20, pady=(8, 4), fill='x')

        ctk.CTkLabel(input_row, text='N =',
                     font=('Segoe UI', 14, 'bold'),
                     text_color=FG).pack(side='left', padx=(14, 6), pady=12)
        self.entry = ctk.CTkEntry(input_row,
                                  font=('Consolas', 14),
                                  placeholder_text='Enter a positive integer',
                                  width=320)
        self.entry.pack(side='left', padx=(0, 10), pady=12, fill='x',
                        expand=True)
        self.entry.bind('<Return>', lambda _e: self._compute())

        self.compute_btn = ctk.CTkButton(input_row, text='Compute',
                                         font=('Segoe UI', 13, 'bold'),
                                         width=120,
                                         command=self._compute)
        self.compute_btn.pack(side='left', padx=(0, 14), pady=12)

        # ---------- Status / class chip ----------
        status_row = ctk.CTkFrame(self, fg_color='transparent')
        status_row.pack(side='top', padx=20, pady=(2, 4), fill='x')

        self.class_chip = ctk.CTkLabel(status_row, text='—',
                                       font=('Segoe UI', 12, 'bold'),
                                       text_color=FG, fg_color='#334155',
                                       corner_radius=12,
                                       width=110, height=22)
        self.class_chip.pack(side='left', padx=(0, 12))

        self.summary = ctk.CTkLabel(status_row, text='',
                                    font=('Segoe UI', 12),
                                    text_color=MUTED, anchor='w',
                                    justify='left')
        self.summary.pack(side='left', fill='x', expand=True)

        # ---------- Body: 2 columns ----------
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=12, pady=(4, 8))
        body.grid_columnconfigure(0, weight=3, uniform='cols')
        body.grid_columnconfigure(1, weight=4, uniform='cols')
        body.grid_rowconfigure(0, weight=1)

        # Left column — divisors + factorization
        left = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=10)
        left.grid(row=0, column=0, sticky='nsew', padx=(8, 6))

        ctk.CTkLabel(left, text='Divisors',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, anchor='w').pack(fill='x',
                                                     padx=14, pady=(12, 4))
        self.factor_count_lbl = ctk.CTkLabel(left, text='', anchor='w',
                                             font=('Segoe UI', 11),
                                             text_color=MUTED)
        self.factor_count_lbl.pack(fill='x', padx=14)

        self.factors_box = ctk.CTkTextbox(left,
                                          font=('Consolas', 12),
                                          fg_color=SUNKEN,
                                          text_color=FG,
                                          border_width=1,
                                          border_color=GRID,
                                          activate_scrollbars=True,
                                          wrap='word')
        self.factors_box.pack(fill='both', expand=True,
                              padx=14, pady=(6, 12))
        self.factors_box.configure(state='disabled')

        ctk.CTkLabel(left, text='Prime factorization',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, anchor='w').pack(fill='x',
                                                     padx=14, pady=(0, 4))
        self.factorization_lbl = ctk.CTkLabel(
            left, text='', font=('Segoe UI', 18, 'bold'),
            text_color=ACCENT, anchor='w', justify='left',
            wraplength=360)
        self.factorization_lbl.pack(fill='x', padx=14, pady=(0, 14))

        # Right column — chart + number-theory facts
        right = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=10)
        right.grid(row=0, column=1, sticky='nsew', padx=(6, 8))

        ctk.CTkLabel(right, text='Prime factor multiplicities',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, anchor='w').pack(fill='x',
                                                     padx=14, pady=(12, 4))

        chart_frame = ctk.CTkFrame(right, fg_color=BG, corner_radius=8)
        chart_frame.pack(fill='both', expand=True, padx=14, pady=(0, 10))

        self.fig = Figure(figsize=(5, 3.2), facecolor=BG, dpi=100)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)

        # Number-theory grid
        ntg = ctk.CTkFrame(right, fg_color='transparent')
        ntg.pack(fill='x', padx=14, pady=(0, 12))
        for i in range(4):
            ntg.grid_columnconfigure(i, weight=1, uniform='nt')

        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        for col, (key, title) in enumerate([
            ('sigma0', 'σ₀ count'),
            ('sigma1', 'σ₁ sum'),
            ('aliquot', 's (aliquot)'),
            ('phi', 'φ totient'),
        ]):
            cell = ctk.CTkFrame(ntg, fg_color=SUNKEN, corner_radius=8)
            cell.grid(row=0, column=col, padx=4, pady=2, sticky='nsew')
            ctk.CTkLabel(cell, text=title,
                         font=('Segoe UI', 11),
                         text_color=MUTED).pack(pady=(8, 0))
            value = ctk.CTkLabel(cell, text='—',
                                 font=('Consolas', 14, 'bold'),
                                 text_color=FG)
            value.pack(pady=(0, 8))
            self._stat_labels[key] = value

        # Bottom hint
        hint = ctk.CTkLabel(self,
                            text='Press Enter or click Compute · '
                                 'classification highlights prime / perfect / '
                                 'abundant / deficient',
                            font=('Segoe UI', 11), text_color=MUTED)
        hint.pack(side='bottom', pady=(0, 8))

    def _style_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_color(GRID)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.title.set_color(FG)
        ax.grid(True, color='#1e293b', linewidth=0.8, axis='y')

    # ------------------------------------------------------------- compute
    def _set_factor_text(self, text: str) -> None:
        self.factors_box.configure(state='normal')
        self.factors_box.delete('1.0', 'end')
        self.factors_box.insert('1.0', text)
        self.factors_box.configure(state='disabled')

    def _compute(self) -> None:
        raw = self.entry.get().strip()
        try:
            n = int(raw)
        except ValueError:
            self._set_factor_text('')
            self.factor_count_lbl.configure(text='Enter a valid integer.')
            self.factorization_lbl.configure(text='', text_color=BAD)
            self.summary.configure(text='Invalid input.', text_color=BAD)
            self.class_chip.configure(text='ERROR', fg_color=BAD,
                                      text_color=FG)
            self.ax.clear()
            self._style_axes()
            self.canvas.draw()
            return
        if n <= 0:
            self._set_factor_text('')
            self.factor_count_lbl.configure(text='N must be positive.')
            self.factorization_lbl.configure(text='', text_color=BAD)
            self.summary.configure(text='N must be a positive integer.',
                                   text_color=BAD)
            self.class_chip.configure(text='ERROR', fg_color=BAD,
                                      text_color=FG)
            self.ax.clear()
            self._style_axes()
            self.canvas.draw()
            return

        # For huge N the factor list itself would be astronomical; cap it.
        # (prime_factorization handles big N via Pollard's rho.)
        try:
            self.compute_btn.configure(state='disabled', text='Working…')
            self.update_idletasks()

            pf = prime_factorization(n)
            label = classify(n)
            sigma1 = divisor_sum(n)
            phi = euler_totient(n)
            aliquot = proper_divisor_sum(n)

            # Only enumerate divisors directly when feasible.
            if n <= 5_000_000:
                divs = factors(n)
                divs_text = ', '.join(str(d) for d in divs)
                count = len(divs)
            else:
                # sigma_0 from prime factorization, but skip explicit list.
                count = 1
                for e in pf.values():
                    count *= (e + 1)
                divs_text = ('(divisor list suppressed for very large N — '
                             f'σ₀ = {count})')
        finally:
            self.compute_btn.configure(state='normal', text='Compute')

        # ---------- Update widgets ----------
        self._set_factor_text(divs_text)
        self.factor_count_lbl.configure(
            text=f'{count} divisor{"s" if count != 1 else ""}')

        if pf:
            self.factorization_lbl.configure(
                text=f'{n} = {pretty_factorization(pf)}', text_color=ACCENT)
        else:
            # n == 1
            self.factorization_lbl.configure(text='1 = 1 (no prime factors)',
                                             text_color=ACCENT)

        chip_color = CLASS_COLOR.get(label, '#334155')
        chip_text = label.upper()
        self.class_chip.configure(text=chip_text, fg_color=chip_color,
                                  text_color='#0b1220'
                                  if label in ('perfect', 'abundant')
                                  else FG)

        # Summary line
        if label == 'prime':
            extra = 'No proper factors except 1.'
        elif label == 'perfect':
            extra = f's(N) = {aliquot} = N — perfect number.'
        elif label == 'abundant':
            extra = f's(N) = {aliquot} > N — abundant number.'
        else:
            extra = f's(N) = {aliquot} < N — deficient number.'
        self.summary.configure(
            text=f'N = {n:,}.  {extra}', text_color=MUTED)

        self._stat_labels['sigma0'].configure(text=f'{count:,}')
        self._stat_labels['sigma1'].configure(text=f'{sigma1:,}')
        self._stat_labels['aliquot'].configure(text=f'{aliquot:,}')
        self._stat_labels['phi'].configure(text=f'{phi:,}')

        # ---------- Update chart ----------
        self._draw_chart(pf)

    def _draw_chart(self, pf: dict[int, int]) -> None:
        ax = self.ax
        ax.clear()
        self._style_axes()

        if not pf:
            ax.text(0.5, 0.5, '1 has no prime factors',
                    ha='center', va='center',
                    color=MUTED, fontsize=12,
                    transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            self.fig.tight_layout()
            self.canvas.draw()
            return

        primes = sorted(pf)
        exps = [pf[p] for p in primes]
        labels = [str(p) for p in primes]

        bars = ax.bar(labels, exps, color=ACCENT, edgecolor='#0ea5e9',
                      linewidth=1.0)
        for bar, e in zip(bars, exps):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.05,
                    str(e), ha='center', va='bottom',
                    color=FG, fontsize=10, fontweight='bold')

        ax.set_xlabel('Prime factor')
        ax.set_ylabel('Multiplicity (exponent)')
        ax.set_title('Prime factor multiplicities')
        # Integer ticks on Y axis
        ymax = max(exps) + 1
        ax.set_ylim(0, ymax + 0.2)
        ax.set_yticks(range(0, ymax + 1))

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == '__main__':
    FactorFinderApp().mainloop()
