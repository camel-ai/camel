---
name: claude-code
description: Uses Claude Code (Anthropic's agentic coding tool) to work on the CAMEL multi-agent framework. Claude Code can autonomously explore the codebase, edit files, run commands, and create pull requests as an alternative to GitHub Copilot.
tools: ["read", "edit", "search", "terminal"]
---

# Claude Code Agent for CAMEL

You help developers use **Claude Code** as an AI coding agent for the CAMEL
repository, serving as an alternative to GitHub Copilot.

## What is Claude Code

Claude Code is Anthropic's agentic coding tool that runs in the terminal. It
can understand codebases, edit files, run commands, search code, and manage
git workflows — all through natural language. Documentation:
https://code.claude.com/docs/en/overview

## Installation

```bash
# Install Claude Code (requires Node.js >= 18)
npm install -g @anthropic-ai/claude-code

# Navigate to the CAMEL repository
cd camel

# Launch Claude Code
claude
```

## Configuration

Claude Code reads the `CLAUDE.md` file in the repository root for
project-specific instructions. This file is already configured for the
CAMEL project with development environment setup, code style guidelines,
testing commands, and project structure information.

### Key Configuration Files

- `CLAUDE.md` — Project instructions for Claude Code (repo root)
- `~/.claude/settings.json` — User-level settings
- `.claude/settings.json` — Project-level settings

### Setting Permissions

```bash
# Allow common development tools
claude config add allowedTools "bash(pytest:*)"
claude config add allowedTools "bash(make:*)"
claude config add allowedTools "bash(pre-commit:*)"
```

## Using Claude Code for CAMEL Development

### Interactive Mode

```bash
# Start an interactive session in the CAMEL repo
cd camel
claude

# Example prompts:
# > Fix the failing test in test/test_agent.py
# > Add a new toolkit function following the naming convention
# > Run the linter and fix any issues
```

### Non-Interactive (Headless) Mode

```bash
# Run a single task
claude -p "Run pytest --fast-test-mode and fix any failures"

# Process an issue
claude -p "$(gh issue view 123 --json body -q .body)"
```

### CI/GitHub Actions Integration

Claude Code can run in CI as an automated agent. Add to your workflow:

```yaml
- name: Run Claude Code
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
  run: |
    npm install -g @anthropic-ai/claude-code
    claude -p "Review the changes and run tests" --allowedTools \
      "bash(pytest:*)" "bash(make:*)" "read" "edit"
```

## CAMEL-Specific Workflow

When working on the CAMEL project, Claude Code should:

1. **Setup**: Run `uv pip install -e ".[all, dev, docs]"` if needed
2. **Code style**: Follow Ruff formatting (79 char lines), Google
   docstrings (`r"""..."""`), use `logger` not `print()`
3. **Testing**: Run `pytest --fast-test-mode .` for quick validation
4. **Linting**: Run `make ruff-fix` then `pre-commit run --all-files`
5. **Dependencies**: Run `uv lock` after changing `pyproject.toml`
