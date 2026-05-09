"""Sound Mimic — CustomTkinter GUI.

A Simon-says memory game with four big colored tiles. The computer
plays a sequence by flashing tiles + beeping; the player clicks tiles
to repeat. Each round adds one new pad.

Run:
    uv run python sound_mimic/sound_mimic_gui.py
"""
from __future__ import annotations

import platform
import threading
from typing import Callable

import customtkinter as ctk

from sound_mimic import PITCHES, Game


def _is_windows() -> bool:
    return platform.system() == 'Windows'


def _play_tone_blocking(pad: int, n_pads: int, ms: int) -> None:
    """Play the tone for `pad` (blocking). Uses winsound on Windows."""
    pitches = PITCHES[n_pads]
    freq = pitches[pad]
    if _is_windows():
        try:
            import winsound
            winsound.Beep(freq, ms)
            return
        except Exception:
            pass
    # Cross-platform fallback: terminal bell + sleep on the calling thread.
    import sys
    import time
    sys.stdout.write('\a')
    sys.stdout.flush()
    time.sleep(ms / 1000.0)


# Pad colors: idle bg, flash bg, label.
PAD_THEMES = (
    {'idle': '#7f1d1d', 'flash': '#ef4444', 'name': 'RED'},     # 0
    {'idle': '#14532d', 'flash': '#22c55e', 'name': 'GREEN'},   # 1
    {'idle': '#1e3a8a', 'flash': '#3b82f6', 'name': 'BLUE'},    # 2
    {'idle': '#854d0e', 'flash': '#facc15', 'name': 'YELLOW'},  # 3
)

TITLE_FONT = ('Segoe UI', 32, 'bold')
LABEL_FONT = ('Segoe UI', 13)
STATUS_FONT = ('Segoe UI', 14)
ROUND_FONT = ('Segoe UI', 22, 'bold')
TILE_FONT = ('Segoe UI', 16, 'bold')


