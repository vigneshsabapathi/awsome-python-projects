"""Clickbait Headline Generator — CustomTkinter GUI.

Dark-themed desktop UI with a big headline display, category dropdown,
spacebar-binding for "Generate", batch viewer, and a Copy button.

Run:
    uv run python clickbait/clickbait_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from clickbait import (
    CATEGORIES,
    generate_batch,
    generate_headline,
    outrage_score,
)

TITLE_FONT = ('Segoe UI', 28, 'bold')
HEADLINE_FONT = ('Segoe UI', 22, 'bold')
LABEL_FONT = ('Segoe UI', 13)
META_FONT = ('Segoe UI', 12, 'italic')
BTN_FONT = ('Segoe UI', 14, 'bold')
BATCH_FONT = ('Segoe UI', 13)

BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
ACCENT = '#38bdf8'
ACCENT_HOVER = '#0ea5e9'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
WARN = '#f87171'
OK = '#34d399'


class ClickbaitApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Clickbait Headline Generator')
        self.geometry('760x620')
        self.minsize(640, 520)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.current_headline: str = ''
        self.category_var = ctk.StringVar(value='general')

        self._build_ui()
        self._generate()

        # Spacebar generates a fresh headline; Ctrl+C copies; Ctrl+B batches.
        self.bind('<space>', lambda _e: self._generate())
        self.bind('<Control-c>', lambda _e: self._copy())
        self.bind('<Control-b>', lambda _e: self._batch_window())
        self.after(100, self.focus_force)

    # ----- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(18, 4), padx=24, fill='x')
        ctk.CTkLabel(header, text='CLICKBAIT', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(header,
                     text='Press SPACE for a fresh headline',
                     font=LABEL_FONT, text_color=MUTED).pack(pady=(2, 0))

        # Category + seed controls.
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='top', pady=(8, 4), padx=24, fill='x')

        ctk.CTkLabel(controls, text='Category:', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 6))
        self.category_menu = ctk.CTkOptionMenu(
            controls,
            values=sorted(CATEGORIES.keys()),
            variable=self.category_var,
            command=lambda _v: self._generate(),
            fg_color=PANEL, button_color=BORDER,
            button_hover_color=ACCENT, text_color=TEXT,
            dropdown_fg_color=PANEL, dropdown_text_color=TEXT,
            width=140,
        )
        self.category_menu.pack(side='left', padx=(0, 18))

        ctk.CTkLabel(controls, text='Seed:', font=LABEL_FONT,
                     text_color=MUTED).pack(side='left', padx=(0, 6))
        self.seed_entry = ctk.CTkEntry(controls, width=110,
                                       placeholder_text='(random)',
                                       fg_color=PANEL, border_color=BORDER,
                                       text_color=TEXT)
        self.seed_entry.pack(side='left', padx=(0, 6))
        ctk.CTkButton(controls, text='Apply seed', width=90,
                      fg_color=BORDER, hover_color='#475569',
                      command=self._apply_seed).pack(side='left')

        # Headline panel — the centerpiece.
        panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=18,
                             border_color=BORDER, border_width=1)
        panel.pack(side='top', expand=True, fill='both',
                   padx=24, pady=(16, 12))

        self.headline_label = ctk.CTkLabel(
            panel, text='', font=HEADLINE_FONT, text_color=TEXT,
            wraplength=640, justify='center',
        )
        self.headline_label.pack(expand=True, padx=24, pady=(28, 8))

        self.meta_label = ctk.CTkLabel(panel, text='', font=META_FONT,
                                       text_color=MUTED)
        self.meta_label.pack(pady=(0, 24))

        # Action row.
        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(side='top', pady=(0, 8), padx=24, fill='x')

        ctk.CTkButton(actions, text='Generate (Space)',
                      font=BTN_FONT, fg_color=ACCENT,
                      hover_color=ACCENT_HOVER, text_color='#0f172a',
                      command=self._generate).pack(side='left',
                                                   expand=True, fill='x',
                                                   padx=(0, 6))
        ctk.CTkButton(actions, text='Generate batch of 10',
                      font=BTN_FONT, fg_color=BORDER,
                      hover_color='#475569', text_color=TEXT,
                      command=self._batch_window).pack(side='left',
                                                       expand=True, fill='x',
                                                       padx=6)
        ctk.CTkButton(actions, text='Copy',
                      font=BTN_FONT, fg_color=BORDER,
                      hover_color='#475569', text_color=TEXT,
                      command=self._copy).pack(side='left',
                                               expand=True, fill='x',
                                               padx=(6, 0))

        self.status_label = ctk.CTkLabel(self, text=' ', font=LABEL_FONT,
                                         text_color=MUTED)
        self.status_label.pack(side='bottom', pady=(0, 12))

    # ----- behaviour -------------------------------------------------------
    def _generate(self) -> None:
        category = self.category_var.get()
        self.current_headline = generate_headline(self.rng, category)
        self.headline_label.configure(text=self.current_headline)
        score = outrage_score(self.current_headline)
        bar = '#' * (score // 10) + '.' * (10 - score // 10)
        self.meta_label.configure(
            text=f'Outrage [{bar}] {score}/100  •  category: {category}'
        )
        self._set_status('Press SPACE for another, or Copy to share.', MUTED)

    def _apply_seed(self) -> None:
        raw = self.seed_entry.get().strip()
        if not raw:
            self.rng = random.Random()
            self._set_status('Seed cleared — back to random.', MUTED)
        else:
            try:
                self.rng = random.Random(int(raw))
                self._set_status(f'Seed locked to {raw}.', OK)
            except ValueError:
                self._set_status('Seed must be an integer.', WARN)
                return
        self._generate()

    def _copy(self) -> None:
        if not self.current_headline:
            return
        self.clipboard_clear()
        self.clipboard_append(self.current_headline)
        self._set_status('Copied to clipboard.', OK)

    def _set_status(self, text: str, color: str) -> None:
        self.status_label.configure(text=text, text_color=color)

    # ----- batch viewer ----------------------------------------------------
    def _batch_window(self) -> None:
        category = self.category_var.get()
        # Use a fresh rng-snapshot so the main RNG stream isn't disturbed.
        batch = generate_batch(10, rng=self.rng, category=category)

        win = ctk.CTkToplevel(self)
        win.title(f'Batch · {category}')
        win.geometry('640x520')
        win.configure(fg_color=BG)
        win.transient(self)

        ctk.CTkLabel(win, text=f'10 fresh headlines — {category}',
                     font=('Segoe UI', 16, 'bold'),
                     text_color=TEXT).pack(pady=(14, 6))

        scroll = ctk.CTkScrollableFrame(win, fg_color=PANEL,
                                        border_color=BORDER, border_width=1,
                                        corner_radius=12)
        scroll.pack(expand=True, fill='both', padx=18, pady=(4, 14))

        for i, headline in enumerate(batch, 1):
            score = outrage_score(headline)
            row = ctk.CTkFrame(scroll, fg_color='transparent')
            row.pack(fill='x', padx=6, pady=4)
            ctk.CTkLabel(row, text=f'{i:2d}.', font=BATCH_FONT,
                         text_color=MUTED, width=28).pack(side='left',
                                                          anchor='n')
            ctk.CTkLabel(row, text=headline, font=BATCH_FONT,
                         text_color=TEXT, justify='left',
                         wraplength=480, anchor='w').pack(side='left',
                                                          fill='x',
                                                          expand=True)
            ctk.CTkLabel(row, text=f'{score:3d}', font=BATCH_FONT,
                         text_color=ACCENT, width=36).pack(side='right')


if __name__ == '__main__':
    ClickbaitApp().mainloop()
