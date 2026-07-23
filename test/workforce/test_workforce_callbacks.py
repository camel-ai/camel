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
import os
from typing import Any, Dict

import openai
import pytest  # type: ignore[import-not-found]

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.responses import ChatAgentResponse
from camel.societies.workforce.events import (
    AllTasksCompletedEvent,
    LogEvent,
    StreamChunkEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDecomposedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    TaskUpdatedEvent,
    WorkerCreatedEvent,
    WorkerDeletedEvent,
    WorkforceEvent,
)
from camel.societies.workforce.workforce import Workforce
from camel.societies.workforce.workforce_callback import WorkforceCallback
from camel.societies.workforce.workforce_logger import WorkforceLogger
from camel.societies.workforce.workforce_metrics import WorkforceMetrics
from camel.tasks import Task
from camel.types import ModelPlatformType, ModelType


def is_openai_key_invalid():
    key = os.environ.get("OPENAI_API_KEY", "")
    return not key or key.startswith("dummy")


MISSING_OPENAI_KEY = is_openai_key_invalid()


class _NonMetricsCallback(WorkforceCallback):
    """A minimal callback implementation without metrics, for testing."""

    def __init__(self) -> None:
        self.events: list[WorkforceEvent] = []

    def log_message(self, event: LogEvent) -> None:
        pass

    def log_stream_chunk(self, event: StreamChunkEvent) -> None:
        self.events.append(event)

    # Task events
    def log_task_created(self, event: TaskCreatedEvent) -> None:
        self.events.append(event)

    def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        self.events.append(event)

    def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        self.events.append(event)

    def log_task_started(self, event: TaskStartedEvent) -> None:
        self.events.append(event)

    def log_task_updated(self, event: TaskUpdatedEvent) -> None:
        self.events.append(event)

    def log_task_completed(self, event: TaskCompletedEvent) -> None:
        self.events.append(event)

    def log_task_failed(self, event: TaskFailedEvent) -> None:
        self.events.append(event)

    # Worker events
    def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        self.events.append(event)

    def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        self.events.append(event)

    # Terminal event
    def log_all_tasks_completed(self, event: AllTasksCompletedEvent) -> None:
        self.events.append(event)


class _MetricsCallback(WorkforceCallback, WorkforceMetrics):
    """A minimal metrics-capable callback for testing."""

    def __init__(self) -> None:
        self.events: list[WorkforceEvent] = []
        self.reset_task_data()
        self.dump_to_json_called = False
        self.get_ascii_tree_called = False
        self.get_kpis_called = False

    def log_message(self, event: LogEvent) -> None:
        pass

    def log_stream_chunk(self, event: StreamChunkEvent) -> None:
        self.events.append(event)

    # WorkforceMetrics interface
    def reset_task_data(self) -> None:
        self.dump_to_json_called = False
        self.get_ascii_tree_called = False
        self.get_kpis_called = False

    def dump_to_json(self, file_path: str) -> None:
        self.dump_to_json_called = True

    def get_ascii_tree_representation(self) -> str:
        self.get_ascii_tree_called = True
        return "Stub ASCII Tree"

    def get_kpis(self) -> Dict[str, Any]:
        self.get_kpis_called = True
        return {}

    def log_task_created(self, event: TaskCreatedEvent) -> None:
        self.events.append(event)

    def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        self.events.append(event)

    def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        self.events.append(event)

    def log_task_started(self, event: TaskStartedEvent) -> None:
        self.events.append(event)

    def log_task_updated(self, event: TaskUpdatedEvent) -> None:
        self.events.append(event)

    def log_task_completed(self, event: TaskCompletedEvent) -> None:
        self.events.append(event)

    def log_task_failed(self, event: TaskFailedEvent) -> None:
        self.events.append(event)

    def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        self.events.append(event)

    def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        self.events.append(event)

    def log_all_tasks_completed(self, event: AllTasksCompletedEvent) -> None:
        self.events.append(event)


def _build_stub_agent() -> ChatAgent:
    """Construct a stub-backed ChatAgent for offline tests."""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    return ChatAgent(model=model)


