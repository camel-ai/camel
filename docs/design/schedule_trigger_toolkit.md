# Design: Schedule Trigger Toolkit

Status: **Draft / for review**
Author: CAMEL-AI
Target branch: `claude/feat-trigger-operations-SMTrJ`

## 1. Goal

Give an agent a **toolkit to CRUD its own schedules**. When a schedule
fires, it **notifies the existing session** — the same `ChatAgent` or
`Workforce` that created it — so the agent can act on the trigger without a
human re-prompting it.

Concretely, the agent should be able to say things like:

- "Every weekday at 9am, summarize my unread email." (recurring cron)
- "In 30 minutes, check if the build finished." (one-shot delay)
- "Every 5 minutes until the deploy is green, poll CI." (interval + stop
  condition)

…and then *cancel / list / pause / update* those schedules later, all
through tool calls.

### Non-goals (v1)

- Distributed / multi-process scheduling (single process, single session).
- Cross-session fan-out (a trigger created in session A waking session B).
- Guaranteed exactly-once delivery across crashes (we aim for at-least-once
  with idempotency keys; see §7).

## 2. The core design tension

A **tool runs *during* a step** — synchronously, inside the agent's
reasoning loop. A **schedule fires *later*** — typically when the agent is
idle with no `step()` on the stack. The feature therefore splits into two
problems with very different shapes:

1. **CRUD half (easy).** `create_schedule(...)`, `list_schedules()`, etc.
   are ordinary tool calls. The toolkit already gets a back-reference to its
   owning agent via the existing `RegisteredAgentToolkit` mixin
   (`camel/toolkits/base.py:119`), wired automatically by `ChatAgent`
   (`camel/agents/chat_agent.py:604`).

2. **"Notify the session" half (hard).** Something must **outlive a single
   step** to (a) keep time and (b) re-enter the session when a trigger
   fires. This is where the runtimes differ:

| Runtime | Live loop between turns? | Natural injection point |
|---|---|---|
| **Workforce** | ✅ async `_listen_to_channel()` runs while tasks pending (`workforce.py:5207`) | `add_task()` → `_pending_tasks` deque, consumed next loop iteration (`workforce.py:2249`) |
| **ChatAgent** | ❌ dies when `step()` returns | needs a thin runner that drains an inbox and calls `step()`; can wake a blocked loop via `pause_event` (`chat_agent.py:2941`) |

A bare `ChatAgent` is request/response — it is not a daemon. So for the
ChatAgent path we ship a small **`AgentSession` runner** that stays alive
and drains an inbox queue. Workforce already has such a loop, so there the
integration is nearly free.

## 3. Architecture — three decoupled layers

```
┌──────────────────────────────────────────────────────────┐
│  ScheduleToolkit  (BaseToolkit + RegisteredAgentToolkit)  │  agent-facing tools
│   create_schedule / list / get / update / cancel / pause  │
└───────────────┬──────────────────────────────────────────┘
                │ CRUD
┌───────────────▼──────────────────────────────────────────┐
│  Scheduler engine  (session-scoped, background thread)    │  owns timing + store
│   - ScheduleStore (pluggable; default JSON file)          │
│   - timer thread; croniter for cron exprs                 │
│   on fire ──► sink.deliver(TriggerEvent)                  │
└───────────────┬──────────────────────────────────────────┘
                │ polymorphic delivery (knows nothing about agents)
┌───────────────▼──────────────────────────────────────────┐
│  TriggerSink  (one adapter per runtime)                   │  re-enters the session
│   • ChatAgentSink   → inbox queue, drained by AgentSession│
│   • WorkforceSink   → workforce.add_task(Task(payload))   │
└──────────────────────────────────────────────────────────┘
```

**Key invariant:** the Scheduler depends only on the `TriggerSink`
interface. It never imports `ChatAgent` or `Workforce`. That decoupling is
exactly what lets one toolkit serve multiple runtimes — to add a runtime you
write one ~30-line sink, nothing else.

### Why this split

- The **toolkit** is pure CRUD over a store: trivially testable, no timing.
- The **engine** is pure time→event: testable with a fake clock, no agents.
- The **sink** is pure delivery: testable with a stub session.

Each layer is unit-testable in isolation with no LLM calls.

## 4. Data model

