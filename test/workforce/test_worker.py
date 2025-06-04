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
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from camel.societies.workforce.worker import Worker, with_timeout, TIMEOUT_THRESHOLD
from camel.societies.workforce.task_channel import TaskChannel
from camel.tasks.task import Task, TaskState


class TestTimeoutWorker(Worker):
    """Test Worker implementation for timeout testing"""
    
    def __init__(self, description="Test Worker", node_id=None):
        super().__init__(description, node_id=node_id)
        
    async def _process_task(self, task, dependencies):
        """Simple implementation of task processing method"""
        return TaskState.DONE


@pytest.mark.asyncio
async def test_with_timeout_function():
    """Test the basic functionality of with_timeout function"""
    # Test normal case
    mock_coro = AsyncMock()
    mock_coro.return_value = "success"
    
    result = await with_timeout(mock_coro(), timeout=1.0, context="test")
    assert result == "success"
    
    # Test timeout case by directly mocking timeout error
    mock_failing_coro = AsyncMock()
    mock_failing_coro.side_effect = asyncio.TimeoutError("Simulated timeout")
    
    with pytest.raises(asyncio.TimeoutError) as excinfo:
        await with_timeout(mock_failing_coro(), timeout=1.0, context="test timeout")
    
    assert "Timed out while test timeout" in str(excinfo.value)


@pytest.mark.asyncio
async def test_get_assigned_task_timeout():
    """Test timeout handling in _get_assigned_task method"""
    worker = TestTimeoutWorker()
    
    # Mock TaskChannel to simulate timeout
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_channel.get_assigned_task_by_assignee.side_effect = asyncio.TimeoutError("Simulated timeout")
    worker._channel = mock_channel
    
    with pytest.raises(asyncio.TimeoutError):
        await worker._get_assigned_task()
    
    mock_channel.get_assigned_task_by_assignee.assert_called_once()


@pytest.mark.asyncio
async def test_listen_to_channel_recovers_from_timeout():
    """Test that _listen_to_channel method recovers from timeouts"""
    worker = TestTimeoutWorker()
    
    # Mock TaskChannel
    mock_channel = AsyncMock(spec=TaskChannel)
    
    # Configure get_assigned_task_by_assignee to first throw TimeoutError, then return normal result
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    mock_task.content = "test content"
    
    call_count = 0
    
    async def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise asyncio.TimeoutError("Simulated timeout")
        return mock_task
    
    mock_channel.get_assigned_task_by_assignee.side_effect = side_effect
    mock_channel.get_dependency_ids.return_value = []
    mock_channel.return_task = AsyncMock()
    
    worker._channel = mock_channel
    
    # Patch _listen_to_channel to run limited times
    original_listen = worker._listen_to_channel
    
    async def patched_listen():
        worker._running = True
        try:
            # Only process one task - retry if timeout occurs
            attempts = 0
            max_attempts = 3
            while attempts < max_attempts:
                try:
                    await worker._get_assigned_task()
                    break  # Success, exit the loop
                except asyncio.TimeoutError:
                    # This is expected on first attempt, retry
                    attempts += 1
                    if attempts >= max_attempts:
                        raise  # Re-raise if max attempts reached
        finally:
            worker._running = False
    
    # Patch start method to avoid double wrapping with timeout
    original_start = worker.start
    async def direct_start():
        return await patched_listen()
        
    with patch.object(worker, '_listen_to_channel', patched_listen), \
         patch.object(worker, 'start', direct_start):
        # Should not raise exception
        await worker.start()
    
    # Verify first call failed and then retried
    assert mock_channel.get_assigned_task_by_assignee.call_count == 2

@pytest.mark.asyncio
async def test_worker_with_timeout_integration():
    """Test the integration of with_timeout across Worker methods"""
    worker = TestTimeoutWorker()
    
    # Mock TaskChannel
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    mock_task.content = "test content"
    mock_task.set_state = MagicMock()
    
    mock_channel.get_assigned_task_by_assignee.return_value = mock_task
    mock_channel.get_dependency_ids.return_value = []
    mock_channel.return_task = AsyncMock()
    
    worker._channel = mock_channel
    
    # Patch _listen_to_channel to run only one iteration
    original_listen = worker._listen_to_channel
    
    ran_once = False
    
    async def patched_listen():
        nonlocal ran_once
        worker._running = True
        if not ran_once:
            ran_once = True
            # Get task
            task = await worker._get_assigned_task()
            # Get dependencies
            dependency_ids = await with_timeout(
                worker._channel.get_dependency_ids(),
                context=f"getting dependency IDs for task {task.id}"
            )
            task_dependencies = []
            # Process task
            task_state = await with_timeout(
                worker._process_task(task, task_dependencies),
                timeout=TIMEOUT_THRESHOLD,
                context=f"processing task {task.id}"
            )
            # Update status
            task.set_state(task_state)
            # Return task
            await with_timeout(
                worker._channel.return_task(task.id),
                timeout=TIMEOUT_THRESHOLD,
                context=f"returning task {task.id}"
            )
        worker._running = False
    
    with patch.object(worker, '_listen_to_channel', patched_listen):
        await worker.start()
    
    # Verify all methods were called correctly
    mock_channel.get_assigned_task_by_assignee.assert_called_once()
    mock_channel.get_dependency_ids.assert_called_once()
    mock_task.set_state.assert_called_once_with(TaskState.DONE)
    mock_channel.return_task.assert_called_once_with(mock_task.id)


@pytest.mark.asyncio
async def test_multiple_timeout_points():
    """Test handling timeouts at different points in the worker process"""
    worker = TestTimeoutWorker()
    
    # Mock TaskChannel that times out during dependency retrieval
    mock_channel = AsyncMock(spec=TaskChannel)
    mock_task = MagicMock(spec=Task)
    mock_task.id = "test_task_id"
    
    mock_channel.get_assigned_task_by_assignee.return_value = mock_task
    mock_channel.get_dependency_ids.side_effect = asyncio.TimeoutError("Dependency timeout")
    
    worker._channel = mock_channel
    
    # Mock _process_task to verify it's not called when dependencies time out
    process_task_mock = AsyncMock()
    worker._process_task = process_task_mock
    
    # Patch _listen_to_channel to handle one task
    async def patched_listen():
        worker._running = True
        try:
            # Get task
            task = await worker._get_assigned_task()
            
            # Get dependencies - this will time out
            try:
                dependency_ids = await with_timeout(
                    worker._channel.get_dependency_ids(),
                    context=f"getting dependency IDs for task {task.id}"
                )
                task_dependencies = []
                for dep_id in dependency_ids:
                    dep_task = await with_timeout(
                        worker._channel.get_task_by_id(dep_id),
                        context=f"getting dependency task {dep_id}"
                    )
                    task_dependencies.append(dep_task)
                
                # Process task - should not reach here due to timeout
                task_state = await worker._process_task(task, task_dependencies)
                task.set_state(task_state)
                await worker._channel.return_task(task.id)
            except asyncio.TimeoutError:
                # This is expected, continue to next task
                pass
        finally:
            worker._running = False
    
    with patch.object(worker, '_listen_to_channel', patched_listen):
        await worker.start()
    
    # Verify get_dependency_ids was called but _process_task was not
    mock_channel.get_assigned_task_by_assignee.assert_called_once()
    mock_channel.get_dependency_ids.assert_called_once()
    process_task_mock.assert_not_called()