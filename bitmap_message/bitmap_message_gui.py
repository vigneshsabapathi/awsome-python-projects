"""Bitmap Message — CustomTkinter GUI.

Live two-pane editor: type a message on top, edit the bitmap on the left,
see the rendered ASCII art on the right. Copies to clipboard with one click.

Run:
    uv run python bitmap_message/bitmap_message_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from bitmap_message import PRESETS, render

DEFAULT_PRESET = 'Diamond'

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
MONO = ('Consolas', 11)
MONO_BOLD = ('Consolas', 11, 'bold')


class BitmapMessageApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Bitmap Message')
        self.geometry('1100x700')
        self.minsize(900, 560)
        self.configure(fg_color=BG)

        self._build_ui()
        self._refresh()
        self.message_entry.focus()

    def _build_ui(self) -> None:
        # Header
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='BITMAP MESSAGE',
                     font=('Segoe UI', 24, 'bold'),
                     text_color=FG).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Type a message — non-space pixels in the bitmap '
                          'fill with characters cycled from your message.',
                     font=('Segoe UI', 12), text_color=MUTED).pack(anchor='w',
                                                                    pady=(2, 0))

        # Bottom controls (packed first to stay visible)
        self.status = ctk.CTkLabel(self, text='', font=('Segoe UI', 11),
                                   text_color=MUTED)
        self.status.pack(side='bottom', pady=(2, 8))

        actions = ctk.CTkFrame(self, fg_color='transparent')
        actions.pack(side='bottom', padx=20, pady=(0, 4), fill='x')
        ctk.CTkLabel(actions, text='Preset:',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=FG).pack(side='left')
        self.preset_var = ctk.StringVar(value=DEFAULT_PRESET)
        self.preset_menu = ctk.CTkOptionMenu(
            actions, values=list(PRESETS.keys()), variable=self.preset_var,
            width=130, fg_color=PANEL, button_color='#334155',
            button_hover_color='#475569',
            command=self._on_preset_change)
        self.preset_menu.pack(side='left', padx=(8, 0))
        ctk.CTkButton(actions, text='Copy preview',
                      fg_color=ACCENT, hover_color='#0ea5e9',
                      text_color='#0f172a', font=('Segoe UI', 12, 'bold'),
                      width=140, command=self._copy_preview).pack(side='right')
        ctk.CTkButton(actions, text='Reset bitmap',
                      fg_color='#334155', hover_color='#475569',
                      width=120,
                      command=self._reset_bitmap).pack(side='right',
                                                        padx=(0, 8))

        # Message input row
        msg_row = ctk.CTkFrame(self, fg_color='transparent')
        msg_row.pack(side='top', padx=20, pady=(8, 4), fill='x')
        ctk.CTkLabel(msg_row, text='Message:',
                     font=('Segoe UI', 13, 'bold'),
                     text_color=FG).pack(side='left')
        self.message_entry = ctk.CTkEntry(msg_row, font=('Segoe UI', 14),
                                          height=36, placeholder_text='Hello!')
        self.message_entry.pack(side='left', fill='x', expand=True,
                                padx=(10, 0))
        self.message_entry.insert(0, 'Hello!')
        self.message_entry.bind('<KeyRelease>', lambda _e: self._refresh())

        # Two-pane: bitmap source | preview
        panes = ctk.CTkFrame(self, fg_color='transparent')
        panes.pack(side='top', fill='both', expand=True,
                   padx=20, pady=(8, 4))
        panes.grid_columnconfigure(0, weight=1, uniform='pane')
        panes.grid_columnconfigure(1, weight=1, uniform='pane')
        panes.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(panes, text='Bitmap (editable)',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=MUTED, anchor='w').grid(row=0, column=0,
                                                         sticky='ew',
                                                         pady=(0, 4))
        ctk.CTkLabel(panes, text='Preview',
                     font=('Segoe UI', 12, 'bold'),
                     text_color=MUTED, anchor='w').grid(row=0, column=1,
                                                         sticky='ew',
                                                         padx=(8, 0),
                                                         pady=(0, 4))

        self.bitmap_box = ctk.CTkTextbox(panes, font=MONO, fg_color=PANEL,
                                         text_color=FG, wrap='none')
        self.bitmap_box.grid(row=1, column=0, sticky='nsew')
        self.bitmap_box.insert('1.0', PRESETS[DEFAULT_PRESET].lstrip('\n'))
        self.bitmap_box.bind('<KeyRelease>', lambda _e: self._refresh())

        self.preview_box = ctk.CTkTextbox(panes, font=MONO_BOLD,
                                          fg_color=PANEL, text_color=ACCENT,
                                          wrap='none')
        self.preview_box.grid(row=1, column=1, sticky='nsew', padx=(8, 0))
        self.preview_box.configure(state='disabled')

    def _current_bitmap(self) -> str:
        return self.bitmap_box.get('1.0', 'end-1c')

    def _current_message(self) -> str:
        return self.message_entry.get()

    def _refresh(self) -> None:
        message = self._current_message()
        bitmap = self._current_bitmap()
        if not message:
            rendered = '(type a message above)'
        else:
            rendered = render(bitmap, message)
        self.preview_box.configure(state='normal')
        self.preview_box.delete('1.0', 'end')
        self.preview_box.insert('1.0', rendered)
        self.preview_box.configure(state='disabled')
        self._update_status(bitmap, message, rendered)

    def _update_status(self, bitmap: str, message: str,
                       rendered: str) -> None:
        lines = bitmap.splitlines()
        rows = len(lines)
        cols = max((len(line) for line in lines), default=0)
        filled = sum(1 for line in lines for c in line if c != ' ')
        msg_len = len(message)
        self.status.configure(
            text=(f'bitmap {rows}×{cols}  •  {filled} filled pixels  •  '
                  f'message length {msg_len}  •  '
                  f'preview {len(rendered)} chars'))

    def _reset_bitmap(self) -> None:
        """Reload the currently-selected preset into the bitmap editor."""
        self._load_preset(self.preset_var.get())

    def _on_preset_change(self, name: str) -> None:
        self._load_preset(name)

    def _load_preset(self, name: str) -> None:
        bitmap = PRESETS.get(name, PRESETS[DEFAULT_PRESET]).lstrip('\n')
        self.bitmap_box.delete('1.0', 'end')
        self.bitmap_box.insert('1.0', bitmap)
        self._refresh()

    def _copy_preview(self) -> None:
        rendered = self.preview_box.get('1.0', 'end-1c')
        self.clipboard_clear()
        self.clipboard_append(rendered)
        self.update()  # Push to system clipboard
        self.status.configure(text='Copied preview to clipboard.')


if __name__ == '__main__':
    BitmapMessageApp().mainloop()
