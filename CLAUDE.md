# CLAUDE.md

Guidance for AI assistants (Claude Code and similar) working in this repository.

## Project

**CAMEL** (`camel-ai` on PyPI, version 0.2.91a4) is a multi-agent framework for
building communicative, tool-using LLM agents and societies. The Python package
lives at `camel/`. Supported Python: `>=3.10,<3.15`.

Homepage: <https://www.camel-ai.org/> · Docs: <https://docs.camel-ai.org>

> **Read `CONTRIBUTING.md` before doing any non-trivial change.** It encodes
> hard project rules — especially the AI-Generated Code Policy below — that
> the maintainers enforce.

### AI-generated code policy (important)

CAMEL has an explicit policy on LLM-generated PRs (`CONTRIBUTING.md` §
"AI-Generated Code Policy"). When using an AI assistant in this repo:

1. **Do not open drive-by PRs.** Every PR must reference a prior accepted
   issue / Discord thread.
2. **No unreviewed LLM output.** Submissions that are primarily LLM-generated
   without meaningful human review will be closed.
3. **Human-verified testing required.** "Theoretically correct but untested"
   is not acceptable; include real test output / screenshots / logs.
4. AI-assisted drafts for issues, discussions, and prototypes are fine if
   edited by a human.

When asked to implement something, produce the code, run the relevant
tests/lints locally, and surface a clear report of what was verified — do
not claim "should work."

## Repository layout

```
camel/                  Main package
├── agents/             ChatAgent, CriticAgent, TaskAgent, MCPAgent, etc.
├── societies/          Multi-agent setups: role_playing, workforce/
├── models/             Model backends (OpenAI, Anthropic, Gemini, Bedrock,
│                       Ollama, vLLM, LiteLLM, … one file per provider)
├── configs/            Per-provider config dataclasses paired with models/
├── toolkits/           Tool implementations exposed to agents (browser,
│                       GitHub, Slack, search, code-exec, MCP, …)
├── messages/           BaseMessage, FunctionCallingMessage, conversion/
├── memories/           AgentMemory, ChatHistoryMemory, blocks, context_creators
├── prompts/            Prompt templates (TextPrompt and task-specific prompts)
├── responses/          ChatAgentResponse and related response types
├── types/              Enums (ModelType, ModelPlatformType, RoleType, …)
├── loaders/            Document/web loaders (firecrawl, unstructured, …)
├── retrievers/         Vector / hybrid retrievers
├── embeddings/         Embedding backends
├── storages/           key_value, vectordb, graph, object storage backends
├── interpreters/       Code interpreters (internal Python, docker, e2b, jupyter)
├── runtimes/           Sandboxed/remote execution runtimes
├── benchmarks/         Benchmark harnesses
├── datagen/, datasets/, datahubs/, data_collectors/, generators.py
│                       Data generation / dataset utilities
├── environments/, verifiers/, extractors/, terminators/
│                       RL-style environment and reward components
├── personas/, tasks/, schemas/, parsers/, services/, bots/, caches/
├── logger.py           Project logger (use this, not `print`)
└── __init__.py         Exposes __version__ and logging helpers

apps/                   Demo apps (Gradio etc.)
examples/               Runnable example scripts, grouped by module
test/                   Pytest tests, mirrors `camel/` layout
docs/                   Mintlify docs + cookbooks (.mdx)
services/               Auxiliary services (agent_mcp, …)
licenses/               License header template + updater script
profiling/              Profiling scripts
data/                   Static assets used by examples/tests
.github/workflows/      CI: pre_commit, pytest_package, pytest_apps,
                        test_minimal_dependency, build_package, …
```

A few hot files worth knowing:

- `camel/agents/chat_agent.py` — the central `ChatAgent` class; many features
  funnel through it.
- `camel/models/model_factory.py` — entry point for constructing model
  backends; pair with `camel/configs/`.
- `camel/societies/workforce/workforce.py` — multi-agent workforce
  orchestration.
