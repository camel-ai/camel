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

import httpx
import pytest
from openai import AsyncOpenAI

from camel.models.base_chat_model import BaseChatModel
from camel.models.client import SGLangClient


class FakeTokenizer:
    model_max_length = 8192

    def apply_chat_template(self, messages, **kwargs):
        return [10, 20, 30]

    def encode(self, text, add_special_tokens=False):
        return [ord(char) for char in text]

    def decode(self, token_ids):
        return "".join(chr(token_id) for token_id in token_ids)


@pytest.mark.asyncio
async def test_tito_backend_uses_in_house_client_via_openai_interface():
    seen = {}

    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "text": "<think>raw</think>answer",
                "output_ids": [41, 42],
                "meta_info": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "finish_reason": {"type": "stop"},
                },
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = SGLangClient(
        base_url="http://sglang.test",
        model="Qwen/Qwen3-0.6B",
        tokenizer=FakeTokenizer(),
        http_client=http_client,
    )
    model = BaseChatModel(
        model_type="Qwen/Qwen3-0.6B",
        model_config_dict={
            "temperature": 0.2,
            "context_length": 8192,
            "top_k": 20,
        },
        client=client,
    )
    messages = [{"role": "user", "content": "hello"}]
    tools = [{"type": "function", "function": {"name": "ping"}}]

    actual = await model.arun(messages, tools=tools)

    assert seen["url"] == "http://sglang.test/generate"
    assert seen["body"] == {
        "input_ids": [10, 20, 30],
        "sampling_params": {"temperature": 0.2, "top_k": 20},
        "return_prompt_token_ids": True,
    }
    assert actual.choices[0].message.content == "<think>raw</think>answer"
    assert model.token_counter.count_tokens_from_messages(messages) == 3
    assert model.token_limit == 8192
    assert model.last_output_token_ids == [41, 42]
    await http_client.aclose()


def test_tito_backend_requires_url_without_injected_client():
    with pytest.raises(ValueError, match="url is required"):
        BaseChatModel(model_type="Qwen/Qwen3-0.6B")


@pytest.mark.asyncio
async def test_tito_backend_starts_async_openai_for_session_url():
    seen = {}

    async def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-session",
                "object": "chat.completion",
                "created": 1,
                "model": "Qwen/Qwen3-0.6B",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "answer",
                        },
                        "finish_reason": "stop",
                        "prompt_token_ids": [1, 2],
                        "meta_info": {
                            "completion_tokens": 1,
                            "output_token_logprobs": [[-0.1, 3]],
                        },
                    }
                ],
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    model = BaseChatModel(
        model_type="Qwen/Qwen3-0.6B",
        model_config_dict={"temperature": 0, "top_k": 20},
        url="http://miles.test/sessions/session-abc",
        http_client=http_client,
    )
    messages = [{"role": "user", "content": "hello"}]

    response = await model.arun(messages)

    assert isinstance(model._async_client, AsyncOpenAI)
    assert seen["url"] == (
        "http://miles.test/sessions/session-abc/v1/chat/completions"
    )
    assert seen["body"] == {
        "messages": messages,
        "model": "Qwen/Qwen3-0.6B",
        "stream": False,
        "temperature": 0,
        "top_k": 20,
    }
    assert response.choices[0].message.content == "answer"
    assert model.last_prompt_tokens == 2
    assert model.last_output_token_ids == [3]
    await model.aclose()
