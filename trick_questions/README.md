# Trick Questions

A riddle-style quiz where the obvious answer is almost always wrong. Three flavors:

| Version | File | Stack |
|---------|------|-------|
| CLI (original) | `trick_questions.py` | stdlib |
| Modern desktop GUI | `trick_questions_gui.py` | CustomTkinter |
| Modern terminal UI | `trick_questions_tui.py` | Textual |

## How it works

28 questions span three difficulty tiers — **Easy → Medium → Hard**. Answer three in a row correctly and the quiz escalates to the next tier. A wrong answer resets your streak. Each question carries a hint (revealed on request) and an explanation (shown after you answer).

## Run

```bash
# CLI
uv run python trick_questions/trick_questions.py
uv run python trick_questions/trick_questions.py --seed 42 --rounds 5

# Desktop GUI (CustomTkinter)
uv run python trick_questions/trick_questions_gui.py

# Terminal UI (Textual)
uv run python trick_questions/trick_questions_tui.py
uv run python trick_questions/trick_questions_tui.py --seed 42 --rounds 5
```

## GUI features

- Question displayed in a card with the current difficulty badge.
- **Hint** button reveals a nudge (penalty-free).
- Submit locks the input and reveals the explanation with a green/red result.
- **Next** button advances to the next question; a summary card appears at the end.
- Score and accuracy tracked in the status bar throughout.

## TUI features

- Dark Tailwind palette — slate-900 background, sky/cyan accents.
- Big question card with color-coded difficulty label (green/amber/red).
- Answer input with cyan focus border; **Enter** submits or advances.
- Explanation revealed inline after each answer.
- Score / accuracy / streak / tier always visible in the scorebar.

| Binding | Action |
|---------|--------|
| Enter | Submit answer / advance to next question |
| Ctrl+H | Reveal hint |
| Ctrl+Q | Quit |

## Architecture

`trick_questions.py` holds the shared `Quiz` engine. Both GUI and TUI import it and call:

- `Quiz.next_question()` — picks the next question from the current tier, returns a dict with `question`, `answer` (regex), `hint`, `explanation`, `difficulty`, `index`.
- `Quiz.check(answer)` — validates the answer, updates streak/score/tier, returns `{"correct", "explanation", "escalated", "streak", "difficulty"}`.
- `Quiz.use_hint()` — records hint usage and returns the hint string.
- `Quiz.state()` — snapshot of `score`, `rounds`, `accuracy`, `difficulty`, `streak`.

## Notes

- Answers are matched with a case-insensitive regex so spelling variations are accepted (e.g. `"noah"` / `"It was Noah"`).
- Difficulty escalates after **3 consecutive correct answers** and resets on any wrong answer.
- Pass `--seed` for a reproducible question order — useful for testing or demos.
