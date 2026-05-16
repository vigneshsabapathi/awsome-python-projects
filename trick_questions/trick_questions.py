"""Trick Questions — CLI.

A quiz of riddle-style trick questions where the obvious answer is almost
always wrong. Each item carries a question, an ``answer`` regex (so the
quiz tolerates phrasing variations), a hint, and an explanation.

The :class:`Quiz` object is the shared core for the GUI and TUI front-ends.
It escalates through three difficulty tiers as the player gets things right
(easy → medium → hard), and tracks per-question stats across the session
(see :meth:`Quiz.state`).

Run:
    uv run python trick_questions/trick_questions.py
    uv run python trick_questions/trick_questions.py --seed 42
    uv run python trick_questions/trick_questions.py --rounds 5
"""
from __future__ import annotations

import argparse
import random
import re
from dataclasses import dataclass, field
from typing import Optional

# --- Question bank -----------------------------------------------------------
# 28 originally authored trick questions. Each ``answer`` is a regex with
# IGNORECASE / VERBOSE flags so the quiz accepts spelling-tolerant input
# (e.g. "noah" / "Noah, not Moses" / "it was Noah").
#
# Difficulty tiers:
#   easy   — classic gotchas the player likely already knows
#   medium — needs a beat of reflection
#   hard   — wordplay, nested misdirection, or precise counting

