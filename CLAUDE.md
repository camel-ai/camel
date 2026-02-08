# CLAUDE.md

This file provides instructions for Claude Code when working on this
repository. See https://code.claude.com/docs/en/overview for details.

## Project Overview

CAMEL (Communicative Agents for "Mind" Exploration of Large Language Model
Society) is an open-source Python framework for building and studying
multi-agent systems. It provides tools for agent communication, task
automation, and world simulation.

## Development Environment

- **Python**: 3.10, 3.11, or 3.12
- **Package Manager**: uv (preferred over pip)
- **Build System**: Hatchling
- **License**: Apache 2.0

### Setup

```bash
pip install uv
uv venv .venv --python=3.10
source .venv/bin/activate
uv pip install -e ".[all, dev, docs]"
pre-commit install
```

### Dependency Changes

Always run `uv lock` after modifying `pyproject.toml`.

## Code Style

- **Formatter/Linter**: Ruff
- **Line Length**: 79 characters
- **Style Guide**: Google Python Style Guide
- **Type Checking**: mypy
- **Docstrings**: Raw docstrings (`r"""..."""`), Google style
- Use `logger` instead of `print()` for output
- Avoid abbreviations in naming (e.g., use `message_window_size` not
  `msg_win_sz`)
- Toolkit functions must use prefixes:
  `<toolkit_prefix>_<action>_<resource>()` (e.g., `github_create_issue()`)

## Testing

- **Framework**: pytest
- Run all tests: `pytest .`
- Run fast tests only: `pytest --fast-test-mode .`
- Tests are in the `test/` directory
- Add unit tests for bug fixes and new features
- Key markers: `asyncio`, `very_slow`, `model_backend`,
  `heavy_dependency`

## Linting and Formatting

- Auto-fix lint errors: `make ruff-fix`
- Run all pre-commit checks: `pre-commit run --all-files`

## PR Conventions

- Bug fixes require unit tests
- Improvements require updated examples and docs
- New features require unit tests and a demo script in `examples/`
- PR labels: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## Project Structure

- `camel/` — Main package source code
- `test/` — Unit and integration tests
- `examples/` — Example scripts and demos
- `docs/` — Documentation (Mintlify)
- `apps/` — Gradio demo applications
