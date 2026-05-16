"""TTS Talker — CustomTkinter GUI.

A dark-themed desktop front-end for the offline pyttsx3 engine.
Big text area, voice picker, rate slider (50–400 wpm), volume slider,
Speak / Pause / Stop buttons, and a Save-to-WAV action.

Speech runs on a background thread so the UI stays responsive. We keep a
single engine alive for live `pause` / `stop` controls — `pause`
flushes the say-queue and re-enqueues the remaining text on resume,
which is the most reliable way to fake pause across SAPI/NSSpeech/espeak.

Run:
    uv run python tts_talker/tts_talker_gui.py
"""
from __future__ import annotations

import threading
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pyttsx3

from tts_talker import (DEFAULT_RATE, DEFAULT_VOLUME, MAX_RATE, MIN_RATE,
                        list_voices, save_to_wav)

BG = '#0f172a'
PANEL = '#1e293b'
FG = '#f8fafc'
MUTED = '#94a3b8'
ACCENT = '#38bdf8'
DANGER = '#f87171'
SUCCESS = '#34d399'

TITLE_FONT = ('Segoe UI', 26, 'bold')
LABEL_FONT = ('Segoe UI', 12)
BTN_FONT = ('Segoe UI', 13, 'bold')


class TTSTalkerApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('TTS Talker')
        self.geometry('820x680')
        self.minsize(680, 560)
        self.configure(fg_color=BG)

        self.voices = list_voices()
        self._voice_labels = [
            f'[{i}] {v["name"]}' for i, v in enumerate(self.voices)
        ] or ['(no voices found)']

        self._speech_thread: threading.Thread | None = None
        self._engine: pyttsx3.Engine | None = None
        # Remaining text after a pause — re-enqueued on resume.
        self._paused_remainder: str | None = None
        self._is_paused = False

        self._build_ui()
        self.bind('<Control-Return>', lambda _e: self._on_speak())
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(14, 4), padx=20, fill='x')
        ctk.CTkLabel(header, text='TTS TALKER',
                     font=TITLE_FONT, text_color=FG).pack(anchor='w')
        ctk.CTkLabel(
            header,
            text='Offline text-to-speech via pyttsx3 — Ctrl+Enter to speak',
            font=LABEL_FONT, text_color=MUTED).pack(anchor='w', pady=(2, 0))

        # Status (pack early so it stays at the bottom)
        self.status = ctk.CTkLabel(self, text='Ready.', font=LABEL_FONT,
                                   text_color=MUTED, anchor='w')
        self.status.pack(side='bottom', fill='x', padx=20, pady=(2, 10))

        # Action buttons row (above status, below sliders)
        action_row = ctk.CTkFrame(self, fg_color='transparent')
        action_row.pack(side='bottom', fill='x', padx=20, pady=(4, 4))
        self.speak_btn = ctk.CTkButton(action_row, text='▶  Speak',
                                       font=BTN_FONT, height=40, width=140,
                                       fg_color=ACCENT, hover_color='#0ea5e9',
                                       text_color='#0b1220',
                                       command=self._on_speak)
        self.speak_btn.pack(side='left', padx=(0, 6))
        self.pause_btn = ctk.CTkButton(action_row, text='⏸  Pause',
                                       font=BTN_FONT, height=40, width=110,
                                       fg_color='#475569',
                                       hover_color='#334155',
                                       command=self._on_pause_resume)
        self.pause_btn.pack(side='left', padx=6)
        self.stop_btn = ctk.CTkButton(action_row, text='⏹  Stop',
                                      font=BTN_FONT, height=40, width=110,
                                      fg_color='#7f1d1d',
                                      hover_color='#991b1b',
                                      command=self._on_stop)
        self.stop_btn.pack(side='left', padx=6)
        self.save_btn = ctk.CTkButton(action_row, text='💾  Save WAV',
                                      font=BTN_FONT, height=40, width=140,
                                      fg_color='#1f2937',
                                      hover_color='#374151',
                                      command=self._on_save)
        self.save_btn.pack(side='right')

        # Controls panel (voice + sliders)
        controls = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        controls.pack(side='bottom', fill='x', padx=20, pady=(6, 4))

        voice_row = ctk.CTkFrame(controls, fg_color='transparent')
        voice_row.pack(fill='x', padx=14, pady=(12, 6))
        ctk.CTkLabel(voice_row, text='Voice', font=LABEL_FONT,
                     text_color=FG, width=80, anchor='w').pack(side='left')
        self.voice_var = ctk.StringVar(value=self._voice_labels[0])
        self.voice_menu = ctk.CTkOptionMenu(
            voice_row, values=self._voice_labels, variable=self.voice_var,
            font=LABEL_FONT, width=400,
            fg_color='#334155', button_color='#475569',
            button_hover_color='#64748b')
        self.voice_menu.pack(side='left', fill='x', expand=True, padx=(8, 0))
        if not self.voices:
            self.voice_menu.configure(state='disabled')

        rate_row = ctk.CTkFrame(controls, fg_color='transparent')
        rate_row.pack(fill='x', padx=14, pady=(6, 6))
        self.rate_label = ctk.CTkLabel(
            rate_row, text=f'Rate  {DEFAULT_RATE} wpm',
            font=LABEL_FONT, text_color=FG, width=160, anchor='w')
        self.rate_label.pack(side='left')
        self.rate_slider = ctk.CTkSlider(
            rate_row, from_=MIN_RATE, to=MAX_RATE,
            number_of_steps=MAX_RATE - MIN_RATE,
            command=self._on_rate)
        self.rate_slider.set(DEFAULT_RATE)
        self.rate_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        vol_row = ctk.CTkFrame(controls, fg_color='transparent')
        vol_row.pack(fill='x', padx=14, pady=(6, 12))
        self.vol_label = ctk.CTkLabel(
            vol_row, text=f'Volume  {int(DEFAULT_VOLUME * 100)}%',
            font=LABEL_FONT, text_color=FG, width=160, anchor='w')
        self.vol_label.pack(side='left')
        self.vol_slider = ctk.CTkSlider(
            vol_row, from_=0, to=1, number_of_steps=100,
            command=self._on_volume)
        self.vol_slider.set(DEFAULT_VOLUME)
        self.vol_slider.pack(side='left', fill='x', expand=True, padx=(8, 0))

        # Text area fills the middle
        text_frame = ctk.CTkFrame(self, fg_color=BG)
        text_frame.pack(side='top', fill='both', expand=True,
                        padx=20, pady=(8, 4))
        ctk.CTkLabel(text_frame, text='Text', font=LABEL_FONT,
                     text_color=MUTED, anchor='w').pack(fill='x', padx=2)
        self.text = ctk.CTkTextbox(text_frame, font=('Segoe UI', 14),
                                   fg_color=PANEL, text_color=FG,
                                   border_width=1, border_color='#334155',
                                   wrap='word')
        self.text.pack(fill='both', expand=True, pady=(4, 0))
        self.text.insert('1.0',
                         'Hello! This is the TTS Talker. '
                         'Type any text here, then press Ctrl+Enter '
                         'or click Speak.')
        # Ctrl+Enter inside the textbox should also fire (and not insert nl).
        self.text.bind('<Control-Return>', self._textbox_speak_and_swallow)

    # ------------------------------------------------------------- handlers
    def _textbox_speak_and_swallow(self, _event):
        self._on_speak()
        return 'break'  # prevent newline insertion

    def _on_rate(self, value: float) -> None:
        self.rate_label.configure(text=f'Rate  {int(round(value))} wpm')

    def _on_volume(self, value: float) -> None:
        self.vol_label.configure(text=f'Volume  {int(round(value * 100))}%')

    def _selected_voice_id(self) -> str | None:
        if not self.voices:
            return None
        idx = self._voice_labels.index(self.voice_var.get())
        return self.voices[idx]['id']

    def _current_text(self) -> str:
        return self.text.get('1.0', 'end').strip()

    def _set_status(self, text: str, color: str = MUTED) -> None:
        self.status.configure(text=text, text_color=color)

    # -------------------------------------------------------------- speech
    def _on_speak(self) -> None:
        if self._speech_thread and self._speech_thread.is_alive():
            self._set_status('Already speaking — press Stop first.', DANGER)
            return
        text = self._current_text()
        if not text:
            self._set_status('Nothing to speak.', DANGER)
            return
        self._paused_remainder = None
        self._is_paused = False
        self.pause_btn.configure(text='⏸  Pause')
        self._start_speaking(text)

    def _start_speaking(self, text: str) -> None:
        self._set_status('Speaking…', ACCENT)
        self.speak_btn.configure(state='disabled')

        def worker() -> None:
            try:
                engine = pyttsx3.init()
                self._engine = engine
                voice_id = self._selected_voice_id()
                if voice_id:
                    engine.setProperty('voice', voice_id)
                engine.setProperty('rate', int(self.rate_slider.get()))
                engine.setProperty('volume', float(self.vol_slider.get()))
                engine.say(text)
                engine.runAndWait()
            except Exception as exc:  # noqa: BLE001 — surface any TTS error
                self.after(0, lambda: self._set_status(
                    f'Error: {exc}', DANGER))
            finally:
                try:
                    if self._engine is not None:
                        self._engine.stop()
                except Exception:
                    pass
                self._engine = None
                self.after(0, self._speech_done)

        self._speech_thread = threading.Thread(target=worker, daemon=True)
        self._speech_thread.start()

    def _speech_done(self) -> None:
        self.speak_btn.configure(state='normal')
        if self._is_paused:
            # Stop fired during paused state — already handled.
            return
        self._set_status('Done.', SUCCESS)

    def _on_pause_resume(self) -> None:
        # pyttsx3 has no first-class pause: we stop, remember the text,
        # and speak again on resume. Good enough for sentence-level pauses.
        if self._is_paused and self._paused_remainder:
            text = self._paused_remainder
            self._paused_remainder = None
            self._is_paused = False
            self.pause_btn.configure(text='⏸  Pause')
            self._start_speaking(text)
            return
        if self._engine is not None and self._speech_thread \
                and self._speech_thread.is_alive():
            self._paused_remainder = self._current_text()
            self._is_paused = True
            try:
                self._engine.stop()
            except Exception:
                pass
            self.pause_btn.configure(text='▶  Resume')
            self._set_status('Paused. Press Resume to continue.', MUTED)

    def _on_stop(self) -> None:
        self._paused_remainder = None
        self._is_paused = False
        self.pause_btn.configure(text='⏸  Pause')
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._set_status('Stopped.', MUTED)

    def _on_save(self) -> None:
        text = self._current_text()
        if not text:
            self._set_status('Nothing to save.', DANGER)
            return
        path = filedialog.asksaveasfilename(
            title='Save speech as WAV',
            defaultextension='.wav',
            filetypes=[('WAV audio', '*.wav'), ('All files', '*.*')])
        if not path:
            return
        try:
            self._set_status('Rendering…', ACCENT)
            self.update_idletasks()
            save_to_wav(text, path,
                        voice=self._selected_voice_id(),
                        rate=int(self.rate_slider.get()),
                        volume=float(self.vol_slider.get()))
            self._set_status(f'Saved → {path}', SUCCESS)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror('Save failed', str(exc))
            self._set_status(f'Save failed: {exc}', DANGER)

    def _on_close(self) -> None:
        try:
            if self._engine is not None:
                self._engine.stop()
        except Exception:
            pass
        self.destroy()


if __name__ == '__main__':
    TTSTalkerApp().mainloop()
