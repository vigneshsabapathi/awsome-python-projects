"""Dice Roller — CustomTkinter GUI.

Dark-themed desktop UI for tabletop dice notation. Supports standard
notation (`2d6+3`, `1d20`), keep-highest/lowest (`4d6kh3`), multiple
expressions per line separated by commas, quick-roll presets, and a
running history panel.

Run:
    uv run python dice_roller/dice_roller_gui.py
"""
from __future__ import annotations

from collections import deque

import customtkinter as ctk

from dice_roller import (
    DiceNotationError,
    roll,
    split_expressions,
)

TITLE_FONT = ('Segoe UI', 30, 'bold')
LABEL_FONT = ('Segoe UI', 13)
HINT_FONT = ('Segoe UI', 11)
TOTAL_FONT = ('Segoe UI', 64, 'bold')
DIE_FONT = ('Segoe UI', 22, 'bold')
HIST_FONT = ('Consolas', 12)

# Tailwind-ish palette per side count, plus a default.
DIE_COLORS = {
    4:   ('#dc2626', '#ffffff'),  # red
    6:   ('#2563eb', '#ffffff'),  # blue
    8:   ('#16a34a', '#ffffff'),  # green
    10:  ('#9333ea', '#ffffff'),  # purple
    12:  ('#0891b2', '#ffffff'),  # cyan
    20:  ('#ea580c', '#ffffff'),  # orange
    100: ('#db2777', '#ffffff'),  # pink
}
DEFAULT_DIE = ('#475569', '#f8fafc')
DROPPED_DIE = ('#1f2937', '#64748b')

QUICK_ROLLS = ['1d6', '1d20', '2d6', '4d6kh3']
HISTORY_LIMIT = 10


class DiceApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Dice Roller')
        self.geometry('640x780')
        self.minsize(560, 700)
        self.configure(fg_color='#0f172a')

        self.history: deque[str] = deque(maxlen=HISTORY_LIMIT)

        self._build_ui()
        self.bind('<Return>', lambda _e: self._roll())
        self.after(100, lambda: self.entry.focus_force())

    # ---- layout ---------------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='DICE ROLLER', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header,
                     text='Notation: 2d6+3, 1d20, 4d6kh3 — comma-separate for batches',
                     font=HINT_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Input row.
        input_frame = ctk.CTkFrame(self, fg_color='transparent')
        input_frame.pack(side='top', pady=(12, 6), padx=20, fill='x')
        self.entry = ctk.CTkEntry(input_frame, font=('Segoe UI', 18),
                                  height=44, justify='center',
                                  placeholder_text='e.g. 2d6+3, 1d20')
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.entry.bind('<Return>', lambda _e: self._roll())
        self.roll_btn = ctk.CTkButton(input_frame, text='Roll',
                                      width=100, height=44,
                                      font=('Segoe UI', 14, 'bold'),
                                      fg_color='#2563eb', hover_color='#1d4ed8',
                                      command=self._roll)
        self.roll_btn.pack(side='left')

        # Quick-roll preset buttons.
        quick = ctk.CTkFrame(self, fg_color='transparent')
        quick.pack(side='top', pady=(0, 6), padx=20, fill='x')
        ctk.CTkLabel(quick, text='Quick:', font=LABEL_FONT,
                     text_color='#94a3b8').pack(side='left', padx=(0, 8))
        for preset in QUICK_ROLLS:
            btn = ctk.CTkButton(quick, text=preset, width=72, height=32,
                                fg_color='#334155', hover_color='#475569',
                                font=('Segoe UI', 12, 'bold'),
                                command=lambda p=preset: self._roll(p))
            btn.pack(side='left', padx=4)

        # Big total display.
        total_box = ctk.CTkFrame(self, fg_color='#1e293b', corner_radius=14)
        total_box.pack(side='top', pady=(10, 6), padx=20, fill='x')
        self.total_label = ctk.CTkLabel(total_box, text='—',
                                        font=TOTAL_FONT, text_color='#f8fafc')
        self.total_label.pack(pady=(8, 0))
        self.total_caption = ctk.CTkLabel(
            total_box, text='Roll something to begin.',
            font=LABEL_FONT, text_color='#94a3b8')
        self.total_caption.pack(pady=(0, 10))

        # Status / error line.
        self.status = ctk.CTkLabel(self, text='', font=LABEL_FONT,
                                   text_color='#f87171')
        self.status.pack(side='top', pady=(0, 4))

        # Die-card pane (scrollable).
        cards_label = ctk.CTkLabel(self, text='Individual rolls',
                                   font=LABEL_FONT, text_color='#cbd5e1',
                                   anchor='w')
        cards_label.pack(side='top', pady=(4, 2), padx=22, fill='x')
        self.cards_frame = ctk.CTkScrollableFrame(
            self, fg_color='#0b1220', height=160, corner_radius=10)
        self.cards_frame.pack(side='top', padx=20, fill='x')

        # History pane.
        hist_label = ctk.CTkLabel(self, text=f'History (last {HISTORY_LIMIT})',
                                  font=LABEL_FONT, text_color='#cbd5e1',
                                  anchor='w')
        hist_label.pack(side='top', pady=(8, 2), padx=22, fill='x')
        self.history_box = ctk.CTkTextbox(
            self, fg_color='#0b1220', text_color='#e2e8f0',
            font=HIST_FONT, height=180, corner_radius=10)
        self.history_box.pack(side='top', padx=20, pady=(0, 14), fill='both',
                              expand=True)
        self.history_box.configure(state='disabled')

    # ---- actions --------------------------------------------------------

    def _roll(self, override: str | None = None) -> None:
        line = override if override is not None else self.entry.get().strip()
        if not line:
            self._set_status('Enter dice notation, e.g. 2d6+3.')
            return
        try:
            parts = split_expressions(line)
            if not parts:
                raise DiceNotationError('No expressions found.')
            results = [roll(p) for p in parts]
        except DiceNotationError as exc:
            self._set_status(str(exc))
            return

        self._set_status('')

        grand_total = sum(r['total'] for r in results)
        self.total_label.configure(text=str(grand_total))
        if len(results) == 1:
            r = results[0]
            self._set_caption(self._caption_for(r))
        else:
            self._set_caption(f'{len(results)} expressions, grand total')

        self._render_cards(results)
        self._push_history(line, results, grand_total)

        if override is not None:
            self.entry.delete(0, 'end')
            self.entry.insert(0, override)

    def _caption_for(self, r: dict) -> str:
        mod = r['modifier']
        kept_sum = sum(r['kept'])
        if 'keep' in r:
            base = (f"{r['notation']}: kept {r['keep']}{r['keep_n']} "
                    f"sum={kept_sum}")
        else:
            base = f"{r['notation']}: dice sum={kept_sum}"
        if mod:
            base += f' {"+" if mod >= 0 else "-"} {abs(mod)}'
        return base

    def _render_cards(self, results: list[dict]) -> None:
        # Clear previous cards.
        for child in self.cards_frame.winfo_children():
            child.destroy()

        for r in results:
            row = ctk.CTkFrame(self.cards_frame, fg_color='transparent')
            row.pack(fill='x', pady=4, padx=4)

            label = ctk.CTkLabel(
                row, text=f"{r['notation']}  =  {r['total']}",
                font=('Segoe UI', 13, 'bold'), text_color='#e2e8f0',
                anchor='w')
            label.pack(side='top', anchor='w', padx=2)

            cards = ctk.CTkFrame(row, fg_color='transparent')
            cards.pack(side='top', anchor='w', pady=(4, 0))

            kept_set = list(r['kept'])
            for value in r['rolls']:
                bg, fg = DIE_COLORS.get(r['sides'], DEFAULT_DIE)
                # If a kh/kl filter dropped this die, gray it out. Pop matched
                # entries so duplicate-value dice are tracked correctly.
                if value in kept_set:
                    kept_set.remove(value)
                else:
                    bg, fg = DROPPED_DIE
                tile = ctk.CTkLabel(cards, text=str(value),
                                    width=48, height=48,
                                    fg_color=bg, text_color=fg,
                                    corner_radius=10, font=DIE_FONT)
                tile.pack(side='left', padx=3)

            if r['modifier']:
                sign = '+' if r['modifier'] >= 0 else '-'
                ctk.CTkLabel(cards, text=f' {sign} {abs(r["modifier"])}',
                             font=DIE_FONT, text_color='#94a3b8'
                             ).pack(side='left', padx=(6, 0))

    def _push_history(self, line: str, results: list[dict],
                      grand_total: int) -> None:
        summaries = []
        for r in results:
            rolls_str = ','.join(str(x) for x in r['rolls'])
            if 'keep' in r:
                kept = ','.join(str(x) for x in r['kept'])
                summaries.append(
                    f"{r['notation']} [{rolls_str}] -> [{kept}] = {r['total']}")
            else:
                summaries.append(
                    f"{r['notation']} [{rolls_str}] = {r['total']}")
        prefix = f'{grand_total:>5} | ' if len(results) > 1 else ''
        entry = prefix + ' ; '.join(summaries)
        self.history.appendleft(entry)
        self._render_history()

    def _render_history(self) -> None:
        self.history_box.configure(state='normal')
        self.history_box.delete('1.0', 'end')
        for line in self.history:
            self.history_box.insert('end', line + '\n')
        self.history_box.configure(state='disabled')

    def _set_status(self, text: str) -> None:
        self.status.configure(text=text)

    def _set_caption(self, text: str) -> None:
        self.total_caption.configure(text=text)


if __name__ == '__main__':
    DiceApp().mainloop()
