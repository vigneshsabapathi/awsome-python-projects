"""Tower of Hanoi — CustomTkinter GUI.

Dark-theme desktop UI with three vertical pegs on a tk.Canvas. Click a
peg to pick it up as the source, click another peg to drop the top disk
on it. Auto-solve runs the optimal recursive sequence with animation.

Run:
    uv run python hanoi/hanoi_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from hanoi import PEGS, Hanoi, solve_iterative, solve_recursive

# --- Theme -----------------------------------------------------------------

BG = '#0f172a'
PANEL = '#1e293b'
PEG_COLOR = '#475569'
BASE_COLOR = '#334155'
LABEL_COLOR = '#cbd5e1'
HIGHLIGHT = '#38bdf8'

# Disk colors cycle for n_disks up to 10. Largest disk uses index 0.
DISK_COLORS = (
    '#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16',
    '#22c55e', '#14b8a6', '#06b6d4', '#3b82f6', '#a855f7',
)

TITLE_FONT = ('Segoe UI', 28, 'bold')
LABEL_FONT = ('Segoe UI', 13)
STATUS_FONT = ('Segoe UI', 14)


class HanoiApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Tower of Hanoi')
        self.geometry('820x640')
        self.minsize(720, 580)
        self.configure(fg_color=BG)

        self.n_disks = 4
        self.game = Hanoi(self.n_disks)
        self.selected_peg: str | None = None
        self.solving = False  # auto-solve in progress
        self.use_iterative = False
        self._after_id: str | None = None

        # Canvas geometry (set on first draw).
        self.peg_x: dict[str, int] = {}
        self.base_y = 0
        self.peg_top_y = 0
        self.disk_unit = 0  # pixels per disk-size unit (width)
        self.disk_height = 0

        self._build_ui()
        self._draw_board()

    # --- UI construction --------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='TOWER OF HANOI', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(
            header,
            text='Click a peg to select source, click another to drop. '
                 'Optimal = 2^N − 1 moves.',
            font=LABEL_FONT, text_color='#94a3b8',
        ).pack(pady=(2, 0))

        # Bottom controls.
        controls = ctk.CTkFrame(self, fg_color='transparent')
        controls.pack(side='bottom', pady=(6, 14), padx=20, fill='x')

        self.status = ctk.CTkLabel(
            controls, text='', font=STATUS_FONT, text_color=LABEL_COLOR)
        self.status.pack(side='top', pady=(0, 8))

        slider_row = ctk.CTkFrame(controls, fg_color='transparent')
        slider_row.pack(side='top', pady=(0, 8))
        ctk.CTkLabel(slider_row, text='Disks:', font=LABEL_FONT,
                     text_color=LABEL_COLOR).pack(side='left', padx=(0, 8))
        self.slider = ctk.CTkSlider(
            slider_row, from_=3, to=10, number_of_steps=7,
            width=240, command=self._on_slider)
        self.slider.set(self.n_disks)
        self.slider.pack(side='left')
        self.disks_label = ctk.CTkLabel(
            slider_row, text=str(self.n_disks),
            font=('Segoe UI', 14, 'bold'), text_color='#f8fafc', width=28)
        self.disks_label.pack(side='left', padx=(8, 0))

        self.method_switch = ctk.CTkSwitch(
            slider_row, text='Iterative (parity bit)',
            command=self._on_method_toggle, font=LABEL_FONT)
        self.method_switch.pack(side='left', padx=(20, 0))

        button_row = ctk.CTkFrame(controls, fg_color='transparent')
        button_row.pack(side='top')
        self.new_btn = ctk.CTkButton(
            button_row, text='New', width=90, fg_color='#334155',
            hover_color='#475569', command=self._new_game)
        self.new_btn.pack(side='left', padx=4)
        self.solve_btn = ctk.CTkButton(
            button_row, text='Auto-Solve', width=120,
            fg_color='#0ea5e9', hover_color='#0284c7',
            command=self._auto_solve)
        self.solve_btn.pack(side='left', padx=4)
        self.stop_btn = ctk.CTkButton(
            button_row, text='Stop', width=90, fg_color='#ef4444',
            hover_color='#dc2626', command=self._stop_solve, state='disabled')
        self.stop_btn.pack(side='left', padx=4)

        # Canvas fills remaining space.
        self.canvas = ctk.CTkCanvas(
            self, bg=PANEL, highlightthickness=0, bd=0)
        self.canvas.pack(side='top', fill='both', expand=True,
                         padx=20, pady=(8, 4))
        self.canvas.bind('<Button-1>', self._on_canvas_click)
        self.canvas.bind('<Configure>', lambda _e: self._draw_board())

    # --- Drawing ----------------------------------------------------------

    def _compute_geometry(self) -> None:
        w = max(self.canvas.winfo_width(), 200)
        h = max(self.canvas.winfo_height(), 200)
        # Three pegs evenly spaced.
        self.peg_x = {peg: int(w * (i + 1) / 4)
                      for i, peg in enumerate(PEGS)}
        margin_bottom = 40
        margin_top = 40
        self.base_y = h - margin_bottom
        self.peg_top_y = margin_top
        # Disk geometry.
        self.disk_height = max(10, min(28, (h - margin_top - margin_bottom)
                                       // (self.n_disks + 2)))
        # Largest disk width fits comfortably between pegs.
        peg_pitch = w // 4
        max_disk_width = int(peg_pitch * 0.9)
        self.disk_unit = max(6, max_disk_width // self.n_disks)

    def _draw_board(self) -> None:
        self.canvas.delete('all')
        self._compute_geometry()
        w = self.canvas.winfo_width()

        # Base rail.
        self.canvas.create_rectangle(
            20, self.base_y, w - 20, self.base_y + 8,
            fill=BASE_COLOR, outline='')

        # Pegs.
        for peg, x in self.peg_x.items():
            color = HIGHLIGHT if peg == self.selected_peg else PEG_COLOR
            self.canvas.create_rectangle(
                x - 4, self.peg_top_y, x + 4, self.base_y,
                fill=color, outline='')
            # Peg label below the base.
            self.canvas.create_text(
                x, self.base_y + 22, text=peg,
                fill=LABEL_COLOR, font=('Segoe UI', 14, 'bold'))

        # Disks.
        for peg, x in self.peg_x.items():
            stack = self.game.pegs[peg]
            for level, disk in enumerate(stack):
                width = disk * self.disk_unit
                top = self.base_y - (level + 1) * self.disk_height
                bottom = top + self.disk_height - 2
                color = DISK_COLORS[(disk - 1) % len(DISK_COLORS)]
                self.canvas.create_rectangle(
                    x - width // 2, top, x + width // 2, bottom,
                    fill=color, outline='#0f172a', width=1)
                # Disk size number, drawn only when there's room.
                if self.disk_height >= 14:
                    self.canvas.create_text(
                        x, (top + bottom) // 2, text=str(disk),
                        fill='#0f172a',
                        font=('Segoe UI', max(8, self.disk_height - 8),
                              'bold'))

    # --- Interaction ------------------------------------------------------

    def _on_canvas_click(self, event) -> None:
        if self.solving:
            return
        peg = self._peg_at(event.x)
        if peg is None:
            return
        if self.selected_peg is None:
            if not self.game.pegs[peg]:
                self._set_status(f'Peg {peg} is empty.', '#f87171')
                return
            self.selected_peg = peg
            self._draw_board()
            self._set_status(
                f'Source: {peg} (top disk {self.game.top(peg)}). '
                'Click destination.', LABEL_COLOR)
        else:
            src, dst = self.selected_peg, peg
            self.selected_peg = None
            if src == dst:
                self._draw_board()
                self._set_status('Move cancelled.', LABEL_COLOR)
                return
            ok = self.game.move(src, dst)
            self._draw_board()
            if not ok:
                self._set_status(
                    f'Illegal: cannot place {self.game.top(src)} on '
                    f'{self.game.top(dst)}.', '#f87171')
                return
            self._post_move()

    def _peg_at(self, x: int) -> str | None:
        # Snap to nearest peg if click lands within the peg's column.
        if not self.peg_x:
            return None
        closest = min(self.peg_x, key=lambda p: abs(self.peg_x[p] - x))
        # Tolerance = half the inter-peg distance.
        half_pitch = self.canvas.winfo_width() // 8
        if abs(self.peg_x[closest] - x) <= half_pitch:
            return closest
        return None

    def _post_move(self) -> None:
        if self.game.is_solved('C'):
            self._set_status(
                f'Solved in {self.game.move_count} moves '
                f'(optimal = {(1 << self.n_disks) - 1}).', '#34d399')
        else:
            self._set_status(
                f'Move #{self.game.move_count}. '
                f'Goal: stack all on C.', LABEL_COLOR)

    # --- Auto-solve -------------------------------------------------------

    def _auto_solve(self) -> None:
        if self.solving:
            return
        # Reset to a fresh starting position so the optimal count is honest.
        self.game.reset()
        self.selected_peg = None
        self._draw_board()
        if self.use_iterative:
            moves = solve_iterative(self.n_disks, 'A', 'B', 'C')
        else:
            moves = solve_recursive(self.n_disks, 'A', 'B', 'C')
        delay_ms = max(60, min(500, 1500 // max(1, len(moves))))
        self.solving = True
        self.solve_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.new_btn.configure(state='disabled')
        self._run_step(moves, 0, delay_ms)

    def _run_step(self, moves, idx: int, delay_ms: int) -> None:
        if not self.solving or idx >= len(moves):
            self._finish_solve()
            return
        s, d = moves[idx]
        self.game.move(s, d)
        self._draw_board()
        self._set_status(
            f'Auto-solving — step {idx + 1}/{len(moves)}: {s} → {d}',
            HIGHLIGHT)
        self._after_id = self.after(
            delay_ms, lambda: self._run_step(moves, idx + 1, delay_ms))

    def _finish_solve(self) -> None:
        self.solving = False
        self.solve_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.new_btn.configure(state='normal')
        if self.game.is_solved('C'):
            self._set_status(
                f'Auto-solved in {self.game.move_count} moves '
                f'(optimal = {(1 << self.n_disks) - 1}).', '#34d399')

    def _stop_solve(self) -> None:
        self.solving = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None
        self._finish_solve()
        self._set_status('Auto-solve stopped.', '#f87171')

    # --- Controls ---------------------------------------------------------

    def _on_slider(self, value: float) -> None:
        n = int(round(value))
        if n == self.n_disks:
            return
        self.n_disks = n
        self.disks_label.configure(text=str(n))
        self._new_game()

    def _on_method_toggle(self) -> None:
        self.use_iterative = bool(self.method_switch.get())
        method = 'iterative parity' if self.use_iterative else 'recursive'
        self._set_status(f'Solver: {method}.', LABEL_COLOR)

    def _new_game(self) -> None:
        if self.solving:
            self._stop_solve()
        self.game = Hanoi(self.n_disks)
        self.selected_peg = None
        self._draw_board()
        self._set_status(
            f'{self.n_disks} disks. Optimal = '
            f'{(1 << self.n_disks) - 1} moves.', LABEL_COLOR)

    def _set_status(self, text: str, color: str = LABEL_COLOR) -> None:
        self.status.configure(text=text, text_color=color)


if __name__ == '__main__':
    HanoiApp().mainloop()
