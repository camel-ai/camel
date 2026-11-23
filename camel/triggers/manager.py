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
r"""The :class:`TriggerManager` ties the framework together.

It owns the store, instantiates concrete triggers from specs, runs each as an
asyncio task on the host event loop, and routes fired
:class:`~camel.triggers.models.TriggerEvent` objects to a delivery callback
(the *sink*). It also exposes synchronous CRUD methods used by the toolkit.

Design note: the manager is runtime-agnostic. It never imports ``Workforce``
or ``ChatAgent`` — the host passes an ``emit`` coroutine that knows how to
inject events into that runtime. This is what lets one framework serve many
runtimes (see ``camel/societies/workforce/workforce.py`` for the Workforce
wiring).
"""

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Optional

from camel.logger import get_logger

from .base import (
    BaseTrigger,
    get_trigger_class,
)
from .models import TriggerEvent, TriggerSpec, TriggerState
from .store import BaseTriggerStore, InMemoryTriggerStore
from .webhook_server import WebhookServer
from .webhook_trigger import WebhookTrigger

logger = get_logger(__name__)

EmitCallback = Callable[[TriggerEvent], Awaitable[None]]


class TriggerManager:
    r"""Runs trigger sources and routes their events to a sink.

    Args:
        store (Optional[BaseTriggerStore]): Persistence backend. Defaults to an
            in-memory store.
        emit (Optional[EmitCallback]): Coroutine called with each fired event.
            If ``None``, events are dropped with a warning (CRUD-only mode).
        webhook_host (str): Host for the shared webhook server.
        webhook_port (int): Port for the shared webhook server.
        dedupe_window (int): Number of recent idempotency keys remembered to
            suppress duplicate fires (e.g. coalesced misfires).
    """

    def __init__(
        self,
        store: Optional[BaseTriggerStore] = None,
        emit: Optional[EmitCallback] = None,
        webhook_host: str = "127.0.0.1",
        webhook_port: int = 8080,
        dedupe_window: int = 256,
    ) -> None:
        self.store = store or InMemoryTriggerStore()
        self._emit = emit
        self._triggers: Dict[str, BaseTrigger] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._running = False
        self._webhook_server = WebhookServer(webhook_host, webhook_port)
        self._dedupe_window = dedupe_window
        self._recent_keys: List[str] = []
        self._seen_keys: set = set()

    # -- lifecycle ----------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def has_active_triggers(self) -> bool:
        r"""Whether any trigger is currently ACTIVE.

        The host loop (e.g. Workforce) consults this to decide whether to stay
        alive while idle.
        """
        return any(s.state == TriggerState.ACTIVE for s in self.store.list())

    async def start(self) -> None:
        r"""Load persisted triggers and launch their source tasks."""
        if self._running:
            return
        self._loop = asyncio.get_running_loop()
        self._running = True
        for spec in self.store.list():
            if spec.state == TriggerState.ACTIVE:
                await self._launch(spec)
        logger.info(
            f"TriggerManager started with {len(self._tasks)} "
            f"active trigger(s)."
        )

    async def stop(self) -> None:
        r"""Cancel all source tasks and stop the webhook server."""
        self._running = False
        for task in self._tasks.values():
            task.cancel()
        for task in list(self._tasks.values()):
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.warning(f"Trigger task error during stop: {e}")
        self._tasks.clear()
        self._triggers.clear()
        if self._webhook_server.is_running:
            await self._webhook_server.stop()

    # -- event routing ------------------------------------------------------

    async def _on_fire(self, spec_id: str, event: TriggerEvent) -> None:
        r"""Internal emit wrapper: dedupe, persist counters, forward to
        sink."""
        if event.idempotency_key in self._seen_keys:
            logger.debug(f"Duplicate fire suppressed: {event.idempotency_key}")
            return
        self._remember_key(event.idempotency_key)

        # Update persisted counters / exhaustion state.
        spec = self.store.get(spec_id)
        if spec is not None:
            spec.run_count = event.run_count
            spec.last_run = event.fired_at
            if self._spec_exhausted(spec):
                spec.state = TriggerState.EXHAUSTED
            self.store.update(spec)
            # Keep the live trigger's spec in sync so it stops itself.
            if spec_id in self._triggers:
                self._triggers[spec_id].spec = spec

        if self._emit is None:
            logger.warning(
                f"Trigger '{event.trigger_name}' fired but no sink is "
                f"configured; event dropped."
            )
            return
        await self._emit(event)

    @staticmethod
    def _spec_exhausted(spec: TriggerSpec) -> bool:
        from datetime import datetime, timezone

        if spec.max_runs is not None and spec.run_count >= spec.max_runs:
            return True
        if spec.until is not None and datetime.now(timezone.utc) >= spec.until:
            return True
        return False

    def _remember_key(self, key: str) -> None:
        self._recent_keys.append(key)
        self._seen_keys.add(key)
        if len(self._recent_keys) > self._dedupe_window:
            old = self._recent_keys.pop(0)
            self._seen_keys.discard(old)

    async def _launch(self, spec: TriggerSpec) -> None:
        r"""Instantiate and start the source task for a spec."""
        cls = get_trigger_class(spec.type)
        trigger = cls(spec)
        self._triggers[spec.id] = trigger

        if isinstance(trigger, WebhookTrigger):
            await self._webhook_server.start()
            self._webhook_server.register(trigger)

        async def emit(event: TriggerEvent, _id: str = spec.id) -> None:
            await self._on_fire(_id, event)

        self._tasks[spec.id] = asyncio.create_task(
            self._supervise(trigger, emit)
        )

    async def _supervise(self, trigger: BaseTrigger, emit: EmitCallback):
        r"""Run a trigger's source, logging unexpected failures."""
        try:
            await trigger.run(emit)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(
                f"Trigger '{trigger.spec.name}' ({trigger.spec.id}) crashed: "
                f"{e}",
                exc_info=True,
            )

    async def _teardown(self, spec_id: str) -> None:
        r"""Cancel and clean up a single trigger's task."""
        task = self._tasks.pop(spec_id, None)
        trigger = self._triggers.pop(spec_id, None)
        if isinstance(trigger, WebhookTrigger):
            self._webhook_server.unregister(trigger)
        if task is not None:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass

    # -- CRUD (sync-facing; safe to call from the toolkit) ------------------

    def create(
        self,
        name: str,
        type: str,
        payload: str,
        config: Dict[str, Any],
        max_runs: Optional[int] = None,
        until: Optional[str] = None,
    ) -> TriggerSpec:
        r"""Validate and persist a new trigger, launching it if running."""
        cls = get_trigger_class(type)
        norm_config = cls.validate_config(config)
        from datetime import datetime, timezone

        until_dt = None
        if until is not None:
            until_dt = datetime.fromisoformat(until)
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)

        spec = TriggerSpec(
            name=name,
            type=type,
            payload=payload,
            config=norm_config,
            max_runs=max_runs,
            until=until_dt,
        )
        self.store.add(spec)
        self._schedule_launch(spec)
        return spec

    def get(self, trigger_id: str) -> Optional[TriggerSpec]:
        return self.store.get(trigger_id)

    def list(self, active_only: bool = False) -> List[TriggerSpec]:
        specs = self.store.list()
        if active_only:
            specs = [s for s in specs if s.state == TriggerState.ACTIVE]
        return specs

    def update(self, trigger_id: str, **fields: Any) -> Optional[TriggerSpec]:
        r"""Update mutable fields of a trigger and relaunch it."""
        spec = self.store.get(trigger_id)
        if spec is None:
            return None
        allowed = {"name", "payload", "config", "max_runs", "until"}
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"Field '{key}' is not updatable.")
            if key == "config":
                cls = get_trigger_class(spec.type)
                value = cls.validate_config(value)
            setattr(spec, key, value)
        self.store.update(spec)
        self._schedule_relaunch(spec)
        return spec

    def set_state(
        self, trigger_id: str, state: TriggerState
    ) -> Optional[TriggerSpec]:
        spec = self.store.get(trigger_id)
        if spec is None:
            return None
        spec.state = state
        self.store.update(spec)
        if state == TriggerState.ACTIVE:
            self._schedule_relaunch(spec)
        else:
            self._schedule_teardown(trigger_id)
        return spec

    def delete(self, trigger_id: str) -> bool:
        existed = self.store.delete(trigger_id)
        if existed:
            self._schedule_teardown(trigger_id)
        return existed

    # -- async-bridging helpers --------------------------------------------
    # CRUD is called from the toolkit (possibly off-loop). When the manager is
    # running we schedule launch/teardown on its loop; otherwise it's a no-op
    # until start().

    def _schedule_launch(self, spec: TriggerSpec) -> None:
        if not self._running or self._loop is None:
            return
        if spec.state != TriggerState.ACTIVE:
            return
        asyncio.run_coroutine_threadsafe(self._launch(spec), self._loop)

    def _schedule_relaunch(self, spec: TriggerSpec) -> None:
        if not self._running or self._loop is None:
            return

        async def _relaunch():
            await self._teardown(spec.id)
            if spec.state == TriggerState.ACTIVE:
                await self._launch(spec)

        asyncio.run_coroutine_threadsafe(_relaunch(), self._loop)

    def _schedule_teardown(self, trigger_id: str) -> None:
        if not self._running or self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(
            self._teardown(trigger_id), self._loop
        )
