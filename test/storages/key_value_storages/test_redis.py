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
import json
import threading
from unittest.mock import AsyncMock, patch

import pytest

from camel.storages.key_value_storages import RedisStorage


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sid():
    return "test_sid"


@pytest.fixture
def mock_redis_client():
    client = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.setex = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def redis_storage(sid, mock_redis_client):
    with patch(
        'camel.storages.key_value_storages.RedisStorage._create_client'
    ) as create_client_mock:
        create_client_mock.return_value = None
        storage = RedisStorage(sid=sid, loop=asyncio.get_event_loop())
        storage._client = mock_redis_client
        yield storage


def test_save(sid, redis_storage, mock_redis_client):
    records_to_save = [{"key1": "value1"}, {"key2": "value2"}]
    redis_storage.save(records_to_save)

    mock_redis_client.set.assert_called_once_with(
        sid, json.dumps(records_to_save)
    )


def test_load(redis_storage, mock_redis_client):
    records_to_save = [{"key3": "value3"}, {"key4": "value4"}]
    mock_redis_client.get.return_value = json.dumps(records_to_save)

    loaded_records = redis_storage.load()
    assert loaded_records == records_to_save


def test_clear(sid, redis_storage, mock_redis_client):
    redis_storage.clear()

    mock_redis_client.delete.assert_called_once_with(sid)


def _make_storage(sid, client, loop=None):
    r"""Builds a RedisStorage with a stub client and no real connection.

    ``_create_client`` is patched out rather than pointed at a fake server:
    what is under test is the sync/async bridging in ``_run_async``, which is
    upstream of any Redis I/O.
    """
    with patch(
        'camel.storages.key_value_storages.RedisStorage._create_client'
    ) as create_client_mock:
        create_client_mock.return_value = None
        storage = RedisStorage(sid=sid, loop=loop)
    storage._client = client
    return storage


def _call_from_inside_a_running_loop(fn, *args, **kwargs):
    r"""Calls ``fn`` from a thread that is *running* an event loop.

    The sync methods have to be invoked on the loop thread itself -- that is
    what a FastAPI handler or a notebook cell does, and it is the only way to
    reach the branch that used to hang. Offloading with
    ``asyncio.to_thread`` would leave the worker with no running loop and
    would silently exercise the plain ``run_until_complete`` path instead.

    The call runs on a daemon thread with a join timeout, so a regression
    that hangs fails the test rather than stalling the suite: ``_run_async``
    waits on ``future.result()`` with no timeout at all, so nothing else
    would ever end the wait.
    """
    outcome = {}

    def target():
        async def main():
            try:
                outcome["value"] = fn(*args, **kwargs)
            except BaseException as exc:
                outcome["error"] = exc

        asyncio.run(main())

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=30)

    assert not thread.is_alive(), (
        "the call never returned: the coroutine is waiting on a loop that "
        "this thread is blocking"
    )
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]


