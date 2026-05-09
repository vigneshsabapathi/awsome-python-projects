"""Lucky Stars - CustomTkinter desktop GUI.

Dark theme with an animated starfield background, a big rolling-stars
display, and a styled fortune card. Save button appends to the JSON
history file shared with the CLI.

Run:
    uv run python lucky_stars/lucky_stars_gui.py
"""
from __future__ import annotations

import math
import random

import customtkinter as ctk

from lucky_stars import (
    STARS,
    UNICODE_SYMBOLS,
    read_fortune,
    save_reading,
)

# --- palette -----------------------------------------------------------------
BG = '#06070d'
PANEL = '#13162a'
BORDER = '#262a47'
ACCENT = '#fde68a'      # warm starlight
ACCENT_HOVER = '#fbbf24'
MUTED = '#8b93b3'
TEXT = '#f8fafc'
THEME_COLOR = {
    'love':    '#f472b6',
    'work':    '#60a5fa',
    'money':   '#34d399',
    'health':  '#a3e635',
    'fortune': '#c084fc',
}

TITLE_FONT = ('Segoe UI', 30, 'bold')
SUBTITLE_FONT = ('Segoe UI', 13)
ROLL_FONT = ('Segoe UI Symbol', 72, 'bold')
NAMES_FONT = ('Segoe UI', 13, 'italic')
THEME_FONT = ('Segoe UI', 16, 'bold')
MSG_FONT = ('Segoe UI', 18, 'bold')
BTN_FONT = ('Segoe UI', 14, 'bold')
STATUS_FONT = ('Segoe UI', 12)

ROLL_FRAME_MS = 80
ROLL_TOTAL_FRAMES = 18  # ~1.4s


class LuckyStarsApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')

        self.title('Lucky Stars')
        self.geometry('780x680')
        self.minsize(660, 580)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.current_reading: dict | None = None
        self._roll_job: str | None = None
        self._roll_counter = 0

        self._build_ui()
        self._start_starfield()

        self.bind('<space>', lambda _e: self._roll())
        self.bind('<Control-s>', lambda _e: self._save())
        self.after(100, self.focus_force)

    # ----- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        # Animated starfield canvas (background layer).
        self.canvas = ctk.CTkCanvas(self, bg=BG, highlightthickness=0)
        self.canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        # Fixed star positions; only the twinkle phase animates.
        self._stars_bg = [
            (random.random(), random.random(), random.random())
            for _ in range(70)
        ]

        # Foreground container.
        self.fg = ctk.CTkFrame(self, fg_color='transparent')
        self.fg.place(relx=0, rely=0, relwidth=1, relheight=1)

        ctk.CTkLabel(self.fg, text='LUCKY  STARS',
                     font=TITLE_FONT, text_color=ACCENT).pack(pady=(22, 0))
        ctk.CTkLabel(self.fg,
                     text='Roll three stars - read what the night sky says.',
                     font=SUBTITLE_FONT, text_color=MUTED).pack(pady=(2, 12))

        # Roll display panel.
        self.panel = ctk.CTkFrame(self.fg, fg_color=PANEL, corner_radius=22,
                                  border_color=BORDER, border_width=1)
        self.panel.pack(padx=28, pady=(4, 12), fill='both', expand=True)

        self.roll_label = ctk.CTkLabel(
            self.panel, text='✦  ✧  ✦', font=ROLL_FONT, text_color=TEXT,
        )
        self.roll_label.pack(pady=(28, 4))

        self.names_label = ctk.CTkLabel(
            self.panel, text='Press ROLL to read your fortune.',
            font=NAMES_FONT, text_color=MUTED,
        )
        self.names_label.pack(pady=(0, 14))

        self.theme_label = ctk.CTkLabel(self.panel, text='',
                                        font=THEME_FONT, text_color=ACCENT)
        self.theme_label.pack()

        self.msg_label = ctk.CTkLabel(
            self.panel, text='',
            font=MSG_FONT, text_color=TEXT,
            wraplength=620, justify='center',
        )
        self.msg_label.pack(padx=24, pady=(8, 22), fill='x')

        # Action row.
        actions = ctk.CTkFrame(self.fg, fg_color='transparent')
        actions.pack(pady=(0, 6), padx=28, fill='x')

        self.roll_btn = ctk.CTkButton(
            actions, text='Roll the stars  (Space)', font=BTN_FONT,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color='#1a1300',
            command=self._roll, height=46,
        )
        self.roll_btn.pack(side='left', expand=True, fill='x', padx=(0, 6))

        self.save_btn = ctk.CTkButton(
            actions, text='Save reading  (Ctrl+S)', font=BTN_FONT,
            fg_color=BORDER, hover_color='#3a3f64', text_color=TEXT,
            command=self._save, height=46, state='disabled',
        )
        self.save_btn.pack(side='left', expand=True, fill='x', padx=(6, 0))

        # Seed row.
        seed_row = ctk.CTkFrame(self.fg, fg_color='transparent')
        seed_row.pack(pady=(8, 4), padx=28, fill='x')
        ctk.CTkLabel(seed_row, text='Seed:', font=STATUS_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 6))
        self.seed_entry = ctk.CTkEntry(
            seed_row, width=120, placeholder_text='(random)',
            fg_color=PANEL, border_color=BORDER, text_color=TEXT,
        )
        self.seed_entry.pack(side='left', padx=(0, 6))
        ctk.CTkButton(seed_row, text='Apply', width=70,
                      fg_color=BORDER, hover_color='#3a3f64',
                      command=self._apply_seed).pack(side='left')

        self.status_label = ctk.CTkLabel(self.fg, text=' ', font=STATUS_FONT,
                                         text_color=MUTED)
        self.status_label.pack(side='bottom', pady=(0, 12))

    # ----- starfield animation --------------------------------------------
    def _start_starfield(self) -> None:
        self._twinkle_tick = 0
        self._draw_starfield()

    def _draw_starfield(self) -> None:
        c = self.canvas
        c.delete('star')
        w = max(self.winfo_width(), 1)
        h = max(self.winfo_height(), 1)
        t = self._twinkle_tick
        for i, (rx, ry, phase) in enumerate(self._stars_bg):
            # Sin-based twinkle on each star, offset by its own phase.
            brightness = 0.45 + 0.55 * (
                0.5 + 0.5 * math.sin((t / 14.0) + phase * 6.28)
            )
            level = int(brightness * 200) + 30
            color = f'#{level:02x}{level:02x}{min(255, level + 30):02x}'
            x = rx * w
            y = ry * h
            size = 1 + (i % 3)
            c.create_oval(x, y, x + size, y + size, fill=color,
                          outline='', tags='star')
        self._twinkle_tick += 1
        self.after(120, self._draw_starfield)

    # ----- behaviour ------------------------------------------------------
    def _roll(self) -> None:
        if self._roll_job is not None:
            return  # already rolling
        self.roll_btn.configure(state='disabled')
        self.save_btn.configure(state='disabled')
        self.theme_label.configure(text='')
        self.msg_label.configure(text='')
        self.names_label.configure(text='Rolling...')
        self._roll_counter = 0
        self._tick_roll()

    def _tick_roll(self) -> None:
        self._roll_counter += 1
        # Random unicode triple while spinning.
        spin = '  '.join(self.rng.choice(UNICODE_SYMBOLS) for _ in range(3))
        self.roll_label.configure(text=spin)
        if self._roll_counter < ROLL_TOTAL_FRAMES:
            self._roll_job = self.after(ROLL_FRAME_MS, self._tick_roll)
        else:
            self._roll_job = None
            self._reveal()

    def _reveal(self) -> None:
        reading = read_fortune(self.rng)
        self.current_reading = reading
        symbols_unicode = [
            UNICODE_SYMBOLS[next(i for i, s in enumerate(STARS)
                                 if s['name'] == name)]
            for name in reading['stars']
        ]
        self.roll_label.configure(text='   '.join(symbols_unicode))
        self.names_label.configure(text=', '.join(reading['stars']))
        theme = reading['theme']
        self.theme_label.configure(
            text=theme.upper(),
            text_color=THEME_COLOR.get(theme, ACCENT),
        )
        self.msg_label.configure(text=reading['message'])
        self.roll_btn.configure(state='normal')
        self.save_btn.configure(state='normal')
        self._set_status('Press SPACE to roll again, Ctrl+S to save.', MUTED)

    def _apply_seed(self) -> None:
        raw = self.seed_entry.get().strip()
        if not raw:
            self.rng = random.Random()
            self._set_status('Seed cleared - back to random.', MUTED)
            return
        try:
            self.rng = random.Random(int(raw))
            self._set_status(f'Seed locked to {raw}. Roll for a shareable reading.',
                             ACCENT)
        except ValueError:
            self._set_status('Seed must be an integer.', '#f87171')

    def _save(self) -> None:
        if self.current_reading is None:
            return
        path = save_reading(self.current_reading)
        self._set_status(f'Saved to {path}', '#34d399')

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, text_color=color)


if __name__ == '__main__':
    LuckyStarsApp().mainloop()
