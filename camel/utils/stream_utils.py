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
r"""Utilities for detecting and normalizing streaming chat responses."""

from __future__ import annotations

import asyncio
from types import GeneratorType
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Optional, Tuple

from camel.logger import get_logger

if TYPE_CHECKING:
    from camel.responses import ChatAgentResponse

logger = get_logger(__name__)


def _is_cumulative(contents: list[str]) -> bool:
    r"""Return whether each content piece grows from the previous one.

    This identifies cumulative streaming output, such as streams produced
    with ``stream_accumulate=True``. Delta streaming output should be
    concatenated instead.

    Args:
        contents (list[str]): Non-empty ``chunk.msg.content`` pieces
            collected from a streaming response.

    Returns:
        bool: Whether each later content string strictly grows in length and
            starts with the previous content string.
    """

    return all(
        len(contents[i + 1]) > len(contents[i])
        and contents[i + 1].startswith(contents[i])
        for i in range(len(contents) - 1)
    )


def _finalize_stream(
    contents: list[str], final_response: Optional[ChatAgentResponse]
) -> Tuple[ChatAgentResponse, str]:
    r"""Normalize collected stream chunks into a final response and content.

    Args:
        contents (list[str]): Message content pieces collected from the
            stream.
        final_response (Optional[ChatAgentResponse]): Last response chunk
            observed while consuming the stream.

    Returns:
        Tuple[ChatAgentResponse, str]: Final response object and assembled
            message content.
    """

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
    r"""Collect chunks from a synchronous streaming response.

    Args:
        response (Any): Iterable synchronous streaming response.
        stream_callback (Optional[Callable[[ChatAgentResponse], None]]):
            Optional callback executed for each observed chunk.

    Returns:
        Tuple[Optional[ChatAgentResponse], list[str]]: Last observed response
            chunk and the collected non-empty content pieces.
    """

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
    r"""Collect chunks from an asynchronous streaming response.

    Args:
        response (Any): Async or sync iterable streaming response.
        stream_callback (Optional[Callable[[ChatAgentResponse],
            Optional[Awaitable[None]]]]): Optional sync or async callback
            executed for each observed chunk.

    Returns:
        Tuple[Optional[ChatAgentResponse], list[str]]: Last observed response
            chunk and the collected non-empty content pieces.
    """

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
    r"""Return whether an object represents a streaming chat response.

    Args:
        response (Any): Object that may represent a chat response. Typically
            a :obj:`StreamingChatAgentResponse`, a generator of response
            chunks, or an iterable that does not expose a ``msg`` attribute.

    Returns:
        bool: Whether the object is detected as streaming according to the
            response heuristics.
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
    r"""Consume a synchronous response into final response and content.

    Args:
        response (Any): Complete :obj:`ChatAgentResponse` or streaming
            iterable of partial response chunks.
        stream_callback (Optional[Callable[[ChatAgentResponse], None]]):
            Optional callable executed for each chunk as it is produced.

    Returns:
        Tuple[Any, str]: Last chunk observed, or an empty
            :obj:`ChatAgentResponse` placeholder, and the assembled message
            content string.

    Raises:
        RuntimeError: If an async streaming response is consumed while an
            event loop is already running.
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
    r"""Consume an async-friendly response into final response and content.

    This variant handles :obj:`AsyncStreamingChatAgentResponse` objects with
    ``async for`` while keeping the same return contract as
    :func:`consume_response_content`.

    Args:
        response (Any): Complete :obj:`ChatAgentResponse`, synchronous
            streaming iterable, or asynchronous streaming response.
        stream_callback (Optional[Callable[[ChatAgentResponse],
            Optional[Awaitable[None]]]]): Optional sync or async callback
            executed for each observed chunk.

    Returns:
        Tuple[Any, str]: Last chunk observed, or an empty
            :obj:`ChatAgentResponse` placeholder, and the assembled message
            content string.
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
