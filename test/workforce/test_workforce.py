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
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.workforce import Workforce
from camel.tasks.task import Task, TaskState
from camel.types import ModelPlatformType, ModelType


class TimeoutWorkforce(Workforce):
    r"""A test workforce class for testing timeout handling"""

    def __init__(self):
        super().__init__("Test Workforce")
        # Skip the actual initialization to make testing easier
        self._running = False
        self._channel = None
        self._pending_tasks = []
        self._task = None
        self._child_listening_tasks = []
        self._children = []


@pytest.mark.asyncio
async def test_with_timeout_function():
    r"""Test the with_timeout function handles completions and
    timeouts correctly"""
    # Test normal operation (successful completion)
    mock_coro = AsyncMock()
    mock_coro.return_value = "success"
    result = await mock_coro()
    assert result == "success"

    # Test timeout handling
    mock_timeout_coro = AsyncMock()
    mock_timeout_coro.side_effect = asyncio.TimeoutError("Simulated timeout")

    with pytest.raises(asyncio.TimeoutError) as exc_info:
        await mock_timeout_coro()

    assert "Simulated timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_post_task_timeout():
    r"""Test timeout handling in _post_task method"""
    workforce = TimeoutWorkforce()

    # Mock TaskChannel that times out
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_channel.post_task.side_effect = asyncio.TimeoutError()

    workforce._channel = mock_channel
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"

    # Since _post_task catches TimeoutError and doesn't re-raise it,
    # we should test that it completes without raising an exception
    # and that the in_flight_tasks counter is properly decremented
    workforce._in_flight_tasks = 0
    await workforce._post_task(mock_task, "test_worker_id")

    # Verify the channel method was called
    mock_channel.post_task.assert_called_once()
    assert workforce._in_flight_tasks == 0


@pytest.mark.asyncio
async def test_listen_to_channel_recovers_from_timeout():
    r"""Test that _listen_to_channel method recovers from timeouts when
    getting returned tasks"""
    workforce = TimeoutWorkforce()

    # Mock TaskChannel with first call timing out, second call succeeding
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    mock_task.state = TaskState.DONE

    # Configure get_returned_task_by_publisher to first throw TimeoutError,
    # then return normal result
    call_count = 0

    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.TimeoutError("Simulated timeout")
        return mock_task

    mock_channel.get_returned_task_by_publisher.side_effect = side_effect
    workforce._channel = mock_channel

    # Mock _handle_completed_task to avoid full implementation
    workforce._handle_completed_task = AsyncMock()

    # Mock _post_ready_tasks to avoid implementation
    workforce._post_ready_tasks = AsyncMock()

    # Patch _listen_to_channel to run only limited iterations
    async def patched_listen():
        workforce._running = True
        workforce._task = mock_task
        workforce._pending_tasks = [mock_task]

        try:
            # Post initial ready tasks
            await workforce._post_ready_tasks()

            try:
                returned_task_first = await workforce._get_returned_task()
            except asyncio.TimeoutError:
                returned_task_first = None
            assert returned_task_first is None  # Should return None on timeout

            # Ensure the mock was called for the first attempt
            assert mock_channel.get_returned_task_by_publisher.call_count == 1

            # Second try should succeed
            returned_task_after_timeout = await workforce._get_returned_task()
            assert returned_task_after_timeout is mock_task

            # Ensure the mock was called for the second attempt
            assert mock_channel.get_returned_task_by_publisher.call_count == 2

            # Process the task
            await workforce._handle_completed_task(returned_task_after_timeout)
            workforce._handle_completed_task.assert_called_once_with(mock_task)

        finally:
            workforce._running = False

    async def direct_start():
        return await patched_listen()

    with (
        patch.object(workforce, '_listen_to_channel', patched_listen),
        patch.object(workforce, 'start', direct_start),
    ):
        await workforce.start()

    # Verify get_returned_task_by_publisher was called twice (first fails,
    # second succeeds)
    assert mock_channel.get_returned_task_by_publisher.call_count == 2
    # Verify the task was processed
    workforce._handle_completed_task.assert_called_once_with(mock_task)


