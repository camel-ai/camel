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
r"""Tests for Workforce <-> trigger integration.

Constructing a full ``Workforce`` requires model/tokenizer setup, so these
tests bind the real Workforce trigger methods onto a lightweight stand-in
that provides only the attributes those methods touch. This exercises the
actual injection / idle-wait / keep-alive logic without an LLM.
"""

import asyncio
from collections import deque

import pytest

from camel.societies.workforce.workforce import Workforce
from camel.triggers import TriggerManager, TriggerState
from camel.triggers.models import TriggerEvent

pytest.importorskip("croniter")


class _WFStub:
    r"""Minimal stand-in exposing the attributes the trigger methods use."""

    def __init__(self):
        self.node_id = "stub-wf"
        self._pending_tasks = deque()
        self._stop_requested = False
        self._skip_requested = False
        self._trigger_manager = None
        self._trigger_wakeup = asyncio.Event()

    # Bind the real implementations.
    enable_triggers = Workforce.enable_triggers
    trigger_manager = Workforce.trigger_manager
    _has_active_triggers = Workforce._has_active_triggers
    _wait_for_trigger = Workforce._wait_for_trigger
    _inject_trigger_event = Workforce._inject_trigger_event


def _event(payload="hello", key="t1:slot", data=None):
    return TriggerEvent(
        trigger_id="t1",
        trigger_name="my-trigger",
        trigger_type="schedule",
        payload=payload,
        data=data or {},
        run_count=1,
        idempotency_key=key,
    )


def test_enable_triggers_attaches_manager():
    wf = _WFStub()
    mgr = wf.enable_triggers()
    assert isinstance(mgr, TriggerManager)
    assert wf.trigger_manager is mgr
    # Not running yet -> not keeping the loop alive.
    assert wf._has_active_triggers() is False


@pytest.mark.asyncio
async def test_inject_event_appends_task_and_wakes():
    wf = _WFStub()
    wf.enable_triggers()
    await wf._inject_trigger_event(_event(payload="ping", key="t1:1"))
    assert len(wf._pending_tasks) == 1
    task = wf._pending_tasks[0]
    assert task.id == "t1:1"  # idempotency key becomes the task id
    assert task.content == "ping"
    assert task.additional_info["_trigger_name"] == "my-trigger"
    assert wf._trigger_wakeup.is_set()


@pytest.mark.asyncio
async def test_inject_event_embeds_structured_data():
    wf = _WFStub()
    wf.enable_triggers()
    await wf._inject_trigger_event(
        _event(payload="handle", key="t1:2", data={"status": "ok"})
    )
    content = wf._pending_tasks[0].content
    assert "handle" in content
    assert "status" in content and "ok" in content


@pytest.mark.asyncio
async def test_inject_event_skipped_when_stopping():
    wf = _WFStub()
    wf.enable_triggers()
    wf._stop_requested = True
    await wf._inject_trigger_event(_event())
    assert len(wf._pending_tasks) == 0


@pytest.mark.asyncio
async def test_has_active_triggers_reflects_manager_state():
    wf = _WFStub()
    mgr = wf.enable_triggers()
    await mgr.start()
    mgr.create(
        name="p",
        type="schedule",
        payload="p",
        config={"kind": "interval", "seconds": 1.0},
    )
    assert wf._has_active_triggers() is True

    # Pausing all triggers should drop keep-alive.
    spec_id = mgr.list()[0].id
    mgr.set_state(spec_id, TriggerState.PAUSED)
    assert wf._has_active_triggers() is False
    await mgr.stop()


@pytest.mark.asyncio
async def test_wait_for_trigger_returns_on_wakeup():
    wf = _WFStub()
    wf.enable_triggers()

    async def fire_soon():
        await asyncio.sleep(0.05)
        wf._trigger_wakeup.set()

    firer = asyncio.ensure_future(fire_soon())
    # Should return well before the 5s timeout once wakeup is set.
    await asyncio.wait_for(wf._wait_for_trigger(), timeout=2.0)
    await firer


@pytest.mark.asyncio
async def test_wait_for_trigger_short_circuits_on_stop():
    wf = _WFStub()
    wf.enable_triggers()
    wf._stop_requested = True
    # Returns immediately without waiting.
    await asyncio.wait_for(wf._wait_for_trigger(), timeout=0.5)