- `camel/toolkits/base.py` and `camel/toolkits/function_tool.py` — base
  classes for tool/toolkit implementations.

## Environment & install

The project uses **`uv`**. From `CONTRIBUTING.md` Quick Start:

```bash
pip install uv
uv venv .venv --python=3.10
source .venv/bin/activate
uv pip install -e ".[all, dev, docs]"
pre-commit install
```

Lighter installs are available via optional-dependency groups in
`pyproject.toml`: `rag`, `web_tools`, `document_tools`, `media_tools`,
`communication_tools`, `data_tools`, `research_tools`, `dev_tools`,
`model_platforms`, `huggingface`, `storage`, `owl`, `eigent`,
`earth-science`. Use the narrowest extras that cover the task.

When dependencies change in `pyproject.toml`, run `uv lock` to refresh
`uv.lock`.

Common API keys are loaded from a project-root `.env` (see `.env.example`).
`test/conftest.py` calls `load_dotenv()` so `pytest` picks them up
automatically.

## Tests

Five pytest modes, defined in `test/conftest.py`:

| Flag                       | What runs                                              |
| -------------------------- | ------------------------------------------------------ |
| *(default)*                | All except `very_slow`                                 |
| `--full-test-mode`         | Everything, including `very_slow`                      |
| `--default-test-mode`      | Everything except `very_slow` (explicit form)          |
| `--fast-test-mode`         | Skip `optional` and `model_backend` (no LLM calls)     |
| `--llm-test-only`          | Only `model_backend` tests                             |
| `--very-slow-test-only`    | Only `very_slow` tests                                 |

Registered markers (`pyproject.toml`): `asyncio`, `very_slow`,
`model_backend`, `heavy_dependency`. `--strict-markers` is on, so new
markers must be registered first.

Common commands:

```bash
pytest .                                  # full default run
pytest --fast-test-mode .                 # no-LLM, fast feedback
pytest test/agents/test_chat_agent.py     # one file
pytest --cov --cov-report=html            # coverage report → htmlcov/
```

CI (`.github/workflows/pytest_package.yml`) excludes
`heavy_dependency`-marked tests and a fixed `--ignore` list of slow /
environment-sensitive files; mirror those ignores when reproducing CI
locally.

## Lint, format, types

Tooling is configured in `pyproject.toml` and `.pre-commit-config.yaml`:

- **Ruff** (`v0.7.4` via pre-commit): linter + formatter.
  - `line-length = 79`, `target-version = "py310"`, `quote-style = "preserve"`.
  - Enabled rule sets: `I`, `B`, `C4`, `PGH`, `RUF`, `E`. See `tool.ruff.lint.ignore`
    for the intentionally-disabled rules — don't re-enable them in one-off changes.
  - First-party isort module: `camel`.
- **mypy** (`namespace-packages`, runs against `camel`, `test`, `apps`).
  Many third-party libs are listed under `tool.mypy.overrides` with
  `ignore_missing_imports = true`; add to that list rather than scattering
  `# type: ignore` when a new optional dep lacks stubs.
- **codespell**, **gitleaks**, **end-of-file-fixer**, **trailing-whitespace**
  run via pre-commit.
- **License header check** runs `licenses/update_license.py` on every Python
  file (see "License headers" below).

Run them locally:

```bash
ruff check . --fix              # or `make ruff-fix`
ruff format .
uv run mypy --namespace-packages -p camel -p test -p apps
pre-commit run --all-files      # full gauntlet
```

`Makefile` provides `make format`, `make ruff`, `make mypy`,
`make pre-commit` and similar shortcuts.

## Conventions

### License headers (enforced by pre-commit)

Every `*.py` file must start with the standard Apache 2.0 banner from
`licenses/license_template.txt`. New files: copy it verbatim. If
pre-commit's `check-license` rewrites your file, accept the change. The
current header reads `Copyright 2023-2026`.

### Docstrings (from `CONTRIBUTING.md` §"Writing Docstrings")

