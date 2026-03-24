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
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class AgentEventBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')
    event_type: Literal[
        "step_started",
        "step_completed",
        "step_failed",
        "tool_started",
        "tool_completed",
        "tool_failed",
    ]
    agent_id: str
    role_name: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class StepStartedEvent(AgentEventBase):
    event_type: Literal["step_started"] = "step_started"
    input_summary: str


class StepCompletedEvent(AgentEventBase):
    event_type: Literal["step_completed"] = "step_completed"
    output_summary: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class StepFailedEvent(AgentEventBase):
    event_type: Literal["step_failed"] = "step_failed"
    error_message: str


class ToolStartedEvent(AgentEventBase):
    event_type: Literal["tool_started"] = "tool_started"
    tool_name: str
    tool_call_id: str
    toolkit_name: Optional[str] = None
    input_summary: Optional[str] = None


class ToolCompletedEvent(AgentEventBase):
    event_type: Literal["tool_completed"] = "tool_completed"
    tool_name: str
    tool_call_id: str
    toolkit_name: Optional[str] = None
    output_summary: Optional[str] = None
    mask_output: bool = False


class ToolFailedEvent(AgentEventBase):
    event_type: Literal["tool_failed"] = "tool_failed"
    tool_name: str
    tool_call_id: str
    toolkit_name: Optional[str] = None
    error_message: str


AgentEvent = Union[
    StepStartedEvent,
    StepCompletedEvent,
    StepFailedEvent,
    ToolStartedEvent,
    ToolCompletedEvent,
    ToolFailedEvent,
]
