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

import base64
import sys
import types

import pytest

from camel.configs import BedrockConfig
from camel.models import AWSBedrockConverseModel
from camel.types import ModelType


def _make_model(
    model_config_dict=None,
    **kwargs,
) -> AWSBedrockConverseModel:
    if model_config_dict is None:
        model_config_dict = BedrockConfig().as_dict()
    return AWSBedrockConverseModel(
        ModelType.AWS_CLAUDE_3_HAIKU,
        model_config_dict=model_config_dict,
        api_key="dummy_key",
        region_name="us-west-2",
        **kwargs,
    )


@pytest.mark.model_backend
def test_converse_cache_checkpoints_not_shared_object():
    model = _make_model(
        BedrockConfig(
            cache_control="5m",
        ).as_dict(),
        bedrock_client=object(),
    )

    system, messages = model._convert_openai_to_bedrock_messages(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
    )
    assert system[-1] == {"cachePoint": {"type": "default"}}
    assert messages[-1]["content"][-1] == {"cachePoint": {"type": "default"}}
    assert system[-1] is not messages[-1]["content"][-1]


@pytest.mark.model_backend
def test_converse_builds_tool_config_and_tool_messages():
    model = _make_model(
        BedrockConfig(
            cache_control="5m",
            tool_choice="auto",
        ).as_dict(),
        bedrock_client=object(),
    )

    request = model._build_converse_request(
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "question"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "search_docs",
                            "arguments": '{"q":"camel"}',
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_1",
                "content": '{"answer":"ok"}',
            },
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_docs",
                    "description": "Search docs",
                    "parameters": {
                        "type": "object",
                        "properties": {"q": {"type": "string"}},
                        "required": ["q"],
                    },
                },
            }
        ],
    )

    assert request["toolConfig"]["toolChoice"] == {"auto": {}}
    assert (
        request["toolConfig"]["tools"][0]["toolSpec"]["name"] == "search_docs"
    )
    assert request["messages"][1]["role"] == "assistant"
    assert any(
        isinstance(block, dict) and "toolUse" in block
        for block in request["messages"][1]["content"]
    )
    assert request["messages"][2]["role"] == "user"
    assert "toolResult" in request["messages"][2]["content"][0]


@pytest.mark.model_backend
def test_converse_tool_choice_none_disables_tools():
    model = _make_model(
        BedrockConfig(tool_choice="none").as_dict(),
        bedrock_client=object(),
    )
    request = model._build_converse_request(
        messages=[{"role": "user", "content": "hello"}],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "search_docs",
                    "parameters": {"type": "object"},
                },
            }
        ],
    )
    assert "toolConfig" not in request


@pytest.mark.model_backend
def test_converse_supports_data_url_image_conversion():
    image_bytes = b"test-image"
    data_url = (
        "data:image/png;base64," + base64.b64encode(image_bytes).decode()
    )
    model = _make_model(bedrock_client=object())

    blocks = model._to_bedrock_content_blocks(
        [{"type": "image_url", "image_url": {"url": data_url}}]
    )
    assert blocks[0]["image"]["format"] == "png"
    assert blocks[0]["image"]["source"]["bytes"] == image_bytes


@pytest.mark.model_backend
def test_converse_response_format_builds_output_config():
    from pydantic import BaseModel as PydanticBaseModel

    class MySchema(PydanticBaseModel):
        """Extract structured data."""

        title: str
        summary: str

    model = _make_model(bedrock_client=object())
    request = model._build_converse_request(
        messages=[{"role": "user", "content": "hello"}],
        response_format=MySchema,
    )
    assert "outputConfig" in request
    text_format = request["outputConfig"]["textFormat"]
    assert text_format["type"] == "json_schema"
    json_schema = text_format["structure"]["jsonSchema"]
    assert json_schema["name"] == "MySchema"
    assert '"title"' in json_schema["schema"]
    assert '"summary"' in json_schema["schema"]


@pytest.mark.model_backend
def test_converse_no_response_format_no_output_config():
    model = _make_model(bedrock_client=object())
    request = model._build_converse_request(
        messages=[{"role": "user", "content": "hello"}],
    )
    assert "outputConfig" not in request


@pytest.mark.model_backend
def test_parse_json_or_text_scalar_json_is_text():
    model = _make_model(bedrock_client=object())
    assert model._parse_json_or_text("42") == {"text": "42"}
    assert model._parse_json_or_text("true") == {"text": "true"}


