---
name: docs-incremental-update
description: >
  Incrementally update Mintlify documentation (.mdx) to match source code
  changes. Use when: (1) source files referenced in doc_code_map frontmatter
  have changed, (2) a PR touches Python modules that are documented in
  docs/mintlify/key_modules/ or docs/mintlify/mcp/, (3) the user asks to
  sync, refresh, or update documentation after code changes.
---

# Docs Incremental Update

Update Mintlify .mdx documentation so it stays in sync with CAMEL source code.

## Quick Reference

| Item | Path |
|------|------|
| Doc roots | `docs/mintlify/key_modules/`, `docs/mintlify/mcp/` |
| Mapping utility | `docs/scripts/docs_sync/doc_code_map.py` |
| Auto-sync script | `.camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py` |
| Workflow | `.github/workflows/docs_release_auto_sync_pr.yml` |

## Workflow

### Step 1 — Identify Impacted Docs

Determine which `.mdx` files are affected by the code change.

```bash
# From repo root
python docs/scripts/docs_sync/doc_code_map.py impacted \
  --changed-file <file1> --changed-file <file2>

# Or using git refs
python docs/scripts/docs_sync/doc_code_map.py impacted \
  --base-ref <base> --head-ref <head>
```

Each `.mdx` file declares a `doc_code_map` block in its YAML frontmatter:

```yaml
---
title: MCP Toolkit
doc_code_map:
  - "camel/toolkits/mcp_toolkit.py"
  - "camel/runtime/llm_guard_runtime.py"
---
```

### Step 2 — Read Mapped Code and Current Doc

For each impacted doc:

1. Open the `.mdx` file and separate the frontmatter from the body.
2. Resolve every glob pattern in `doc_code_map` to actual source files.
3. Read the source files — these represent the ground truth.

### Step 3 — Update the Document Body

Rewrite only the parts of the body that are outdated relative to the code.

Rules:
- **Preserve frontmatter** — never modify the `---` block.
- **Preserve style** — keep existing section structure and tone.
- **Preserve Mintlify components** — keep Card, Accordion, Tab, CodeGroup, etc.
- **Update code snippets** — fix imports, class names, method signatures, parameters.
- **Update prose** — fix descriptions that no longer match the code.
- **Remove references** to deleted classes/methods/parameters.
- **Add references** to newly introduced public API when relevant.

### Step 4 — Verify

```bash
# Ensure all patterns still resolve
python docs/scripts/docs_sync/doc_code_map.py verify
```

Check that no frontmatter was accidentally removed or duplicated.

## Mintlify Component Cheatsheet

Use these components in `.mdx` files:

```mdx
<Card title="Title" icon="icon-name" href="/path">
  Description text.
</Card>
```

```mdx
<Accordion title="Click to expand">
  Hidden content revealed on click.
</Accordion>
```

```mdx
<Tabs>
  <Tab title="Python">
    Python content here.
  </Tab>
  <Tab title="TypeScript">
    TypeScript content here.
  </Tab>
</Tabs>
```

```mdx
<CodeGroup>
```python title="example.py"
print("hello")
```
```bash title="shell"
echo hello
```
</CodeGroup>
```

```mdx
<Note>Important information the reader should know.</Note>
<Warning>Critical warning about potential issues.</Warning>
<Tip>Helpful suggestion or best practice.</Tip>
```

## Automated Workflow

The GitHub Actions workflow `docs_release_auto_sync_pr.yml` runs
automatically on each release:

1. Verifies `doc_code_map` patterns (`doc_code_map.py verify`).
2. Computes impacted docs from the diff between the previous and current tag.
3. Runs `auto_sync_docs_with_chatagent.py` to regenerate doc bodies via
   CAMEL ChatAgent.
4. Opens a PR with the changes.

To trigger manually:

```bash
gh workflow run docs_release_auto_sync_pr.yml \
  -f base_ref=v0.2.0 \
  -f head_ref=v0.3.0 \
  -f model_platform=openai \
  -f model_type=gpt-4o-mini
```

Required secret: `OPENAI_API_KEY` (or the key matching the chosen platform).
