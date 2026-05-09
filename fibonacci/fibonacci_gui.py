"""Fibonacci — CustomTkinter GUI with embedded matplotlib.

Compute F(N) using any of five algorithms, time it, and plot F(k) for
k = 1..N. Toggle log scale to make the exponential growth visible across
the whole range. The status line reports F(N)/F(N-1), which converges to
the golden ratio phi.

Run:
    uv run python fibonacci/fibonacci_gui.py
"""
from __future__ import annotations

import math
import time

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from fibonacci import (
    ALGORITHMS,
    RECURSIVE_MAX,
    compute,
    sequence_up_to,
)

# Tailwind-ish dark palette (matches sibling projects).
BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
GOLD = '#f59e0b'
GREEN = '#34d399'
RED = '#f87171'

PHI = (1.0 + math.sqrt(5.0)) / 2.0
DEFAULT_N = 20
N_MAX_CHART = 200  # Above this we still compute, but cap the plotted range.


class FibonacciApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Fibonacci')
        self.geometry('900x780')
        self.minsize(760, 660)
        self.configure(fg_color=BG)

        self._log_scale = ctk.BooleanVar(value=False)
        self._build_ui()
        self._compute_and_draw()

    # ---------- UI ----------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='FIBONACCI',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(header,
                     text='Five algorithms, one sequence — F(n) = F(n-1) + F(n-2)',
                     font=('Segoe UI', 12),
                     text_color=MUTED).pack(pady=(2, 0))

        # Status (bottom).
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 12),
                                   text_color=MUTED, justify='center')
        self.status.pack(side='bottom', pady=(2, 10))

        # Controls (bottom).
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='bottom', padx=20, pady=(4, 4), fill='x')

        row1 = ctk.CTkFrame(controls, fg_color='transparent')
        row1.pack(padx=14, pady=(10, 4), fill='x')
        ctk.CTkLabel(row1, text='N:', font=('Segoe UI', 13, 'bold'),
                     text_color=FG, width=40, anchor='w').pack(side='left')
        self.n_entry = ctk.CTkEntry(row1, width=90,
                                    font=('Segoe UI', 13))
        self.n_entry.insert(0, str(DEFAULT_N))
        self.n_entry.pack(side='left', padx=(0, 16))
        self.n_entry.bind('<Return>', lambda _e: self._compute_and_draw())

        ctk.CTkLabel(row1, text='Algorithm:',
                     font=('Segoe UI', 13), text_color=FG).pack(side='left')
        self.algo_var = ctk.StringVar(value='iter')
        self.algo_menu = ctk.CTkOptionMenu(
            row1, variable=self.algo_var, values=list(ALGORITHMS), width=130,
            font=('Segoe UI', 12))
        self.algo_menu.pack(side='left', padx=(8, 16))

        self.log_check = ctk.CTkCheckBox(
            row1, text='Log y-scale', variable=self._log_scale,
            command=self._redraw, font=('Segoe UI', 12))
        self.log_check.pack(side='left', padx=(0, 16))

        self.bench_var = ctk.BooleanVar(value=False)
        self.bench_check = ctk.CTkCheckBox(
            row1, text='Benchmark all', variable=self.bench_var,
            font=('Segoe UI', 12))
        self.bench_check.pack(side='left')

        self.compute_btn = ctk.CTkButton(
            row1, text='Compute', width=120,
            font=('Segoe UI', 13, 'bold'),
            command=self._compute_and_draw)
        self.compute_btn.pack(side='right')

        # Result panel (above controls).
        result_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        result_frame.pack(side='bottom', padx=20, pady=(0, 6), fill='x')

        self.result_value = ctk.CTkLabel(
            result_frame, text='', font=('Consolas', 14),
            text_color=FG, anchor='w', justify='left',
            wraplength=820)
        self.result_value.pack(padx=12, pady=(8, 2), fill='x')
        self.result_meta = ctk.CTkLabel(
            result_frame, text='', font=('Segoe UI', 12),
            text_color=MUTED, anchor='w', justify='left')
        self.result_meta.pack(padx=12, pady=(0, 2), fill='x')
        self.ratio_label = ctk.CTkLabel(
            result_frame, text='', font=('Segoe UI', 12),
            text_color=GOLD, anchor='w', justify='left')
        self.ratio_label.pack(padx=12, pady=(0, 8), fill='x')

        # Chart area fills the middle.
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

    # ---------- Compute / draw ----------

    def _parse_n(self) -> int | None:
        raw = self.n_entry.get().strip()
        try:
            n = int(raw)
        except ValueError:
            self._error(f'N must be an integer, got {raw!r}')
            return None
        if n < 0:
            self._error('N must be non-negative')
            return None
        return n

    def _error(self, msg: str) -> None:
        self.result_value.configure(text='—', text_color=RED)
        self.result_meta.configure(text=msg, text_color=RED)
        self.ratio_label.configure(text='')
        self.status.configure(text=msg, text_color=RED)

    def _compute_and_draw(self) -> None:
        n = self._parse_n()
        if n is None:
            return

        algo = self.algo_var.get()
        if algo == 'recursive' and n > RECURSIVE_MAX:
            self._error(f'naive recursion blocked for n>{RECURSIVE_MAX} '
                        f'(O(2^n) would hang)')
            return

        if self.bench_var.get():
            self._benchmark(n)
        else:
            self._single(n, algo)

        self._redraw()

    def _single(self, n: int, algo: str) -> None:
        try:
            start = time.perf_counter()
            value = compute(n, algo)
            secs = time.perf_counter() - start
        except (ValueError, RecursionError) as exc:
            self._error(str(exc))
            return

        shown = str(value)
        digits = len(shown)
        if digits > 80:
            shown = shown[:40] + '...' + shown[-20:]
        self.result_value.configure(
            text=f'F({n}) = {shown}', text_color=FG)
        self.result_meta.configure(
            text=f'{digits:,} digits   |   {algo}   |   {secs * 1000:.3f} ms',
            text_color=MUTED)

        # phi convergence.
        if n >= 2:
            try:
                fn = compute(n, 'iter')
                fn1 = compute(n - 1, 'iter')
                ratio = fn / fn1 if fn1 else float('inf')
                err = abs(ratio - PHI)
                self.ratio_label.configure(
                    text=(f'F({n})/F({n - 1}) = {ratio:.12f}    '
                          f'phi = {PHI:.12f}    '
                          f'|error| = {err:.2e}'))
            except (OverflowError, ZeroDivisionError):
                # Float division of huge ints overflows; use log-domain.
                self.ratio_label.configure(text='ratio: (too large for float)')
        else:
            self.ratio_label.configure(text='')

        self.status.configure(
            text=f'Computed F({n}) via {algo} in {secs * 1000:.3f} ms',
            text_color=MUTED)

    def _benchmark(self, n: int) -> None:
        from fibonacci import benchmark
        results = benchmark(n)
        # Find fastest for highlight.
        fastest_algo = min(results, key=lambda a: results[a][1])

        lines = []
        for algo in ALGORITHMS:
            if algo not in results:
                lines.append(f'{algo:<10} skipped (would explode)')
                continue
            value, secs = results[algo]
            ms = secs * 1000
            tag = ' <-- fastest' if algo == fastest_algo else ''
            lines.append(f'{algo:<10} {ms:>10.3f} ms{tag}')
        self.result_value.configure(
            text=f'Benchmark for F({n}):\n' + '\n'.join(lines),
            text_color=FG)
        self.result_meta.configure(
            text='All algorithms compared on the same N',
            text_color=MUTED)
        self.ratio_label.configure(text='')
        self.status.configure(
            text=f'Benchmark complete — fastest: {fastest_algo}',
            text_color=GREEN)

    def _redraw(self) -> None:
        n = self._parse_n()
        if n is None:
            return
        ax = self.ax
        ax.clear()
        self._style_axes()

        plot_n = min(n, N_MAX_CHART)
        if plot_n < 1:
            ax.set_title('Pick N >= 1 to see the sequence')
            self.canvas.draw()
            return

        seq = sequence_up_to(plot_n)  # F(0)..F(plot_n)
        ks = list(range(1, plot_n + 1))
        vals = seq[1:]

        log_scale = self._log_scale.get()
        if log_scale:
            ax.set_yscale('log')

        ax.plot(ks, vals, color=ACCENT, linewidth=1.6, marker='o',
                markersize=3, label='F(k)', zorder=3)

        # Highlight the chosen N (or its plot cap).
        marker_k = plot_n
        marker_v = vals[-1]
        ax.scatter([marker_k], [marker_v], color=GOLD, s=60,
                   zorder=5, edgecolors=FG, linewidths=0.8,
                   label=f'F({marker_k})')

        ax.set_xlabel('k')
        ax.set_ylabel('F(k)' + (' (log)' if log_scale else ''))
        title = f'Fibonacci sequence — F(1) .. F({plot_n})'
        if n > N_MAX_CHART:
            title += f'   (capped from N={n})'
        ax.set_title(title)

        legend = ax.legend(loc='upper left', frameon=False,
                           labelcolor=FG, fontsize=9)
        for text in legend.get_texts():
            text.set_color(FG)

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == '__main__':
    FibonacciApp().mainloop()
