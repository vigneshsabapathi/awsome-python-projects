"""DNA Visualization — CustomTkinter GUI.

Dark-themed desktop viewer with Rich-style per-base coloring:
  A = red, T = orange, C = blue, G = green, U = magenta (mRNA)
Speed slider, transcription toggle, genome-mode toggle.

Run:
    uv run python dna_viz/dna_viz_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from dna_viz import BASE_COLORS, RESET, colorize, render_helix

BG    = '#0f172a'
PANEL = '#1e293b'
FG    = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
MONO  = ('Consolas', 11)

# Per-base tk colors (no ANSI)
BASE_TK: dict[str, str] = {
    'A': '#f87171',   # red
    'T': '#fb923c',   # orange
    'C': '#60a5fa',   # blue
    'G': '#4ade80',   # green
    'U': '#c084fc',   # magenta (mRNA uracil)
    '|': '#e2e8f0',   # off-white strand
    '-': '#475569',   # slate rung
}


class DNAApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('DNA Visualization')
        self.geometry('900x680')
        self.minsize(700, 500)
        self.configure(fg_color=BG)

        self.phase      = 0.0
        self.running    = True
        self.rng        = random.Random(42)
        self.g_offset   = 0
        self._after_id: str | None = None
        self._tag_names: list[str] = []

        self._build_ui()
        self._tick()

    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        # Header
        hdr = ctk.CTkFrame(self, fg_color='transparent')
        hdr.pack(side='top', pady=(12, 2), padx=20, fill='x')
        ctk.CTkLabel(hdr, text='DNA DOUBLE HELIX',
                     font=('Segoe UI', 22, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(hdr,
                     text='Two anti-parallel strands linked by complementary base pairs  '
                          ' A↔T  C↔G',
                     font=('Segoe UI', 11), text_color=MUTED).pack(anchor='w')

        # Controls
        ctrl = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        ctrl.pack(side='top', padx=20, pady=(6, 4), fill='x')
        ctrl.grid_columnconfigure((1, 3), weight=1)

        self.speed_var = ctk.DoubleVar(value=0.10)
        self._slider(ctrl, 0, 'Speed', self.speed_var, 0.0, 0.5)

        self.zoom_var = ctk.DoubleVar(value=1.0)
        self._slider(ctrl, 2, 'Zoom (rows)', self.zoom_var, 0.5, 2.0)

        # Toggles row
        tog = ctk.CTkFrame(self, fg_color='transparent')
        tog.pack(side='top', padx=20, pady=(2, 4), fill='x')

        self.transcribe_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(tog, text='Transcription mode (DNA→mRNA)',
                      variable=self.transcribe_var,
                      progress_color='#c084fc', text_color=FG,
                      font=('Segoe UI', 12)).pack(side='left', padx=(0, 16))

        self.genome_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(tog, text='Genome sequence',
                      variable=self.genome_var,
                      progress_color=ACCENT, text_color=FG,
                      font=('Segoe UI', 12)).pack(side='left', padx=(0, 16))

        self.pause_btn = ctk.CTkButton(
            tog, text='Pause', width=90,
            fg_color='#334155', hover_color='#475569',
            command=self._toggle_pause)
        self.pause_btn.pack(side='right')

        # Legend chips
        leg = ctk.CTkFrame(self, fg_color='transparent')
        leg.pack(side='top', padx=20, pady=(0, 4), fill='x')
        for base, color in [('A', '#f87171'), ('T', '#fb923c'),
                             ('C', '#60a5fa'), ('G', '#4ade80'),
                             ('U', '#c084fc')]:
            ctk.CTkLabel(leg, text=f'  {base}  ',
                         fg_color=color,
                         text_color='#0f172a' if base in ('T', 'U') else '#0f172a',
                         corner_radius=6,
                         font=('Segoe UI', 11, 'bold')).pack(
                side='left', padx=3)
        ctk.CTkLabel(leg, text='← bases   | = strand backbone   - = rung',
                     text_color=MUTED,
                     font=('Segoe UI', 10)).pack(side='left', padx=8)

        # Status bar
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 10),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 6))

        # Canvas (monospace textbox)
        self.canvas = ctk.CTkTextbox(self, font=MONO,
                                     fg_color=PANEL, text_color=FG,
                                     wrap='none')
        self.canvas.pack(side='top', fill='both', expand=True,
                         padx=20, pady=(0, 4))
        self.canvas.configure(state='disabled')

    def _slider(self, parent: ctk.CTkFrame, col: int, label: str,
                var: ctk.DoubleVar, lo: float, hi: float) -> None:
        ctk.CTkLabel(parent, text=label,
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).grid(row=0, column=col,
                                         sticky='w', padx=(12, 6), pady=(8, 0))
        readout = ctk.CTkLabel(parent, text=f'{var.get():.2f}',
                               text_color=MUTED, font=('Segoe UI', 11), width=48)
        readout.grid(row=0, column=col + 1, sticky='e',
                     padx=(0, 12), pady=(8, 0))
        ctk.CTkSlider(parent, variable=var, from_=lo, to=hi,
                      progress_color=ACCENT,
                      button_color=ACCENT,
                      button_hover_color='#0ea5e9').grid(
            row=1, column=col, columnspan=2, sticky='ew',
            padx=(12, 12), pady=(0, 10))
        var.trace_add('write', lambda *_a, v=var, r=readout:
                      r.configure(text=f'{v.get():.2f}'))

    # ------------------------------------------------------------------
    def _toggle_pause(self) -> None:
        self.running = not self.running
        self.pause_btn.configure(text='Resume' if not self.running else 'Pause')

    # ------------------------------------------------------------------
    def _tick(self) -> None:
        try:
            speed       = float(self.speed_var.get())
            zoom        = float(self.zoom_var.get())
            transcribe  = bool(self.transcribe_var.get())
            genome_mode = bool(self.genome_var.get())

            width, height = self._estimate_dims(zoom)
            frame = render_helix(
                width, height, self.phase, self.rng,
                transcribe=transcribe,
                genome_mode=genome_mode,
                genome_offset=self.g_offset,
            )
            self._draw_colored(frame)
            mode = 'DNA→mRNA' if transcribe else 'DNA helix'
            seq  = 'genome' if genome_mode else 'random'
            self.status.configure(
                text=f'{mode} | {seq} | phase={self.phase:.2f} | '
                     f'{"running" if self.running else "paused"}')

            if self.running:
                self.phase    += speed
                self.g_offset += 1
        except Exception as exc:
            self.status.configure(text=f'render error: {exc}')

        self._after_id = self.after(60, self._tick)  # ~16 fps

    def _estimate_dims(self, zoom: float) -> tuple[int, int]:
        try:
            pw = self.canvas.winfo_width()
            ph = self.canvas.winfo_height()
        except Exception:
            pw, ph = 0, 0
        w = max(40, min(200, pw // 7)) if pw > 1 else 80
        h = max(10, min(80, int(ph // 14 * zoom))) if ph > 1 else 30
        return w, h

    def _draw_colored(self, frame: str) -> None:
        self.canvas.configure(state='normal')
        # Remove old tags
        for tag in self._tag_names:
            try:
                self.canvas.tag_delete(tag)
            except Exception:
                pass
        self._tag_names.clear()
        self.canvas.delete('1.0', 'end')

        lines = frame.split('\n')
        for row_idx, line in enumerate(lines):
            if row_idx:
                self.canvas.insert('end', '\n')
            for col_idx, ch in enumerate(line):
                color = BASE_TK.get(ch, '')
                if color and ch != ' ':
                    tag = f'c{row_idx}_{col_idx}'
                    self._tag_names.append(tag)
                    start = self.canvas.index('end-1c')
                    self.canvas.insert('end', ch)
                    end = self.canvas.index('end-1c')
                    self.canvas.tag_add(tag, start, end)
                    self.canvas.tag_config(tag, foreground=color)
                else:
                    self.canvas.insert('end', ch)

        self.canvas.configure(state='disabled')

    def destroy(self) -> None:
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()


if __name__ == '__main__':
    DNAApp().mainloop()
