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
r"""Regression tests for ``Workforce.reset()`` and its event loop.

``reset()`` used to hand ``_pause_event.set()`` to ``self._loop`` and block on
the result. Both cases below reach a loop that will never advance that
coroutine, so ``reset()`` never returned.

Every assertion runs ``reset()`` on a separate daemon thread and checks that
the thread finished, rather than calling it inline. A reintroduced hang then
*fails* the test instead of stalling the run: the original code has no timeout
anywhere on that path.
"""

import asyncio
import os
import threading

import pytest

from camel.societies.workforce.workforce import Workforce, WorkforceState


@pytest.fixture(autouse=True)
def stub_openai_api_key(monkeypatch):
    r"""Ensure OPENAI_API_KEY is set during tests."""
    previous_value = os.environ.get("OPENAI_API_KEY")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy")
    yield
    if previous_value is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", previous_value)


def call_off_thread(func, timeout: float = 5.0) -> None:
    r"""Runs ``func`` on a daemon thread and asserts that it returned.

    Assertions inside the thread would be swallowed, so the outcome is
    collected and re-raised on the caller.
    """
    outcome: list = []

    def body() -> None:
        try:
            func()
            outcome.append(None)
        except BaseException as exc:
            outcome.append(exc)

    thread = threading.Thread(target=body, daemon=True)
    thread.start()
    thread.join(timeout)
    assert not thread.is_alive(), (
        f"{getattr(func, '__name__', func)} did not return within "
        f"{timeout}s -- it is waiting on an event loop that cannot advance it"
    )
    if outcome and outcome[0] is not None:
        raise outcome[0]


def test_reset_returns_when_the_stored_loop_is_open_but_idle():
    r"""``_process_task_with_intervention`` deliberately leaves ``self._loop``
    open when it returns in the ``PAUSED`` state, so that
    ``continue_from_pause`` can reuse it. Nothing drives the loop in between,
    so anything submitted to it there is never advanced -- and the loop looks
    healthy to ``not self._loop.is_closed()``.
    """
    workforce = Workforce("reset-idle-loop")
    loop = asyncio.new_event_loop()
    try:
        workforce._loop = loop
        # What ``run_until_complete`` leaves behind: open, but not running.
        loop.run_until_complete(asyncio.sleep(0))
        workforce._state = WorkforceState.PAUSED
        workforce._pause_event.clear()
        assert not loop.is_closed() and not loop.is_running()

        call_off_thread(workforce.reset)

        assert workforce._pause_event.is_set(), (
            "reset() must release the pause, otherwise the next task waits "
            "on an event nobody sets"
        )
        assert workforce._state == WorkforceState.IDLE
    finally:
        loop.close()


def test_reset_returns_when_called_on_its_own_loops_thread():
    r"""``reset()`` is reachable from the thread running ``self._loop``:
    ``process_task`` stores the caller's running loop
    (``self._loop = current_loop``) and ``handle_decompose_append_task`` calls
    ``reset()``. Waiting there for a coroutine that only this thread can
    advance wedges the loop permanently -- and takes every task on it along.
    """
    workforce = Workforce("reset-own-thread")
    loop = asyncio.new_event_loop()
    loop_running = threading.Event()

    def run_loop() -> None:
        asyncio.set_event_loop(loop)
        loop.call_soon(loop_running.set)
        loop.run_forever()

    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    assert loop_running.wait(5)

    try:
        workforce._loop = loop
        workforce._pause_event.clear()

        reset_done = threading.Event()

        def reset_on_the_loop() -> None:
            workforce.reset()
            reset_done.set()

        loop.call_soon_threadsafe(reset_on_the_loop)
        assert reset_done.wait(5), "reset() never returned on the loop thread"

        # Probed by scheduling onto the loop rather than by elapsed time: a
        # wedged loop still reports ``is_running()``, so only work that has to
        # go through it can tell the difference.
        probe = asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop)
        probe.result(timeout=5)
        assert workforce._pause_event.is_set()
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join(timeout=5)
        loop.close()


def test_reset_releases_the_pause_for_tasks_awaiting_on_another_loop():
    r"""The pause event is shared with child workforces and awaited from
    whichever loop is running the work, so setting it must actually wake those
    waiters -- which is the reason the old code routed it onto ``self._loop``
    in the first place.

    ``asyncio.Event.set()`` schedules the wake-ups on the loop each waiter is
    attached to, not on the loop of whoever calls it, so a plain synchronous
    call is enough.

    This one passes against the old code too: it guards the premise of the fix
    rather than the hang, since a direct ``set()`` would be worthless if the
    waiters did not wake.
    """
    workforce = Workforce("reset-wakes-waiters")
    workforce._pause_event.clear()
    resumed = threading.Event()

    async def wait_for_resume() -> None:
        await workforce._pause_event.wait()
        resumed.set()

    async def main() -> None:
        workforce._loop = asyncio.get_running_loop()
        waiter = asyncio.ensure_future(wait_for_resume())
        await asyncio.sleep(0)  # let the waiter reach the ``wait()``
        # ``reset()`` runs off the loop, which is the arrangement
        # ``process_task`` produces for a caller on another thread.
        await asyncio.to_thread(workforce.reset)
        await asyncio.wait_for(waiter, timeout=5)

    asyncio.run(main())
    assert resumed.is_set()


def test_reset_returns_when_no_loop_was_ever_created():
    r"""The pre-existing path: ``reset()`` before any task has run. Kept so the
    common case cannot regress while the loop-bearing paths are changed.
    """
    workforce = Workforce("reset-no-loop")
    workforce._pause_event.clear()
    assert workforce._loop is None

    call_off_thread(workforce.reset)

    assert workforce._pause_event.is_set()
    assert workforce._state == WorkforceState.IDLE


def test_reset_returns_when_the_stored_loop_is_closed():
    r"""``_process_task_with_intervention`` closes the loop on any non-paused
    exit, leaving ``self._loop`` pointing at a closed loop.
    """
    workforce = Workforce("reset-closed-loop")
    loop = asyncio.new_event_loop()
    loop.close()
    workforce._loop = loop
    workforce._pause_event.clear()

    call_off_thread(workforce.reset)

    assert workforce._pause_event.is_set()
    assert workforce._state == WorkforceState.IDLE
