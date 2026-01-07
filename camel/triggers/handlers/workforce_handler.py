# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
"""Workforce handler for processing trigger events."""

from typing import TYPE_CHECKING, Any, Callable, Optional

from camel.logger import get_logger
from camel.tasks.task import Task
from camel.triggers.base_trigger import TriggerEvent
from camel.triggers.handlers.trigger_event_handler import TriggerEventHandler

if TYPE_CHECKING:
    from camel.societies.workforce.workforce import Workforce

logger = get_logger(__name__)


class WorkforceHandler(TriggerEventHandler):
    """Handler that processes trigger events using a Workforce.

    This handler converts trigger events into Tasks and processes them
    through a Workforce for multi-agent collaboration.

    Args:
        workforce (Optional[Workforce]): Workforce instance for processing.
            If None, a default Workforce will be created.
            (default: :obj:`None`)
        default_task (Optional[Task]): Default task template to use.
            If provided, the task content will be updated with event info.
            (default: :obj:`None`)
        task_factory (Optional[Callable[[TriggerEvent], Task]]): Custom
            function to convert events to tasks. If provided, this takes
            precedence over default_task. (default: :obj:`None`)
        stop_after_task (bool): Whether to stop the workforce gracefully
            after processing each task. (default: :obj:`True`)
    """

    def __init__(
        self,
        workforce: Optional['Workforce'] = None,
        default_task: Optional[Task] = None,
        task_factory: Optional[Callable[[TriggerEvent], Task]] = None,
        stop_after_task: bool = True,
    ):
        self.default_task = default_task
        self.task_factory = task_factory
        self.stop_after_task = stop_after_task

        if workforce is None:
            from camel.societies.workforce.workforce import Workforce

            self.workforce = Workforce("Default Trigger Workforce")
            logger.info("Created default Workforce for trigger handling")
        else:
            self.workforce = workforce

    async def handle(self, event: TriggerEvent) -> Any:
        """Handle trigger event by processing with Workforce.

        Args:
            event (TriggerEvent): The trigger event to process.

        Returns:
            Any: The result from Workforce task processing.
        """
        # Use custom task factory if provided
        if self.task_factory:
            task = self.task_factory(event)
        elif self.default_task:
            task = self.default_task
            # Update task content with event information
            if event.payload is not None:
                task.content = (
                    f"Process trigger event from {event.trigger_id}\n"
                    f"Payload: {event.payload}"
                )
            else:
                logger.error(
                    "Event payload is None; cannot update default task content"
                )
        else:
            task = self._event_to_task(event)

        # Process through workforce
        result = await self.workforce.process_task_async(task)

        if self.stop_after_task:
            self.workforce.stop_gracefully()

        return result

    def _event_to_task(self, event: TriggerEvent) -> Task:
        """Convert trigger event to Task.

        Args:
            event (TriggerEvent): The trigger event to convert.

        Returns:
            Task: A Task object representing the event.
        """
        task_content = f"Process trigger event from {event.trigger_id}"

        # Use payload to enhance task content
        if "task_content" in event.payload:
            task_content = event.payload["task_content"]
        elif "message" in event.payload:
            task_content = f"Process: {event.payload['message']}"

        return Task(
            content=task_content,
            id=f"trigger_{event.trigger_id}_{event.timestamp.isoformat()}",
            additional_info={
                "trigger_event": event.dict(),
                "source": "trigger_system",
            },
        )

    def set_default_task(self, task: Task) -> None:
        """Set or update the default task template.

        Args:
            task (Task): The task template to use.
        """
        self.default_task = task
        logger.info(f"Updated default task: {task.id}")
