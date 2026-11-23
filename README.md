# EB1A open-source fix — CAMEL-AI (camel-ai/camel)

- **Repo:** https://github.com/camel-ai/camel (multi-agent LLM framework — AI platform / LLM-agent systems, Bhavana's field)
- **Stars:** 18,051 (verified via GitHub API, Nov 21, 2026); last push Nov 16, 2026
- **Issue:** https://github.com/camel-ai/camel/issues/4542 — "[BUG] ModelType.DEFAULT is gpt-4.1-mini-2025-04-14 (OpenAI shutdown Jan 14, 2027); create_chat_agent example also uses Sonnet 4.5 (retires Nov 30)"
- **License:** Apache License 2.0 (OSI open-source; no source-available caveat)
- **Status:** fix + tests written Nov 21, 2026. **No PR submitted** — for Bhavana to try locally first and raise herself if it checks out.
- **No-PR check:** issue has 0 comments and no linked PR (issue timeline empty); the repo's open PRs were scanned for `4542` / `modeltype` / `gpt-4.1` / `default model` with no match. The reporter said "Happy to open a PR for this if it's useful" but has not. Re-check for a new PR before raising one.

## What was wrong

1. `ModelType.DEFAULT` fell back to `gpt-4.1-mini-2025-04-14`. OpenAI shuts that snapshot down on **Jan 14, 2027** and names `gpt-6-luna` as the replacement (verified on OpenAI's deprecations page and its `gpt-6-luna` model page). Every `ChatAgent` created without a model uses the default, so the out-of-the-box path stops working on that date.
2. There was no `gpt-6-luna` member in `ModelType` at all. `DEFAULT` currently shares `GPT_4_1_MINI`'s value, so Python makes it an alias and it inherits `is_openai` and the 1M `token_limit`; a new value needs its own entries.
3. `gpt-6-luna` supports function calling on Chat Completions **only with `reasoning_effort` set to `none`** ("Use the Responses API for built-in tools and function calling. Chat Completions supports function calling only with `reasoning_effort` set to `none`." — OpenAI `gpt-6-luna` model page). `OpenAIModel` defaults to `api_mode="chat_completions"` and `ChatGPTConfig.reasoning_effort` defaults to `None` (not sent), so a tool-using agent on the new default model would fail at the API.
4. The `examples/agents/create_chat_agent.py` example used two more retiring models: `gpt-4o-mini` (same Jan 14, 2027 shutdown) and `claude-sonnet-4-5` (Anthropic retires Sonnet 4.5 on **Nov 30, 2026**, replacement `claude-sonnet-5-5` — verified on Anthropic's Sonnet page and model docs; Sonnet 5.5 has a 1M-token context window).

## What the fix does

- `camel/types/enums.py`
  - `DEFAULT` now falls back to `"gpt-6-luna"` (still overridable with the `DEFAULT_MODEL_TYPE` env var).
  - New member `GPT_6_LUNA = "gpt-6-luna"`, added to `is_openai`, with `token_limit` **1,050,000** (OpenAI model page: "1,050,000 context window").
  - New member `CLAUDE_SONNET_5_5 = "claude-sonnet-5-5"`, added to `is_anthropic`, with `token_limit` **1,000,000** (Anthropic: 1M-token context window).
  - `GPT_4_1_MINI`, `GPT_4O_MINI`, and `CLAUDE_SONNET_4_5` are left in place (still valid members; only the default and the example move).
  - Deliberately **not** added to `is_azure_openai`: that list already lags behind (it has no `GPT_5_1`/`GPT_5_2`/`GPT_5_4`/`GPT_5_5` either), so adding only `GPT_6_LUNA` there would be inconsistent. If a maintainer wants Azure coverage, that is a separate follow-up.
- `camel/models/openai_model.py` — `_sanitize_config` now defaults `reasoning_effort` to `"none"` when **all** of these hold: model is `GPT_6_LUNA`, `api_mode` is `"chat_completions"`, the request carries tools, and no `reasoning_effort` was configured. An explicitly configured value is never overridden, the input dict is not mutated, and the Responses API path is untouched (it supports function calling at any reasoning effort). No-tools requests are untouched, so the model's default (medium) reasoning effort still applies there.
- `examples/agents/create_chat_agent.py` — `gpt-4o-mini` → `gpt-6-luna` and `claude-sonnet-4-5` → `claude-sonnet-5-5` in all seven agent setups.

## Files in this folder

- `fix.patch` — unified diff of the three source files above; applies cleanly to `camel-ai/camel` master with `git apply fix.patch` (verified).
- `test_model_type.py` — updated `test/models/test_model_type.py` with 3 new tests: default is `gpt-6-luna` and no longer an alias of `GPT_4_1_MINI`; `GPT_6_LUNA` membership / `is_openai` / `value_for_tiktoken` / 1,050,000 token limit; `CLAUDE_SONNET_5_5` membership / `is_anthropic` / 1,000,000 token limit.
- `test_openai_model.py` — updated `test/models/test_openai_model.py`: `GPT_6_LUNA` added to the `test_openai_model` parametrize list, plus 4 new mocked-client tests: tools on Chat Completions send `reasoning_effort="none"`; no-tools requests send none; an explicit `reasoning_effort="low"` is kept; the Responses API path sends none.

## Local test steps (Bhavana: run before raising the PR)

```bash
git clone https://github.com/camel-ai/camel.git && cd camel
git apply /path/to/fix.patch
cp /path/to/test_model_type.py test/models/test_model_type.py
cp /path/to/test_openai_model.py test/models/test_openai_model.py
pip install -e ".[dev]"        # or: uv sync --extra dev
python -m pytest test/models/test_model_type.py -v
python -m pytest test/models/test_openai_model.py -v
```

No API keys are needed: the new tests use mocked OpenAI clients, following the file's existing `test_prompt_cache_key_passed_to_api` pattern.

## Honest test outcome (what actually ran)

- `python -m py_compile` on all three patched source files and both test files: **clean**.
- `fix.patch` dry-run-applies cleanly to pristine copies of the three files and reproduces the patched files byte-for-byte.
- Enum behaviour was verified with a standalone harness that loads the real patched `camel/types/enums.py` (with the repo's real `unified_model_type.py` and a stub logger): **14/14 assertions pass** (DEFAULT value, no longer an alias, `is_openai`, `value_for_tiktoken`, token limits 1,050,000 / 1,000_000, unchanged limits for the old models). The same harness against the **unpatched** file fails exactly on the new assertions (DEFAULT still `gpt-4.1-mini-2025-04-14`, alias still holds, `GPT_6_LUNA` missing).
- `_sanitize_config` was verified by extracting the method verbatim from the patched `openai_model.py` (via `ast`) and running it against a stub model type: **8/8 cases pass** (tools → `"none"`, no tools → untouched, explicit `"low"` kept, Responses path untouched, other models untouched, O-series stripping unchanged). Against the **unpatched** method, exactly the new-behaviour case fails.
- **Not run:** the repo's own pytest suite. The published package (0.2.90) is older than master (0.2.91a7, the issue's base), and the downloaded sdist failed an execution-risk check in this environment, so it was not extracted or installed — run `pytest` locally with the steps above instead. The new pytest tests mirror the harness cases 1:1 but go through the real `model.run()` → `_request_chat_completion()` path with a mocked client, so they still need a local run before the PR.
- Also verified: `ruff` line-length is 79 in this repo and no added line exceeds it.

## PR rules

- Reference the open issue: **camel-ai/camel#4542**. Do **not** open a new issue for this fix — one already exists.
- Re-check the issue and the open-PR list for a competing fix before submitting (none existed Nov 21, 2026; the reporter offered to open one).
- Title suggestion: `fix(types): move DEFAULT to gpt-6-luna; default reasoning_effort to none for tool calls (#4542)`.
- Nothing here touches ADP work. Only the three source files + two test files change.
