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
)
from camel.societies.workforce.workforce import Workforce
from camel.societies.workforce.workforce_callback import WorkforceCallback
from camel.societies.workforce.workforce_logger import WorkforceLogger
from camel.societies.workforce.workforce_metrics import WorkforceMetrics
from camel.types import ModelPlatformType, ModelType


class _NonMetricsCallback(WorkforceCallback):
    """A minimal callback implementation without metrics, for testing."""

    def __init__(self) -> None:
        self.worker_created_called = 0

    # Task events
    def log_task_created(self, event: TaskCreatedEvent) -> None:
        pass

    def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        pass

    def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        pass

    def log_task_started(self, event: TaskStartedEvent) -> None:
        pass

    def log_task_completed(self, event: TaskCompletedEvent) -> None:
        pass

    def log_task_failed(self, event: TaskFailedEvent) -> None:
        pass

    # Worker events
    def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        self.worker_created_called += 1

    def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        pass

    # Terminal event
    def log_all_tasks_completed(self, event: AllTasksCompletedEvent) -> None:
        pass


class _MetricsCallback(WorkforceCallback, WorkforceMetrics):
    """A minimal metrics-capable callback for testing."""

    def __init__(self) -> None:
        self.reset_task_data()

    # WorkforceMetrics interface
    def reset_task_data(self) -> None:
        self.created = 0
        self.completed = 0
        self.failed = 0

    def dump_to_json(self, file_path: str) -> None:
        # Writes an empty JSON object to the specified file for
        # testing purposes.
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("{}")

    def get_ascii_tree_representation(self) -> str:
        return "test-tree"

    def get_kpis(self) -> Dict[str, Any]:
        return {
            "tasks_created": self.created,
            "tasks_completed": self.completed,
            "tasks_failed": self.failed,
        }

    # WorkforceCallback interface
    def log_task_created(self, event: TaskCreatedEvent) -> None:
        self.created += 1

    def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        pass

    def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        pass

    def log_task_started(self, event: TaskStartedEvent) -> None:
        pass

    def log_task_completed(self, event: TaskCompletedEvent) -> None:
        self.completed += 1

    def log_task_failed(self, event: TaskFailedEvent) -> None:
        self.failed += 1

    def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        pass

    def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        pass

    def log_all_tasks_completed(self, event: AllTasksCompletedEvent) -> None:
        pass


def _build_stub_agent() -> ChatAgent:
    """Construct a stub-backed ChatAgent for offline tests."""
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.STUB,
    )
    return ChatAgent(model=model)


def test_workforce_callbacks_default_and_metrics_behavior(tmp_path):
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
    assert cb.worker_created_called >= 1

    # 2) Metrics-capable callback present -> no default WorkforceLogger
    metrics_cb = _MetricsCallback()
    wf2 = Workforce("CB Test - With Metrics", callbacks=[metrics_cb])
    assert all(not isinstance(c, WorkforceLogger) for c in wf2._callbacks)
    # Also confirm that the metrics callback remains
    assert any(isinstance(c, _MetricsCallback) for c in wf2._callbacks)

    # 3) Invalid callback type -> ValueError
    with pytest.raises(ValueError, match="instances of WorkforceCallback"):
        Workforce("CB Test - Invalid", callbacks=[object()])
