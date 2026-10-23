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
import json
import os

import httpx
import pytest

from camel.models.client import SGLangClient


class FakeTokenizer:
    model_max_length = 4096

    def __init__(self):
        self.calls = []

    def apply_chat_template(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return [10, 20, 30]

    def encode(self, text, add_special_tokens=False):
        return [ord(char) for char in text]

    def decode(self, token_ids):
        return "".join(chr(token_id) for token_id in token_ids)


@pytest.mark.asyncio
async def test_native_client_sends_ids_and_parses_qwen_tool_call():
    seen = {}

    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "text": (
                    "thinking\n<tool_call>\n"
                    '{"name":"weather","arguments":{"city":"Paris"}}'
                    "\n</tool_call>"
                ),
                "output_ids": [41, 42],
                "meta_info": {
                    "id": "request-1",
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "finish_reason": {"type": "stop"},
                },
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    tokenizer = FakeTokenizer()
    client = SGLangClient(
        "http://sglang.test/v1",
        model="Qwen/Qwen3-0.6B",
        tokenizer=tokenizer,
        chat_template="custom-template",
        chat_template_kwargs={"enable_thinking": False},
        http_client=http_client,
    )
    tools = [
        {
            "type": "function",
            "function": {"name": "weather", "parameters": {}},
        }
    ]

    response = await client.create_chat_completion(
        [{"role": "user", "content": "weather?"}],
        tools=tools,
        model_config={"temperature": 0, "max_tokens": 7, "stream": False},
    )

    assert seen["url"] == "http://sglang.test/generate"
    assert seen["body"] == {
        "input_ids": [10, 20, 30],
        "sampling_params": {"temperature": 0, "max_new_tokens": 7},
        "return_prompt_token_ids": True,
    }
    assert tokenizer.calls[0][1] == {
        "tokenize": True,
        "add_generation_prompt": True,
        "chat_template": "custom-template",
        "enable_thinking": False,
        "tools": tools,
    }
    message = response.choices[0].message
    assert message.content == "thinking"
    assert message.tool_calls[0].function.name == "weather"
    assert json.loads(message.tool_calls[0].function.arguments) == {
        "city": "Paris"
    }
    assert response.output_token_ids == [41, 42]
    assert response.prompt_token_ids == [10, 20, 30]
    assert client.last_generation.output_token_ids == [41, 42]
    await http_client.aclose()


@pytest.mark.asyncio
async def test_openai_mode_uses_chat_completions_contract():
    seen = {}

    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        seen["authorization"] = request.headers.get("authorization")
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-session-1",
                "object": "chat.completion",
                "created": 1,
                "model": "Qwen/Qwen3-0.6B",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_calls": [
                                {
                                    "id": "call_from_server",
                                    "type": "function",
                                    "function": {
                                        "name": "weather",
                                        "arguments": '{"city":"Paris"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                        "prompt_token_ids": [10, 20, 30],
                        "meta_info": {
                            "completion_tokens": 2,
                            "output_token_logprobs": [
                                [-0.1, 41],
                                [-0.2, 42],
                            ],
                        },
                    }
                ],
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = SGLangClient(
        "http://miles.test/sessions/session-123",
        model="Qwen/Qwen3-0.6B",
        api_mode="openai",
        api_key="session-key",
        http_client=http_client,
    )
    messages = [{"role": "user", "content": "weather?"}]
    tools = [
        {
            "type": "function",
            "function": {"name": "weather", "parameters": {}},
        }
    ]

    response = await client.create_chat_completion(
        messages,
        tools=tools,
        model_config={
            "temperature": 0,
            "max_new_tokens": 7,
            "context_length": 4096,
            "stream": False,
        },
    )

    assert client.api_mode == "openai"
    assert client.tokenizer is None
    assert seen["url"] == (
        "http://miles.test/sessions/session-123/v1/chat/completions"
    )
    assert seen["authorization"] == "Bearer session-key"
    assert seen["body"] == {
        "model": "Qwen/Qwen3-0.6B",
        "messages": messages,
        "tools": tools,
        "temperature": 0,
        "max_tokens": 7,
        "stream": False,
        "return_prompt_token_ids": True,
    }
    assert response.choices[0].message.content == ""
    assert response.choices[0].message.tool_calls[0].id == ("call_from_server")
    assert response.choices[0].meta_info["completion_tokens"] == 2
    assert response.prompt_token_ids == [10, 20, 30]
    assert response.output_token_ids == [41, 42]
    assert client.last_generation.prompt_token_ids == [10, 20, 30]
    assert client.last_generation.output_token_ids == [41, 42]
    await http_client.aclose()


@pytest.mark.asyncio
async def test_explicit_openai_mode_accepts_v1_base_url():
    seen = {}

    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 1,
                "model": "model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "ok",
                        },
                        "finish_reason": "stop",
                    }
                ],
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = SGLangClient(
        "http://sglang.test/v1",
        model="model",
        api_mode="openai",
        http_client=http_client,
    )

    await client.create_chat_completion([{"role": "user", "content": "hello"}])

    assert seen["url"] == "http://sglang.test/v1/chat/completions"
    await http_client.aclose()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.environ.get("SGLANG_QWEN3_URL"),
    reason="set SGLANG_QWEN3_URL to a Qwen/Qwen3-0.6B SGLang server",
)
async def test_qwen3_06b_sglang_returns_token_ids():
    client = SGLangClient(
        os.environ["SGLANG_QWEN3_URL"],
        model="Qwen/Qwen3-0.6B",
        tokenizer="Qwen/Qwen3-0.6B",
        chat_template_kwargs={"enable_thinking": False},
    )
    try:
        response = await client.create_chat_completion(
            [{"role": "user", "content": "Reply with only: OK"}],
            model_config={"temperature": 0, "max_tokens": 8},
        )
        assert response.choices[0].message.content
        assert response.prompt_token_ids
        assert response.output_token_ids
    finally:
        await client.aclose()


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
