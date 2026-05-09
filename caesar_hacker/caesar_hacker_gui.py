"""Caesar Hacker — CustomTkinter GUI.

Paste ciphertext, see all 26 candidate decryptions ranked by
English-likelihood score. The best row is highlighted; "Use" buttons
let you copy any candidate to the clipboard. The "overlap" column
visualises the diff-vs-ciphertext twist — what fraction of letters
each candidate shares with the original ciphertext.

Run:
    uv run python caesar_hacker/caesar_hacker_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from caesar_hacker import crack, letter_overlap

# Tailwind-flavoured dark palette (matches bagels_gui).
BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
ACCENT = '#38bdf8'
GOOD = '#34d399'
WARN = '#f87171'
HEADER_BG = '#0b1220'
ROW_ALT = '#172033'
HIGHLIGHT = '#14532d'  # green-900 — "best" row
HIGHLIGHT_FG = '#bbf7d0'

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 13)
HEADER_FONT = ('Consolas', 12, 'bold')
ROW_FONT = ('Consolas', 12)
MONO_FONT = ('Consolas', 13)


class CaesarHackerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Caesar Hacker')
        self.geometry('960x720')
        self.minsize(860, 600)
        self.configure(fg_color=BG)

        # Model state.
        self.ciphertext: str = ''
        self.candidates: list[tuple[int, float, str]] = []
        # Row widgets are stored so we can recolour the "best" row and
        # rebuild on each crack without flicker.
        self._row_widgets: list[dict] = []

        self._build_ui()
        # Seed with the canonical example so first-run shows real data.
        self.input_box.insert('1.0', 'Khoor, Zruog! Wklv lv d whvw.')
        self._on_crack()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 6))
        ctk.CTkLabel(header, text='CAESAR HACKER', font=TITLE_FONT,
                     text_color=TEXT).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Brute-force every Caesar shift, ranked by '
                          'English-likelihood (chi-squared + word hits)',
                     font=LABEL_FONT, text_color=MUTED).pack(anchor='w',
                                                              pady=(2, 0))

        # Input area.
        input_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                   border_color=BORDER, border_width=1)
        input_frame.pack(side='top', fill='x', padx=20, pady=(8, 8))

        ctk.CTkLabel(input_frame, text='Ciphertext', font=LABEL_FONT,
                     text_color=MUTED).pack(anchor='w', padx=12, pady=(8, 2))
        self.input_box = ctk.CTkTextbox(input_frame, height=80,
                                         font=MONO_FONT,
                                         fg_color=HEADER_BG,
                                         text_color=TEXT,
                                         border_color=BORDER, border_width=1)
        self.input_box.pack(fill='x', padx=12, pady=(0, 8))

        button_row = ctk.CTkFrame(input_frame, fg_color='transparent')
        button_row.pack(fill='x', padx=12, pady=(0, 10))
        ctk.CTkButton(button_row, text='Crack', width=100,
                      font=('Segoe UI', 13, 'bold'),
                      fg_color=ACCENT, hover_color='#0ea5e9',
                      text_color=BG,
                      command=self._on_crack).pack(side='left')
        ctk.CTkButton(button_row, text='Clear', width=80,
                      fg_color=BORDER, hover_color='#475569',
                      command=self._on_clear).pack(side='left', padx=(8, 0))
        ctk.CTkButton(button_row, text='Copy Best', width=110,
                      fg_color=GOOD, hover_color='#10b981', text_color=BG,
                      command=self._on_copy_best).pack(side='left',
                                                        padx=(8, 0))
        self.status = ctk.CTkLabel(button_row, text='', font=LABEL_FONT,
                                    text_color=MUTED)
        self.status.pack(side='right')

        # Results table.
        results_panel = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                      border_color=BORDER, border_width=1)
        results_panel.pack(side='top', fill='both', expand=True,
                           padx=20, pady=(0, 16))

        # Column layout: rank, shift, score, overlap, plaintext, button.
        # We model the table with grid inside a scrollable frame.
        self._build_table_header(results_panel)

        self.scroll = ctk.CTkScrollableFrame(results_panel,
                                              fg_color='transparent',
                                              scrollbar_button_color=BORDER,
                                              scrollbar_button_hover_color=MUTED)
        self.scroll.pack(fill='both', expand=True, padx=8, pady=(0, 8))

    def _build_table_header(self, parent: ctk.CTkFrame) -> None:
        head = ctk.CTkFrame(parent, fg_color=HEADER_BG, corner_radius=6)
        head.pack(fill='x', padx=8, pady=(8, 4))
        # Match the column widths we use in row builds.
        cols = (('#',       60,  'w'),
                ('shift',   60,  'w'),
                ('score',   90,  'e'),
                ('overlap', 80,  'e'),
                ('plaintext', 1,  'w'),  # stretches
                ('',        90,  'e'))
        for i, (label, w, anchor) in enumerate(cols):
            head.grid_columnconfigure(i, weight=(1 if w == 1 else 0),
                                       minsize=(w if w != 1 else 0))
            ctk.CTkLabel(head, text=label, font=HEADER_FONT,
                         text_color=MUTED, anchor=anchor).grid(
                row=0, column=i, sticky='ew', padx=8, pady=4)

    def _build_row(self, parent, idx: int, shift: int, score: float,
                   overlap: float, plaintext: str, is_best: bool) -> dict:
        bg = HIGHLIGHT if is_best else (PANEL if idx % 2 == 0 else ROW_ALT)
        fg = HIGHLIGHT_FG if is_best else TEXT

        row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=4)
        row.pack(fill='x', pady=1)
        cols = ((str(idx + 1),               60, 'w'),
                (str(shift),                  60, 'w'),
                (f'{score:>9.2f}',            90, 'e'),
                (f'{overlap * 100:>5.1f}%',   80, 'e'))
        for i, (text, w, anchor) in enumerate(cols):
            row.grid_columnconfigure(i, minsize=w)
            ctk.CTkLabel(row, text=text, font=ROW_FONT, text_color=fg,
                         anchor=anchor).grid(row=0, column=i,
                                              sticky='ew', padx=8, pady=4)
        # Plaintext stretches.
        row.grid_columnconfigure(4, weight=1)
        snippet = plaintext if len(plaintext) <= 110 else plaintext[:109] + '…'
        plain_label = ctk.CTkLabel(row, text=snippet, font=ROW_FONT,
                                    text_color=fg, anchor='w')
        plain_label.grid(row=0, column=4, sticky='ew', padx=8, pady=4)

        use_btn = ctk.CTkButton(
            row, text='Use this shift', width=120, height=24,
            font=('Segoe UI', 11),
            fg_color=ACCENT if not is_best else GOOD,
            hover_color='#0ea5e9' if not is_best else '#10b981',
            text_color=BG,
            command=lambda s=shift, p=plaintext: self._on_use_shift(s, p))
        use_btn.grid(row=0, column=5, padx=8, pady=4, sticky='e')

        return {'frame': row, 'plain': plaintext, 'shift': shift}

    # -------------------------------------------------------------- Actions
    def _on_crack(self) -> None:
        text = self.input_box.get('1.0', 'end').strip()
        if not text:
            self._set_status('Enter ciphertext above to begin.', WARN)
            self._clear_rows()
            return
        self.ciphertext = text
        self.candidates = crack(text)
        self._render_rows()
        best_shift, best_score, best_plain = self.candidates[0]
        self._set_status(
            f'Best: shift={best_shift}  score={best_score:.2f}', GOOD)

    def _on_clear(self) -> None:
        self.input_box.delete('1.0', 'end')
        self.ciphertext = ''
        self.candidates = []
        self._clear_rows()
        self._set_status('', MUTED)

    def _on_copy_best(self) -> None:
        if not self.candidates:
            self._set_status('Nothing to copy yet.', WARN)
            return
        best_plain = self.candidates[0][2]
        self.clipboard_clear()
        self.clipboard_append(best_plain)
        self._set_status('Top result copied to clipboard.', GOOD)

    def _on_use_shift(self, shift: int, plaintext: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(plaintext)
        self._set_status(
            f'Copied shift={shift} plaintext to clipboard.', GOOD)

    def _set_status(self, text: str, color: str) -> None:
        self.status.configure(text=text, text_color=color)

    def _clear_rows(self) -> None:
        for w in self._row_widgets:
            w['frame'].destroy()
        self._row_widgets = []

    def _render_rows(self) -> None:
        self._clear_rows()
        for i, (shift, score, plaintext) in enumerate(self.candidates):
            overlap = letter_overlap(self.ciphertext, plaintext)
            self._row_widgets.append(
                self._build_row(self.scroll, i, shift, score, overlap,
                                 plaintext, is_best=(i == 0)))


if __name__ == '__main__':
    CaesarHackerApp().mainloop()
