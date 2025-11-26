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
from camel.societies.workforce import SingleAgentWorker
from camel.societies.workforce.base import BaseNode
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
from camel.types import ModelPlatformType, ModelType


class _NonMetricsCallback(WorkforceCallback):
    """A minimal callback implementation without metrics, for testing."""

    def __init__(self) -> None:
        self.events: list[WorkforceEvent] = []

    # Task events
    async def log_task_created(self, event: TaskCreatedEvent) -> None:
        self.events.append(event)

    async def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        self.events.append(event)

    async def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        self.events.append(event)

    async def log_task_started(self, event: TaskStartedEvent) -> None:
        self.events.append(event)

    async def log_task_completed(self, event: TaskCompletedEvent) -> None:
        self.events.append(event)

    async def log_task_failed(self, event: TaskFailedEvent) -> None:
        self.events.append(event)

    # Worker events
    async def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        self.events.append(event)

    async def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        self.events.append(event)

    # Terminal event
    async def log_all_tasks_completed(
        self, event: AllTasksCompletedEvent
    ) -> None:
        self.events.append(event)


class _MetricsCallback(WorkforceCallback, WorkforceMetrics):
    """A minimal metrics-capable callback for testing."""

    def __init__(self) -> None:
        self.events: list[WorkforceEvent] = []
        self.dump_to_json_called = False
        self.get_ascii_tree_called = False
        self.get_kpis_called = False

    # WorkforceMetrics interface
    async def reset_task_data(self) -> None:
        self.dump_to_json_called = False
        self.get_ascii_tree_called = False
        self.get_kpis_called = False

    async def dump_to_json(self, file_path: str) -> None:
        self.dump_to_json_called = True

    async def get_ascii_tree_representation(self) -> str:
        self.get_ascii_tree_called = True
        return "Stub ASCII Tree"

    async def get_kpis(self) -> Dict[str, Any]:
        self.get_kpis_called = True
        return {}

    async def log_task_created(self, event: TaskCreatedEvent) -> None:
        self.events.append(event)

    async def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        self.events.append(event)

    async def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        self.events.append(event)

    async def log_task_started(self, event: TaskStartedEvent) -> None:
        self.events.append(event)

    async def log_task_completed(self, event: TaskCompletedEvent) -> None:
        self.events.append(event)

    async def log_task_failed(self, event: TaskFailedEvent) -> None:
        self.events.append(event)

    async def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        self.events.append(event)

    async def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        self.events.append(event)

    async def log_all_tasks_completed(
        self, event: AllTasksCompletedEvent
    ) -> None:
        self.events.append(event)


def _build_stub_agent() -> ChatAgent:
    """Construct a stub-backed ChatAgent for offline tests."""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    return ChatAgent(model=model)


def _build_persona_agent(role_name: str, content: str) -> ChatAgent:
    """Construct a stub-backed ChatAgent with a system persona."""
    return ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name=role_name,
            content=content,
        ),
        model=ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI,
            model_type=ModelType.STUB,
        ),
    )


def _build_worker_specs() -> list[tuple[str, str, ChatAgent]]:
    """Build the standard trio of workers used across tests."""
    return [
        (
            "A researcher who can search online for information.",
            "SearchWork",
            _build_persona_agent(
                "Research Specialist",
                "You are a research specialist who excels at finding and "
                "gathering information from the web.",
            ),
        ),
        (
            "An analyst who can process research findings.",
            "AnalystWorker",
            _build_persona_agent(
                "Business Analyst",
                "You are an expert business analyst. Your job is "
                "to analyze research findings, identify key insights, "
                "opportunities, and challenges.",
            ),
        ),
        (
            "A writer who can create a final report from the analysis.",
            "WriterWorker",
            _build_persona_agent(
                "Report Writer",
                "You are a professional report writer. You take "
                "analytical insights and synthesize them into a clear, "
                "concise, and well-structured final report.",
            ),
        ),
    ]


async def _assert_metrics_callbacks(
    workforce: Workforce, cb: _MetricsCallback
):
    """Verify metrics callback toggles across reset cycles."""
    assert not cb.dump_to_json_called
    assert not cb.get_ascii_tree_called
    assert not cb.get_kpis_called
    await workforce.dump_workforce_logs_async("foo.log")
    assert cb.dump_to_json_called

    await workforce.reset_async()
    assert not cb.dump_to_json_called
    assert not cb.get_ascii_tree_called
    assert not cb.get_kpis_called
    await workforce.get_workforce_kpis_async()
    assert cb.get_kpis_called

    await workforce.reset_async()
    assert not cb.dump_to_json_called
    assert not cb.get_ascii_tree_called
    assert not cb.get_kpis_called
    await workforce.get_workforce_log_tree_async()
    assert cb.get_ascii_tree_called


@pytest.mark.asyncio
async def test_workforce_callback_registration_and_metrics_handling():
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
    await wf1.add_single_agent_worker_async("UnitTest Worker", agent)
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "preconfigure_children",
    [False, True],
    ids=["add_workers_at_runtime", "preconfigure_children"],
)
async def test_workforce_emits_expected_events_for_worker_init_modes(
    preconfigure_children: bool,
):
    """Validate event ordering for both worker setup paths."""
    cb = _MetricsCallback()
    coordinator_agent = _build_stub_agent()
    task_agent = _build_stub_agent()
    worker_specs = _build_worker_specs()

    if preconfigure_children:
        children: list[BaseNode] = [
            SingleAgentWorker(description=child_desc, worker=agent)
            for _, child_desc, agent in worker_specs
        ]
        workforce = Workforce(
            'Business Analysis Team',
            graceful_shutdown_timeout=30.0,
            callbacks=[cb],
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
            children=children,
        )
    else:
        workforce = Workforce(
            'Business Analysis Team',
            graceful_shutdown_timeout=30.0,
            callbacks=[cb],
            coordinator_agent=coordinator_agent,
            task_agent=task_agent,
        )
        for add_desc, _, agent in worker_specs:
            await workforce.add_single_agent_worker_async(
                add_desc,
                worker=agent,
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

    await workforce.process_task_async(human_task)

    expected_events = [
        "WorkerCreatedEvent",
        "WorkerCreatedEvent",
        "WorkerCreatedEvent",
        "TaskCreatedEvent",
        "WorkerCreatedEvent",
        "TaskAssignedEvent",
        "TaskStartedEvent",
        "TaskCompletedEvent",
        "AllTasksCompletedEvent",
    ]
    actual_events = [e.__class__.__name__ for e in cb.events]
    assert actual_events == expected_events

    await _assert_metrics_callbacks(workforce, cb)
