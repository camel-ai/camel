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
from datetime import datetime
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task
from camel.triggers.base_trigger import (
    BaseTrigger,
    TriggerEvent,
    TriggerState,
    TriggerType,
)
from camel.triggers.handlers import ChatAgentHandler, WorkforceHandler
from camel.triggers.trigger_manager import TriggerManager
from camel.types import ModelPlatformType, ModelType


class MockTrigger(BaseTrigger):
    """Mock trigger for testing purposes"""

    def __init__(
        self,
        trigger_id: str = "test_trigger",
        name: str = "Test Trigger",
        description: str = "A test trigger",
        config: Dict[str, Any] | None = None,
    ):
        super().__init__(
            trigger_id=trigger_id,
            name=name,
            description=description,
            config=config or {},
        )

    async def initialize(self) -> bool:
        return True

    async def activate(self) -> bool:
        self.state = TriggerState.ACTIVE
        return True

    async def deactivate(self) -> bool:
        self.state = TriggerState.INACTIVE
        return True

    async def test_connection(self) -> bool:
        return True

    def validate_config(self, config: Dict[str, Any]) -> bool:
        return True

    async def process_trigger_event(self, event_data: Any) -> TriggerEvent:
        return TriggerEvent(
            trigger_id=self.trigger_id,
            trigger_type=TriggerType.CUSTOM,
            timestamp=datetime.now(),
            payload=event_data,
        )

    async def emit_test_event(self, payload: Dict[str, Any]):
        """Helper method to emit test events"""
        event = await self.process_trigger_event(payload)
        await self._emit_trigger_event(event)


def test_trigger_manager_initialization_none_handler():
    """Test TriggerManager initialization with no handler"""
    manager = TriggerManager()

    assert manager.handler is None
    assert manager.database_adapter is None
    assert len(manager.triggers) == 0
    assert len(manager.execution_log) == 0


def test_trigger_manager_initialization_with_workforce():
    """Test TriggerManager initialization with Workforce handler"""
    workforce = Workforce("Test Workforce")
    handler = WorkforceHandler(workforce=workforce)
    manager = TriggerManager(handler=handler)

    assert manager.handler is handler
    assert isinstance(manager.handler, WorkforceHandler)
    assert manager.handler.workforce is workforce


def test_trigger_manager_initialization_with_chat_agent():
    """Test TriggerManager initialization with ChatAgent handler"""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    chat_agent = ChatAgent(system_message="Test assistant", model=model)
    handler = ChatAgentHandler(chat_agent=chat_agent)
    manager = TriggerManager(handler=handler)

    assert manager.handler is handler
    assert isinstance(manager.handler, ChatAgentHandler)
    assert manager.handler.chat_agent is chat_agent


def test_trigger_manager_validation_error_workforce_with_none_handler():
    """Test that TriggerManager works with None handler"""
    manager = TriggerManager(handler=None)

    assert manager.handler is None


def test_trigger_manager_default_handlers():
    """Test that handlers can be created with default configurations"""
    workforce_handler = WorkforceHandler()
    chat_agent_handler = ChatAgentHandler()

    assert workforce_handler.workforce is not None
    assert chat_agent_handler.chat_agent is not None


def test_trigger_manager_default_workforce_creation():
    """Test that default Workforce is created in WorkforceHandler
    when no workforce provided"""
    handler = WorkforceHandler()

    assert handler.workforce is not None
    assert isinstance(handler.workforce, Workforce)


def test_trigger_manager_default_chat_agent_creation():
    """Test that default ChatAgent is created in ChatAgentHandler
    when no chat_agent provided"""
    handler = ChatAgentHandler()

    assert handler.chat_agent is not None
    assert isinstance(handler.chat_agent, ChatAgent)


@pytest.mark.asyncio
async def test_register_trigger():
    """Test registering a trigger without auto-activation"""
    manager = TriggerManager()
    trigger = MockTrigger()

    result = await manager.register_trigger(trigger, auto_activate=False)

    assert result is True
    assert trigger.trigger_id in manager.triggers
    assert manager.triggers[trigger.trigger_id] == trigger
    assert trigger.state == TriggerState.INACTIVE


@pytest.mark.asyncio
async def test_register_trigger_with_auto_activation():
    """Test registering a trigger with auto-activation"""
    manager = TriggerManager()
    trigger = MockTrigger()

    result = await manager.register_trigger(trigger, auto_activate=True)

    assert result is True
    assert trigger.trigger_id in manager.triggers
    assert trigger.state == TriggerState.ACTIVE


@pytest.mark.asyncio
async def test_register_trigger_with_workforce_handler():
    """Test registering trigger with workforce handler"""
    workforce = Workforce("Test Workforce")
    handler = WorkforceHandler(workforce=workforce)
    manager = TriggerManager(handler=handler)
    trigger = MockTrigger()

    await manager.register_trigger(trigger, auto_activate=False)

    assert trigger.trigger_id in manager.triggers
    assert len(trigger._callbacks) > 0


