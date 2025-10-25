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
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class WorkforceEventBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    event_type: Literal[
        "task_decomposed",
        "task_created",
        "task_assigned",
        "task_started",
        "task_completed",
        "task_failed",
        "worker_created",
        "worker_deleted",
        "queue_status",
        "all_tasks_completed",
    ]
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class WorkerCreatedEvent(WorkforceEventBase):
    event_type: Literal["worker_created"] = "worker_created"
    worker_id: str
    worker_type: str
    role: str


class WorkerDeletedEvent(WorkforceEventBase):
    event_type: Literal["worker_deleted"] = "worker_deleted"
    worker_id: str
    reason: Optional[str] = None


class TaskDecomposedEvent(WorkforceEventBase):
    event_type: Literal["task_decomposed"] = "task_decomposed"
    parent_task_id: str
    subtask_ids: List[str]


class TaskCreatedEvent(WorkforceEventBase):
    event_type: Literal["task_created"] = "task_created"
    task_id: str
    description: str
    parent_task_id: Optional[str] = None
    task_type: Optional[str] = None


class TaskAssignedEvent(WorkforceEventBase):
    event_type: Literal["task_assigned"] = "task_assigned"
    task_id: str
    worker_id: str
    queue_time_seconds: Optional[float] = None
    dependencies: Optional[List[str]] = None


class TaskStartedEvent(WorkforceEventBase):
    event_type: Literal["task_started"] = "task_started"
    task_id: str
    worker_id: str


class TaskCompletedEvent(WorkforceEventBase):
    event_type: Literal["task_completed"] = "task_completed"
    task_id: str
    worker_id: str
    result_summary: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    token_usage: Optional[Dict[str, int]] = None


class TaskFailedEvent(WorkforceEventBase):
    event_type: Literal["task_failed"] = "task_failed"
    task_id: str
    error_message: str
    worker_id: Optional[str] = None


class AllTasksCompletedEvent(WorkforceEventBase):
    event_type: Literal["all_tasks_completed"] = "all_tasks_completed"


class QueueStatusEvent(WorkforceEventBase):
    event_type: Literal["queue_status"] = "queue_status"
    queue_name: str
    length: int
    pending_task_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


WorkforceEvent = Union[
    TaskDecomposedEvent,
    TaskCreatedEvent,
    TaskAssignedEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    WorkerCreatedEvent,
    WorkerDeletedEvent,
    AllTasksCompletedEvent,
    QueueStatusEvent,
]
