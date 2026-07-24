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
from types import SimpleNamespace

from camel.models.openai_responses_adapter import (
    iter_response_events_to_chat_chunks,
    response_to_chat_completion,
)

MODEL = "gpt-4o"


def _usage_val(usage, key):
    # Emitted usage may be a dict or an openai ``CompletionUsage`` model
    # depending on how ``.construct`` coerces it; read it either way.
    return usage[key] if isinstance(usage, dict) else getattr(usage, key)


def _usage(input_tokens: int = 10, output_tokens: int = 5):
    return SimpleNamespace(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )


def _text_item(text: str = "hello"):
    return SimpleNamespace(
        type="message",
        content=[SimpleNamespace(type="output_text", text=text)],
    )


def _tool_item():
    return SimpleNamespace(
        type="function_call",
        call_id="call_1",
        id="fc_1",
        name="get_weather",
        arguments='{"city": "beijing"}',
    )


def _response(*, status, output, incomplete_reason=None):
    return SimpleNamespace(
        id="resp_1",
        created_at=1234567890,
        status=status,
        incomplete_details=(
            SimpleNamespace(reason=incomplete_reason)
            if incomplete_reason is not None
            else None
        ),
        output=output,
        usage=_usage(),
    )


# --------------------------------------------------------------------------- #
# Non-streaming: response_to_chat_completion                                  #
# --------------------------------------------------------------------------- #


def test_non_streaming_max_output_tokens_maps_to_length():
    # A Responses call truncated at max_output_tokens.
    response = _response(
        status="incomplete",
        output=[_text_item("partial answer")],
        incomplete_reason="max_output_tokens",
    )

    completion = response_to_chat_completion(response, MODEL)

    assert completion.choices[0].finish_reason == "length"
    # Usage must survive the mapping.
    assert _usage_val(completion.usage, "completion_tokens") == 5
    assert _usage_val(completion.usage, "total_tokens") == 15


def test_non_streaming_content_filter_maps_to_content_filter():
    response = _response(
        status="incomplete",
        output=[_text_item("")],
        incomplete_reason="content_filter",
    )

    completion = response_to_chat_completion(response, MODEL)

    assert completion.choices[0].finish_reason == "content_filter"


def test_non_streaming_completed_text_is_stop():
    # Regression guard: a normal completed response stays "stop".
    response = _response(status="completed", output=[_text_item("done")])

    completion = response_to_chat_completion(response, MODEL)

    assert completion.choices[0].finish_reason == "stop"


def test_non_streaming_completed_tool_call_is_tool_calls():
    # Regression guard: a completed tool call stays "tool_calls".
    response = _response(status="completed", output=[_tool_item()])

    completion = response_to_chat_completion(response, MODEL)

    assert completion.choices[0].finish_reason == "tool_calls"


# --------------------------------------------------------------------------- #
# Streaming: iter_response_events_to_chat_chunks                              #
# --------------------------------------------------------------------------- #


def _stream_finish_chunks(events):
    chunks = list(iter_response_events_to_chat_chunks(iter(events), MODEL))
    return [c for c in chunks if c.choices[0].finish_reason is not None]


def test_streaming_max_output_tokens_maps_to_length_and_keeps_usage():
    events = [
        SimpleNamespace(
            type="response.created",
            response=SimpleNamespace(id="resp_1"),
        ),
        SimpleNamespace(
            type="response.output_text.delta",
            delta="partial",
            item_id="msg_1",
        ),
        SimpleNamespace(
            type="response.incomplete",
            response=SimpleNamespace(
                id="resp_1",
                status="incomplete",
                incomplete_details=SimpleNamespace(reason="max_output_tokens"),
                usage=_usage(),
            ),
        ),
    ]

    finish_chunks = _stream_finish_chunks(events)

    # Exactly one terminal chunk (the incomplete branch fires, so the
    # abnormal-termination safety fallback does not also emit one).
    assert len(finish_chunks) == 1
    terminal = finish_chunks[0]
    assert terminal.choices[0].finish_reason == "length"
    assert terminal.usage is not None
    assert _usage_val(terminal.usage, "total_tokens") == 15


def test_streaming_completed_is_stop():
    # Regression guard: a completed text stream stays "stop".
    events = [
        SimpleNamespace(
            type="response.created",
            response=SimpleNamespace(id="resp_1"),
        ),
        SimpleNamespace(
            type="response.output_text.delta",
            delta="hi",
            item_id="msg_1",
        ),
        SimpleNamespace(
            type="response.completed",
            response=SimpleNamespace(
                id="resp_1", status="completed", usage=_usage()
            ),
        ),
    ]

    finish_chunks = _stream_finish_chunks(events)

    assert len(finish_chunks) == 1
    assert finish_chunks[0].choices[0].finish_reason == "stop"


def test_streaming_failed_emits_single_terminal_chunk():
    # A failed stream terminates through the terminal branch, not the
    # abnormal-termination fallback, so usage is preserved and only one
    # finishing chunk is emitted.
    events = [
        SimpleNamespace(
            type="response.created",
            response=SimpleNamespace(id="resp_1"),
        ),
        SimpleNamespace(
            type="response.failed",
            response=SimpleNamespace(
                id="resp_1",
                status="failed",
                incomplete_details=None,
                usage=_usage(),
            ),
        ),
    ]

    finish_chunks = _stream_finish_chunks(events)

    assert len(finish_chunks) == 1
    assert finish_chunks[0].usage is not None
