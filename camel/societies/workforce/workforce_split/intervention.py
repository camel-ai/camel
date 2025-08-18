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
    r"""Class to handle workforce pause, resume, and stop operations."""

    def __init__(self):
        r"""Initialize the WorkforceIntervention class."""
        pass

    async def async_pause(
        self,
        pause_event,
        node_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Async implementation of pause to run on the event loop.

        Args:
            pause_event (asyncio.Event): The pause event to control.
            node_id (str): The node identifier.
            loop (asyncio.AbstractEventLoop, optional): The event loop to use.
                (default: :obj:`None`)
        """
        # Clear the pause event to pause execution
        pause_event.clear()
        logger.info(f"Workforce {node_id} paused.")

    def pause(
        self,
        pause_event,
        node_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        submit_coro_to_loop_func=None,
    ) -> None:
        r"""Pause the workforce execution.
        If the internal event-loop is already running we schedule the
        asynchronous pause coroutine onto it.  When the loop has not yet
        been created (e.g. the caller presses the hot-key immediately after
        workforce start-up) we fall back to a synchronous state change so
        that no tasks will be scheduled until the loop is ready.

        Args:
            pause_event (asyncio.Event): The pause event to control.
            node_id (str): The node identifier.
            loop (asyncio.AbstractEventLoop, optional): The event loop to use.
                (default: :obj:`None`)
            submit_coro_to_loop_func (Callable, optional): Function to submit
                coroutines to the event loop. (default: :obj:`None`)
        """

        if loop and not loop.is_closed() and submit_coro_to_loop_func:
            # Use _submit_coro_to_loop like the original implementation
            submit_coro_to_loop_func(
                self.async_pause(pause_event, node_id, loop)
            )
        else:
            # Loop not yet created, just clear the pause event so when loop
            # starts it will proceed in paused state.
            pause_event.clear()
            logger.info(
                f"Workforce {node_id} paused " f"(event-loop not yet started)."
            )

    async def async_resume(
        self,
        pause_event,
        node_id: str,
        pending_tasks=None,
        post_ready_tasks_func=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        r"""Async implementation of resume to run on the event loop.

        Args:
            pause_event (asyncio.Event): The pause event to control.
            node_id (str): The node identifier.
            pending_tasks (Any, optional): The pending tasks to process.
                (default: :obj:`None`)
            post_ready_tasks_func (Callable, optional): Function to post ready
                tasks. (default: :obj:`None`)
            loop (asyncio.AbstractEventLoop, optional): The event loop to use.
                (default: :obj:`None`)
        """
        # Set the pause event to resume execution
        pause_event.set()
        logger.info(f"Workforce {node_id} resumed.")

        # Re-post ready tasks (if any)
        if pending_tasks and post_ready_tasks_func:
            await post_ready_tasks_func()

    def resume(
        self,
        pause_event,
        node_id: str,
        pending_tasks=None,
        post_ready_tasks_func=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        submit_coro_to_loop_func=None,
    ) -> None:
        r"""Resume execution after a manual pause.

        Args:
            pause_event (asyncio.Event): The pause event to control.
            node_id (str): The node identifier.
            pending_tasks (Any, optional): The pending tasks to process.
                (default: :obj:`None`)
            post_ready_tasks_func (Callable, optional): Function to post ready
                tasks. (default: :obj:`None`)
            loop (asyncio.AbstractEventLoop, optional): The event loop to use.
                (default: :obj:`None`)
            submit_coro_to_loop_func (Callable, optional): Function to submit
                coroutines to the event loop. (default: :obj:`None`)
        """
        if loop and not loop.is_closed() and submit_coro_to_loop_func:
            # Use _submit_coro_to_loop like the original implementation
            submit_coro_to_loop_func(
                self.async_resume(
                    pause_event,
                    node_id,
                    pending_tasks,
                    post_ready_tasks_func,
                    loop,
                )
            )
        else:
            # Loop not running yet, just set the pause event so when loop
            # starts it will proceed in running state.
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

        Args:
            pause_event (asyncio.Event): The pause event to control.
            node_id (str): The node identifier.
            loop (asyncio.AbstractEventLoop, optional): The event loop to use.
                (default: :obj:`None`)
        """
        if pause_event.is_set() is False:
            pause_event.set()  # Resume if paused to process stop
        logger.info(f"Workforce {node_id} stop requested.")

    def stop_gracefully(
        self,
        pause_event,
        node_id: str,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        submit_coro_to_loop_func=None,
    ) -> None:
        r"""Request workforce to finish current in-flight work then halt.

        Works both when the internal event-loop is alive and when it has not
        yet been started.  In the latter case we simply mark the stop flag so
        that the loop (when it eventually starts) will exit immediately after
        initialisation.

        Args:
            pause_event (asyncio.Event): The pause event to control.
            node_id (str): The node identifier.
            loop (asyncio.AbstractEventLoop, optional): The event loop to use.
                (default: :obj:`None`)
            submit_coro_to_loop_func (Callable, optional): Function to submit
                coroutines to the event loop. (default: :obj:`None`)
        """

        if loop and not loop.is_closed() and submit_coro_to_loop_func:
            # Use _submit_coro_to_loop like the original implementation
            submit_coro_to_loop_func(
                self.async_stop_gracefully(pause_event, node_id, loop)
            )
        else:
            # Loop not yet created, ensure any pending pause is released so
            # that when the loop does start it can see the stop request and
            # exit.
            pause_event.set()
            logger.info(
                f"Workforce {node_id} stop requested "
                f"(event-loop not yet started)."
            )
