# Progress Bar

An animated terminal progress bar library plus three demo apps that showcase five visual styles side-by-side.

| Version | File | Stack |
|---------|------|-------|
| CLI library + showcase | `progress_bar.py` | stdlib |
| Desktop GUI gallery | `progress_bar_gui.py` | CustomTkinter |
| Terminal UI gallery | `progress_bar_tui.py` | Textual |

## Styles

| Style | What it looks like | Notes |
|-------|--------------------|-------|
| `blocks` | `█████▍   ` | Eighth-block sub-cell resolution (`▏▎▍▌▋▊▉█`). Smoothest. |
| `simple` | `[====>   ]` | Pure ASCII, works on any terminal. |
| `dots` | `⠿⠿⠿⠷⠁    ` | Braille dots, 6 levels per cell. |
| `gradient` | colored `█` | 256-color ANSI heatmap, blue → red. |
| `spinner` | `⠋ ████  ` | Rotating Braille spinner + bar. |

## Run

```bash
# CLI showcase — static gallery + animated demo of each style
uv run python progress_bar/progress_bar.py

# Just one style (animated)
uv run python progress_bar/progress_bar.py blocks
uv run python progress_bar/progress_bar.py gradient

# Iterator wrap demo
uv run python progress_bar/progress_bar.py --iter

# Desktop GUI (CustomTkinter) — animated gallery, speed/target sliders
uv run python progress_bar/progress_bar_gui.py

# Terminal UI (Textual) — scrollable gallery, space/r/ctrl+q
uv run python progress_bar/progress_bar_tui.py
```

## Library API

```python
from progress_bar import bar, ProgressBar, STYLES, format_eta, format_rate

# Pure rendering — returns a string, no side effects.
print(bar(0.42, width=40, style='blocks'))

# Iterator-style — wraps any iterable with len().
for chunk in ProgressBar(work_chunks, style='gradient', prefix='download'):
    process(chunk)

# Manual updates — when you don't have an iterable.
with ProgressBar(total=1_000_000, style='blocks') as pb:
    for batch in stream():
        pb.update(len(batch))
```

### `bar(progress, width=40, style='blocks') -> str`

Pure function. Renders one bar to a string. `progress` is clamped to `[0, 1]`. Returns at least `width` visible characters (the `gradient` style emits ANSI escapes around colored cells, so the returned string is longer than its visible width).

### `ProgressBar(iterable=None, total=None, *, width=30, style='blocks', prefix='', stream=sys.stdout, ema_alpha=0.3, min_interval=0.05)`

- Iterator (`for x in pb: ...`) or context manager (`with pb: ...`) or manual (`pb.update(n)`).
- ETA and rate are computed from an **exponentially-weighted moving average** (default `α=0.3`) over instantaneous chunk-rates. This avoids flicker when chunk sizes vary, and reacts faster than a simple overall mean.
- Redraws are throttled to `min_interval` seconds (default 50 ms) so terminal output doesn't dominate runtime.

## Architecture

`progress_bar.py` exports a small surface:

- `bar(progress, width, style)` — pure renderer.
- `ProgressBar(...)` — stateful iterator with EMA-smoothed rate + ETA.
- `STYLES` — tuple of supported style names, used by both UIs.
- `format_eta`, `format_rate`, `spinner_frame` — small helpers, reused across all three apps.

The GUI and TUI both import from `progress_bar` and supply their own visual rendering — the GUI draws on a `CTkCanvas` so each style gets a different geometry (filled rect, ASCII text, dot grid, gradient stripes, spinner glyph + inner bar), and the TUI emits Rich markup that Textual styles per row.

## Notes

- **EMA over plain mean.** A naive overall-mean rate (`n / elapsed`) under-reports speed if work was slow at the start, and over-reports if work was slow at the end. EMA tracks recent throughput, which is what humans actually want to see in an ETA.
- **Sub-cell resolution.** The `blocks` style uses Unicode eighth-block characters (`▏▎▍▌▋▊▉█`) so a `width=10` bar still has 80 visually distinct positions.
- **Gradient is column-stable.** Each column's color is fixed by its column index, not by the current `progress`. New cells appear; existing cells don't change color. This avoids the "rainbow strobing" effect when bars update fast.
- **Throttled draws.** `ProgressBar.update()` only redraws every `min_interval` seconds. With chunky updates (`pb.update(1)` on a 1M-item loop) the unthrottled cost of escape codes alone can dominate runtime.