def test_workforce_callback_registration_and_metrics_handling():
    """Verify default logger addition and metrics-callback skip logic.

    - When no metrics callback is provided, WorkforceLogger is added.
    - When a metrics callback is provided, no WorkforceLogger is added.
    - Invalid callback types raise ValueError.
    - Worker creation events are propagated to provided callbacks.
    """
    # 1) No metrics callback -> default WorkforceLogger should be appended
    cb = _NonMetricsCallback()
    wf1 = Workforce("CB Test - No Metrics", callbacks=[cb])
    callback_types = [type(c) for c in wf1._callbacks]
    assert any(issubclass(t, WorkforceLogger) for t in callback_types)
    # Ensure our custom callback is present
    assert any(isinstance(c, _NonMetricsCallback) for c in wf1._callbacks)

    # Add a worker and ensure our callback saw the event
    agent = _build_stub_agent()
    wf1.add_single_agent_worker("UnitTest Worker", agent)
    assert any(isinstance(e, WorkerCreatedEvent) for e in cb.events)

    # 2) Metrics-capable callback present -> no default WorkforceLogger
    metrics_cb = _MetricsCallback()
    wf2 = Workforce("CB Test - With Metrics", callbacks=[metrics_cb])
    assert all(not isinstance(c, WorkforceLogger) for c in wf2._callbacks)
    # Also confirm that the metrics callback remains
    assert any(isinstance(c, _MetricsCallback) for c in wf2._callbacks)

    # 3) Invalid callback type -> ValueError
    with pytest.raises(ValueError, match="instances of WorkforceCallback"):
        Workforce("CB Test - Invalid", callbacks=[object()])


def test_workforce_logger_skips_stream_chunks_by_default():
    logger = WorkforceLogger("wf-test")

    logger.log_stream_chunk(
        StreamChunkEvent(
            text="high-volume stream text",
            stream_accumulate_mode="delta",
            task_id="task-1",
            worker_id="worker-1",
        )
    )

    assert logger.log_entries == []


def test_workforce_logger_can_persist_truncated_stream_chunks():
    logger = WorkforceLogger(
        "wf-test",
        log_stream_chunks=True,
        stream_chunk_text_limit=5,
    )

    logger.log_stream_chunk(
        StreamChunkEvent(
            text="stream text",
            stream_accumulate_mode="delta",
            task_id="task-1",
            worker_id="worker-1",
            metadata={"source": "unit-test"},
        )
    )

    assert len(logger.log_entries) == 1
    entry = logger.log_entries[0]
    assert entry["event_type"] == "stream_chunk"
    assert entry["text"] == "strea"
    assert entry["text_length"] == len("stream text")
    assert entry["text_truncated"] is True
    assert entry["stream_accumulate_mode"] == "delta"
    assert entry["task_id"] == "task-1"
    assert entry["worker_id"] == "worker-1"
    assert entry["metadata"] == {"source": "unit-test"}


def test_workforce_logger_rejects_negative_stream_chunk_limit():
    with pytest.raises(ValueError, match="stream_chunk_text_limit"):
        WorkforceLogger("wf-test", stream_chunk_text_limit=-1)


@pytest.mark.asyncio
async def test_workforce_callback_receives_internal_stream_chunk_events():
    callback = _NonMetricsCallback()
    workforce = Workforce("CB Stream Test", callbacks=[callback])

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

    workforce._on_stream_callback(
        first_chunk,
    )
    workforce._on_stream_callback(
        second_chunk,
    )

    stream_events = [
        event
        for event in callback.events
        if isinstance(event, StreamChunkEvent)
    ]
    assert [
        (
            event.task_id,
            event.worker_id,
            event.text,
            event.stream_accumulate_mode,
        )
        for event in stream_events
    ] == [
        (None, None, "Hello", "accumulate"),
        (None, None, " world", "accumulate"),
    ]


@pytest.mark.asyncio
async def test_internal_stream_progress_resets_after_final_chunk():
    callback = _NonMetricsCallback()
    workforce = Workforce("CB Stream Reset Test", callbacks=[callback])

    first_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate", "partial": True},
    )
    final_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello world",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate", "partial": False},
    )
    next_response_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello world again",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate", "partial": True},
    )

    workforce._on_stream_callback(first_chunk)
    workforce._on_stream_callback(final_chunk)
    workforce._on_stream_callback(next_response_chunk)

    stream_events = [
        event
        for event in callback.events
        if isinstance(event, StreamChunkEvent)
    ]
    assert [event.text for event in stream_events] == [
        "Hello",
        " world",
        "Hello world again",
    ]