class SoundMimicApp(ctk.CTk):
    N_PADS = 4

    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Sound Mimic')
        self.geometry('480x600')
        self.minsize(420, 540)
        self.configure(fg_color='#0f172a')

        self.game = Game(n_pads=self.N_PADS)
        self.high_score: int = 0  # in-memory for the session

        # While the computer is playing the sequence, ignore clicks.
        self.busy: bool = False
        # The player's current input position (index into self.game.sequence).
        self.input_index: int = 0

        self.tile_buttons: list[ctk.CTkButton] = []
        self._build_ui()
        self._reset_game(start=False)

    # --- UI construction -------------------------------------------------

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(16, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='SOUND MIMIC', font=TITLE_FONT,
                     text_color='#f8fafc').pack()
        ctk.CTkLabel(
            header,
            text='Watch & listen, then click the tiles in order',
            font=LABEL_FONT, text_color='#94a3b8'
        ).pack(pady=(2, 0))

        # Bottom controls — packed bottom-up so they're always visible.
        self.start_btn = ctk.CTkButton(
            self, text='Start / New Game',
            fg_color='#334155', hover_color='#475569',
            command=self._start_new_game)
        self.start_btn.pack(side='bottom', pady=(4, 12))

        self.status = ctk.CTkLabel(self, text='', font=STATUS_FONT,
                                   text_color='#cbd5e1')
        self.status.pack(side='bottom', pady=(4, 0))

        # Score row.
        score_frame = ctk.CTkFrame(self, fg_color='transparent')
        score_frame.pack(side='top', pady=(8, 4))
        self.round_label = ctk.CTkLabel(
            score_frame, text='Round 0', font=ROUND_FONT,
            text_color='#f8fafc')
        self.round_label.pack(side='left', padx=12)
        self.high_label = ctk.CTkLabel(
            score_frame, text='Best 0', font=ROUND_FONT,
            text_color='#facc15')
        self.high_label.pack(side='left', padx=12)

        # 2x2 tile grid.
        board = ctk.CTkFrame(self, fg_color='transparent')
        board.pack(side='top', pady=12, padx=20, expand=True, fill='both')
        for i in range(2):
            board.grid_rowconfigure(i, weight=1, uniform='row')
            board.grid_columnconfigure(i, weight=1, uniform='col')

        layout = (
            (0, 0, 0),  # pad index, row, col
            (1, 0, 1),
            (2, 1, 0),
            (3, 1, 1),
        )
        for pad, row, col in layout:
            theme = PAD_THEMES[pad]
            btn = ctk.CTkButton(
                board, text=theme['name'],
                fg_color=theme['idle'], hover_color=theme['flash'],
                text_color='#f8fafc', font=TILE_FONT,
                corner_radius=14, height=120, width=120,
                command=self._make_click(pad))
            btn.grid(row=row, column=col, padx=8, pady=8, sticky='nsew')
            self.tile_buttons.append(btn)

    def _make_click(self, pad: int) -> Callable[[], None]:
        return lambda p=pad: self._on_pad_click(p)

    # --- Game flow -------------------------------------------------------

    def _set_status(self, text: str, color: str = '#cbd5e1') -> None:
        self.status.configure(text=text, text_color=color)

    def _refresh_score(self) -> None:
        self.round_label.configure(text=f'Round {self.game.round}')
        self.high_label.configure(text=f'Best {self.high_score}')

    def _start_new_game(self) -> None:
        self._reset_game(start=True)

    def _reset_game(self, start: bool) -> None:
        self.game.reset()
        self.input_index = 0
        self.busy = False
        self._refresh_score()
        if start:
            self._set_status('Get ready…', '#cbd5e1')
            self.after(450, self._begin_round)
        else:
            self._set_status('Press Start to begin.', '#cbd5e1')

    def _begin_round(self) -> None:
        self.game.next_round()
        self.input_index = 0
        self._refresh_score()
        self._set_status(f'Watch — {self.game.round} note(s)…', '#cbd5e1')
        self._play_sequence_async()

    def _play_sequence_async(self) -> None:
        """Play the sequence on a worker thread; UI flashes are scheduled
        back onto Tk via `self.after`. winsound.Beep is blocking so we
        must not run it on the Tk thread."""
        self.busy = True
        # Speed-up twist: trim ms each round.
        round_n = self.game.round
        tone_ms = max(140, 380 - 18 * (round_n - 1))
        gap_ms = max(80, 220 - 18 * (round_n - 1))
        sequence = list(self.game.sequence)

        def worker() -> None:
            import time
            for pad in sequence:
                # Schedule the visual flash on the Tk thread.
                self.after(0, lambda p=pad: self._flash_tile(p, tone_ms))
                # Play the tone (blocks this worker thread, not the UI).
                _play_tone_blocking(pad, self.N_PADS, tone_ms)
                time.sleep(gap_ms / 1000.0)
            self.after(0, self._finish_playback)

        threading.Thread(target=worker, daemon=True).start()

    def _flash_tile(self, pad: int, ms: int) -> None:
        theme = PAD_THEMES[pad]
        btn = self.tile_buttons[pad]
        btn.configure(fg_color=theme['flash'])
        # Restore after the tone duration.
        self.after(ms, lambda: btn.configure(fg_color=theme['idle']))

    def _finish_playback(self) -> None:
        self.busy = False
        self._set_status(
            f'Your turn — repeat {self.game.round} note(s).', '#34d399')

    def _on_pad_click(self, pad: int) -> None:
        if self.busy:
            return
        if self.game.round == 0:
            # No game in progress yet.
            self._set_status('Press Start to begin.', '#facc15')
            return

        # Visual + audio feedback for the click.
        self._flash_tile(pad, 200)
        threading.Thread(
            target=_play_tone_blocking, args=(pad, self.N_PADS, 200),
            daemon=True).start()

        expected = self.game.sequence[self.input_index]
        if pad != expected:
            self._game_over()
            return

        self.input_index += 1
        if self.input_index >= len(self.game.sequence):
            # Round cleared.
            if self.game.round > self.high_score:
                self.high_score = self.game.round
                self._refresh_score()
            self._set_status('Nice! Next round…', '#34d399')
            self.after(700, self._begin_round)

    def _game_over(self) -> None:
        self.busy = True
        score = self.game.round - 1
        if self.game.round > self.high_score:
            # Edge case: shouldn't usually trigger here, but keep symmetric.
            self.high_score = score
        self._refresh_score()
        self._set_status(
            f'Wrong note! Final score: {score}. Press Start to try again.',
            '#f87171')


if __name__ == '__main__':
    SoundMimicApp().mainloop()
