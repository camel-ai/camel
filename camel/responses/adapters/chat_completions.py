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
"""Adapters for mapping OpenAI Chat Completions to CAMEL abstractions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from camel.messages.base import BaseMessage
from camel.responses.model_response import (
    CamelModelResponse,
    CamelToolCall,
    CamelUsage,
)
from camel.types import ChatCompletion, RoleType


def _choice_tool_calls_to_camel(
    choice_msg: Any,
) -> Optional[List[CamelToolCall]]:
    tool_calls = getattr(choice_msg, "tool_calls", None)
    if not tool_calls:
        return None
    result: List[CamelToolCall] = []
    for tc in tool_calls:
        func = getattr(tc, "function", None)
        name = getattr(func, "name", None) if func else None
        args_str = getattr(func, "arguments", "{}") if func else "{}"
        try:
            import json

            args = json.loads(args_str) if isinstance(args_str, str) else {}
        except Exception:
            args = {}
        result.append(
            CamelToolCall(id=getattr(tc, "id", ""), name=name or "", args=args)
        )
    return result


def adapt_chat_to_camel_response(
    response: ChatCompletion,
) -> CamelModelResponse:
    """Convert an OpenAI ChatCompletion into a CamelModelResponse.

    This performs the minimal mapping needed in Phase 1 and keeps the
    original response accessible via the `raw` field.
    """
    output_messages: List[BaseMessage] = []
    finish_reasons: List[str] = []
    tool_call_requests: Optional[List[CamelToolCall]] = None

    for _, choice in enumerate(response.choices):
        finish_reasons.append(str(choice.finish_reason))

        msg = choice.message
        # Skip empty (no content and no tool calls)
        if (
            getattr(msg, "content", None) is None
            or str(getattr(msg, "content", "")).strip() == ""
        ) and not getattr(msg, "tool_calls", None):
            continue

        bm = BaseMessage(
            role_name="assistant",
            role_type=RoleType.ASSISTANT,
            meta_dict={},
            content=getattr(msg, "content", "") or "",
            parsed=getattr(msg, "parsed", None),
        )
        output_messages.append(bm)

        # Collect tool calls from the first non-empty choice only
        # (align with existing usage)
        if tool_call_requests is None:
            tool_call_requests = _choice_tool_calls_to_camel(msg)

    usage_raw: Dict[str, Any] = {}
    usage_obj: Optional[Any] = getattr(response, "usage", None)
    if usage_obj is not None:
        try:
            # Pydantic model -> dict
            usage_raw = usage_obj.model_dump()  # type: ignore[no-any-return]
        except Exception:
            try:
                import dataclasses

                usage_raw = dataclasses.asdict(usage_obj)  # type: ignore[arg-type]
            except Exception:
                usage_raw = {}

    usage = CamelUsage(
        input_tokens=(usage_raw or {}).get("prompt_tokens"),
        output_tokens=(usage_raw or {}).get("completion_tokens"),
        total_tokens=(usage_raw or {}).get("total_tokens"),
        raw=usage_raw or None,
    )

    return CamelModelResponse(
        id=getattr(response, "id", ""),
        model=getattr(response, "model", None),
        created=getattr(response, "created", None),
        output_messages=output_messages,
        tool_call_requests=tool_call_requests,
        finish_reasons=finish_reasons,
        usage=usage,
        raw=response,
    )
