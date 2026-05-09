"""Progress Bar — CustomTkinter GUI gallery.

Side-by-side gallery of every bar style animating in unison. Speed slider
controls how fast progress climbs; target slider sets the goal; restart
resets every bar to 0%.

Run:
    uv run python progress_bar/progress_bar_gui.py
"""
from __future__ import annotations

import time

import customtkinter as ctk

from progress_bar import STYLES, format_eta, format_rate

BG = '#0f172a'
PANEL = '#1e293b'
PANEL_FG = '#0b1220'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'

HEADER_FONT = ('Segoe UI', 24, 'bold')
LABEL_FONT = ('Segoe UI', 13)
SMALL_FONT = ('Segoe UI', 11)
META_FONT = ('Consolas', 11)

# Color pairs for the canvas-drawn progress fill, one per style.
STYLE_COLORS: dict[str, tuple[str, str]] = {
    'blocks':   ('#22d3ee', '#67e8f9'),  # cyan
    'simple':   ('#94a3b8', '#cbd5e1'),  # slate
    'dots':     ('#f472b6', '#f9a8d4'),  # pink
    'gradient': ('#a78bfa', '#facc15'),  # purple → yellow gradient
    'spinner':  ('#34d399', '#6ee7b7'),  # green
}

# 10-frame spinner glyphs (Braille) for the spinner row.
SPINNER_GLYPHS = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'