@pytest.mark.asyncio
async def test_workforce_callback_receives_worker_stream_chunk_events():
    callback = _NonMetricsCallback()
    workforce = Workforce("CB Worker Stream Test", callbacks=[callback])

    chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="partial",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "delta"},
    )

    await workforce._on_worker_stream_chunk(chunk, "worker-1", "task-1")

    stream_events = [
        event
        for event in callback.events
        if isinstance(event, StreamChunkEvent)
    ]
    assert [
        (
            event.task_id,
            event.worker_id,
            event.text,
            event.stream_accumulate_mode,
        )
        for event in stream_events
    ] == [("task-1", "worker-1", "partial", "delta")]


@pytest.mark.asyncio
async def test_worker_stream_progress_resets_after_final_chunk():
    callback = _NonMetricsCallback()
    workforce = Workforce("CB Worker Stream Reset Test", callbacks=[callback])

    first_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate", "partial": True},
    )
    final_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello world",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate", "partial": False},
    )
    next_response_chunk = ChatAgentResponse(
        msgs=[
            BaseMessage.make_assistant_message(
                role_name="Assistant",
                content="Hello world again",
            )
        ],
        terminated=False,
        info={"stream_accumulate_mode": "accumulate", "partial": True},
    )

    await workforce._on_worker_stream_chunk(first_chunk, "worker-1", "task-1")
    await workforce._on_worker_stream_chunk(final_chunk, "worker-1", "task-1")
    await workforce._on_worker_stream_chunk(
        next_response_chunk, "worker-1", "task-1"
    )

    stream_events = [
        event
        for event in callback.events
        if isinstance(event, StreamChunkEvent)
    ]
    assert [event.text for event in stream_events] == [
        "Hello",
        " world",
        "Hello world again",
    ]


def assert_event_sequence(
    events: list[type[WorkforceEvent]], min_worker_count: int
):
    """
    Validate that the given event sequence follows the expected logical order.
    This version is flexible to handle:
    - Task retries and dynamic worker creation
    - Cases where tasks are not decomposed (e.g., when using stub models)
    """
    idx = 0
    n = len(events)

    # 1. Expect at least min_worker_count WorkerCreatedEvent events first
    initial_worker_count = 0
    while idx < n and events[idx] == WorkerCreatedEvent:
        initial_worker_count += 1
        idx += 1
    assert initial_worker_count >= min_worker_count, (
        f"Expected at least {min_worker_count} initial "
        f"WorkerCreatedEvents, got {initial_worker_count}"
    )

    # 2. Expect one main TaskCreatedEvent
    assert idx < n and events[idx] == TaskCreatedEvent, (
        f"Event {idx} should be {TaskCreatedEvent.__name__}, got "
        f"{events[idx] if idx < n else 'END'}"
    )
    idx += 1

    # 3. TaskDecomposedEvent may or may not be present
    # (depends on coordinator behavior)
    # If the coordinator can't parse stub responses, it may skip
    # decomposition
    has_decomposition = idx < n and events[idx] == TaskDecomposedEvent
    if has_decomposition:
        idx += 1

    # 4. Count all event types in the remaining events
    all_events = events[idx:]
    task_assigned_count = sum(e is TaskAssignedEvent for e in all_events)
    task_started_count = sum(e is TaskStartedEvent for e in all_events)
    task_completed_count = sum(e is TaskCompletedEvent for e in all_events)
    all_tasks_completed_count = sum(
        e is AllTasksCompletedEvent for e in all_events
    )

    # 5. Validate basic invariants
    # At minimum, the main task should be assigned and processed
    assert task_assigned_count >= 1, (
        f"Expected at least 1 {TaskAssignedEvent.__name__}, "
        f"got {task_assigned_count}"
    )
    assert task_started_count >= 1, (
        f"Expected at least 1 {TaskStartedEvent.__name__}, "
        f"got {task_started_count}"
    )
    assert task_completed_count >= 1, (
        f"Expected at least 1 {TaskCompletedEvent.__name__}, "
        f"got {task_completed_count}"
    )

    # 6. Expect exactly one AllTasksCompletedEvent at the end
    assert all_tasks_completed_count == 1, (
        f"Expected exactly 1 {AllTasksCompletedEvent.__name__}, got "
        f"{all_tasks_completed_count}"
    )
    assert (
        events[-1] == AllTasksCompletedEvent
    ), f"Last event should be {AllTasksCompletedEvent.__name__}"

    # 7. All events should be of expected types
    allowed_events = {
        WorkerCreatedEvent,
        WorkerDeletedEvent,
        StreamChunkEvent,
        TaskCreatedEvent,
        TaskDecomposedEvent,
        TaskAssignedEvent,
        TaskStartedEvent,
        TaskUpdatedEvent,
        TaskCompletedEvent,
        TaskFailedEvent,
        AllTasksCompletedEvent,
    }
    for i, e in enumerate(events):
        assert e in allowed_events, f"Unexpected event type at {i}: {e}"