@pytest.mark.asyncio
async def test_deactivate_all_triggers():
    """Test deactivating all registered triggers"""
    manager = TriggerManager()
    trigger1 = MockTrigger(trigger_id="trigger1")
    trigger2 = MockTrigger(trigger_id="trigger2")

    await manager.register_trigger(trigger1, auto_activate=True)
    await manager.register_trigger(trigger2, auto_activate=True)

    assert trigger1.state == TriggerState.ACTIVE
    assert trigger2.state == TriggerState.ACTIVE

    await manager.deactivate_all_triggers()

    assert trigger1.state == TriggerState.INACTIVE
    assert trigger2.state == TriggerState.INACTIVE


def test_set_default_task():
    """Test setting default task for Workforce processing"""
    handler = WorkforceHandler()
    task = Task(content="Test task", id="test_task_1")

    handler.default_task = task

    assert handler.default_task is task
    assert handler.default_task.id == "test_task_1"


def test_set_default_prompt():
    """Test setting default prompt for ChatAgent processing"""
    handler = ChatAgentHandler()
    prompt = "Process this trigger event carefully"

    handler.set_default_prompt(prompt)

    assert handler.default_prompt == prompt


def test_get_trigger_status():
    """Test getting status of all triggers"""
    manager = TriggerManager()

    # Create mock trigger directly to avoid async
    trigger1 = MockTrigger(trigger_id="trigger1", name="Test Trigger 1")
    trigger2 = MockTrigger(trigger_id="trigger2", name="Test Trigger 2")
    trigger1.state = TriggerState.ACTIVE
    trigger2.state = TriggerState.INACTIVE

    manager.triggers["trigger1"] = trigger1
    manager.triggers["trigger2"] = trigger2

    status = manager.get_trigger_status()

    assert "trigger1" in status
    assert "trigger2" in status
    assert status["trigger1"]["state"] == "active"
    assert status["trigger2"]["state"] == "inactive"
    assert status["trigger1"]["type"] == "MockTrigger"
    assert status["trigger2"]["type"] == "MockTrigger"


@pytest.mark.asyncio
async def test_handle_trigger_event_with_none_handler():
    """Test that events are logged but not processed with no handler"""
    manager = TriggerManager(handler=None)
    trigger = MockTrigger()

    await manager.register_trigger(trigger, auto_activate=True)

    event = TriggerEvent(
        trigger_id="test_trigger",
        trigger_type=TriggerType.CUSTOM,
        timestamp=datetime.now(),
        payload={"test": "data"},
    )

    # Should not raise error, just log
    await manager._handle_trigger_event(event)


