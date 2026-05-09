"""Simple Substitution Cipher — CustomTkinter GUI.

Dark-themed desktop UI. Edit the 26-letter key, type plaintext or
ciphertext, toggle encrypt/decrypt, hit Auto-crack to launch a
simulated-annealing attack on the ciphertext. A matplotlib chart
shows the letter-frequency distribution of the current input
overlaid with the English baseline.

Run:
    uv run python simple_sub/simple_sub_gui.py
"""
from __future__ import annotations

import string
import threading
import tkinter as tk

import customtkinter as ctk
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from simple_sub import (
    ALPHABET,
    ENGLISH_FREQ,
    crack_with_key,
    decrypt,
    encrypt,
    letter_frequencies,
    random_key,
)

# Tailwind-flavoured dark palette (matches caesar_cipher_gui).
TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 13)
KEY_FONT = ('Consolas', 14, 'bold')
BUTTON_FONT = ('Segoe UI', 13, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#38bdf8'
GOOD = '#34d399'
WARN = '#f87171'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
BORDER = '#334155'


class SimpleSubApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Simple Substitution Cipher')
        self.geometry('1080x880')
        self.minsize(960, 800)
        self.configure(fg_color=BG)

        self.mode = tk.StringVar(value='encrypt')
        self.key_var = tk.StringVar(value=ALPHABET)
        self._suspend_update = False
        self._cracking = False

        self._build_ui()
        self._update_output()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # --- Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='SIMPLE SUBSTITUTION CIPHER',
                     font=TITLE_FONT, text_color=TEXT).pack()
        ctk.CTkLabel(
            header,
            text='Each letter mapped to another via a 26-character permutation. '
                 'Auto-crack uses simulated annealing on bigram/trigram scores.',
            font=LABEL_FONT, text_color=MUTED,
        ).pack(pady=(2, 0))

        # --- Bottom action bar
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(side='bottom', fill='x', padx=20, pady=(4, 14))
        self.count_label = ctk.CTkLabel(bottom, text='0 chars', font=LABEL_FONT,
                                        text_color=MUTED)
        self.count_label.pack(side='left')
        self.copy_btn = ctk.CTkButton(bottom, text='Copy output',
                                      width=130, height=36, font=BUTTON_FONT,
                                      fg_color=BORDER, hover_color='#475569',
                                      command=self._copy_output)
        self.copy_btn.pack(side='right')
        self.crack_btn = ctk.CTkButton(bottom, text='Auto-crack',
                                       width=130, height=36, font=BUTTON_FONT,
                                       fg_color=ACCENT, hover_color='#0ea5e9',
                                       text_color=BG,
                                       command=self._auto_crack)
        self.crack_btn.pack(side='right', padx=(0, 8))
        self.random_btn = ctk.CTkButton(bottom, text='Random key',
                                        width=130, height=36, font=BUTTON_FONT,
                                        fg_color='#475569',
                                        hover_color='#64748b',
                                        command=self._on_random_key)
        self.random_btn.pack(side='right', padx=(0, 8))

        # --- Mode toggle
        mode_frame = ctk.CTkFrame(self, fg_color='transparent')
        mode_frame.pack(side='bottom', pady=(2, 4))
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_frame, values=['encrypt', 'decrypt'],
            command=self._on_mode_change, font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color='#0ea5e9',
        )
        self.mode_seg.set('encrypt')
        self.mode_seg.pack()

        # --- Key entry
        key_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                 border_color=BORDER, border_width=1)
        key_frame.pack(side='bottom', fill='x', padx=20, pady=(4, 6))
        top_row = ctk.CTkFrame(key_frame, fg_color='transparent')
        top_row.pack(fill='x', padx=12, pady=(10, 0))
        ctk.CTkLabel(top_row, text='Key (26 letters)',
                     font=LABEL_FONT, text_color=MUTED).pack(side='left')
        self.key_status = ctk.CTkLabel(top_row, text='valid permutation',
                                       font=LABEL_FONT, text_color=GOOD)
        self.key_status.pack(side='right')

        # Reference row above the entry — shows the canonical alphabet
        # so the user can read the key as a substitution table.
        ref_row = ctk.CTkFrame(key_frame, fg_color='transparent')
        ref_row.pack(fill='x', padx=12, pady=(4, 0))
        ctk.CTkLabel(ref_row, text='ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                     font=KEY_FONT, text_color=MUTED).pack(side='left')

        self.key_entry = ctk.CTkEntry(
            key_frame, font=KEY_FONT,
            fg_color=BG, border_color=BORDER, border_width=1,
            text_color=ACCENT, justify='left',
            textvariable=self.key_var,
        )
        self.key_entry.pack(fill='x', padx=12, pady=(0, 12))
        self.key_var.trace_add('write', self._on_key_change)

        # --- Body: input/output panes + frequency chart
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(8, 0))

        # Two-column layout: text panes left, frequency chart right.
        body.grid_columnconfigure(0, weight=3, minsize=420)
        body.grid_columnconfigure(1, weight=2, minsize=380)
        body.grid_rowconfigure(0, weight=1)

        text_col = ctk.CTkFrame(body, fg_color='transparent')
        text_col.grid(row=0, column=0, sticky='nsew', padx=(0, 12))

        ctk.CTkLabel(text_col, text='Input', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.input_box = ctk.CTkTextbox(text_col, height=160, font=MONO_FONT,
                                        fg_color=PANEL, text_color=TEXT,
                                        border_width=1, border_color=BORDER)
        self.input_box.pack(fill='both', expand=True, pady=(2, 8))
        self.input_box.insert('1.0', 'Hello, World! This is a substitution cipher demo.')
        self.input_box.bind('<KeyRelease>', lambda _e: self._update_output())

        ctk.CTkLabel(text_col, text='Output', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.output_box = ctk.CTkTextbox(text_col, height=160, font=MONO_FONT,
                                         fg_color=PANEL, text_color=ACCENT,
                                         border_width=1, border_color=BORDER)
        self.output_box.pack(fill='both', expand=True, pady=(2, 0))

        # Frequency chart panel
        chart_panel = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=10,
                                    border_color=BORDER, border_width=1)
        chart_panel.grid(row=0, column=1, sticky='nsew')
        ctk.CTkLabel(chart_panel,
                     text='Letter-frequency analysis',
                     font=LABEL_FONT, text_color=MUTED, anchor='w').pack(
            fill='x', padx=12, pady=(8, 2))
        ctk.CTkLabel(chart_panel,
                     text='Bars: input letter frequencies. Line: English baseline.',
                     font=('Segoe UI', 10), text_color=MUTED,
                     anchor='w').pack(fill='x', padx=12, pady=(0, 6))

        self.fig = Figure(figsize=(5, 4), dpi=100, facecolor=PANEL)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()
        self.canvas = FigureCanvasTkAgg(self.fig, master=chart_panel)
        self.canvas.get_tk_widget().pack(fill='both', expand=True,
                                         padx=8, pady=(0, 8))

    def _style_axes(self) -> None:
        ax = self.ax
        ax.set_facecolor(PANEL)
        for spine in ax.spines.values():
            spine.set_color(BORDER)
        ax.tick_params(colors=MUTED, labelsize=9)
        ax.yaxis.label.set_color(MUTED)
        ax.xaxis.label.set_color(MUTED)
        ax.title.set_color(TEXT)
        ax.set_xlabel('Letter')
        ax.set_ylabel('Frequency (%)')

    # --------------------------------------------------------------- events
    def _on_key_change(self, *_args: object) -> None:
        # Validate the key. Show colour-coded status. If invalid,
        # don't update the output (avoids a flood of errors).
        if self._suspend_update:
            return
        key = self.key_var.get().upper()
        # Force uppercase echo back.
        if key != self.key_var.get():
            self._suspend_update = True
            self.key_var.set(key)
            self._suspend_update = False
        if len(key) != 26:
            self.key_status.configure(text=f'{len(key)}/26 chars',
                                      text_color=WARN)
            return
        if any(c not in ALPHABET for c in key):
            self.key_status.configure(text='non-letter chars',
                                      text_color=WARN)
            return
        if sorted(key) != list(ALPHABET):
            self.key_status.configure(text='not a permutation',
                                      text_color=WARN)
            return
        self.key_status.configure(text='valid permutation',
                                  text_color=GOOD)
        self._update_output()

    def _on_mode_change(self, _value: str) -> None:
        self._update_output()

    def _on_random_key(self) -> None:
        self.key_var.set(random_key())
        # _on_key_change updates output.

    def _copy_output(self) -> None:
        text = self.output_box.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(text)
        original = self.copy_btn.cget('text')
        self.copy_btn.configure(text='Copied!')
        self.after(900, lambda: self.copy_btn.configure(text=original))

    def _auto_crack(self) -> None:
        if self._cracking:
            return
        text = self.input_box.get('1.0', 'end-1c')
        if not text.strip():
            return
        # Crack always operates on the input as ciphertext.
        self._cracking = True
        self.crack_btn.configure(text='Cracking...', state='disabled')
        self.key_status.configure(text='annealing — please wait...',
                                  text_color=ACCENT)
        # Run the search on a worker thread so the UI stays responsive.
        threading.Thread(target=self._crack_worker, args=(text,),
                         daemon=True).start()

    def _crack_worker(self, text: str) -> None:
        try:
            plain, key, score = crack_with_key(text)
        except Exception as e:  # pragma: no cover
            self.after(0, self._crack_failed, str(e))
            return
        self.after(0, self._crack_done, plain, key, score)

    def _crack_done(self, plain: str, key: str, score: float) -> None:
        # The discovered `key` is the plaintext->ciphertext map. Switch
        # the UI to decrypt mode with that key so the input (treated as
        # ciphertext) becomes plaintext.
        self.mode_seg.set('decrypt')
        self._suspend_update = True
        self.key_var.set(key)
        self._suspend_update = False
        self.key_status.configure(
            text=f'cracked: score={score:+.1f}', text_color=GOOD)
        self._update_output()
        self.crack_btn.configure(text='Auto-crack', state='normal')
        self._cracking = False

    def _crack_failed(self, msg: str) -> None:
        self.key_status.configure(text=f'crack failed: {msg}', text_color=WARN)
        self.crack_btn.configure(text='Auto-crack', state='normal')
        self._cracking = False

    # ----------------------------------------------------------------- core
    def _update_output(self) -> None:
        if self._suspend_update:
            return
        text = self.input_box.get('1.0', 'end-1c')
        key = self.key_var.get().upper()
        # Only run the cipher when the key is a valid permutation;
        # otherwise leave the output as-is to avoid flicker.
        result = ''
        try:
            result = (encrypt(text, key) if self.mode_seg.get() == 'encrypt'
                      else decrypt(text, key))
        except ValueError:
            result = ''
        self.output_box.configure(state='normal')
        self.output_box.delete('1.0', 'end')
        self.output_box.insert('1.0', result)

        letters = sum(1 for c in text if c.isalpha())
        self.count_label.configure(
            text=f'{len(text)} chars  •  {letters} letters'
        )
        self._refresh_chart(text)

    def _refresh_chart(self, text: str) -> None:
        ax = self.ax
        ax.clear()
        self._style_axes()
        freqs = letter_frequencies(text)
        labels = list(string.ascii_uppercase)
        observed = [freqs[ch] for ch in labels]
        baseline = [ENGLISH_FREQ[ch] for ch in labels]
        x = list(range(len(labels)))
        ax.bar(x, observed, color=ACCENT, alpha=0.85, label='input')
        ax.plot(x, baseline, color=GOOD, linewidth=1.5,
                marker='o', markersize=3, label='English')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=8)
        ax.legend(facecolor=PANEL, edgecolor=BORDER, labelcolor=TEXT,
                  fontsize=9, loc='upper right')
        ax.set_ylim(0, max(15, max(observed + [0]) + 2))
        self.fig.tight_layout()
        self.canvas.draw_idle()


if __name__ == '__main__':
    SimpleSubApp().mainloop()
