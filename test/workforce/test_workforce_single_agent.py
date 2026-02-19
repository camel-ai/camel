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
import time
from typing import List
from unittest.mock import AsyncMock, patch

import pytest

from camel.agents.chat_agent import ChatAgent
from camel.messages.base import BaseMessage
from camel.societies.workforce import Workforce
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.tasks.task import Task, TaskState


class AlwaysFailingWorker(SingleAgentWorker):
    """A worker that always fails tasks for testing purposes."""

    def __init__(self, description: str):
        # Create a dummy agent - won't be used since we override _process_task
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Failing Worker", content="This worker always fails."
        )
        agent = ChatAgent(sys_msg)
        super().__init__(description, agent)

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        """Always return failed task."""
        task.state = TaskState.FAILED
        task.result = "Task failed deliberately for testing"
        return TaskState.FAILED


@pytest.mark.asyncio
async def test_graceful_shutdown_immediate_timeout():
    """Test that 0 timeout causes immediate shutdown."""
    # Create workforce with 0 timeout (immediate shutdown)
    workforce = Workforce("Test Workforce", graceful_shutdown_timeout=0.0)

    # Create a task to test with
    task = Task(content="This will fail", id="test_task")

    # Test the graceful shutdown method directly
    start_time = time.time()

    # Call graceful shutdown with 0 timeout (should return immediately)
    await workforce._graceful_shutdown(task)

    end_time = time.time()
    execution_time = end_time - start_time

    # Should complete immediately (well under 0.1 seconds)
    assert (
        execution_time < 0.1
    ), f"Expected immediate shutdown, but took {execution_time:.2f} seconds"
    print(
        f"✓ Immediate shutdown test passed - execution time: "
        f"{execution_time:.3f}s"
    )


@pytest.mark.asyncio
async def test_graceful_shutdown_one_second_timeout():
    """Test that 1 second timeout waits approximately 1 second
    before shutdown."""
    # Create workforce with 1 second timeout
    workforce = Workforce("Test Workforce", graceful_shutdown_timeout=1.0)

    # Create a task to test with
    task = Task(content="This will fail", id="test_task")

    # Test the graceful shutdown method directly
    start_time = time.time()

    # Call graceful shutdown with 1 second timeout
    await workforce._graceful_shutdown(task)

    end_time = time.time()
    execution_time = end_time - start_time

    # Should take approximately 1 second
    # (allow 0.1s margin for processing overhead)
    assert (
        0.9 <= execution_time <= 1.2
    ), f"Expected ~1 second shutdown, but took {execution_time:.2f} seconds"
    print(
        f"✓ 1-second timeout test passed - execution time: "
        f"{execution_time:.2f}s"
    )


@pytest.mark.asyncio
@patch('camel.tasks.task.Task.decompose')
@patch(
    'camel.societies.workforce.single_agent_worker.SingleAgentWorker._process_task'
)
async def test_get_dep_tasks_info(mock_process_task, mock_decompose):
    """Original test for backwards compatibility."""
    sys_msg = BaseMessage.make_assistant_message(
        role_name="programmer",
        content="You are a python programmer.",
    )
    agent = ChatAgent(sys_msg)
    test_worker = SingleAgentWorker('agent1', agent)
    human_task = Task(
        content='develop a python program of investing stock.',
        id='0',
    )

    # Configure the mocks
    mock_subtasks = [
        Task(content="Task 1", id="1"),
        Task(content="Task 2", id="2"),
    ]
    mock_decompose.return_value = mock_subtasks
    mock_process_task.return_value = TaskState.DONE

    # Execute the test
    subtasks = human_task.decompose(agent)
    await test_worker._process_task(human_task, subtasks)

    # Verify the mocks were called
    mock_decompose.assert_called_once_with(agent)
    mock_process_task.assert_called_once_with(human_task, mock_subtasks)


def _make_worker():
    """Helper to create a SingleAgentWorker for breakpoint resume tests."""
    sys_msg = BaseMessage.make_assistant_message(
        role_name="test_worker",
        content="You are a test worker.",
    )
    agent = ChatAgent(sys_msg)
    return SingleAgentWorker("test worker", agent)


class TestBuildRetryMessage:
    """Tests for _build_retry_message."""

    def test_basic_retry_message(self):
        worker = _make_worker()
        task = Task(content="do something", id="t1")
        task.failure_count = 2
        task.result = "ValueError: bad input"

        msg = worker._build_retry_message(task)

        assert "Retry attempt 2" in msg
        assert "ValueError: bad input" in msg

    def test_none_result_fallback(self):
        worker = _make_worker()
        task = Task(content="do something", id="t1")
        task.failure_count = 1
        task.result = None

        msg = worker._build_retry_message(task)

        assert "Unknown error" in msg


class TestRetainedAgentLifecycle:
    """Tests for agent retention, release and discard."""

    @pytest.mark.asyncio
    async def test_release_retained_agent_returns_to_pool(self):
        worker = _make_worker()
        mock_agent = AsyncMock(spec=ChatAgent)
        worker._failed_task_agents["t1"] = mock_agent
        worker._return_worker_agent = AsyncMock()

        await worker.release_retained_agent("t1")

        assert "t1" not in worker._failed_task_agents
        worker._return_worker_agent.assert_awaited_once_with(mock_agent)

    @pytest.mark.asyncio
    async def test_release_nonexistent_agent_is_noop(self):
        worker = _make_worker()
        worker._return_worker_agent = AsyncMock()

        await worker.release_retained_agent("no_such_task")

        worker._return_worker_agent.assert_not_awaited()

    def test_discard_retained_agent(self):
        worker = _make_worker()
        mock_agent = AsyncMock(spec=ChatAgent)
        worker._failed_task_agents["t1"] = mock_agent

        worker.discard_retained_agent("t1")

        assert "t1" not in worker._failed_task_agents

    def test_reset_clears_failed_task_agents(self):
        worker = _make_worker()
        worker._failed_task_agents["t1"] = AsyncMock(spec=ChatAgent)
        worker._failed_task_agents["t2"] = AsyncMock(spec=ChatAgent)

        worker.reset()

        assert len(worker._failed_task_agents) == 0
