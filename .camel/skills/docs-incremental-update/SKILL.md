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

- Only use this skill when the driver is **Python source changes** referenced
  by a target document's `doc_code_map`.
- Do **not** use it for docs-only edits, workflow/YAML changes, or broad
  wording cleanups without Python changes.
- Prefer **no document change** when Python edits are internal and do not
  affect public API, behavior, configuration, examples, or reader understanding.

## Edit Rule

Use terminal tools to inspect the target doc, inspect any relevant code, and
edit the target doc directly. Keep changes scoped to that doc and preserve its
frontmatter.
CI treats the run as successful based on the resulting target doc file state,
not on any special status token in the chat response.


## Quick Reference

| Item | Path |
|------|------|
| Doc roots | `docs/mintlify/` |
| Mapping utility | `docs/mintlify/scripts/docs_sync/doc_code_map.py` |
| Auto-sync script | `.camel/skills/docs-incremental-update/scripts/auto_sync_docs_with_chatagent.py` |
| Workflow | `.github/workflows/docs_release_auto_sync_pr.yml` |

## Workflow

### Step 1 — Identify Impacted Docs

Determine which `.mdx` files are affected by the code change.

```bash
# From repo root, pass only changed Python files
python docs/mintlify/scripts/docs_sync/doc_code_map.py impacted \
  --changed-file <file1> --changed-file <file2>

# Or using git refs
python docs/mintlify/scripts/docs_sync/doc_code_map.py impacted \
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

### Step 2 — Read Current Doc and Relevant Code

For each impacted doc:

1. Open the target `.mdx` file and inspect its `doc_code_map` frontmatter.
2. Use the provided changed Python file list as initial context.
3. Read any source files needed to judge whether the doc is still accurate.
4. Compare the target doc against the current code and decide whether a
   reader-facing update is actually needed.

### Step 3 — Update the Document Body

Rewrite only the parts of the body that are outdated relative to the code.

Rules:
- **Edit the target doc directly through terminal tools** for this run.
- **Let file changes speak for themselves** — if no update is needed, leave the
  target doc untouched instead of relying on a sentinel reply.
- **Use changed Python files as context, not a hard boundary** — inspect other
  relevant code when needed to make a correct documentation decision.
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
- After finishing, either leave the file unchanged or update it in place.
- Do not return the full rewritten document body in chat; a short status note
  is enough.

### Step 4 — Verify

```bash
# Ensure all patterns still resolve
python docs/mintlify/scripts/docs_sync/doc_code_map.py verify
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
2. Writes `changed_python_files.txt` from the release diff for all changed
   `*.py` files that may match `doc_code_map`.
3. Computes `impacted_docs.txt` from that changed Python file list.
4. Runs `auto_sync_docs_with_chatagent.py` with both files so the agent knows
   which target doc it may inspect and update directly through terminal tools,
   while using `changed_python_files.txt` as context. The script accepts
   success based on whether the target doc actually changed and rejects edits
   outside the target doc.
5. Opens a PR with the changes.
