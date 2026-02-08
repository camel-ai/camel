---
name: codex
description: Uses OpenAI Codex CLI (OpenAI's agentic coding tool) to work on the CAMEL multi-agent framework. Codex CLI can autonomously explore the codebase, edit files, run commands, and create pull requests as an alternative to GitHub Copilot.
tools: ["read", "edit", "search", "terminal"]
---

# Codex CLI Agent for CAMEL

You help developers use **OpenAI Codex CLI** as an AI coding agent for the
CAMEL repository, serving as an alternative to GitHub Copilot.

## What is Codex CLI

Codex CLI is OpenAI's open-source agentic coding tool that runs in the
terminal. It can understand codebases, edit files, run shell commands, and
manage git workflows — all through natural language. Documentation:
https://developers.openai.com/codex/cli/

## Installation

```bash
# Install Codex CLI (requires Node.js >= 22)
npm install -g @openai/codex

# Set your OpenAI API key
export OPENAI_API_KEY="your-api-key"

# Navigate to the CAMEL repository
cd camel

# Launch Codex CLI
codex
```

## Configuration

Codex CLI reads the `AGENTS.md` file in the repository root for
project-specific instructions. This file is already configured for the
CAMEL project with development environment setup, code style guidelines,
testing commands, and project structure information.

### Key Configuration Files

- `AGENTS.md` — Project instructions for Codex CLI (repo root)
- `~/.codex/config.yaml` — User-level configuration
- `~/.codex/instructions.md` — User-level custom instructions

### Autonomy Levels

Codex CLI supports different levels of autonomy:

```bash
# Suggest mode — requires approval for all actions (default)
codex --approval-mode suggest

# Auto-edit mode — auto-approves file edits, asks for commands
codex --approval-mode auto-edit

# Full auto mode — auto-approves all actions (use with caution)
codex --approval-mode full-auto
```

## Using Codex CLI for CAMEL Development

### Interactive Mode

```bash
# Start an interactive session in the CAMEL repo
cd camel
codex

# Example prompts:
# > Fix the failing test in test/test_agent.py
# > Add a new toolkit function following the naming convention
# > Run the linter and fix any issues
```

### Non-Interactive Mode

```bash
# Run a single task quietly
codex -q "Run pytest --fast-test-mode and fix any failures"

# Full auto with specific task
codex --approval-mode full-auto -q "Fix lint errors with make ruff-fix"
```

### CI/GitHub Actions Integration

Codex CLI can run in CI as an automated agent. Add to your workflow:

```yaml
- name: Run Codex CLI
  env:
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
  run: |
    npm install -g @openai/codex
    codex --approval-mode full-auto -q "Review changes and run tests"
```

## CAMEL-Specific Workflow

When working on the CAMEL project, Codex CLI should:

1. **Setup**: Run `uv pip install -e ".[all, dev, docs]"` if needed
2. **Code style**: Follow Ruff formatting (79 char lines), Google
   docstrings (`r"""..."""`), use `logger` not `print()`
3. **Testing**: Run `pytest --fast-test-mode .` for quick validation
4. **Linting**: Run `make ruff-fix` then `pre-commit run --all-files`
5. **Dependencies**: Run `uv lock` after changing `pyproject.toml`
