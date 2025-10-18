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
from typing import Any, Dict

import pytest

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce.events import (
    AllTasksCompletedEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDecomposedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    WorkerCreatedEvent,
    WorkerDeletedEvent,
    WorkforceEvent,
)
from camel.societies.workforce.workforce import Workforce
from camel.societies.workforce.workforce_callback import WorkforceCallback
from camel.societies.workforce.workforce_logger import WorkforceLogger
from camel.societies.workforce.workforce_metrics import WorkforceMetrics
from camel.tasks import Task
from camel.toolkits import SearchToolkit
from camel.types import ModelPlatformType, ModelType


class _NonMetricsCallback(WorkforceCallback):
    """A minimal callback implementation without metrics, for testing."""

    def __init__(self) -> None:
        self.events: list[WorkforceEvent] = []

    # Task events
    def log_task_created(self, event: TaskCreatedEvent) -> None:
        self.events.append(event)

    def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        self.events.append(event)

    def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        self.events.append(event)

    def log_task_started(self, event: TaskStartedEvent) -> None:
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


def assert_event_sequence(events: list[str], worker_count: int):
    """
    Validate that the given event sequence follows the expected logical order.
    """
    idx = 0
    n = len(events)

    # 1. Expect N WorkerCreatedEvent events first
    for _ in range(worker_count):
        assert idx < n, f"Missing WorkerCreatedEvent[{_}]"
        assert (
            events[idx] == "WorkerCreatedEvent"
        ), f"Event {idx} should be WorkerCreatedEvent, got {events[idx]}"
        idx += 1

    # 2. Expect one main TaskCreatedEvent
    assert (
        idx < n and events[idx] == "TaskCreatedEvent"
    ), f"Event {idx} should be TaskCreatedEvent"
    idx += 1

    # 3. Expect one TaskDecomposedEvent
    assert (
        idx < n and events[idx] == "TaskDecomposedEvent"
    ), f"Event {idx} should be TaskDecomposedEvent"
    idx += 1

    # 4. Expect a continuous sequence of child TaskCreatedEvent events
    sub_task_count = 0
    while idx < n and events[idx] == "TaskCreatedEvent":
        sub_task_count += 1
        idx += 1
    assert sub_task_count > 0, "No child TaskCreatedEvent detected"

    # 5. Expect the same number of consecutive TaskAssignedEvent events
    for i in range(sub_task_count):
        assert (
            idx < n and events[idx] == "TaskAssignedEvent"
        ), f"Event {idx} should be TaskAssignedEvent ({i+1}/{sub_task_count})"
        idx += 1

    # 6. Expect TaskStartedEvent and TaskCompletedEvent counts to match
    #    sub_task_count. Order between them is flexible, they just need to
    #    match in count.
    remaining_events = events[
        idx:-1
    ]  # the last one should be AllTasksCompletedEvent
    started_count = remaining_events.count("TaskStartedEvent")
    completed_count = (
        remaining_events.count("TaskCompletedEvent") - 1
    )  # exclude the main task TaskCompletedEvent
    assert (
        started_count == sub_task_count
    ), f"Expected {sub_task_count} TaskStartedEvent, got {started_count}"
    assert (
        completed_count == sub_task_count
    ), f"Expected {sub_task_count} TaskCompletedEvent, got {completed_count}"

    # Allow optional misc events (like TaskFailedEvent) in between
    allowed_misc = {
        "TaskFailedEvent",
        "TaskStartedEvent",
        "TaskCompletedEvent",
    }
    for e in remaining_events:
        assert e in allowed_misc, f"Unexpected event type: {e}"

    # 7. Expect the final event to be AllTasksCompletedEvent
    assert (
        events[-1] == "AllTasksCompletedEvent"
    ), "Last event should be AllTasksCompletedEvent"


def test_workforce_emits_expected_event_sequence():
    search_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Research Specialist",
            content="You are a research specialist who excels at finding and "
            "gathering information from the web.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
        tools=[SearchToolkit().search_wiki],
    )

    analyst_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Business Analyst",
            content="You are an expert business analyst. Your job is "
            "to analyze research findings, identify key insights, "
            "opportunities, and challenges.",
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
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
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
        ),
    )

    cb = _MetricsCallback()
    workforce = Workforce(
        'Business Analysis Team',
        graceful_shutdown_timeout=30.0,
        callbacks=[cb],
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
            "Conduct a comprehensive market analysis for launching a new "
            "electric scooter in Berlin. The analysis should cover: "
            "1. Current market size and key competitors. "
            "2. Target audience and their preferences. "
            "3. Local regulations and potential challenges. "
            "Finally, synthesize all findings into a summary report."
        ),
        id='0',
    )

    workforce.process_task(human_task)

    # test that the event sequence is as expected
    actual_events = [e.__class__.__name__ for e in cb.events]
    assert_event_sequence(actual_events, worker_count=3)

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
