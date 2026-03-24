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
from typing import Awaitable, Callable, List, Optional
from unittest.mock import AsyncMock, patch

import pytest

from camel.agents.chat_agent import (
    AsyncStreamingChatAgentResponse,
    ChatAgent,
)
from camel.messages.base import BaseMessage
from camel.responses import ChatAgentResponse
from camel.societies.workforce import Workforce
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.utils import TaskResult
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
        self,
        task: Task,
        dependencies: List[Task],
        stream_callback: Optional[
            Callable[["ChatAgentResponse"], Optional[Awaitable[None]]]
        ] = None,
    ) -> TaskState:
        """Always return failed task."""
        task.state = TaskState.FAILED
        task.result = "Task failed deliberately for testing"
        return TaskState.FAILED


class StreamingProbeWorker(SingleAgentWorker):
    """A worker that emits one artificial streaming chunk."""

    def __init__(self, description: str):
        sys_msg = BaseMessage.make_assistant_message(
            role_name="Streaming Probe",
            content="Emit one stream chunk.",
        )
        agent = ChatAgent(sys_msg)
        super().__init__(description, agent)

    async def _process_task(
        self,
        task: Task,
        dependencies: List[Task],
        stream_callback: Optional[
            Callable[["ChatAgentResponse"], Optional[Awaitable[None]]]
        ] = None,
    ) -> TaskState:
        chunk = ChatAgentResponse(
            msgs=[
                BaseMessage.make_assistant_message(
                    role_name="Assistant", content="partial"
                )
            ],
            terminated=False,
            info={"stream_accumulate_mode": "delta"},
        )
        if stream_callback:
            maybe = stream_callback(chunk)
            if maybe is not None:
                await maybe
        task.state = TaskState.DONE
        task.result = "ok"
        return TaskState.DONE


class _DummyChannel:
    async def return_task(self, task_id: str) -> None:
        self.last_task_id = task_id


async def _async_stream(chunks: List[ChatAgentResponse]):
    for chunk in chunks:
        yield chunk


def _make_stream_chunk(
    content: str,
    *,
    parsed: Optional[TaskResult] = None,
    info: Optional[dict] = None,
) -> ChatAgentResponse:
    message = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content=content,
    )
    message.parsed = parsed
    return ChatAgentResponse(
        msgs=[message],
        terminated=False,
        info=info or {},
    )


class FakeWorkerAgent:
    def __init__(self, response, agent_id: str = "worker-clone-1"):
        self.role_name = "Fake Worker Agent"
        self.agent_id = agent_id
        self._execution_context = {"stale": "value"}
        self.astep = AsyncMock(return_value=response)


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


@pytest.mark.asyncio
async def test_worker_forwards_stream_chunks_to_registered_callback():
    worker = StreamingProbeWorker("probe")
    worker.set_channel(_DummyChannel())
    received = []

    async def stream_handler(chunk, worker_id, task_id):
        received.append((worker_id, task_id, chunk.msg.content))

    worker.set_stream_callback(stream_handler)
    task = Task(content="test", id="task-stream")

    await worker._process_single_task(task)

    assert len(received) == 1
    worker_id, task_id, content = received[0]
    assert worker_id
    assert task_id == "task-stream"
    assert content == "partial"


@pytest.mark.asyncio
async def test_worker_stream_callback_exception_does_not_fail_task():
    worker = StreamingProbeWorker("probe")
    worker.set_channel(_DummyChannel())

    async def failing_stream_handler(chunk, worker_id, task_id):
        raise RuntimeError("stream push failed")

    worker.set_stream_callback(failing_stream_handler)
    task = Task(content="test", id="task-stream-fail-safe")

    await worker._process_single_task(task)

    assert task.state == TaskState.DONE
    assert task.result == "ok"


@pytest.mark.asyncio
async def test_workforce_stream_callback_accumulate_mode_emits_delta():
    chunks = []

    def on_stream(worker_id: str, task_id: str, text: str, mode: str):
        chunks.append((worker_id, task_id, text, mode))

    workforce = Workforce("stream test", stream_callback=on_stream)

    first_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate"},
    )
    second_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello world",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate"},
    )

    await workforce._on_worker_stream_chunk(first_chunk, "worker-1", "task-1")
    await workforce._on_worker_stream_chunk(second_chunk, "worker-1", "task-1")

    assert chunks == [
        ("worker-1", "task-1", "Hello", "accumulate"),
        ("worker-1", "task-1", " world", "accumulate"),
    ]