```python
class TriggerType(str, Enum):
    CRON     = "cron"      # croniter expression, e.g. "0 9 * * 1-5"
    INTERVAL = "interval"  # every N seconds
    ONCE     = "once"      # single fire at a datetime / after a delay

class Schedule(BaseModel):
    id: str                      # uuid
    name: str                    # human label, agent-supplied
    trigger_type: TriggerType
    trigger_expr: str            # cron string | seconds | iso-datetime
    payload: str                 # the message/instruction injected on fire
    owner_session_id: str        # which session created it
    enabled: bool = True
    next_run: datetime
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None         # stop after N fires
    until: Optional[datetime] = None        # stop after this time
    created_at: datetime
    metadata: dict = {}          # idempotency key, tags, etc.
```

`payload` is intentionally just text: on fire it becomes a user-role
message (ChatAgent) or a `Task.content` (Workforce). Keeping it a plain
string keeps the sinks dumb and the model's mental model simple.

## 5. Toolkit API (agent-facing tools)

All methods return JSON-serializable dicts (CAMEL convention: tools return
strings/dicts the model can read back).

| Tool | Args | Returns |
|---|---|---|
| `create_schedule` | `name, trigger_type, trigger_expr, payload, max_runs?, until?` | `{id, next_run}` |
| `list_schedules` | `enabled_only?` | `[{id, name, trigger, next_run, run_count}]` |
| `get_schedule` | `id` | full `Schedule` dict |
| `update_schedule` | `id, **fields` | updated `Schedule` |
| `pause_schedule` / `resume_schedule` | `id` | `{id, enabled}` |
| `cancel_schedule` | `id` | `{id, deleted: true}` |

Validation lives in the toolkit: cron strings are checked with
`croniter.is_valid`, intervals must be `> 0`, `once` datetimes must be in
the future. Invalid input returns a readable error string the model can
self-correct from — never raises into the step loop.

## 6. Scheduler engine

- **Thread model:** one daemon `threading.Thread` per session running a
  sleep-until-next-due loop (`min(next_run)` across enabled schedules,
  bounded by a max poll interval so newly-added schedules are noticed). A
  `threading.Condition` wakes the loop immediately on CRUD changes instead
  of busy-polling.
