# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
import asyncio
import os

import pytest

from camel.triggers import (
    InMemoryTriggerStore,
    JsonFileTriggerStore,
    TriggerManager,
    TriggerSpec,
    TriggerState,
)
from camel.triggers.base import available_trigger_types
from camel.triggers.schedule_trigger import ScheduleTrigger
from camel.triggers.webhook_trigger import WebhookTrigger

croniter = pytest.importorskip("croniter")


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


def _make_spec(**kw) -> TriggerSpec:
    defaults = dict(
        name="t",
        type="schedule",
        payload="do something",
        config={"kind": "interval", "seconds": 1.0},
    )
    defaults.update(kw)
    return TriggerSpec(**defaults)


def test_inmemory_store_crud():
    store = InMemoryTriggerStore()
    spec = _make_spec()
    store.add(spec)
    assert store.get(spec.id).name == "t"
    assert len(store.list()) == 1

    spec.name = "renamed"
    store.update(spec)
    assert store.get(spec.id).name == "renamed"

    assert store.delete(spec.id) is True
    assert store.delete(spec.id) is False
    assert store.get(spec.id) is None


def test_inmemory_store_isolates_copies():
    # Mutating a returned spec must not mutate the stored one.
    store = InMemoryTriggerStore()
    spec = _make_spec()
    store.add(spec)
    fetched = store.get(spec.id)
    fetched.name = "mutated"
    assert store.get(spec.id).name == "t"


def test_json_file_store_roundtrip(tmp_path):
    path = os.path.join(tmp_path, "triggers.json")
    store = JsonFileTriggerStore(path)
    spec = _make_spec(max_runs=3)
    store.add(spec)

    # New store instance reads from the same file (survives "restart").
    store2 = JsonFileTriggerStore(path)
    loaded = store2.get(spec.id)
    assert loaded is not None
    assert loaded.name == "t"
    assert loaded.max_runs == 3
    assert loaded.config == {"kind": "interval", "seconds": 1.0}


# --------------------------------------------------------------------------
# Config validation
# --------------------------------------------------------------------------


def test_schedule_validate_cron():
    cfg = ScheduleTrigger.validate_config(
        {"kind": "cron", "expr": "0 9 * * 1-5"}
    )
    assert cfg["kind"] == "cron"
    with pytest.raises(ValueError):
        ScheduleTrigger.validate_config({"kind": "cron", "expr": "nope"})


def test_schedule_validate_interval():
    cfg = ScheduleTrigger.validate_config({"kind": "interval", "seconds": 5})
    assert cfg["seconds"] == 5.0
    with pytest.raises(ValueError):
        ScheduleTrigger.validate_config({"kind": "interval", "seconds": 0.0})
    with pytest.raises(ValueError):
        ScheduleTrigger.validate_config({"kind": "interval", "seconds": True})


def test_schedule_validate_once_must_be_future():
    with pytest.raises(ValueError):
        ScheduleTrigger.validate_config(
            {"kind": "once", "at": "2000-01-01T00:00:00+00:00"}
        )


def test_schedule_validate_unknown_kind():
    with pytest.raises(ValueError):
        ScheduleTrigger.validate_config({"kind": "weekly"})


def test_webhook_validate():
    cfg = WebhookTrigger.validate_config(
        {"path": "/hooks/ci", "method": "post"}
    )
    assert cfg == {"path": "/hooks/ci", "method": "POST"}
    with pytest.raises(ValueError):
        WebhookTrigger.validate_config({"path": "no-leading-slash"})
    with pytest.raises(ValueError):
        WebhookTrigger.validate_config({"path": "/x", "method": "FOO"})


def test_registry_has_builtins():
    types = available_trigger_types()
    assert "schedule" in types
    assert "webhook" in types


# --------------------------------------------------------------------------
# Manager (functional, fast)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_manager_fires_interval_and_exhausts():
    fired = []

    async def sink(event):
        fired.append(event)

    mgr = TriggerManager(emit=sink)
    await mgr.start()
    mgr.create(
        name="poll",
        type="schedule",
        payload="poll ci",
        config={"kind": "interval", "seconds": 1.0},
        max_runs=2,
    )
    # Wait long enough for two 1s fires.
    for _ in range(40):
        if len(fired) >= 2:
            break
        await asyncio.sleep(0.1)
    await mgr.stop()

    assert len(fired) == 2
    assert fired[0].payload == "poll ci"
    # After max_runs the spec is marked exhausted.
    specs = mgr.list()
    assert specs[0].state == TriggerState.EXHAUSTED
    assert not mgr.has_active_triggers


@pytest.mark.asyncio
async def test_manager_dedupes_idempotency_key():
    fired = []

    async def sink(event):
        fired.append(event)

    mgr = TriggerManager(emit=sink)
    await mgr.start()
    spec = mgr.create(
        name="x",
        type="schedule",
        payload="p",
        config={"kind": "interval", "seconds": 1.0},
    )
    # Fire the same idempotency key twice directly.
    from camel.triggers.models import TriggerEvent

    ev = TriggerEvent(
        trigger_id=spec.id,
        trigger_name="x",
        trigger_type="schedule",
        payload="p",
        run_count=1,
        idempotency_key=f"{spec.id}:slot-1",
    )
    await mgr._on_fire(spec.id, ev)
    await mgr._on_fire(spec.id, ev)
    await mgr.stop()
    assert len(fired) == 1


@pytest.mark.asyncio
async def test_manager_pause_resume_cancel():
    mgr = TriggerManager(emit=None)  # CRUD-only
    await mgr.start()
    spec = mgr.create(
        name="x",
        type="schedule",
        payload="p",
        config={"kind": "interval", "seconds": 1.0},
    )
    assert mgr.has_active_triggers

    mgr.set_state(spec.id, TriggerState.PAUSED)
    assert not mgr.has_active_triggers

    mgr.set_state(spec.id, TriggerState.ACTIVE)
    assert mgr.has_active_triggers

    assert mgr.delete(spec.id) is True
    assert mgr.get(spec.id) is None
    await mgr.stop()


@pytest.mark.asyncio
async def test_manager_create_invalid_raises_before_persist():
    mgr = TriggerManager()
    with pytest.raises(ValueError):
        mgr.create(
            name="bad",
            type="schedule",
            payload="p",
            config={"kind": "cron", "expr": "totally invalid"},
        )
    assert mgr.list() == []
