# Design: Schedule Trigger for Workforce

Status: **Draft / for review**
Author: CAMEL-AI
Target branch: `claude/feat-trigger-operations-SMTrJ`

## 1. Goal

Give a `Workforce` agent a **toolkit to CRUD its own schedules**. When a
schedule fires, it **injects a task into the same running workforce** — so
the workforce acts on the trigger without a human re-prompting it.

Example agent intents:

- "Every weekday at 9am, summarize my unread email." (recurring cron)
- "In 30 minutes, check if the build finished." (one-shot delay)
- "Every 5 minutes until the deploy is green, poll CI." (interval + stop)

…plus *cancel / list / pause / update* later, all through tool calls.

Scope is **Workforce only** for v1 (it already has a daemon loop). ChatAgent
/ RolePlaying are deferred.

## 2. Why the task channel is the wrong layer

Two facts from the source rule out integrating at `task_channel.py`:

1. **`post_task` requires an `assignee_id`** (`task_channel.py:203`). The
   channel is the *coordinator→worker* transport; tasks there are already
   decomposed and assigned. A high-level trigger ("summarize my email")
   must instead enter *above* the channel and flow through the normal
   pending-queue → assignment path.
2. The channel has no concept of time, idling, or schedule ownership — it
   is pure task transport. Bolting scheduling onto it conflates two
   responsibilities.

**Conclusion: extend the listen loop (`_listen_to_channel`), not the
channel.** The loop is where pending tasks are consumed and where "is there
more work?" is decided — exactly the two things scheduling touches.

## 3. The decisive constraint: the loop is *not* an idle daemon

From `workforce.py:5218` and the early break at `:5256`:

```python
while (self._task is None or self._pending_tasks
       or self._in_flight_tasks > 0) and not self._stop_requested:
    ...
    if not self._pending_tasks and self._in_flight_tasks == 0:
        break   # "All tasks completed, will exit loop"
```

The workforce is a daemon **only while it has work**. The instant the queue
drains, `_listen_to_channel()` returns and the run ends. A trigger meant for
9am tomorrow has nothing alive to inject into if today's work finished at
5pm.

So the core feature work is **not** task injection (that part is easy). It
is teaching the workforce to **idle while alive** when schedules are
registered. That capability is genuinely new.

Two supporting facts that shape the mechanism:

- **`add_task` is neither thread-safe nor loop-waking** (`workforce.py:2280`,
  `:2317`): it is a bare `self._pending_tasks.append(...)` on a plain
  `deque`, no lock, no notify. The loop is meanwhile parked in
  `await self._get_returned_task()` / `await self._pause_event.wait()`.
  Appending from a separate **thread** is both a data race and invisible to
  the loop until something else wakes it.
- Therefore the scheduler must run as an **asyncio task on the workforce's
  own event loop**, not a background thread. On fire it mutates state and
  notifies the loop using the same `asyncio` primitives the loop already
  waits on. This eliminates the cross-thread race and the missed-wakeup
  problem together.

> Note: this overturns the earlier general design's "stdlib timer thread +
> `add_task`" sink for the Workforce case. `croniter` for cron math still
> applies; the *threading* model does not.

## 4. Architecture

```
┌──────────────────────────────────────────────────────────┐
│  ScheduleToolkit  (BaseToolkit + RegisteredAgentToolkit)  │  agent-facing tools
│   create / list / get / update / pause / resume / cancel  │
└───────────────┬──────────────────────────────────────────┘
                │ CRUD over store
┌───────────────▼──────────────────────────────────────────┐
│  ScheduleStore  (pluggable; default JSON file)            │  persistence
└───────────────┬──────────────────────────────────────────┘
                │ read by
┌───────────────▼──────────────────────────────────────────┐
│  WorkforceScheduler  (asyncio task on workforce loop)     │  timing
│   - sleeps until min(next_run); croniter for cron         │
│   - woken immediately on CRUD via asyncio.Event           │
│   on fire ──► workforce._inject_scheduled_task(event)     │
└───────────────┬──────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────┐
│  Workforce listen loop  (two minimal extensions)          │
│   (a) keep-alive: don't exit while triggers are active    │
│   (b) async inject: append as subtask + wake the loop     │
└──────────────────────────────────────────────────────────┘
```