@pytest.mark.asyncio
async def test_single_agent_worker_normalizes_delta_stream_and_ctx():
    sys_msg = BaseMessage.make_assistant_message(
        role_name="programmer",
        content="You are a python programmer.",
    )
    base_agent = ChatAgent(sys_msg)
    worker = SingleAgentWorker(
        "agent1",
        base_agent,
        use_agent_pool=False,
        use_structured_output_handler=False,
    )

    chunks = [
        _make_stream_chunk(
            "Hel",
            info={
                "stream_accumulate_mode": "delta",
                "partial": True,
            },
        ),
        _make_stream_chunk(
            "lo",
            parsed=TaskResult(content="Task finished", failed=False),
            info={
                "usage": {"total_tokens": 12, "prompt_tokens": 5},
                "tool_calls": [{"name": "search"}],
                "stream_accumulate_mode": "delta",
            },
        ),
    ]
    fake_agent = FakeWorkerAgent(
        AsyncStreamingChatAgentResponse(_async_stream(chunks))
    )
    worker._get_worker_agent = AsyncMock(return_value=fake_agent)
    worker._return_worker_agent = AsyncMock()

    parent_task = Task(content="parent", id="parent-task")
    task = Task(content="child", id="task-1", parent=parent_task)

    state = await worker._process_task(task, [])

    assert state == TaskState.DONE
    assert task.result == "Task finished"
    assert task.additional_info is not None
    assert task.additional_info["execution_context"] == {
        "task_id": "task-1",
        "parent_task_id": "parent-task",
        "worker_node_id": worker.node_id,
        "worker_description": "agent1",
        "original_worker_id": worker.worker.agent_id,
        "borrowed_agent_id": "worker-clone-1",
        "agent_id": "worker-clone-1",
        "attempt": 1,
    }
    assert (
        fake_agent._execution_context
        == task.additional_info["execution_context"]
    )
    assert "stale" not in fake_agent._execution_context

    worker_attempt = task.additional_info["worker_attempts"][0]
    assert worker_attempt["attempt"] == 1
    assert (
        worker_attempt["execution_context"]
        == task.additional_info["execution_context"]
    )
    assert worker_attempt["response_content_summary"] == "Hello"
    assert worker_attempt["tool_call_count"] == 1
    assert worker_attempt["token_usage"] == {
        "total_tokens": 12,
        "prompt_tokens": 5,
    }
    assert task.additional_info["token_usage"] == {
        "total_tokens": 12,
        "prompt_tokens": 5,
    }


@pytest.mark.asyncio
async def test_single_agent_worker_attempt_counter_uses_existing_attempts():
    sys_msg = BaseMessage.make_assistant_message(
        role_name="programmer",
        content="You are a python programmer.",
    )
    base_agent = ChatAgent(sys_msg)
    worker = SingleAgentWorker(
        "agent1",
        base_agent,
        use_agent_pool=False,
        use_structured_output_handler=False,
    )

    final_message = BaseMessage.make_assistant_message(
        role_name="Assistant",
        content="Completed",
    )
    final_message.parsed = TaskResult(content="Completed", failed=False)
    response = ChatAgentResponse(
        msgs=[final_message],
        terminated=False,
        info={"usage": {"total_tokens": 7}, "tool_calls": []},
    )
    fake_agent = FakeWorkerAgent(response, agent_id="worker-clone-2")
    worker._get_worker_agent = AsyncMock(return_value=fake_agent)
    worker._return_worker_agent = AsyncMock()

    task = Task(
        content="follow up",
        id="task-2",
        additional_info={"worker_attempts": [{"attempt": 1}]},
    )

    state = await worker._process_task(task, [])

    assert state == TaskState.DONE
    assert task.additional_info is not None
    assert task.additional_info["execution_context"]["attempt"] == 2
    assert task.additional_info["execution_context"]["borrowed_agent_id"] == (
        "worker-clone-2"
    )
    assert task.additional_info["worker_attempts"][-1]["attempt"] == 2
    assert (
        task.additional_info["worker_attempts"][-1]["response_content_summary"]
        == "Completed"
    )
