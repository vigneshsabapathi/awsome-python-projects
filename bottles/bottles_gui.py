"""99 Bottles of Beer — CustomTkinter GUI.

Dark-themed desktop UI with a big lyrics display, "Next verse" button
(also bound to Space), starting-count slider, scroll-through animation,
and a Remix toggle.

Run:
    uv run python bottles/bottles_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from bottles import _bottles_phrase, render_verse

TITLE_FONT = ('Segoe UI', 28, 'bold')
LYRICS_FONT = ('Consolas', 22, 'bold')
LABEL_FONT = ('Segoe UI', 13)
META_FONT = ('Segoe UI', 12, 'italic')
BTN_FONT = ('Segoe UI', 14, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
ACCENT = '#38bdf8'
ACCENT_HOVER = '#0ea5e9'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
WARN = '#f87171'
OK = '#34d399'

# Scroll animation: how fast to flip verses when the user holds "Play".
SCROLL_INTERVAL_MS = 350


class BottlesApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('99 Bottles of Beer')
        self.geometry('780x640')
        self.minsize(660, 540)
        self.configure(fg_color=BG)

        # Internal state.
        self.start_count: int = 99
        self.current: int = 99
        self.remix_var = ctk.BooleanVar(value=False)
        self.scrolling: bool = False
        self._scroll_after_id: str | None = None
        self.rng = random.Random()

        self._build_ui()
        self._render_current()

        # Keyboard: Space advances, R toggles remix, Enter resets.
        self.bind('<space>', lambda _e: self._next_verse())
        self.bind('<r>', lambda _e: self._toggle_remix())
        self.bind('<R>', lambda _e: self._toggle_remix())
        self.bind('<Return>', lambda _e: self._reset())
        self.after(100, self.focus_force)

    # ----- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(18, 4), padx=24, fill='x')
        ctk.CTkLabel(header, text='99 BOTTLES', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(
            header,
            text='Press SPACE for the next verse  -  R for remix  -  '
                 'Enter to reset',
            font=LABEL_FONT, text_color=MUTED,
        ).pack(pady=(2, 0))

        # Start-count slider + remix toggle.
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='top', pady=(8, 4), padx=24, fill='x')

        ctk.CTkLabel(controls, text='Start at:', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 6))
        self.start_label = ctk.CTkLabel(controls, text='99 bottles',
                                        font=LABEL_FONT, text_color=ACCENT,
                                        width=110, anchor='w')
        self.start_label.pack(side='left', padx=(0, 8))

        self.start_slider = ctk.CTkSlider(
            controls, from_=1, to=99, number_of_steps=98,
            command=self._on_slider,
            fg_color=BORDER, progress_color=ACCENT,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
        )
        self.start_slider.set(99)
        self.start_slider.pack(side='left', expand=True, fill='x',
                               padx=(0, 18))

        self.remix_switch = ctk.CTkSwitch(
            controls, text='Remix', variable=self.remix_var,
            command=self._render_current, font=LABEL_FONT,
            progress_color=ACCENT, button_color=TEXT,
            button_hover_color=ACCENT_HOVER,
        )
        self.remix_switch.pack(side='left')

        # Lyrics panel — the centerpiece, big monospace text.
        panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=18,
                             border_color=BORDER, border_width=1)
        panel.pack(side='top', expand=True, fill='both',
                   padx=24, pady=(16, 12))

        self.lyrics_label = ctk.CTkLabel(
            panel, text='', font=LYRICS_FONT, text_color=TEXT,
            wraplength=680, justify='center',
        )
        self.lyrics_label.pack(expand=True, padx=24, pady=(28, 8))

        self.meta_label = ctk.CTkLabel(panel, text='', font=META_FONT,
                                       text_color=MUTED)
        self.meta_label.pack(pady=(0, 24))

        # Action row.
        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(side='top', pady=(0, 8), padx=24, fill='x')

        ctk.CTkButton(
            actions, text='Next verse (Space)', font=BTN_FONT,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color='#0f172a',
            command=self._next_verse,
        ).pack(side='left', expand=True, fill='x', padx=(0, 6))

        self.play_btn = ctk.CTkButton(
            actions, text='Play scroll', font=BTN_FONT,
            fg_color=BORDER, hover_color='#475569', text_color=TEXT,
            command=self._toggle_scroll,
        )
        self.play_btn.pack(side='left', expand=True, fill='x', padx=6)

        ctk.CTkButton(
            actions, text='Reset', font=BTN_FONT,
            fg_color=BORDER, hover_color='#475569', text_color=TEXT,
            command=self._reset,
        ).pack(side='left', expand=True, fill='x', padx=(6, 0))

        self.status_label = ctk.CTkLabel(self, text=' ', font=LABEL_FONT,
                                         text_color=MUTED)
        self.status_label.pack(side='bottom', pady=(0, 12))

    # ----- behaviour -------------------------------------------------------
    def _on_slider(self, value: float) -> None:
        new_start = int(round(value))
        self.start_count = new_start
        self.current = new_start
        self.start_label.configure(text=_bottles_phrase(new_start))
        self._render_current()
        self._set_status('Starting count updated.', MUTED)

    def _toggle_remix(self) -> None:
        self.remix_var.set(not self.remix_var.get())
        self._render_current()

    def _next_verse(self) -> None:
        # 0 is the wraparound verse; after that we loop back to start.
        if self.current <= 0:
            self.current = self.start_count
        else:
            self.current -= 1
        self._render_current()

    def _reset(self) -> None:
        self._stop_scroll()
        self.current = self.start_count
        self._render_current()
        self._set_status('Reset to start.', MUTED)

    def _toggle_scroll(self) -> None:
        if self.scrolling:
            self._stop_scroll()
        else:
            self._start_scroll()

    def _start_scroll(self) -> None:
        self.scrolling = True
        self.play_btn.configure(text='Pause scroll')
        self._tick_scroll()

    def _stop_scroll(self) -> None:
        self.scrolling = False
        self.play_btn.configure(text='Play scroll')
        if self._scroll_after_id is not None:
            try:
                self.after_cancel(self._scroll_after_id)
            except Exception:
                pass
            self._scroll_after_id = None

    def _tick_scroll(self) -> None:
        if not self.scrolling:
            return
        self._next_verse()
        # When we hit the wraparound verse, pause briefly to let the user
        # appreciate the punchline, then continue.
        delay = SCROLL_INTERVAL_MS * 2 if self.current == 0 else SCROLL_INTERVAL_MS
        self._scroll_after_id = self.after(delay, self._tick_scroll)

    def _render_current(self) -> None:
        n = max(0, self.current)
        text = render_verse(n, remix=self.remix_var.get(), rng=self.rng)
        self.lyrics_label.configure(text=text)
        if n == 0:
            label = 'wraparound verse'
        else:
            label = f'verse {self.start_count - n + 1} of {self.start_count + 1}'
        mode = 'remix' if self.remix_var.get() else 'classic'
        self.meta_label.configure(
            text=f'{label}  -  bottles left: {n}  -  mode: {mode}'
        )

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, text_color=color)


if __name__ == '__main__':
    BottlesApp().mainloop()
