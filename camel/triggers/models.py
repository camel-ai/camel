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
r"""Data models shared across the trigger framework.

The framework is intentionally generic: a *trigger* is any source that emits
:class:`TriggerEvent` objects over time (a schedule, an incoming webhook, a
file watcher, ...). Each concrete trigger type stores its type-specific
settings inside :attr:`TriggerSpec.config`, so the persistence layer and the
CRUD toolkit can stay agnostic to the trigger kind.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TriggerState(str, Enum):
    r"""Lifecycle state of a trigger.

    - ``ACTIVE``: the trigger is enabled and (if the manager is running) its
      source task is live.
    - ``PAUSED``: the trigger is disabled; its config is retained but it will
      not fire.
    - ``EXHAUSTED``: the trigger reached ``max_runs`` / ``until`` and will not
      fire again, but is kept for inspection until deleted.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    EXHAUSTED = "exhausted"


class TriggerSpec(BaseModel):
    r"""Persisted, type-agnostic description of a trigger.

    Args:
        id (str): Unique identifier (auto-generated UUID by default).
        name (str): Human-readable label supplied by the agent.
        type (str): Registered trigger type name, e.g. ``"schedule"`` or
            ``"webhook"``. Determines which :class:`~camel.triggers.base.
            BaseTrigger` subclass drives it.
        payload (str): The instruction injected into the session when the
            trigger fires. Becomes the task/message content.
        config (Dict[str, Any]): Type-specific settings, validated by the
            owning trigger class (e.g.
            ``{"kind": "cron", "expr": "0 9 * * 1-5"}`` for a schedule, or
            ``{"path": "/hooks/ci"}`` for a webhook).
        state (TriggerState): Current lifecycle state.
        run_count (int): Number of times the trigger has fired.
        max_runs (Optional[int]): Auto-exhaust after this many fires.
        until (Optional[datetime]): Auto-exhaust after this time (UTC).
        last_run (Optional[datetime]): Timestamp of the last fire.
        created_at (datetime): Creation timestamp (UTC).
        metadata (Dict[str, Any]): Free-form tags/notes.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str
    payload: str
    config: Dict[str, Any] = Field(default_factory=dict)
    state: TriggerState = TriggerState.ACTIVE
    run_count: int = 0
    max_runs: Optional[int] = None
    until: Optional[datetime] = None
    last_run: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def enabled(self) -> bool:
        r"""Whether the trigger is allowed to fire."""
        return self.state == TriggerState.ACTIVE

    def summary(self) -> Dict[str, Any]:
        r"""Compact dict for listing tools (omits verbose config)."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "state": self.state.value,
            "run_count": self.run_count,
            "max_runs": self.max_runs,
            "last_run": (self.last_run.isoformat() if self.last_run else None),
        }


class TriggerEvent(BaseModel):
    r"""A single firing of a trigger, handed to the delivery sink.

    Args:
        trigger_id (str): ID of the trigger that fired.
        trigger_name (str): Name of the trigger that fired.
        trigger_type (str): Type of the trigger that fired.
        payload (str): The instruction to act on (from
            :attr:`TriggerSpec.payload`).
        data (Dict[str, Any]): Optional structured data carried by the fire
            (e.g. a webhook request body).
        fired_at (datetime): When the trigger fired (UTC).
        run_count (int): The 1-based fire count for this event.
        idempotency_key (str): Stable key identifying this specific fire, used
            downstream as a task ID to dedupe replays/misfires.
    """

    trigger_id: str
    trigger_name: str
    trigger_type: str
    payload: str
    data: Dict[str, Any] = Field(default_factory=dict)
    fired_at: datetime = Field(default_factory=_utcnow)
    run_count: int = 0
    idempotency_key: str

    def to_task_content(self) -> str:
        r"""Render the event as task/message content.

        Appends a compact data block when structured data is present so the
        downstream agent can see, e.g., the webhook body.
        """
        if not self.data:
            return self.payload
        import json

        return (
            f"{self.payload}\n\n[trigger data]\n"
            f"{json.dumps(self.data, default=str, indent=2)}"
        )
