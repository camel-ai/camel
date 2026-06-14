# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## What this repo is

CAMEL (`camel-ai` on PyPI) is an open-source multi-agent framework. The core
library lives in `camel/`, with supporting examples, tests, docs, and apps
around it.

Top-level layout:
- `camel/` — the library source (the only thing published to PyPI)
- `test/` — pytest test suite, mirrors `camel/` package structure
- `examples/` — runnable scripts demonstrating features (mirrors `camel/` topics)
- `docs/` — Mintlify documentation source
- `apps/` — standalone demo applications (e.g. Gradio apps)
- `services/`, `misc/`, `profiling/`, `data/` — auxiliary tooling/data
- `licenses/` — license header template + `update_license.py` script

### Key subpackages under `camel/`

- `agents/` — `ChatAgent` and other agent types (critic, task, search, etc.)
- `societies/` — multi-agent orchestration: `role_playing.py`, `workforce/`
- `models/` — model backends, one file per provider, all wired through
  `model_factory.py` / `model_manager.py`
- `toolkits/` — tool implementations agents can call (one file/dir per toolkit)
- `messages/`, `memories/`, `responses/`, `prompts/` — agent I/O and memory
- `types/` — shared enums and type definitions (`ModelType`, `ModelPlatformType`, etc.)
- `configs/` — per-model configuration classes
- `interpreters/`, `runtimes/`, `environments/` — code execution / RL environments
- `embeddings/`, `retrievers/`, `storages/` — RAG building blocks
- `datasets/`, `datagen/`, `datahubs/`, `data_collectors/`, `loaders/`,
  `extractors/`, `verifiers/`, `benchmarks/` — data generation/evaluation pipelines
- `utils/`, `logger.py`, `human.py`, `generators.py` — shared helpers

## Setup

```sh
pip install uv
uv venv .venv --python=3.10   # supports 3.10, 3.11, 3.12
source .venv/bin/activate
uv pip install -e ".[all, dev, docs]"
pre-commit install
```

API keys for tests/examples go in a `.env` file at the repo root (see
`.env.example`); `test/conftest.py` loads it automatically via `dotenv`.

## Common commands

All commands assume the venv is active (or prefix with `uv run`).

```sh
# Format + lint + autofix
make format            # yapf/isort + ruff --fix
make ruff              # ruff check only
make ruff-fix          # ruff check --fix

# Type checking
make mypy              # mypy camel --install-types --non-interactive --namespace-packages

# Run the full pre-commit suite (ruff, mypy, license header check,
# codespell, gitleaks, whitespace/EOF fixers)
make pre-commit

# Tests
pytest .                       # full suite (needs API keys for some tests)
pytest --fast-test-mode .      # local-only tests, no LLM calls
pytest --llm-test-only .       # tests requiring model_backend, excluding very slow
pytest --very-slow-test-only . # only very_slow-marked tests
pytest path/to/test_file.py -k test_name   # run a single test

# License headers (auto-add/update Apache-2.0 header on all .py files)
python licenses/update_license.py . licenses/license_template.txt

# Dependency lockfile (run after editing pyproject.toml dependencies)
uv lock
```

CI runs ruff, mypy, and pytest, so run `make ruff`, `make mypy`, and the
relevant pytest subset before considering a change done.

## Code conventions

- **License header**: every `.py` file (except under `docs/` and
  `examples/usecases/`) starts with the Apache-2.0 header from
  `licenses/license_template.txt`. Run `python licenses/update_license.py .
  licenses/license_template.txt` if you add new files.
- **Line length**: 79 characters (ruff `line-length = 79`).
- **Imports**: isort-style via ruff, first-party package is `camel`.
- **Docstrings**: Google-style, raw strings (`r"""..."""`), `Args:`/`Returns:`
  sections, 79-char wrapping. Public classes/methods should be documented.
- **No abbreviations**: use descriptive names (`message_window_size`, not
  `msg_win_sz`) — code is read by both humans and agents.
- **Logging, not printing**: use `from camel.logger import get_logger;
  logger = get_logger(__name__)` instead of `print()`.
- **Toolkit function naming**: every public method on a `BaseToolkit`
  subclass must use a toolkit-specific prefix, e.g. `github_create_issue()`,
  not `create_issue()`. Don't shadow Python builtins. When renaming, keep a
  deprecated alias for at least 2 minor versions.
- Avoid unnecessary abstractions, speculative features, or backwards-compat
  shims — match the existing minimal/explicit style of the codebase.

## Adding things (typical patterns)

- **New model backend**: add `camel/models/<name>_model.py` implementing
  `BaseModelBackend`, register it in `camel/models/model_factory.py` and
  `camel/models/__init__.py`, add a corresponding entry/config under
  `camel/types/enums.py` and `camel/configs/`.
- **New toolkit**: add `camel/toolkits/<name>_toolkit.py` subclassing
  `BaseToolkit`, export tools via `get_tools()` returning `FunctionTool`s,
  follow the toolkit prefix naming rule, export from
  `camel/toolkits/__init__.py`.
- **New feature/bugfix**: add/update unit tests in `test/` (mirroring the
  `camel/` path), and add a demo script under `examples/` for new features.

## Testing notes

- Tests mirror `camel/`'s structure under `test/`.
- Many tests call real model APIs and are marked `model_backend` (requires
  API keys, e.g. `OPENAI_API_KEY`) — use `--fast-test-mode` to skip these
  during local iteration.
- `very_slow` marks tests only run in full test mode.
- `heavy_dependency` marks tests needing large optional extras.
- `test/test_all_exports.py` checks `from camel import *` and `camel.__all__`
  stay consistent — update it if you change top-level exports in
  `camel/__init__.py`.

## Environment variables for debugging

```sh
export CAMEL_MODEL_LOG_ENABLED=true              # log model requests/responses
export CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED=true # include model_config_dict in logs
export CAMEL_LOG_DIR=camel_logs                  # output dir for logs (UTF-8 JSON)
```

## Contribution policy (important for AI-generated changes)

This project has an explicit **AI-Generated Code Policy** (see
`CONTRIBUTING.md`):
- PRs must reference a prior discussed/accepted issue or Discord thread.
- Code must be human-reviewed and tested — no "theoretically correct but
  untested" submissions; include proof of testing.
- Don't produce large, low-signal, or "vibe-coded" diffs. Keep changes
  focused and minimal, matching the surrounding code style exactly.

## Versioning

CAMEL follows SemVer but is pre-1.0 (`0.x`), so even patch releases may
contain breaking changes. Current version is tracked in
`camel/__init__.py` (`__version__`) and `pyproject.toml`.
