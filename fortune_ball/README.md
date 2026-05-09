# Magic Fortune Ball

A Magic 8-ball: ask a yes/no question, get one of 25 hand-authored
responses themed positive, neutral, or negative. Three front-ends share
the same response pool: a CLI, a CustomTkinter desktop GUI with an
animated shake, and a Textual TUI with an ASCII ball.

## Features

- **25 authored responses** - 10 positive, 5 neutral, 10 negative
  (the same shape as the original Magic 8-ball)
- **Sentiment-balanced output** - every answer is tagged
  `positive` / `neutral` / `negative` so UIs can color-code the result
- **Bias slider (twist)** - tilt the pool toward optimism or pessimism
  while neutral keeps its share, so "hazy" answers never disappear
- **Remember mode (twist)** - the same question always gets the same
  answer ("the ball knows you")
- **Animated shake** in the GUI - jitter offsets that decay before reveal
- **Three front-ends** sharing one pure-function core:
  CLI, CustomTkinter desktop GUI, Textual TUI

## Run

```bash
# CLI
uv run python fortune_ball/fortune_ball.py
uv run python fortune_ball/fortune_ball.py --question "Will it rain?"
uv run python fortune_ball/fortune_ball.py --bias 0.7 --seed 42
uv run python fortune_ball/fortune_ball.py --remember --question "Will it rain?"

# Desktop GUI (CustomTkinter)
uv run python fortune_ball/fortune_ball_gui.py

# Terminal UI (Textual)
uv run python fortune_ball/fortune_ball_tui.py
```

### CLI flags

| Flag | Default | Meaning |
|---|---|---|
| `-q / --question Q` | prompt | the yes/no question |
| `-b / --bias F` | `0.5` | sentiment bias slider in `[0, 1]` (0 = all-negative, 1 = all-positive) |
| `-s / --seed N` | random | seed the RNG for reproducible answers |
| `--remember` | off | same question -> same answer (stable across runs) |

### GUI bindings

- **Enter** - ask the ball
- **Ask** button - same as Enter
- **Bias slider** - shifts the pool toward optimism or pessimism
- **Remember checkbox** - lock answers to the question text

### TUI bindings

- **Enter** - ask
- **Ctrl+B** - cycle bias preset (pessimistic / balanced / optimistic)
- **Ctrl+R** - toggle remember mode
- **Ctrl+Q** - quit

## Architecture

```
fortune_ball/
  fortune_ball.py        Pure functions + CLI
    POSITIVE / NEUTRAL / NEGATIVE  authored response tuples (10/5/10)
    SENTIMENTS                     dict mapping label -> tuple
    all_responses()                -> list[(answer, sentiment)]
    ask(question, rng, *,          -> {"answer": str,
        bias, remember)                "sentiment": "positive"|"neutral"|"negative"}
    main(argv)                     argparse entry-point
  fortune_ball_gui.py    CustomTkinter front-end (animated canvas ball)
  fortune_ball_tui.py    Textual front-end (ASCII ball)
```

The core is dependency-free (stdlib only). Each front-end imports
`ask` and the response constants from `fortune_ball`, so adding or
editing a response instantly shows up in all three UIs.

### `ask(question, rng=None, *, bias=0.5, remember=False)`

1. Validate inputs (question must be a non-empty string,
   `bias in [0, 1]`).
2. If `remember=True`, derive a stable RNG seed by SHA-256-hashing the
   lower-cased question - same wording, same answer.
3. Pick a sentiment label using a weighted roll where neutral keeps
   its authored share (5/25 = 0.2) and the remaining 0.8 of probability
   mass is split between positive and negative according to `bias`.
4. Pick a random response from that sentiment's pool.
5. Return `{"answer": str, "sentiment": str}`.

Time complexity: O(1) per ask (one hash if remember-mode, one bucket
choice, one in-bucket choice).

### Bias slider math

```
neutral_share = 5 / 25 = 0.20
remaining     = 1 - neutral_share = 0.80
pos_share     = remaining * bias
neg_share     = remaining * (1 - bias)
roll = rng.random()
  roll < pos_share                         -> positive
  pos_share <= roll < pos_share+neg_share  -> negative
  else                                     -> neutral
```

At `bias=0.5` this reproduces the natural 10/5/10 distribution
(40% positive, 40% negative, 20% neutral). At `bias=1.0` you get
80% positive, 20% neutral, 0% negative.

### GUI shake animation

`_animate_shake(frames_left, result)` schedules itself with
`self.after(SHAKE_INTERVAL_MS, ...)`. Each frame redraws the entire
ball at a random `(dx, dy)` offset whose amplitude decays linearly
with `frames_left / SHAKE_FRAMES`. After 14 frames the shake settles
and `_reveal()` repaints the ball with the answer color-coded
(green / grey / red).