- Use raw triple-quoted strings: `r"""..."""`.
- Google style (`tool.ruff.lint.pydocstyle.convention = "google"`).
- Keep every line ≤ 79 chars; 4-space continuation indent.
- Document parameters in an `Args:` block with type and a
  `(default: :obj:<value>)` suffix when applicable.

### Naming

- **Avoid abbreviations.** `message_window_size`, not `msg_win_sz`.
- **Toolkit functions must be prefixed by the toolkit name.** Pattern:
  `<toolkit_prefix>_<action>_<resource>` — e.g. `github_create_issue()`,
  `excel_create_workbook()`. Never shadow Python builtins (use
  `math_round`, not `round`). When renaming a public tool method, keep a
  deprecated alias with a warning for at least two minor versions.

### Logging

Use `camel.logger` — never `print`. Example:

```python
from camel.logger import get_logger
logger = get_logger(__name__)
logger.info("...")
```

Optional model I/O logging is controlled by env vars (see
`CONTRIBUTING.md`): `CAMEL_MODEL_LOG_ENABLED`,
`CAMEL_MODEL_LOG_MODEL_CONFIG_ENABLED`, `CAMEL_LOG_DIR`.

### Module exports

Public surface goes through `__init__.py` re-exports (see
`camel/agents/__init__.py` for the pattern). When adding a new agent /
model / toolkit, append it to the package `__init__.py` and `__all__`.
`test/test_all_exports.py` guards top-level exports — run it after
changing public APIs.

### Optional dependencies

Many subsystems (browser, RAG, audio, …) gate on optional extras. When
adding a feature that imports a heavy library, put the import inside the
function/class that needs it, mark the test with `heavy_dependency` (or
`@pytest.mark.heavy_dependency`), and add the dependency to the
appropriate `pyproject.toml` extra (not the base `dependencies`).

## Adding things — quick checklist

**New model backend** (`camel/models/<provider>_model.py`):
1. Subclass `BaseModelBackend`.
2. Add matching `camel/configs/<provider>_config.py`.
3. Register in `camel/models/__init__.py` and `camel/models/model_factory.py`.
4. Add enums in `camel/types/enums.py` (`ModelType`, `ModelPlatformType`).
5. Tests in `test/models/`; mark LLM-calling tests with `model_backend`.

**New toolkit** (`camel/toolkits/<name>_toolkit.py`):
1. Subclass `BaseToolkit`.
2. Prefix every public method with the toolkit name (see Naming above).
3. Export from `camel/toolkits/__init__.py`.
4. Tests in `test/toolkits/`; example in `examples/toolkits/`.
5. Use `@dependencies_required` / `@api_keys_required` decorators for
   optional deps and required env vars.

**New agent** (`camel/agents/<name>_agent.py`):
1. Subclass `BaseAgent` (or `ChatAgent` if it's a thin specialization).
2. Export from `camel/agents/__init__.py`.
3. Tests in `test/agents/`; example in `examples/agents/`.

## Git workflow

- **Default branch is `master`** (CI gates on push/PR to `master` and `qa`).
- **One issue per change.** PRs need a linked, pre-discussed issue.
- **PR title prefix** picks the label (`CONTRIBUTING.md` §"Labeling PRs"):
  `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `chore:`.
- Two reviewer approvals required before merge; merging is done by
  maintainers.
- Pre-commit must pass; CI must be green.
- Examples and docs should be updated alongside code changes when they're
  affected.

## Things to avoid

- Reformatting unrelated files / mass renames in a feature PR.
- Adding new top-level packages, scripts, or markdown files unless
  explicitly requested.
- Loosening lint configuration to silence a warning instead of fixing the
  code.
- Adding `print` statements, `# type: ignore` blanket suppressions,
  or `sys.path` hacks.
- Touching `uv.lock` by hand — regenerate with `uv lock`.
- Committing API keys or `.env`; gitleaks runs in pre-commit.
