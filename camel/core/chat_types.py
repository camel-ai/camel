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
# Copyright 2023-2024 @ CAMEL-AI.org
# SPDX-License-Identifier: Apache-2.0
"""Neutral chat abstractions and adapters for model payloads.

Phase 1 introduces Camel-native structures that mirror the semantics of the
existing OpenAI Chat Completions API so higher layers can reason about
messages, tool calls, and usage without depending on vendor-specific models.

Later phases will plug additional adapters (e.g. OpenAI Responses API) into
the same abstractions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Union

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
)
from openai.types.completion_usage import CompletionUsage

JsonDict = Dict[str, Any]
MessageContent = Optional[Union[str, List[JsonDict]]]


def _to_dict(obj: Any) -> JsonDict:
    """Attempt to convert a Pydantic model or generic object into a dict."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[call-arg]
    if isinstance(obj, dict):
        return obj
    # Fallback best-effort conversion
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


@dataclass
class CamelToolCall:
    """Camel representation of a tool call emitted by the model."""

    name: Optional[str]
    arguments: Optional[str]
    id: Optional[str] = None
    type: str = "function"
    raw: Any = None

    @classmethod
    def from_chat_completion(
        cls, tool_call: Union[ChatCompletionMessageToolCall, JsonDict]
    ) -> "CamelToolCall":
        data = _to_dict(tool_call)
        function_data = data.get("function") or {}
        return cls(
            name=function_data.get("name"),
            arguments=function_data.get("arguments"),
            id=data.get("id"),
            type=data.get("type", "function"),
            raw=tool_call,
        )


@dataclass
class CamelMessage:
    """Camel-neutral view of a single message (role + content + metadata)."""

    role: str
    content: MessageContent
    name: Optional[str] = None
    tool_calls: List[CamelToolCall] = field(default_factory=list)
    function_call: Optional[JsonDict] = None
    parsed: Optional[Any] = None
    raw: Any = None

    @classmethod
    def from_chat_completion(
        cls, message: Union[ChatCompletionMessage, JsonDict]
    ) -> "CamelMessage":
        data = _to_dict(message)
        role = data.get("role", "")
        content: MessageContent = data.get("content")
        tool_calls_param = data.get("tool_calls") or []
        tool_calls = [
            CamelToolCall.from_chat_completion(tool_call)
            for tool_call in tool_calls_param
        ]
        function_call = data.get("function_call")
        parsed = data.get("parsed")
        return cls(
            role=role,
            content=content,
            name=data.get("name"),
            tool_calls=tool_calls,
            function_call=function_call,
            parsed=parsed,
            raw=message,
        )

    def has_meaningful_content(self) -> bool:
        """Mirror legacy filtering: skip empty content without tool calls."""
        if self.tool_calls:
            return True
        if isinstance(self.content, str):
            return bool(self.content.strip())
        if isinstance(self.content, list):
            return len(self.content) > 0
        return False


@dataclass
class CamelUsage:
    """Normalized token usage data."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    raw: Any = None

    @classmethod
    def from_chat_completion(
        cls, usage: Optional[CompletionUsage]
    ) -> Optional["CamelUsage"]:
        if usage is None:
            return None
        data = _to_dict(usage)
        return cls(
            prompt_tokens=data.get("prompt_tokens"),
            completion_tokens=data.get("completion_tokens"),
            total_tokens=data.get("total_tokens"),
            raw=usage,
        )


@dataclass
class CamelModelResponse:
    """Camel-neutral wrapper of a full model response."""

    messages: List[CamelMessage] = field(default_factory=list)
    finish_reasons: List[str] = field(default_factory=list)
    usage: Optional[CamelUsage] = None
    response_id: Optional[str] = None
    raw: Any = None

    @classmethod
    def from_chat_completion(
        cls, response: ChatCompletion
    ) -> "CamelModelResponse":
        messages: List[CamelMessage] = []
        for choice in response.choices:
            message = CamelMessage.from_chat_completion(choice.message)
            if message.has_meaningful_content():
                messages.append(message)

        finish_reasons = [
            str(choice.finish_reason) for choice in response.choices
        ]

        usage = CamelUsage.from_chat_completion(response.usage)
        response_id = getattr(response, "id", None)

        return cls(
            messages=messages,
            finish_reasons=finish_reasons,
            usage=usage,
            response_id=response_id,
            raw=response,
        )

    @property
    def tool_calls(self) -> Iterable[CamelToolCall]:
        """Flatten tool calls across assistant messages."""
        for message in self.messages:
            for tool_call in message.tool_calls:
                yield tool_call