QUESTIONS: list[dict] = [
    # ---------- EASY ----------
    {
        "question": "How many of each animal did Moses bring on the Ark?",
        "answer": r"\b(noah|none|zero|0)\b",
        "hint": "Re-read the question carefully — pay attention to the name.",
        "explanation": ("It was Noah, not Moses, who built the Ark. "
                         "Moses brought zero animals."),
        "difficulty": "easy",
    },
    {
        "question": "If a plane crashes exactly on the US/Canada border, "
                     "where do they bury the survivors?",
        "answer": r"\b(you\s*don'?t|nowhere|don'?t\s*bury|they'?re\s*alive|"
                   r"survivors|alive)\b",
        "hint": "Read every word — focus on who you'd be burying.",
        "explanation": ("You don't bury survivors — they're still alive."),
        "difficulty": "easy",
    },
    {
        "question": "A doctor gives you 3 pills and tells you to take one "
                     "every half hour. How long until you've taken them all?",
        "answer": r"\b(1|one)\s*(hour|hr|h)\b",
        "hint": "The first pill is taken at time zero, not after 30 minutes.",
        "explanation": ("Pill 1 at t=0, pill 2 at t=30 min, pill 3 at t=60 min "
                         "— a total of one hour."),
        "difficulty": "easy",
    },
    {
        "question": "Some months have 31 days, some have 30. How many "
                     "have 28?",
        "answer": r"\b(12|twelve|all|every)\b",
        "hint": "Every month contains 28 days — even the long ones.",
        "explanation": ("All 12 months have (at least) 28 days. February is "
                         "the only one that *only* has 28."),
        "difficulty": "easy",
    },
    {
        "question": "What weighs more: a pound of feathers or a pound of "
                     "lead?",
        "answer": r"\b(same|equal|neither|both|the\s*same)\b",
        "hint": "Look at the units, not the materials.",
        "explanation": ("They both weigh exactly one pound."),
        "difficulty": "easy",
    },
    {
        "question": "A farmer has 17 sheep. All but 9 die. How many are "
                     "left?",
        "answer": r"\b(9|nine)\b",
        "hint": "\"All but 9 die\" means 9 survive.",
        "explanation": ("\"All but 9\" means 9 sheep are spared, so 9 are "
                         "left."),
        "difficulty": "easy",
    },
    {
        "question": "I have two coins totaling 30 cents. One of them is not "
                     "a nickel. What are the coins?",
        "answer": r"\b(quarter\s*(and|&|\+)?\s*(a\s*)?nickel|"
                   r"nickel\s*(and|&|\+)?\s*(a\s*)?quarter|25\s*\+\s*5)\b",
        "hint": "Only ONE of the coins is not a nickel — the other can be.",
        "explanation": ("A quarter and a nickel. The quarter is the one that "
                         "is not a nickel."),
        "difficulty": "easy",
    },
    {
        "question": "Before Mount Everest was discovered, what was the "
                     "tallest mountain in the world?",
        "answer": r"\b(everest|mount\s*everest|mt\.?\s*everest)\b",
        "hint": "Discovery doesn't change a mountain's height.",
        "explanation": ("Mount Everest was always the tallest — it just "
                         "hadn't been measured yet."),
        "difficulty": "easy",
    },
    {
        "question": "If there are 5 apples on the table and you take 3, "
                     "how many do you have?",
        "answer": r"\b(3|three)\b",
        "hint": "It asks how many *you* have, not how many remain.",
        "explanation": ("You took 3, so you have 3."),
        "difficulty": "easy",
    },
    # ---------- MEDIUM ----------
    {
        "question": "What goes up but never comes down?",
        "answer": r"\b(age|your\s*age)\b",
        "hint": "It only moves in one direction — about you.",
        "explanation": ("Your age. It increases monotonically and is "
                         "famously irreversible."),
        "difficulty": "medium",
    },
    {
        "question": "Which is heavier: a kilogram of bricks or a kilogram "
                     "of butterflies?",
        "answer": r"\b(same|equal|neither|both|the\s*same)\b",
        "hint": "The unit is the giveaway again.",
        "explanation": ("A kilogram is a kilogram regardless of what it's "
                         "made of."),
        "difficulty": "medium",
    },
    {
        "question": "A man is looking at a portrait. \"Brothers and sisters "
                     "I have none, but that man's father is my father's "
                     "son.\" Who is in the portrait?",
        "answer": r"\b(his\s*son|the\s*son|son)\b",
        "hint": "\"My father's son\" — with no siblings — must be himself.",
        "explanation": ("\"My father's son\" is the speaker himself (he has "
                         "no brothers). So the portrait shows his son."),
        "difficulty": "medium",
    },
    {
        "question": "What 5-letter word becomes shorter when you add two "
                     "letters to it?",
        "answer": r"\b(short)\b",
        "hint": "It's a word that literally describes what's happening.",
        "explanation": ("\"Short\" plus \"er\" becomes \"shorter\"."),
        "difficulty": "medium",
    },
    {
        "question": "If two's company and three's a crowd, what are four "
                     "and five?",
        "answer": r"\b(9|nine)\b",
        "hint": "It's a maths question dressed up as a saying.",
        "explanation": ("4 + 5 = 9. The proverb is misdirection."),
        "difficulty": "medium",
    },
    {
        "question": "How many seconds are there in a year?",
        "answer": r"\b(12|twelve)\b",
        "hint": "Think dates, not durations — \"the second of...\".",
        "explanation": ("Twelve — January 2nd, February 2nd, March 2nd, and "
                         "so on through the year."),
        "difficulty": "medium",
    },
    {
        "question": "A rooster lays an egg on the apex of a slanted roof. "
                     "Which side does it roll down?",
        "answer": r"\b(neither|none|no\s*side|roosters?\s*don'?t|"
                   r"don'?t\s*lay)\b",
        "hint": "Check your biology — who actually lays eggs?",
        "explanation": ("Roosters are male; they don't lay eggs."),
        "difficulty": "medium",
    },
    {
        "question": "A man pushes his car to a hotel and tells the owner "
                     "he's bankrupt. Why?",
        "answer": r"\b(monopoly|board\s*game|playing\s*monopoly)\b",
        "hint": "It's a game, not real life.",
        "explanation": ("They're playing Monopoly. He landed on a hotel he "
                         "couldn't afford."),
        "difficulty": "medium",
    },
    {
        "question": "What gets wetter the more it dries?",
        "answer": r"\b(towel|a\s*towel)\b",
        "hint": "You use it after a shower.",
        "explanation": ("A towel — it absorbs water from whatever it's "
                         "drying."),
        "difficulty": "medium",
    },
    {
        "question": "If you're running a race and you overtake the person "
                     "in 2nd place, what position are you in?",
        "answer": r"\b(2nd|second)\b",
        "hint": "You took their position, not the leader's.",
        "explanation": ("You'd be in 2nd place, not 1st — you only passed "
                         "the runner who *was* 2nd."),
        "difficulty": "medium",
    },
    # ---------- HARD ----------
    {
        "question": "What has a head, a tail, but no body?",
        "answer": r"\b(coin|a\s*coin)\b",
        "hint": "You flip it.",
        "explanation": ("A coin has a head and a tail (sides) but no body."),
        "difficulty": "hard",
    },
    {
        "question": "How many times can you subtract 10 from 100?",
        "answer": r"\b(once|1|one\s*time)\b",
        "hint": "After the first subtraction, it's no longer 100.",
        "explanation": ("Only once. After that, you'd be subtracting from "
                         "90, then 80, etc. — not from 100."),
        "difficulty": "hard",
    },
    {
        "question": "Two fathers and two sons go fishing. They each catch "
                     "one fish, and they bring home only three fish. How?",
        "answer": r"\b(grand(father|son|pa)|three\s*generations|"
                   r"only\s*three\s*people)\b",
        "hint": "Three people can be \"two fathers AND two sons\".",
        "explanation": ("There are only three people: a grandfather, his "
                         "son, and his grandson. The middle person is both "
                         "a father and a son."),
        "difficulty": "hard",
    },
    {
        "question": "What word in the English language is always spelled "
                     "incorrectly?",
        "answer": r"\b(incorrectly)\b",
        "hint": "Look at the question literally.",
        "explanation": ("\"Incorrectly\" — it's the only word that's "
                         "spelled \"incorrectly\" (literally)."),
        "difficulty": "hard",
    },
    {
        "question": "A woman has 7 children, half of them are boys. How is "
                     "this possible?",
        "answer": r"\b(all\s*(are\s*)?boys|all\s*boys|every\s*one|each\s*one|"
                   r"they'?re\s*all\s*boys)\b",
        "hint": "Half of every boy is also a boy.",
        "explanation": ("All 7 are boys. Half of 7 boys is still 3.5 boys, "
                         "but every one of them is a boy — so half of them "
                         "are boys (and so is the other half)."),
        "difficulty": "hard",
    },
    {
        "question": "I am taken from a mine and shut up in a wooden case, "
                     "from which I am never released, yet I am used by "
                     "almost everyone. What am I?",
        "answer": r"\b(pencil(\s*lead)?|graphite|lead|pencil)\b",
        "hint": "It writes, but its core is locked inside wood.",
        "explanation": ("Pencil lead (graphite). It's mined, encased in "
                         "wood, and used everywhere."),
        "difficulty": "hard",
    },
    {
        "question": "What 4-letter word can be written forward, backward, "
                     "or upside down, and can still be read from left to "
                     "right?",
        "answer": r"\b(noon)\b",
        "hint": "It's a time of day with rotational symmetry.",
        "explanation": ("\"NOON\" — palindromic and (in block capitals) "
                         "rotationally symmetric."),
        "difficulty": "hard",
    },
    {
        "question": "A taxi driver is going the wrong way down a one-way "
                     "street. He passes ten police officers, none of whom "
                     "stop him. Why?",
        "answer": r"\b(walking|on\s*foot|not\s*driving|wasn'?t\s*driving)\b",
        "hint": "He's a taxi driver, but is he currently driving?",
        "explanation": ("He's walking — not driving — down the street."),
        "difficulty": "hard",
    },
    {
        "question": "What can travel around the world while staying in a "
                     "corner?",
        "answer": r"\b(stamp|a\s*stamp|postage\s*stamp)\b",
        "hint": "It rides on envelopes.",
        "explanation": ("A postage stamp — it sits in the corner of an "
                         "envelope and travels everywhere."),
        "difficulty": "hard",
    },
]