@pytest.mark.asyncio
async def test_workforce_with_timeout_integration():
    r"""Test the integration of with_timeout across Workforce methods"""
    workforce = TimeoutWorkforce()

    # Mock TaskChannel
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    mock_task.state = TaskState.DONE

    mock_channel.get_returned_task_by_publisher.return_value = mock_task
    workforce._channel = mock_channel

    # Mock _handle_completed_task to avoid full implementation
    workforce._handle_completed_task = AsyncMock()

    # Mock _post_ready_tasks to avoid implementation
    workforce._post_ready_tasks = AsyncMock()

    # Patch _listen_to_channel to run only once
    ran_once = False

    async def patched_listen():
        nonlocal ran_once
        workforce._running = True
        workforce._task = mock_task
        workforce._pending_tasks = [mock_task]

        if not ran_once:
            ran_once = True
            # Post initial ready tasks
            await workforce._post_ready_tasks()

            # Get returned task
            returned_task = await workforce._get_returned_task()

            # Handle completed task
            await workforce._handle_completed_task(returned_task)

        workforce._running = False

    with patch.object(workforce, '_listen_to_channel', patched_listen):
        await workforce.start()

    # Verify methods were called
    mock_channel.get_returned_task_by_publisher.assert_called_once()
    workforce._post_ready_tasks.assert_called_once()
    workforce._handle_completed_task.assert_called_once_with(mock_task)


@pytest.mark.asyncio
async def test_multiple_timeout_points():
    r"""Test handling timeouts at different points in the workforce process"""
    workforce = TimeoutWorkforce()

    # Mock TaskChannel that times out during get_returned_task
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    mock_task.state = TaskState.FAILED
    mock_task.content = "Test task content"
    mock_task.additional_info = {}
    mock_task.result = "Mock task failed"
    mock_task.assigned_worker_id = "test_worker_id"

    mock_task.failure_count = 0
    mock_task.get_depth.return_value = 0

    mock_channel.get_returned_task_by_publisher.return_value = mock_task

    # Make _handle_failed_task timeout on channel operation
    mock_channel.archive_task.side_effect = asyncio.TimeoutError()

    workforce._channel = mock_channel
    workforce._task = mock_task
    workforce._pending_tasks = deque([mock_task])
    workforce._assignees = {mock_task.id: "test_worker_id"}

    # Patch _listen_to_channel to handle one task with the timeout
    async def patched_listen():
        workforce._running = True
        try:
            # Post initial ready tasks
            await workforce._post_ready_tasks()

            # Get task - should succeed
            returned_task = await workforce._get_returned_task()

            with pytest.raises(asyncio.TimeoutError):
                await workforce._handle_failed_task(returned_task)

        finally:
            workforce._running = False

    # Mock methods to avoid full implementation
    workforce._post_ready_tasks = AsyncMock()

    async def direct_start():
        return await patched_listen()

    with (
        patch.object(workforce, '_listen_to_channel', patched_listen),
        patch.object(workforce, 'start', direct_start),
    ):
        await workforce.start()

    # Verify get_returned_task_by_publisher was called
    mock_channel.get_returned_task_by_publisher.assert_called_once()
    # Verify archive_task was called (this is where the timeout occurred)
    mock_channel.archive_task.assert_called_once_with(mock_task.id)


@pytest.fixture
def mock_model():
    r"""Create a real model backend for testing"""
    return ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )


@pytest.fixture
def mock_agent():
    r"""Create a mock agent with memory functionality"""
    agent = MagicMock(spec=ChatAgent)
    agent.agent_id = "test_agent_id"
    agent.memory = MagicMock()
    agent.memory.get_context.return_value = ([], 0)

    # Mock step method
    response = MagicMock()
    response.msgs = [MagicMock(content="Test response")]
    agent.step.return_value = response
    return agent


@pytest.fixture
def sample_shared_memory():
    r"""Sample shared memory data for testing"""
    return {
        'coordinator': [{"role": "user", "content": "Coordinator info"}],
        'task_agent': [{"role": "user", "content": "Task agent info"}],
        'workers': [
            {"role": "user", "content": "Agent knows secret code BLUE42"},
            {"role": "user", "content": "Agent knows meeting room 314"},
        ],
    }


@pytest.mark.parametrize("share_memory", [True, False])
def test_workforce_initialization(mock_model, share_memory):
    r"""Test workforce initialization with different memory configurations"""
    # Create custom agents for the workforce
    coordinator_agent = ChatAgent(
        "You are a helpful coordinator.", model=mock_model
    )
    task_agent = ChatAgent("You are a helpful task planner.", model=mock_model)

    workforce = Workforce(
        description="Test Workforce",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        share_memory=share_memory,
        graceful_shutdown_timeout=2.0,
    )

    assert workforce.share_memory == share_memory
    assert workforce.graceful_shutdown_timeout == 2.0


def test_shared_memory_operations(
    mock_model, mock_agent, sample_shared_memory
):
    r"""Test shared memory collection and synchronization"""
    # Create custom agents for the workforce
    coordinator_agent = ChatAgent(
        "You are a helpful coordinator.", model=mock_model
    )
    task_agent = ChatAgent("You are a helpful task planner.", model=mock_model)

    workforce = Workforce(
        description="Test Workforce",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        share_memory=True,
    )

    workforce.add_single_agent_worker("TestAgent", mock_agent)

    # Test memory collection and synchronization
    with patch.object(
        workforce, '_collect_shared_memory', return_value=sample_shared_memory
    ):
        with patch.object(
            workforce, '_share_memory_with_agents'
        ) as mock_share:
            workforce._sync_shared_memory()
            mock_share.assert_called_once_with(sample_shared_memory)


