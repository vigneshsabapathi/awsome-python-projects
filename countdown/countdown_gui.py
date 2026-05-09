"""Countdown — CustomTkinter GUI.

Big seven-segment ASCII display, minutes/seconds inputs, Start/Pause/Reset,
and an optional bell at zero. Color shifts red when fewer than 10 seconds
remain. Includes an optional Pomodoro mode (25m work / 5m break cycle).

Run:
    uv run python countdown/countdown_gui.py
"""
from __future__ import annotations

import customtkinter as ctk

from countdown import render_clock

try:
    import winsound  # type: ignore[import-not-found]
    _HAS_WINSOUND = True
except ImportError:
    _HAS_WINSOUND = False


DISPLAY_FONT = ('Consolas', 28, 'bold')
LABEL_FONT = ('Segoe UI', 13)
TITLE_FONT = ('Segoe UI', 32, 'bold')
STATUS_FONT = ('Segoe UI', 14)
BTN_FONT = ('Segoe UI', 13, 'bold')

NORMAL_COLOR = '#38bdf8'  # cyan
WARN_COLOR = '#f87171'    # red — when remaining < 10s
DONE_COLOR = '#34d399'    # green — at zero


class CountdownApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Countdown')
        self.geometry('560x520')
        self.minsize(520, 480)
        self.configure(fg_color='#0f172a')

        # State.
        self.total_seconds: int = 60
        self.remaining: int = 60
        self.running: bool = False
        self.beep_at_zero: ctk.BooleanVar = ctk.BooleanVar(value=True)
        self.pomodoro: ctk.BooleanVar = ctk.BooleanVar(value=False)
        self.pomo_phase: str = 'work'   # 'work' or 'break'
        self.pomo_cycle: int = 1
        self.pomo_total: int = 4
        self._tick_job: str | None = None

        self._build_ui()
        self._refresh_display()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='COUNTDOWN', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(header,
                     text='Seven-segment ASCII timer',
                     font=LABEL_FONT, text_color='#94a3b8').pack(pady=(2, 0))

        # Display — uses a CTkLabel with monospace font, multi-line.
        display_frame = ctk.CTkFrame(self, fg_color='#111827',
                                     corner_radius=12)
        display_frame.pack(side='top', pady=14, padx=20, fill='x')
        self.display = ctk.CTkLabel(display_frame, text='', font=DISPLAY_FONT,
                                    text_color=NORMAL_COLOR, justify='center')
        self.display.pack(pady=18, padx=18)

        # Status (under display).
        self.status = ctk.CTkLabel(self, text='Ready.', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='top', pady=(0, 8))

        # Inputs row.
        input_frame = ctk.CTkFrame(self, fg_color='transparent')
        input_frame.pack(side='top', pady=(4, 4), padx=20)
        ctk.CTkLabel(input_frame, text='Min', font=LABEL_FONT,
                     text_color='#94a3b8').pack(side='left', padx=(0, 4))
        self.min_entry = ctk.CTkEntry(input_frame, width=64, justify='center',
                                      font=('Segoe UI', 14))
        self.min_entry.insert(0, '1')
        self.min_entry.pack(side='left', padx=(0, 12))
        ctk.CTkLabel(input_frame, text='Sec', font=LABEL_FONT,
                     text_color='#94a3b8').pack(side='left', padx=(0, 4))
        self.sec_entry = ctk.CTkEntry(input_frame, width=64, justify='center',
                                      font=('Segoe UI', 14))
        self.sec_entry.insert(0, '0')
        self.sec_entry.pack(side='left')

        # Toggles row.
        toggles = ctk.CTkFrame(self, fg_color='transparent')
        toggles.pack(side='top', pady=(8, 4))
        ctk.CTkCheckBox(toggles, text='Beep at zero', font=LABEL_FONT,
                        variable=self.beep_at_zero).pack(side='left', padx=8)
        ctk.CTkCheckBox(toggles, text='Pomodoro (25/5)', font=LABEL_FONT,
                        variable=self.pomodoro,
                        command=self._on_pomodoro_toggle).pack(
            side='left', padx=8)

        # Buttons row.
        btns = ctk.CTkFrame(self, fg_color='transparent')
        btns.pack(side='top', pady=(10, 14))
        self.start_btn = ctk.CTkButton(btns, text='Start', width=96,
                                       font=BTN_FONT, fg_color='#16a34a',
                                       hover_color='#15803d',
                                       command=self._on_start)
        self.start_btn.pack(side='left', padx=6)
        self.pause_btn = ctk.CTkButton(btns, text='Pause', width=96,
                                       font=BTN_FONT, fg_color='#ca8a04',
                                       hover_color='#a16207',
                                       command=self._on_pause)
        self.pause_btn.pack(side='left', padx=6)
        self.reset_btn = ctk.CTkButton(btns, text='Reset', width=96,
                                       font=BTN_FONT, fg_color='#334155',
                                       hover_color='#475569',
                                       command=self._on_reset)
        self.reset_btn.pack(side='left', padx=6)

    # ------------------------------------------------------------- helpers
    def _parse_inputs(self) -> int | None:
        try:
            mins = int(self.min_entry.get() or '0')
            secs = int(self.sec_entry.get() or '0')
        except ValueError:
            self._set_status('Enter integers only.', WARN_COLOR)
            return None
        if mins < 0 or secs < 0:
            self._set_status('Values must be non-negative.', WARN_COLOR)
            return None
        total = mins * 60 + secs
        if total <= 0:
            self._set_status('Set a duration greater than zero.', WARN_COLOR)
            return None
        return total

    def _refresh_display(self) -> None:
        self.display.configure(text=render_clock(self.remaining))
        if self.remaining <= 0:
            color = DONE_COLOR
        elif self.remaining < 10:
            color = WARN_COLOR
        else:
            color = NORMAL_COLOR
        self.display.configure(text_color=color)

    def _set_status(self, text: str, color: str = '#cbd5e1') -> None:
        self.status.configure(text=text, text_color=color)

    def _on_pomodoro_toggle(self) -> None:
        if self.pomodoro.get():
            self.min_entry.delete(0, 'end'); self.min_entry.insert(0, '25')
            self.sec_entry.delete(0, 'end'); self.sec_entry.insert(0, '0')
            self._set_status('Pomodoro: 25m work / 5m break × 4.')
        else:
            self._set_status('Manual mode.')

    # ----------------------------------------------------------- callbacks
    def _on_start(self) -> None:
        if self.running:
            return
        if self.remaining <= 0:
            total = self._parse_inputs()
            if total is None:
                return
            self.total_seconds = total
            self.remaining = total
            if self.pomodoro.get():
                self.pomo_phase = 'work'
                self.pomo_cycle = 1
        self.running = True
        self._set_status(self._phase_label() + ' — running…')
        self._tick()

    def _on_pause(self) -> None:
        if not self.running:
            return
        self.running = False
        if self._tick_job is not None:
            self.after_cancel(self._tick_job)
            self._tick_job = None
        self._set_status('Paused.', '#fbbf24')

    def _on_reset(self) -> None:
        self.running = False
        if self._tick_job is not None:
            self.after_cancel(self._tick_job)
            self._tick_job = None
        total = self._parse_inputs()
        if total is None:
            return
        self.total_seconds = total
        self.remaining = total
        if self.pomodoro.get():
            self.pomo_phase = 'work'
            self.pomo_cycle = 1
        self._refresh_display()
        self._set_status('Reset.')

    def _phase_label(self) -> str:
        if not self.pomodoro.get():
            return 'Countdown'
        return f'Pomodoro {self.pomo_phase} ({self.pomo_cycle}/{self.pomo_total})'

    def _beep(self) -> None:
        if not self.beep_at_zero.get():
            return
        if _HAS_WINSOUND:
            try:
                winsound.Beep(880, 220)
            except Exception:
                print('\a', end='', flush=True)
        else:
            print('\a', end='', flush=True)

    def _advance_pomodoro(self) -> bool:
        """Return True if a new phase was started; False if all cycles done."""
        if self.pomo_phase == 'work':
            self.pomo_phase = 'break'
            self.total_seconds = 5 * 60
        else:
            self.pomo_phase = 'work'
            self.pomo_cycle += 1
            if self.pomo_cycle > self.pomo_total:
                return False
            self.total_seconds = 25 * 60
        self.remaining = self.total_seconds
        return True

    def _tick(self) -> None:
        self._refresh_display()
        if self.remaining <= 0:
            self._beep()
            if self.pomodoro.get() and self._advance_pomodoro():
                self._refresh_display()
                self._set_status(self._phase_label() + ' — running…')
                self._tick_job = self.after(1000, self._tick)
                return
            self.running = False
            self._set_status('Time is up!', DONE_COLOR)
            return
        self.remaining -= 1
        if self.running:
            self._tick_job = self.after(1000, self._tick)


if __name__ == '__main__':
    CountdownApp().mainloop()