# Sanity check at import — every entry must compile cleanly.
for _q in QUESTIONS:
    re.compile(_q["answer"], re.IGNORECASE | re.VERBOSE)


# --- Per-question stats ------------------------------------------------------
@dataclass
class QStat:
    """Persistent counters for a single question across the session."""
    asked: int = 0
    correct: int = 0
    hints_used: int = 0


# --- Quiz core ---------------------------------------------------------------
DIFFICULTY_ORDER: tuple[str, ...] = ("easy", "medium", "hard")
# How many *consecutive* correct answers are needed to escalate to the
# next tier. Resets on a wrong answer.
ESCALATE_AFTER: int = 3


@dataclass
class Quiz:
    """Stateful quiz engine.

    Attributes:
        rng: optional ``random.Random`` for reproducible question order.
        difficulty: current tier, escalates with a streak of correct answers.
        streak: length of the current correct-answer streak.
        score: total correct answers this session.
        rounds: total questions asked this session.
        stats: per-question counters keyed by question index.
        hint_used: True if the player has revealed the hint for the *current*
            question (resets when :meth:`next_question` is called).
    """
    rng: random.Random = field(default_factory=random.Random)
    difficulty: str = "easy"
    streak: int = 0
    score: int = 0
    rounds: int = 0
    stats: dict[int, QStat] = field(default_factory=dict)
    hint_used: bool = False
    _current_idx: Optional[int] = None

    def _eligible_indices(self) -> list[int]:
        """Indices of questions matching the current difficulty tier."""
        return [i for i, q in enumerate(QUESTIONS)
                if q["difficulty"] == self.difficulty]

    def next_question(self) -> dict:
        """Pick and return the next question.

        The returned dict mirrors the QUESTIONS entry plus an ``index`` key
        so callers can reference the question for stats / answer-checking.
        """
        pool = self._eligible_indices()
        if not pool:
            # Defensive: shouldn't happen with the bundled QUESTIONS list.
            pool = list(range(len(QUESTIONS)))

        # Prefer questions that have been asked the least — keeps the player
        # cycling through the bank rather than re-rolling the same gotcha.
        min_asked = min(self.stats.get(i, QStat()).asked for i in pool)
        fresh = [i for i in pool
                 if self.stats.get(i, QStat()).asked == min_asked]

        idx = self.rng.choice(fresh)
        self._current_idx = idx
        self.hint_used = False

        q = QUESTIONS[idx]
        return {
            "index": idx,
            "question": q["question"],
            "answer": q["answer"],          # the regex pattern (string)
            "hint": q["hint"],
            "explanation": q["explanation"],
            "difficulty": q["difficulty"],
        }

    def use_hint(self) -> str:
        """Record a hint usage and return the hint string."""
        if self._current_idx is None:
            raise RuntimeError("call next_question() before use_hint()")
        if not self.hint_used:
            self.hint_used = True
            stat = self.stats.setdefault(self._current_idx, QStat())
            stat.hints_used += 1
        return QUESTIONS[self._current_idx]["hint"]

    def check(self, answer: str) -> dict:
        """Validate a player's answer and update session state.

        Returns:
            ``{"correct": bool, "explanation": str, "expected_pattern": str,
              "difficulty": str, "escalated": bool, "streak": int}``
        """
        if self._current_idx is None:
            raise RuntimeError("call next_question() before check()")

        q = QUESTIONS[self._current_idx]
        pattern = re.compile(q["answer"], re.IGNORECASE | re.VERBOSE)
        normalized = (answer or "").strip()
        is_correct = bool(normalized) and bool(pattern.search(normalized))

        # Update counters.
        stat = self.stats.setdefault(self._current_idx, QStat())
        stat.asked += 1
        self.rounds += 1
        escalated = False
        if is_correct:
            stat.correct += 1
            self.score += 1
            self.streak += 1
            # Escalate after a streak; cap at "hard".
            if (self.streak >= ESCALATE_AFTER
                    and self.difficulty != DIFFICULTY_ORDER[-1]):
                tier = DIFFICULTY_ORDER.index(self.difficulty)
                self.difficulty = DIFFICULTY_ORDER[tier + 1]
                self.streak = 0
                escalated = True
        else:
            self.streak = 0

        return {
            "correct": is_correct,
            "explanation": q["explanation"],
            "expected_pattern": q["answer"],
            "difficulty": q["difficulty"],
            "escalated": escalated,
            "streak": self.streak,
        }

    def state(self) -> dict:
        """Snapshot the session state. Useful for the GUI/TUI status bar."""
        accuracy = (self.score / self.rounds) if self.rounds else 0.0
        return {
            "score": self.score,
            "rounds": self.rounds,
            "accuracy": accuracy,
            "difficulty": self.difficulty,
            "streak": self.streak,
            "hint_used": self.hint_used,
            "stats": {i: vars(s) for i, s in self.stats.items()},
        }


