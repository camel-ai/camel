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

import os
import types
from contextlib import contextmanager
from unittest.mock import MagicMock

from pydantic import BaseModel

from camel.models.openai_responses_model import OpenAIResponsesModel
from camel.responses.adapters.responses_adapter import (
    responses_to_camel_response,
)
from camel.responses.model_response import CamelModelResponse
from camel.types import ModelType


@contextmanager
def env(var: str, value: str):
    old = os.environ.get(var)
    os.environ[var] = value
    try:
        yield
    finally:
        if old is None:
            del os.environ[var]
        else:
            os.environ[var] = old


class _StubResp:
    def __init__(self, text: str):
        self.id = "resp_001"
        self.model = "gpt-4.1-mini"
        self.created = 1730000200
        self.output_text = text
        self.usage = {"input_tokens": 1, "output_tokens": 2}


def test_openai_responses_model_non_streaming(monkeypatch):
    with env("OPENAI_API_KEY", "test"):
        model = OpenAIResponsesModel(ModelType.GPT_4_1_MINI)

        class _StubClient:
            def __init__(self):
                self.responses = types.SimpleNamespace(
                    create=lambda **kwargs: _StubResp("ok")
                )

        # Replace clients to avoid network
        model._client = _StubClient()

        result = model.run([{"role": "user", "content": "hello"}])
        assert isinstance(result, CamelModelResponse)
        assert result.id == "resp_001"
        assert (
            result.output_messages
            and result.output_messages[0].content == "ok"
        )


class _Person(BaseModel):
    name: str


def test_openai_responses_model_parse(monkeypatch):
    with env("OPENAI_API_KEY", "test"):
        model = OpenAIResponsesModel(ModelType.GPT_4_1_MINI)

        class _StubParsedResp:
            def __init__(self):
                self.id = "resp_002"
                self.model = "gpt-4.1-mini"
                self.created = 1730000300
                self.output_text = "John"
                self.parsed = _Person(name="John")

        class _StubClient:
            def __init__(self):
                self.responses = types.SimpleNamespace(
                    parse=lambda **kwargs: _StubParsedResp()
                )

        model._client = _StubClient()
        result = model.run(
            [{"role": "user", "content": "who?"}], response_format=_Person
        )
        assert isinstance(result, CamelModelResponse)
        assert result.id == "resp_002"
        msg = result.output_messages[0]
        assert msg.content == "John"
        assert isinstance(msg.parsed, _Person) and msg.parsed.name == "John"


def test_responses_to_camel_response_with_audio():
    # Mock a response with audio output
    mock_response = MagicMock()
    mock_response.id = "resp_123"
    mock_response.model = "gpt-4o-audio-preview"
    mock_response.created = 1234567890

    mock_audio_chunk = {
        "type": "output_audio",
        "audio": {
            "data": (
                "UklGRgAAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQAA"
                "AAA="
            ),
            "format": "wav",
            "transcript": "Hello world",
        },
    }

    mock_text_chunk = {"type": "output_text", "text": "Hello text"}

    mock_item = MagicMock()
    mock_item.content = [mock_text_chunk, mock_audio_chunk]

    mock_response.output = [mock_item]
    mock_response.output_text = None
    mock_response.usage = None  # Fix validation error

    camel_response = responses_to_camel_response(mock_response)

    assert "Hello text" in camel_response.output_messages[0].content
    assert camel_response.output_messages[0].audio_bytes is not None
    assert camel_response.output_messages[0].audio_transcript == "Hello world"


def test_responses_to_camel_response_keeps_logprobs():
    mock_response = MagicMock()
    mock_response.id = "resp_124"
    mock_response.model = "gpt-4o-mini"
    mock_response.created = 1234567891

    logprob_entry = {
        "token": "Hi",
        "bytes": [72, 105],
        "logprob": -0.1,
        "top_logprobs": [],
    }
    mock_text_chunk = {
        "type": "output_text",
        "text": "Hi there",
        "logprobs": [logprob_entry],
    }

    mock_item = MagicMock()
    mock_item.content = [mock_text_chunk]

    mock_response.output = [mock_item]
    mock_response.output_text = None
    mock_response.usage = {"input_tokens": 10, "output_tokens": 5}

    camel_response = responses_to_camel_response(mock_response)

    assert camel_response.logprobs is not None
    assert camel_response.logprobs[0][0]["token"] == "Hi"
    assert camel_response.usage.input_tokens == 10
    assert camel_response.usage.output_tokens == 5
    assert camel_response.usage.total_tokens == 15


