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
"""Utilities to detect and normalize streaming chat responses."""

from __future__ import annotations

import asyncio
from types import GeneratorType
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Tuple

from camel.logger import get_logger

if TYPE_CHECKING:
    from camel.responses import ChatAgentResponse

logger = get_logger(__name__)


def _is_cumulative(contents: list[str]) -> bool:
    """Return True if each string is a prefix of the next one.

    Streaming heuristic:
    - Gather non-empty ``chunk.msg.content`` pieces.
    - If each later piece starts with the previous, treat as cumulative
      (covers ``stream_accumulate=True``) and use the last piece.
    - Otherwise concatenate pieces in order (covers delta streaming).
    """

    return all(
        contents[i + 1].startswith(contents[i])
        for i in range(len(contents) - 1)
    )


def _finalize_stream(
    contents: list[str], final_response: Optional[ChatAgentResponse]
) -> Tuple[ChatAgentResponse, str]:
    """Normalize collected chunks into ``(final_response, content)``."""

    from camel.responses import (
        ChatAgentResponse,  # local import to avoid cycles
    )

    if final_response is None:
        final_response = ChatAgentResponse(msgs=[], terminated=False, info={})

    if not contents:
        return final_response, ""

    if len(contents) == 1:
        return final_response, contents[0]

    if _is_cumulative(contents):
        return final_response, contents[-1]

    return final_response, "".join(contents)


def _collect_sync_stream(
    response: Any,
    stream_callback: Optional[Callable[[ChatAgentResponse], None]] = None,
) -> Tuple[Optional[ChatAgentResponse], list[str]]:
    """Collect chunks from a sync streaming response."""

    final_response: Optional[ChatAgentResponse] = None
    contents: list[str] = []

    for chunk in response:
        final_response = chunk
        if stream_callback:
            try:
                stream_callback(chunk)
            except Exception:
                logger.warning(
                    "stream_callback failed while processing a stream chunk",
                    exc_info=True,
                )
        if getattr(chunk, "msg", None) and chunk.msg.content is not None:
            contents.append(chunk.msg.content)

    return final_response, contents


async def _collect_async_stream(
    response: Any,
    stream_callback: Optional[
        Callable[[ChatAgentResponse], Optional[Awaitable[None]]]
    ] = None,
) -> Tuple[Optional[ChatAgentResponse], list[str]]:
    """Collect chunks from an async streaming response."""

    final_response: Optional[ChatAgentResponse] = None
    contents: list[str] = []

    from camel.agents.chat_agent import AsyncStreamingChatAgentResponse

    async def _handle_chunk(chunk: Any) -> None:
        nonlocal final_response
        final_response = chunk
        if stream_callback:
            try:
                maybe = stream_callback(chunk)
                if asyncio.iscoroutine(maybe):
                    await maybe
            except Exception:
                logger.warning(
                    "stream_callback failed while processing a stream chunk",
                    exc_info=True,
                )
        if getattr(chunk, "msg", None) and chunk.msg.content is not None:
            contents.append(chunk.msg.content)

    if isinstance(response, AsyncStreamingChatAgentResponse):
        async for chunk in response:
            await _handle_chunk(chunk)
    else:
        for chunk in response:
            await _handle_chunk(chunk)

    return final_response, contents


def is_streaming_response(response: Any) -> bool:
    """Return True when the object represents a streaming sync response.

    Args:
        response: Any object that might represent a chat response. Typically
            a ``StreamingChatAgentResponse`` instance, a generator of
            response chunks, or any iterable that does not expose a
            ``msg`` attribute.

    Returns:
        bool: ``True`` if the object is detected as streaming according
        to the heuristics above, otherwise ``False``.
    """
    from camel.agents.chat_agent import (
        AsyncStreamingChatAgentResponse,
        StreamingChatAgentResponse,
    )

    non_streaming_iterables = (str, bytes, bytearray, dict)
    is_streaming = (
        isinstance(response, StreamingChatAgentResponse)
        or isinstance(response, AsyncStreamingChatAgentResponse)
        or isinstance(response, GeneratorType)
    )
    if (
        not is_streaming
        and hasattr(response, "__iter__")
        and not hasattr(response, "msg")
        and not isinstance(response, non_streaming_iterables)
    ):
        is_streaming = True

    return is_streaming


def consume_response_content(
    response: Any,
    stream_callback: Optional[Callable[[ChatAgentResponse], None]] = None,
) -> Tuple[Any, str]:
    """Consume a sync response (streaming or not) into final_response, content.

    Args:
        response: A complete ``ChatAgentResponse`` or a streaming
            iterable of partial responses/chunks.
        stream_callback: Optional callable executed for each chunk as it
            is produced. The callback receives the current chunk and is
            intended for side effects such as logging or UI updates.

    Returns:
        Tuple[Any, str]: The last chunk observed (or an empty
        ``ChatAgentResponse`` placeholder) and the assembled message
        content string derived from the streamed pieces.
    """
    from camel.agents.chat_agent import AsyncStreamingChatAgentResponse

    if isinstance(response, AsyncStreamingChatAgentResponse):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # No running loop; safely consume async stream synchronously.
            return asyncio.run(
                consume_response_content_async(response, stream_callback)
            )
        raise RuntimeError(
            "consume_response_content received an "
            "AsyncStreamingChatAgentResponse while an event loop is running; "
            "use await consume_response_content_async instead."
        )

    if not is_streaming_response(response):
        content = (
            response.msg.content if getattr(response, "msg", None) else ""
        )
        return response, content

    final_response, contents = _collect_sync_stream(response, stream_callback)
    return _finalize_stream(contents, final_response)


async def consume_response_content_async(
    response: Any,
    stream_callback: Optional[
        Callable[[ChatAgentResponse], Optional[Awaitable[None]]]
    ] = None,
) -> Tuple[Any, str]:
    """Async-friendly variant of :func:`consume_response_content`.

    This version handles ``AsyncStreamingChatAgentResponse`` objects using
    ``async for`` while retaining the same return contract.
    """

    if not is_streaming_response(response):
        content = (
            response.msg.content if getattr(response, "msg", None) else ""
        )
        return response, content

    final_response, contents = await _collect_async_stream(
        response, stream_callback
    )
    return _finalize_stream(contents, final_response)
