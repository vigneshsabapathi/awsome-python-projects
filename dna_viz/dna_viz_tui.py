"""DNA Visualization — Textual TUI.

Dark Tailwind palette terminal UI for the rotating DNA double helix.
Per-base color coding: A red, T orange, C blue, G green, U magenta.

Bindings:
  Space    pause / resume
  +        speed up
  -        slow down
  t        toggle transcription mode (DNA → mRNA)
  g        toggle genome sequence
  Ctrl+Q   quit

Run:
    uv run python dna_viz/dna_viz_tui.py
"""
from __future__ import annotations

import random

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static
from textual.reactive import reactive

from dna_viz import render_helix

# Tailwind-inspired palette
BASE_RICH: dict[str, str] = {
    'A': 'red',
    'T': 'dark_orange',
    'C': 'dodger_blue2',
    'G': 'chartreuse3',
    'U': 'medium_orchid',
    '|': 'grey93',
    '-': 'grey42',
}


class HelixView(Static):
    """The animated helix canvas."""

    DEFAULT_CSS = """
    HelixView {
        background: #1e293b;
        color: #f8fafc;
        padding: 0 1;
        height: 1fr;
    }
    """

    phase:      reactive[float] = reactive(0.0)
    g_offset:   reactive[int]   = reactive(0)

    def __init__(self) -> None:
        super().__init__('')
        self.rng = random.Random(42)

    def render_frame(self, width: int, height: int, phase: float,
                     g_offset: int, transcribe: bool,
                     genome_mode: bool) -> Text:
        raw = render_helix(
            max(20, width - 2), max(5, height),
            phase, self.rng,
            transcribe=transcribe,
            genome_mode=genome_mode,
            genome_offset=g_offset,
        )
        text = Text(no_wrap=True)
        for ch in raw:
            color = BASE_RICH.get(ch, '')
            if color and ch not in (' ', '\n'):
                text.append(ch, style=color)
            else:
                text.append(ch)
        return text


class DNATUIApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #38bdf8;
        padding: 1 0 0 0;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding: 0 0 1 0;
    }

    #legend {
        height: 1;
        align-horizontal: center;
        padding: 0 1;
    }

    .base-chip {
        padding: 0 1;
        margin: 0 1;
        height: 1;
        text-style: bold;
    }

    #status {
        text-align: center;
        color: #94a3b8;
        height: 1;
        padding: 0 1;
    }

    #controls {
        height: 1;
        align-horizontal: center;
        color: #64748b;
    }
    """

    BINDINGS = [
        Binding('space',   'toggle_pause',      'Pause/Resume'),
        Binding('+',       'speed_up',          'Speed +'),
        Binding('-',       'speed_down',         'Speed -'),
        Binding('t',       'toggle_transcribe',  'Transcribe'),
        Binding('g',       'toggle_genome',      'Genome'),
        Binding('ctrl+q',  'quit',               'Quit'),
    ]

    TITLE = 'DNA Visualization'

    def __init__(self) -> None:
        super().__init__()
        self.running    = True
        self.speed      = 0.10
        self.transcribe = False
        self.genome     = False
        self._phase     = 0.0
        self._g_offset  = 0
        self._timer     = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('DNA DOUBLE HELIX', id='title')
        yield Static(
            'Two anti-parallel strands   A↔T   C↔G', id='subtitle')
        with Horizontal(id='legend'):
            for base, style, label in [
                ('A', 'on red',          'Adenine'),
                ('T', 'on dark_orange',  'Thymine'),
                ('C', 'on dodger_blue2', 'Cytosine'),
                ('G', 'on chartreuse3',  'Guanine'),
                ('U', 'on medium_orchid','Uracil (mRNA)'),
            ]:
                yield Static(f'  {base}: {label}  ',
                             classes='base-chip',
                             markup=False)
        yield HelixView(id='helix')
        yield Static('', id='status')
        yield Footer()

    def on_mount(self) -> None:
        self._helix = self.query_one('#helix', HelixView)
        self._status = self.query_one('#status', Static)
        self._timer = self.set_interval(1 / 15, self._tick)

    def _tick(self) -> None:
        if not self.running:
            return
        w = self._helix.content_size.width  or 80
        h = self._helix.content_size.height or 25

        frame = self._helix.render_frame(
            w, h, self._phase, self._g_offset,
            self.transcribe, self.genome)
        self._helix.update(frame)

        mode = 'DNA→mRNA' if self.transcribe else 'DNA helix'
        seq  = 'genome'   if self.genome     else 'random'
        self._status.update(
            f'{mode} | {seq} | phase={self._phase:.2f} | '
            f'speed={self.speed:.2f} | {"running" if self.running else "PAUSED"}')

        self._phase    += self.speed
        self._g_offset += 1

    # ------------------------------------------------------------------
    def action_toggle_pause(self) -> None:
        self.running = not self.running
        if not self.running:
            self._status.update('PAUSED — press Space to resume')

    def action_speed_up(self) -> None:
        self.speed = min(0.5, round(self.speed + 0.02, 3))

    def action_speed_down(self) -> None:
        self.speed = max(0.01, round(self.speed - 0.02, 3))

    def action_toggle_transcribe(self) -> None:
        self.transcribe = not self.transcribe

    def action_toggle_genome(self) -> None:
        self.genome = not self.genome


if __name__ == '__main__':
    DNATUIApp().run()
