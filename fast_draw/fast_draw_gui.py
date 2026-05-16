"""Fast Draw — CustomTkinter GUI.

Click anywhere on the window (or press Space) when you see DRAW!
Clicking during the WAIT phase counts as a false start.

Run:
    uv run python fast_draw/fast_draw_gui.py
"""
from __future__ import annotations

import threading
import time

import customtkinter as ctk

from fast_draw import Game

# ---------------------------------------------------------------------------
# Colour palette (dark theme)
# ---------------------------------------------------------------------------
BG_DARK   = '#0f172a'
BG_CARD   = '#1e293b'
SLATE     = '#334155'
SLATE_LT  = '#475569'
TEXT_DIM  = '#94a3b8'
TEXT_MAIN = '#f8fafc'
GREEN     = '#22c55e'
RED       = '#ef4444'
YELLOW    = '#eab308'
CYAN      = '#38bdf8'

FONT_HUGE   = ('Segoe UI', 80, 'bold')
FONT_TITLE  = ('Segoe UI', 28, 'bold')
FONT_LABEL  = ('Segoe UI', 13)
FONT_STAT   = ('Segoe UI', 14, 'bold')
FONT_BTN    = ('Segoe UI', 14, 'bold')


class FastDrawApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Fast Draw')
        self.geometry('560x680')
        self.minsize(480, 580)
        self.configure(fg_color=BG_DARK)

        self._game = Game()
        self._active = False   # True while a round is in-flight
        self._draw_ts: float | None = None

        self._build_ui()
        self._reset_display()

        # Bind click on entire window + space
        self.bind('<Button-1>', self._on_trigger)
        self.bind('<space>', self._on_trigger)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Title
        ctk.CTkLabel(self, text='FAST DRAW', font=FONT_TITLE,
                     text_color=CYAN).pack(pady=(20, 2))
        ctk.CTkLabel(self, text='React when you see DRAW!',
                     font=FONT_LABEL, text_color=TEXT_DIM).pack(pady=(0, 8))

        # Big signal label
        self._signal = ctk.CTkLabel(self, text='—', font=FONT_HUGE,
                                    text_color=TEXT_DIM, fg_color='transparent')
        self._signal.pack(expand=True)

        # Sub-message
        self._msg = ctk.CTkLabel(self, text='Press Start to begin',
                                 font=FONT_LABEL, text_color=TEXT_DIM)
        self._msg.pack(pady=(0, 12))

        # Stats panel
        stats_frame = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=12)
        stats_frame.pack(padx=24, pady=(0, 12), fill='x')
        stats_frame.columnconfigure((0, 1, 2, 3), weight=1)

        self._stat_labels: dict[str, ctk.CTkLabel] = {}
        for col, (key, title) in enumerate([
            ('current', 'Last'),
            ('best',    'Best'),
            ('avg10',   'Avg 10'),
            ('fails',   'False Starts'),
        ]):
            ctk.CTkLabel(stats_frame, text=title, font=FONT_LABEL,
                         text_color=TEXT_DIM).grid(row=0, column=col,
                                                    padx=8, pady=(10, 2))
            lbl = ctk.CTkLabel(stats_frame, text='—', font=FONT_STAT,
                               text_color=TEXT_MAIN)
            lbl.grid(row=1, column=col, padx=8, pady=(2, 10))
            self._stat_labels[key] = lbl

        # Start button
        self._btn = ctk.CTkButton(self, text='Start Round',
                                  font=FONT_BTN,
                                  fg_color=SLATE, hover_color=SLATE_LT,
                                  height=44,
                                  command=self._start_round)
        self._btn.pack(padx=24, pady=(0, 20), fill='x')

    # ------------------------------------------------------------------
    # Game flow
    # ------------------------------------------------------------------

    def _reset_display(self) -> None:
        self._set_signal('—', TEXT_DIM)
        self._msg.configure(text='Press Start to begin', text_color=TEXT_DIM)
        self._active = False

    def _set_signal(self, text: str, colour: str) -> None:
        self._signal.configure(text=text, text_color=colour)

    def _start_round(self) -> None:
        if self._active:
            return
        self._active = True
        self._draw_ts = None
        self._btn.configure(state='disabled')
        self._set_signal('WAIT', YELLOW)
        self._msg.configure(text='Hold on...', text_color=TEXT_DIM)

        self._game.start_round()
        threading.Thread(target=self._fire_draw, daemon=True).start()

    def _fire_draw(self) -> None:
        """Background thread: sleep the wait period, then fire DRAW on UI thread."""
        wait = self._game._wait_secs  # type: ignore[attr-defined]
        time.sleep(wait)
        self.after(0, self._show_draw)

    def _show_draw(self) -> None:
        if not self._active:
            return
        self._game.draw_now()
        self._draw_ts = time.perf_counter()
        self._set_signal('DRAW!', GREEN)
        self._msg.configure(text='CLICK or press SPACE!', text_color=GREEN)

    def _on_trigger(self, _event=None) -> None:
        if not self._active:
            return

        if self._game.phase == 'waiting':
            # False start
            result = self._game.false_start_now()
            self._active = False
            self._set_signal('FALSE START', RED)
            self._msg.configure(text='You clicked too early!', text_color=RED)
            self._update_stats(result, false_start=True)
            self.after(1500, self._ready_for_next)

        elif self._game.phase == 'draw' and self._draw_ts is not None:
            elapsed_ms = (time.perf_counter() - self._draw_ts) * 1000
            result = self._game.react(elapsed_ms)
            self._active = False
            self._set_signal(f'{elapsed_ms:.0f} ms', CYAN)
            self._msg.configure(text='Great!', text_color=CYAN)
            self._update_stats(result, false_start=False)
            self.after(1500, self._ready_for_next)

    def _ready_for_next(self) -> None:
        self._set_signal('—', TEXT_DIM)
        self._msg.configure(text='Press Start for next round',
                            text_color=TEXT_DIM)
        self._btn.configure(state='normal')

    def _update_stats(self, result: dict, false_start: bool) -> None:
        if false_start:
            self._stat_labels['current'].configure(text='FAIL', text_color=RED)
        else:
            ms = result['ms']
            self._stat_labels['current'].configure(
                text=f'{ms:.0f} ms', text_color=CYAN)

        best = result['best_ms']
        self._stat_labels['best'].configure(
            text=f'{best:.0f} ms' if best is not None else '—',
            text_color=GREEN)

        # avg over last 10 valid rounds
        valid = [e['ms'] for e in self._game.history[-10:]
                 if not e['false_start']]
        if valid:
            avg = sum(valid) / len(valid)
            self._stat_labels['avg10'].configure(
                text=f'{avg:.0f} ms', text_color=TEXT_MAIN)
        else:
            self._stat_labels['avg10'].configure(text='—', text_color=TEXT_DIM)

        fails = sum(1 for e in self._game.history if e['false_start'])
        self._stat_labels['fails'].configure(
            text=str(fails), text_color=YELLOW if fails else TEXT_DIM)


if __name__ == '__main__':
    FastDrawApp().mainloop()
