# docs code map tooling

This folder keeps Mintlify documentation in sync with CAMEL source code.

## Scripts

| Script | Purpose |
|--------|---------|
| `doc_code_map.py` | Validate `doc_code_map` frontmatter and find impacted docs after code changes. |
| `auto_sync_docs_with_chatagent.py` | Ask a CAMEL ChatAgent to inspect impacted docs with terminal tools and update them directly. Located at `.camel/skills/docs-incremental-update/scripts/`. |

Documented doc roots:

- `docs/mintlify/key_modules/*.mdx`
- `docs/mintlify/mcp/*.mdx`

## How It Works

Each `.mdx` doc declares a `doc_code_map` block in its YAML frontmatter listing
glob patterns for the source files it documents. When code changes land,
`doc_code_map.py impacted` matches the changed files against those patterns to
produce a list of impacted docs. `auto_sync_docs_with_chatagent.py` then passes
each target doc path plus `changed_python_files.txt` to a CAMEL ChatAgent. The
agent uses terminal tools to inspect the target doc, resolve `doc_code_map`,
read mapped Python files, and update the target doc directly.

The GitHub Actions workflow `.github/workflows/docs_release_auto_sync_pr.yml`
orchestrates this end-to-end on every release tag diff and opens a PR
automatically when mapped docs actually changed.

## Commands

Verify all mappings and ensure every pattern resolves to at least one file:

```bash
python docs/scripts/docs_sync/doc_code_map.py verify
```

Print impacted docs from an explicit changed-file list:

```bash
python docs/scripts/docs_sync/doc_code_map.py impacted \
  --changed-file camel/toolkits/mcp_toolkit.py \
  --changed-file camel/societies/workforce/workforce.py
```

Print impacted docs from a file containing changed paths:

```bash
python docs/scripts/docs_sync/doc_code_map.py impacted \
  --changed-files-file changed_python_files.txt
```

Print impacted docs from git refs:

```bash
python docs/scripts/docs_sync/doc_code_map.py impacted --base-ref <base> --head-ref <head>
```

Auto-sync impacted docs with CAMEL ChatAgent:

```bash
python .camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py \
  --docs-file impacted_docs.txt \
  --changed-files-file changed_python_files.txt \
  --model-platform openai \
  --model-type gpt-5.4
```

## Environment Variables

The auto-sync script requires an API key for the chosen model platform.
The release workflow is fixed to OpenAI `gpt-5.4` and expects
`OPENAI_API_KEY`.

| Platform | Variable |
|----------|----------|
| OpenAI (default) | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Other platforms | See CAMEL `ModelPlatformType` docs |

Example:

```bash
export OPENAI_API_KEY=...
```

## Manual Multi-Platform Support

When you run the script directly, both `--model-platform` and `--model-type`
can be overridden to use any backend supported by CAMEL's `ModelFactory`.
For example:

```bash
python .camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py \
  --docs-file impacted_docs.txt \
  --model-platform anthropic \
  --model-type claude-sonnet-4-20250514
```

## Repo Skill

The repo skill at `.camel/skills/docs-incremental-update/` guides the agent to
inspect only the changed Python files plus the impacted doc, then edit that doc
directly through terminal tools with the smallest necessary diff.
