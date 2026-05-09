"""Clickbait Headline Generator — CLI.

Combines templates with category-aware word lists to produce sensationalized
headlines. Pure functions are exposed for the GUI/TUI front-ends.

Run:
    uv run python clickbait/clickbait.py            # one headline
    uv run python clickbait/clickbait.py --batch 5  # five at once
    uv run python clickbait/clickbait.py --category tech --seed 42
"""
from __future__ import annotations

import argparse
import random
import re
from typing import Iterable

# --- Templates ---------------------------------------------------------------
# Slot tokens: {number}, {adjective}, {noun}, {outcome}
# Authored from scratch — no external sources.
TEMPLATES: tuple[str, ...] = (
    "{number} {adjective} {noun} that will {outcome}",
    "You won't believe what these {adjective} {noun} did — {outcome}",
    "Top {number} {adjective} {noun} doctors don't want you to see (#{small} will {outcome})",
    "This {adjective} {noun} is going viral and it's about to {outcome}",
    "{number} reasons {noun} are secretly {adjective} — number {small} will {outcome}",
    "Scientists are stunned: {adjective} {noun} can {outcome}",
    "How one {adjective} {noun} managed to {outcome} in under {small} minutes",
    "{number} {adjective} {noun} hacks that will {outcome} (no one is talking about #{small})",
    "Local mom discovers {adjective} {noun} trick that experts say will {outcome}",
    "Forget everything you knew: {noun} are actually {adjective}, and they {outcome}",
    "The {adjective} truth about {noun} nobody is brave enough to admit — it will {outcome}",
    "I tried {number} {adjective} {noun} for a week — the results will {outcome}",
)

# --- Word banks --------------------------------------------------------------
# Per-category word lists for the {adjective}, {noun}, {outcome} slots.
# Each category is self-contained so a headline never mixes vibes.
GENERAL: dict[str, list[str]] = {
    "adjective": [
        "shocking", "unbelievable", "wild", "mysterious", "outrageous",
        "jaw-dropping", "bizarre", "mind-bending", "scandalous", "legendary",
        "ridiculous", "earth-shattering",
    ],
    "noun": [
        "secrets", "habits", "tricks", "moments", "stories", "facts",
        "twists", "mistakes", "revelations", "lessons", "moves", "rituals",
    ],
    "outcome": [
        "change your life forever",
        "blow your mind",
        "leave you speechless",
        "make you question everything",
        "ruin your weekend in the best way",
        "unlock your true potential",
        "haunt your dreams (in a good way)",
        "redefine what you thought possible",
        "make you cancel your plans",
        "trigger an existential crisis",
    ],
}

ANIMALS: dict[str, list[str]] = {
    "adjective": [
        "fluffy", "feral", "majestic", "tiny", "sneaky", "chaotic",
        "ferocious", "well-dressed", "secretly genius", "tactical",
    ],
    "noun": [
        "cats", "dogs", "otters", "raccoons", "pigeons", "axolotls",
        "owls", "goats", "octopuses", "capybaras",
    ],
    "outcome": [
        "steal your heart",
        "outsmart your toddler",
        "take over your timeline",
        "out-cuddle your therapist",
        "make you reconsider your career",
        "turn your house upside down",
        "rewrite the laws of cuteness",
    ],
}

TECH: dict[str, list[str]] = {
    "adjective": [
        "AI-powered", "open-source", "blockchain-fueled", "deprecated",
        "quantum", "low-code", "serverless", "self-hosted", "edge-deployed",
        "vibes-based", "production-grade",
    ],
    "noun": [
        "frameworks", "side projects", "startups", "engineers", "kernels",
        "compilers", "kubernetes clusters", "regex tricks", "type systems",
        "shell aliases",
    ],
    "outcome": [
        "make recruiters slide into your DMs",
        "get you promoted to staff",
        "10x your debugging speed",
        "end the tabs vs spaces war",
        "ship to prod on a Friday",
        "make standups bearable again",
        "replace your entire backend",
    ],
}

FOOD: dict[str, list[str]] = {
    "adjective": [
        "buttery", "forbidden", "unholy", "gourmet", "deep-fried",
        "five-ingredient", "bougie", "grandma-approved", "viral",
        "weirdly spicy",
    ],
    "noun": [
        "pasta hacks", "breakfast tacos", "ramen upgrades", "cookie recipes",
        "sandwich combos", "smoothies", "brunch tricks", "pantry staples",
        "midnight snacks",
    ],
    "outcome": [
        "ruin all other meals for you",
        "make your in-laws cry (happy tears)",
        "be your new Sunday ritual",
        "convert any picky eater",
        "earn you a Michelin star at home",
        "reset your relationship with carbs",
    ],
}

MONEY: dict[str, list[str]] = {
    "adjective": [
        "passive-income", "tax-free", "millionaire-tier", "frugal",
        "high-yield", "recession-proof", "side-hustle", "boring-but-rich",
        "unhinged", "boomer-approved",
    ],
    "noun": [
        "money habits", "investing tricks", "budget hacks", "side hustles",
        "spending traps", "wealth secrets", "credit moves", "savings plans",
    ],
    "outcome": [
        "retire you a decade early",
        "double your net worth by Friday",
        "make your accountant nervous",
        "shut down your overdraft alerts forever",
        "fund your next vacation (and the one after)",
        "make compound interest your best friend",
    ],
}

