# docs code map tooling

This folder keeps Mintlify documentation in sync with CAMEL source code.

## Scripts

| Script | Purpose |
|--------|---------|
| `doc_code_map.py` | Validate `doc_code_map` frontmatter and find impacted docs after code changes. |
| `auto_sync_docs_with_chatagent.py` | Regenerate doc bodies for impacted files using a CAMEL ChatAgent. Located at `.camel/skills/docs-incremental-update/scripts/`. |

Documented doc roots:

- `docs/mintlify/key_modules/*.mdx`
- `docs/mintlify/mcp/*.mdx`

## How It Works

Each `.mdx` doc declares a `doc_code_map` block in its YAML frontmatter listing
glob patterns for the source files it documents. When code changes land,
`doc_code_map.py impacted` matches the changed files against those patterns to
produce a list of impacted docs. `auto_sync_docs_with_chatagent.py` then feeds
each doc + its mapped source code to a CAMEL ChatAgent, which rewrites the body
while preserving the frontmatter and Mintlify components.

The GitHub Actions workflow `.github/workflows/docs_release_auto_sync_pr.yml`
orchestrates this end-to-end on every release and opens a PR automatically.

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

Print impacted docs from git refs:

```bash
python docs/scripts/docs_sync/doc_code_map.py impacted --base-ref <base> --head-ref <head>
```

Auto-sync impacted docs with CAMEL ChatAgent:

```bash
python .camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py \
  --docs-file impacted_docs.txt \
  --model-platform openai \
  --model-type gpt-4o-mini
```

## Environment Variables

The auto-sync script requires an API key for the chosen model platform:

| Platform | Variable |
|----------|----------|
| OpenAI (default) | `OPENAI_API_KEY` |
| Anthropic | `ANTHROPIC_API_KEY` |
| Other platforms | See CAMEL `ModelPlatformType` docs |

Example:

```bash
export OPENAI_API_KEY=...
```

## Multi-Platform Support

Both `--model-platform` and `--model-type` can be overridden to use any backend
supported by CAMEL's `ModelFactory`. For example:

```bash
python .camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py \
  --docs-file impacted_docs.txt \
  --model-platform anthropic \
  --model-type claude-sonnet-4-20250514
```

## Claude Code Skill

A companion Claude Code skill is available at
`.camel/skills/docs-incremental-update/`. It guides interactive, manual doc
updates following the same doc-code-map approach used by the automated workflow.
