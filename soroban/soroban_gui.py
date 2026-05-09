"""Soroban — CustomTkinter GUI.

A wooden-frame Japanese abacus rendered on a Tk Canvas. Click any bead to
slide it toward / away from the reckoning bar; type into the entry to set
the number directly. Number entry and bead state stay in two-way sync.

Run:
    uv run python soroban/soroban_gui.py
"""
from __future__ import annotations

import tkinter as tk
from typing import Callable

import customtkinter as ctk

from soroban import DEFAULT_COLUMNS, render

# ----- Colour palette (dark theme, wooden soroban accents) -----
BG = '#0f172a'
PANEL = '#1e293b'
FRAME_WOOD = '#7c4a1e'
FRAME_WOOD_DARK = '#5a3614'
ROD = '#c4a47c'
BAR = '#facc15'
BEAD = '#f5deb3'
BEAD_DARK = '#a07a44'
BEAD_HL = '#fff7e0'
BEAD_ACTIVE = '#f97316'
BEAD_ACTIVE_DARK = '#9a3412'
TEXT = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'

# ----- Layout constants -----
COL_WIDTH = 56
TOP_DECK_H = 70           # 2 slot heights
BOTTOM_DECK_H = 175       # 5 slot heights
TOP_PAD = 24
BAR_H = 14
BOT_PAD = 24
BEAD_R = 18
FRAME_THICK = 14

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
ENTRY_FONT = ('Segoe UI', 22)


