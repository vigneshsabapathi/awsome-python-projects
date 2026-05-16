"""Water Bucket Puzzle — CustomTkinter GUI.

Two animated buckets on a tk.Canvas, six operation buttons, target entry,
and a Solve button that animates the BFS-shortest sequence. A side panel
explains *why* the puzzle is (un)solvable using gcd / Bezout's identity.

Run:
    uv run python water_bucket/water_bucket_gui.py
"""
from __future__ import annotations

import tkinter as tk
from typing import Optional

import customtkinter as ctk

from water_bucket import (
    OP_LABEL,
    Buckets,
    explain_solvability,
    is_solvable,
    solve,
)


# Tailwind-ish dark palette — matches the bagels GUI for visual consistency.
BG          = '#0f172a'
PANEL       = '#1e293b'
PANEL_DARK  = '#111827'
ACCENT      = '#38bdf8'   # cyan
ACCENT_DIM  = '#0284c7'
WATER       = '#0ea5e9'   # sky-500
WATER_DARK  = '#0369a1'
BUCKET_RIM  = '#cbd5e1'
BUCKET_FILL = '#1f2937'
TEXT        = '#f8fafc'
SUBTEXT     = '#94a3b8'
ERROR       = '#f87171'
SUCCESS     = '#34d399'
WARN        = '#eab308'

TITLE_FONT  = ('Segoe UI', 30, 'bold')
LABEL_FONT  = ('Segoe UI', 13)
BTN_FONT    = ('Segoe UI', 13, 'bold')
MONO_FONT   = ('Consolas', 12)
PANEL_FONT  = ('Consolas', 11)

CANVAS_W    = 460
CANVAS_H    = 360
BUCKET_W    = 130
BUCKET_H    = 280
ANIM_FRAMES = 18
ANIM_DELAY  = 18    # ms per frame  -> ~320 ms per move


class WaterBucketApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Water Bucket Puzzle')
        self.geometry('960x720')
        self.minsize(900, 680)
        self.configure(fg_color=BG)

        # State.
        self.a_cap = 3
        self.b_cap = 5
        self.target = 4
        self.buckets = Buckets(self.a_cap, self.b_cap)
        self.animating = False
        # Cancel token for in-flight animations.
        self._anim_after: Optional[str] = None

        self._build_ui()
        self._refresh_explanation()
        self._redraw(self.buckets.a, self.buckets.b)
        self._set_status('Ready. Try fill_b -> pour_b_to_a -> empty_a … '
                         "or click Solve.")

    # ---------- layout ------------------------------------------------------
    def _build_ui(self) -> None:
        # Header bar.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', pady=(14, 4), padx=20)
        ctk.CTkLabel(header, text='WATER BUCKET PUZZLE',
                     font=TITLE_FONT, text_color=TEXT).pack(side='left')
        ctk.CTkLabel(header, text='Die-Hard-style measuring',
                     font=LABEL_FONT, text_color=SUBTEXT).pack(
            side='left', padx=12, pady=(10, 0))

        # Two-column body: canvas+ops on the left, controls+explainer right.
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=20, pady=8)

        left = ctk.CTkFrame(body, fg_color=PANEL_DARK, corner_radius=14)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10), pady=0)

        right = ctk.CTkFrame(body, fg_color='transparent')
        right.pack(side='right', fill='both', expand=False, padx=(10, 0))

        # ----- left: canvas with the two buckets -------------------------
        self.canvas = tk.Canvas(left, width=CANVAS_W, height=CANVAS_H,
                                bg=PANEL_DARK, highlightthickness=0,
                                bd=0)
        self.canvas.pack(pady=(20, 8), padx=20)

        # Operation buttons under the canvas — 2 rows of 3.
        ops_grid = ctk.CTkFrame(left, fg_color='transparent')
        ops_grid.pack(pady=(4, 14), padx=20, fill='x')
        for i in range(3):
            ops_grid.columnconfigure(i, weight=1)

        def mkbtn(parent: ctk.CTkFrame, text: str, op: str,
                  color: str, hover: str) -> ctk.CTkButton:
            return ctk.CTkButton(parent, text=text,
                                 fg_color=color, hover_color=hover,
                                 text_color=TEXT, font=BTN_FONT, height=38,
                                 command=lambda: self._user_op(op))

        # row 0: fills + empties pair them (A-color, B-color).
        mkbtn(ops_grid, 'Fill A', 'fill_a', '#2563eb', '#1d4ed8').grid(
            row=0, column=0, sticky='ew', padx=4, pady=4)
        mkbtn(ops_grid, 'Empty A', 'empty_a', '#475569', '#334155').grid(
            row=0, column=1, sticky='ew', padx=4, pady=4)
        mkbtn(ops_grid, 'Pour A -> B', 'pour_a_to_b', '#0ea5e9',
              '#0284c7').grid(row=0, column=2, sticky='ew', padx=4, pady=4)

        mkbtn(ops_grid, 'Fill B', 'fill_b', '#7c3aed', '#6d28d9').grid(
            row=1, column=0, sticky='ew', padx=4, pady=4)
        mkbtn(ops_grid, 'Empty B', 'empty_b', '#475569', '#334155').grid(
            row=1, column=1, sticky='ew', padx=4, pady=4)
        mkbtn(ops_grid, 'Pour B -> A', 'pour_b_to_a', '#0ea5e9',
              '#0284c7').grid(row=1, column=2, sticky='ew', padx=4, pady=4)

        # ----- right column: capacity + solve + explainer -----------------
        right.configure(width=320)

        cap_box = ctk.CTkFrame(right, fg_color=PANEL, corner_radius=14)
        cap_box.pack(fill='x', pady=(0, 10))
        ctk.CTkLabel(cap_box, text='Setup', font=BTN_FONT,
                     text_color=TEXT).pack(anchor='w', padx=14, pady=(10, 4))

        for label, attr, default in (
                ('Capacity A', 'a_entry', str(self.a_cap)),
                ('Capacity B', 'b_entry', str(self.b_cap)),
                ('Target  C', 't_entry', str(self.target))):
            row = ctk.CTkFrame(cap_box, fg_color='transparent')
            row.pack(fill='x', padx=14, pady=2)
            ctk.CTkLabel(row, text=label, font=LABEL_FONT, width=90,
                         anchor='w', text_color=SUBTEXT).pack(side='left')
            entry = ctk.CTkEntry(row, font=MONO_FONT, width=80, height=30,
                                 justify='center')
            entry.insert(0, default)
            entry.pack(side='left', padx=(6, 0))
            setattr(self, attr, entry)

        btn_row = ctk.CTkFrame(cap_box, fg_color='transparent')
        btn_row.pack(fill='x', padx=14, pady=(8, 12))
        self.apply_btn = ctk.CTkButton(btn_row, text='Apply / Reset',
                                       fg_color='#475569',
                                       hover_color='#334155',
                                       font=BTN_FONT, height=34,
                                       command=self._apply_setup)
        self.apply_btn.pack(side='left', expand=True, fill='x', padx=(0, 4))
        self.solve_btn = ctk.CTkButton(btn_row, text='Solve',
                                       fg_color=ACCENT,
                                       hover_color=ACCENT_DIM,
                                       text_color='#0b1220',
                                       font=BTN_FONT, height=34,
                                       command=self._solve_animate)
        self.solve_btn.pack(side='right', expand=True, fill='x', padx=(4, 0))

        # Explainer panel — gcd / Bezout writeup.
        exp_box = ctk.CTkFrame(right, fg_color=PANEL, corner_radius=14)
        exp_box.pack(fill='both', expand=True)
        ctk.CTkLabel(exp_box, text='Why solvable?', font=BTN_FONT,
                     text_color=TEXT).pack(anchor='w', padx=14,
                                           pady=(10, 4))
        self.explain = ctk.CTkTextbox(exp_box, font=PANEL_FONT,
                                      fg_color=PANEL_DARK, text_color=TEXT,
                                      wrap='word', activate_scrollbars=False,
                                      border_width=0, height=210)
        self.explain.pack(fill='both', expand=True, padx=12, pady=(0, 12))
        self.explain.configure(state='disabled')

        # Footer: status line.
        self.status = ctk.CTkLabel(self, text='', font=LABEL_FONT,
                                   text_color=SUBTEXT, anchor='w')
        self.status.pack(side='bottom', fill='x', padx=24, pady=(0, 12))

    # ---------- canvas drawing ----------------------------------------------
    def _bucket_rect(self, which: str) -> tuple[int, int, int, int]:
        """Return (x0, y0, x1, y1) for bucket A or B."""
        gap = 60
        total = 2 * BUCKET_W + gap
        x0_a = (CANVAS_W - total) // 2
        y0   = (CANVAS_H - BUCKET_H) // 2 + 10
        if which == 'a':
            return (x0_a, y0, x0_a + BUCKET_W, y0 + BUCKET_H)
        return (x0_a + BUCKET_W + gap, y0,
                x0_a + 2 * BUCKET_W + gap, y0 + BUCKET_H)

    def _draw_bucket(self, which: str, level: float, capacity: int) -> None:
        """Draw one bucket. level is a float in [0, capacity]."""
        x0, y0, x1, y1 = self._bucket_rect(which)
        # Outer rim — left/right walls + base (open top, like a real bucket).
        pad = 4
        # Body fill (empty interior).
        self.canvas.create_rectangle(x0, y0, x1, y1,
                                     fill=BUCKET_FILL,
                                     outline='', width=0)
        # Water level — fills from the bottom up.
        ratio = 0 if capacity <= 0 else max(0.0, min(1.0, level / capacity))
        if ratio > 0:
            water_h = (y1 - y0 - 2 * pad) * ratio
            wy0 = y1 - pad - water_h
            self.canvas.create_rectangle(x0 + pad, wy0,
                                         x1 - pad, y1 - pad,
                                         fill=WATER, outline='')
            # Subtle highlight band at the top of the water.
            self.canvas.create_line(x0 + pad, wy0,
                                    x1 - pad, wy0,
                                    fill='#7dd3fc', width=2)

        # Walls (drawn after the water so the rim sits on top).
        self.canvas.create_line(x0, y0, x0, y1, fill=BUCKET_RIM, width=4)
        self.canvas.create_line(x1, y0, x1, y1, fill=BUCKET_RIM, width=4)
        self.canvas.create_line(x0 - 2, y1, x1 + 2, y1,
                                fill=BUCKET_RIM, width=4)

        # Capacity tick marks (1 per liter, max 12).
        if capacity <= 12:
            for k in range(1, capacity):
                ty = y1 - pad - (y1 - y0 - 2 * pad) * (k / capacity)
                self.canvas.create_line(x0 + pad, ty, x0 + pad + 8, ty,
                                        fill='#475569', width=1)

        # Label + amount text.
        label = f'A   {int(round(level))} / {capacity}' if which == 'a' \
                else f'B   {int(round(level))} / {capacity}'
        self.canvas.create_text((x0 + x1) // 2, y0 - 18,
                                text=label, fill=TEXT,
                                font=('Segoe UI', 13, 'bold'))

    def _redraw(self, a_level: float, b_level: float) -> None:
        self.canvas.delete('all')
        # Draw a target band across both buckets at the target level (if it
        # fits in the larger bucket).
        if 0 < self.target <= max(self.a_cap, self.b_cap):
            self._draw_target_band()
        self._draw_bucket('a', a_level, self.a_cap)
        self._draw_bucket('b', b_level, self.b_cap)

    def _draw_target_band(self) -> None:
        # Dashed line at C across whichever bucket(s) it fits in.
        for which, cap in (('a', self.a_cap), ('b', self.b_cap)):
            if self.target > cap:
                continue
            x0, y0, x1, y1 = self._bucket_rect(which)
            pad = 4
            ratio = self.target / cap
            ty = y1 - pad - (y1 - y0 - 2 * pad) * ratio
            self.canvas.create_line(x0 - 6, ty, x1 + 6, ty,
                                    fill=WARN, width=2, dash=(4, 4))
            self.canvas.create_text(x1 + 18, ty, text=f'C={self.target}',
                                    fill=WARN, font=('Segoe UI', 11, 'bold'),
                                    anchor='w')

    # ---------- user actions ------------------------------------------------
    def _user_op(self, op: str) -> None:
        if self.animating:
            return
        before = self.buckets.state
        self.buckets.apply(op)
        after = self.buckets.state
        self._animate_step(op, before, after, on_done=self._after_user_op)

    def _after_user_op(self) -> None:
        a, b = self.buckets.state
        if a == self.target or b == self.target:
            self._set_status(
                f'Target {self.target} reached! state = ({a}, {b})',
                color=SUCCESS)
        else:
            self._set_status(f'state = ({a}, {b})')

    def _apply_setup(self) -> None:
        if self.animating:
            return
        try:
            a_cap = int(self.a_entry.get())
            b_cap = int(self.b_entry.get())
            target = int(self.t_entry.get())
        except ValueError:
            self._set_status('Capacities and target must be whole numbers.',
                             color=ERROR)
            return
        if a_cap < 1 or b_cap < 1 or target < 0:
            self._set_status(
                'Capacities >= 1 and target >= 0.', color=ERROR)
            return

        self.a_cap = a_cap
        self.b_cap = b_cap
        self.target = target
        self.buckets = Buckets(a_cap, b_cap)
        self._refresh_explanation()
        self._redraw(0, 0)
        self._set_status(
            f'Reset: A={a_cap}, B={b_cap}, target={target}.')

    def _refresh_explanation(self) -> None:
        text = explain_solvability(self.a_cap, self.b_cap, self.target)
        self.explain.configure(state='normal')
        self.explain.delete('1.0', 'end')
        self.explain.insert('1.0', text)
        self.explain.configure(state='disabled')

    def _solve_animate(self) -> None:
        if self.animating:
            return
        # Pull setup straight from entries first.
        self._apply_setup()
        if not is_solvable(self.a_cap, self.b_cap, self.target):
            self._set_status('Unsolvable — see "Why solvable?" panel.',
                             color=ERROR)
            return
        ops = solve(self.a_cap, self.b_cap, self.target)
        if not ops:
            self._set_status('Already there: target is 0.', color=SUCCESS)
            return

        self._set_status(
            f'Solving in {len(ops)} step(s)…')
        # Reset and walk the solution one step at a time.
        self.buckets.reset()
        self._redraw(0, 0)
        self._play(ops, 0)

    def _play(self, ops: list[str], i: int) -> None:
        if i >= len(ops):
            a, b = self.buckets.state
            self._set_status(
                f'Done in {len(ops)} step(s). final state = ({a}, {b})',
                color=SUCCESS)
            return
        op = ops[i]
        before = self.buckets.state
        self.buckets.apply(op)
        after = self.buckets.state

        def next_step() -> None:
            self._set_status(
                f'Step {i + 1}/{len(ops)}: {OP_LABEL[op]}  ->  ({after[0]}, '
                f'{after[1]})')
            self._play(ops, i + 1)

        self._animate_step(op, before, after, on_done=next_step)

    # ---------- animation ---------------------------------------------------
    def _animate_step(self, op: str, before: tuple[int, int],
                      after: tuple[int, int], on_done) -> None:
        """Linearly interpolate water levels from `before` to `after`."""
        self.animating = True
        a0, b0 = before
        a1, b1 = after

        def frame(i: int) -> None:
            t = i / ANIM_FRAMES
            a = a0 + (a1 - a0) * t
            b = b0 + (b1 - b0) * t
            self._redraw(a, b)
            if i < ANIM_FRAMES:
                self._anim_after = self.after(
                    ANIM_DELAY, lambda: frame(i + 1))
            else:
                self._redraw(a1, b1)
                self.animating = False
                on_done()

        frame(0)

    # ---------- helpers -----------------------------------------------------
    def _set_status(self, text: str, color: str = SUBTEXT) -> None:
        self.status.configure(text=text, text_color=color)


if __name__ == '__main__':
    WaterBucketApp().mainloop()
