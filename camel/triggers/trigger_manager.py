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
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task
from camel.triggers.adapters.database_adapter import DatabaseAdapter
from camel.triggers.base_trigger import BaseTrigger, TriggerEvent

logger = get_logger(__name__)


class TriggerManager:
    """Central manager for all triggers - integrates with Workforce"""

    def __init__(
        self,
        workforce: Optional[Workforce] = None,
        database_adapter: Optional[DatabaseAdapter] = None,
    ):
        self.workforce = workforce
        self.database_adapter = database_adapter
        self.triggers: Dict[str, BaseTrigger] = {}
        self.execution_log: List[Dict[str, Any]] = []

    async def register_trigger(
        self, trigger: BaseTrigger, auto_activate: bool = True
    ) -> bool:
        """Register and optionally activate a trigger"""

        # Add callback to handle trigger events
        if self.workforce:
            trigger.task_channel = self.workforce._channel
            trigger.workforce = self.workforce
            trigger.add_callback(self._handle_trigger_event)
        else:
            logger.warning(
                "No workforce associated with TriggerManager; triggers will not create tasks."
            )

        self.triggers[trigger.trigger_id] = trigger

        if auto_activate:
            return await trigger.activate()
        return True

    async def _handle_trigger_event(self, event: TriggerEvent):
        """Handle trigger event by creating and submitting tasks"""
        try:
            # Convert trigger event to Task
            task = self._event_to_task(event)

            # Submit to workforce
            if self.workforce:
                # Process through normal workforce flow
                await self.workforce.process_task_async(task)
                self.workforce.stop_gracefully()

            # Save execution record
            if self.database_adapter:
                await self.database_adapter.save_execution_record(
                    {
                        "trigger_id": event.trigger_id,
                        "task_id": task.id,
                        "timestamp": event.timestamp,
                        "payload": event.payload,
                        "status": "submitted",
                    }
                )

        except Exception as e:
            logger.error(f"Error handling trigger event: {e}")

    def _event_to_task(self, event: TriggerEvent) -> Task:
        """Convert trigger event to Task"""
        # This could be configurable per trigger
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

    async def deactivate_all_triggers(self):
        """Deactivate all registered triggers"""
        for trigger in self.triggers.values():
            await trigger.deactivate()

    def get_trigger_status(self) -> Dict[str, Any]:
        """Get status of all triggers"""
        return {
            trigger_id: {
                "state": trigger.state.value,
                "type": trigger.__class__.__name__,
                "description": trigger.description,
            }
            for trigger_id, trigger in self.triggers.items()
        }
