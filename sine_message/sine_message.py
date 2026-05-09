"""Sine Message — display a message bouncing along a sine wave.

Each character of `message` sits in a column at integer Y offset:

    y(x) = round(amplitude * sin(frequency * x + phase))

The message is repeated horizontally to fill `width` columns; when the phase
advances every frame, the wave appears to scroll.

The default `render` produces a pure sine. The companion `render_overlay`
mixes a sine, a cosine, and a higher harmonic for a richer ribbon, and
`render_lissajous` adds X-jitter so the message traces a 2-D Lissajous curve
instead of a 1-D wave.

CLI:
    uv run python sine_message/sine_message.py            # static frame
    uv run python sine_message/sine_message.py --animate  # phase-scroll loop

Tags: animation, ascii-art, math, trigonometry, beginner
"""
from __future__ import annotations

import argparse
import math
import sys
import time

DEFAULT_MESSAGE = 'Sine message scrolling forever ~ '


def _grid(width: int, height: int) -> list[list[str]]:
    return [[' '] * width for _ in range(height)]


def _y_offset(x: int, amplitude: float, frequency: float, phase: float,
              fn=math.sin) -> int:
    """Integer Y offset for column `x` along a single trig wave."""
    return int(round(amplitude * fn(frequency * x + phase)))


def render(message: str, width: int = 80, amplitude: float = 8.0,
           frequency: float = 0.2, phase: float = 0.0) -> str:
    """Render `message` along a sine wave as a multi-line string.

    The output has `2 * amplitude + 1` rows. Each column `x` in `[0, width)`
    receives the character `message[x % len(message)]` at row
    `amplitude - int(round(amplitude * sin(frequency * x + phase)))`,
    so positive sine values rise toward the top of the canvas.
    """
    if not message:
        raise ValueError('message must be non-empty')
    amp = max(0, int(round(amplitude)))
    height = 2 * amp + 1
    grid = _grid(width, height)
    for x in range(width):
        ch = message[x % len(message)]
        offset = _y_offset(x, amp, frequency, phase)
        row = amp - offset  # invert: +sin -> upper rows
        # `amp - offset` is always within [0, height) because |offset| <= amp.
        grid[row][x] = ch
    return '\n'.join(''.join(row) for row in grid)


def render_overlay(message: str, width: int = 80, amplitude: float = 8.0,
                   frequency: float = 0.2, phase: float = 0.0) -> str:
    """Sine + cosine + harmonic overlay — three waves, three layers.

    Each wave draws the message at its own Y-offset; layers are drawn back
    to front so the primary sine sits on top when waves cross.
    """
    if not message:
        raise ValueError('message must be non-empty')
    amp = max(0, int(round(amplitude)))
    height = 2 * amp + 1
    grid = _grid(width, height)
    waves = (
        # (function, amplitude_factor, frequency_factor, phase_offset)
        (math.sin, 0.5, 2.0, 0.0),       # higher harmonic, half amp (back)
        (math.cos, 0.85, 1.0, 0.0),      # cosine companion
        (math.sin, 1.0, 1.0, 0.0),       # primary sine (drawn last)
    )
    for fn, amp_f, freq_f, ph_off in waves:
        for x in range(width):
            ch = message[x % len(message)]
            local_amp = amp * amp_f
            offset = int(round(local_amp * fn(frequency * freq_f * x
                                              + phase + ph_off)))
            row = amp - offset
            if 0 <= row < height:
                grid[row][x] = ch
    return '\n'.join(''.join(row) for row in grid)


def render_lissajous(message: str, width: int = 80, amplitude: float = 8.0,
                     frequency: float = 0.2, phase: float = 0.0,
                     x_wobble: float = 3.0,
                     x_freq_ratio: float = 0.7) -> str:
    """2-D Lissajous: characters wobble in X as well as Y.

    Column position becomes `x + round(x_wobble * cos(x_freq_ratio * x))`,
    so the message traces a Lissajous-like curve. Earlier characters get
    overwritten by later ones when columns collide.
    """
    if not message:
        raise ValueError('message must be non-empty')
    amp = max(0, int(round(amplitude)))
    height = 2 * amp + 1
    grid = _grid(width, height)
    for x in range(width):
        ch = message[x % len(message)]
        y_off = int(round(amp * math.sin(frequency * x + phase)))
        x_off = int(round(x_wobble * math.cos(x_freq_ratio * frequency * x
                                              + phase)))
        col = x + x_off
        if 0 <= col < width:
            row = amp - y_off
            if 0 <= row < height:
                grid[row][col] = ch
    return '\n'.join(''.join(row) for row in grid)


def _animate(message: str, width: int, amplitude: float, frequency: float,
             phase_step: float = 0.1, fps: int = 20,
             renderer=render) -> None:
    """Loop forever scrolling the wave. Ctrl+C to stop."""
    phase = 0.0
    delay = 1.0 / max(1, fps)
    try:
        while True:
            frame = renderer(message, width=width, amplitude=amplitude,
                             frequency=frequency, phase=phase)
            # ANSI clear + home cursor; falls back to printing on dumb terms.
            sys.stdout.write('\x1b[H\x1b[2J')
            sys.stdout.write(frame)
            sys.stdout.write('\n')
            sys.stdout.flush()
            phase += phase_step
            time.sleep(delay)
    except KeyboardInterrupt:
        sys.stdout.write('\n')


_RENDERERS = {
    'sine': render,
    'overlay': render_overlay,
    'lissajous': render_lissajous,
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog='sine_message',
        description='Display a message along a sine wave (static or '
                    'animated).')
    p.add_argument('-m', '--message', default=DEFAULT_MESSAGE,
                   help='Message text to wrap along the wave.')
    p.add_argument('-w', '--width', type=int, default=80,
                   help='Canvas width in columns (default: 80).')
    p.add_argument('-a', '--amplitude', type=float, default=8.0,
                   help='Wave amplitude in rows (default: 8).')
    p.add_argument('-f', '--frequency', type=float, default=0.2,
                   help='Wave angular frequency (default: 0.2).')
    p.add_argument('--mode', choices=tuple(_RENDERERS), default='sine',
                   help='Renderer: sine, overlay, or lissajous.')
    p.add_argument('--animate', action='store_true',
                   help='Loop forever, advancing phase every frame.')
    p.add_argument('--phase-step', type=float, default=0.1,
                   help='Phase delta per frame in --animate mode.')
    p.add_argument('--fps', type=int, default=20,
                   help='Target frames per second in --animate mode.')
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    renderer = _RENDERERS[args.mode]
    if args.animate:
        _animate(args.message, args.width, args.amplitude, args.frequency,
                 phase_step=args.phase_step, fps=args.fps, renderer=renderer)
    else:
        print(renderer(args.message, width=args.width,
                       amplitude=args.amplitude, frequency=args.frequency,
                       phase=0.0))


if __name__ == '__main__':
    main()
