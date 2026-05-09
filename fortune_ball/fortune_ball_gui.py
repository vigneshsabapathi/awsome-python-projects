"""Magic Fortune Ball - CustomTkinter GUI.

Dark-themed desktop UI with a big black ball drawn on a tk.Canvas, an
animated shake before the answer reveals, and color-coded results
(green / grey / red).

Run:
    uv run python fortune_ball/fortune_ball_gui.py
"""
from __future__ import annotations

import random

import customtkinter as ctk

from fortune_ball import ask

TITLE_FONT = ('Segoe UI', 28, 'bold')
ANSWER_FONT = ('Segoe UI', 18, 'bold')
LABEL_FONT = ('Segoe UI', 13)
META_FONT = ('Segoe UI', 12, 'italic')
BTN_FONT = ('Segoe UI', 14, 'bold')

BG = '#0f172a'
PANEL = '#1e293b'
BORDER = '#334155'
ACCENT = '#a855f7'         # purple - mystical vibe
ACCENT_HOVER = '#9333ea'
MUTED = '#94a3b8'
TEXT = '#f8fafc'
POS_COLOR = '#34d399'      # green
NEU_COLOR = '#cbd5e1'      # grey
NEG_COLOR = '#f87171'      # red

SENTIMENT_COLOR: dict[str, str] = {
    'positive': POS_COLOR,
    'neutral': NEU_COLOR,
    'negative': NEG_COLOR,
}

# Canvas geometry.
CANVAS_W = 360
CANVAS_H = 360
BALL_CX = CANVAS_W // 2
BALL_CY = CANVAS_H // 2
BALL_R = 140
WINDOW_R = 60          # inner answer window
SHAKE_FRAMES = 14
SHAKE_INTERVAL_MS = 45
SHAKE_AMPLITUDE = 14


class FortuneBallApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')
        ctk.set_default_color_theme('dark-blue')

        self.title('Magic Fortune Ball')
        self.geometry('560x780')
        self.minsize(520, 720)
        self.configure(fg_color=BG)

        self.rng = random.Random()
        self.bias = 0.5
        self.remember = ctk.BooleanVar(value=False)
        self._shaking = False
        self._ball_items: list[int] = []

        self._build_ui()
        self._draw_ball(answer_text='8', answer_color=TEXT)

        self.bind('<Return>', lambda _e: self._ask())
        self.after(120, lambda: self.question_entry.focus_set())

    # ----- UI construction -------------------------------------------------
    def _build_ui(self) -> None:
        # Header.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', pady=(18, 4), padx=24, fill='x')
        ctk.CTkLabel(header, text='MAGIC FORTUNE BALL', font=TITLE_FONT,
                     text_color=TEXT).pack()
        ctk.CTkLabel(
            header,
            text='Ask a yes/no question and shake the ball',
            font=LABEL_FONT, text_color=MUTED,
        ).pack(pady=(2, 0))

        # Canvas with the ball.
        self.canvas = ctk.CTkCanvas(
            self, width=CANVAS_W, height=CANVAS_H,
            bg=BG, highlightthickness=0, bd=0,
        )
        self.canvas.pack(side='top', pady=(8, 4))

        # Question entry.
        question_row = ctk.CTkFrame(self, fg_color='transparent')
        question_row.pack(side='top', padx=24, fill='x', pady=(8, 6))
        self.question_entry = ctk.CTkEntry(
            question_row,
            placeholder_text='Will it rain tomorrow?',
            font=LABEL_FONT, fg_color=PANEL, border_color=BORDER,
            text_color=TEXT, height=36,
        )
        self.question_entry.pack(side='left', expand=True, fill='x',
                                 padx=(0, 8))
        self.ask_button = ctk.CTkButton(
            question_row, text='Ask', font=BTN_FONT, width=110,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color='#0f172a',
            command=self._ask,
        )
        self.ask_button.pack(side='left')

        # Bias slider (the twist).
        bias_frame = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12,
                                  border_color=BORDER, border_width=1)
        bias_frame.pack(side='top', padx=24, fill='x', pady=(6, 6))
        ctk.CTkLabel(
            bias_frame,
            text='Sentiment bias  (more negative <----> more positive)',
            font=LABEL_FONT, text_color=MUTED,
        ).pack(pady=(8, 0))
        self.bias_slider = ctk.CTkSlider(
            bias_frame, from_=0.0, to=1.0, number_of_steps=20,
            command=self._on_bias_change,
            button_color=ACCENT, button_hover_color=ACCENT_HOVER,
            progress_color=ACCENT,
        )
        self.bias_slider.set(0.5)
        self.bias_slider.pack(padx=14, pady=(2, 4), fill='x')
        self.bias_label = ctk.CTkLabel(
            bias_frame, text='balanced (0.50)', font=META_FONT,
            text_color=MUTED,
        )
        self.bias_label.pack(pady=(0, 8))

        # Remember toggle.
        ctk.CTkCheckBox(
            self, text='Remember mode (same question -> same answer)',
            variable=self.remember, font=LABEL_FONT,
            text_color=TEXT, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            border_color=BORDER,
        ).pack(side='top', pady=(2, 8))

        # Result label below the ball.
        self.result_label = ctk.CTkLabel(
            self, text=' ', font=ANSWER_FONT, text_color=TEXT,
            wraplength=480, justify='center',
        )
        self.result_label.pack(side='top', padx=24, pady=(2, 0))
        self.sentiment_label = ctk.CTkLabel(
            self, text=' ', font=META_FONT, text_color=MUTED,
        )
        self.sentiment_label.pack(side='top', pady=(0, 12))

    # ----- ball rendering --------------------------------------------------
    def _draw_ball(self, answer_text: str, answer_color: str,
                   dx: int = 0, dy: int = 0) -> None:
        """Redraw the entire ball with optional offset (for shake animation)."""
        # Wipe previous frame.
        for item in self._ball_items:
            self.canvas.delete(item)
        self._ball_items.clear()

        cx = BALL_CX + dx
        cy = BALL_CY + dy

        # Outer black ball with subtle dark-purple rim.
        self._ball_items.append(self.canvas.create_oval(
            cx - BALL_R - 4, cy - BALL_R - 4,
            cx + BALL_R + 4, cy + BALL_R + 4,
            fill='#1a0f2e', outline='',
        ))
        self._ball_items.append(self.canvas.create_oval(
            cx - BALL_R, cy - BALL_R, cx + BALL_R, cy + BALL_R,
            fill='#0a0a0a', outline=BORDER, width=2,
        ))
        # Highlight - small white-ish glint, top-left.
        self._ball_items.append(self.canvas.create_oval(
            cx - BALL_R + 24, cy - BALL_R + 24,
            cx - BALL_R + 64, cy - BALL_R + 60,
            fill='#3b3b4b', outline='',
        ))
        # Inner answer window (dark navy disc).
        self._ball_items.append(self.canvas.create_oval(
            cx - WINDOW_R, cy - WINDOW_R, cx + WINDOW_R, cy + WINDOW_R,
            fill='#0d1b3a', outline='#1f2a44', width=2,
        ))
        # Answer text.
        font_size = 36 if len(answer_text) <= 2 else 11
        self._ball_items.append(self.canvas.create_text(
            cx, cy, text=answer_text, fill=answer_color,
            font=('Segoe UI', font_size, 'bold'),
            width=WINDOW_R * 2 - 16, justify='center',
        ))

    # ----- behaviour -------------------------------------------------------
    def _on_bias_change(self, value: float) -> None:
        self.bias = float(value)
        if self.bias < 0.35:
            label = 'pessimistic'
        elif self.bias > 0.65:
            label = 'optimistic'
        else:
            label = 'balanced'
        self.bias_label.configure(text=f'{label} ({self.bias:.2f})')

    def _ask(self) -> None:
        if self._shaking:
            return
        question = self.question_entry.get().strip()
        if not question:
            self.result_label.configure(
                text='Type a question first.', text_color=NEG_COLOR,
            )
            self.sentiment_label.configure(text=' ')
            return

        try:
            result = ask(
                question, rng=self.rng, bias=self.bias,
                remember=bool(self.remember.get()),
            )
        except (ValueError, TypeError) as exc:
            self.result_label.configure(text=str(exc), text_color=NEG_COLOR)
            return

        # Disable input during the shake, then reveal.
        self._shaking = True
        self.ask_button.configure(state='disabled', text='Shaking...')
        self.result_label.configure(text='...', text_color=MUTED)
        self.sentiment_label.configure(text=' ')
        self._draw_ball(answer_text='?', answer_color=MUTED)
        self._animate_shake(SHAKE_FRAMES, result)

    def _animate_shake(self, frames_left: int, result: dict) -> None:
        if frames_left <= 0:
            self._reveal(result)
            return
        # Random jitter offsets shrink as the shake winds down.
        decay = frames_left / SHAKE_FRAMES
        amp = max(2, int(SHAKE_AMPLITUDE * decay))
        dx = random.randint(-amp, amp)
        dy = random.randint(-amp, amp)
        self._draw_ball(answer_text='?', answer_color=MUTED, dx=dx, dy=dy)
        self.after(
            SHAKE_INTERVAL_MS,
            lambda: self._animate_shake(frames_left - 1, result),
        )

    def _reveal(self, result: dict) -> None:
        color = SENTIMENT_COLOR[result['sentiment']]
        # The ball recenters with the answer text.
        self._draw_ball(answer_text=result['answer'], answer_color=color)
        self.result_label.configure(text=result['answer'], text_color=color)
        self.sentiment_label.configure(
            text=f'sentiment: {result["sentiment"]}', text_color=color,
        )
        self.ask_button.configure(state='normal', text='Ask')
        self._shaking = False


if __name__ == '__main__':
    FortuneBallApp().mainloop()