class SorobanApp(ctk.CTk):
    def __init__(self, columns: int = DEFAULT_COLUMNS) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.columns = columns
        self.title('Soroban')
        # Width: 2 frame uprights + columns * COL_WIDTH + padding
        canvas_w = 2 * FRAME_THICK + columns * COL_WIDTH + 20
        canvas_h = (TOP_PAD + TOP_DECK_H + BAR_H + BOTTOM_DECK_H + BOT_PAD
                    + 2 * FRAME_THICK)
        self.canvas_w = canvas_w
        self.canvas_h = canvas_h
        self.geometry(f'{max(560, canvas_w + 60)}x{canvas_h + 220}')
        self.minsize(560, canvas_h + 220)
        self.configure(fg_color=BG)

        # digits[i] for column i (i=0 is leftmost = highest place value)
        self.digits: list[int] = [0] * columns
        # bead_ids per column: dict with 'top' (1 oval id) and 'bottom' (4 ids)
        self.bead_ids: list[dict] = []
        # Suppress entry->canvas updates while we're updating the entry
        # programmatically (prevents recursive updates).
        self._entry_lock = False

        self._build_ui()
        self._draw_frame_and_rods()
        self._draw_beads()
        self._sync_entry_from_digits()

    # ------------------------------------------------------------------
    # UI scaffolding
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='SOROBAN', font=TITLE_FONT,
                     text_color=TEXT).pack(anchor='w')
        ctk.CTkLabel(header,
                     text='Click beads to slide them, or type a number below.',
                     font=LABEL_FONT, text_color=MUTED).pack(anchor='w',
                                                             pady=(2, 0))

        # Bottom controls (packed first so canvas grabs leftover space)
        ctrl = ctk.CTkFrame(self, fg_color='transparent')
        ctrl.pack(side='bottom', pady=(8, 14), padx=20, fill='x')

        self.entry = ctk.CTkEntry(ctrl, font=ENTRY_FONT, height=44,
                                  justify='center',
                                  placeholder_text='enter a number')
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 8))
        self.entry.bind('<KeyRelease>', self._on_entry_change)
        self.entry.bind('<Return>', self._on_entry_change)

        ctk.CTkButton(ctrl, text='Clear', width=80, height=44,
                      fg_color='#334155', hover_color='#475569',
                      command=self._clear).pack(side='left', padx=(0, 6))
        ctk.CTkButton(ctrl, text='+1', width=60, height=44,
                      fg_color='#0e7490', hover_color='#0891b2',
                      command=lambda: self._add(1)).pack(side='left', padx=2)
        ctk.CTkButton(ctrl, text='+10', width=60, height=44,
                      fg_color='#0e7490', hover_color='#0891b2',
                      command=lambda: self._add(10)).pack(side='left', padx=2)

        # Status / value readout
        self.status = ctk.CTkLabel(self, text='value: 0',
                                   font=('Segoe UI', 13),
                                   text_color=ACCENT)
        self.status.pack(side='bottom', pady=(0, 4))

        # Canvas (the soroban itself) — wrap in a panel for the wooden look
        canvas_holder = ctk.CTkFrame(self, fg_color=PANEL,
                                     corner_radius=14)
        canvas_holder.pack(side='top', pady=10, padx=20)

        self.canvas = tk.Canvas(canvas_holder, width=self.canvas_w,
                                height=self.canvas_h, bg=PANEL,
                                highlightthickness=0, bd=0)
        self.canvas.pack(padx=10, pady=10)
        self.canvas.bind('<Button-1>', self._on_canvas_click)

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------
    def _col_x(self, col_index: int) -> int:
        # Column index 0 is leftmost; rod center x:
        return FRAME_THICK + 10 + col_index * COL_WIDTH + COL_WIDTH // 2

    def _bar_y(self) -> int:
        return FRAME_THICK + TOP_PAD + TOP_DECK_H + BAR_H // 2

    def _top_slot_y(self, slot: int) -> int:
        # slot 0 = high (resting), slot 1 = low (active, kissing bar)
        deck_top = FRAME_THICK + TOP_PAD
        slot_h = TOP_DECK_H // 2
        return deck_top + slot * slot_h + slot_h // 2

    def _bot_slot_y(self, slot: int) -> int:
        # slot 0 = top of bottom deck (kisses bar when occupied),
        # slot 4 = bottom of bottom deck (resting position)
        deck_top = FRAME_THICK + TOP_PAD + TOP_DECK_H + BAR_H
        slot_h = BOTTOM_DECK_H // 5
        return deck_top + slot * slot_h + slot_h // 2

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def _draw_frame_and_rods(self) -> None:
        c = self.canvas
        w, h = self.canvas_w, self.canvas_h
        # Outer wooden frame (thick rectangles on all 4 sides)
        c.create_rectangle(0, 0, w, FRAME_THICK,
                           fill=FRAME_WOOD, outline=FRAME_WOOD_DARK)
        c.create_rectangle(0, h - FRAME_THICK, w, h,
                           fill=FRAME_WOOD, outline=FRAME_WOOD_DARK)
        c.create_rectangle(0, 0, FRAME_THICK, h,
                           fill=FRAME_WOOD, outline=FRAME_WOOD_DARK)
        c.create_rectangle(w - FRAME_THICK, 0, w, h,
                           fill=FRAME_WOOD, outline=FRAME_WOOD_DARK)

        # Reckoning bar (yellow-gold, full width inside frame)
        bar_y = self._bar_y()
        c.create_rectangle(FRAME_THICK, bar_y - BAR_H // 2,
                           w - FRAME_THICK, bar_y + BAR_H // 2,
                           fill=BAR, outline='#a16207', width=1)

        # Vertical rods, one per column
        for i in range(self.columns):
            x = self._col_x(i)
            c.create_line(x, FRAME_THICK,
                          x, h - FRAME_THICK,
                          fill=ROD, width=3)

    def _draw_beads(self) -> None:
        # (Re-)create bead ovals for every column based on self.digits.
        # We delete and redraw only the bead items, not the frame/rods.
        for col_dict in self.bead_ids:
            for bid in (col_dict.get('top_ids') or []) + col_dict.get(
                    'bottom_ids', []):
                self.canvas.delete(bid)
        self.bead_ids = []

        for col_index, digit in enumerate(self.digits):
            self._draw_column_beads(col_index, digit)

    def _draw_column_beads(self, col_index: int, digit: int) -> None:
        x = self._col_x(col_index)
        top_active = digit >= 5
        bottom_active = digit % 5

        # Top bead position: slot 0 (high) when inactive, slot 1 (low) active
        top_y = self._top_slot_y(1 if top_active else 0)
        top_id = self._draw_bead(x, top_y, active=top_active)

        bottom_ids = []
        # Active beads occupy slots 0..bottom_active-1 (kissing bar)
        for k in range(bottom_active):
            y = self._bot_slot_y(k)
            bottom_ids.append(self._draw_bead(x, y, active=True))
        # Inactive beads rest at the bottom: slots (5 - n_inactive)..4
        n_inactive = 4 - bottom_active
        for k in range(n_inactive):
            slot = 5 - n_inactive + k
            y = self._bot_slot_y(slot)
            bottom_ids.append(self._draw_bead(x, y, active=False))

        self.bead_ids.append({
            'col': col_index,
            'top_ids': [top_id],
            'bottom_ids': bottom_ids,
        })

    def _draw_bead(self, x: int, y: int, active: bool) -> int:
        fill = BEAD_ACTIVE if active else BEAD
        outline = BEAD_ACTIVE_DARK if active else BEAD_DARK
        # Diamond-ish bead: oval, slightly wider than tall
        bid = self.canvas.create_oval(x - BEAD_R - 3, y - BEAD_R + 4,
                                      x + BEAD_R + 3, y + BEAD_R - 4,
                                      fill=fill, outline=outline, width=2)
        # Highlight strip for a tiny 3D feel
        self.canvas.create_arc(x - BEAD_R - 1, y - BEAD_R + 5,
                               x + BEAD_R + 1, y + BEAD_R - 5,
                               start=30, extent=120,
                               style='arc',
                               outline=BEAD_HL, width=2)
        return bid

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------
    def _on_canvas_click(self, event) -> None:
        # Determine which column was clicked
        x, y = event.x, event.y
        col_index = self._column_for_x(x)
        if col_index is None:
            return
        bar_y = self._bar_y()
        if y < bar_y:
            # Top deck click → toggle the heaven bead
            self._toggle_top(col_index)
        else:
            # Bottom deck click → set bottom_active to the slot the user
            # tapped (closest to bar). Slot index 0..4. We map y to slot:
            slot = self._slot_for_y(y)
            if slot is None:
                return
            digit = self.digits[col_index]
            top_active = 1 if digit >= 5 else 0
            old_bottom = digit % 5
            # Slot semantics for setting:
            #   click slot k near top of deck → "I want k+1 beads up"
            #   click on a resting bead's row → set count so that bead is up
            # If user clicked on the gap or a resting bead, we set the count
            # to the slot index from the bar (slot 0 = 1 bead up, slot 4 =
            # 5 beads up which clamps to 4).
            new_bottom = slot + 1 if slot < 4 else old_bottom
            # If user clicked the existing topmost active bead, slide it down
            # (decrement). This makes the clicks toggle-like.
            if old_bottom > 0 and slot == old_bottom - 1:
                new_bottom = old_bottom - 1
            elif old_bottom == 0 and slot >= old_bottom:
                # Clicked a resting bead → push beads up to reach that slot
                # mapped from the bottom: bottom slot 4 = 0 beads up, slot 3
                # = 1 bead up, etc.
                # Simpler: new_bottom = number of slots ABOVE the click point
                new_bottom = slot + 1 if slot < 4 else 0
            new_bottom = max(0, min(4, new_bottom))
            self._set_digit(col_index, top_active * 5 + new_bottom)

    def _toggle_top(self, col_index: int) -> None:
        digit = self.digits[col_index]
        top_active = 1 if digit >= 5 else 0
        bottom = digit % 5
        new_top = 0 if top_active else 1
        self._set_digit(col_index, new_top * 5 + bottom)

    def _column_for_x(self, x: int) -> int | None:
        for i in range(self.columns):
            cx = self._col_x(i)
            if abs(x - cx) <= COL_WIDTH // 2:
                return i
        return None

    def _slot_for_y(self, y: int) -> int | None:
        deck_top = FRAME_THICK + TOP_PAD + TOP_DECK_H + BAR_H
        slot_h = BOTTOM_DECK_H // 5
        rel = y - deck_top
        if rel < 0:
            return None
        slot = rel // slot_h
        if slot < 0 or slot > 4:
            return None
        return int(slot)

    # ------------------------------------------------------------------
    # State updates
    # ------------------------------------------------------------------
    def _set_digit(self, col_index: int, digit: int) -> None:
        digit = max(0, min(9, digit))
        if self.digits[col_index] == digit:
            return
        self.digits[col_index] = digit
        self._draw_beads()
        self._sync_entry_from_digits()

    def _sync_entry_from_digits(self) -> None:
        n = self._current_value()
        self._entry_lock = True
        self.entry.delete(0, 'end')
        self.entry.insert(0, str(n))
        self._entry_lock = False
        self.status.configure(text=f'value: {n}')

    def _current_value(self) -> int:
        return int(''.join(str(d) for d in self.digits))

    def _on_entry_change(self, _event=None) -> None:
        if self._entry_lock:
            return
        text = self.entry.get().strip()
        if not text:
            new_digits = [0] * self.columns
        else:
            if not text.isdecimal():
                self.status.configure(
                    text='value: (invalid — digits only)')
                return
            n = int(text)
            if n < 0 or len(str(n)) > self.columns:
                self.status.configure(
                    text=f'value: (out of range — max '
                         f'{10 ** self.columns - 1})')
                return
            s = str(n).rjust(self.columns, '0')
            new_digits = [int(c) for c in s]
        if new_digits != self.digits:
            self.digits = new_digits
            self._draw_beads()
        self.status.configure(text=f'value: {self._current_value()}')

    def _clear(self) -> None:
        self.digits = [0] * self.columns
        self._draw_beads()
        self._sync_entry_from_digits()

    def _add(self, delta: int) -> None:
        new = self._current_value() + delta
        if new < 0 or len(str(new)) > self.columns:
            return
        s = str(new).rjust(self.columns, '0')
        self.digits = [int(c) for c in s]
        self._draw_beads()
        self._sync_entry_from_digits()


def main() -> None:
    SorobanApp().mainloop()


if __name__ == '__main__':
    main()
