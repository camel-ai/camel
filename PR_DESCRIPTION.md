# Fix: prevent orphan `tool` messages when `enable_snapshot_clean` is on

## Summary
This PR fixes a state-leak issue in `ChatAgent` that can produce invalid message history (orphan `tool` messages) across agent reuse scenarios.

## Root Cause
- `ChatAgent` keeps snapshot-clean metadata in `_tool_output_history`.
- `reset()` previously did not clear this cache.
- When an agent instance is reused (e.g., worker pool), stale entries from a previous task can still be processed.
- `_clean_snapshot_in_memory()` could rewrite a cleaned `FUNCTION/tool` record even if the original referenced records no longer existed in current memory.
- This may inject orphan `tool` messages (without preceding `assistant.tool_calls`), which can trigger strict backend validation errors (e.g., Azure/LiteLLM 400).

## Fix Approach
1. Clear snapshot-clean cache on reset:
   - `ChatAgent.reset()` now clears `_tool_output_history`.
2. Add safe-guard before rewriting cleaned tool output:
   - In `_clean_snapshot_in_memory()`, only rewrite when referenced record UUIDs still exist in storage.
   - If no referenced records are found, skip rewrite and mark the entry as cached.

## Why this is safe
- Normal snapshot-clean flow is unchanged when records exist.
- Only stale/cross-task cache entries are blocked from writing new `tool` records.
- This prevents invalid cross-conversation contamination without affecting valid tool-call chains.

## Tests
Added unit tests in `test/agents/test_chat_agent.py`:
- `test_chat_agent_reset_clears_tool_output_history`
- `test_clean_snapshot_in_memory_skips_missing_records`

