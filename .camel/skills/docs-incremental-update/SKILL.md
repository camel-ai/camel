---
name: docs-incremental-update
description: >
  Incrementally update Mintlify documentation (.mdx) from Python source
  changes only. Use when: (1) Python files referenced in doc_code_map
  frontmatter have changed, (2) a PR touches Python modules documented in
  docs/mintlify/key_modules/ or docs/mintlify/mcp/, (3) the user asks to
  sync docs after Python code changes. Prefer minimal diffs and leave correct
  content untouched.
---

# Docs Incremental Update

Update Mintlify .mdx documentation so it stays in sync with CAMEL source code.

## Scope

- Only use this skill when the driver is **Python source changes** under
  `camel/**`.
- Do **not** use it for docs-only edits, workflow/YAML changes, or broad
  wording cleanups without Python changes.
- Prefer **no document change** when Python edits are internal and do not
  affect public API, behavior, configuration, examples, or reader understanding.

## Edit Rule

Do not use browser/search/other toolkits unless the user explicitly asks.
If you use terminal tools to edit the impacted document directly, keep the
changes scoped to that doc and preserve its frontmatter.

## Agent Setup

When wiring an agent for this skill, enable only:

- `camel.toolkits.SkillToolkit`
- `camel.toolkits.TerminalToolkit`

Keep terminal usage focused on the impacted docs and their mapped Python files.

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
# From repo root, pass only changed Python files
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
  - "camel/runtimes/llm_guard_runtime.py"
---
```

### Step 2 — Read Mapped Code and Current Doc

For each impacted doc:

1. Load the `docs-incremental-update` skill through `SkillToolkit`.
2. Use terminal as needed to confirm the Python diff, inspect specific mapped
   files, or update the impacted doc directly.
3. Open the `.mdx` file and separate the frontmatter from the body.
4. Resolve every glob pattern in `doc_code_map` to actual source files.
5. Read the source files — these represent the ground truth.

### Step 3 — Update the Document Body

Rewrite only the parts of the body that are outdated relative to the code.

Rules:
- **If you edit through tools, keep changes scoped to the impacted docs** for
  this run.
- **Focus on changed Python files first** — inspect the diff between the base
  and head refs when available.
- **Base changes only on mapped Python files** — they are the source of truth.
- **Ignore non-Python changes** — docs, workflow, YAML, test-only, and release
  metadata changes should not trigger doc edits by themselves.
- **Prefer the smallest possible diff** — keep all already-correct content.
- **Preserve frontmatter** — never modify the `---` block.
- **Preserve style** — keep existing section structure and tone.
- **Preserve Mintlify components** — keep Card, Accordion, Tab, CodeGroup, etc.
- **Update code snippets** — fix imports, class names, method signatures, parameters.
- **Update prose** — fix descriptions that no longer match the code.
- **Remove references** to deleted classes/methods/parameters.
- **Add references** to newly introduced public API when relevant.
- **Skip the document entirely** if the Python change is internal and does not
  require reader-facing doc updates.

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

~~~~mdx
<CodeGroup>
```python title="example.py"
print("hello")
```
```bash title="shell"
echo hello
```
</CodeGroup>
~~~~

```mdx
<Note>Important information the reader should know.</Note>
<Warning>Critical warning about potential issues.</Warning>
<Tip>Helpful suggestion or best practice.</Tip>
```

## Automated Workflow

The GitHub Actions workflow `docs_release_auto_sync_pr.yml` runs
automatically on each release:

1. Verifies `doc_code_map` patterns (`doc_code_map.py verify`).
2. Writes `changed_python_files.txt` from the release diff, limited to
   `camel/**.py` and `services/**.py`.
3. Computes `impacted_docs.txt` from that changed Python file list.
4. Runs `auto_sync_docs_with_chatagent.py` with both files so the agent knows:
   which Python files changed and which docs it may update.
5. Opens a PR with the changes.
