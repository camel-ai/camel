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
"""Helpers for converting OpenAI Responses API payloads into CAMEL types."""

from __future__ import annotations

import base64
import json
import time
from typing import Any, Dict, Iterator, List, Optional, Type

from openai.types.chat import ChatCompletionChunk
from openai.types.chat.chat_completion_chunk import (
    Choice,
    ChoiceDelta,
    ChoiceDeltaToolCall,
    ChoiceDeltaToolCallFunction,
)
from pydantic import BaseModel

from camel.messages.base import BaseMessage
from camel.responses.model_response import (
    CamelModelResponse,
    CamelToolCall,
    CamelUsage,
)
from camel.types import RoleType


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
            content = getattr(item, "content", None) or (
                item.get("content") if isinstance(item, dict) else None
            )
            if isinstance(content, list):
                for chunk in content:
                    chunk_type = None
                    if isinstance(chunk, dict):
                        chunk_type = chunk.get("type")

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
                                except Exception:
                                    pass
                            transcript = audio.get("transcript")
                            if transcript:
                                audio_transcript = transcript
                    elif chunk_type == "function_call":
                        pass

    # Check for tool calls in the output list directly
    tool_call_requests: List[CamelToolCall] = []
    if isinstance(output, list):
        for item in output:
            # Check if item is a tool call
            # The item might be an object or dict
            item_type = getattr(item, "type", None) or (
                item.get("type") if isinstance(item, dict) else None
            )

            if item_type == "function_call":
                call_id = getattr(item, "call_id", None) or (
                    item.get("call_id") if isinstance(item, dict) else None
                )
                name = getattr(item, "name", None) or (
                    item.get("name") if isinstance(item, dict) else None
                )
                arguments = getattr(item, "arguments", None) or (
                    item.get("arguments") if isinstance(item, dict) else None
                )

                if call_id and name:
                    args_dict = {}
                    if arguments:
                        try:
                            args_dict = json.loads(arguments)
                        except Exception:
                            pass

                    tool_call_requests.append(
                        CamelToolCall(id=call_id, name=name, args=args_dict)
                    )

    if not text:
        text = "\n".join(parts) if parts else ""

    parsed_obj = None
    if expected_parsed_type is not None:
        parsed_obj = getattr(resp, "output_parsed", None)
        if parsed_obj is None:
            parsed_obj = getattr(resp, "parsed", None)
        if parsed_obj is None:
            output = getattr(resp, "output", None)
            if isinstance(output, list) and output:
                first = output[0]
                parsed_obj = getattr(first, "parsed", None)
                if parsed_obj is None and isinstance(first, dict):
                    parsed_obj = first.get("parsed")
                if parsed_obj is None:
                    content = getattr(first, "content", None) or (
                        first.get("content")
                        if isinstance(first, dict)
                        else None
                    )
                    if isinstance(content, list) and content:
                        first_content = content[0]
                        if isinstance(first_content, dict):
                            parsed_obj = first_content.get("parsed")

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
                usage_raw = usage_obj.model_dump()  # type: ignore[no-any-return]
            elif isinstance(usage_obj, dict):
                usage_raw = dict(usage_obj)
    except Exception:
        usage_raw = None

    usage_dict = usage_raw or {}
    usage = CamelUsage(
        input_tokens=usage_dict.get("prompt_tokens"),
        output_tokens=usage_dict.get("completion_tokens"),
        total_tokens=usage_dict.get("total_tokens"),
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


def responses_stream_to_chunks(
    stream: Iterator[Any],
) -> Iterator[ChatCompletionChunk]:
    """Convert a Responses API stream into ChatCompletionChunk iterator.

    This allows existing streaming consumers (like ChatAgent) to consume
    Responses API streams without modification.
    """
    response_id = ""
    model = ""
    created = int(time.time())

    for chunk in stream:
        chunk_type = getattr(chunk, "type", None)

        # Update common fields if available
        if hasattr(chunk, "response"):
            resp = chunk.response
            if hasattr(resp, "id"):
                response_id = resp.id
            if hasattr(resp, "model"):
                model = resp.model
            if hasattr(resp, "created_at"):
                created = int(resp.created_at)

        if chunk_type == "response.output_item.added":
            item = getattr(chunk, "item", None)
            item_type = getattr(item, "type", None)
            output_index = getattr(chunk, "output_index", 0)

            if item_type == "function_call":
                # Start of a tool call
                call_id = getattr(item, "call_id", None)
                name = getattr(item, "name", None)

                tool_call = ChoiceDeltaToolCall(
                    index=output_index,  # Use output_index as tool_call index?
                    id=call_id,
                    type="function",
                    function=ChoiceDeltaToolCallFunction(
                        name=name, arguments=""
                    ),
                )

                yield ChatCompletionChunk(
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
            delta_arg = getattr(chunk, "delta", "")
            output_index = getattr(chunk, "output_index", 0)

            tool_call = ChoiceDeltaToolCall(
                index=output_index,
                function=ChoiceDeltaToolCallFunction(arguments=delta_arg),
            )

            yield ChatCompletionChunk(
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
            delta_text = getattr(chunk, "delta", "")

            yield ChatCompletionChunk(
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
            pass

        elif chunk_type == "response.completed":
            yield ChatCompletionChunk(
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
