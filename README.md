# Awesome Python Projects

A collection of mini Python projects, each in its own subfolder.

## Setup

This project uses [uv](https://github.com/astral-sh/uv) instead of pip.

```bash
# Create the virtual environment (already done)
uv venv .venv

# Activate it
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (bash/git-bash):
source .venv/Scripts/activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt

# Add a new dependency
uv pip install <package>
uv pip freeze > requirements.txt
```

## Structure

```
awsome-python-projects/
├── .venv/              # Shared virtual environment
├── requirements.txt    # Shared dependencies
├── project-1/          # Each mini project lives in its own folder
├── project-2/
└── ...
```