The scheduler is **owned by the Workforce** and lives on its event loop. The
toolkit stays pure CRUD; it never touches timing or the loop.

## 5. Two changes to the listen loop

### 5.1 Keep-alive (idle but alive)

Decision: **the loop idles and stays alive** while schedules are registered,
turning a workforce run into a long-running service.

Extend the exit condition so an active scheduler keeps the loop alive:

```python
while (self._task is None or self._pending_tasks
       or self._in_flight_tasks > 0
       or self._scheduler_active) and not self._stop_requested:
```

And the mid-loop "all done" break becomes an **idle park** instead of an
exit when triggers exist:

```python
if not self._pending_tasks and self._in_flight_tasks == 0:
    if self._scheduler_active:
        await self._idle_wait()   # parks until a trigger injects or stop
        continue
    break                          # unchanged when no scheduler
```

`_idle_wait()` waits (no busy-poll) on an `asyncio.Event` that is set by
either (a) a fired trigger injecting a task, or (b) a stop/skip request. This
reuses the existing pause/stop plumbing rather than inventing a new loop.

### 5.2 Async task injection

Decision: fired triggers enter as **direct subtasks** (`as_subtask=True`) —
already-atomic instructions, no decomposition, lower latency.

```python
async def _inject_scheduled_task(self, event: TriggerEvent) -> None:
    task = Task(content=event.payload, id=event.idempotency_key)
    self._pending_tasks.append(task)          # same loop/thread → safe
    self._wake_idle.set()                      # wake _idle_wait()
```

Because the scheduler runs on the workforce's event loop, this append
happens on the **same thread** as the loop — no lock needed, no race. The
`_wake_idle` event ensures an idling loop picks it up immediately.

If a fire happens while the workforce is busy, the subtask simply queues
behind current work and is assigned when a worker frees up — natural
backpressure.

## 6. Scheduler engine (`WorkforceScheduler`)

- **Co-runs on the workforce loop**: started as `asyncio.create_task(...)`
  when the workforce starts (if any schedules exist) and cancelled on stop.
- **Sleep-until-due**: `await asyncio.wait_for(self._crud_changed.wait(),
  timeout=seconds_until_next_due)`. Waking early on CRUD changes means new /
  edited schedules are honored without polling.
- **Cron** via `croniter` (new **optional** dep under a `[scheduler]`
  extra). `next_run` recomputed after each fire.
- **Fire**: when `now >= next_run` and `enabled`, build `TriggerEvent`, call
  `workforce._inject_scheduled_task(event)`, then bump `run_count`, set
  `last_run`, recompute `next_run`; disable/delete on `max_runs` / `until` /
  `ONCE`.
- **Misfire**: if the process slept past a due slot, coalesce to a single
  fire on wake.

```python
class TriggerEvent(BaseModel):
    schedule_id: str
    name: str
    payload: str
    fired_at: datetime
    run_count: int
    idempotency_key: str   # f"{schedule_id}:{slot.isoformat()}" → used as Task.id
```

`_scheduler_active` (used in §5.1) is simply "scheduler task running AND ≥1
enabled schedule".

## 7. Data model

```python
class TriggerType(str, Enum):
    CRON = "cron"; INTERVAL = "interval"; ONCE = "once"

class Schedule(BaseModel):
    id: str
    name: str
    trigger_type: TriggerType
    trigger_expr: str          # cron string | seconds | iso-datetime
    payload: str               # becomes Task.content on fire
    enabled: bool = True
    next_run: datetime
    last_run: Optional[datetime] = None
    run_count: int = 0
    max_runs: Optional[int] = None
    until: Optional[datetime] = None
    created_at: datetime
    metadata: dict = {}
```

## 8. Toolkit API (agent-facing)

All return JSON-serializable dicts; validation errors return readable
strings (never raise into the loop) so the model can self-correct.

