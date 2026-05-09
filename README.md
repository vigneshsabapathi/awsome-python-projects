# Awesome Python Projects

A collection of mini Python projects, each in its own subfolder. Most ship as a CLI plus a CustomTkinter desktop GUI and a Textual terminal UI.

## Projects

| Folder | Description | Flavors |
|---|---|---|
| [`bagels/`](bagels/README.md) | Deductive 3-digit guessing game with Fermi / Pico / Bagels clues. | CLI · GUI · TUI |
| [`birthday_paradox/`](birthday_paradox/README.md) | Monte Carlo simulation of birthday-collision probability with theoretical curve, 95% Wilson CI, embedded matplotlib chart. | CLI · GUI · TUI |
| [`bitmap_message/`](bitmap_message/README.md) | Render a message as ASCII art using a 2-tone bitmap and modulo-cycled characters. Four shape presets. | CLI · GUI · TUI |
| [`blackjack/`](blackjack/README.md) | Card game vs. dealer with soft/hard aces, basic-strategy hint button, 3:2 natural payout, running bankroll. | CLI · GUI · TUI |
| [`caesar_cipher/`](caesar_cipher/README.md) | Letter-shift cipher with chi-squared brute-force panel and one-click auto-crack. | CLI · GUI · TUI |
| [`calendar_maker/`](calendar_maker/README.md) | Month/year calendar from scratch via Zeller's congruence. US federal holidays + leap-year rules. Year-view toggle. | CLI · GUI · TUI |
| [`clickbait/`](clickbait/README.md) | Template-based headline generator across 5 categories with seedable RNG and an outrage-score meter. | CLI · GUI · TUI |
| [`collatz/`](collatz/README.md) | Hailstone sequence with embedded matplotlib (linear/log toggle) + stopping-time scatter for n=1..N. | CLI · GUI · TUI |
| [`diamonds/`](diamonds/README.md) | ASCII diamond generator (outlined or filled, sizes 1..30) with grow animation. | CLI · GUI · TUI |
| [`dice_roller/`](dice_roller/README.md) | Parses `NdM±K` plus extended `4d6kh3` keep-highest. Monte Carlo histogram, seedable, history. | CLI · GUI · TUI |
| [`fibonacci/`](fibonacci/README.md) | Five algorithms (iter / naive / memo / matrix-exp / Binet) with side-by-side benchmark and φ convergence chart. | CLI · GUI · TUI |
| [`game_of_life/`](game_of_life/README.md) | Conway's GoL via NumPy 8-shift vectorization. Glider / pulsar / Gosper gun patterns, toroidal edges, trail fade. | CLI · GUI · TUI |
| [`hangman/`](hangman/README.md) | Word-guess game with hand-drawn ASCII gallows + **Evil Hangman** adversarial mode. | CLI · GUI · TUI |

## Setup

This project uses [uv](https://github.com/astral-sh/uv) instead of pip.

```bash
# Create the virtual environment (already done in the repo)
uv venv .venv

# Activate it
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (bash / git-bash):
source .venv/Scripts/activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Add a new dependency
uv pip install <package>
uv pip freeze > requirements.txt
```

## Running a project

```bash
uv run python <folder>/<entry>.py
```

For example:

```bash
uv run python bagels/bagels_gui.py
uv run python birthday_paradox/birthday_paradox_gui.py
uv run python bitmap_message/bitmap_message_gui.py
uv run python game_of_life/game_of_life_gui.py
```

Each subfolder's README has the full list of run commands and flavor-specific notes.

## Inspiration

Most projects are reimagined from Al Sweigart's *The Big Book of Small Python Projects* ([inventwithpython.com/bigbookpython](https://inventwithpython.com/bigbookpython/)). All implementations here are written from scratch — no source code copied from the book — and most projects add at least one creative twist (vectorization, brute-force panels, alternative algorithms, embedded charts, adversarial modes, etc.) over the original CLI.
