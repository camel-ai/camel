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

import json
import tempfile
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from camel.societies.workforce.workforce_callback import WorkforceCallback


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class TranscriptEvent:
    event_type: str
    workforce_id: str
    timestamp: datetime = field(default_factory=_utc_now)
    task_id: str | None = None
    agent_id: str | None = None
    agent_name: str | None = None
    source: str = "camel"
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class TranscriptEventType:
    LOG = "log"
    USER_MESSAGE = "user_message"
    AGENT_PROMPT = "agent_prompt"
    AGENT_REPLY = "agent_reply"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    TASK_CREATED = "task_created"
    TASK_DECOMPOSED = "task_decomposed"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_UPDATED = "task_updated"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    WORKER_CREATED = "worker_created"
    WORKER_DELETED = "worker_deleted"
    NOTICE = "notice"
    HUMAN_QUESTION = "human_question"
    HUMAN_REPLY = "human_reply"
    ALL_TASKS_COMPLETED = "all_tasks_completed"


class TranscriptStore:
    """Append-only JSONL transcript store."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    @classmethod
    def create_temp(cls, workforce_id: str) -> "TranscriptStore":
        filename = f"workforce-{workforce_id}-{uuid.uuid4().hex[:8]}.jsonl"
        return cls(Path(tempfile.gettempdir()) / filename)

    def append(self, event: TranscriptEvent) -> dict[str, Any]:
        data = event.to_dict()
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(data, ensure_ascii=False))
                handle.write("\n")
        return data

    def read_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]


class WorkforceTranscriptCallback(WorkforceCallback):
    """Persists workforce lifecycle events into a transcript store."""

    def __init__(self, workforce_id: str, store: TranscriptStore):
        self.workforce_id = workforce_id
        self.store = store

    def _append(
        self,
        event_type: str,
        *,
        task_id: str | None = None,
        agent_id: str | None = None,
        agent_name: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self.store.append(
            TranscriptEvent(
                event_type=event_type,
                workforce_id=self.workforce_id,
                task_id=task_id,
                agent_id=agent_id,
                agent_name=agent_name,
                payload=payload or {},
            )
        )

    def log_message(self, event) -> None:
        self._append(
            TranscriptEventType.LOG,
            payload={"message": event.message, "level": event.level},
        )

    def log_task_created(self, event) -> None:
        self._append(
            TranscriptEventType.TASK_CREATED,
            task_id=event.task_id,
            payload={
                "description": event.description,
                "parent_task_id": event.parent_task_id,
                "task_type": event.task_type,
            },
        )

    def log_task_decomposed(self, event) -> None:
        self._append(
            TranscriptEventType.TASK_DECOMPOSED,
            task_id=event.parent_task_id,
            payload={"subtask_ids": event.subtask_ids},
        )

    def log_task_assigned(self, event) -> None:
        self._append(
            TranscriptEventType.TASK_ASSIGNED,
            task_id=event.task_id,
            agent_id=event.worker_id,
            payload={
                "queue_time_seconds": event.queue_time_seconds,
                "dependencies": event.dependencies or [],
            },
        )

    def log_task_started(self, event) -> None:
        self._append(
            TranscriptEventType.TASK_STARTED,
            task_id=event.task_id,
            agent_id=event.worker_id,
        )

    def log_task_updated(self, event) -> None:
        self._append(
            TranscriptEventType.TASK_UPDATED,
            task_id=event.task_id,
            agent_id=event.worker_id,
            payload={
                "update_type": event.update_type,
                "old_value": event.old_value,
                "new_value": event.new_value,
                "parent_task_id": event.parent_task_id,
                "metadata": event.metadata,
            },
        )

    def log_task_completed(self, event) -> None:
        self._append(
            TranscriptEventType.TASK_COMPLETED,
            task_id=event.task_id,
            agent_id=event.worker_id,
            payload={
                "parent_task_id": event.parent_task_id,
                "result_summary": event.result_summary,
                "processing_time_seconds": event.processing_time_seconds,
                "token_usage": event.token_usage,
            },
        )

    def log_task_failed(self, event) -> None:
        self._append(
            TranscriptEventType.TASK_FAILED,
            task_id=event.task_id,
            agent_id=event.worker_id,
            payload={
                "parent_task_id": event.parent_task_id,
                "error_message": event.error_message,
            },
        )

    def log_worker_created(self, event) -> None:
        self._append(
            TranscriptEventType.WORKER_CREATED,
            agent_id=event.worker_id,
            agent_name=event.role,
            payload={"worker_type": event.worker_type},
        )

    def log_worker_deleted(self, event) -> None:
        self._append(
            TranscriptEventType.WORKER_DELETED,
            agent_id=event.worker_id,
            payload={"reason": event.reason},
        )

    def log_all_tasks_completed(self, event) -> None:
        self._append(TranscriptEventType.ALL_TASKS_COMPLETED)
