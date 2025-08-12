# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import asyncio
from typing import Optional

from camel.logger import get_logger

logger = get_logger(__name__)


class WorkforceIntervention:
    """Class to handle workforce pause, resume, and stop operations."""

    def __init__(self):
        """Initialize the WorkforceIntervention class."""
        pass

    async def async_pause(
        self,
        workforce_state,
        pause_event,
        node_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Async implementation of pause to run on the event loop."""
        if workforce_state == "running":
            # Update state to paused
            workforce_state = "paused"
            pause_event.clear()
            logger.info(f"Workforce {node_id} paused.")

    def pause(
        self,
        workforce_state,
        pause_event,
        node_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Pause the workforce execution.
        If the internal event-loop is already running we schedule the
        asynchronous pause coroutine onto it.  When the loop has not yet
        been created (e.g. the caller presses the hot-key immediately after
        workforce start-up) we fall back to a synchronous state change so
        that no tasks will be scheduled until the loop is ready.
        """

        if loop and not loop.is_closed():
            # Submit coroutine to loop
            if loop.is_running():
                loop.create_task(
                    self.async_pause(
                        workforce_state, pause_event, node_id, loop
                    )
                )
            else:
                asyncio.run_coroutine_threadsafe(
                    self.async_pause(
                        workforce_state, pause_event, node_id, loop
                    ),
                    loop,
                )
        else:
            # Loop not yet created, just mark state so when loop starts it
            # will proceed.
            if workforce_state == "running":
                workforce_state = "paused"
                pause_event.clear()
                logger.info(
                    f"Workforce {node_id} paused "
                    f"(event-loop not yet started)."
                )

    async def async_resume(
        self,
        workforce_state,
        pause_event,
        node_id: str,
        pending_tasks=None,
        post_ready_tasks_func=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Async implementation of resume to run on the event loop."""
        if workforce_state == "paused":
            workforce_state = "running"
            pause_event.set()
            logger.info(f"Workforce {node_id} resumed.")

            # Re-post ready tasks (if any)
            if pending_tasks and post_ready_tasks_func:
                await post_ready_tasks_func()

    def resume(
        self,
        workforce_state,
        pause_event,
        node_id: str,
        pending_tasks=None,
        post_ready_tasks_func=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Resume execution after a manual pause."""

        if loop and not loop.is_closed():
            # Submit coroutine to loop
            if loop.is_running():
                loop.create_task(
                    self.async_resume(
                        workforce_state,
                        pause_event,
                        node_id,
                        pending_tasks,
                        post_ready_tasks_func,
                        loop,
                    )
                )
            else:
                asyncio.run_coroutine_threadsafe(
                    self.async_resume(
                        workforce_state,
                        pause_event,
                        node_id,
                        pending_tasks,
                        post_ready_tasks_func,
                        loop,
                    ),
                    loop,
                )
        else:
            # Loop not running yet, just mark state so when loop starts it
            # will proceed.
            if workforce_state == "paused":
                workforce_state = "running"
                pause_event.set()
                logger.info(
                    f"Workforce {node_id} resumed "
                    f"(event-loop not yet started)."
                )

    async def async_stop_gracefully(
        self,
        pause_event,
        node_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Async implementation of stop_gracefully to run on the event
        loop.
        """
        if pause_event.is_set() is False:
            pause_event.set()  # Resume if paused to process stop
        logger.info(f"Workforce {node_id} stop requested.")

    def stop_gracefully(
        self,
        pause_event,
        node_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Request workforce to finish current in-flight work then halt.

        Works both when the internal event-loop is alive and when it has not
        yet been started.  In the latter case we simply mark the stop flag so
        that the loop (when it eventually starts) will exit immediately after
        initialisation.
        """

        if loop and not loop.is_closed():
            # Submit coroutine to loop
            if loop.is_running():
                loop.create_task(
                    self.async_stop_gracefully(pause_event, node_id, loop)
                )
            else:
                asyncio.run_coroutine_threadsafe(
                    self.async_stop_gracefully(pause_event, node_id, loop),
                    loop,
                )
        else:
            # Loop not yet created, set the flag synchronously so later
            # startup will respect it.
            # Ensure any pending pause is released so that when the loop does
            # start it can see the stop request and exit.
            pause_event.set()
            logger.info(
                f"Workforce {node_id} stop requested "
                f"(event-loop not yet started)."
            )
