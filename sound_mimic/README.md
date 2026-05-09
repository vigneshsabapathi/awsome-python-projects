# Sound Mimic

A Simon-says memory game. The computer plays a sequence of beeps at different pitches; you repeat it. Each round adds one new note. How long can you keep up?

Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI | `sound_mimic.py` | stdlib (+ `winsound` on Windows) |
| Modern desktop GUI | `sound_mimic_gui.py` | CustomTkinter |
| Modern terminal UI | `sound_mimic_tui.py` | Textual |

## Run

```bash
# CLI
uv run python sound_mimic/sound_mimic.py

# Desktop GUI
uv run python sound_mimic/sound_mimic_gui.py

# Terminal UI
uv run python sound_mimic/sound_mimic_tui.py
```

## How it plays

The computer flashes one of the colored pads (red / green / blue / yellow) and plays the matching tone, then waits for you to repeat the sequence. After every successful round it adds one more note.

| UI | How you input |
|----|---------------|
| CLI | Type the pad numbers (e.g. `1324`) and press Enter. |
| GUI | Click the colored tiles in order. |
| TUI | Press the `1`, `2`, `3`, `4` keys. |

### TUI bindings

- **space** — start
- **n** — new game
- **1-4** — press a pad
- **Ctrl+Q** — quit

### CLI difficulty

The CLI prompts for difficulty at the start:

- `1` — easy: 4 pads (C, E, G, C')
- `2` — normal: 6 pads (C, D, E, G, B, C')
- `3` — hard: 8 pads (C-major octave)

## The twist: speed-up

Each round trims 18ms off both the tone duration and the gap between tones, bottoming out at 140ms tone / 80ms gap. Round 1 is leisurely; round 15 is frantic. The musical pitches still match, so the sequence stays recognizable as melody — your fingers just have to keep up.

The GUI also tracks an in-session high score next to the round counter.

## Audio

`winsound.Beep(freq, ms)` is a stdlib module on Windows that drives the actual PC-speaker / sound-card beep at a specific frequency. On non-Windows platforms `winsound` doesn't exist, so the code degrades to writing the terminal bell character (`\a`) and sleeping the equivalent duration — the timing/visual gameplay still works, you just won't get pitched tones.

The four base pitches are C4 / E4 / G4 / C5 — a major triad plus the octave. They sound musical even when triggered in random order, which is what gives Simon its iconic "memorable melody" feel.

## Architecture

`sound_mimic.py` exposes the pure game logic:

- `Game(n_pads=4, rng=None)` — dataclass with `sequence`, `round`, `next_round()`, `check(player_seq)`, `reset()`, `state()`.
- `play_tone(pad, n_pads, ms)` — best-effort cross-platform tone playback.
- `PITCHES`, `PAD_NAMES` — constants for 4/6/8-pad modes.

The GUI and TUI both import `Game` and `PITCHES` directly. They run `winsound.Beep` on a background thread (it's blocking) and schedule visual flashes on the UI thread, so the event loop never stalls.

## Notes

- `winsound` is in the standard library on Windows — no extra packages needed.
- The RNG is injectable (`Game(rng=random.Random(seed))`) so tests can pin determinism.
- The CLI's ANSI color escapes assume a terminal that supports them (Windows Terminal, modern PowerShell, every Unix terminal). Plain `cmd.exe` may render the escapes literally.
