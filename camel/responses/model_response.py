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
"""Unified response models used by CAMEL runtime.

These types are model-agnostic and can be populated from both legacy
Chat Completions and the newer OpenAI Responses API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from camel.messages.base import BaseMessage


class CamelToolCall(BaseModel):
    """Represents a single tool call request emitted by the model."""

    id: str
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


class CamelUsage(BaseModel):
    """Normalized usage counters with raw response attached for reference."""

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw: Optional[Dict[str, Any]] = None


class CamelModelResponse(BaseModel):
    """Unified model response returned by adapters/backends.

    Fields mirror the needs of ChatAgent and friends without exposing
    provider-specific schemas.
    """

    id: str
    model: Optional[str] = None
    created: Optional[int] = None

    output_messages: List[BaseMessage] = Field(default_factory=list)
    tool_call_requests: Optional[List[CamelToolCall]] = None
    finish_reasons: List[str] = Field(default_factory=list)
    usage: CamelUsage = Field(default_factory=CamelUsage)

    # Keep a handle to the original provider response for debugging/tests
    raw: Any = None
