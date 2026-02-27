# docs code map tooling

This folder contains tooling for `doc_code_map` in Mintlify docs:

- `docs/mintlify/key_modules/*.mdx`
- `docs/mintlify/mcp/*.mdx`

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
python docs/scripts/docs_sync/auto_sync_docs_with_chatagent.py \
  --docs-file impacted_docs.txt \
  --model-platform openai \
  --model-type gpt-4o-mini
```

Required env vars for the default OpenAI setup:

```bash
export OPENAI_API_KEY=...
```
