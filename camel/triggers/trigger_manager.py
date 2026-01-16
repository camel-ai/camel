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
import json
from collections import deque
from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.triggers.adapters.database_adapter import DatabaseAdapter
from camel.triggers.base_trigger import BaseTrigger, TriggerEvent
from camel.triggers.handlers import TriggerEventHandler

logger = get_logger(__name__)


class TriggerManager:
    """Central manager for all triggers with unified handler abstraction.

    The TriggerManager coordinates trigger registration, activation, and
    event processing through a pluggable handler interface. This design
    allows users to easily customize event processing logic.

    Args:
        handler (Optional[TriggerEventHandler]): The handler instance
            responsible for processing trigger events. If None, events
            will be logged but not processed. Users can provide custom
            handlers or use built-in ones like WorkforceHandler or
            ChatAgentHandler. (default: :obj:`None`)
        database_adapter (Optional[DatabaseAdapter]): Database adapter for
            persisting trigger execution records and event logs.
            (default: :obj:`None`)
        allow_duplicate_events (bool): Whether to allow processing of
            duplicate events. If False, events with the same correlation
            ID or payload hash will be skipped. (default: :obj:`False`)
    """

    def __init__(
        self,
        handler: Optional[TriggerEventHandler] = None,
        database_adapter: Optional[DatabaseAdapter] = None,
        allow_duplicate_events: bool = False,
    ):
        self.handler = handler
        self.database_adapter = database_adapter
        self.triggers: Dict[str, BaseTrigger] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self.allow_duplicate_events = allow_duplicate_events
        self.processed_events: deque = deque(maxlen=1000)

        if self.handler is None:
            logger.warning(
                "No handler configured - triggers will be registered but "
                "events will not be automatically processed"
            )

    async def register_trigger(
        self, trigger: BaseTrigger, auto_activate: bool = True
    ) -> bool:
        """Register and optionally activate a trigger.

        Args:
            trigger (BaseTrigger): The trigger to register.
            auto_activate (bool): Whether to activate the trigger
                immediately after registration. (default: :obj:`True`)

        Returns:
            bool: True if registration (and activation if requested)
                was successful.
        """
        # Add callback to handle trigger events if handler is configured
        if self.handler is not None:
            trigger.add_callback(self._handle_trigger_event)
            logger.info(
                f"Registered trigger {trigger.trigger_id} with handler "
                f"{self.handler.__class__.__name__}"
            )
        else:
            logger.info(
                f"Registered trigger {trigger.trigger_id} without handler - "
                "events will not be auto-processed"
            )

        self.triggers[trigger.trigger_id] = trigger

        if auto_activate:
            return await trigger.activate()
        return True

    async def _handle_trigger_event(self, event: TriggerEvent) -> None:
        """Handle trigger event by delegating to the configured handler.

        Args:
            event (TriggerEvent): The trigger event to process.
        """
        # Deduplication logic (skip if allow_duplicate_events is enabled)
        if not self.allow_duplicate_events:
            event_id = self._get_event_id(event)

            if event_id in self.processed_events:
                logger.info(f"Duplicate event {event_id} ignored")
                return

            self.processed_events.append(event_id)

        if self.handler is None:
            logger.warning(
                f"Trigger event from {event.trigger_id} received but "
                "no handler configured - event not processed"
            )
            return

        try:
            result = await self.handler.handle(event)

            # Save execution record
            if self.database_adapter:
                await self.database_adapter.save_execution_record(
                    {
                        "trigger_id": event.trigger_id,
                        "task_id": getattr(result, 'id', None)
                        if hasattr(result, 'id')
                        else f"trigger_{event.trigger_id}_"
                        f"{event.timestamp.isoformat()}",
                        "timestamp": event.timestamp,
                        "payload": event.payload,
                        "status": "processed",
                        "result": str(result) if result else None,
                        "handler_type": self.handler.__class__.__name__,
                    }
                )

            # Log execution
            self.execution_log.append(
                {
                    "trigger_id": event.trigger_id,
                    "timestamp": event.timestamp,
                    "status": "processed",
                    "handler": self.handler.__class__.__name__,
                }
            )

        except Exception as e:
            logger.error(f"Error handling trigger event: {e}")
            self.execution_log.append(
                {
                    "trigger_id": event.trigger_id,
                    "timestamp": event.timestamp,
                    "status": "error",
                    "error": str(e),
                    "handler": self.handler.__class__.__name__
                    if self.handler
                    else None,
                }
            )

    def _get_event_id(self, event: TriggerEvent) -> str:
        """Generate a unique identifier for an event for deduplication.

        Args:
            event (TriggerEvent): The trigger event.

        Returns:
            str: A unique identifier for the event.
        """
        event_id = event.correlation_id
        if not event_id and isinstance(event.payload, dict):
            # Try to find unique ID in payload (e.g. Slack)
            event_id = event.payload.get("event_id") or event.payload.get("id")

        if not event_id:
            # Create a deterministic hash of the payload
            try:
                payload_str = json.dumps(event.payload, sort_keys=True)
                event_id = f"{event.trigger_id}:{payload_str}"
            except (TypeError, ValueError):
                # Fallback for non-serializable payloads
                event_id = f"{event.trigger_id}:{event.payload!s}"

        return event_id

    def set_handler(self, handler: TriggerEventHandler) -> None:
        """Set or update the event handler.

        This allows changing the handler at runtime. Note that this only
        affects future events - already registered trigger callbacks
        will still use the internal handler method.

        Args:
            handler (TriggerEventHandler): The new handler to use.
        """
        self.handler = handler
        logger.info(f"Updated handler to {handler.__class__.__name__}")

    async def deactivate_all_triggers(self) -> None:
        """Deactivate all registered triggers."""
        for trigger in self.triggers.values():
            await trigger.deactivate()

    def get_trigger_status(self) -> Dict[str, Any]:
        """Get status of all triggers.

        Returns:
            Dict[str, Any]: Status information for each registered trigger.
        """
        return {
            trigger_id: {
                "state": trigger.state.value,
                "type": trigger.__class__.__name__,
                "description": trigger.description,
            }
            for trigger_id, trigger in self.triggers.items()
        }

    def get_execution_log(
        self, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get the execution log.

        Args:
            limit (Optional[int]): Maximum number of entries to return.
                If None, returns all entries. (default: :obj:`None`)

        Returns:
            List[Dict[str, Any]]: List of execution log entries.
        """
        if limit is not None:
            return self.execution_log[-limit:]
        return self.execution_log
