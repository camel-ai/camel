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
from enum import Enum
from typing import Any, Dict, List, Optional

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task
from camel.triggers.adapters.database_adapter import DatabaseAdapter
from camel.triggers.base_trigger import BaseTrigger, TriggerEvent
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


class CallbackHandlerType(Enum):
    """Enum defining types of callback handlers for trigger events"""

    WORKFORCE = "workforce"
    CHAT_AGENT = "chat_agent"
    NONE = "none"


class TriggerManager:
    """Central manager for all triggers - integrates with Workforce or
    ChatAgent

    Args:
        handler_type (Optional[CallbackHandlerType]): Type of callback
            handler to use for processing trigger events. Can be
            WORKFORCE, CHAT_AGENT, or NONE. (default: :obj:`NONE`)
        workforce (Optional[Workforce]): Workforce instance for processing
            trigger events when handler_type is WORKFORCE. If None and
            handler_type is WORKFORCE, a default Workforce will be
            created. (default: :obj:`None`)
        chat_agent (Optional[ChatAgent]): ChatAgent instance for
            processing trigger events when handler_type is CHAT_AGENT. If
            None and handler_type is CHAT_AGENT, a default ChatAgent will
            be created. (default: :obj:`None`)
        database_adapter (Optional[DatabaseAdapter]): Database adapter for
            persisting trigger execution records and event logs.
            (default: :obj:`None`)
        default_task (Optional[Task]): Default task template to use when
            processing trigger events with Workforce. If provided, the
            task content will be updated with event information.
            (default: :obj:`None`)
        default_prompt (Optional[str]): Default prompt template to use
            when processing trigger events with ChatAgent. The prompt will
            be combined with event payload information.
            (default: :obj:`None`)
        allow_duplicate_events (bool): Whether to allow processing of
            duplicate events. If False, events with the same correlation
            ID or payload hash will be skipped. (default: :obj:`False`)
    """

    def __init__(
        self,
        handler_type: Optional[CallbackHandlerType] = CallbackHandlerType.NONE,
        workforce: Optional[Workforce] = None,
        chat_agent: Optional[ChatAgent] = None,
        database_adapter: Optional[DatabaseAdapter] = None,
        default_task: Optional[Task] = None,
        default_prompt: Optional[str] = None,
        allow_duplicate_events: bool = False,
    ):
        self.handler_type = handler_type
        self.workforce = workforce
        self.chat_agent = chat_agent
        self.database_adapter = database_adapter
        self.default_task = default_task
        self.default_prompt = default_prompt
        self.triggers: Dict[str, BaseTrigger] = {}
        self.execution_log: List[Dict[str, Any]] = []
        self.allow_duplicate_events = allow_duplicate_events
        self.processed_events: deque = deque(maxlen=1000)

        # Validate handler configuration
        self._validate_handler_configuration()

        # Initialize default handler if none provided
        self._initialize_default_handler()

    def _validate_handler_configuration(self):
        """Validate that the handler configuration is correct"""
        if self.handler_type == CallbackHandlerType.NONE:
            if self.workforce is not None:
                raise ValueError(
                    "Handler type is NONE but workforce instance was "
                    "provided. Either set handler_type to WORKFORCE or "
                    "remove workforce parameter."
                )
            if self.chat_agent is not None:
                raise ValueError(
                    "Handler type is NONE but chat_agent instance was "
                    "provided. Either set handler_type to CHAT_AGENT or "
                    "remove chat_agent parameter."
                )

    def _initialize_default_handler(self):
        """Initialize default handler if none provided"""
        if self.handler_type == CallbackHandlerType.WORKFORCE:
            if self.workforce is None:
                # Create default workforce with basic configuration
                self.workforce = Workforce("Default Trigger Workforce")
                logger.info("Created default Workforce for trigger handling")
        elif self.handler_type == CallbackHandlerType.CHAT_AGENT:
            if self.chat_agent is None:
                # Create default ChatAgent with basic configuration
                model = ModelFactory.create(
                    model_platform=ModelPlatformType.DEFAULT,
                    model_type=ModelType.DEFAULT,
                )
                self.chat_agent = ChatAgent(
                    system_message=(
                        "You are a helpful assistant that processes trigger "
                        "events and tasks."
                    ),
                    model=model,
                )
                logger.info("Created default ChatAgent for trigger handling")
        elif self.handler_type == CallbackHandlerType.NONE:
            logger.warning(
                "No handler configured - triggers will call provided callbacks"
            )

    async def register_trigger(
        self, trigger: BaseTrigger, auto_activate: bool = True
    ) -> bool:
        """Register and optionally activate a trigger"""

        # Add callback to handle trigger events
        if (
            self.handler_type == CallbackHandlerType.WORKFORCE
            and self.workforce
        ):
            trigger.workforce = self.workforce
            trigger.add_callback(self._handle_trigger_event)
        elif (
            self.handler_type == CallbackHandlerType.CHAT_AGENT
            and self.chat_agent
        ):
            trigger.add_callback(self._handle_trigger_event)
        elif self.handler_type == CallbackHandlerType.NONE:
            logger.info(
                f"Handler type is NONE - trigger {trigger.trigger_id} "
                "registered but will not auto-process events"
            )
        else:
            logger.warning(
                f"No {self.handler_type.value} handler available; "
                "triggers will not process events."
            )

        self.triggers[trigger.trigger_id] = trigger

        if auto_activate:
            return await trigger.activate()
        return True

    async def _handle_trigger_event(self, event: TriggerEvent):
        """Handle trigger event by processing with configured handler"""
        # Deduplication logic (skip if allow_duplicate_events is enabled)
        if not self.allow_duplicate_events:
            event_id = event.correlation_id
            if not event_id and isinstance(event.payload, dict):
                # Try to find unique ID in payload (e.g. Slack)
                event_id = event.payload.get("event_id") or event.payload.get(
                    "id"
                )

            if not event_id:
                # Create a deterministic hash of the payload
                try:
                    payload_str = json.dumps(event.payload, sort_keys=True)
                    event_id = f"{event.trigger_id}:{payload_str}"
                except (TypeError, ValueError):
                    # Fallback for non-serializable payloads
                    event_id = f"{event.trigger_id}:{event.payload!s}"

            if event_id in self.processed_events:
                logger.info(f"Duplicate event {event_id} ignored")
                return

            self.processed_events.append(event_id)

        if self.handler_type == CallbackHandlerType.NONE:
            logger.warning(
                f"Trigger event from {event.trigger_id} received but "
                "handler type is NONE - no processing performed"
            )
            return

        try:
            result = None

            if (
                self.handler_type == CallbackHandlerType.WORKFORCE
                and self.workforce
            ):
                # Use provided task or convert event to Task
                if self.default_task:
                    task = self.default_task
                    # Update task content with event information
                    if event.payload is not None:
                        task.content = (
                            f"Process trigger event from {event.trigger_id}\n"
                            f"Payload: {event.payload}"
                        )
                    else:
                        logger.error(
                            "Event payload is None; cannot update default "
                            "task content."
                        )
                else:
                    task = self._event_to_task(event)

                # Process through workforce
                result = await self.workforce.process_task_async(task)
                self.workforce.stop_gracefully()

            elif (
                self.handler_type == CallbackHandlerType.CHAT_AGENT
                and self.chat_agent
            ):
                # Combine default prompt with event payload
                if self.default_prompt:
                    prompt = (
                        f"{self.default_prompt}\n\n"
                        f"Trigger ID: {event.trigger_id}\n"
                        f"Event Payload: {event.payload}"
                    )
                else:
                    prompt = (
                        f"Process trigger event from {event.trigger_id}\n"
                        f"Payload: {event.payload}"
                    )

                # Process with ChatAgent
                response = await self.chat_agent.astep(prompt)
                result = response.msg.content

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
                        "handler_type": self.handler_type.value,
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

    def set_default_task(self, task: Task):
        """Set or update the default task for Workforce processing"""
        self.default_task = task
        logger.info(f"Updated default task: {task.id}")

    def set_default_prompt(self, prompt: str):
        """Set or update the default prompt for ChatAgent processing"""
        self.default_prompt = prompt
        logger.info("Updated default prompt for ChatAgent processing")

    def get_handler_info(self) -> Dict[str, Any]:
        """Get information about the current handler configuration"""
        return {
            "handler_type": self.handler_type.value,
            "workforce_available": self.workforce is not None,
            "chat_agent_available": self.chat_agent is not None,
            "has_default_task": self.default_task is not None,
            "has_default_prompt": self.default_prompt is not None,
            "database_adapter": self.database_adapter is not None,
        }

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