def test_constructing_in_a_thread_without_a_loop(sid, mock_redis_client):
    r"""Construction must not require the calling thread to have a loop.

    ``asyncio.get_event_loop()`` raises ``RuntimeError`` in a thread that has
    no loop, so building a ``RedisStorage`` from a worker thread failed
    outright.
    """
    outcome = {}

    def target():
        try:
            storage = _make_storage(sid, mock_redis_client)
            outcome["value"] = storage.load()
        except BaseException as exc:
            outcome["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout=30)

    assert not thread.is_alive()
    assert "error" not in outcome, outcome.get("error")
    assert outcome["value"] == []


def test_save_and_load_inside_a_running_loop(sid, mock_redis_client):
    r"""The regression: sync methods called while a loop runs on this thread.

    ``_run_async`` handed the coroutine to the caller's own loop and then
    blocked on ``future.result()`` with no timeout. The loop cannot advance a
    coroutine while the thread it runs on is blocked, so the call hung
    forever.
    """
    records = [{"key1": "value1"}]
    mock_redis_client.get.return_value = json.dumps(records)
    storage = _make_storage(sid, mock_redis_client)

    def exercise():
        storage.save(records)
        return storage.load()

    assert _call_from_inside_a_running_loop(exercise) == records
    mock_redis_client.set.assert_called_once_with(sid, json.dumps(records))


def test_supplied_idle_loop_is_not_driven_from_an_async_thread(
    sid, mock_redis_client
):
    r"""A caller-supplied loop that is idle must not be run re-entrantly.

    Even when the supplied loop is *not* the one running here,
    ``run_until_complete`` refuses to drive it from a thread that is already
    running another loop, raising "Cannot run the event loop while another
    loop is running". This is the failure mode of the common shape where a
    storage is built at import time and used from async code later.

    The assertion is on ``_run_async`` directly rather than on ``load()``:
    ``load()`` catches every exception and returns ``[]``, so an assertion on
    its result cannot distinguish "the load worked and the store was empty"
    from "the bridge raised and the error was swallowed" -- which is also why
    this bug can surface as silent data loss rather than as a traceback.
    """
    idle_loop = asyncio.new_event_loop()

    async def probe():
        return "done"

    try:
        storage = _make_storage(sid, mock_redis_client, loop=idle_loop)
        assert (
            _call_from_inside_a_running_loop(storage._run_async, probe())
            == "done"
        )
    finally:
        idle_loop.close()


def test_coroutine_does_not_run_on_the_callers_loop(sid, mock_redis_client):
    r"""The coroutine must run on a loop other than the one being blocked.

    Scheduling it on the caller's loop is the cause of the hang, so the
    property is asserted directly rather than inferred from the absence of a
    timeout.
    """
    storage = _make_storage(sid, mock_redis_client)
    seen = []

    async def probe():
        seen.append(asyncio.get_running_loop())
        return "done"

    def exercise():
        caller_loop = asyncio.get_running_loop()
        assert storage._run_async(probe()) == "done"
        return caller_loop

    caller_loop = _call_from_inside_a_running_loop(exercise)

    assert seen and seen[0] is not caller_loop


def test_supplied_running_loop_is_still_used_from_another_thread(
    sid, mock_redis_client
):
    r"""A supplied loop running elsewhere is used, not bypassed.

    This is the case ``run_coroutine_threadsafe`` is actually for, and the
    only one the original code got right, so the fix must not regress it: an
    application that hands in its own loop should keep its Redis traffic
    there.
    """
    other_loop = asyncio.new_event_loop()
    ready = threading.Event()

    def run():
        asyncio.set_event_loop(other_loop)
        other_loop.call_soon(ready.set)
        other_loop.run_forever()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    assert ready.wait(timeout=10)

    try:
        storage = _make_storage(sid, mock_redis_client, loop=other_loop)
        seen = []

        async def probe():
            seen.append(asyncio.get_running_loop())
            return "done"

        assert storage._run_async(probe()) == "done"
        assert seen == [other_loop]
    finally:
        other_loop.call_soon_threadsafe(other_loop.stop)
        thread.join(timeout=10)
        other_loop.close()


def test_exceptions_propagate_from_inside_a_running_loop(
    sid, mock_redis_client
):
    r"""A failure in the coroutine must reach the synchronous caller."""
    storage = _make_storage(sid, mock_redis_client)

    async def boom():
        raise RuntimeError("coroutine failed")

    def exercise():
        return storage._run_async(boom())

    with pytest.raises(RuntimeError, match="coroutine failed"):
        _call_from_inside_a_running_loop(exercise)


def test_context_manager_stops_the_background_loop(sid, mock_redis_client):
    r"""Leaving the ``with`` block must not leave a thread per instance."""
    storage = _make_storage(sid, mock_redis_client)

    with storage:
        assert storage.load() == []
        loop = storage._owned_loop
        assert loop is not None and loop.is_running()

    assert storage._owned_loop is None
    assert loop.is_closed()
    mock_redis_client.close.assert_awaited_once()
