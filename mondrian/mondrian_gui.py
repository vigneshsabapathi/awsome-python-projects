"""Mondrian Art Generator — CustomTkinter GUI.

A dark-themed desktop UI that generates Piet-Mondrian-style paintings on a
``tk.Canvas``. Tweak depth and canvas size with sliders, set a seed for
reproducibility, switch style presets, and save the result as a PNG via Pillow.

Run:
    uv run python mondrian/mondrian_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk
from datetime import datetime

import customtkinter as ctk

from mondrian import PALETTES, Rect, generate, render_image

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
BORDER_COLOR = '#0f0f0f'
BORDER_WIDTH = 5  # canvas line thickness (pixels)

DEFAULT_WIDTH = 720
DEFAULT_HEIGHT = 540
DEFAULT_DEPTH = 5
DEFAULT_STYLE = 'mondrian'


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return '#{:02x}{:02x}{:02x}'.format(*rgb)


class MondrianApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Mondrian Art Generator')
        self.geometry('1080x720')
        self.minsize(900, 600)
        self.configure(fg_color=BG)

        self.rects: list[Rect] = []
        self.current_seed: int = 0
        self.canvas_w: int = DEFAULT_WIDTH
        self.canvas_h: int = DEFAULT_HEIGHT
        self.depth: int = DEFAULT_DEPTH
        self.style: str = DEFAULT_STYLE

        self._build_ui()
        self._regenerate(reuse_seed=False)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='MONDRIAN ART GENERATOR',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Recursive subdivision into colored rectangles. '
                          'Adjust depth and canvas size, then Generate.',
                     font=('Segoe UI', 12),
                     text_color=MUTED).pack(anchor='w', pady=(2, 0))

        # Bottom status bar (packed first so it's always visible)
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 8))

        # Main split: controls (left) | canvas (right)
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(8, 4))
        body.grid_columnconfigure(0, weight=0, minsize=260)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        controls = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=10)
        controls.grid(row=0, column=0, sticky='nsw', padx=(0, 12))

        # Style picker
        ctk.CTkLabel(controls, text='Style preset',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(anchor='w', padx=14, pady=(14, 2))
        self.style_var = ctk.StringVar(value=self.style)
        self.style_menu = ctk.CTkOptionMenu(
            controls, values=sorted(PALETTES.keys()),
            variable=self.style_var,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b',
            command=self._on_style_change)
        self.style_menu.pack(fill='x', padx=14, pady=(0, 10))

        # Depth slider
        self.depth_label = ctk.CTkLabel(
            controls, text=f'Depth: {self.depth}',
            font=('Segoe UI', 12, 'bold'), text_color=FG)
        self.depth_label.pack(anchor='w', padx=14, pady=(6, 2))
        self.depth_slider = ctk.CTkSlider(
            controls, from_=2, to=8, number_of_steps=6,
            command=self._on_depth_change)
        self.depth_slider.set(self.depth)
        self.depth_slider.pack(fill='x', padx=14, pady=(0, 8))

        # Width slider
        self.width_label = ctk.CTkLabel(
            controls, text=f'Width: {self.canvas_w}px',
            font=('Segoe UI', 12, 'bold'), text_color=FG)
        self.width_label.pack(anchor='w', padx=14, pady=(6, 2))
        self.width_slider = ctk.CTkSlider(
            controls, from_=320, to=1280, number_of_steps=24,
            command=self._on_width_change)
        self.width_slider.set(self.canvas_w)
        self.width_slider.pack(fill='x', padx=14, pady=(0, 8))

        # Height slider
        self.height_label = ctk.CTkLabel(
            controls, text=f'Height: {self.canvas_h}px',
            font=('Segoe UI', 12, 'bold'), text_color=FG)
        self.height_label.pack(anchor='w', padx=14, pady=(6, 2))
        self.height_slider = ctk.CTkSlider(
            controls, from_=240, to=960, number_of_steps=24,
            command=self._on_height_change)
        self.height_slider.set(self.canvas_h)
        self.height_slider.pack(fill='x', padx=14, pady=(0, 12))

        # Seed entry
        ctk.CTkLabel(controls, text='Seed',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(anchor='w', padx=14, pady=(4, 2))
        self.seed_entry = ctk.CTkEntry(controls, placeholder_text='random')
        self.seed_entry.pack(fill='x', padx=14, pady=(0, 12))
        self.seed_entry.bind('<Return>',
                             lambda _e: self._regenerate(reuse_seed=False))

        # Buttons
        ctk.CTkButton(controls, text='Generate',
                      fg_color=ACCENT, hover_color='#0ea5e9',
                      text_color='#0f172a',
                      font=('Segoe UI', 13, 'bold'),
                      command=lambda: self._regenerate(reuse_seed=False)
                      ).pack(fill='x', padx=14, pady=(4, 6))
        ctk.CTkButton(controls, text='Re-render (same seed)',
                      fg_color='#334155', hover_color='#475569',
                      command=lambda: self._regenerate(reuse_seed=True)
                      ).pack(fill='x', padx=14, pady=(0, 6))
        ctk.CTkButton(controls, text='Save PNG…',
                      fg_color='#334155', hover_color='#475569',
                      command=self._save_png
                      ).pack(fill='x', padx=14, pady=(0, 14))

        # Canvas pane
        canvas_frame = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=10)
        canvas_frame.grid(row=0, column=1, sticky='nsew')
        canvas_frame.grid_rowconfigure(0, weight=1)
        canvas_frame.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_frame, bg=BORDER_COLOR,
                                highlightthickness=0,
                                width=self.canvas_w, height=self.canvas_h)
        self.canvas.grid(row=0, column=0, padx=12, pady=12)

    # ----------------------------------------------------------- handlers
    def _on_style_change(self, _name: str) -> None:
        self.style = self.style_var.get()
        self._regenerate(reuse_seed=True)

    def _on_depth_change(self, value: float) -> None:
        self.depth = int(round(value))
        self.depth_label.configure(text=f'Depth: {self.depth}')

    def _on_width_change(self, value: float) -> None:
        self.canvas_w = int(round(value))
        self.width_label.configure(text=f'Width: {self.canvas_w}px')
        self.canvas.configure(width=self.canvas_w)

    def _on_height_change(self, value: float) -> None:
        self.canvas_h = int(round(value))
        self.height_label.configure(text=f'Height: {self.canvas_h}px')
        self.canvas.configure(height=self.canvas_h)

    # ----------------------------------------------------------- actions
    def _regenerate(self, *, reuse_seed: bool) -> None:
        seed_text = self.seed_entry.get().strip()
        if reuse_seed and not seed_text:
            seed = self.current_seed
        elif seed_text:
            try:
                seed = int(seed_text)
            except ValueError:
                self._set_status(f'Seed must be an integer; got {seed_text!r}',
                                 '#f87171')
                return
        else:
            seed = random.randrange(2 ** 31)
            self.seed_entry.delete(0, 'end')
            self.seed_entry.insert(0, str(seed))
        self.current_seed = seed
        rng = random.Random(seed)
        self.rects = generate(self.canvas_w, self.canvas_h, rng,
                              depth=self.depth, style=self.style)
        self._draw()
        self._set_status(
            f'{len(self.rects)} rectangles • style {self.style} • '
            f'depth {self.depth} • {self.canvas_w}×{self.canvas_h} • '
            f'seed {self.current_seed}', MUTED)

    def _draw(self) -> None:
        self.canvas.configure(width=self.canvas_w, height=self.canvas_h)
        self.canvas.delete('all')
        for r in self.rects:
            self.canvas.create_rectangle(
                r.x, r.y, r.x + r.w, r.y + r.h,
                fill=_rgb_to_hex(r.color),
                outline=BORDER_COLOR,
                width=BORDER_WIDTH,
            )
        # Outer frame to ensure top/left edges are framed too.
        self.canvas.create_rectangle(
            0, 0, self.canvas_w - 1, self.canvas_h - 1,
            outline=BORDER_COLOR, width=BORDER_WIDTH * 2,
        )

    def _save_png(self) -> None:
        if not self.rects:
            self._set_status('Nothing to save — generate first.', '#f87171')
            return
        try:
            from tkinter import filedialog
            default = (f'mondrian-{self.style}-seed{self.current_seed}-'
                       f'{datetime.now().strftime("%Y%m%d-%H%M%S")}.png')
            path = filedialog.asksaveasfilename(
                defaultextension='.png',
                filetypes=[('PNG image', '*.png')],
                initialfile=default,
                title='Save Mondrian PNG')
            if not path:
                return
            img = render_image(self.rects, self.canvas_w, self.canvas_h)
            img.save(path)
            self._set_status(f'Saved -> {path}', '#34d399')
        except Exception as exc:  # noqa: BLE001 — surface error to user
            self._set_status(f'Save failed: {exc}', '#f87171')

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, text_color=color)


if __name__ == '__main__':
    MondrianApp().mainloop()
