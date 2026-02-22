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

import asyncio

import pytest

from camel.agents.chat_agent import (
    AsyncStreamingChatAgentResponse,
    StreamingChatAgentResponse,
)
from camel.messages import BaseMessage
from camel.responses import ChatAgentResponse
from camel.utils.stream_utils import (
    consume_response_content,
    consume_response_content_async,
    is_streaming_response,
)


def _make_chunk(content: str | None) -> ChatAgentResponse:
    if content is None:
        return ChatAgentResponse(msgs=[], terminated=False, info={})
    return ChatAgentResponse(
        msgs=[BaseMessage.make_assistant_message("assistant", content)],
        terminated=False,
        info={},
    )


def _sync_stream(chunks: list[ChatAgentResponse]):
    for chunk in chunks:
        yield chunk


async def _async_stream(chunks: list[ChatAgentResponse]):
    for chunk in chunks:
        yield chunk


class _IterableNoMsg:
    def __iter__(self):
        yield _make_chunk("x")


def test_is_streaming_response_for_standard_types():
    assert is_streaming_response(_sync_stream([_make_chunk("x")]))
    assert not is_streaming_response(_make_chunk("x"))
    assert not is_streaming_response("plain string")
    assert not is_streaming_response({"k": "v"})


def test_is_streaming_response_for_stream_wrappers_and_iterable():
    sync_wrapped = StreamingChatAgentResponse(_sync_stream([_make_chunk("x")]))
    async_wrapped = AsyncStreamingChatAgentResponse(
        _async_stream([_make_chunk("x")])
    )

    assert is_streaming_response(sync_wrapped)
    assert is_streaming_response(async_wrapped)
    assert is_streaming_response(_IterableNoMsg())


def test_consume_response_content_non_streaming_response():
    response = _make_chunk("final answer")

    final_response, content = consume_response_content(response)

    assert final_response is response
    assert content == "final answer"


def test_consume_response_content_single_chunk_stream():
    final_response, content = consume_response_content(
        _sync_stream([_make_chunk("hello")])
    )

    assert content == "hello"
    assert final_response.msg.content == "hello"


def test_consume_response_content_cumulative_stream_uses_last_piece():
    chunks = [_make_chunk("H"), _make_chunk("He"), _make_chunk("Hello")]

    final_response, content = consume_response_content(_sync_stream(chunks))

    assert final_response.msg.content == "Hello"
    assert content == "Hello"


def test_consume_response_content_delta_stream_concatenates():
    chunks = [_make_chunk("He"), _make_chunk("llo"), _make_chunk("!")]

    final_response, content = consume_response_content(_sync_stream(chunks))

    assert final_response.msg.content == "!"
    assert content == "Hello!"


def test_consume_response_content_empty_stream_returns_placeholder():
    final_response, content = consume_response_content(_sync_stream([]))

    assert isinstance(final_response, ChatAgentResponse)
    assert final_response.msgs == []
    assert final_response.terminated is False
    assert final_response.info == {}
    assert content == ""


def test_consume_response_content_callback_runs_for_every_chunk():
    chunks = [_make_chunk("a"), _make_chunk(None), _make_chunk("b")]
    seen = []

    def callback(chunk: ChatAgentResponse) -> None:
        seen.append(chunk)

    final_response, content = consume_response_content(
        _sync_stream(chunks), callback
    )

    assert len(seen) == 3
    assert final_response is chunks[-1]
    assert content == "ab"


def test_consume_response_content_callback_exception_is_swallowed(caplog):
    def bad_callback(_: ChatAgentResponse) -> None:
        raise RuntimeError("callback failed")

    final_response, content = consume_response_content(
        _sync_stream([_make_chunk("x")]), bad_callback
    )

    assert final_response.msg.content == "x"
    assert content == "x"
    assert (
        "stream_callback failed while processing a stream chunk" in caplog.text
    )


def test_consume_response_content_sync_consumes_async_stream_without_loop():
    async_wrapped = AsyncStreamingChatAgentResponse(
        _async_stream([_make_chunk("H"), _make_chunk("Hi")])
    )

    final_response, content = consume_response_content(async_wrapped)

    assert final_response.msg.content == "Hi"
    assert content == "Hi"


@pytest.mark.asyncio
async def test_consume_response_content_raises_for_async_stream_in_loop():
    async_wrapped = AsyncStreamingChatAgentResponse(
        _async_stream([_make_chunk("x")])
    )

    with pytest.raises(
        RuntimeError, match="use await consume_response_content_async"
    ):
        consume_response_content(async_wrapped)


@pytest.mark.asyncio
async def test_consume_response_content_async_non_streaming_response():
    response = _make_chunk("non streaming")

    final_response, content = await consume_response_content_async(response)

    assert final_response is response
    assert content == "non streaming"


@pytest.mark.asyncio
async def test_consume_response_content_async_with_sync_iterable_stream():
    chunks = [_make_chunk("foo"), _make_chunk("bar")]

    final_response, content = await consume_response_content_async(chunks)

    assert final_response is chunks[-1]
    assert content == "foobar"


@pytest.mark.asyncio
async def test_consume_response_content_async_with_async_stream_wrapper():
    async_wrapped = AsyncStreamingChatAgentResponse(
        _async_stream([_make_chunk("a"), _make_chunk("ab")])
    )

    final_response, content = await consume_response_content_async(
        async_wrapped
    )

    assert final_response.msg.content == "ab"
    assert content == "ab"


@pytest.mark.asyncio
async def test_consume_response_content_async_callback_runs_for_every_chunk():
    chunks = [_make_chunk("a"), _make_chunk(None), _make_chunk("b")]
    seen = []

    async def callback(chunk: ChatAgentResponse) -> None:
        await asyncio.sleep(0)
        seen.append(chunk)

    final_response, content = await consume_response_content_async(
        chunks, callback
    )

    assert len(seen) == 3
    assert final_response is chunks[-1]
    assert content == "ab"


@pytest.mark.asyncio
async def test_consume_response_content_async_callback_exception_is_swallowed(
    caplog,
):
    async def bad_callback(_: ChatAgentResponse) -> None:
        raise RuntimeError("callback failed")

    final_response, content = await consume_response_content_async(
        [_make_chunk("x")], bad_callback
    )

    assert final_response.msg.content == "x"
    assert content == "x"
    assert (
        "stream_callback failed while processing a stream chunk" in caplog.text
    )
