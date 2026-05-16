"""Vigenère Cipher — CustomTkinter GUI.

Dark-themed desktop UI with live encrypt/decrypt, a keyword entry, and
an auto-crack panel showing IC, Kasiski candidates, and the recovered key.

Run:
    uv run python vigenere/vigenere_gui.py
"""
from __future__ import annotations

import threading
import tkinter as tk

import customtkinter as ctk

from vigenere import (
    ENGLISH_IC,
    RANDOM_IC,
    candidate_key_lengths,
    crack,
    decrypt,
    encrypt,
    friedman_estimate,
    friedman_ic,
    kasiski,
)

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
MONO_FONT = ('Consolas', 13)
BUTTON_FONT = ('Segoe UI', 13, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
ACCENT = '#38bdf8'
GOOD = '#34d399'
WARN = '#f87171'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
BORDER = '#334155'


class VigenereApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Vigenère Cipher')
        self.geometry('900x700')
        self.minsize(820, 620)
        self.configure(fg_color=BG)

        self.mode = tk.StringVar(value='encrypt')
        self.key_var = tk.StringVar(value='KEY')
        self._suspend_update = False
        self._cracking = False

        self._build_ui()
        self._update_output()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=20, pady=(16, 4))
        ctk.CTkLabel(header, text='VIGENÈRE CIPHER', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(
            header,
            text='Polyalphabetic Caesar cipher — Kasiski + IC + per-column crack',
            font=LABEL_FONT, text_color=MUTED,
        ).pack(pady=(2, 0))

        # Bottom action bar
        bottom = ctk.CTkFrame(self, fg_color='transparent')
        bottom.pack(side='bottom', fill='x', padx=20, pady=(4, 14))
        self.count_label = ctk.CTkLabel(bottom, text='0 chars',
                                        font=LABEL_FONT, text_color=MUTED)
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

        # Mode toggle
        mode_frame = ctk.CTkFrame(self, fg_color='transparent')
        mode_frame.pack(side='bottom', pady=(2, 4))
        self.mode_seg = ctk.CTkSegmentedButton(
            mode_frame, values=['encrypt', 'decrypt'],
            command=self._on_mode_change, font=BUTTON_FONT,
            selected_color=ACCENT, selected_hover_color='#0ea5e9',
        )
        self.mode_seg.set('encrypt')
        self.mode_seg.pack()

        # Key entry
        key_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=10,
                                 border_color=BORDER, border_width=1)
        key_frame.pack(side='bottom', fill='x', padx=20, pady=(4, 6))
        top_row = ctk.CTkFrame(key_frame, fg_color='transparent')
        top_row.pack(fill='x', padx=12, pady=(10, 0))
        ctk.CTkLabel(top_row, text='Key (letters only)',
                     font=LABEL_FONT, text_color=MUTED).pack(side='left')
        self.key_status = ctk.CTkLabel(top_row, text='valid key',
                                       font=LABEL_FONT, text_color=GOOD)
        self.key_status.pack(side='right')

        self.key_entry = ctk.CTkEntry(
            key_frame, font=('Consolas', 14, 'bold'),
            fg_color=BG, border_color=BORDER, border_width=1,
            text_color=ACCENT, justify='left',
            textvariable=self.key_var,
        )
        self.key_entry.pack(fill='x', padx=12, pady=(4, 12))
        self.key_var.trace_add('write', self._on_key_change)

        # Body: input/output panes + crack panel
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=(8, 0))

        body.grid_columnconfigure(0, weight=3, minsize=420)
        body.grid_columnconfigure(1, weight=2, minsize=320)
        body.grid_rowconfigure(0, weight=1)

        # Left column: input + output
        text_col = ctk.CTkFrame(body, fg_color='transparent')
        text_col.grid(row=0, column=0, sticky='nsew', padx=(0, 12))

        ctk.CTkLabel(text_col, text='Input', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.input_box = ctk.CTkTextbox(text_col, height=160, font=MONO_FONT,
                                        fg_color=PANEL, text_color=TEXT,
                                        border_width=1, border_color=BORDER)
        self.input_box.pack(fill='both', expand=True, pady=(2, 8))
        self.input_box.insert('1.0', 'Hello, World! This is a Vigenère cipher demo.')
        self.input_box.bind('<KeyRelease>', lambda _e: self._update_output())

        ctk.CTkLabel(text_col, text='Output', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x')
        self.output_box = ctk.CTkTextbox(text_col, height=160, font=MONO_FONT,
                                         fg_color=PANEL, text_color=ACCENT,
                                         border_width=1, border_color=BORDER)
        self.output_box.pack(fill='both', expand=True, pady=(2, 0))

        # Right column: crack analysis panel
        crack_panel = ctk.CTkFrame(body, fg_color=PANEL, corner_radius=10,
                                   border_color=BORDER, border_width=1)
        crack_panel.grid(row=0, column=1, sticky='nsew')
        ctk.CTkLabel(crack_panel, text='Crack analysis',
                     font=LABEL_FONT, text_color=MUTED,
                     anchor='w').pack(fill='x', padx=12, pady=(8, 2))
        ctk.CTkLabel(crack_panel,
                     text='IC, Kasiski candidates, recovered key',
                     font=('Segoe UI', 10), text_color=MUTED,
                     anchor='w').pack(fill='x', padx=12, pady=(0, 6))

        self.crack_box = ctk.CTkTextbox(crack_panel, font=MONO_FONT,
                                        fg_color=PANEL, text_color='#cbd5e1',
                                        border_width=0)
        self.crack_box.pack(fill='both', expand=True, padx=8, pady=(0, 8))
        self.crack_box.configure(state='disabled')

    # --------------------------------------------------------------- events
    def _on_key_change(self, *_args: object) -> None:
        if self._suspend_update:
            return
        raw = self.key_var.get()
        upper = raw.upper()
        if upper != raw:
            self._suspend_update = True
            self.key_var.set(upper)
            self._suspend_update = False
        letters_only = ''.join(c for c in upper if c.isalpha())
        if not letters_only:
            self.key_status.configure(text='need letters', text_color=WARN)
            return
        self.key_status.configure(text='valid key', text_color=GOOD)
        self._update_output()

    def _on_mode_change(self, _value: str) -> None:
        self._update_output()

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
        self._cracking = True
        self.crack_btn.configure(text='Cracking...', state='disabled')
        self.key_status.configure(text='cracking — please wait...',
                                  text_color=ACCENT)
        threading.Thread(target=self._crack_worker, args=(text,),
                         daemon=True).start()

    def _crack_worker(self, text: str) -> None:
        try:
            key, plain = crack(text)
        except Exception as e:
            self.after(0, self._crack_failed, str(e))
            return
        self.after(0, self._crack_done, key, plain)

    def _crack_done(self, key: str, plain: str) -> None:
        if key:
            self._suspend_update = True
            self.key_var.set(key)
            self._suspend_update = False
            self.mode_seg.set('decrypt')
            self.key_status.configure(text=f'cracked: {key}', text_color=GOOD)
        else:
            self.key_status.configure(text='crack failed', text_color=WARN)
        self._update_output()
        self.crack_btn.configure(text='Auto-crack', state='normal')
        self._cracking = False

    def _crack_failed(self, msg: str) -> None:
        self.key_status.configure(text=f'crack failed: {msg}', text_color=WARN)
        self.crack_btn.configure(text='Auto-crack', state='normal')
        self._cracking = False

    # ---------------------------------------------------------------- core
    def _update_output(self) -> None:
        if self._suspend_update:
            return
        text = self.input_box.get('1.0', 'end-1c')
        raw_key = self.key_var.get()
        letters_only = ''.join(c for c in raw_key.upper() if c.isalpha())

        result = ''
        if letters_only:
            try:
                result = (encrypt(text, letters_only)
                          if self.mode_seg.get() == 'encrypt'
                          else decrypt(text, letters_only))
            except ValueError:
                result = ''

        self.output_box.configure(state='normal')
        self.output_box.delete('1.0', 'end')
        self.output_box.insert('1.0', result)

        letters = sum(1 for c in text if c.isalpha())
        self.count_label.configure(
            text=f'{len(text)} chars  •  {letters} letters'
        )
        self._refresh_crack_panel(text)

    def _refresh_crack_panel(self, text: str) -> None:
        self.crack_box.configure(state='normal')
        self.crack_box.delete('1.0', 'end')

        if not text.strip() or sum(1 for c in text if c.isalpha()) < 6:
            self.crack_box.insert('end', '(need more text for analysis)\n')
            self.crack_box.configure(state='disabled')
            return

        ic = friedman_ic(text)
        est = friedman_estimate(text)
        self.crack_box.insert(
            'end',
            f'IC      = {ic:.4f}\n'
            f'  English ≈ {ENGLISH_IC:.4f}  random ≈ {RANDOM_IC:.4f}\n'
            f'Friedman estimate: {est:.2f}\n\n'
        )

        ks = kasiski(text)
        top_ks = ks[:6] if ks else []
        self.crack_box.insert(
            'end',
            f'Kasiski top: {top_ks if top_ks else "— (too short)"}\n\n'
        )

        self.crack_box.insert('end', 'Per-length column IC (top 8):\n')
        for length, ic_l, votes in candidate_key_lengths(text)[:8]:
            tag = '*' if votes else ' '
            self.crack_box.insert(
                'end',
                f'  {tag} L={length:>2}  IC={ic_l:.4f}  k={votes}\n'
            )

        self.crack_box.configure(state='disabled')


if __name__ == '__main__':
    VigenereApp().mainloop()
