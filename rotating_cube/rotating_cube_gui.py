"""Rotating Cube — CustomTkinter GUI.

Live ASCII wireframe in a big monospace label, with sliders for
spin rate (X / Y / Z), FOV, scale, and shape selection.

Run:
    uv run python rotating_cube/rotating_cube_gui.py
"""
from __future__ import annotations

import math
import time

import customtkinter as ctk

from rotating_cube import (
    SHAPES,
    edges_2d,
    make_shape,
    project,
    render,
)

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
ACCENT_DARK = '#0ea5e9'
MONO = ('Consolas', 11)
MONO_BOLD = ('Consolas', 11, 'bold')
LABEL = ('Segoe UI', 12)
LABEL_BOLD = ('Segoe UI', 12, 'bold')

DEFAULTS = {
    'rx': 30.0,
    'ry': 45.0,
    'rz': 15.0,
    'fov': 70.0,
    'scale': 1.0,
    'distance': 4.0,
}

FRAME_MS = 33  # ~30 FPS


class RotatingCubeApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Rotating Cube')
        self.geometry('960x720')
        self.minsize(820, 600)
        self.configure(fg_color=BG)

        # Animation state
        self.angles = [0.0, 0.0, 0.0]
        self.paused = False
        self.shape_name = 'cube'
        self.last_tick = time.perf_counter()
        # Used to lock out slider callbacks while we programmatically
        # reset values (otherwise they'd ping-pong).
        self._suppress = False

        self._build_ui()
        self._tick()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', padx=20, pady=(14, 4), fill='x')
        ctk.CTkLabel(header, text='ROTATING CUBE',
                     font=('Segoe UI', 22, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='3D wireframe → rotation matrices → perspective '
                          'projection → ASCII raster.',
                     font=('Segoe UI', 11),
                     text_color=MUTED).pack(anchor='w', pady=(2, 0))

        # Status (bottom)
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(4, 8))

        # Controls (right)
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        controls.pack(side='right', fill='y', padx=(8, 16), pady=(8, 4))

        ctk.CTkLabel(controls, text='Controls', font=LABEL_BOLD,
                     text_color=FG).pack(pady=(12, 4), padx=14)

        ctk.CTkLabel(controls, text='Shape', font=LABEL,
                     text_color=MUTED).pack(pady=(8, 2), padx=14, anchor='w')
        self.shape_var = ctk.StringVar(value=self.shape_name)
        ctk.CTkOptionMenu(controls, values=list(SHAPES.keys()),
                          variable=self.shape_var,
                          command=self._on_shape_change,
                          fg_color='#334155', button_color='#475569',
                          button_hover_color='#64748b').pack(padx=14,
                                                               fill='x')

        self.rx_slider = self._make_slider(controls, 'X spin (°/s)',
                                           -180, 180, DEFAULTS['rx'])
        self.ry_slider = self._make_slider(controls, 'Y spin (°/s)',
                                           -180, 180, DEFAULTS['ry'])
        self.rz_slider = self._make_slider(controls, 'Z spin (°/s)',
                                           -180, 180, DEFAULTS['rz'])
        self.fov_slider = self._make_slider(controls, 'FOV (°)',
                                            20, 150, DEFAULTS['fov'])
        self.scale_slider = self._make_slider(controls, 'Scale',
                                              0.3, 2.5, DEFAULTS['scale'])

        btns = ctk.CTkFrame(controls, fg_color='transparent')
        btns.pack(padx=14, pady=(12, 14), fill='x')
        self.pause_btn = ctk.CTkButton(btns, text='Pause',
                                       fg_color=ACCENT,
                                       hover_color=ACCENT_DARK,
                                       text_color='#0f172a',
                                       font=LABEL_BOLD,
                                       command=self._toggle_pause)
        self.pause_btn.pack(fill='x', pady=(0, 6))
        ctk.CTkButton(btns, text='Reset',
                      fg_color='#334155', hover_color='#475569',
                      command=self._reset).pack(fill='x')

        # Canvas (center fill)
        self.canvas = ctk.CTkLabel(self, text='', font=MONO_BOLD,
                                   fg_color=PANEL, text_color=ACCENT,
                                   corner_radius=8, anchor='nw',
                                   justify='left')
        self.canvas.pack(side='left', fill='both', expand=True,
                         padx=(16, 0), pady=(8, 4))
        # Cell size measurement happens on the first tick — Tk reports
        # 1x1 until the widget is mapped.
        self.canvas.bind('<Configure>', lambda _e: None)

    def _make_slider(self, parent, label: str, low: float, high: float,
                     default: float) -> ctk.CTkSlider:
        ctk.CTkLabel(parent, text=label, font=LABEL,
                     text_color=MUTED).pack(pady=(8, 2), padx=14, anchor='w')
        var = ctk.DoubleVar(value=default)
        slider = ctk.CTkSlider(parent, from_=low, to=high, variable=var,
                               progress_color=ACCENT,
                               button_color=ACCENT,
                               button_hover_color=ACCENT_DARK,
                               command=lambda v, lbl=label: self._update_slider_label(lbl, v))
        slider.pack(padx=14, fill='x')
        value_lbl = ctk.CTkLabel(parent, text=f'{default:.1f}',
                                  font=('Consolas', 11), text_color=FG)
        value_lbl.pack(padx=14, anchor='e', pady=(0, 4))
        slider.value_label = value_lbl  # type: ignore[attr-defined]
        slider.value_var = var  # type: ignore[attr-defined]
        return slider

    def _update_slider_label(self, _label: str, _value: float) -> None:
        if self._suppress:
            return
        for s in (self.rx_slider, self.ry_slider, self.rz_slider,
                   self.fov_slider, self.scale_slider):
            v = s.value_var.get()  # type: ignore[attr-defined]
            s.value_label.configure(text=f'{v:.1f}')  # type: ignore[attr-defined]

    # ------------------------------------------------------------ events
    def _on_shape_change(self, name: str) -> None:
        self.shape_name = name

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.configure(text='Resume' if self.paused else 'Pause')

    def _reset(self) -> None:
        self._suppress = True
        try:
            self.angles = [0.0, 0.0, 0.0]
            self.rx_slider.value_var.set(DEFAULTS['rx'])  # type: ignore[attr-defined]
            self.ry_slider.value_var.set(DEFAULTS['ry'])  # type: ignore[attr-defined]
            self.rz_slider.value_var.set(DEFAULTS['rz'])  # type: ignore[attr-defined]
            self.fov_slider.value_var.set(DEFAULTS['fov'])  # type: ignore[attr-defined]
            self.scale_slider.value_var.set(DEFAULTS['scale'])  # type: ignore[attr-defined]
        finally:
            self._suppress = False
        self._update_slider_label('reset', 0.0)

    # ----------------------------------------------------------- render
    def _canvas_chars(self) -> tuple[int, int]:
        """Translate the canvas's pixel size into character cells.

        Consolas at 11pt is roughly 7 px wide and 14 px tall; we measure
        once per tick to tolerate window resizes.
        """
        w_px = max(self.canvas.winfo_width(), 200)
        h_px = max(self.canvas.winfo_height(), 200)
        char_w, char_h = 7, 14
        return max(20, w_px // char_w), max(10, h_px // char_h)

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = now - self.last_tick
        self.last_tick = now

        if not self.paused:
            rx = math.radians(self.rx_slider.value_var.get())  # type: ignore[attr-defined]
            ry = math.radians(self.ry_slider.value_var.get())  # type: ignore[attr-defined]
            rz = math.radians(self.rz_slider.value_var.get())  # type: ignore[attr-defined]
            self.angles[0] += rx * dt
            self.angles[1] += ry * dt
            self.angles[2] += rz * dt

        scale = float(self.scale_slider.value_var.get())  # type: ignore[attr-defined]
        fov = float(self.fov_slider.value_var.get())  # type: ignore[attr-defined]
        shape = make_shape(self.shape_name, scale).rotate(*self.angles)
        proj = project(shape, DEFAULTS['distance'], fov)
        edges = edges_2d(shape, proj)
        cols, rows = self._canvas_chars()
        frame = render(cols, rows, edges)
        self.canvas.configure(text=frame)

        verts = len(shape.vertices)
        edge_n = len(shape.edges)
        ax = math.degrees(self.angles[0]) % 360
        ay = math.degrees(self.angles[1]) % 360
        az = math.degrees(self.angles[2]) % 360
        self.status.configure(
            text=(f'shape {self.shape_name} • {verts} verts • {edge_n} edges'
                  f'   |   angles ({ax:6.1f}°, {ay:6.1f}°, {az:6.1f}°)'
                  f'   |   {"PAUSED" if self.paused else "running"}'
                  f' • frame {cols}×{rows}'))

        self.after(FRAME_MS, self._tick)


if __name__ == '__main__':
    RotatingCubeApp().mainloop()
