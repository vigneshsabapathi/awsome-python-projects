"""TTS Talker — offline text-to-speech CLI.

Wraps `pyttsx3` (which uses SAPI on Windows, NSSpeechSynthesizer on macOS,
espeak on Linux) so the same code is usable from CLI, GUI, and TUI front-ends.

Pure helpers (used by the GUI/TUI):
    list_voices() -> list[dict]          — enumerate available voices
    speak(text, voice=None, rate=180,
          volume=1.0)                    — speak text, blocking until done
    save_to_wav(text, path, ...)         — render to a WAV file instead of speaking

Run the CLI:
    uv run python tts_talker/tts_talker.py "Hello world"
    uv run python tts_talker/tts_talker.py --list-voices
    uv run python tts_talker/tts_talker.py "fast" --rate 320
    uv run python tts_talker/tts_talker.py "save me" --save out.wav
"""
from __future__ import annotations

import argparse
import sys
from typing import Iterable

import pyttsx3

DEFAULT_RATE = 180   # words per minute, the pyttsx3 default
MIN_RATE = 50
MAX_RATE = 400       # speed-reading territory
DEFAULT_VOLUME = 1.0


def _new_engine() -> pyttsx3.Engine:
    """Build a fresh engine. We deliberately do NOT cache a module-level
    engine: pyttsx3 keeps an internal run-loop state that gets confused
    when reused across GUI events, especially after `runAndWait()`."""
    return pyttsx3.init()


def list_voices() -> list[dict]:
    """Return one dict per available system voice.

    Each dict has: id, name, languages, gender, age. Values that pyttsx3
    can't determine come back as empty strings/lists rather than None so
    UI code doesn't need null-guards.
    """
    engine = _new_engine()
    try:
        out: list[dict] = []
        for v in engine.getProperty('voices'):
            out.append({
                'id': v.id,
                'name': getattr(v, 'name', '') or '',
                'languages': list(getattr(v, 'languages', []) or []),
                'gender': getattr(v, 'gender', '') or '',
                'age': getattr(v, 'age', '') or '',
            })
        return out
    finally:
        # Engines hold COM handles on Windows; release them deterministically.
        try:
            engine.stop()
        except Exception:
            pass
        del engine


def _clamp_rate(rate: int) -> int:
    return max(MIN_RATE, min(MAX_RATE, int(rate)))


def _clamp_volume(volume: float) -> float:
    return max(0.0, min(1.0, float(volume)))


def _configure(engine: pyttsx3.Engine, voice: str | None,
               rate: int, volume: float) -> None:
    if voice:
        engine.setProperty('voice', voice)
    engine.setProperty('rate', _clamp_rate(rate))
    engine.setProperty('volume', _clamp_volume(volume))


def speak(text: str, voice: str | None = None,
          rate: int = DEFAULT_RATE, volume: float = DEFAULT_VOLUME) -> None:
    """Speak `text` synchronously. Returns when speech finishes."""
    if not text:
        return
    engine = _new_engine()
    try:
        _configure(engine, voice, rate, volume)
        engine.say(text)
        engine.runAndWait()
    finally:
        try:
            engine.stop()
        except Exception:
            pass


def save_to_wav(text: str, path: str, voice: str | None = None,
                rate: int = DEFAULT_RATE,
                volume: float = DEFAULT_VOLUME) -> str:
    """Render `text` to a WAV file at `path`. Returns the absolute path."""
    if not text:
        raise ValueError('Refusing to save empty text.')
    engine = _new_engine()
    try:
        _configure(engine, voice, rate, volume)
        engine.save_to_file(text, path)
        engine.runAndWait()
    finally:
        try:
            engine.stop()
        except Exception:
            pass
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _print_voices(voices: Iterable[dict]) -> None:
    for i, v in enumerate(voices):
        langs = ', '.join(str(lang) for lang in v['languages']) or '—'
        gender = v['gender'] or '—'
        print(f'  [{i}] {v["name"]}')
        print(f'        id={v["id"]}')
        print(f'        languages={langs}  gender={gender}')


def _resolve_voice(voices: list[dict], selector: str | None) -> str | None:
    """Allow `--voice <index>` or `--voice <substring of name>`."""
    if not selector:
        return None
    if selector.isdecimal():
        idx = int(selector)
        if 0 <= idx < len(voices):
            return voices[idx]['id']
        raise SystemExit(
            f'Voice index {idx} out of range (have {len(voices)} voices).')
    needle = selector.lower()
    for v in voices:
        if needle in v['name'].lower() or needle == v['id']:
            return v['id']
    raise SystemExit(f'No voice matched "{selector}". '
                     'Use --list-voices to see options.')


def main() -> None:
    parser = argparse.ArgumentParser(
        prog='tts_talker',
        description='Speak text aloud via pyttsx3 (offline TTS).')
    parser.add_argument('text', nargs='*',
                        help='Text to speak. If omitted, reads from stdin.')
    parser.add_argument('--list-voices', action='store_true',
                        help='Print available voices and exit.')
    parser.add_argument('--voice', default=None,
                        help='Voice index (e.g. 0) or name substring '
                             '(e.g. "Zira").')
    parser.add_argument('--rate', type=int, default=DEFAULT_RATE,
                        help=f'Words per minute ({MIN_RATE}-{MAX_RATE}). '
                             f'Default: {DEFAULT_RATE}.')
    parser.add_argument('--volume', type=float, default=DEFAULT_VOLUME,
                        help='0.0–1.0. Default: 1.0.')
    parser.add_argument('--save', metavar='PATH', default=None,
                        help='Render to a WAV file instead of speaking.')
    args = parser.parse_args()

    voices = list_voices()

    if args.list_voices:
        if not voices:
            print('No voices found.')
            return
        print(f'{len(voices)} voice(s) available:')
        _print_voices(voices)
        return

    text = ' '.join(args.text).strip()
    if not text:
        if sys.stdin.isatty():
            print('Enter text to speak (Ctrl+D / Ctrl+Z then Enter to finish):')
        text = sys.stdin.read().strip()
    if not text:
        parser.error('No text provided.')

    voice_id = _resolve_voice(voices, args.voice)

    if args.save:
        out = save_to_wav(text, args.save, voice=voice_id,
                          rate=args.rate, volume=args.volume)
        print(f'Saved → {out}')
    else:
        speak(text, voice=voice_id, rate=args.rate, volume=args.volume)


if __name__ == '__main__':
    main()