- **Cron:** `croniter` (new **optional** dependency under a `[scheduler]`
  extra; matches CAMEL's optional-dependency pattern). `next_run` is
  recomputed from `croniter(expr, base=now)` after each fire.
- **Firing:** when `now >= next_run` and `enabled`, build a `TriggerEvent`
  and call `sink.deliver(event)`. Then increment `run_count`, set
  `last_run`, recompute `next_run`; disable/delete if `max_runs`/`until`
  reached or `ONCE`.
- **Misfire policy:** if the process was asleep past a due time, fire once
  on wake (coalesce), not once-per-missed-slot. Configurable later.
- **Thread-safety:** the store is guarded by a lock; CRUD from the tool
  thread and reads from the timer thread are serialized.

```python
class TriggerEvent(BaseModel):
    schedule_id: str
    name: str
    payload: str
    fired_at: datetime
    run_count: int
    idempotency_key: str   # f"{schedule_id}:{next_run.isoformat()}"

class TriggerSink(Protocol):
    def deliver(self, event: TriggerEvent) -> None: ...
```

## 7. Delivery per runtime

### 7.1 ChatAgent + `AgentSession` runner

Because a bare `ChatAgent` does not run between turns, we add a small
host loop:

```python
class AgentSession:
    """Keeps a ChatAgent alive and drains a trigger inbox."""
    def __init__(self, agent: ChatAgent):
        self.agent = agent
        self.inbox: queue.Queue[TriggerEvent] = queue.Queue()

    # ChatAgentSink.deliver() just does self.inbox.put(event)

    def run_forever(self):
        while not self._stop:
            event = self.inbox.get()              # blocks until a trigger
            msg = f"[scheduled trigger: {event.name}] {event.payload}"
            self.agent.step(msg)                  # agent reacts, may use tools
```

- The sink only enqueues; the session loop owns all `agent.step()` calls,
  so we never call `step()` re-entrantly from inside a tool (which the loop
  forbids anyway).
- If the agent is mid-`step()` when a trigger arrives, it's simply picked up
  on the next `inbox.get()` — natural backpressure, no interruption of an
  in-flight turn.
- Optional: expose the agent's `pause_event` so an idle blocked loop can be
  woken immediately (`chat_agent.py:2941`).

This runner is opt-in. Users who only want CRUD-without-self-notification
(e.g. an external system reads the schedule store) can skip it.

### 7.2 Workforce

```python
class WorkforceSink:
    def __init__(self, workforce: Workforce):
        self.workforce = workforce
    def deliver(self, event: TriggerEvent) -> None:
        self.workforce.add_task(Task(content=event.payload,
                                     id=event.idempotency_key))
```

`add_task` appends to `_pending_tasks`; the running `_listen_to_channel()`
loop assigns it on the next iteration (`workforce.py:2249`, `:5207`). No
changes to workforce internals required. Thread-safety of the deque append
from the timer thread is the one spot we must verify/guard during
implementation.

## 8. Persistence (pluggable, default JSON file)

```python
class ScheduleStore(Protocol):
    def add(self, s: Schedule) -> None: ...
    def get(self, id: str) -> Optional[Schedule]: ...
    def list(self) -> list[Schedule]: ...
    def update(self, s: Schedule) -> None: ...
    def delete(self, id: str) -> None: ...

class JsonFileStore(ScheduleStore):   # default
    # atomic write (tmp + os.replace), one file per session
class InMemoryStore(ScheduleStore):   # tests / ephemeral
```

On engine start, load persisted schedules and recompute `next_run` for
each (handling misfires per §6). This is what lets schedules survive a
process restart. A DB-backed store can be added later behind the same
Protocol.

## 9. Idempotency & safety

- **Idempotency key** = `schedule_id + scheduled-slot`. Workforce uses it as
  `Task.id`; the ChatAgent runner can dedup recent keys to avoid double-fire
  on restart misfire coalescing.
- **Runaway guard:** intervals have an enforced minimum; `max_runs`/`until`
  strongly encouraged in tool descriptions so the model bounds recurrence.
- **Resource cleanup:** the daemon thread stops when the session closes;
  `AgentSession` exposes `stop()`.

## 10. File layout

```
camel/toolkits/schedule_toolkit.py        # ScheduleToolkit (tools)
camel/schedules/__init__.py
camel/schedules/models.py                 # Schedule, TriggerEvent, enums
camel/schedules/engine.py                 # Scheduler (timer thread)
camel/schedules/store.py                  # ScheduleStore, JsonFileStore, InMemory
camel/schedules/sinks.py                  # TriggerSink, ChatAgentSink, WorkforceSink
camel/societies/agent_session.py          # AgentSession runner
examples/toolkits/schedule_toolkit.py     # runnable demo (cron + once)
test/toolkits/test_schedule_toolkit.py    # CRUD + fake-clock engine tests
```

Register `ScheduleToolkit` in `camel/toolkits/__init__.py`. Add `croniter`
under an optional `[scheduler]` extra in `pyproject.toml`.

## 11. Test plan (no LLM calls)

- **Toolkit CRUD:** create/list/update/pause/cancel against `InMemoryStore`;
  invalid cron / negative interval / past `once` return error strings.
- **Engine with fake clock:** inject a controllable `now()`; assert fire
  timing, `next_run` recomputation, `max_runs`/`until` termination, misfire
  coalescing.
- **Sinks with stub session:** `ChatAgentSink` enqueues; `WorkforceSink`
  calls `add_task` with the idempotency id (stub workforce).
- **Persistence:** `JsonFileStore` round-trips; reload recomputes `next_run`.
- **Concurrency smoke:** CRUD from one thread while the timer thread fires,
  asserting no lost/duplicated schedules.

## 12. Open questions for review

1. **Engine lifetime ownership** — should the scheduler thread be owned by
   the toolkit, or by the `AgentSession` / `Workforce`? (Leaning: owned by
   the runner/session so toolkit stays pure CRUD.)
2. **One thread per session vs one shared scheduler** — v1 proposes
   per-session for isolation; a shared engine with session tagging scales
   better but complicates teardown.
3. **Should triggers carry structured payloads** (tool name + args) instead
   of free text, so the agent can be *directed* rather than *prompted*?
4. **Workforce deque thread-safety** — confirm `add_task` from a non-loop
   thread is safe, or route through `task_channel.post_task` via
   `run_coroutine_threadsafe` instead.
```

</content>
</invoke>
