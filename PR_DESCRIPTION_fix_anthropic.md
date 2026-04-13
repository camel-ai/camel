# PR Description

## Summary
- Simplify `AnthropicModel` structured output handling by removing the legacy beta structured-outputs path and keeping the stable `messages.create + output_config` flow.
- Update the Anthropic structured output example to better match real third-party Anthropic-compatible endpoints by supporting configurable base URL/model, using a local fallback token counter, and documenting a successful combined `response_format + tools` run.

## What Changed
- `camel/models/anthropic_model.py`
  - Removed the legacy `use_beta_for_structured_outputs` constructor argument and internal beta-header branch.
  - Removed the `ANTHROPIC_BETA_FOR_STRUCTURED_OUTPUTS` constant.
  - Unified sync and async execution onto the standard `messages.create` path.
- `test/models/test_anthropic_model.py`
  - Removed beta structured-output compatibility tests that no longer apply.
  - Kept the tests that validate the current `output_config` request shape and tool/schema handling.
- `docs/mintlify/reference/camel.models.anthropic_model.mdx`
  - Removed the obsolete `use_beta_for_structured_outputs` parameter from the generated reference text.
- `examples/models/anthropic_structured_output_example.py`
  - Simplified the example to a single combined scenario: Anthropic structured output plus tool use.
  - Added support for `ANTHROPIC_API_BASE_URL` and `ANTHROPIC_MODEL` so the example can run against Anthropic-compatible platforms.
  - Added a local fallback token counter (`OpenAITokenCounter(ModelType.GPT_4O_MINI)`) with an inline comment explaining why third-party compatible endpoints may need it.
  - Added a minimal explicit `max_tokens` config for compatibility with endpoints that require it.
  - Appended a real sample output block showing the raw JSON response, parsed object, parsed JSON, and tool calls.

## Testing
- `python3 -m py_compile camel/models/anthropic_model.py test/models/test_anthropic_model.py`: passed
- `python3 -m py_compile examples/models/anthropic_structured_output_example.py`: passed
- `ANTHROPIC_API_KEY=... ANTHROPIC_API_BASE_URL='https://zenmux.ai/api/anthropic' ANTHROPIC_MODEL='claude-opus-4-6' uv run --extra model_platforms python examples/models/anthropic_structured_output_example.py`: passed
  - Verified `response_format + tools` together
  - Verified parsed Pydantic output was populated
  - Verified tool calls were executed and recorded

## Risks / Compatibility
- This removes the explicit legacy beta structured-output fallback from `AnthropicModel`. Environments that still depend on the old beta header path will need to migrate to the standard `output_config` flow.
- The example now documents a third-party compatible endpoint workaround via a local fallback token counter. That change is limited to the example and does not alter the shared token counting implementation.

## Out of Scope
- No broader changes to token counting behavior across the Anthropic backend.
- No changes to unrelated model backends or shared structured output APIs.
