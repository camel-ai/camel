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
"""Helpers for converting OpenAI Responses API payloads into CAMEL types."""

from __future__ import annotations

import base64
import json
import time
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Type

from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import (
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)
from pydantic import BaseModel

from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.responses.model_response import (
    CamelModelResponse,
    CamelToolCall,
    CamelUsage,
)
from camel.types import RoleType

logger = get_logger(__name__)


def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute from object or dict uniformly.

    This helper handles the common pattern where an item can be either
    a Pydantic model (with attributes) or a plain dict. It first tries
    getattr, then falls back to dict.get if the object is a dict.

    Args:
        obj: The object to get the attribute from (can be object or dict).
        key: The attribute/key name to retrieve.
        default: Default value if attribute/key is not found.

    Returns:
        The attribute value, or default if not found.
    """
    val = getattr(obj, key, None)
    if val is not None:
        return val
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def responses_to_camel_response(
    resp: Any, expected_parsed_type: Optional[Type[BaseModel]] = None
) -> CamelModelResponse:
    r"""Map a Responses API object to :class:`CamelModelResponse`."""

    audio_bytes: Optional[bytes] = None
    audio_transcript: Optional[str] = None
    logprobs_list: List[Any] = []

    text = getattr(resp, "output_text", None)
    parts: List[str] = []
    output = getattr(resp, "output", None)
    if isinstance(output, list):
        for item in output:
            content = _get_attr(item, "content")
            if isinstance(content, list):
                for chunk in content:
                    chunk_type = _get_attr(chunk, "type")

                    if chunk_type in ("output_text", "text", "input_text"):
                        val = chunk.get("text") or chunk.get("output_text")
                        if val:
                            parts.append(str(val))
                        lp = (
                            chunk.get("logprobs")
                            if isinstance(chunk, dict)
                            else getattr(chunk, "logprobs", None)
                        )
                        if lp is not None:
                            logprobs_list.append(lp)
                    elif chunk_type == "output_audio":
                        audio = chunk.get("audio")
                        if isinstance(audio, dict):
                            b64_data = audio.get("data")
                            if b64_data:
                                try:
                                    audio_bytes = base64.b64decode(b64_data)
                                except Exception as e:
                                    logger.warning(
                                        "Failed to decode audio data from "
                                        "base64: %s. Audio data will be None.",
                                        e,
                                    )
                            transcript = audio.get("transcript")
                            if transcript:
                                audio_transcript = transcript
                    elif chunk_type == "function_call":
                        pass
                    elif chunk_type == "output_image":
                        image_url = chunk.get("image_url") or chunk.get("url")
                        if image_url:
                            parts.append(f"[image]: {image_url}")
                    elif chunk_type == "output_file":
                        file_url = (
                            chunk.get("file_url")
                            or chunk.get("url")
                            or chunk.get("file_id")
                        )
                        if file_url:
                            parts.append(f"[file]: {file_url}")

    # Check for tool calls in the output list directly
    tool_call_requests: List[CamelToolCall] = []
    if isinstance(output, list):
        for item in output:
            # Check if item is a tool call
            # The item might be an object or dict
            item_type = _get_attr(item, "type")

            if item_type == "function_call":
                call_id = _get_attr(item, "call_id")
                name = _get_attr(item, "name")
                arguments = _get_attr(item, "arguments")

                if call_id and name:
                    args_dict = {}
                    if arguments:
                        try:
                            args_dict = json.loads(arguments)
                        except Exception as e:
                            # Log warning with truncated arguments.
                            args_snippet = (
                                arguments[:200] + "..."
                                if len(arguments) > 200
                                else arguments
                            )
                            logger.warning(
                                "Failed to parse tool call arguments as JSON "
                                "for function '%s' (call_id=%s): %s. "
                                "Arguments snippet: %s",
                                name,
                                call_id,
                                e,
                                args_snippet,
                            )

                    tool_call_requests.append(
                        CamelToolCall(id=call_id, name=name, args=args_dict)
                    )

    if not text:
        text = "\n".join(parts) if parts else ""

    parsed_obj = None
    if expected_parsed_type is not None:
        parsed_obj = _get_attr(resp, "output_parsed")
        if parsed_obj is None:
            parsed_obj = _get_attr(resp, "parsed")
        if parsed_obj is None:
            output = _get_attr(resp, "output")
            if isinstance(output, list) and output:
                first = output[0]
                parsed_obj = _get_attr(first, "parsed")
                if parsed_obj is None:
                    content = _get_attr(first, "content")
                    if isinstance(content, list) and content:
                        first_content = content[0]
                        parsed_obj = _get_attr(first_content, "parsed")

    message = BaseMessage(
        role_name="assistant",
        role_type=RoleType.ASSISTANT,
        meta_dict={},
        content=text or "",
        audio_bytes=audio_bytes,
        audio_transcript=audio_transcript,
        parsed=parsed_obj if isinstance(parsed_obj, BaseModel) else None,
    )

    if tool_call_requests:
        # OpenAI message format for tool_calls
        openai_tool_calls = []
        for tc in tool_call_requests:
            openai_tool_calls.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.args),
                    },
                }
            )
        if message.meta_dict is None:
            message.meta_dict = {}
        message.meta_dict["tool_calls"] = openai_tool_calls

    usage_raw: Optional[Dict[str, Any]] = None
    usage_obj = getattr(resp, "usage", None)
    try:
        if usage_obj is not None:
            if hasattr(usage_obj, "model_dump"):
                usage_raw = (
                    usage_obj.model_dump()  # type: ignore[no-any-return]
                )
            elif isinstance(usage_obj, dict):
                usage_raw = dict(usage_obj)
    except Exception as e:
        logger.warning(
            "Failed to extract usage information from response: %s. "
            "Usage data will be None.",
            e,
        )
        usage_raw = None

    usage_dict = usage_raw or {}
    input_tokens = usage_dict.get("input_tokens")
    if input_tokens is None:
        input_tokens = usage_dict.get("prompt_tokens")

    output_tokens = usage_dict.get("output_tokens")
    if output_tokens is None:
        output_tokens = usage_dict.get("completion_tokens")

    total_tokens = usage_dict.get("total_tokens")
    if total_tokens is None and input_tokens is not None:
        if output_tokens is not None:
            total_tokens = input_tokens + output_tokens

    usage = CamelUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        raw=usage_raw or None,
    )
    logprobs: Optional[List[Any]] = logprobs_list if logprobs_list else None

    return CamelModelResponse(
        id=getattr(resp, "id", ""),
        model=getattr(resp, "model", None),
        created=getattr(resp, "created", None),
        output_messages=[message],
        tool_call_requests=tool_call_requests if tool_call_requests else None,
        finish_reasons=["stop"],
        usage=usage,
        logprobs=logprobs,
        raw=resp,
    )


def _process_stream_chunk(
    chunk: Any,
    response_id: str,
    model: str,
    created: int,
) -> tuple[Optional[ChatCompletionChunk], str, str, int]:
    """Process a single stream chunk and return the result.

    This helper extracts the common logic for processing Responses API
    stream chunks, used by both sync and async stream processors.

    Args:
        chunk: The stream chunk to process.
        response_id: Current response ID.
        model: Current model name.
        created: Current created timestamp.

    Returns:
        A tuple of (
            chunk_result,
            updated_response_id,
            updated_model,
            updated_created,
        ).
        chunk_result is None if no ChatCompletionChunk should be yielded.
    """
    chunk_type = _get_attr(chunk, "type")

    # Update common fields if available
    resp = _get_attr(chunk, "response")
    if resp is not None:
        resp_id = _get_attr(resp, "id")
        if resp_id:
            response_id = resp_id
        resp_model = _get_attr(resp, "model")
        if resp_model:
            model = resp_model
        resp_created = _get_attr(resp, "created_at")
        if resp_created:
            created = int(resp_created)

    result: Optional[ChatCompletionChunk] = None

    if chunk_type == "response.output_item.added":
        item = _get_attr(chunk, "item")
        item_type = _get_attr(item, "type")
        output_index = _get_attr(chunk, "output_index", 0)

        if item_type == "function_call":
            call_id = _get_attr(item, "call_id")
            name = _get_attr(item, "name")

            tool_call = ChoiceDeltaToolCall(
                index=output_index,
                id=call_id,
                type="function",
                function=ChoiceDeltaToolCallFunction(name=name, arguments=""),
            )

            result = ChatCompletionChunk(
                id=response_id,
                choices=[
                    Choice(
                        delta=ChoiceDelta(tool_calls=[tool_call]),
                        finish_reason=None,
                        index=0,
                        logprobs=None,
                    )
                ],
                created=created,
                model=model,
                object="chat.completion.chunk",
            )

    elif chunk_type == "response.function_call_arguments.delta":
        delta_arg = _get_attr(chunk, "delta", "")
        output_index = _get_attr(chunk, "output_index", 0)

        tool_call = ChoiceDeltaToolCall(
            index=output_index,
            function=ChoiceDeltaToolCallFunction(arguments=delta_arg),
        )

        result = ChatCompletionChunk(
            id=response_id,
            choices=[
                Choice(
                    delta=ChoiceDelta(tool_calls=[tool_call]),
                    finish_reason=None,
                    index=0,
                    logprobs=None,
                )
            ],
            created=created,
            model=model,
            object="chat.completion.chunk",
        )

    elif chunk_type == "response.output_text.delta":
        delta_text = _get_attr(chunk, "delta", "")

        result = ChatCompletionChunk(
            id=response_id,
            choices=[
                Choice(
                    delta=ChoiceDelta(content=delta_text),
                    finish_reason=None,
                    index=0,
                    logprobs=None,
                )
            ],
            created=created,
            model=model,
            object="chat.completion.chunk",
        )

    elif chunk_type == "response.output_item.done":
        pass  # No output needed

    elif chunk_type == "response.completed":
        result = ChatCompletionChunk(
            id=response_id,
            choices=[
                Choice(
                    delta=ChoiceDelta(),
                    finish_reason="stop",
                    index=0,
                    logprobs=None,
                )
            ],
            created=created,
            model=model,
            object="chat.completion.chunk",
        )

    return result, response_id, model, created


def responses_stream_to_chunks(
    stream: Iterator[Any],
) -> Iterator[ChatCompletionChunk]:
    """Convert a Responses API stream into ChatCompletionChunk iterator.

    This allows existing streaming consumers (like ChatAgent) to consume
    Responses API streams without modification.

    Args:
        stream: Synchronous iterator of Responses API stream chunks.

    Yields:
        ChatCompletionChunk objects compatible with existing streaming
        consumers.
    """
    response_id = ""
    model = ""
    created = int(time.time())

    for chunk in stream:
        result, response_id, model, created = _process_stream_chunk(
            chunk, response_id, model, created
        )
        if result is not None:
            yield result


async def async_responses_stream_to_chunks(
    stream: AsyncIterator[Any],
) -> AsyncIterator[ChatCompletionChunk]:
    """Convert an async Responses API stream into async
    ChatCompletionChunk iterator.

    This is the async version of responses_stream_to_chunks, for use with
    async streaming consumers.

    Args:
        stream: Asynchronous iterator of Responses API stream chunks.

    Yields:
        ChatCompletionChunk objects compatible with existing streaming
        consumers.
    """
    response_id = ""
    model = ""
    created = int(time.time())

    async for chunk in stream:
        result, response_id, model, created = _process_stream_chunk(
            chunk, response_id, model, created
        )
        if result is not None:
            yield result
