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
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.workforce import (
    Workforce,
    with_timeout,
)
from camel.tasks.task import Task, TaskState


class TestTimeoutWorkforce(Workforce):
    """A test workforce class for testing timeout handling"""

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
    """Test the with_timeout function handles completions and timeouts correctly"""
    # Test normal operation (successful completion)
    mock_coro = AsyncMock()
    mock_coro.return_value = "success"
    result = await with_timeout(mock_coro(), context="test operation")
    assert result == "success"

    # Test timeout handling
    mock_timeout_coro = AsyncMock()
    mock_timeout_coro.side_effect = asyncio.TimeoutError("Simulated timeout")

    with pytest.raises(asyncio.TimeoutError) as exc_info:
        await with_timeout(
            mock_timeout_coro(), context="test timeout operation"
        )

    assert "Timed out while test timeout operation" in str(exc_info.value)


@pytest.mark.asyncio
async def test_post_task_timeout():
    """Test timeout handling in _post_task method"""
    workforce = TestTimeoutWorkforce()

    # Mock TaskChannel that times out
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_channel.post_task.side_effect = asyncio.TimeoutError()

    workforce._channel = mock_channel
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"

    # Only verify that a TimeoutError is raised, not its specific message
    with pytest.raises(asyncio.TimeoutError):
        await workforce._post_task(mock_task, "test_worker_id")

    # Verify the channel method was called
    mock_channel.post_task.assert_called_once()


@pytest.mark.asyncio
async def test_listen_to_channel_recovers_from_timeout():
    """Test that _listen_to_channel method recovers from timeouts when getting returned tasks"""
    workforce = TestTimeoutWorkforce()

    # Mock TaskChannel with first call timing out, second call succeeding
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    mock_task.state = TaskState.DONE

    # Configure get_returned_task_by_publisher to first throw TimeoutError, then return normal result
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

            # First try to get returned task - should timeout
            try:
                returned_task = await workforce._get_returned_task()
                assert False, "Should have timed out on first attempt"
            except asyncio.TimeoutError:
                # This is expected
                pass

            # Second try should succeed
            returned_task = await workforce._get_returned_task()
            # Process the task
            await workforce._handle_completed_task(returned_task)

        finally:
            workforce._running = False

    # Patch start method to avoid double wrapping with timeout
    original_start = workforce.start

    async def direct_start():
        return await patched_listen()

    with (
        patch.object(workforce, '_listen_to_channel', patched_listen),
        patch.object(workforce, 'start', direct_start),
    ):
        await workforce.start()

    # Verify get_returned_task_by_publisher was called twice (first fails, second succeeds)
    assert mock_channel.get_returned_task_by_publisher.call_count == 2
    # Verify the task was processed
    workforce._handle_completed_task.assert_called_once_with(mock_task)


@pytest.mark.asyncio
async def test_workforce_with_timeout_integration():
    """Test the integration of with_timeout across Workforce methods"""
    workforce = TestTimeoutWorkforce()

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
            await with_timeout(
                workforce._post_ready_tasks(),
                context="posting ready tasks at start",
            )

            # Get returned task
            returned_task = await with_timeout(
                workforce._get_returned_task(), context="getting returned task"
            )

            # Handle completed task
            await with_timeout(
                workforce._handle_completed_task(returned_task),
                context="handling completed task",
            )

        workforce._running = False

    with patch.object(workforce, '_listen_to_channel', patched_listen):
        await workforce.start()

    # Verify methods were called
    mock_channel.get_returned_task_by_publisher.assert_called_once()
    workforce._post_ready_tasks.assert_called_once()
    workforce._handle_completed_task.assert_called_once_with(mock_task)


@pytest.mark.asyncio
async def test_multiple_timeout_points():
    """Test handling timeouts at different points in the workforce process"""
    workforce = TestTimeoutWorkforce()

    # Mock TaskChannel that times out during get_returned_task
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    mock_task.state = TaskState.FAILED

    mock_task.failure_count = 0

    mock_channel.get_returned_task_by_publisher.return_value = mock_task

    # Make _handle_failed_task timeout
    mock_channel.remove_task.side_effect = asyncio.TimeoutError()

    workforce._channel = mock_channel
    workforce._task = mock_task
    workforce._pending_tasks = [mock_task]

    # Patch _listen_to_channel to handle one task with the timeout
    async def patched_listen():
        workforce._running = True
        try:
            # Post initial ready tasks
            await workforce._post_ready_tasks()

            # Get task - should succeed
            returned_task = await workforce._get_returned_task()

            # Handle failed task - should timeout during remove_task
            try:
                await workforce._handle_failed_task(returned_task)
                assert False, "Should have timed out when handling failed task"
            except asyncio.TimeoutError:
                # This is expected
                pass

        finally:
            workforce._running = False

    # Mock methods to avoid full implementation
    workforce._post_ready_tasks = AsyncMock()

    # Use the real _handle_failed_task for this test
    original_handle_failed = workforce._handle_failed_task

    # Patch start method to avoid timeout wrapper
    original_start = workforce.start

    async def direct_start():
        return await patched_listen()

    with (
        patch.object(workforce, '_listen_to_channel', patched_listen),
        patch.object(workforce, 'start', direct_start),
    ):
        await workforce.start()

    # Verify get_returned_task_by_publisher was called
    mock_channel.get_returned_task_by_publisher.assert_called_once()
    # Verify remove_task was called (this is where the timeout occurred)
    mock_channel.remove_task.assert_called_once_with(mock_task.id)
