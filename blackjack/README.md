# Blackjack

Classic Blackjack (21) — try to beat the dealer without busting. Aces count as 1 or 11, dealer stands on 17, naturals pay 3:2. Three flavors share one game-logic core:

| Version | File | Stack |
|---------|------|-------|
| CLI | `blackjack.py` | stdlib |
| Modern desktop GUI | `blackjack_gui.py` | CustomTkinter |
| Modern terminal UI | `blackjack_tui.py` | Textual |

## Rules

- Player and dealer each start with 2 cards. Dealer's first card is the **hole card** (face down).
- **Hit** — draw another card. **Stand** — end your turn.
- **Double** — double your bet, draw exactly one card, then auto-stand. Only legal as your first decision.
- A two-card 21 is a **natural blackjack** and pays **3:2**.
- Dealer reveals the hole card and hits while their total is below **17** (stands on all 17s, including soft 17).
- Closer to 21 wins. Going over 21 is a **bust** (instant loss). Equal totals **push** (no money moves).

## Run

```bash
# CLI
uv run python blackjack/blackjack.py

# Desktop GUI (CustomTkinter)
uv run python blackjack/blackjack_gui.py

# Terminal UI (Textual)
uv run python blackjack/blackjack_tui.py
```

## TUI bindings

| Key | Action |
|-----|--------|
| `h` | Hit |
| `s` | Stand |
| `d` | Double (when legal) |
| `n` | New hand |
| `?` | Basic-strategy hint |
| `Ctrl+Q` | Quit |

## Features

- **Visual cards** in both GUI and TUI — rectangles with rank + suit, red for hearts/diamonds, dark for spades/clubs. The dealer's hole card stays face down (`?`) until you stand or bust.
- **Running bankroll** — start with $100, $10 per hand. Win/loss/push tracked across hands. Out-of-chips ends the run.
- **3:2 blackjack payout** — a natural 21 pays 1.5× the bet (the casino-standard player edge).
- **Basic-strategy hint** — press the **Hint** button (GUI) or `?` (TUI) at any decision and the chart-correct play is shown (Hit / Stand / Double). Hard and soft totals both supported. The chart is hard-coded for the S17 (dealer stands on soft 17) variant.
- **Soft-total annotation** — the player's total reads `(soft)` whenever an Ace is still counted as 11, so you know your hand can't bust on the next hit.
- **Animated dealer play** — the dealer draws one card every ~0.5s in both GUI and TUI so each draw is visible.

## Architecture

The CLI module `blackjack.py` is the single source of truth for game logic. Both front-ends import its pure functions:

| Symbol | What it does |
|--------|--------------|
| `Card` | `namedtuple('Card', ['rank', 'suit'])` |
| `SUITS`, `RANKS`, `RANK_VALUES` | Card constants |
| `make_deck()` | Returns a fresh shuffled 52-card deck |
| `deal_card(deck)` | Pops a card off the deck (auto-reshuffles if empty) |
| `hand_value(cards)` | Best total ≤ 21; demotes Aces 11 → 1 as needed |
| `is_soft(cards)` | True if at least one Ace is still counted as 11 |
| `is_blackjack(cards)` | True for a 2-card 21 |
| `is_bust(cards)` | True if total > 21 |
| `dealer_should_hit(cards)` | `True` while total < 17 |
| `basic_strategy_hint(player, upcard)` | `'H'`, `'S'`, or `'D'` |
| `STARTING_BANKROLL`, `DEFAULT_BET`, `BLACKJACK_PAYOUT` | Game constants |

`hand_value` accepts both `Card` namedtuples and bare rank strings (`['A', '7']`) so the function is trivially testable without building a full deck.

## Notes

- **Aces are tricky.** Each Ace starts at 11; demote one to 1 each iteration while the total exceeds 21. Never demote past 1.
- **Soft vs hard hand.** A 'soft' hand has an un-demoted Ace, so the next hit can never bust — that's why basic strategy is more aggressive on soft totals.
- **No splits.** Splitting pairs adds significant UI complexity (two parallel hands per round). Doubling and the basic-strategy hint cover the most common decisions; splits could be a future addition.
- **House edge.** With S17, 3:2 naturals, no surrender, and a single deck, basic strategy gets the player to roughly a 0.2–0.5% disadvantage. Add the hint button and watch your bankroll last longer.
