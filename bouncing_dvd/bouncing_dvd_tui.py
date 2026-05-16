"""Bouncing DVD Logo — Textual TUI.

Dark Tailwind palette. Each logo is rendered as a colored block of
half-block characters (▀). Stats panel shows bounces, corners, and FPS.

Bindings
--------
- space    play/pause
- +        speed up
- -        slow down
- n        add a new logo
- ctrl+q   quit

Run:
    uv run python bouncing_dvd/bouncing_dvd_tui.py
"""
from __future__ import annotations

import random
import time

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static

from bouncing_dvd import COLORS, Logo, random_logo

# ── palette ────────────────────────────────────────────────────────────────
BG    = '#0f172a'
PANEL = '#1e293b'
TEXT  = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
DEAD  = '#0f172a'

# Map color names to hex
_HEX: dict[str, str] = {
    'red':     '#ef4444',
    'orange':  '#f97316',
    'yellow':  '#facc15',
    'green':   '#22c55e',
    'cyan':    '#06b6d4',
    'blue':    '#3b82f6',
    'magenta': '#d946ef',
    'white':   '#f8fafc',
}

# Field dimensions in "cells" (terminal columns / half-block rows).
# Each terminal row renders 2 vertical cells via ▀ trick.
FIELD_W = 80   # columns
FIELD_H = 40   # logical rows (20 terminal lines)

# Logo dimensions in cells (approx "DVD" text width × 2 high)
LOGO_W = 5
LOGO_H = 2

FPS_MIN  = 2
FPS_MAX  = 30
FPS_STEP = 2


class DVDView(Static):
    """Renders the play field with half-block characters."""

    def render_field(self, logos: list[Logo], field_w: int, field_h: int) -> Text:
        # Build a color grid: None = dead, else hex color string
        grid: list[list[str | None]] = [
            [None] * field_w for _ in range(field_h)
        ]
        for lg in logos:
            hex_color = _HEX[lg.color]
            for dy in range(LOGO_H):
                for dx in range(LOGO_W):
                    px, py = lg.x + dx, lg.y + dy
                    if 0 <= px < field_w and 0 <= py < field_h:
                        grid[py][px] = hex_color

        text = Text(no_wrap=True, overflow='ellipsis')
        for r in range(0, field_h, 2):
            top = grid[r]
            bot = grid[r + 1] if r + 1 < field_h else [None] * field_w
            for c in range(field_w):
                fg = top[c] or DEAD
                bg = bot[c] or DEAD
                text.append('▀', style=f'{fg} on {bg}')
            if r + 2 < field_h:
                text.append('\n')
        return text


class BouncingDVDApp(App):
    CSS = f"""
    Screen {{
        background: {BG};
        color: {TEXT};
        align: center top;
    }}

    #title {{
        text-align: center;
        text-style: bold;
        color: {TEXT};
        padding-top: 1;
    }}

    #subtitle {{
        text-align: center;
        color: {MUTED};
        padding-bottom: 1;
    }}

    #field_panel {{
        align: center middle;
        background: {PANEL};
        border: tall #334155;
        padding: 0 1;
        margin: 1 2;
    }}

    #dvd_view {{
        width: auto;
        height: auto;
        background: {DEAD};
    }}

    #stats {{
        text-align: center;
        color: {MUTED};
        padding: 0 2;
    }}
    """

    BINDINGS = [
        Binding('space',  'toggle_play', 'Play/Pause'),
        Binding('+',      'speed_up',    'Faster'),
        Binding('-',      'slow_down',   'Slower'),
        Binding('n',      'add_logo',    'New Logo'),
        Binding('ctrl+q', 'quit',        'Quit'),
    ]

    TITLE = 'Bouncing DVD Logo'

    def __init__(self) -> None:
        super().__init__()
        self._field_w = FIELD_W
        self._field_h = FIELD_H
        self._logos: list[Logo] = []
        self._running = True
        self._fps = 15
        self._last_tick = time.perf_counter()
        self._fps_display = 0.0
        self._timer = None
        self._rng = random.Random()
        # Spawn initial logo
        self._logos.append(
            random_logo(self._field_w, self._field_h, LOGO_W, LOGO_H, self._rng))

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('BOUNCING DVD LOGO', id='title')
        yield Static(
            'space play/pause  •  +/- speed  •  n new logo  •  ctrl+q quit',
            id='subtitle')
        with Vertical(id='field_panel'):
            yield DVDView(id='dvd_view')
        yield Static('', id='stats')
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        self._timer = self.set_interval(1.0 / self._fps, self._tick)

    # ── Rendering ────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        view = self.query_one('#dvd_view', DVDView)
        view.update(view.render_field(self._logos, self._field_w, self._field_h))
        self._update_stats()

    def _update_stats(self) -> None:
        bounces = sum(lg.bounces for lg in self._logos)
        corners = sum(lg.corners for lg in self._logos)
        state = 'PLAYING' if self._running else 'PAUSED '
        stats = (
            f'[{ACCENT}]{state}[/]   '
            f'logos [{TEXT}]{len(self._logos)}[/]   '
            f'bounces [{TEXT}]{bounces:>5d}[/]   '
            f'corners [{TEXT}]{corners:>3d}[/]   '
            f'fps [{TEXT}]{self._fps_display:>4.1f}[/]   '
            f'target [{TEXT}]{self._fps}[/]'
        )
        self.query_one('#stats', Static).update(stats)

    # ── Tick loop ─────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self._last_tick
        self._fps_display = 1.0 / dt if dt > 0 else 0.0
        self._last_tick = now

        if not self._running:
            self._update_stats()
            return

        for lg in self._logos:
            lg.step(self._field_w, self._field_h, LOGO_W, LOGO_H)
        self._refresh()

    def _reset_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
        self._timer = self.set_interval(1.0 / self._fps, self._tick)

    # ── Actions ───────────────────────────────────────────────────────────────

    def action_toggle_play(self) -> None:
        self._running = not self._running
        self._update_stats()

    def action_speed_up(self) -> None:
        self._fps = min(self._fps + FPS_STEP, FPS_MAX)
        self._reset_timer()
        self._update_stats()

    def action_slow_down(self) -> None:
        self._fps = max(self._fps - FPS_STEP, FPS_MIN)
        self._reset_timer()
        self._update_stats()

    def action_add_logo(self) -> None:
        self._logos.append(
            random_logo(self._field_w, self._field_h, LOGO_W, LOGO_H, self._rng))
        self._refresh()


if __name__ == '__main__':
    BouncingDVDApp().run()
