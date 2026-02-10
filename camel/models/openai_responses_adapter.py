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
import json
import time
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    Optional,
    Type,
)

from pydantic import BaseModel

from camel.types import ChatCompletion, ChatCompletionChunk


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _usage_to_openai(usage: Any) -> Optional[Dict[str, int]]:
    if not usage:
        return None
    input_tokens = int(_get(usage, "input_tokens", 0) or 0)
    output_tokens = int(_get(usage, "output_tokens", 0) or 0)
    total_tokens = int(
        _get(usage, "total_tokens", input_tokens + output_tokens)
    )
    return {
        "prompt_tokens": input_tokens,
        "completion_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _extract_text_from_message_item(item: Any) -> str:
    parts = _get(item, "content", []) or []
    text_parts = []
    for part in parts:
        if _get(part, "type") == "output_text":
            text_parts.append(_get(part, "text", "") or "")
    return "".join(text_parts)


def _extract_tool_call(item: Any) -> Dict[str, Any]:
    return {
        "id": _get(item, "call_id", "") or _get(item, "id", ""),
        "type": "function",
        "function": {
            "name": _get(item, "name", ""),
            "arguments": _get(item, "arguments", "") or "",
        },
    }


def _build_chat_completion_chunk(
    *,
    chunk_id: str,
    model: str,
    delta: Dict[str, Any],
    finish_reason: Optional[str] = None,
    usage: Optional[Dict[str, int]] = None,
) -> ChatCompletionChunk:
    return ChatCompletionChunk.construct(
        id=chunk_id,
        choices=[
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
        created=int(time.time()),
        model=model,
        object="chat.completion.chunk",
        usage=usage,
    )


def response_to_chat_completion(
    response: Any,
    model: str,
    response_format: Optional[Type[BaseModel]] = None,
) -> ChatCompletion:
    output_items = _get(response, "output", []) or []
    content = ""
    tool_calls = []

    for item in output_items:
        item_type = _get(item, "type")
        if item_type == "message":
            content += _extract_text_from_message_item(item)
        elif item_type == "function_call":
            tool_calls.append(_extract_tool_call(item))

    finish_reason = "tool_calls" if tool_calls else "stop"
    message: Dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls:
        message["tool_calls"] = tool_calls

    if response_format is not None and content:
        try:
            message["parsed"] = response_format.model_validate_json(content)
        except Exception:
            try:
                parsed_json = json.loads(content)
                message["parsed"] = response_format.model_validate(parsed_json)
            except Exception:
                pass

    return ChatCompletion.construct(
        id=_get(response, "id", f"chatcmpl-{int(time.time())}"),
        choices=[
            {
                "index": 0,
                "message": message,
                "finish_reason": finish_reason,
            }
        ],
        created=int(_get(response, "created_at", time.time())),
        model=model,
        object="chat.completion",
        usage=_usage_to_openai(_get(response, "usage")),
    )


def iter_response_events_to_chat_chunks(
    event_stream: Any,
    model: str,
    on_response_completed: Optional[Callable[[str], None]] = None,
) -> Generator[ChatCompletionChunk, None, None]:
    has_tool_call = False
    has_finish_reason = False
    response_id = ""
    usage: Optional[Dict[str, int]] = None
    tool_idx_map: Dict[int, int] = {}
    tool_meta_emitted: Dict[int, bool] = {}
    tool_args_delta_seen: Dict[int, bool] = {}

    for event in event_stream:
        event_type = _get(event, "type", "")
        chunk_id = ""

        if event_type in ("response.created", "response.in_progress"):
            resp = _get(event, "response")
            if resp:
                response_id = _get(resp, "id", response_id)
            continue

        if event_type == "response.output_text.delta":
            delta = _get(event, "delta", "") or ""
            chunk_id = _get(event, "item_id", response_id)
            if delta:
                yield _build_chat_completion_chunk(
                    chunk_id=chunk_id,
                    model=model,
                    delta={"content": delta},
                )
            continue

        # Tool call item can appear as added/done; handle both.
        if event_type in (
            "response.output_item.added",
            "response.output_item.done",
        ):
            item = _get(event, "item")
            if _get(item, "type") == "function_call":
                has_tool_call = True
                out_idx = int(_get(event, "output_index", 0))
                mapped_idx = tool_idx_map.setdefault(
                    out_idx, len(tool_idx_map)
                )
                # `added/done` may include full arguments, while separate
                # `...arguments.delta` events stream the same payload.
                # Avoid emitting duplicated arguments into ChatAgent
                # accumulation, otherwise JSON becomes invalid.
                if event_type == "response.output_item.added":
                    tc = {
                        "index": mapped_idx,
                        "id": _get(item, "call_id", "")
                        or _get(item, "id", ""),
                        "type": "function",
                        "function": {
                            "name": _get(item, "name", ""),
                            "arguments": "",
                        },
                    }
                    tool_meta_emitted[out_idx] = True
                    chunk_id = _get(item, "id", response_id)
                    yield _build_chat_completion_chunk(
                        chunk_id=chunk_id,
                        model=model,
                        delta={"tool_calls": [tc]},
                    )
                else:  # response.output_item.done
                    if not tool_args_delta_seen.get(out_idx, False):
                        tc = {
                            "index": mapped_idx,
                            "function": {
                                "arguments": _get(item, "arguments", "") or "",
                            },
                        }
                        if not tool_meta_emitted.get(out_idx, False):
                            tc["id"] = _get(item, "call_id", "") or _get(
                                item, "id", ""
                            )
                            tc["type"] = "function"
                            tc["function"]["name"] = _get(item, "name", "")
                        chunk_id = _get(item, "id", response_id)
                        yield _build_chat_completion_chunk(
                            chunk_id=chunk_id,
                            model=model,
                            delta={"tool_calls": [tc]},
                        )
            continue

        # Some SDKs emit function-call argument deltas with this name.
        if event_type in (
            "response.function_call_arguments.delta",
            "response.output_item.function_call_arguments.delta",
        ):
            has_tool_call = True
            out_idx = int(_get(event, "output_index", 0))
            mapped_idx = tool_idx_map.setdefault(out_idx, len(tool_idx_map))
            tool_args_delta_seen[out_idx] = True
            delta = _get(event, "delta", "") or ""
            tc = {
                "index": mapped_idx,
                "function": {"arguments": delta},
            }
            chunk_id = _get(event, "item_id", response_id)
            yield _build_chat_completion_chunk(
                chunk_id=chunk_id,
                model=model,
                delta={"tool_calls": [tc]},
            )
            continue

        if event_type == "response.completed":
            resp = _get(event, "response")
            if resp:
                response_id = _get(resp, "id", response_id)
                usage = _usage_to_openai(_get(resp, "usage"))
            if on_response_completed is not None and response_id:
                on_response_completed(response_id)
            finish_reason = "tool_calls" if has_tool_call else "stop"
            has_finish_reason = True
            yield _build_chat_completion_chunk(
                chunk_id=response_id,
                model=model,
                delta={},
                finish_reason=finish_reason,
                usage=usage,
            )
            continue

    # Safety fallback for abnormal stream termination.
    if not has_finish_reason:
        yield _build_chat_completion_chunk(
            chunk_id=response_id,
            model=model,
            delta={},
            finish_reason="stop",
            usage=usage,
        )


async def aiter_response_events_to_chat_chunks(
    event_stream: Any,
    model: str,
    on_response_completed: Optional[Callable[[str], None]] = None,
) -> AsyncGenerator[ChatCompletionChunk, None]:
    has_tool_call = False
    has_finish_reason = False
    response_id = ""
    usage: Optional[Dict[str, int]] = None
    tool_idx_map: Dict[int, int] = {}
    tool_meta_emitted: Dict[int, bool] = {}
    tool_args_delta_seen: Dict[int, bool] = {}

    async for event in event_stream:
        event_type = _get(event, "type", "")
        chunk_id = ""

        if event_type in ("response.created", "response.in_progress"):
            resp = _get(event, "response")
            if resp:
                response_id = _get(resp, "id", response_id)
            continue

        if event_type == "response.output_text.delta":
            delta = _get(event, "delta", "") or ""
            chunk_id = _get(event, "item_id", response_id)
            if delta:
                yield _build_chat_completion_chunk(
                    chunk_id=chunk_id,
                    model=model,
                    delta={"content": delta},
                )
            continue

        if event_type in (
            "response.output_item.added",
            "response.output_item.done",
        ):
            item = _get(event, "item")
            if _get(item, "type") == "function_call":
                has_tool_call = True
                out_idx = int(_get(event, "output_index", 0))
                mapped_idx = tool_idx_map.setdefault(
                    out_idx, len(tool_idx_map)
                )
                if event_type == "response.output_item.added":
                    tc = {
                        "index": mapped_idx,
                        "id": _get(item, "call_id", "")
                        or _get(item, "id", ""),
                        "type": "function",
                        "function": {
                            "name": _get(item, "name", ""),
                            "arguments": "",
                        },
                    }
                    tool_meta_emitted[out_idx] = True
                    chunk_id = _get(item, "id", response_id)
                    yield _build_chat_completion_chunk(
                        chunk_id=chunk_id,
                        model=model,
                        delta={"tool_calls": [tc]},
                    )
                else:
                    if not tool_args_delta_seen.get(out_idx, False):
                        tc = {
                            "index": mapped_idx,
                            "function": {
                                "arguments": _get(item, "arguments", "") or "",
                            },
                        }
                        if not tool_meta_emitted.get(out_idx, False):
                            tc["id"] = _get(item, "call_id", "") or _get(
                                item, "id", ""
                            )
                            tc["type"] = "function"
                            tc["function"]["name"] = _get(item, "name", "")
                        chunk_id = _get(item, "id", response_id)
                        yield _build_chat_completion_chunk(
                            chunk_id=chunk_id,
                            model=model,
                            delta={"tool_calls": [tc]},
                        )
            continue

        if event_type in (
            "response.function_call_arguments.delta",
            "response.output_item.function_call_arguments.delta",
        ):
            has_tool_call = True
            out_idx = int(_get(event, "output_index", 0))
            mapped_idx = tool_idx_map.setdefault(out_idx, len(tool_idx_map))
            tool_args_delta_seen[out_idx] = True
            delta = _get(event, "delta", "") or ""
            tc = {
                "index": mapped_idx,
                "function": {"arguments": delta},
            }
            chunk_id = _get(event, "item_id", response_id)
            yield _build_chat_completion_chunk(
                chunk_id=chunk_id,
                model=model,
                delta={"tool_calls": [tc]},
            )
            continue

        if event_type == "response.completed":
            resp = _get(event, "response")
            if resp:
                response_id = _get(resp, "id", response_id)
                usage = _usage_to_openai(_get(resp, "usage"))
            if on_response_completed is not None and response_id:
                on_response_completed(response_id)
            finish_reason = "tool_calls" if has_tool_call else "stop"
            has_finish_reason = True
            yield _build_chat_completion_chunk(
                chunk_id=response_id,
                model=model,
                delta={},
                finish_reason=finish_reason,
                usage=usage,
            )
            continue

    if not has_finish_reason:
        yield _build_chat_completion_chunk(
            chunk_id=response_id,
            model=model,
            delta={},
            finish_reason="stop",
            usage=usage,
        )