CATEGORIES: dict[str, dict[str, list[str]]] = {
    "general": GENERAL,
    "animals": ANIMALS,
    "tech": TECH,
    "food": FOOD,
    "money": MONEY,
}


# --- Token utilities ---------------------------------------------------------
TOKEN_RE = re.compile(r"\{(\w+)\}")


def find_slots(template: str) -> list[str]:
    """Return the ordered list of slot names referenced in ``template``."""
    return TOKEN_RE.findall(template)


def _pick(rng: random.Random, words: Iterable[str]) -> str:
    """Pick a word from a non-empty iterable. Raises on empty input."""
    pool = list(words)
    if not pool:
        raise ValueError("word list is empty")
    return rng.choice(pool)


def _resolve_slot(slot: str, rng: random.Random,
                  bank: dict[str, list[str]]) -> str:
    """Resolve one slot token to a word.

    ``{number}`` and ``{small}`` are synthesized; everything else comes from
    the chosen category's word bank.
    """
    if slot == "number":
        # Clickbait list-counts skew to suspiciously specific numerals.
        return str(rng.choice([5, 7, 9, 10, 12, 13, 15, 17, 21, 27, 99, 101]))
    if slot == "small":
        return str(rng.randint(2, 9))
    if slot not in bank:
        raise KeyError(f"missing slot '{slot}' in word bank")
    return _pick(rng, bank[slot])


def _fill_template(template: str, rng: random.Random,
                   bank: dict[str, list[str]]) -> str:
    """Replace every ``{token}`` in ``template`` with a resolved word."""
    return TOKEN_RE.sub(
        lambda m: _resolve_slot(m.group(1), rng, bank), template
    )


# --- Public API --------------------------------------------------------------
def generate_headline(rng: random.Random | None = None,
                      category: str | None = None) -> str:
    """Return one clickbait headline.

    Args:
        rng: Optional ``random.Random`` for deterministic / shareable seeds.
        category: One of ``CATEGORIES`` keys; defaults to ``"general"``.
    """
    rng = rng or random.Random()
    cat_key = (category or "general").lower()
    if cat_key not in CATEGORIES:
        raise ValueError(
            f"unknown category {category!r}; choose from {sorted(CATEGORIES)}"
        )
    bank = CATEGORIES[cat_key]
    template = rng.choice(TEMPLATES)
    headline = _fill_template(template, rng, bank)
    # Capitalize the first character without nuking the rest of the casing.
    return headline[:1].upper() + headline[1:]


def generate_batch(n: int, rng: random.Random | None = None,
                   category: str | None = None) -> list[str]:
    """Return ``n`` headlines using the same RNG / category settings."""
    if n < 0:
        raise ValueError("n must be non-negative")
    rng = rng or random.Random()
    return [generate_headline(rng, category) for _ in range(n)]


# --- Outrage meter (creative twist) -----------------------------------------
SUPERLATIVES: frozenset[str] = frozenset({
    "shocking", "unbelievable", "jaw-dropping", "mind-bending", "scandalous",
    "legendary", "outrageous", "ridiculous", "earth-shattering", "wild",
    "bizarre", "mysterious", "forbidden", "unhinged", "unholy", "viral",
    "stunned", "secret", "secrets", "secretly", "hacks", "trick", "tricks",
    "won't", "never", "everything", "nobody", "forever",
})


def outrage_score(headline: str) -> int:
    """0-100 score: how dense the superlatives / clickbait words are.

    Counts hits from ``SUPERLATIVES`` and the presence of digits/exclamations,
    normalized against the headline's word count and capped at 100.
    """
    words = re.findall(r"[A-Za-z']+", headline.lower())
    if not words:
        return 0
    hits = sum(1 for w in words if w in SUPERLATIVES)
    # Bonus signals: digits and shouty punctuation.
    if re.search(r"\d", headline):
        hits += 1
    if "!" in headline:
        hits += 1
    density = hits / len(words)
    return min(100, int(round(density * 250)))


# --- CLI ---------------------------------------------------------------------
def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate sensationalized clickbait headlines."
    )
    parser.add_argument("-n", "--batch", type=int, default=1,
                        help="how many headlines to generate (default: 1)")
    parser.add_argument("-c", "--category", default="general",
                        choices=sorted(CATEGORIES),
                        help="word-bank category")
    parser.add_argument("-s", "--seed", type=int, default=None,
                        help="seed for reproducible / shareable output")
    parser.add_argument("--score", action="store_true",
                        help="print the outrage score next to each headline")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    rng = random.Random(args.seed)
    headlines = generate_batch(args.batch, rng=rng, category=args.category)
    for h in headlines:
        if args.score:
            print(f"[{outrage_score(h):3d}] {h}")
        else:
            print(h)


if __name__ == "__main__":
    main()