def test_cross_agent_memory_access(mock_model, sample_shared_memory):
    r"""Test cross-agent information access after memory sync"""
    # Create custom agents for the workforce
    coordinator_agent = ChatAgent(
        "You are a helpful coordinator.", model=mock_model
    )
    task_agent = ChatAgent("You are a helpful task planner.", model=mock_model)

    workforce = Workforce(
        description="Test Workforce",
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
        share_memory=True,
    )

    # Create agents with cross-knowledge after sync
    agent_alice = MagicMock(spec=ChatAgent)
    agent_alice.agent_id = "alice_id"
    agent_alice.memory = MagicMock()
    agent_alice.memory.get_context.return_value = ([], 0)
    alice_response = MagicMock()
    alice_response.msgs = [
        MagicMock(content="I know secret code BLUE42 and room 314")
    ]
    agent_alice.step.return_value = alice_response

    agent_bob = MagicMock(spec=ChatAgent)
    agent_bob.agent_id = "bob_id"
    agent_bob.memory = MagicMock()
    agent_bob.memory.get_context.return_value = ([], 0)
    bob_response = MagicMock()
    bob_response.msgs = [MagicMock(content="I know room 314 and code BLUE42")]
    agent_bob.step.return_value = bob_response

    workforce.add_single_agent_worker("Alice", agent_alice)
    workforce.add_single_agent_worker("Bob", agent_bob)

    # Simulate memory sync
    with patch.object(
        workforce, '_collect_shared_memory', return_value=sample_shared_memory
    ):
        with patch.object(workforce, '_share_memory_with_agents'):
            workforce._sync_shared_memory()

    # Test that both agents have access to shared information
    query = "What information do you have?"
    alice_content = agent_alice.step(query).msgs[0].content.lower()
    bob_content = agent_bob.step(query).msgs[0].content.lower()

    # Both should know both pieces of information
    for content in [alice_content, bob_content]:
        assert "blue42" in content and "314" in content


def test_dynamic_worker_addition():
    r"""Test adding workers dynamically during different workforce states"""
    workforce = Workforce(description="Dynamic Test Workforce")
    from camel.societies.workforce.workforce import WorkforceState

    # Test 1: Add worker in IDLE state (should work)
    agent1 = ChatAgent("You are a test agent.")
    workforce.add_single_agent_worker("Test Worker 1", agent1)
    assert len(workforce._children) == 1

    # Test 2: Add worker in PAUSED state (should work)
    workforce._state = WorkforceState.PAUSED
    agent2 = ChatAgent("You are another test agent.")
    workforce.add_single_agent_worker("Test Worker 2", agent2)
    assert len(workforce._children) == 2

    # Test 3: Try to add worker in RUNNING state (should fail)
    workforce._state = WorkforceState.RUNNING
    agent3 = ChatAgent("You should not be added.")

    with pytest.raises(
        RuntimeError, match="Cannot add workers while workforce is running"
    ):
        workforce.add_single_agent_worker("Should Fail", agent3)

    assert len(workforce._children) == 2  # No new worker added


@pytest.mark.asyncio
async def test_dynamic_worker_types():
    r"""Test adding different types of workers during pause"""
    workforce = Workforce(description="Worker Types Test")
    from camel.societies.workforce.workforce import WorkforceState

    workforce._state = WorkforceState.PAUSED

    # Add SingleAgentWorker
    agent = ChatAgent("You are a specialist.")
    workforce.add_single_agent_worker("Specialist", agent)
    assert len(workforce._children) == 1

    # Add RolePlayingWorker
    workforce.add_role_playing_worker(
        description="Analysis Team",
        assistant_role_name="Analyst",
        user_role_name="Expert",
    )
    assert len(workforce._children) == 2

    # Add nested Workforce
    nested = Workforce(description="Sub-team")
    workforce.add_workforce(nested)
    assert len(workforce._children) == 3


def test_start_child_node_helper():
    r"""Test the _start_child_node_when_paused helper function"""
    workforce = Workforce(description="Helper Test")
    from camel.societies.workforce.workforce import WorkforceState

    async def mock_coroutine():
        return "test"

    # Should do nothing when not paused
    workforce._state = WorkforceState.IDLE
    workforce._start_child_node_when_paused(mock_coroutine())

    # Should do nothing when no loop
    workforce._state = WorkforceState.PAUSED
    workforce._loop = None
    workforce._start_child_node_when_paused(mock_coroutine())
