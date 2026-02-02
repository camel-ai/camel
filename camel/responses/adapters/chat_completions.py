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
"""Adapters for mapping OpenAI Chat Completions to CAMEL abstractions."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.responses.model_response import (
    CamelModelResponse,
    CamelToolCall,
    CamelUsage,
)
from camel.types import ChatCompletion, RoleType

logger = get_logger(__name__)


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute or dict item uniformly."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _json_loads_safe(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            import json

            return json.loads(val)
        except Exception as exc:
            snippet = val[:200] + "..." if len(val) > 200 else val
            logger.warning(
                "Failed to parse tool call arguments as JSON. Snippet=%s, error=%s",  # noqa:E501
                snippet,
                exc,
            )
            return {}
    if val is not None:
        logger.debug(
            "Unexpected type for tool call arguments: %s", type(val).__name__
        )
    return {}


def _choice_tool_calls_to_camel(
    choice_msg: Any,
) -> Optional[List[CamelToolCall]]:
    tool_calls = _get(choice_msg, "tool_calls", None)
    if not tool_calls:
        return None
    result: List[CamelToolCall] = []
    for tc in tool_calls:
        func = _get(tc, "function", None)
        # Prefer nested function fields; fall back to flat keys if present
        name = (
            _get(func, "name", None)
            if func is not None
            else _get(tc, "name", None)
        )
        args_src = (
            _get(func, "arguments", None)
            if func is not None
            else _get(tc, "arguments", None)
        )
        args = _json_loads_safe(args_src)
        call_id = _get(tc, "id", "")
        result.append(
            CamelToolCall(
                id=str(call_id or ""), name=str(name or ""), args=args
            )
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
    logprobs_list: List[Any] = []

    for _, choice in enumerate(response.choices):
        finish_reasons.append(str(choice.finish_reason))
        logprobs_list.append(getattr(choice, "logprobs", None))

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

    # Preserve logprobs if caller requested them
    logprobs: Optional[List[Any]] = (
        logprobs_list if any(lp is not None for lp in logprobs_list) else None
    )

    usage_raw: Dict[str, Any] = {}
    usage_obj: Optional[Any] = getattr(response, "usage", None)
    if usage_obj is not None:
        import dataclasses

        if hasattr(usage_obj, "model_dump"):
            try:
                usage_raw = usage_obj.model_dump()  # type: ignore[no-any-return]
            except Exception as exc:
                logger.warning("Failed to dump usage via model_dump: %s", exc)
        elif dataclasses.is_dataclass(usage_obj):
            try:
                usage_raw = dataclasses.asdict(usage_obj)  # type: ignore[arg-type]
            except Exception as exc:
                logger.warning(
                    "Failed to dump usage via dataclasses.asdict: %s", exc
                )
        elif isinstance(usage_obj, dict):
            usage_raw = dict(usage_obj)
        else:
            logger.debug(
                "Unsupported usage type: %s", type(usage_obj).__name__
            )

    usage_dict = usage_raw or {}
    usage = CamelUsage(
        input_tokens=usage_dict.get("prompt_tokens"),
        output_tokens=usage_dict.get("completion_tokens"),
        total_tokens=usage_dict.get("total_tokens"),
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
        logprobs=logprobs,
        raw=response,
    )
