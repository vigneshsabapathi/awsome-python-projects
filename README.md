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
| [`caesar_hacker/`](caesar_hacker/README.md) | Brute-forces a Caesar cipher: ranks all 26 shifts by chi-squared + word-hit hybrid score, with letter-overlap diff. | CLI · GUI · TUI |
| [`cho_han/`](cho_han/README.md) | Edo-period Japanese dice gambling. Animated cup, bankroll history chart, Monte Carlo ruin probability. | CLI · GUI · TUI |
| [`countdown/`](countdown/README.md) | Visual timer rendered as hand-authored seven-segment ASCII digits. Pomodoro mode, stopwatch toggle. | CLI · GUI · TUI |
| [`deep_cave/`](deep_cave/README.md) | Procedural infinite-scroll cave via constrained random walk. Hazards (gems, water, boulders), seeded reproducible runs. | CLI · GUI · TUI |
| [`dice_math/`](dice_math/README.md) | Speed math drill on rolled dice. Modes: sum / product / max / pair. Persisted JSON leaderboard. | CLI · GUI · TUI |
| [`etching/`](etching/README.md) | Etch-A-Sketch drawing — arrow keys move a pen on a canvas. 8-direction movement, color cycle, PNG export, playback replay. | CLI · GUI · TUI |
| [`factor_finder/`](factor_finder/README.md) | Divisors + prime factorization with Miller-Rabin + Pollard's rho. σ₀, σ₁, φ, prime/perfect/abundant/deficient classification. | CLI · GUI · TUI |
| [`forest_fire/`](forest_fire/README.md) | Drossel-Schwabl forest-fire CA via NumPy shifts. Wind direction, lightning, near-critical density. | CLI · GUI · TUI |
| [`four_in_a_row/`](four_in_a_row/README.md) | Connect Four with α-β minimax AI (depths 2/4/6), center-out ordering, transposition table, animated drops. | CLI · GUI · TUI |
| [`guess_number/`](guess_number/README.md) | Higher/lower with binary-search hint button + entropy display. Reverse mode (computer guesses optimally). | CLI · GUI · TUI |
| [`fortune_ball/`](fortune_ball/README.md) | Magic 8-ball with sentiment-balanced answer pool, animated shake, deterministic "remember mode" via SHA-256-seeded RNG. | CLI · GUI · TUI |
| [`hacking/`](hacking/README.md) | Fallout-style password hacking minigame with Mastermind-like likeness clues + Shannon-entropy hint. | CLI · GUI · TUI |
| [`hangman/`](hangman/README.md) | Word-guess game with hand-drawn ASCII gallows + **Evil Hangman** adversarial mode. | CLI · GUI · TUI |
| [`hex_grid/`](hex_grid/README.md) | Honeycomb ASCII tilings with axial / cube / offset coordinate overlays + SVG export. | CLI · GUI · TUI |
| [`hourglass/`](hourglass/README.md) | ASCII hourglass with angle-of-repose grain settling + age-graded color fade. | CLI · GUI · TUI |
| [`hungry_robots/`](hungry_robots/README.md) | Grid chase game: robots step toward you, collisions create wrecks. Safe-teleport + level progression. | CLI · GUI · TUI |
| [`jaccuse/`](jaccuse/README.md) | Film-noir mystery deduction with weighted-witness reliability (10% lie rate) + auto-deduce hints. | CLI · GUI · TUI |
| [`langton_ant/`](langton_ant/README.md) | Langton's Ant CA with multi-color "Turmite" rule strings (RL / RLR / LLRR / LRRRRRLLR). | CLI · GUI · TUI |
| [`leetspeak/`](leetspeak/README.md) | Probabilistic l33t-text converter with multi-char `at`→`@` substitutions and brute-force decode panel. | CLI · GUI · TUI |
| [`lucky_stars/`](lucky_stars/README.md) | Star-roll fortune-telling with seedable readings + JSON history + compatibility scoring. | CLI · GUI · TUI |
| [`mancala/`](mancala/README.md) | Kalah-variant Mancala with α-β minimax AI (easy/medium/hard/expert), animated stone-sowing. | CLI · GUI · TUI |
| [`maze_runner_2d/`](maze_runner_2d/README.md) | Top-down ASCII maze with 3 generators (recursive backtracker / Prim / Wilson) + BFS solution overlay + fog-of-war. | CLI · GUI · TUI |
| [`maze_runner_3d/`](maze_runner_3d/README.md) | First-person ASCII pseudo-3D dungeon view with mini-map, torch-radius dimming, occasional goblin sprites. | CLI · GUI · TUI |
| [`million_dice/`](million_dice/README.md) | NumPy-vectorized dice statistics with embedded matplotlib + CLT convergence panel (N=1..5). | CLI · GUI · TUI |
| [`mondrian/`](mondrian/README.md) | Recursive-subdivision generative art with Mondrian / Rothko / Bauhaus presets and PNG export. | CLI · GUI · TUI |
| [`monty_hall/`](monty_hall/README.md) | Monty Hall puzzle with N-door generalization, Wilson CI bars, and step-by-step Bayesian derivation tab. | CLI · GUI · TUI |
| [`mult_table/`](mult_table/README.md) | Multiplication table with 12-stop heatmap and modular-arithmetic mode showing Z/nZ ring patterns. | CLI · GUI · TUI |
| [`bottles/`](bottles/README.md) | "99 Bottles of Beer" lyrics generator covering both classic and **niNety nniinE** random-case remix variants. | CLI · GUI · TUI |
| [`numeral_systems/`](numeral_systems/README.md) | Multi-base converter (2..36) + Roman numerals + fractional bases + two's-complement (8/16/32/64-bit). | CLI · GUI · TUI |
| [`periodic_table/`](periodic_table/README.md) | All 118 elements with category-colored tiles, search, details panel, and quiz mode. | CLI · GUI · TUI |
| [`pig_latin/`](pig_latin/README.md) | Pig Latin translator with proper-noun preservation, contractions, hyphens, plus Greek and Ubbi-Dubbi modes. | CLI · GUI · TUI |
| [`powerball/`](powerball/README.md) | Lottery simulation with EV calculator, break-even jackpot solver, lifetime-loss model. | CLI · GUI · TUI |
| [`primes/`](primes/README.md) | Sieve of Eratosthenes + segmented + Miller-Rabin primality + **Ulam spiral** visualization. | CLI · GUI · TUI |
| [`progress_bar/`](progress_bar/README.md) | Five progress bar styles (blocks/simple/dots/gradient/spinner) with EMA-smoothed ETA. | CLI · GUI · TUI |
| [`rainbow/`](rainbow/README.md) | Animated rainbow text with HSV→RGB→ANSI-256 quantization, lolcat phase shift, arcs and bands. | CLI · GUI · TUI |
| [`rps/`](rps/README.md) | Rock Paper Scissors with **Markov-predictor** AI mode + always-win cheat mode (covers #59 + #60). | CLI · GUI · TUI |
| [`rot13/`](rot13/README.md) | ROT13 cipher with self-inverse demo and ROT47 printable-ASCII variant. | CLI · GUI · TUI |
| [`rotating_cube/`](rotating_cube/README.md) | 3D wireframe cube projected to ASCII via rotation matrices. Toggle to tetra / octa / dodecahedron. | CLI · GUI · TUI |
| [`ur/`](ur/README.md) | Royal Game of Ur (Finkel reconstruction) with H-shaped board and **expectimax** AI. | CLI · GUI · TUI |
| [`seven_segment/`](seven_segment/README.md) | Reusable seven-segment ASCII display library with LCD/LED color presets and warm-up animation. | CLI · GUI · TUI |
| [`shining_carpet/`](shining_carpet/README.md) | Animated tessellated carpet patterns (Shining hex / Persian medallion / Bauhaus weave) with click-stamp twist. | CLI · GUI · TUI |
| [`simple_sub/`](simple_sub/README.md) | Substitution cipher with **simulated-annealing auto-crack** + frequency analysis chart. | CLI · GUI · TUI |
| [`sine_message/`](sine_message/README.md) | Text wobbling along a sine wave with phase scroll, multi-wave overlay, and Lissajous mode. | CLI · GUI · TUI |
| [`sliding_puzzle/`](sliding_puzzle/README.md) | 15-puzzle with **A\*** solver (Manhattan heuristic), animated tile slides, parity-check, n=3/4/5. | CLI · GUI · TUI |
| [`snail_race/`](snail_race/README.md) | 4-snail race with personality-based step distributions, sportsbook odds, and bankroll betting. | CLI · GUI · TUI |
| [`soroban/`](soroban/README.md) | Japanese abacus rendering with two-way number↔beads sync and step-by-step addition animation. | CLI · GUI · TUI |
| [`sound_mimic/`](sound_mimic/README.md) | Simon-says memory game with `winsound.Beep` audio, 4/6/8 pad modes, speed-up rounds. | CLI · GUI · TUI |
| [`spongecase/`](spongecase/README.md) | sPoNgEbOb mocking-text converter with intensity slider, deterministic mode, and 🧽 at max. | CLI · GUI · TUI |
| [`sudoku/`](sudoku/README.md) | 9×9 sudoku with backtracking + MRV solver, uniqueness-preserving generator, hint button. | CLI · GUI · TUI |

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
