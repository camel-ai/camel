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
import os
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
            cache_checkpoint_target="both",
        ).as_dict(),
        bedrock_client=object(),
    )

    system, messages = model._convert_openai_to_bedrock_messages(
        [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "hello"},
        ]
    )
    assert system[-1] == {"cachePoint": {"type": "default", "ttl": "5m"}}
    assert messages[-1]["content"][-1] == {
        "cachePoint": {"type": "default", "ttl": "5m"}
    }
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
async def test_converse_async_not_supported():
    model = _make_model(bedrock_client=object())
    with pytest.raises(NotImplementedError):
        await model._arun([{"role": "user", "content": "hi"}])


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
    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "AKIA_TEST_KEY"
