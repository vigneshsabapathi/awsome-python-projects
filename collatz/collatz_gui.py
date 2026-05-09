"""Collatz Sequence — CustomTkinter GUI.

Two embedded matplotlib views in one dark-themed window:

- Top chart: the hailstone path for the current n (value vs step index).
  Toggle linear / log y-axis. The peak step is marked.
- Bottom chart: stopping-time scatter for n = 1..N, with N controlled by
  a slider. The chaotic banded structure is the visually striking pattern
  the conjecture lives in.

Run:
    uv run python collatz/collatz_gui.py
"""
from __future__ import annotations

import customtkinter as ctk
import matplotlib

matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from collatz import (
    collatz_sequence,
    max_value,
    stopping_time,
    stopping_times_up_to,
)

DEFAULT_N = 27          # Famous: peaks at 9232, 111 steps.
N_INPUT_MAX = 10 ** 12  # We accept big n; matplotlib handles it via log scale.
COMPARE_MIN, COMPARE_MAX = 50, 5000
DEFAULT_COMPARE = 1000

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
HOT = '#f59e0b'
WIN = '#34d399'
DANGER = '#f87171'


class CollatzApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Collatz Sequence')
        self.geometry('960x820')
        self.minsize(820, 680)
        self.configure(fg_color=BG)

        self.current_n: int = DEFAULT_N
        self.current_seq: list[int] = collatz_sequence(DEFAULT_N)
        self.compare_limit: int = DEFAULT_COMPARE
        self.log_scale: bool = False
        self.stopping_times: list[int] = []

        self._build_ui()
        self._compute_stopping_times()
        self._redraw_all()

    # ---------- UI scaffolding ----------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='COLLATZ SEQUENCE',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(
            header,
            text='Hailstone numbers — every positive integer (we believe) reaches 1',
            font=('Segoe UI', 12), text_color=MUTED,
        ).pack(pady=(2, 0))

        # Status bar at bottom.
        self.status = ctk.CTkLabel(
            self, text='', font=('Segoe UI', 12),
            text_color=MUTED, justify='center',
        )
        self.status.pack(side='bottom', pady=(2, 10))

        # Controls panel.
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='bottom', padx=20, pady=(4, 4), fill='x')

        # Row 1: n input + log toggle + run button.
        row1 = ctk.CTkFrame(controls, fg_color='transparent')
        row1.pack(padx=14, pady=(10, 4), fill='x')
        ctk.CTkLabel(row1, text='Starting n:',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG, width=110, anchor='w').pack(side='left')
        self.n_entry = ctk.CTkEntry(row1, width=160,
                                    font=('Segoe UI', 13))
        self.n_entry.insert(0, str(DEFAULT_N))
        self.n_entry.pack(side='left', padx=(0, 8))
        self.n_entry.bind('<Return>', lambda _e: self._on_apply_n())

        ctk.CTkButton(row1, text='Plot', width=80,
                      font=('Segoe UI', 12, 'bold'),
                      command=self._on_apply_n).pack(side='left')

        self.log_switch = ctk.CTkSwitch(
            row1, text='Log scale', font=('Segoe UI', 12),
            command=self._on_log_toggle,
        )
        self.log_switch.pack(side='right')

        # Row 2: compare slider for stopping-time scatter.
        row2 = ctk.CTkFrame(controls, fg_color='transparent')
        row2.pack(padx=14, pady=(4, 10), fill='x')
        self.compare_label = ctk.CTkLabel(
            row2,
            text=f'Compare n = 1..{DEFAULT_COMPARE}',
            font=('Segoe UI', 13, 'bold'),
            text_color=FG, width=200, anchor='w',
        )
        self.compare_label.pack(side='left')
        self.compare_slider = ctk.CTkSlider(
            row2, from_=COMPARE_MIN, to=COMPARE_MAX,
            number_of_steps=(COMPARE_MAX - COMPARE_MIN) // 50,
            command=self._on_compare_slider,
        )
        self.compare_slider.set(DEFAULT_COMPARE)
        self.compare_slider.pack(side='left', fill='x', expand=True,
                                 padx=(8, 0))

        # Charts area: split between sequence text + sequence chart + scatter.
        charts = ctk.CTkFrame(self, fg_color=BG)
        charts.pack(side='top', fill='both', expand=True,
                    padx=12, pady=(8, 4))

        # Top: sequence chart on the right, scrollable text on the left.
        top = ctk.CTkFrame(charts, fg_color=BG)
        top.pack(side='top', fill='both', expand=True)

        text_frame = ctk.CTkFrame(top, fg_color=PANEL, corner_radius=8)
        text_frame.pack(side='left', fill='y', padx=(0, 8))
        ctk.CTkLabel(text_frame, text='Sequence',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(pady=(8, 2), padx=10, anchor='w')
        self.seq_text = ctk.CTkTextbox(
            text_frame, width=240, font=('Consolas', 11),
            fg_color='#0b1220', text_color=FG, border_width=0,
        )
        self.seq_text.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        seq_chart_frame = ctk.CTkFrame(top, fg_color=BG)
        seq_chart_frame.pack(side='left', fill='both', expand=True)
        self.seq_fig = Figure(figsize=(6, 3), facecolor=BG, dpi=100)
        self.seq_ax = self.seq_fig.add_subplot(111)
        self._style_axes(self.seq_ax)
        self.seq_canvas = FigureCanvasTkAgg(self.seq_fig, master=seq_chart_frame)
        self.seq_canvas.get_tk_widget().pack(fill='both', expand=True)

        # Bottom: stopping-time scatter.
        scatter_frame = ctk.CTkFrame(charts, fg_color=BG)
        scatter_frame.pack(side='top', fill='both', expand=True,
                           pady=(8, 0))
        self.scatter_fig = Figure(figsize=(8, 3), facecolor=BG, dpi=100)
        self.scatter_ax = self.scatter_fig.add_subplot(111)
        self._style_axes(self.scatter_ax)
        self.scatter_canvas = FigureCanvasTkAgg(self.scatter_fig,
                                                master=scatter_frame)
        self.scatter_canvas.get_tk_widget().pack(fill='both', expand=True)

    def _style_axes(self, ax) -> None:
        ax.set_facecolor(BG)
        for spine in ax.spines.values():
            spine.set_color('#334155')
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.xaxis.label.set_color(MUTED)
        ax.yaxis.label.set_color(MUTED)
        ax.title.set_color(FG)
        ax.grid(True, color='#1e293b', linewidth=0.8)

    # ---------- Event handlers ----------

    def _on_apply_n(self) -> None:
        raw = self.n_entry.get().strip()
        try:
            n = int(raw)
        except ValueError:
            self.status.configure(
                text=f'Invalid n: {raw!r} (must be a positive integer)',
                text_color=DANGER)
            return
        if n <= 0:
            self.status.configure(
                text=f'n must be positive (got {n})', text_color=DANGER)
            return
        if n > N_INPUT_MAX:
            self.status.configure(
                text=f'n is too large (limit {N_INPUT_MAX:,})',
                text_color=DANGER)
            return
        self.current_n = n
        try:
            self.current_seq = collatz_sequence(n)
        except RecursionError:
            self.status.configure(text='Sequence too long to render',
                                  text_color=DANGER)
            return
        self._redraw_sequence()
        self._redraw_status()

    def _on_log_toggle(self) -> None:
        self.log_scale = bool(self.log_switch.get())
        self._redraw_sequence()

    def _on_compare_slider(self, value: float) -> None:
        # Snap to multiples of 50 so we don't recompute on every pixel.
        new_limit = int(round(value / 50) * 50)
        new_limit = max(COMPARE_MIN, min(COMPARE_MAX, new_limit))
        if new_limit == self.compare_limit:
            return
        self.compare_limit = new_limit
        self.compare_label.configure(text=f'Compare n = 1..{new_limit}')
        self._compute_stopping_times()
        self._redraw_scatter()
        self._redraw_status()

    # ---------- Compute ----------

    def _compute_stopping_times(self) -> None:
        self.stopping_times = stopping_times_up_to(self.compare_limit)

    # ---------- Redraw ----------

    def _redraw_all(self) -> None:
        self._redraw_sequence()
        self._redraw_scatter()
        self._redraw_status()

    def _redraw_sequence(self) -> None:
        ax = self.seq_ax
        ax.clear()
        self._style_axes(ax)

        seq = self.current_seq
        ax.plot(range(len(seq)), seq, color=ACCENT, linewidth=1.6, zorder=3)
        ax.scatter(range(len(seq)), seq, s=14, color=ACCENT, zorder=4)

        peak = max(seq)
        peak_idx = seq.index(peak)
        ax.scatter([peak_idx], [peak], s=70, color=HOT,
                   edgecolor=FG, linewidth=1.2, zorder=5,
                   label=f'peak = {peak:,}')
        ax.axhline(1, color='#475569', linewidth=0.6, linestyle='--',
                   alpha=0.6)

        ax.set_xlabel('Step index')
        ax.set_ylabel('Value')
        ax.set_title(
            f'Hailstone path for n = {self.current_n:,}'
            f'   ({len(seq) - 1} steps, peak {peak:,})')
        if self.log_scale:
            ax.set_yscale('log')
        else:
            ax.set_yscale('linear')

        legend = ax.legend(loc='upper right', frameon=False,
                           labelcolor=FG, fontsize=9)
        if legend is not None:
            for text in legend.get_texts():
                text.set_color(FG)

        self.seq_fig.tight_layout()
        self.seq_canvas.draw()

        # Refresh the side text box.
        self.seq_text.configure(state='normal')
        self.seq_text.delete('1.0', 'end')
        # Show as wrapped comma-separated list; cap displayed length so very
        # long sequences don't freeze the textbox.
        max_show = 4000
        items = [f'{v:,}' for v in seq[:max_show]]
        body = ', '.join(items)
        if len(seq) > max_show:
            body += f', … ({len(seq) - max_show} more)'
        self.seq_text.insert('1.0', body)
        self.seq_text.configure(state='disabled')

    def _redraw_scatter(self) -> None:
        ax = self.scatter_ax
        ax.clear()
        self._style_axes(ax)

        ns = list(range(1, self.compare_limit + 1))
        ts = self.stopping_times
        ax.scatter(ns, ts, s=4, color=ACCENT, alpha=0.55, zorder=3)

        # Highlight current n.
        if 1 <= self.current_n <= self.compare_limit:
            cn_steps = ts[self.current_n - 1]
            ax.scatter([self.current_n], [cn_steps],
                       s=70, color=HOT, edgecolor=FG, linewidth=1.2,
                       zorder=5,
                       label=f'n = {self.current_n}, steps = {cn_steps}')
            legend = ax.legend(loc='upper left', frameon=False,
                               labelcolor=FG, fontsize=9)
            if legend is not None:
                for text in legend.get_texts():
                    text.set_color(FG)

        ax.set_xlabel('Starting n')
        ax.set_ylabel('Stopping time (steps)')
        ax.set_title(
            'Stopping time vs n — note the chaotic banded structure '
            '(conjectured but unproven to be finite)')

        self.scatter_fig.tight_layout()
        self.scatter_canvas.draw()

    def _redraw_status(self) -> None:
        n = self.current_n
        seq = self.current_seq
        steps = len(seq) - 1
        peak = max(seq)
        # Hardest n found in the current compare range.
        if self.stopping_times:
            best_idx = max(range(len(self.stopping_times)),
                           key=self.stopping_times.__getitem__)
            best_n = best_idx + 1
            best_steps = self.stopping_times[best_idx]
            extra = (f'   |   record in 1..{self.compare_limit}: '
                     f'n={best_n} → {best_steps} steps')
        else:
            extra = ''
        self.status.configure(
            text=(f'n={n:,}   steps={steps}   peak={peak:,}'
                  f'   ratio={peak / n:.1f}x{extra}'),
            text_color=MUTED,
        )


if __name__ == '__main__':
    CollatzApp().mainloop()
