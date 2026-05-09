"""Rotating Cube — Textual TUI.

Live ASCII wireframe in a terminal canvas with axis-toggle bindings.

Bindings:
    space   pause / resume
    x/y/z   toggle rotation around that axis
    s       cycle shape (cube → tetrahedron → octahedron → dodecahedron)
    r       reset angles + speeds
    f / g   FOV in / out
    a / d   scale down / up
    ctrl+q  quit

Run:
    uv run python rotating_cube/rotating_cube_tui.py
"""
from __future__ import annotations

import math
import time

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from rotating_cube import (
    SHAPES,
    edges_2d,
    make_shape,
    project,
    render,
)

SHAPE_NAMES = list(SHAPES.keys())

DEFAULTS = {
    'rx': 30.0,
    'ry': 45.0,
    'rz': 15.0,
    'fov': 70.0,
    'scale': 1.0,
    'distance': 4.0,
}

FRAME_INTERVAL = 1 / 30  # seconds — ~30 FPS


class RotatingCubeApp(App):
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

    #body {
        height: 1fr;
        padding: 0 2;
    }

    #canvas {
        width: 1fr;
        height: 1fr;
        background: #1e293b;
        color: #38bdf8;
        text-style: bold;
        padding: 1;
    }

    #side {
        width: 32;
        background: #1e293b;
        color: #cbd5e1;
        padding: 1 2;
        margin-left: 1;
    }

    #side > .heading {
        color: #f8fafc;
        text-style: bold;
        padding-bottom: 1;
    }

    #side > .row {
        color: #cbd5e1;
        height: 1;
    }

    #status {
        height: 1;
        background: #1e293b;
        color: #cbd5e1;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding('space', 'pause', 'Pause', priority=True),
        Binding('x', 'toggle_x', 'Toggle X', priority=True),
        Binding('y', 'toggle_y', 'Toggle Y', priority=True),
        Binding('z', 'toggle_z', 'Toggle Z', priority=True),
        Binding('s', 'cycle_shape', 'Shape', priority=True),
        Binding('r', 'reset', 'Reset', priority=True),
        Binding('f', 'fov_in', 'FOV-', priority=True),
        Binding('g', 'fov_out', 'FOV+', priority=True),
        Binding('a', 'scale_down', 'Scale-', priority=True),
        Binding('d', 'scale_up', 'Scale+', priority=True),
        Binding('ctrl+q', 'quit', 'Quit', priority=True),
    ]
    TITLE = 'Rotating Cube'

    def __init__(self) -> None:
        super().__init__()
        self.angles = [0.0, 0.0, 0.0]
        # Per-axis enable flags so the user can isolate one rotation at a time.
        self.axis_enabled = [True, True, True]
        self.paused = False
        self.shape_idx = 0
        self.fov = DEFAULTS['fov']
        self.scale = DEFAULTS['scale']
        self.last_tick = time.perf_counter()

    # -------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('ROTATING CUBE', id='title')
        yield Static('3D wireframe → rotation matrices → ASCII', id='subtitle')
        with Horizontal(id='body'):
            yield Static('', id='canvas')
            with Vertical(id='side'):
                yield Static('Controls', classes='heading')
                yield Static('space  pause/run', classes='row')
                yield Static('x/y/z  toggle axis', classes='row')
                yield Static('s      cycle shape', classes='row')
                yield Static('r      reset', classes='row')
                yield Static('f / g  FOV in/out', classes='row')
                yield Static('a / d  scale -/+', classes='row')
                yield Static('ctrl+q quit', classes='row')
                yield Static(' ', classes='row')
                yield Static('State', classes='heading')
                yield Static('', id='state')
        yield Static('', id='status')
        yield Footer()

    # ------------------------------------------------------------- mount
    def on_mount(self) -> None:
        # Drive animation off a Textual interval timer instead of a thread —
        # keeps everything on the event loop and respects pause cleanly.
        self.set_interval(FRAME_INTERVAL, self._tick)

    # ------------------------------------------------------------- actions
    def action_pause(self) -> None:
        self.paused = not self.paused

    def action_toggle_x(self) -> None:
        self.axis_enabled[0] = not self.axis_enabled[0]

    def action_toggle_y(self) -> None:
        self.axis_enabled[1] = not self.axis_enabled[1]

    def action_toggle_z(self) -> None:
        self.axis_enabled[2] = not self.axis_enabled[2]

    def action_cycle_shape(self) -> None:
        self.shape_idx = (self.shape_idx + 1) % len(SHAPE_NAMES)

    def action_reset(self) -> None:
        self.angles = [0.0, 0.0, 0.0]
        self.axis_enabled = [True, True, True]
        self.fov = DEFAULTS['fov']
        self.scale = DEFAULTS['scale']
        self.shape_idx = 0
        self.paused = False

    def action_fov_in(self) -> None:
        # FOV "in" = narrower lens = telephoto = smaller fov number.
        self.fov = max(20.0, self.fov - 5.0)

    def action_fov_out(self) -> None:
        self.fov = min(150.0, self.fov + 5.0)

    def action_scale_down(self) -> None:
        self.scale = max(0.3, self.scale - 0.1)

    def action_scale_up(self) -> None:
        self.scale = min(2.5, self.scale + 0.1)

    # ------------------------------------------------------------- render
    def _canvas_size(self) -> tuple[int, int]:
        canvas = self.query_one('#canvas', Static)
        # Subtract 1 cell padding on each side; the CSS pads by 1.
        w = max(canvas.size.width - 2, 20)
        h = max(canvas.size.height - 2, 10)
        return w, h

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self.last_tick
        self.last_tick = now

        rates = [
            math.radians(DEFAULTS['rx']) if self.axis_enabled[0] else 0.0,
            math.radians(DEFAULTS['ry']) if self.axis_enabled[1] else 0.0,
            math.radians(DEFAULTS['rz']) if self.axis_enabled[2] else 0.0,
        ]
        if not self.paused:
            self.angles = [a + r * dt for a, r in zip(self.angles, rates)]

        shape_name = SHAPE_NAMES[self.shape_idx]
        shape = make_shape(shape_name, self.scale).rotate(*self.angles)
        proj = project(shape, DEFAULTS['distance'], self.fov)
        edges = edges_2d(shape, proj)
        cols, rows = self._canvas_size()
        frame = render(cols, rows, edges)
        self.query_one('#canvas', Static).update(frame)

        ax = math.degrees(self.angles[0]) % 360
        ay = math.degrees(self.angles[1]) % 360
        az = math.degrees(self.angles[2]) % 360
        flags = ''.join(c if on else '·'
                         for c, on in zip('XYZ', self.axis_enabled))
        state = (
            f'shape: [b]{shape_name}[/]\n'
            f'verts: {len(shape.vertices)}\n'
            f'edges: {len(shape.edges)}\n'
            f'angles:\n'
            f'  x {ax:6.1f}°\n'
            f'  y {ay:6.1f}°\n'
            f'  z {az:6.1f}°\n'
            f'axes: {flags}\n'
            f'fov:   {self.fov:5.1f}°\n'
            f'scale: {self.scale:5.2f}\n'
            f'state: {"[b yellow]PAUSED[/]" if self.paused else "running"}'
        )
        self.query_one('#state', Static).update(state)
        self.query_one('#status', Static).update(
            f'frame {cols}×{rows} • dt {dt*1000:5.1f} ms'
            ' — press ctrl+q to quit')


if __name__ == '__main__':
    RotatingCubeApp().run()