| Tool | Args | Returns |
|---|---|---|
| `create_schedule` | `name, trigger_type, trigger_expr, payload, max_runs?, until?` | `{id, next_run}` |
| `list_schedules` | `enabled_only?` | `[{id, name, trigger, next_run, run_count}]` |
| `get_schedule` | `id` | full `Schedule` |
| `update_schedule` | `id, **fields` | updated `Schedule` |
| `pause_schedule` / `resume_schedule` | `id` | `{id, enabled}` |
| `cancel_schedule` | `id` | `{id, deleted: true}` |

Cron validated with `croniter.is_valid`; intervals `> 0`; `once` must be
future. Every CRUD op sets the scheduler's `_crud_changed` event so timing
updates immediately.

The toolkit reaches the workforce/scheduler via a reference supplied at
construction (the workforce owns both). It does **not** rely on
`RegisteredAgentToolkit` here, since the relevant object is the Workforce,
not a single ChatAgent — see Open Question 1.

## 9. Persistence (pluggable, default JSON file)

```python
class ScheduleStore(Protocol):
    def add/get/list/update/delete(...): ...

class JsonFileStore(ScheduleStore):   # default; atomic tmp+os.replace
class InMemoryStore(ScheduleStore):   # tests / ephemeral
```

On workforce start, load schedules and recompute `next_run` (misfire rules
per §6), so schedules survive a process restart.

## 10. Idempotency & safety

- **Idempotency key** = `schedule_id + scheduled-slot`, reused as `Task.id`
  so a coalesced misfire can't double-enqueue the same slot.
- **Runaway guard**: enforced minimum interval; tool descriptions push the
  model toward `max_runs` / `until`.
- **Lifecycle**: scheduler task is cancelled in the workforce stop path;
  no thread to join (it's an asyncio task).

## 11. File layout

```
camel/schedules/__init__.py
camel/schedules/models.py          # Schedule, TriggerEvent, enums
camel/schedules/store.py           # ScheduleStore, JsonFileStore, InMemoryStore
camel/schedules/scheduler.py       # WorkforceScheduler (asyncio task)
camel/toolkits/schedule_toolkit.py # ScheduleToolkit (CRUD tools)
# edits:
camel/societies/workforce/workforce.py   # keep-alive + _inject_scheduled_task + _idle_wait
examples/workforce/scheduled_triggers.py # runnable demo
test/societies/test_workforce_scheduler.py
```

Add `croniter` under an optional `[scheduler]` extra in `pyproject.toml`.

## 12. Test plan (no LLM calls)

- **Toolkit CRUD** against `InMemoryStore`; invalid cron / interval / past
  `once` return error strings; CRUD sets `_crud_changed`.
- **Scheduler with fake clock**: injectable `now()`; assert fire timing,
  `next_run` recompute, `max_runs` / `until` termination, misfire coalesce.
- **Loop keep-alive**: workforce with one schedule and empty queue stays in
  `_idle_wait()` instead of exiting; a fire injects a subtask and it gets
  processed; stop request breaks the idle.
- **Injection**: `_inject_scheduled_task` appends with the idempotency id and
  wakes the loop; double-fire of the same slot dedups by `Task.id`.
- **Persistence**: `JsonFileStore` round-trips; reload recomputes `next_run`.

## 13. Open questions for review

1. **Toolkit→workforce wiring.** The toolkit needs the scheduler/workforce
   handle. Pass it explicitly at construction (proposed), or add a
   `RegisteredWorkforceToolkit` mixin mirroring `RegisteredAgentToolkit`?
2. **Auto-stop policy.** With keep-alive, a workforce with an active
   schedule never self-terminates. Do we want a `max_idle` / explicit
   `shutdown` tool so the agent can end the service, plus a hard cap?
3. **Snapshot/resume interaction.** The loop saves snapshots before tasks;
   should idle periods snapshot too, and should persisted schedules restore
   on resume from snapshot?
4. **Pause semantics.** When the workforce is paused (`_pause_event`),
   should the scheduler also pause (no fires), or queue fires to deliver on
   resume? (Proposed: pause fires too, coalesce on resume.)
</content>
