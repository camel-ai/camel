# Design: Agentic Triggers

Status: **Implemented (v1)**
Author: CAMEL-AI
Branch: `claude/feat-trigger-operations-SMTrJ`

## 1. Goal

Give an agent a **versatile trigger framework** it can CRUD at runtime. A
*trigger* is any source that emits events over time — a **schedule** (cron /
interval / one-shot) or an incoming **webhook** today, anything else
tomorrow. When a trigger fires, it **injects a task into the running session**
so the agent acts on it without a human re-prompting.

Example agent intents:

- "Every weekday at 9am, summarize my unread email." (cron schedule)
- "In 30 minutes, check if the build finished." (one-shot schedule)
- "When CI POSTs to /hooks/ci, triage the result." (webhook)

…plus *list / get / update / pause / resume / cancel*, all through tools.

v1 wires the framework into **Workforce** (it already runs a daemon loop). The
framework itself is runtime-agnostic, so other runtimes can be added by
supplying one small sink.

## 2. Layers

```
ScheduleTrigger  WebhookTrigger  ...        # pluggable trigger types
        \            |           /
         \           |          /
          v          v         v
      TriggerManager (asyncio tasks + dedupe + store)   # timing, runtime-agnostic
                     |
                     | emit(event)  ── injected by host
                     v
   Workforce listen loop  (keep-alive + async inject)   # the runtime
        ^
        |
   TriggerToolkit  (create/list/get/update/pause/resume/cancel)  # agent-facing CRUD
```

Files:

```
camel/triggers/models.py            # TriggerSpec, TriggerEvent, TriggerState
camel/triggers/base.py              # BaseTrigger + register_trigger registry
camel/triggers/store.py             # BaseTriggerStore, InMemory, JsonFile
camel/triggers/schedule_trigger.py  # cron / interval / once
camel/triggers/webhook_trigger.py   # incoming HTTP
camel/triggers/webhook_server.py    # shared aiohttp server
camel/triggers/manager.py           # TriggerManager
camel/toolkits/trigger_toolkit.py   # TriggerToolkit (CRUD tools)
camel/societies/workforce/workforce.py  # enable_triggers + loop integration
examples/triggers/workforce_triggers.py
test/triggers/, test/toolkits/test_trigger_toolkit.py,
test/workforce/test_workforce_triggers.py
```

`croniter` + `aiohttp` are optional, under the `triggers` extra:
`pip install 'camel-ai[triggers]'`.

## 3. Extensibility — adding a trigger type

Implement `BaseTrigger` and register it. Nothing else changes — the toolkit,
store, and manager are all type-agnostic (they only read `TriggerSpec.type`
and `.config`).

```python
@register_trigger("file_watch")
class FileWatchTrigger(BaseTrigger):
    @classmethod
    def validate_config(cls, config): ...      # validate & normalize config
    async def run(self, emit):                  # loop; await emit(event) on fire
        ...
```

`config` is a free-form dict validated by the owning class, so each type
carries its own settings without schema churn elsewhere.

## 4. Why the task channel was the wrong layer

`task_channel.post_task` requires an `assignee_id` — it is the
coordinator→worker transport, and tasks there are already decomposed and
assigned. A high-level trigger payload must enter *above* the channel and flow
through normal assignment. So the integration point is the **listen loop**,
not the channel.

## 5. The decisive constraint and the two loop changes

The Workforce listen loop is a daemon **only while it has work**: it breaks the
moment `_pending_tasks` is empty and nothing is in flight
(`workforce.py`, "All tasks completed, will exit loop"). So the real work is
teaching it to **idle while alive** when triggers are registered.

Two changes in `_listen_to_channel`:

1. **Keep-alive** — `_has_active_triggers()` is added to the loop's exit
   condition, and the "all done" break becomes an idle park
   (`_wait_for_trigger`) instead of an exit when triggers are active.
2. **Async injection** — `_inject_trigger_event` appends the fired event as a
   direct subtask and sets a wakeup event. Because the manager runs as an
   asyncio task on the workforce's own event loop, this append is on the loop
   thread (no lock, no cross-thread race), and the wakeup releases an idling
   loop immediately.

Supporting decisions (from review):

- **Loop idles, stays alive** — a workforce with active triggers becomes a
  long-running service; it self-terminates only when triggers are exhausted /
  paused, or on an explicit stop.
- **Direct subtask** — fired triggers enter via `as_subtask=True` (no
  decomposition), lower latency for already-atomic instructions.

## 6. Reliability

- **Idempotency**: each event has `idempotency_key = trigger_id + slot`, reused
  as the injected `Task.id`. The manager also keeps a bounded set of recent
  keys, so a coalesced misfire can't double-enqueue the same slot.
- **Exhaustion**: `max_runs` / `until` mark a trigger `EXHAUSTED`; the loop
  then stops being kept alive by it.
- **Persistence**: `JsonFileTriggerStore` (atomic tmp+replace) survives restart;
  `InMemoryTriggerStore` for tests/ephemeral. Backend is pluggable.
- **Webhook auth**: optional HMAC-SHA256 `X-Signature` validation per hook.
- **Lifecycle**: the manager starts when the loop starts and is cancelled when
  it exits; webhook server stops with it.

## 7. Tests (no LLM, no live network in unit tests)

- Store CRUD + JSON round-trip/reload.
- Config validation for cron / interval / once / webhook (bad input raises).
- Manager firing on a fast interval, exhaustion, idempotency dedupe,
  pause/resume/cancel, invalid-create-before-persist.
- Toolkit CRUD returning error strings (never raising into the step loop).
- Workforce integration: inject appends task w/ idempotency id, embeds
  structured data, respects stop, keep-alive reflects manager state, idle wait
  wakes on event and short-circuits on stop.

(Webhook server is additionally validated end-to-end manually with a real
HTTP POST → 202 + fire, unknown path → 404.)

## 8. Open questions / follow-ups

1. **ChatAgent runtime** — add an `AgentSession` runner (drains an inbox,
   calls `step()`) so a bare ChatAgent gets the same self-notification. Same
   framework, one new sink.
2. **Structured payloads** — let a trigger carry a tool-name + args instead of
   free text, to *direct* rather than *prompt* the agent.
3. **Auto-stop policy** — a `max_idle` / explicit shutdown tool so a
   trigger-driven workforce can bound its own lifetime.
4. **Snapshot/resume** — persist & restore active triggers across workforce
   snapshots.