@pytest.mark.model_backend
def test_converse_stream_is_supported():
    class DummyEventStream:
        def __init__(self, events):
            self._events = events

        def __iter__(self):
            return iter(self._events)

    class DummyClient:
        def converse_stream(self, **kwargs):
            return {
                "stream": DummyEventStream(
                    [
                        {"messageStart": {"role": "assistant"}},
                        {"contentBlockDelta": {"delta": {"text": "hello"}}},
                        {"messageStop": {"stopReason": "end_turn"}},
                    ]
                )
            }

    model = _make_model(
        BedrockConfig(stream=True).as_dict(),
        bedrock_client=DummyClient(),
    )
    chunks = list(model._run([{"role": "user", "content": "hi"}]))
    assert len(chunks) >= 2
    assert chunks[-1].choices[0].finish_reason == "stop"


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_converse_async_non_stream():
    """Test async non-stream converse with a mock aioboto3 session."""

    class MockAsyncClient:
        async def converse(self, **kwargs):
            return {
                "output": {
                    "message": {
                        "role": "assistant",
                        "content": [{"text": "hello async"}],
                    }
                },
                "stopReason": "end_turn",
                "usage": {
                    "inputTokens": 10,
                    "outputTokens": 5,
                },
                "ResponseMetadata": {"RequestId": "req-async-123"},
            }

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class MockSession:
        def client(self, *args, **kwargs):
            return MockAsyncClient()

    # Patch aioboto3.Session to return our mock
    import sys
    import types as _types

    mock_aioboto3 = _types.SimpleNamespace(Session=MockSession)
    monkeypatch_token = sys.modules.get("aioboto3")
    sys.modules["aioboto3"] = mock_aioboto3
    try:
        model = _make_model(bedrock_client=object())
        result = await model._arun([{"role": "user", "content": "hi"}])
        assert result.id == "req-async-123"
        assert result.choices[0].message.content == "hello async"
        assert result.usage.prompt_tokens == 10
        assert result.usage.completion_tokens == 5
    finally:
        if monkeypatch_token is not None:
            sys.modules["aioboto3"] = monkeypatch_token
        else:
            sys.modules.pop("aioboto3", None)


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_converse_async_stream():
    """Test async stream converse with a mock aioboto3 session."""

    class MockAsyncEventStream:
        def __init__(self, events):
            self._events = events
            self._index = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._index >= len(self._events):
                raise StopAsyncIteration
            event = self._events[self._index]
            self._index += 1
            return event

    class MockAsyncClient:
        async def converse_stream(self, **kwargs):
            return {
                "stream": MockAsyncEventStream(
                    [
                        {"messageStart": {"role": "assistant"}},
                        {"contentBlockDelta": {"delta": {"text": "hi async"}}},
                        {"messageStop": {"stopReason": "end_turn"}},
                    ]
                )
            }

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class MockSession:
        def client(self, *args, **kwargs):
            return MockAsyncClient()

    import sys
    import types as _types

    mock_aioboto3 = _types.SimpleNamespace(Session=MockSession)
    monkeypatch_token = sys.modules.get("aioboto3")
    sys.modules["aioboto3"] = mock_aioboto3
    try:
        model = _make_model(
            BedrockConfig(stream=True).as_dict(),
            bedrock_client=object(),
        )
        result = await model._arun([{"role": "user", "content": "hi"}])
        chunks = [chunk async for chunk in result]
        assert len(chunks) >= 2
        assert chunks[-1].choices[0].finish_reason == "stop"
    finally:
        if monkeypatch_token is not None:
            sys.modules["aioboto3"] = monkeypatch_token
        else:
            sys.modules.pop("aioboto3", None)


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_converse_async_missing_aioboto3():
    """Test that ImportError is raised when aioboto3 is not installed."""
    import sys

    monkeypatch_token = sys.modules.get("aioboto3")
    sys.modules["aioboto3"] = None  # type: ignore[assignment]
    try:
        model = _make_model(bedrock_client=object())
        with pytest.raises(ImportError, match="aioboto3"):
            await model._arun([{"role": "user", "content": "hi"}])
    finally:
        if monkeypatch_token is not None:
            sys.modules["aioboto3"] = monkeypatch_token
        else:
            sys.modules.pop("aioboto3", None)


@pytest.mark.model_backend
def test_bedrock_client_supports_api_key_and_region_name(monkeypatch):
    def _fake_boto3_client(service_name, **kwargs):
        return {"service_name": service_name, "kwargs": kwargs}

    fake_boto3 = types.SimpleNamespace(client=_fake_boto3_client)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)

    model = AWSBedrockConverseModel(
        ModelType.AWS_CLAUDE_3_HAIKU,
        model_config_dict=BedrockConfig().as_dict(),
        api_key="AKIA_TEST_KEY",
        region_name="us-east-1",
    )

    client = model.bedrock_client
    assert client["service_name"] == "bedrock-runtime"
    assert client["kwargs"]["region_name"] == "us-east-1"
    assert "aws_access_key_id" not in client["kwargs"]
