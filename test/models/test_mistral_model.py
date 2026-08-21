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

import pytest

from camel.configs import MistralConfig
from camel.models import MistralModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


def _mock_mistral_response(finish_reason):
    r"""A minimal Mistral ChatCompletionResponse carrying one choice."""
    return SimpleNamespace(
        id="cmpl-1",
        created=1700000000,
        model="mistral-large-latest",
        usage=SimpleNamespace(
            prompt_tokens=11, completion_tokens=7, total_tokens=18
        ),
        choices=[
            SimpleNamespace(
                index=0,
                finish_reason=finish_reason,
                message=SimpleNamespace(
                    role="assistant", content="hi", tool_calls=None
                ),
            )
        ],
    )


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.MISTRAL_LARGE,
        ModelType.MISTRAL_NEMO,
        ModelType.MISTRAL_7B,
        ModelType.MISTRAL_MIXTRAL_8x7B,
        ModelType.MISTRAL_MIXTRAL_8x22B,
        ModelType.MISTRAL_CODESTRAL,
        ModelType.MISTRAL_CODESTRAL_MAMBA,
        ModelType.MISTRAL_PIXTRAL_12B,
        ModelType.MISTRAL_MEDIUM_3_1,
        ModelType.MISTRAL_SMALL_3_2,
        ModelType.MAGISTRAL_SMALL_1_2,
        ModelType.MAGISTRAL_MEDIUM_1_2,
    ],
)
def test_mistral_model(model_type):
    model_config_dict = MistralConfig().as_dict()
    model = MistralModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_to_mistral_chatmessage_preserves_tool_call_ids(monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "test_key")
    model = MistralModel(ModelType.MISTRAL_LARGE, MistralConfig().as_dict())

    tool_call_id_1 = "call_tool_1"
    tool_call_id_2 = "call_tool_2"
    messages = [
        {"role": "user", "content": "Please run two calculations."},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": tool_call_id_1,
                    "type": "function",
                    "function": {
                        "name": "add",
                        "arguments": '{"a": 2, "b": 3}',
                    },
                },
                {
                    "id": tool_call_id_2,
                    "type": "function",
                    "function": {
                        "name": "multiply",
                        "arguments": '{"a": 4, "b": 5}',
                    },
                },
            ],
        },
        {
            "role": "tool",
            "tool_call_id": tool_call_id_1,
            "content": "5",
            "name": "add",
        },
        {
            "role": "tool",
            "tool_call_id": tool_call_id_2,
            "content": "20",
            "name": "multiply",
        },
    ]

    mistral_messages = model._to_mistral_chatmessage(messages)

    assistant_message = mistral_messages[1]
    assert assistant_message.tool_calls is not None
    assert len(assistant_message.tool_calls) == 2
    assert assistant_message.tool_calls[0].id == tool_call_id_1
    assert assistant_message.tool_calls[1].id == tool_call_id_2

    first_tool_message = mistral_messages[2]
    second_tool_message = mistral_messages[3]
    assert first_tool_message.tool_call_id == tool_call_id_1
    assert second_tool_message.tool_call_id == tool_call_id_2


@pytest.mark.model_backend
def test_to_openai_response_maps_model_length_to_length(monkeypatch):
    r"""Mistral's own context-limit stop must reach the caller as the
    OpenAI term for a length stop. Left raw, a truncated generation is
    unreadable to any consumer that branches on "length"."""
    monkeypatch.setenv("MISTRAL_API_KEY", "test_key")
    model = MistralModel(ModelType.MISTRAL_LARGE, MistralConfig().as_dict())

    result = model._to_openai_response(_mock_mistral_response("model_length"))

    assert result.choices[0].finish_reason == "length"


@pytest.mark.model_backend
@pytest.mark.parametrize("finish_reason", ["stop", "length", "tool_calls"])
def test_to_openai_response_passes_through_openai_reasons(
    monkeypatch, finish_reason
):
    r"""The three Mistral reasons that are already OpenAI terms are
    unchanged by the mapping."""
    monkeypatch.setenv("MISTRAL_API_KEY", "test_key")
    model = MistralModel(ModelType.MISTRAL_LARGE, MistralConfig().as_dict())

    result = model._to_openai_response(_mock_mistral_response(finish_reason))

    assert result.choices[0].finish_reason == finish_reason


@pytest.mark.model_backend
def test_to_openai_response_raises_for_failed_generation(monkeypatch):
    r"""Mistral's "error" reason has no OpenAI equivalent, so it is raised
    rather than reported as a finished generation."""
    monkeypatch.setenv("MISTRAL_API_KEY", "test_key")
    model = MistralModel(ModelType.MISTRAL_LARGE, MistralConfig().as_dict())

    with pytest.raises(RuntimeError, match="error"):
        model._to_openai_response(_mock_mistral_response("error"))


@pytest.mark.model_backend
def test_to_openai_response_finish_reason_none_stays_none(monkeypatch):
    r"""A response with no finish reason still maps to None, not to a
    default, so an unfinished generation is not reported as completed."""
    monkeypatch.setenv("MISTRAL_API_KEY", "test_key")
    model = MistralModel(ModelType.MISTRAL_LARGE, MistralConfig().as_dict())

    result = model._to_openai_response(_mock_mistral_response(None))

    assert result.choices[0].finish_reason is None


def test_map_finish_reason_unknown_value_passes_through():
    r"""mistralai types FinishReason as a Literal plus UnrecognizedStr, so a
    value added by a later API version is forwarded unchanged instead of
    raising."""
    assert MistralModel._map_finish_reason("some_new_reason") == (
        "some_new_reason"
    )
