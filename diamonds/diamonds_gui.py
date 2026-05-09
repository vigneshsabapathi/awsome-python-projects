"""Diamonds — CustomTkinter GUI.

Dark theme, size slider (1..30), Outlined/Filled toggle, monospace preview,
Copy button. Updates live as you drag the slider. Has a "Grow" toggle that
animates the diamond from size 1 up to the slider value at 4 fps.

Run:
    uv run python diamonds/diamonds_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from diamonds import filled, outlined

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
GROW = '#a78bfa'
MONO = ('Consolas', 12)
MONO_BOLD = ('Consolas', 12, 'bold')

MIN_SIZE = 1
MAX_SIZE = 30
ANIMATION_FPS = 4
ANIMATION_INTERVAL_MS = int(1000 / ANIMATION_FPS)


class DiamondsApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Diamonds')
        self.geometry('820x680')
        self.minsize(700, 560)
        self.configure(fg_color=BG)

        self._size = 6
        self._style = 'outlined'      # 'outlined' or 'filled'
        self._animating = False
        self._anim_step = 1
        self._anim_after_id: str | None = None

        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='DIAMONDS',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='ASCII-art diamonds — drag the slider, flip the '
                          'style, or watch one grow.',
                     font=('Segoe UI', 12),
                     text_color=MUTED).pack(anchor='w', pady=(2, 0))

        # Status bar at the bottom
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 8))

        # Action row
        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(side='bottom', padx=20, pady=(0, 4), fill='x')

        ctk.CTkLabel(actions, text='Style:',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(side='left')
        self.style_var = ctk.StringVar(value='Outlined')
        self.style_menu = ctk.CTkSegmentedButton(
            actions, values=['Outlined', 'Filled'],
            variable=self.style_var,
            selected_color=ACCENT, selected_hover_color='#0ea5e9',
            unselected_color=PANEL, unselected_hover_color='#334155',
            command=self._on_style_change,
        )
        self.style_menu.pack(side='left', padx=(8, 16))

        self.grow_btn = ctk.CTkButton(
            actions, text='Grow ▶',
            fg_color=GROW, hover_color='#8b5cf6',
            text_color='#0f172a', font=('Segoe UI', 12, 'bold'),
            width=110, command=self._toggle_grow)
        self.grow_btn.pack(side='left')

        ctk.CTkButton(actions, text='Copy',
                      fg_color=ACCENT, hover_color='#0ea5e9',
                      text_color='#0f172a', font=('Segoe UI', 12, 'bold'),
                      width=110, command=self._copy_preview).pack(side='right')

        # Slider row
        slider_row = ctk.CTkFrame(self, fg_color='transparent')
        slider_row.pack(side='top', padx=20, pady=(8, 4), fill='x')
        ctk.CTkLabel(slider_row, text='Size:',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG).pack(side='left')
        self.size_label = ctk.CTkLabel(slider_row, text=str(self._size),
                                       font=('Consolas', 14, 'bold'),
                                       text_color=ACCENT, width=32)
        self.size_label.pack(side='left', padx=(8, 8))
        self.size_slider = ctk.CTkSlider(
            slider_row, from_=MIN_SIZE, to=MAX_SIZE,
            number_of_steps=MAX_SIZE - MIN_SIZE,
            command=self._on_slider_change,
            progress_color=ACCENT, button_color=ACCENT,
            button_hover_color='#0ea5e9')
        self.size_slider.set(self._size)
        self.size_slider.pack(side='left', fill='x', expand=True,
                              padx=(4, 0))

        # Preview pane
        preview_wrap = ctk.CTkFrame(self, fg_color='transparent')
        preview_wrap.pack(side='top', fill='both', expand=True,
                          padx=20, pady=(8, 4))
        ctk.CTkLabel(preview_wrap, text='Preview',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=MUTED, anchor='w').pack(anchor='w',
                                                          pady=(0, 4))
        self.preview_box = ctk.CTkTextbox(preview_wrap, font=MONO_BOLD,
                                           fg_color=PANEL, text_color=ACCENT,
                                           wrap='none')
        self.preview_box.pack(fill='both', expand=True)
        self.preview_box.configure(state='disabled')

    # ---------------------------------------------------------- callbacks

    def _on_slider_change(self, value: float) -> None:
        new_size = int(round(value))
        if new_size != self._size:
            self._size = new_size
            self.size_label.configure(text=str(new_size))
        # If user drags while animating, cancel the animation.
        if self._animating:
            self._stop_grow()
        self._refresh()

    def _on_style_change(self, choice: str) -> None:
        self._style = 'filled' if choice == 'Filled' else 'outlined'
        self._refresh()

    def _toggle_grow(self) -> None:
        if self._animating:
            self._stop_grow()
        else:
            self._start_grow()

    def _start_grow(self) -> None:
        self._animating = True
        self._anim_step = 1
        self.grow_btn.configure(text='Stop ■')
        self._tick_grow()

    def _stop_grow(self) -> None:
        self._animating = False
        if self._anim_after_id is not None:
            try:
                self.after_cancel(self._anim_after_id)
            except Exception:
                pass
            self._anim_after_id = None
        self.grow_btn.configure(text='Grow ▶')

    def _tick_grow(self) -> None:
        if not self._animating:
            return
        self._render(self._anim_step)
        target = self._size
        if self._anim_step >= target:
            # Pause at full size for a beat then loop back to 1
            self._anim_step = 1
        else:
            self._anim_step += 1
        self._anim_after_id = self.after(ANIMATION_INTERVAL_MS, self._tick_grow)

    # ------------------------------------------------------------ render

    def _refresh(self) -> None:
        self._render(self._size)

    def _render(self, size: int) -> None:
        renderer = filled if self._style == 'filled' else outlined
        text = renderer(size)
        self.preview_box.configure(state='normal')
        self.preview_box.delete('1.0', 'end')
        self.preview_box.insert('1.0', text)
        self.preview_box.configure(state='disabled')

        line_count = text.count('\n') + 1 if text else 0
        width = max((len(line) for line in text.splitlines()), default=0)
        self.status.configure(
            text=(f'style {self._style}  •  size {size}  •  '
                  f'{line_count} rows × {width} cols  •  '
                  f'{len(text)} chars'))

    def _copy_preview(self) -> None:
        text = self.preview_box.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self.status.configure(text='Copied diamond to clipboard.')


if __name__ == '__main__':
    DiamondsApp().mainloop()