def test_responses_to_camel_response_keeps_output_image():
    mock_response = MagicMock()
    mock_response.id = "resp_125"
    mock_response.model = "gpt-4o-mini"
    mock_response.created = 1234567892

    mock_image_chunk = {
        "type": "output_image",
        "image_url": "https://example.com/img.png",
    }
    mock_item = MagicMock()
    mock_item.content = [mock_image_chunk]

    mock_response.output = [mock_item]
    mock_response.output_text = None
    mock_response.usage = None

    camel_response = responses_to_camel_response(mock_response)

    assert (
        "[image]: https://example.com/img.png"
        in camel_response.output_messages[0].content
    )


def test_openai_messages_to_camel_with_audio():
    from camel.core.messages import openai_messages_to_camel

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Listen to this"},
                {
                    "type": "input_audio",
                    "input_audio": {"data": "base64data", "format": "wav"},
                },
            ],
        }
    ]

    # Currently this will ignore the audio part because it's not implemented
    camel_msgs = openai_messages_to_camel(messages)
    assert len(camel_msgs) == 1
    assert len(camel_msgs[0].content) == 2
    assert camel_msgs[0].content[0].type == "text"
    assert camel_msgs[0].content[1].type == "input_audio"
    assert camel_msgs[0].content[1].payload["data"] == "base64data"
    assert camel_msgs[0].content[1].payload["format"] == "wav"


def test_openai_messages_to_camel_with_file():
    from camel.core.messages import openai_messages_to_camel

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Analyze this file"},
                {"type": "input_file", "file_id": "file-123"},
            ],
        }
    ]

    camel_msgs = openai_messages_to_camel(messages)
    assert len(camel_msgs) == 1
    assert len(camel_msgs[0].content) == 2
    assert camel_msgs[0].content[1].type == "input_file"
    assert camel_msgs[0].content[1].payload["file_id"] == "file-123"


def test_responses_stream_tools():
    from openai.types.chat import ChatCompletionChunk

    from camel.models.openai_responses_model import OpenAIResponsesModel
    from camel.types import ModelType

    # Mock chunks
    class MockChunk:
        def __init__(self, type, **kwargs):
            self.type = type
            for k, v in kwargs.items():
                setattr(self, k, v)

    mock_chunks = [
        MockChunk(
            "response.output_item.added",
            item=types.SimpleNamespace(
                type="function_call", call_id="call_123", name="test_tool"
            ),
            output_index=0,
        ),
        MockChunk(
            "response.function_call_arguments.delta",
            delta='{"arg":',
            output_index=0,
        ),
        MockChunk(
            "response.function_call_arguments.delta",
            delta='"val"}',
            output_index=0,
        ),
        MockChunk("response.output_item.done"),
        MockChunk("response.completed"),
    ]

    with env("OPENAI_API_KEY", "test"):
        model = OpenAIResponsesModel(
            ModelType.GPT_4_1_MINI, model_config_dict={"stream": True}
        )

        class _StubClient:
            def __init__(self):
                self.responses = types.SimpleNamespace(
                    create=lambda **kwargs: iter(mock_chunks)
                )

        model._client = _StubClient()

        stream = model.run([{"role": "user", "content": "call tool"}])

        chunks = list(stream)
        assert len(chunks) > 0
        assert isinstance(chunks[0], ChatCompletionChunk)

        # Verify tool call start
        assert chunks[0].choices[0].delta.tool_calls[0].id == "call_123"
        assert (
            chunks[0].choices[0].delta.tool_calls[0].function.name
            == "test_tool"
        )

        # Verify arguments delta
        assert (
            chunks[1].choices[0].delta.tool_calls[0].function.arguments
            == '{"arg":'
        )
        assert (
            chunks[2].choices[0].delta.tool_calls[0].function.arguments
            == '"val"}'
        )