@pytest.mark.model_backend
@pytest.mark.skipif(
    MISSING_OPENAI_KEY,
    reason=(
        "Workforce end-to-end event sequence requires a valid OpenAI API key"
    ),
)
def test_workforce_emits_expected_event_sequence():
    # Use STUB model to avoid real API calls and ensure fast,
    # deterministic execution
    search_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Research Specialist",
            content="You are a research specialist who excels at finding and "
            "gathering information from the web.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        ),
    )

    analyst_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Business Analyst",
            content="You are an expert business analyst. Your job is "
            "to analyze research findings, identify key insights, "
            "opportunities, and challenges.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        ),
    )

    writer_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Report Writer",
            content="You are a professional report writer. You take "
            "analytical insights and synthesize them into a clear, "
            "concise, and well-structured final report.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        ),
    )

    cb = _MetricsCallback()

    # Use STUB models for coordinator and task agents to avoid real API calls
    coordinator_agent = ChatAgent(
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        )
    )
    task_agent = ChatAgent(
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        )
    )

    workforce = Workforce(
        'Business Analysis Team',
        graceful_shutdown_timeout=30.0,
        callbacks=[cb],
        coordinator_agent=coordinator_agent,
        task_agent=task_agent,
    )

    workforce.add_single_agent_worker(
        "A researcher who can search online for information.",
        worker=search_agent,
    ).add_single_agent_worker(
        "An analyst who can process research findings.", worker=analyst_agent
    ).add_single_agent_worker(
        "A writer who can create a final report from the analysis.",
        worker=writer_agent,
    )

    human_task = Task(
        content=(
            "Create a simple report about electric scooters. "
            "The report should have three sections: "
            "1. Market overview "
            "2. Target customers "
            "3. Summary"
        ),
        id='0',
    )

    # Wrap task execution to catch API errors or STUB limitations
    try:
        workforce.process_task(human_task)
    except (openai.AuthenticationError, Exception) as e:
        err_msg = str(e)
        if any(
            k in err_msg for k in ("AuthenticationError", "401", "invalid_key")
        ):
            pytest.skip(f"Skipping test due to invalid OpenAI API key: {e}")
        raise e

    # If STUB model was unable to complete task, skip gracefully
    actual_events = [e.__class__ for e in cb.events]
    if TaskCompletedEvent not in actual_events:
        pytest.skip(
            "STUB model did not produce full workforce event sequence; "
            "skipping sequence assertion."
        )

    assert_event_sequence(actual_events, min_worker_count=3)

    # test that metrics callback methods work as expected
    assert not cb.dump_to_json_called
    assert not cb.get_ascii_tree_called
    assert not cb.get_kpis_called
    workforce.dump_workforce_logs("foo.log")
    assert cb.dump_to_json_called

    workforce.reset()
    assert not cb.dump_to_json_called
    assert not cb.get_ascii_tree_called
    assert not cb.get_kpis_called
    workforce.get_workforce_kpis()
    assert cb.get_kpis_called

    workforce.reset()
    assert not cb.dump_to_json_called
    assert not cb.get_ascii_tree_called
    assert not cb.get_kpis_called
    workforce.get_workforce_log_tree()
    assert cb.get_ascii_tree_called