class _BarRow:
    """One row in the gallery: name + canvas bar + ETA/rate readout."""

    def __init__(self, parent: ctk.CTkFrame, style: str) -> None:
        self.style = style
        self.spinner_idx = 0

        self.frame = ctk.CTkFrame(parent, fg_color='transparent')
        self.frame.pack(fill='x', padx=18, pady=6)

        self.name = ctk.CTkLabel(self.frame, text=style.upper(),
                                 font=('Segoe UI', 14, 'bold'),
                                 text_color=FG, width=110, anchor='w')
        self.name.pack(side='left')

        self.canvas = ctk.CTkCanvas(
            self.frame, height=28, bg=PANEL_FG,
            highlightthickness=0, bd=0,
        )
        self.canvas.pack(side='left', fill='x', expand=True, padx=(8, 8))

        self.meta = ctk.CTkLabel(self.frame, text='',
                                 font=META_FONT, text_color=MUTED,
                                 width=200, anchor='e')
        self.meta.pack(side='right')

    def draw(self, progress: float, eta_text: str, rate_text: str) -> None:
        progress = max(0.0, min(1.0, progress))
        c = self.canvas
        c.delete('all')
        # update_idletasks lets us read the actual width post-pack.
        c.update_idletasks()
        w = c.winfo_width() or 400
        h = c.winfo_height() or 28
        # Background track
        c.create_rectangle(0, 0, w, h, fill=PANEL, outline='')
        fill_w = int(w * progress)

        if self.style == 'blocks':
            # Solid fill with a brighter cap on the leading edge.
            primary, secondary = STYLE_COLORS['blocks']
            c.create_rectangle(0, 0, fill_w, h, fill=primary, outline='')
            cap_w = min(6, fill_w)
            if cap_w:
                c.create_rectangle(fill_w - cap_w, 0, fill_w, h,
                                   fill=secondary, outline='')

        elif self.style == 'simple':
            # ASCII-style fill: dashes + arrow head, drawn as text.
            primary, _ = STYLE_COLORS['simple']
            cells = max(1, w // 10)
            filled_cells = int(cells * progress)
            chars = '=' * max(0, filled_cells - 1)
            if 0 < filled_cells < cells:
                chars += '>'
            elif filled_cells == cells:
                chars = '=' * cells
            text = '[' + chars.ljust(cells) + ']'
            c.create_text(8, h // 2, text=text, anchor='w',
                          fill=primary, font=('Consolas', 11, 'bold'))

        elif self.style == 'dots':
            # Discrete dot column fill.
            primary, secondary = STYLE_COLORS['dots']
            num_dots = 30
            filled = int(num_dots * progress)
            dot_spacing = w / num_dots
            radius = max(2, int(h / 4))
            cy = h // 2
            for i in range(num_dots):
                cx = int((i + 0.5) * dot_spacing)
                color = primary if i < filled else '#334155'
                if i == filled - 1:
                    color = secondary  # leading dot gets a highlight
                c.create_oval(cx - radius, cy - radius,
                              cx + radius, cy + radius,
                              fill=color, outline='')

        elif self.style == 'gradient':
            # Simulated multi-stop gradient by stacking thin colored stripes.
            stops = ('#a78bfa', '#60a5fa', '#22d3ee',
                     '#34d399', '#facc15', '#fb7185')
            if fill_w > 0:
                stripes = max(1, fill_w)
                for x in range(0, stripes, 2):
                    t = x / max(1, fill_w - 1)
                    seg = t * (len(stops) - 1)
                    lo = int(seg)
                    hi = min(lo + 1, len(stops) - 1)
                    color = _blend(stops[lo], stops[hi], seg - lo)
                    c.create_rectangle(x, 0, x + 2, h, fill=color, outline='')

        elif self.style == 'spinner':
            primary, _ = STYLE_COLORS['spinner']
            # Spinner glyph on the left, fill bar to its right.
            glyph = SPINNER_GLYPHS[self.spinner_idx % len(SPINNER_GLYPHS)]
            c.create_text(14, h // 2, text=glyph, anchor='w',
                          fill=primary, font=('Consolas', 16, 'bold'))
            bar_x0 = 32
            bar_w = max(0, w - bar_x0 - 6)
            inner_fill = int(bar_w * progress)
            c.create_rectangle(bar_x0, 6, bar_x0 + bar_w, h - 6,
                               outline='#334155')
            c.create_rectangle(bar_x0, 6, bar_x0 + inner_fill, h - 6,
                               fill=primary, outline='')

        self.spinner_idx += 1
        pct = f'{progress * 100:5.1f}%'
        self.meta.configure(text=f'{pct}  {rate_text}  ETA {eta_text}')


def _blend(c1: str, c2: str, t: float) -> str:
    """Blend two hex colors. ``t`` in [0,1]."""
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f'#{r:02x}{g:02x}{b:02x}'


class ProgressBarApp(ctk.CTk):
    """Animating gallery with shared progress + per-row visual style."""

    REFRESH_MS = 33  # ~30 FPS

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Progress Bar Gallery')
        self.geometry('900x620')
        self.minsize(760, 520)
        self.configure(fg_color=BG)

        # Animation state
        self.target: float = 1.0     # goal in [0, 1]
        self.speed: float = 0.25     # progress per second
        self.progress: float = 0.0
        self._last_tick: float = time.monotonic()
        self._start: float = self._last_tick
        self._rate_ema: float = 0.0
        self._last_progress_for_rate: float = 0.0
        self._last_rate_time: float = self._last_tick

        self._build_ui()
        self.after(self.REFRESH_MS, self._tick)

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(14, 6))
        ctk.CTkLabel(header, text='PROGRESS BAR GALLERY',
                     font=HEADER_FONT, text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Five styles, one shared timeline. '
                          'Use the sliders to control speed and target.',
                     font=LABEL_FONT, text_color=MUTED).pack(anchor='w',
                                                              pady=(2, 0))

        # Bottom controls — packed first so they survive resize.
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        controls.pack(side='bottom', fill='x', padx=20, pady=(8, 14))

        # Speed slider row
        speed_row = ctk.CTkFrame(controls, fg_color='transparent')
        speed_row.pack(fill='x', padx=14, pady=(12, 4))
        ctk.CTkLabel(speed_row, text='Speed', width=70,
                     font=LABEL_FONT, text_color=FG,
                     anchor='w').pack(side='left')
        self.speed_value = ctk.CTkLabel(speed_row, text=f'{self.speed:.2f}/s',
                                        font=META_FONT, width=80,
                                        text_color=MUTED, anchor='e')
        self.speed_value.pack(side='right')
        self.speed_slider = ctk.CTkSlider(
            speed_row, from_=0.05, to=2.0,
            command=self._on_speed_change,
            progress_color=ACCENT, button_color=ACCENT,
            button_hover_color='#0ea5e9',
        )
        self.speed_slider.set(self.speed)
        self.speed_slider.pack(side='left', fill='x', expand=True, padx=10)

        # Target slider row
        target_row = ctk.CTkFrame(controls, fg_color='transparent')
        target_row.pack(fill='x', padx=14, pady=(4, 4))
        ctk.CTkLabel(target_row, text='Target', width=70,
                     font=LABEL_FONT, text_color=FG,
                     anchor='w').pack(side='left')
        self.target_value = ctk.CTkLabel(target_row,
                                         text=f'{int(self.target * 100)}%',
                                         font=META_FONT, width=80,
                                         text_color=MUTED, anchor='e')
        self.target_value.pack(side='right')
        self.target_slider = ctk.CTkSlider(
            target_row, from_=0.0, to=1.0,
            command=self._on_target_change,
            progress_color=ACCENT, button_color=ACCENT,
            button_hover_color='#0ea5e9',
        )
        self.target_slider.set(self.target)
        self.target_slider.pack(side='left', fill='x', expand=True, padx=10)

        # Restart button row
        button_row = ctk.CTkFrame(controls, fg_color='transparent')
        button_row.pack(fill='x', padx=14, pady=(6, 12))
        ctk.CTkButton(button_row, text='Restart',
                      fg_color=ACCENT, hover_color='#0ea5e9',
                      text_color='#0f172a', font=('Segoe UI', 13, 'bold'),
                      width=120, command=self._restart).pack(side='left')
        self.summary = ctk.CTkLabel(button_row, text='',
                                    font=META_FONT, text_color=MUTED,
                                    anchor='e')
        self.summary.pack(side='right')

        # Gallery frame — animating bars
        gallery = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        gallery.pack(side='top', fill='both', expand=True,
                     padx=20, pady=(4, 8))
        ctk.CTkLabel(gallery, text='Styles',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=MUTED, anchor='w').pack(fill='x',
                                                         padx=18,
                                                         pady=(12, 0))
        self.rows: list[_BarRow] = [_BarRow(gallery, s) for s in STYLES]

    # --- callbacks -----------------------------------------------------------

    def _on_speed_change(self, value: float) -> None:
        self.speed = float(value)
        self.speed_value.configure(text=f'{self.speed:.2f}/s')

    def _on_target_change(self, value: float) -> None:
        self.target = float(value)
        self.target_value.configure(text=f'{int(self.target * 100)}%')

    def _restart(self) -> None:
        self.progress = 0.0
        now = time.monotonic()
        self._start = now
        self._last_tick = now
        self._last_rate_time = now
        self._last_progress_for_rate = 0.0
        self._rate_ema = 0.0

    # --- animation loop ------------------------------------------------------

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        # Move toward target at ``speed`` per second.
        if self.progress < self.target:
            self.progress = min(self.target, self.progress + self.speed * dt)
        elif self.progress > self.target:
            # Allow target slider to drag the bar back too.
            self.progress = max(self.target, self.progress - self.speed * dt)

        # EMA rate (% per second toward target).
        rate_elapsed = now - self._last_rate_time
        if rate_elapsed >= 0.1:
            instant = (self.progress - self._last_progress_for_rate) / rate_elapsed
            if self._rate_ema == 0.0:
                self._rate_ema = instant
            else:
                self._rate_ema = 0.3 * instant + 0.7 * self._rate_ema
            self._last_rate_time = now
            self._last_progress_for_rate = self.progress

        if self._rate_ema > 1e-4 and self.progress < self.target:
            eta_seconds = (self.target - self.progress) / self._rate_ema
        else:
            eta_seconds = 0.0 if self.progress >= self.target else float('inf')

        eta_text = format_eta(eta_seconds)
        rate_text = format_rate(max(0.0, self._rate_ema) * 100)  # %/s as items

        for row in self.rows:
            row.draw(self.progress, eta_text, rate_text)

        elapsed = now - self._start
        self.summary.configure(
            text=f'{self.progress * 100:5.1f}% of {int(self.target * 100)}%  •  '
                 f'elapsed {elapsed:5.1f}s  •  rate {rate_text}'
        )

        self.after(self.REFRESH_MS, self._tick)


if __name__ == '__main__':
    ProgressBarApp().mainloop()
