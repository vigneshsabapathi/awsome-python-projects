"""Magic Fortune Ball - CLI.

Ask the ball a yes/no question, get one of 25 hand-authored responses
themed positive (10), neutral (5), or negative (10). Pure functions are
exposed so the GUI/TUI front-ends can share the same response pool.

Run:
    uv run python fortune_ball/fortune_ball.py
    uv run python fortune_ball/fortune_ball.py --question "Will it rain?"
    uv run python fortune_ball/fortune_ball.py --bias 0.7 --seed 42
    uv run python fortune_ball/fortune_ball.py --remember --question "Will it rain?"
"""
from __future__ import annotations

import argparse
import hashlib
import random
from typing import Iterable

# --- Response pool ----------------------------------------------------------
# Authored from scratch. Three sentiment buckets so the GUI/TUI can color-code
# answers and so the bias knob has something meaningful to tilt.

POSITIVE: tuple[str, ...] = (
    "Yes, without a doubt.",
    "All signs point to yes.",
    "The stars align in your favor.",
    "Absolutely - press on.",
    "It is written: yes.",
    "Fortune smiles - go for it.",
    "The answer is a clear yes.",
    "Trust the path, it leads forward.",
    "The omens are bright.",
    "Yes, and sooner than you think.",
)

NEUTRAL: tuple[str, ...] = (
    "The answer is hidden in mist.",
    "Ask again when the moon turns.",
    "Even the ball is unsure today.",
    "Outcome uncertain - check back later.",
    "Reply hazy - try once more.",
)

NEGATIVE: tuple[str, ...] = (
    "No - the path is closed.",
    "Don't count on it.",
    "The omens warn against it.",
    "My sources say no.",
    "Not in this lifetime.",
    "Walk away. The answer is no.",
    "Definitely not - the stars say so.",
    "Better not pursue this one.",
    "The ball shakes its head: no.",
    "No, and you already knew it.",
)

# Public sentiment registry used by both front-ends.
SENTIMENTS: dict[str, tuple[str, ...]] = {
    "positive": POSITIVE,
    "neutral": NEUTRAL,
    "negative": NEGATIVE,
}


# --- Core API ---------------------------------------------------------------
def all_responses() -> list[tuple[str, str]]:
    """Return ``(answer, sentiment)`` for every authored response."""
    out: list[tuple[str, str]] = []
    for sentiment, pool in SENTIMENTS.items():
        out.extend((ans, sentiment) for ans in pool)
    return out


def _pick(rng: random.Random, pool: Iterable[str]) -> str:
    bag = list(pool)
    if not bag:
        raise ValueError("response pool is empty")
    return rng.choice(bag)


def ask(
    question: str,
    rng: random.Random | None = None,
    *,
    bias: float = 0.5,
    remember: bool = False,
) -> dict:
    """Ask the fortune ball one yes/no question.

    Args:
        question: The question being asked. Used as the seed when
            ``remember=True`` so the same wording yields the same answer.
        rng: Optional ``random.Random`` for deterministic output.
        bias: Slider in ``[0.0, 1.0]``. ``0.5`` is the balanced 10/5/10 pool;
            ``> 0.5`` tilts the pool toward positive answers; ``< 0.5``
            tilts toward negative. Neutral always retains its 5-slot share
            so "hazy" answers never disappear.
        remember: If true, derive the RNG seed from ``question`` so the ball
            "remembers" what it told you - same question, same answer.

    Returns:
        ``{"answer": str, "sentiment": "positive"|"neutral"|"negative"}``
    """
    if not 0.0 <= bias <= 1.0:
        raise ValueError(f"bias must be in [0, 1], got {bias!r}")
    if not isinstance(question, str):
        raise TypeError("question must be a string")
    stripped = question.strip()
    if not stripped:
        raise ValueError("question must not be empty")

    if remember:
        # Stable seed across runs / processes: hash the lowercased question.
        digest = hashlib.sha256(stripped.lower().encode("utf-8")).digest()
        rng = random.Random(int.from_bytes(digest[:8], "big"))
    elif rng is None:
        rng = random.Random()

    sentiment = _weighted_sentiment(rng, bias)
    answer = _pick(rng, SENTIMENTS[sentiment])
    return {"answer": answer, "sentiment": sentiment}


def _weighted_sentiment(rng: random.Random, bias: float) -> str:
    """Pick a sentiment label using the bias slider.

    ``bias`` re-weights positive vs negative around a fixed neutral share
    proportional to the authored pool (5 / 25 = 0.2). Default ``bias=0.5``
    reproduces the natural 10/5/10 ratio.
    """
    neutral_share = len(NEUTRAL) / sum(len(p) for p in SENTIMENTS.values())
    remaining = 1.0 - neutral_share
    pos_share = remaining * bias
    neg_share = remaining * (1.0 - bias)
    roll = rng.random()
    if roll < pos_share:
        return "positive"
    if roll < pos_share + neg_share:
        return "negative"
    return "neutral"


# --- CLI --------------------------------------------------------------------
SENTIMENT_GLYPH: dict[str, str] = {
    "positive": "[+]",
    "neutral": "[~]",
    "negative": "[-]",
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ask the Magic Fortune Ball a yes/no question.",
    )
    parser.add_argument(
        "-q", "--question",
        help="The question. If omitted, you'll be prompted.",
    )
    parser.add_argument(
        "-b", "--bias", type=float, default=0.5,
        help="Sentiment bias slider (0.0=all-negative, 1.0=all-positive). "
             "Default 0.5 keeps the natural 10/5/10 mix.",
    )
    parser.add_argument(
        "-s", "--seed", type=int, default=None,
        help="Seed the RNG for reproducible answers.",
    )
    parser.add_argument(
        "--remember", action="store_true",
        help="Same question always gets the same answer (the ball 'knows you').",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    question = args.question
    if question is None:
        try:
            question = input("Ask the Magic Fortune Ball a yes/no question:\n> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
    if not question.strip():
        print("(no question - the ball stays silent)")
        return

    rng = random.Random(args.seed) if args.seed is not None else None
    result = ask(question, rng=rng, bias=args.bias, remember=args.remember)
    glyph = SENTIMENT_GLYPH[result["sentiment"]]
    print()
    print(f"  ~~ The ball stirs ~~")
    print(f"  {glyph} {result['answer']}")
    print(f"     (sentiment: {result['sentiment']})")


if __name__ == "__main__":
    main()
