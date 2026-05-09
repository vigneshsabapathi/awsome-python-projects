"""Magic Fortune Ball - Textual TUI.

Dark palette. A big ASCII ball with the answer printed in the inner
"window". Ask via the input field; press Enter to ask, Ctrl+Q to quit.

Bindings:
    Enter        Ask the ball
    Ctrl+Q       Quit
    Ctrl+B       Toggle bias (pessimistic / balanced / optimistic)
    Ctrl+R       Toggle "remember" mode

Run:
    uv run python fortune_ball/fortune_ball_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Input, Static

from fortune_ball import ask

# Cycle through the three bias presets with Ctrl+B.
BIAS_PRESETS: list[tuple[str, float]] = [
    ('pessimistic', 0.25),
    ('balanced', 0.50),
    ('optimistic', 0.75),
]

# Hand-drawn ASCII ball template. {LINE1..3} are replaced with the centered
# answer fragment (split across three short lines so it fits in the window).
# Built as a list of lines to avoid quoting headaches with the Magic-8-ball
# silhouette that uses both quotes and backslashes.
BALL_TEMPLATE = "\n".join([
    "              .--======--.",
    "           .-'            '-.",
    "          /    .--====--.    \\",
    "         /   .'          '.   \\",
    "        /   /              \\   \\",
    "       /   /   {LINE1}   \\   \\",
    "       |   |   {LINE2}   |   |",
    "       |   |   {LINE3}   |   |",
    "        \\   \\              /   /",
    "         \\   \\            /   /",
    "          \\   '.        .'   /",
    "           \\    '-....-'    /",
    "            '-.            .-'",
    "               '-........-'",
])


def _wrap_answer(answer: str, width: int = 12) -> tuple[str, str, str]:
    """Wrap ``answer`` into (at most) three centered lines fitting ``width``."""
    words = answer.split()
    lines: list[str] = []
    current = ''
    for word in words:
        candidate = f'{current} {word}'.strip()
        if len(candidate) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word if len(word) <= width else word[: width - 1] + '~'
        if len(lines) == 3:
            break
    if current and len(lines) < 3:
        lines.append(current)
    while len(lines) < 3:
        lines.append('')
    return tuple(line.center(width) for line in lines[:3])  # type: ignore[return-value]


def render_ball(answer: str) -> str:
    """Return the ASCII-ball block with ``answer`` inscribed in the window."""
    a, b, c = _wrap_answer(answer)
    return (
        BALL_TEMPLATE
        .replace('{LINE1}', a)
        .replace('{LINE2}', b)
        .replace('{LINE3}', c)
    )


class FortuneBallApp(App):
    CSS = """
    Screen {
        background: #0f172a;
        color: #f8fafc;
        align: center top;
    }

    #title {
        text-align: center;
        text-style: bold;
        color: #f8fafc;
        padding-top: 1;
    }

    #subtitle {
        text-align: center;
        color: #94a3b8;
        padding-bottom: 1;
    }

    #ball {
        width: 90%;
        max-width: 60;
        height: auto;
        margin: 0 2;
        padding: 1 2;
        background: #1e293b;
        border: tall #334155;
        text-align: center;
        color: #f8fafc;
    }

    #answer {
        text-align: center;
        text-style: bold;
        padding: 1 2;
    }

    #meta {
        text-align: center;
        color: #94a3b8;
        padding: 0 2;
    }

    #question {
        margin: 1 2;
        background: #1e293b;
        border: tall #334155;
    }

    Footer {
        background: #0f172a;
    }
    """

    BINDINGS = [
        Binding('ctrl+q', 'quit', 'Quit'),
        Binding('ctrl+b', 'cycle_bias', 'Cycle bias'),
        Binding('ctrl+r', 'toggle_remember', 'Toggle remember'),
    ]

    TITLE = 'Magic Fortune Ball'

    SENTIMENT_STYLE: dict[str, str] = {
        'positive': '#34d399',
        'neutral': '#cbd5e1',
        'negative': '#f87171',
    }

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        self.bias_index = 1   # balanced
        self.remember = False
        self._initial_ball = render_ball('?')

    @property
    def bias(self) -> float:
        return BIAS_PRESETS[self.bias_index][1]

    @property
    def bias_name(self) -> str:
        return BIAS_PRESETS[self.bias_index][0]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MAGIC FORTUNE BALL', id='title')
        yield Static('Ask a yes/no question. The ball stirs, then speaks.',
                     id='subtitle')
        yield Static(self._initial_ball, id='ball')
        yield Static('(awaiting your question)', id='answer')
        yield Static(self._meta_text(), id='meta')
        yield Vertical(
            Input(placeholder='Will it rain tomorrow?', id='question'),
            id='question-row',
        )
        yield Footer()

    def on_mount(self) -> None:
        self.query_one('#question', Input).focus()

    # ----- actions ---------------------------------------------------------
    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'question':
            self._ask(event.value)

    def action_cycle_bias(self) -> None:
        self.bias_index = (self.bias_index + 1) % len(BIAS_PRESETS)
        self.query_one('#meta', Static).update(self._meta_text())

    def action_toggle_remember(self) -> None:
        self.remember = not self.remember
        self.query_one('#meta', Static).update(self._meta_text())

    # ----- helpers ---------------------------------------------------------
    def _meta_text(self) -> str:
        remember = 'on' if self.remember else 'off'
        return (
            f'bias: {self.bias_name} ({self.bias:.2f})  -  '
            f'remember: {remember}  -  Ctrl+B cycles bias  -  '
            f'Ctrl+R toggles remember'
        )

    def _ask(self, raw: str) -> None:
        question = raw.strip()
        ball = self.query_one('#ball', Static)
        answer = self.query_one('#answer', Static)

        if not question:
            answer.update('[b #f87171]Type a question first.[/]')
            ball.update(render_ball('?'))
            return

        try:
            result = ask(
                question, rng=self.rng, bias=self.bias,
                remember=self.remember,
            )
        except (ValueError, TypeError) as exc:
            answer.update(f'[b #f87171]{exc}[/]')
            return

        color = self.SENTIMENT_STYLE[result['sentiment']]
        # Render the ball with a short fragment in the window, then expand
        # the full sentence underneath in the answer label.
        short = result['answer'].split('-')[0].split('.')[0].strip() or 'yes'
        ball.update(f'[{color}]{render_ball(short)}[/]')
        answer.update(
            f'[b {color}]{result["answer"]}[/]\n'
            f'[i #94a3b8]sentiment: {result["sentiment"]}[/]'
        )
        # Clear the input for the next question.
        self.query_one('#question', Input).value = ''


if __name__ == '__main__':
    FortuneBallApp().run()
