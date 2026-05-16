# TTS Talker

Offline text-to-speech with three front-ends.

| Version | File | Stack |
|---------|------|-------|
| CLI | `tts_talker.py` | `pyttsx3` + argparse |
| Desktop GUI | `tts_talker_gui.py` | CustomTkinter |
| Terminal UI | `tts_talker_tui.py` | Textual |

## Why pyttsx3?

`pyttsx3` is a thin wrapper around the operating system's built-in TTS:

- **Windows** — SAPI5 (the same voices used by Narrator)
- **macOS** — NSSpeechSynthesizer
- **Linux** — `espeak`

That means **no API keys, no network, no model downloads** — speech works
the moment the package is installed.

## Install

`pyttsx3` is **not** in the shared root `requirements.txt`. Install it into the project venv:

```bash
uv pip install pyttsx3
```

> Linux users also need `espeak` from the system package manager
> (`sudo apt install espeak`).

## Run

```bash
# CLI — speak text directly
uv run python tts_talker/tts_talker.py "Hello world"

# CLI — list installed voices
uv run python tts_talker/tts_talker.py --list-voices

# CLI — speed-reading mode (max 400 wpm)
uv run python tts_talker/tts_talker.py "Lorem ipsum…" --rate 380

# CLI — render to WAV instead of speaking
uv run python tts_talker/tts_talker.py "Save me to disk" --save out.wav

# Desktop GUI
uv run python tts_talker/tts_talker_gui.py

# Terminal UI
uv run python tts_talker/tts_talker_tui.py
```

## Controls

### GUI (CustomTkinter)

- **Voice** dropdown — every SAPI/NSSpeech/espeak voice on your system
- **Rate** slider — 50 to 400 words per minute
- **Volume** slider — 0 to 100%
- **Speak** button or **Ctrl+Enter** anywhere
- **Pause / Resume** — flushes the engine queue and re-enqueues remaining text
- **Stop** — abort current speech
- **Save WAV** — render the current text to a `.wav` file via `engine.save_to_file`

### TUI (Textual)

- **Ctrl+Enter** — speak (mapped via `ctrl+j`, the conventional alias)
- **Ctrl+S** — stop
- **Ctrl+W** — save to `out.wav` next to the script
- **Ctrl+Q** — quit
- Voice picker plus +/- steppers for rate and volume

## Architecture

`tts_talker.py` exports the pure helpers reused by both GUIs:

```python
list_voices() -> list[dict]
speak(text, voice=None, rate=180, volume=1.0)
save_to_wav(text, path, voice=None, rate=180, volume=1.0)
```

A new `pyttsx3.Engine` is created per call. Caching a module-level engine
across `runAndWait()` invocations is unreliable on Windows (the COM-backed
SAPI driver gets confused), so we trade a few milliseconds of init for
correctness. The GUI keeps a live engine reference only so `Stop` and
`Pause` can interrupt speech mid-utterance.

## Twist: Save to WAV

`engine.save_to_file(text, path)` renders directly to disk without
playing audio. Useful for batch processing or building audiobooks from
plain text.

## Twist: Speed-reading

The slider/argparse upper bound is **400 wpm** — roughly twice typical
narration speed and approaching the comprehension ceiling for trained
speed-listeners. Combine with a clear voice (Zira on Windows) for a
practical "skim with your ears" workflow.
