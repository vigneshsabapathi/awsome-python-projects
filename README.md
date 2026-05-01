# Awesome Python Projects

A collection of mini Python projects, each in its own subfolder. Most ship as a CLI plus a CustomTkinter desktop GUI and a Textual terminal UI.

## Projects

| Folder | Description | Flavors |
|---|---|---|
| [`bagels/`](bagels/README.md) | Deductive 3-digit guessing game with Fermi / Pico / Bagels clues. | CLI · GUI · TUI |
| [`birthday_paradox/`](birthday_paradox/README.md) | Monte Carlo simulation of birthday-collision probability with theoretical curve, 95% Wilson CI, embedded matplotlib chart. | CLI · GUI · TUI |
| [`bitmap_message/`](bitmap_message/README.md) | Render a message as ASCII art using a 2-tone bitmap and modulo-cycled characters. Four shape presets. | CLI · GUI · TUI |

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
```

Each subfolder's README has the full list of run commands and flavor-specific notes.

## Structure

```
awsome-python-projects/
├── .venv/                      # Shared virtual environment (uv-managed)
├── requirements.txt            # Shared dependencies
├── bagels/
│   ├── bagels.py               # CLI
│   ├── bagels_gui.py           # CustomTkinter desktop
│   ├── bagels_tui.py           # Textual terminal
│   └── README.md
├── birthday_paradox/
│   ├── birthday_paradox.py
│   ├── birthday_paradox_gui.py
│   ├── birthday_paradox_tui.py
│   └── README.md
└── bitmap_message/
    ├── bitmap_message.py
    ├── bitmap_message_gui.py
    ├── bitmap_message_tui.py
    └── README.md
```
