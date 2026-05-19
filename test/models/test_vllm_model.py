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

from typing import Any, cast

import pytest
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk,
    ChoiceDelta,
)
from openai.types.chat.chat_completion_chunk import (
    Choice as ChunkChoice,
)
from openai.types.chat.chat_completion_message import ChatCompletionMessage

from camel.configs import VLLMConfig
from camel.models import VLLMModel
from camel.types import ChatCompletion, ModelType, UnifiedModelType
from camel.utils import OpenAITokenCounter


def _make_vllm_model() -> VLLMModel:
    return VLLMModel(
        ModelType.GPT_4O_MINI,
        api_key="vllm",
        url="http://localhost:8000/v1",
    )


def _make_chat_completion(
    reasoning: str,
    reasoning_content: str | None = None,
) -> ChatCompletion:
    message = ChatCompletionMessage(role="assistant", content="answer")
    message_with_reasoning = cast(Any, message)
    message_with_reasoning.reasoning = reasoning
    if reasoning_content is not None:
        message_with_reasoning.reasoning_content = reasoning_content
    return ChatCompletion(
        id="test",
        model="test",
        object="chat.completion",
        created=0,
        choices=[Choice(index=0, finish_reason="stop", message=message)],
    )


def _make_chat_completion_chunk(reasoning: str) -> ChatCompletionChunk:
    delta = ChoiceDelta(content=None, role="assistant")
    cast(Any, delta).reasoning = reasoning
    return ChatCompletionChunk(
        id="test",
        choices=[
            ChunkChoice(
                index=0,
                delta=delta,
                finish_reason=None,
            )
        ],
        created=0,
        model="test",
        object="chat.completion.chunk",
    )


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GPT_4,
        ModelType.GPT_4_TURBO,
        ModelType.GPT_4O,
        ModelType.GPT_4O_MINI,
    ],
)
def test_vllm_model(model_type: ModelType):
    model = VLLMModel(model_type, api_key="vllm")
    assert model.model_type == model_type
    assert model.model_config_dict == VLLMConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type, UnifiedModelType)
    assert isinstance(model.token_limit, int)


def test_vllm_postprocess_maps_reasoning_to_reasoning_content():
    model = _make_vllm_model()
    response = _make_chat_completion(reasoning="provider reasoning")

    result = model.postprocess_response(response)

    assert result.choices[0].message.reasoning_content == "provider reasoning"


def test_vllm_postprocess_preserves_reasoning_content():
    model = _make_vllm_model()
    response = _make_chat_completion(
        reasoning="provider reasoning",
        reasoning_content="canonical reasoning",
    )

    result = model.postprocess_response(response)

    assert result.choices[0].message.reasoning_content == "canonical reasoning"


def test_vllm_run_maps_stream_reasoning_to_reasoning_content():
    class StreamingVLLMModel(VLLMModel):
        def _run(self, messages, response_format=None, tools=None):
            yield _make_chat_completion_chunk("streamed reasoning")

    model = StreamingVLLMModel(
        ModelType.GPT_4O_MINI,
        api_key="vllm",
        url="http://localhost:8000/v1",
    )

    chunks = list(model.run([{"role": "user", "content": "test"}]))

    assert chunks[0].choices[0].delta.reasoning_content == (
        "streamed reasoning"
    )


@pytest.mark.asyncio
async def test_vllm_arun_maps_stream_reasoning_to_reasoning_content():
    class AsyncStreamingVLLMModel(VLLMModel):
        async def _arun(self, messages, response_format=None, tools=None):
            async def stream():
                yield _make_chat_completion_chunk("async streamed reasoning")

            return stream()

    model = AsyncStreamingVLLMModel(
        ModelType.GPT_4O_MINI,
        api_key="vllm",
        url="http://localhost:8000/v1",
    )

    stream = await model.arun([{"role": "user", "content": "test"}])
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)

    assert chunks[0].choices[0].delta.reasoning_content == (
        "async streamed reasoning"
    )