@pytest.mark.asyncio
async def test_handle_trigger_event_with_workforce():
    """Test event processing with Workforce handler"""
    workforce = Workforce("Test Workforce")
    handler = WorkforceHandler(workforce=workforce)
    manager = TriggerManager(handler=handler)

    # Mock the workforce process_task_async method
    with patch.object(
        workforce, 'process_task_async', new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = Task(
            content="Processed", id="processed_task"
        )

        with patch.object(workforce, 'stop_gracefully') as mock_stop:
            event = TriggerEvent(
                trigger_id="test_trigger",
                trigger_type=TriggerType.CUSTOM,
                timestamp=datetime.now(),
                payload={"message": "Test event"},
            )

            await manager._handle_trigger_event(event)

            # Verify workforce was called
            mock_process.assert_called_once()
            mock_stop.assert_called_once()


@pytest.mark.asyncio
async def test_handle_trigger_event_with_chat_agent():
    """Test event processing with ChatAgent handler"""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    chat_agent = ChatAgent(system_message="Test assistant", model=model)
    handler = ChatAgentHandler(chat_agent=chat_agent)
    manager = TriggerManager(handler=handler)

    # Mock the chat_agent astep method
    mock_response = MagicMock()
    mock_response.msg.content = "Processed response"

    with patch.object(
        chat_agent, 'astep', new_callable=AsyncMock, return_value=mock_response
    ):
        event = TriggerEvent(
            trigger_id="test_trigger",
            trigger_type=TriggerType.CUSTOM,
            timestamp=datetime.now(),
            payload={"message": "Test event"},
        )

        await manager._handle_trigger_event(event)


@pytest.mark.asyncio
async def test_event_deduplication():
    """Test that duplicate events are filtered out"""
    manager = TriggerManager(allow_duplicate_events=False)

    event1 = TriggerEvent(
        trigger_id="test_trigger",
        trigger_type=TriggerType.CUSTOM,
        timestamp=datetime.now(),
        payload={"test": "data"},
        correlation_id="event_123",
    )

    event2 = TriggerEvent(
        trigger_id="test_trigger",
        trigger_type=TriggerType.CUSTOM,
        timestamp=datetime.now(),
        payload={"test": "data"},
        correlation_id="event_123",
    )

    # Process first event
    await manager._handle_trigger_event(event1)
    assert len(manager.processed_events) == 1

    # Try to process duplicate event
    await manager._handle_trigger_event(event2)
    # Should still be 1 (duplicate ignored)
    assert len(manager.processed_events) == 1


@pytest.mark.asyncio
async def test_allow_duplicate_events():
    """Test that duplicate events are allowed when configured"""
    manager = TriggerManager(allow_duplicate_events=True)

    event1 = TriggerEvent(
        trigger_id="test_trigger",
        trigger_type=TriggerType.CUSTOM,
        timestamp=datetime.now(),
        payload={"test": "data"},
        correlation_id="event_123",
    )

    event2 = TriggerEvent(
        trigger_id="test_trigger",
        trigger_type=TriggerType.CUSTOM,
        timestamp=datetime.now(),
        payload={"test": "data"},
        correlation_id="event_123",
    )

    # Process both events (duplicates allowed)
    await manager._handle_trigger_event(event1)
    await manager._handle_trigger_event(event2)

    # Should process both since deduplication is disabled
    assert len(manager.processed_events) == 0


@pytest.mark.asyncio
async def test_event_to_task_conversion():
    """Test conversion of trigger event to task"""
    handler = WorkforceHandler()

    event = TriggerEvent(
        trigger_id="test_trigger",
        trigger_type=TriggerType.CUSTOM,
        timestamp=datetime.now(),
        payload={"task_content": "Custom task from trigger"},
    )

    task = handler._event_to_task(event)

    assert isinstance(task, Task)
    assert (
        "Custom task from trigger" in task.content
        or "test_trigger" in task.content
    )


@pytest.mark.asyncio
async def test_event_to_task_with_message_payload():
    """Test event to task conversion with message in payload"""
    handler = WorkforceHandler()

    event = TriggerEvent(
        trigger_id="test_trigger",
        trigger_type=TriggerType.CUSTOM,
        timestamp=datetime.now(),
        payload={"message": "Process this message"},
    )

    task = handler._event_to_task(event)

    assert isinstance(task, Task)
    assert (
        "Process this message" in task.content
        or "test_trigger" in task.content
    )


@pytest.mark.asyncio
async def test_handle_trigger_event_with_default_task():
    """Test event processing uses default task when configured"""
    workforce = Workforce("Test Workforce")
    default_task = Task(content="Default content", id="default_task")
    handler = WorkforceHandler(workforce=workforce, default_task=default_task)
    manager = TriggerManager(handler=handler)

    with patch.object(
        workforce, 'process_task_async', new_callable=AsyncMock
    ) as mock_process:
        mock_process.return_value = Task(
            content="Processed", id="processed_task"
        )

        with patch.object(workforce, 'stop_gracefully'):
            event = TriggerEvent(
                trigger_id="test_trigger",
                trigger_type=TriggerType.CUSTOM,
                timestamp=datetime.now(),
                payload={"test": "data"},
            )

            await manager._handle_trigger_event(event)

            # Verify workforce was called
            mock_process.assert_called_once()


@pytest.mark.asyncio
async def test_handle_trigger_event_with_default_prompt():
    """Test event processing uses default prompt when configured"""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    chat_agent = ChatAgent(system_message="Test assistant", model=model)
    default_prompt = "Custom prompt template"
    handler = ChatAgentHandler(
        chat_agent=chat_agent, default_prompt=default_prompt
    )
    manager = TriggerManager(handler=handler)

    mock_response = MagicMock()
    mock_response.msg.content = "Processed response"

    with patch.object(
        chat_agent, 'astep', new_callable=AsyncMock, return_value=mock_response
    ) as mock_step:
        event = TriggerEvent(
            trigger_id="test_trigger",
            trigger_type=TriggerType.CUSTOM,
            timestamp=datetime.now(),
            payload={"test": "data"},
        )

        await manager._handle_trigger_event(event)

        # Verify the astep method was called
        mock_step.assert_called_once()

        # Verify the prompt was used
        call_args = mock_step.call_args[0][0]
        assert "test_trigger" in call_args or default_prompt in call_args


@pytest.mark.asyncio
async def test_handle_trigger_event_error_handling():
    """Test that errors during event handling are caught and logged"""
    workforce = Workforce("Test Workforce")
    handler = WorkforceHandler(workforce=workforce)
    manager = TriggerManager(handler=handler)

    # Mock process_task_async to raise an error
    with patch.object(
        workforce, 'process_task_async', new_callable=AsyncMock
    ) as mock_process:
        mock_process.side_effect = Exception("Processing error")

        event = TriggerEvent(
            trigger_id="test_trigger",
            trigger_type=TriggerType.CUSTOM,
            timestamp=datetime.now(),
            payload={"test": "data"},
        )

        # Should not raise error, just log it
        await manager._handle_trigger_event(event)


@pytest.mark.asyncio
async def test_trigger_callback_integration():
    """Test full integration of trigger callbacks with manager"""
    manager = TriggerManager()
    trigger = MockTrigger()

    # Track callback invocation
    callback_called = False

    async def test_callback(event: TriggerEvent):
        nonlocal callback_called
        callback_called = True
        assert event.trigger_id == "test_trigger"
        assert event.payload["test"] == "data"

    trigger.add_callback(test_callback)
    await manager.register_trigger(trigger, auto_activate=True)

    # Emit test event
    await trigger.emit_test_event({"test": "data"})

    # Verify callback was invoked
    assert callback_called is True
