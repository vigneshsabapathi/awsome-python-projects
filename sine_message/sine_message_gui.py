"""Sine Message — CustomTkinter GUI.

Live animated viewer: type a message, drag sliders for amplitude / frequency
/ scroll speed, and watch it surf a sine wave. Optional color cycle paints
each character along a hue gradient that shifts with the phase, so the wave
looks like an iridescent ribbon.

Run:
    uv run python sine_message/sine_message_gui.py
"""
from __future__ import annotations

import colorsys

import customtkinter as ctk

from sine_message import render, render_lissajous, render_overlay

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
MONO = ('Consolas', 12)
MONO_BOLD = ('Consolas', 12, 'bold')

MODES = {
    'Sine': render,
    'Overlay (sine+cos+harmonic)': render_overlay,
    'Lissajous (2D wobble)': render_lissajous,
}


class SineMessageApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Sine Message')
        self.geometry('1100x720')
        self.minsize(900, 600)
        self.configure(fg_color=BG)

        # Animation state.
        self.phase = 0.0
        self.running = True
        self.color_cycle = False
        self._after_id: str | None = None

        self._build_ui()
        self._tick()
        self.message_entry.focus()

    # ---------- UI ----------
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='SINE MESSAGE',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Each character sits at y = round(amp · sin(freq·x '
                          '+ phase)) — phase scrolls every frame.',
                     font=('Segoe UI', 12),
                     text_color=MUTED).pack(anchor='w', pady=(2, 0))

        # Status (bottom)
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 8))

        # Message + mode row
        msg_row = ctk.CTkFrame(self, fg_color='transparent')
        msg_row.pack(side='top', padx=20, pady=(8, 4), fill='x')
        ctk.CTkLabel(msg_row, text='Message:',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG).pack(side='left')
        self.message_entry = ctk.CTkEntry(msg_row, font=('Segoe UI', 14),
                                          height=36,
                                          placeholder_text='Sine wave!')
        self.message_entry.pack(side='left', fill='x', expand=True,
                                padx=(10, 10))
        self.message_entry.insert(0, 'Sine wave scrolling forever ~ ')

        ctk.CTkLabel(msg_row, text='Mode:',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(side='left', padx=(8, 4))
        self.mode_var = ctk.StringVar(value='Sine')
        self.mode_menu = ctk.CTkOptionMenu(
            msg_row, values=list(MODES.keys()), variable=self.mode_var,
            width=220, fg_color=PANEL, button_color='#334155',
            button_hover_color='#475569')
        self.mode_menu.pack(side='left')

        # Controls row (sliders)
        ctrls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10)
        ctrls.pack(side='top', padx=20, pady=(8, 4), fill='x')
        ctrls.grid_columnconfigure((1, 3, 5), weight=1)

        self.amp_var = ctk.DoubleVar(value=8.0)
        self.freq_var = ctk.DoubleVar(value=0.2)
        self.speed_var = ctk.DoubleVar(value=0.1)

        self._slider(ctrls, 0, 'Amplitude', self.amp_var, 1.0, 16.0)
        self._slider(ctrls, 2, 'Frequency', self.freq_var, 0.05, 0.8)
        self._slider(ctrls, 4, 'Speed (Δphase/frame)',
                     self.speed_var, 0.0, 0.5)

        # Toggle row
        toggles = ctk.CTkFrame(self, fg_color='transparent')
        toggles.pack(side='top', padx=20, pady=(2, 4), fill='x')

        self.color_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(toggles, text='Color cycle (rainbow ribbon)',
                      variable=self.color_var,
                      command=self._on_color_toggle,
                      progress_color=ACCENT,
                      text_color=FG,
                      font=('Segoe UI', 12)).pack(side='left')

        self.pause_btn = ctk.CTkButton(toggles, text='Pause',
                                       fg_color='#334155',
                                       hover_color='#475569',
                                       width=90,
                                       command=self._toggle_pause)
        self.pause_btn.pack(side='right')
        ctk.CTkButton(toggles, text='Reset phase',
                      fg_color='#334155', hover_color='#475569',
                      width=110, command=self._reset_phase).pack(
            side='right', padx=(0, 8))

        # Canvas
        self.canvas = ctk.CTkTextbox(self, font=MONO_BOLD,
                                     fg_color=PANEL, text_color=ACCENT,
                                     wrap='none')
        self.canvas.pack(side='top', fill='both', expand=True,
                         padx=20, pady=(8, 4))
        self.canvas.configure(state='disabled')
        # Tags for color cycle.
        self._tag_names: list[str] = []

    def _slider(self, parent, col: int, label: str, var, lo: float,
                hi: float) -> None:
        ctk.CTkLabel(parent, text=label, font=('Segoe UI', 12, 'bold'),
                     text_color=FG).grid(row=0, column=col, sticky='w',
                                          padx=(12, 6), pady=(8, 0))
        slider = ctk.CTkSlider(parent, variable=var, from_=lo, to=hi,
                               progress_color=ACCENT,
                               button_color=ACCENT,
                               button_hover_color='#0ea5e9')
        slider.grid(row=1, column=col, columnspan=2, sticky='ew',
                    padx=(12, 6), pady=(0, 10))
        # Live numeric readout
        readout = ctk.CTkLabel(parent, text=f'{var.get():.2f}',
                               text_color=MUTED, font=('Segoe UI', 11),
                               width=50)
        readout.grid(row=0, column=col + 1, sticky='e',
                     padx=(0, 12), pady=(8, 0))
        var.trace_add('write',
                      lambda *_a, v=var, r=readout:
                      r.configure(text=f'{v.get():.2f}'))

    # ---------- callbacks ----------
    def _toggle_pause(self) -> None:
        self.running = not self.running
        self.pause_btn.configure(text='Resume' if not self.running
                                 else 'Pause')

    def _reset_phase(self) -> None:
        self.phase = 0.0

    def _on_color_toggle(self) -> None:
        self.color_cycle = bool(self.color_var.get())

    # ---------- animation tick ----------
    def _tick(self) -> None:
        try:
            message = self.message_entry.get() or 'Sine wave!'
            amp = float(self.amp_var.get())
            freq = float(self.freq_var.get())
            speed = float(self.speed_var.get())
            mode_name = self.mode_var.get()
            renderer = MODES.get(mode_name, render)

            width = self._estimate_width()
            frame = renderer(message, width=width, amplitude=amp,
                             frequency=freq, phase=self.phase)
            self._draw(frame)
            self.status.configure(
                text=(f'{mode_name}  •  width {width}  •  amp {amp:.1f}  •  '
                      f'freq {freq:.2f}  •  phase {self.phase:.2f}  •  '
                      f'{"running" if self.running else "paused"}'))

            if self.running:
                self.phase += speed
        except Exception as exc:  # pragma: no cover — keep loop alive
            self.status.configure(text=f'render error: {exc}')

        self._after_id = self.after(50, self._tick)  # ~20 fps

    def _estimate_width(self) -> int:
        # Approx character cells based on canvas pixel width / mono cell width.
        try:
            px = self.canvas.winfo_width()
        except Exception:
            px = 0
        if px <= 1:
            return 80
        # Consolas 12pt is roughly 8px wide; clamp into a sensible band.
        return max(40, min(220, px // 8))

    def _draw(self, frame: str) -> None:
        self.canvas.configure(state='normal')
        # Clear previously created hue tags.
        for tag in self._tag_names:
            try:
                self.canvas.tag_delete(tag)
            except Exception:
                pass
        self._tag_names.clear()

        self.canvas.delete('1.0', 'end')

        if not self.color_cycle:
            self.canvas.insert('1.0', frame)
        else:
            # Per-character colors using the column hue + phase rotation.
            lines = frame.split('\n')
            width = max((len(ln) for ln in lines), default=1)
            for row_idx, line in enumerate(lines):
                if row_idx:
                    self.canvas.insert('end', '\n')
                for col_idx, ch in enumerate(line):
                    if ch == ' ':
                        self.canvas.insert('end', ' ')
                        continue
                    hue = ((col_idx / max(1, width)) + self.phase * 0.05) % 1.0
                    r, g, b = colorsys.hsv_to_rgb(hue, 0.85, 1.0)
                    color = f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'
                    tag = f'h{row_idx}_{col_idx}'
                    self._tag_names.append(tag)
                    start = self.canvas.index('end-1c')
                    self.canvas.insert('end', ch)
                    end = self.canvas.index('end-1c')
                    self.canvas.tag_add(tag, start, end)
                    self.canvas.tag_config(tag, foreground=color)

        self.canvas.configure(state='disabled')

    def destroy(self) -> None:  # pragma: no cover
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        super().destroy()


if __name__ == '__main__':
    SineMessageApp().mainloop()
