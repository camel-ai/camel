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
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class WorkforceEventBase(BaseModel):
    r"""Base class for all events emitted by the CAMEL workforce
    system.

    Attributes:
        event_type (str): The type of the event, used for
            discriminating between concrete event classes.
        metadata (Dict[str, Any], optional): A dictionary of additional
            key-value pairs with event-specific information. If not
            given, it will be :obj:`None`.
        timestamp (datetime): The UTC timestamp when the event was
            created. Defaults to the current time.
    """

    model_config = ConfigDict(frozen=True, extra='forbid')
    event_type: Literal[
        "log",
        "stream_chunk",
        "task_decomposed",
        "task_created",
        "task_assigned",
        "task_started",
        "task_updated",
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


class LogEvent(WorkforceEventBase):
    r"""Event for log messages emitted during workforce execution.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"log"`.
        message (str): The log message content.
        level (str): The severity level of the log message, one of
            :obj:`"debug"`, :obj:`"info"`, :obj:`"warning"`,
            :obj:`"error"`, or :obj:`"critical"`.
        color (str, optional): An optional color used when rendering
            the log message, e.g., :obj:`"red"` or :obj:`"cyan"`. If
            not given, it will be :obj:`None`.
    """

    event_type: Literal["log"] = "log"
    message: str
    level: Literal["debug", "info", "warning", "error", "critical"]
    color: (
        Literal[
            "red",
            "green",
            "yellow",
            "blue",
            "cyan",
            "magenta",
            "gray",
            "black",
        ]
        | None
    ) = None


class StreamChunkEvent(WorkforceEventBase):
    r"""Event carrying a chunk of streamed text output from a worker.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"stream_chunk"`.
        text (str): The chunk of streamed text.
        stream_accumulate_mode (str): The accumulation mode of the
            streamed chunks, e.g., :obj:`"accumulate"`.
        task_id (str, optional): The identifier of the task that
            produced this stream chunk. If not given, it will be
            :obj:`None`.
        worker_id (str, optional): The identifier of the worker that
            produced this stream chunk. If not given, it will be
            :obj:`None`.
    """

    event_type: Literal["stream_chunk"] = "stream_chunk"
    text: str
    stream_accumulate_mode: str = "accumulate"
    task_id: Optional[str] = None
    worker_id: Optional[str] = None


class WorkerCreatedEvent(WorkforceEventBase):
    r"""Event emitted when a new worker is added to the workforce.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"worker_created"`.
        worker_id (str): The identifier of the newly created worker.
        worker_type (str): The type of the created worker, e.g.,
            :obj:`"single_agent_worker"`.
        role (str): The role description of the worker.
    """

    event_type: Literal["worker_created"] = "worker_created"
    worker_id: str
    worker_type: str
    role: str


class WorkerDeletedEvent(WorkforceEventBase):
    r"""Event emitted when a worker is removed from the workforce.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"worker_deleted"`.
        worker_id (str): The identifier of the removed worker.
        reason (str, optional): The reason why the worker was
            removed. If not given, it will be :obj:`None`.
    """

    event_type: Literal["worker_deleted"] = "worker_deleted"
    worker_id: str
    reason: Optional[str] = None


class TaskDecomposedEvent(WorkforceEventBase):
    r"""Event emitted when a task is decomposed into subtasks.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"task_decomposed"`.
        parent_task_id (str): The identifier of the decomposed task.
        subtask_ids (List[str]): The identifiers of the created
            subtasks.
    """

    event_type: Literal["task_decomposed"] = "task_decomposed"
    parent_task_id: str
    subtask_ids: List[str]


class TaskCreatedEvent(WorkforceEventBase):
    r"""Event emitted when a new task is created in the workforce.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"task_created"`.
        task_id (str): The identifier of the created task.
        description (str): The description of the task.
        parent_task_id (str, optional): The identifier of the parent
            task if the task was created by decomposition. If not
            given, it will be :obj:`None`.
        task_type (str, optional): The type of the task. If not
            given, it will be :obj:`None`.
    """

    event_type: Literal["task_created"] = "task_created"
    task_id: str
    description: str
    parent_task_id: Optional[str] = None
    task_type: Optional[str] = None


class TaskAssignedEvent(WorkforceEventBase):
    r"""Event emitted when a task is assigned to a worker.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"task_assigned"`.
        task_id (str): The identifier of the assigned task.
        worker_id (str): The identifier of the worker the task was
            assigned to.
        queue_time_seconds (float, optional): The time the task spent
            waiting in the queue before assignment, in seconds. If
            not given, it will be :obj:`None`.
        dependencies (List[str], optional): The identifiers of the
            tasks this task depends on. If not given, it will be
            :obj:`None`.
    """

    event_type: Literal["task_assigned"] = "task_assigned"
    task_id: str
    worker_id: str
    queue_time_seconds: Optional[float] = None
    dependencies: Optional[List[str]] = None


class TaskStartedEvent(WorkforceEventBase):
    r"""Event emitted when a worker starts processing a task.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"task_started"`.
        task_id (str): The identifier of the task being started.
        worker_id (str): The identifier of the worker processing the
            task.
    """

    event_type: Literal["task_started"] = "task_started"
    task_id: str
    worker_id: str


class TaskUpdatedEvent(WorkforceEventBase):
    r"""Event emitted when a task is updated during execution.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"task_updated"`.
        task_id (str): The identifier of the updated task.
        worker_id (str, optional): The identifier of the worker
            handling the task. If not given, it will be :obj:`None`.
        update_type (str): The kind of update, one of
            :obj:`"replan"`, :obj:`"reassign"`, or :obj:`"manual"`.
        old_value (str, optional): The value before the update. If
            not given, it will be :obj:`None`.
        new_value (str, optional): The value after the update. If not
            given, it will be :obj:`None`.
        parent_task_id (str, optional): The identifier of the parent
            task. If not given, it will be :obj:`None`.
        metadata (Dict[str, Any], optional): A dictionary of
            additional key-value pairs with update details. If not
            given, it will be :obj:`None`.
    """

    event_type: Literal["task_updated"] = "task_updated"
    task_id: str
    worker_id: Optional[str] = None
    update_type: Literal["replan", "reassign", "manual"]
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    parent_task_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TaskCompletedEvent(WorkforceEventBase):
    r"""Event emitted when a task is completed successfully.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"task_completed"`.
        task_id (str): The identifier of the completed task.
        worker_id (str): The identifier of the worker that completed
            the task.
        parent_task_id (str, optional): The identifier of the parent
            task. If not given, it will be :obj:`None`.
        result_summary (str, optional): A summary of the task result.
            If not given, it will be :obj:`None`.
        processing_time_seconds (float, optional): The time taken to
            process the task, in seconds. If not given, it will be
            :obj:`None`.
        token_usage (Dict[str, int], optional): The token usage of
            the task processing. If not given, it will be
            :obj:`None`.
    """

    event_type: Literal["task_completed"] = "task_completed"
    task_id: str
    worker_id: str
    parent_task_id: Optional[str] = None
    result_summary: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    token_usage: Optional[Dict[str, int]] = None


class TaskFailedEvent(WorkforceEventBase):
    r"""Event emitted when a task fails during execution.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"task_failed"`.
        task_id (str): The identifier of the failed task.
        parent_task_id (str, optional): The identifier of the parent
            task. If not given, it will be :obj:`None`.
        error_message (str): The error message describing the
            failure.
        worker_id (str, optional): The identifier of the worker that
            was processing the task. If not given, it will be
            :obj:`None`.
    """

    event_type: Literal["task_failed"] = "task_failed"
    task_id: str
    parent_task_id: Optional[str] = None
    error_message: str
    worker_id: Optional[str] = None


class AllTasksCompletedEvent(WorkforceEventBase):
    r"""Event emitted when all tasks in the workforce are completed.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"all_tasks_completed"`.
    """

    event_type: Literal["all_tasks_completed"] = "all_tasks_completed"


class QueueStatusEvent(WorkforceEventBase):
    r"""Event reporting the current status of a task queue.

    Attributes:
        event_type (str): The type of the event, always
            :obj:`"queue_status"`.
        queue_name (str): The name of the queue.
        length (int): The current number of tasks in the queue.
        pending_task_ids (List[str], optional): The identifiers of
            the tasks currently pending in the queue. If not given,
            it will be :obj:`None`.
        metadata (Dict[str, Any], optional): A dictionary of
            additional key-value pairs with queue details. If not
            given, it will be :obj:`None`.
    """

    event_type: Literal["queue_status"] = "queue_status"
    queue_name: str
    length: int
    pending_task_ids: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


WorkforceEvent = Union[
    LogEvent,
    StreamChunkEvent,
    TaskDecomposedEvent,
    TaskCreatedEvent,
    TaskAssignedEvent,
    TaskStartedEvent,
    TaskUpdatedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    WorkerCreatedEvent,
    WorkerDeletedEvent,
    AllTasksCompletedEvent,
    QueueStatusEvent,
]
