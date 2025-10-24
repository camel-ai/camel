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
# Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from openai.types.responses import (
    ParsedResponse,
    Response,
    ResponseCompletedEvent,
    ResponseContentPartAddedEvent,
    ResponseFunctionCallArgumentsDeltaEvent,
    ResponseFunctionToolCall,
    ResponseOutputItemAddedEvent,
    ResponseOutputMessage,
    ResponseOutputText,
    ResponseTextDeltaEvent,
    ResponseUsage,
    response_usage,
)
from pydantic import BaseModel

from camel.core import CamelStreamChunk
from camel.models.openai_responses_model import (
    _messages_to_response_input,
    _response_to_camel,
    _ResponsesStreamManagerAdapter,
)


def _make_usage() -> ResponseUsage:
    return ResponseUsage.construct(
        input_tokens=5,
        output_tokens=10,
        total_tokens=15,
        input_tokens_details=response_usage.InputTokensDetails.construct(
            cached_tokens=0
        ),
        output_tokens_details=response_usage.OutputTokensDetails.construct(
            reasoning_tokens=0
        ),
    )


def test_messages_to_response_input_converts_strings():
    messages = [
        {"role": "system", "content": "You are a helper."},
        {"role": "user", "content": "Hello"},
    ]
    converted = _messages_to_response_input(messages)
    assert converted == [
        {
            "role": "system",
            "content": [{"type": "input_text", "text": "You are a helper."}],
        },
        {
            "role": "user",
            "content": [{"type": "input_text", "text": "Hello"}],
        },
    ]


def test_response_to_camel_builds_message_and_usage():
    response = Response.construct(
        id="resp_1",
        created_at=0,
        model="gpt-4.1",
        object="response",
        status="completed",
        output=[
            ResponseOutputMessage.construct(
                id="msg_1",
                role="assistant",
                status="completed",
                type="message",
                content=[
                    ResponseOutputText.construct(
                        type="output_text",
                        text="Hello world",
                        annotations=[],
                        logprobs=None,
                    )
                ],
            )
        ],
        usage=_make_usage(),
    )

    camel_response = _response_to_camel(response)
    assert camel_response.response_id == "resp_1"
    assert camel_response.finish_reasons == ["completed"]
    assert camel_response.messages[0].content == "Hello world"
    assert camel_response.usage and camel_response.usage.total_tokens == 15


def test_response_to_camel_attaches_tool_calls():
    response = Response.construct(
        id="resp_2",
        created_at=0,
        model="gpt-4.1",
        object="response",
        status="completed",
        output=[
            ResponseOutputMessage.construct(
                id="msg_2",
                role="assistant",
                status="completed",
                type="message",
                content=[
                    ResponseOutputText.construct(
                        type="output_text",
                        text="Calling tool",
                        annotations=[],
                        logprobs=None,
                    )
                ],
            ),
            ResponseFunctionToolCall.construct(
                id="tool_1",
                call_id="tool_1",
                type="function_call",
                name="add",
                arguments='{"x":1,"y":2}',
                status="completed",
            ),
        ],
        usage=_make_usage(),
    )

    camel_response = _response_to_camel(response)
    tool_calls = list(camel_response.tool_calls)
    assert len(tool_calls) == 1
    assert tool_calls[0].name == "add"
    assert tool_calls[0].arguments == '{"x":1,"y":2}'
    assert camel_response.messages[0].tool_calls == tool_calls


class _DummyStream:
    def __init__(self, events, final_response):
        self._events = iter(events)
        self._final_response = final_response

    def __iter__(self):
        for event in self._events:
            yield event

    def get_final_response(self):
        return self._final_response


class _DummyManager:
    def __init__(self, stream):
        self._stream = stream

    def __enter__(self):
        return self._stream

    def __exit__(self, exc_type, exc, exc_tb):
        return False


class StructuredResult(BaseModel):
    summary: str


def test_responses_stream_adapter_emits_chunks_and_final_response():
    message_item = ResponseOutputMessage.construct(
        id="msg_1",
        role="assistant",
        type="message",
        content=[],
        status="in_progress",
    )

    text_part = ResponseOutputText.construct(
        type="output_text",
        text="",
        annotations=[],
    )

    tool_item = ResponseFunctionToolCall.construct(
        type="function_call",
        name="add",
        call_id="tool_1",
        id="tool_1",
        arguments="",
        status="in_progress",
    )

    events = [
        ResponseOutputItemAddedEvent.construct(
            type="response.output_item.added",
            output_index=0,
            sequence_number=0,
            item=message_item,
        ),
        ResponseContentPartAddedEvent.construct(
            type="response.content_part.added",
            output_index=0,
            content_index=0,
            item_id="msg_1",
            sequence_number=1,
            part=text_part,
        ),
        ResponseTextDeltaEvent.construct(
            type="response.output_text.delta",
            output_index=0,
            content_index=0,
            sequence_number=2,
            item_id="msg_1",
            delta="Hello",
            logprobs=[],
            snapshot="Hello",
        ),
        ResponseOutputItemAddedEvent.construct(
            type="response.output_item.added",
            output_index=1,
            sequence_number=3,
            item=tool_item,
        ),
        ResponseFunctionCallArgumentsDeltaEvent.construct(
            type="response.function_call_arguments.delta",
            output_index=1,
            sequence_number=4,
            item_id="tool_1",
            delta='{"x":1',
            snapshot='{"x":1',
        ),
        ResponseFunctionCallArgumentsDeltaEvent.construct(
            type="response.function_call_arguments.delta",
            output_index=1,
            sequence_number=5,
            item_id="tool_1",
            delta=',"y":2}',
            snapshot='{"x":1,"y":2}',
        ),
    ]

    final_response = Response.construct(
        id="resp_final",
        created_at=0,
        model="gpt-4.1",
        object="response",
        status="completed",
        output=[
            ResponseOutputMessage.construct(
                id="msg_final",
                role="assistant",
                type="message",
                status="completed",
                content=[
                    ResponseOutputText.construct(
                        type="output_text",
                        text='{"summary":"done"}',
                        annotations=[],
                    )
                ],
            ),
            ResponseFunctionToolCall.construct(
                type="function_call",
                name="add",
                call_id="tool_1",
                id="tool_1",
                arguments='{"x":1,"y":2}',
                status="completed",
            ),
        ],
        usage=_make_usage(),
    )

    events.append(
        ResponseCompletedEvent.construct(
            type="response.completed",
            sequence_number=6,
            response=ParsedResponse.construct(**final_response.model_dump()),
        )
    )

    dummy_stream = _DummyStream(
        events, ParsedResponse.construct(**final_response.model_dump())
    )
    manager = _DummyManager(dummy_stream)
    adapter_manager = _ResponsesStreamManagerAdapter(manager, StructuredResult)

    with adapter_manager as stream:
        chunks = list(stream)
        assert isinstance(chunks[0], CamelStreamChunk)
        assert chunks[0].content_delta == "Hello"
        tool_delta = chunks[1].tool_call_deltas[0]
        assert tool_delta.name_delta == "add"
        assert tool_delta.arguments_delta in {"{\"x\":1", ',"y":2}'}

        final_completion = stream.get_final_completion()
        assert final_completion.messages[0].content == '{"summary":"done"}'
        assert isinstance(
            final_completion.messages[0].parsed, StructuredResult
        )
        assert final_completion.messages[0].parsed.summary == "done"
