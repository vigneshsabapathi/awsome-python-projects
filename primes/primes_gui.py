"""Prime Numbers — CustomTkinter GUI.

Slider-driven sieve with an Ulam spiral painter. Primes form unexpected
diagonal lines on the spiral; the GUI also surfaces the prime-counting
function pi(N), prime gaps, and twin-prime counts.

Run:
    uv run python primes/primes_gui.py
"""
from __future__ import annotations

import math
import tkinter as tk
from typing import List, Tuple

import customtkinter as ctk

from primes import (
    prime_gaps,
    prime_pi,
    sieve,
    twin_primes,
)

BG = '#0f172a'
PANEL = '#1e293b'
SUNKEN = '#0b1220'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'        # composites
PRIME = '#a78bfa'         # primes
TWIN = '#34d399'          # twin primes (highlighted)
ONE = '#f59e0b'           # the lone center "1"
GRID = '#334155'

DEFAULT_N = 400


def ulam_coords(k: int) -> Tuple[int, int]:
    """Return integer (x, y) lattice coordinates for k on the Ulam spiral.

    The spiral places 1 at the origin, walks right, up, left x2, down x2,
    right x3, ... so each "leg" is ceil((step+1)/2) cells long. We unwind
    that by computing which "ring" k sits on, then walking along the ring.
    """
    if k < 1:
        raise ValueError('k must be >= 1')
    if k == 1:
        return (0, 0)
    # Find the smallest odd m with m*m >= k. The number m*m sits at the
    # bottom-right corner of ring (m-1)/2.
    m = math.isqrt(k - 1)
    if m % 2 == 0:
        m += 1
    if m * m < k:
        m += 2
    ring = (m - 1) // 2
    # Position k relative to the bottom-right corner m*m.
    offset = m * m - k         # 0 at bottom-right, increases going left
    side = 2 * ring             # length of one ring side
    if offset < side:
        # Bottom edge — moving left from (ring, -ring)
        return (ring - offset, -ring)
    offset -= side
    if offset < side:
        # Left edge — moving up from (-ring, -ring)
        return (-ring, -ring + offset)
    offset -= side
    if offset < side:
        # Top edge — moving right from (-ring, ring)
        return (-ring + offset, ring)
    offset -= side
    # Right edge — moving down from (ring, ring) (length side - 1, since
    # we already counted the corner). offset can be at most side - 1.
    return (ring, ring - offset)


class PrimesApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Prime Numbers')
        self.geometry('960x800')
        self.minsize(820, 700)
        self.configure(fg_color=BG)

        self._build_ui()
        self._compute(DEFAULT_N)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='PRIME NUMBERS',
                     font=('Segoe UI', 26, 'bold'),
                     text_color=FG).pack()
        ctk.CTkLabel(header,
                     text='Sieve of Eratosthenes · Ulam spiral · pi(N), gaps, twins',
                     font=('Segoe UI', 12), text_color=MUTED).pack(pady=(2, 0))

        # ---------- Slider row ----------
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        controls.pack(side='top', padx=20, pady=(8, 4), fill='x')

        ctk.CTkLabel(controls, text='N =',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG).pack(side='left', padx=(14, 6), pady=12)
        self.n_label = ctk.CTkLabel(controls, text=str(DEFAULT_N),
                                    font=('Consolas', 14, 'bold'),
                                    text_color=ACCENT, width=70)
        self.n_label.pack(side='left', pady=12)

        self.slider = ctk.CTkSlider(controls, from_=10, to=10000,
                                    number_of_steps=999,
                                    command=self._on_slider)
        self.slider.set(DEFAULT_N)
        self.slider.pack(side='left', padx=12, pady=12, fill='x', expand=True)

        self.twin_chk = ctk.CTkCheckBox(controls, text='Highlight twin primes',
                                        command=self._redraw_only,
                                        text_color=FG)
        self.twin_chk.select()
        self.twin_chk.pack(side='left', padx=(8, 14), pady=12)

        # ---------- Stat strip ----------
        stat_row = ctk.CTkFrame(self, fg_color='transparent')
        stat_row.pack(side='top', padx=20, pady=(2, 4), fill='x')
        for i in range(5):
            stat_row.grid_columnconfigure(i, weight=1, uniform='st')

        self._stat_widgets: dict[str, ctk.CTkLabel] = {}
        for col, (key, title) in enumerate([
            ('pi', 'pi(N)'),
            ('largest', 'largest prime'),
            ('avg_gap', 'avg gap'),
            ('max_gap', 'max gap'),
            ('twins', 'twin pairs'),
        ]):
            cell = ctk.CTkFrame(stat_row, fg_color=SUNKEN, corner_radius=8)
            cell.grid(row=0, column=col, padx=4, sticky='nsew')
            ctk.CTkLabel(cell, text=title,
                         font=('Segoe UI', 11),
                         text_color=MUTED).pack(pady=(8, 0))
            value = ctk.CTkLabel(cell, text='—',
                                 font=('Consolas', 14, 'bold'),
                                 text_color=FG)
            value.pack(pady=(0, 8))
            self._stat_widgets[key] = value

        # ---------- Canvas ----------
        canvas_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        canvas_frame.pack(side='top', fill='both', expand=True,
                          padx=20, pady=(4, 4))

        self.canvas = tk.Canvas(canvas_frame, bg=SUNKEN,
                                highlightthickness=0)
        self.canvas.pack(fill='both', expand=True, padx=10, pady=10)
        self.canvas.bind('<Configure>', lambda _e: self._redraw_only())

        # Tooltip-style status when hovering the canvas
        self.canvas.bind('<Motion>', self._on_hover)
        self.hover_label = ctk.CTkLabel(self, text='Hover over a cell',
                                        font=('Consolas', 11),
                                        text_color=MUTED, anchor='w')
        self.hover_label.pack(side='top', fill='x', padx=22, pady=(0, 4))

        # ---------- Legend ----------
        legend = ctk.CTkFrame(self, fg_color='transparent')
        legend.pack(side='bottom', pady=(0, 10))

        def chip(parent, color: str, text: str) -> None:
            sw = tk.Canvas(parent, width=14, height=14, bg=BG,
                           highlightthickness=0)
            sw.create_rectangle(1, 1, 13, 13, fill=color, outline=color)
            sw.pack(side='left', padx=(8, 4))
            ctk.CTkLabel(parent, text=text, font=('Segoe UI', 11),
                         text_color=MUTED).pack(side='left', padx=(0, 8))

        chip(legend, PRIME, 'prime')
        chip(legend, TWIN, 'twin prime (p, p+2)')
        chip(legend, ACCENT, 'composite')
        chip(legend, ONE, '1 (unit)')

        # Cached state
        self._cells: List[Tuple[int, int, int, int, int]] = []
        # tuples (k, x0, y0, x1, y1) in canvas coords
        self._primes: set[int] = set()
        self._twin_set: set[int] = set()
        self._n: int = 0

    # ------------------------------------------------------------- handlers
    def _on_slider(self, value: float) -> None:
        n = int(round(value))
        # Round to a nice integer for display.
        self.n_label.configure(text=str(n))
        self._compute(n)

    def _redraw_only(self) -> None:
        if self._n:
            self._draw_spiral(self._n)

    def _on_hover(self, event: tk.Event) -> None:
        # Linear scan is fine — at most 10001 cells.
        for k, x0, y0, x1, y1 in self._cells:
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                if k == 1:
                    label = 'k = 1 (neither prime nor composite)'
                elif k in self._twin_set:
                    label = f'k = {k} (twin prime)'
                elif k in self._primes:
                    label = f'k = {k} (prime)'
                else:
                    label = f'k = {k} (composite)'
                self.hover_label.configure(text=label)
                return
        self.hover_label.configure(text='Hover over a cell')

    # ------------------------------------------------------------- compute
    def _compute(self, n: int) -> None:
        n = max(1, int(n))
        self._n = n

        primes_list = sieve(n)
        self._primes = set(primes_list)

        # Twin primes: keep both members of every (p, p+2) pair (only those
        # whose larger member is <= n).
        twins = twin_primes(primes_list)
        twin_members: set[int] = set()
        for p, q in twins:
            twin_members.add(p)
            twin_members.add(q)
        self._twin_set = twin_members

        gaps = prime_gaps(primes_list)
        avg_gap = (sum(gaps) / len(gaps)) if gaps else 0.0
        max_gap = max(gaps) if gaps else 0

        self._stat_widgets['pi'].configure(text=f'{prime_pi(n):,}')
        self._stat_widgets['largest'].configure(
            text=f'{primes_list[-1]:,}' if primes_list else '—')
        self._stat_widgets['avg_gap'].configure(
            text=f'{avg_gap:.2f}' if gaps else '—')
        self._stat_widgets['max_gap'].configure(
            text=f'{max_gap}' if gaps else '—')
        self._stat_widgets['twins'].configure(text=f'{len(twins):,}')

        self._draw_spiral(n)

    def _draw_spiral(self, n: int) -> None:
        self.canvas.delete('all')
        self._cells = []

        w = max(self.canvas.winfo_width(), 100)
        h = max(self.canvas.winfo_height(), 100)

        # Choose a square spiral with side s such that s*s >= n.
        s = math.isqrt(n)
        if s * s < n:
            s += 1
        if s % 2 == 0:
            s += 1   # odd side keeps the spiral centered on (0, 0)

        # Compute coords up front so we know the bounding box.
        coords = [ulam_coords(k) for k in range(1, n + 1)]
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)

        cell_w = max(2, min((w - 20) // (x_max - x_min + 1),
                            (h - 20) // (y_max - y_min + 1)))
        # Always at least 2 px so structure remains visible at large N.
        bx = (w - cell_w * (x_max - x_min + 1)) / 2
        by = (h - cell_w * (y_max - y_min + 1)) / 2

        highlight_twins = bool(self.twin_chk.get())

        for k, (gx, gy) in enumerate(coords, start=1):
            # Convert grid coords to canvas pixels (y flipped: spiral up = up).
            cx = bx + (gx - x_min) * cell_w
            cy = by + (y_max - gy) * cell_w
            x1 = cx + cell_w
            y1 = cy + cell_w

            if k == 1:
                color = ONE
            elif highlight_twins and k in self._twin_set:
                color = TWIN
            elif k in self._primes:
                color = PRIME
            else:
                color = ACCENT

            outline = SUNKEN if cell_w >= 6 else color
            self.canvas.create_rectangle(cx, cy, x1, y1,
                                         fill=color, outline=outline,
                                         width=1 if cell_w >= 6 else 0)
            self._cells.append((k, int(cx), int(cy), int(x1), int(y1)))

        # Center marker text when cell big enough
        if cell_w >= 14:
            for k, x0, y0, x1, y1 in self._cells:
                if cell_w >= 20:
                    self.canvas.create_text((x0 + x1) // 2, (y0 + y1) // 2,
                                            text=str(k),
                                            fill=SUNKEN if k != 1 else FG,
                                            font=('Consolas',
                                                  max(8, cell_w // 3)))


if __name__ == '__main__':
    PrimesApp().mainloop()