# --- CLI ---------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Quiz of riddle-style trick questions."
    )
    parser.add_argument("-r", "--rounds", type=int, default=10,
                        help="number of questions to ask (default: 10)")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="seed for reproducible question order")
    return parser.parse_args(argv)


def _ascii_bar(score: int, total: int, width: int = 20) -> str:
    if total <= 0:
        return "[" + "." * width + "]"
    filled = int(round(width * score / total))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    rng = random.Random(args.seed)
    quiz = Quiz(rng=rng)

    print("Trick Questions — read carefully, the obvious answer is "
          "rarely right.")
    print(f"You will get {args.rounds} questions. Type 'hint' for a "
          "nudge, 'quit' to bail.\n")

    asked = 0
    while asked < args.rounds:
        item = quiz.next_question()
        print(f"[{quiz.difficulty.upper():6s}] Q{asked + 1}: "
              f"{item['question']}")

        answered = False
        while not answered:
            try:
                raw = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                return

            low = raw.lower()
            if low in {"quit", "exit", "q"}:
                print("Quitting early. Final stats below.\n")
                _print_summary(quiz)
                return
            if low == "hint":
                print(f"Hint: {quiz.use_hint()}")
                continue
            if not raw:
                print("(type an answer, or 'hint' / 'quit')")
                continue

            result = quiz.check(raw)
            answered = True
            if result["correct"]:
                print(f"Correct! {result['explanation']}")
                if result["escalated"]:
                    print(f"** Difficulty escalated to "
                          f"{quiz.difficulty.upper()} **")
            else:
                print(f"Nope. {result['explanation']}")
            asked += 1
            print(f"Score: {quiz.score}/{quiz.rounds}  "
                  f"{_ascii_bar(quiz.score, quiz.rounds)}\n")

    _print_summary(quiz)


def _print_summary(quiz: Quiz) -> None:
    s = quiz.state()
    print("=" * 48)
    print(f"Final score: {s['score']}/{s['rounds']}  "
          f"({s['accuracy'] * 100:.0f}%)")
    print(f"Final tier:  {s['difficulty']}")
    if s["stats"]:
        worst = sorted(
            s["stats"].items(),
            key=lambda kv: (kv[1]["correct"] / max(1, kv[1]["asked"])),
        )[:3]
        if worst:
            print("\nMost-missed questions this session:")
            for idx, st in worst:
                acc = st["correct"] / max(1, st["asked"])
                print(f"  - {QUESTIONS[idx]['question'][:60]}... "
                      f"({st['correct']}/{st['asked']}, {acc * 100:.0f}%)")


if __name__ == "__main__":
    main()
