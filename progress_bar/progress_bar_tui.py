"""Progress Bar — Textual TUI gallery.

Scrollable list of every bar style animating in unison. Bindings:
    space   pause / resume
    r       restart from 0%
    ctrl+q  quit

Run:
    uv run python progress_bar/progress_bar_tui.py
"""
from __future__ import annotations

import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, Static

from progress_bar import (
    STYLES,
    bar,
    format_eta,
    format_rate,
    spinner_frame,
)

# Tailwind-ish dark palette
BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'

# Per-style accent colors for the rendered bar text.
STYLE_ACCENT: dict[str, str] = {
    'blocks':   '#22d3ee',
    'simple':   '#cbd5e1',
    'dots':     '#f472b6',
    'gradient': '#a78bfa',
    'spinner':  '#34d399',
}

# Multi-stop palette mapped onto the ``gradient`` row.
GRADIENT_STOPS = ('#a78bfa', '#60a5fa', '#22d3ee',
                  '#34d399', '#facc15', '#fb7185')


class _BarRow(Static):
    """One styled row in the gallery — name, bar body, and meta line."""

    DEFAULT_CSS = """
    _BarRow {
        height: 3;
        padding: 0 2;
        margin: 0 1;
        background: #1e293b;
    }
    """

    def __init__(self, style: str) -> None:
        super().__init__('', id=f'row-{style}')
        self.style_name = style
        self.tick = 0

    def render_row(self, progress: float, paused: bool,
                   eta_text: str, rate_text: str, width: int) -> None:
        """Re-render this row's text with the current progress."""
        self.tick += 1
        body_width = max(20, width - 4)
        body = self._render_body(progress, body_width)
        accent = STYLE_ACCENT[self.style_name]
        pct = f'{progress * 100:5.1f}%'
        flag = '[yellow]paused[/]' if paused else ''
        markup = (
            f'[bold {FG}]{self.style_name.upper():9}[/]  '
            f'[{accent}]{body}[/]\n'
            f'[{MUTED}]{pct}  •  {rate_text}  •  ETA {eta_text}  {flag}[/]'
        )
        self.update(markup)

    def _render_body(self, progress: float, width: int) -> str:
        """Pick a renderer per style. ``gradient`` uses inline Rich markup."""
        if self.style_name == 'gradient':
            return _gradient_markup(progress, width)
        if self.style_name == 'spinner':
            # Reuse the spinner from the library + a short body bar.
            glyph = spinner_frame(self.tick)
            inner = bar(progress, max(1, width - 2), 'blocks')
            return f'{glyph} {inner}'
        return bar(progress, width, self.style_name)


def _gradient_markup(progress: float, width: int) -> str:
    """Produce a multi-stop gradient bar as Rich markup. Visible width = ``width``."""
    progress = max(0.0, min(1.0, progress))
    filled = int(round(progress * width))
    parts: list[str] = []
    for i in range(filled):
        t = i / max(1, width - 1)
        seg = t * (len(GRADIENT_STOPS) - 1)
        lo = int(seg)
        hi = min(lo + 1, len(GRADIENT_STOPS) - 1)
        color = _blend_hex(GRADIENT_STOPS[lo], GRADIENT_STOPS[hi], seg - lo)
        parts.append(f'[{color}]█[/]')
    parts.append(' ' * (width - filled))
    return ''.join(parts)


def _blend_hex(c1: str, c2: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    return f'#{r:02x}{g:02x}{b:02x}'


class ProgressBarTUI(App):
    """Textual app — scrollable gallery, shared timeline, key bindings."""

    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #gallery {
        height: 1fr;
        padding: 1 2;
    }

    #status {
        height: 1;
        padding: 0 2;
        background: #1e293b;
        color: #cbd5e1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding('space', 'toggle_pause', 'Pause/Resume', priority=True),
        Binding('r', 'restart', 'Restart', priority=True),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]

    TITLE = 'Progress Bar Gallery'

    REFRESH_INTERVAL = 1 / 30  # 30 FPS

    def __init__(self) -> None:
        super().__init__()
        self.progress: float = 0.0
        self.speed: float = 0.20      # progress per second
        self.paused: bool = False
        self._start = time.monotonic()
        self._last_tick = self._start
        self._last_progress = 0.0
        self._last_rate_time = self._start
        self._rate_ema = 0.0
        self.rows: list[_BarRow] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('PROGRESS BAR GALLERY', id='title')
        yield Static('Five styles — one shared timeline.  '
                     '[bold]space[/] pauses, [bold]r[/] restarts, '
                     '[bold]ctrl+q[/] quits.',
                     id='subtitle')
        with VerticalScroll(id='gallery'):
            with Vertical():
                self.rows = [_BarRow(s) for s in STYLES]
                for row in self.rows:
                    yield row
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(self.REFRESH_INTERVAL, self._tick)

    # --- actions -------------------------------------------------------------

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused

    def action_restart(self) -> None:
        self.progress = 0.0
        now = time.monotonic()
        self._start = now
        self._last_tick = now
        self._last_rate_time = now
        self._last_progress = 0.0
        self._rate_ema = 0.0

    # --- animation loop ------------------------------------------------------

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_tick
        self._last_tick = now

        if not self.paused and self.progress < 1.0:
            self.progress = min(1.0, self.progress + self.speed * dt)

        # EMA rate, percent/second.
        rate_elapsed = now - self._last_rate_time
        if rate_elapsed >= 0.1:
            instant = (self.progress - self._last_progress) / rate_elapsed * 100
            if self._rate_ema == 0.0:
                self._rate_ema = instant
            else:
                self._rate_ema = 0.3 * instant + 0.7 * self._rate_ema
            self._last_rate_time = now
            self._last_progress = self.progress

        if self._rate_ema > 0.05 and self.progress < 1.0:
            eta_seconds = (1.0 - self.progress) / (self._rate_ema / 100)
        else:
            eta_seconds = 0.0 if self.progress >= 1.0 else float('inf')

        eta_text = format_eta(eta_seconds)
        rate_text = format_rate(max(0.0, self._rate_ema))

        # Use the screen width for nice scaling.
        width = max(30, self.size.width - 30)
        for row in self.rows:
            row.render_row(self.progress, self.paused, eta_text, rate_text, width)

        elapsed = now - self._start
        status = self.query_one('#status', Static)
        state = '[yellow]PAUSED[/]' if self.paused else '[green]RUNNING[/]'
        status.update(
            f'{state}  •  {self.progress * 100:5.1f}%  •  '
            f'elapsed {elapsed:5.1f}s  •  rate {rate_text}  •  ETA {eta_text}'
        )


if __name__ == '__main__':
    ProgressBarTUI().run()
