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

from camel.configs import CohereConfig
from camel.models import CohereModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


def _mock_cohere_tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _mock_cohere_response(*, tool_calls=None, text=None):
    message = SimpleNamespace(
        tool_plan="calling tools" if tool_calls else None,
        content=None if tool_calls else [SimpleNamespace(text=text)],
        tool_calls=tool_calls,
    )
    return SimpleNamespace(
        id="gen-1",
        finish_reason="tool_call" if tool_calls else "complete",
        usage=SimpleNamespace(
            tokens=SimpleNamespace(input_tokens=11, output_tokens=7)
        ),
        message=message,
    )


def test_to_openai_response_preserves_parallel_tool_calls():
    r"""A Cohere turn with several parallel tool calls must map to a single
    choices[0] that carries all of them. Downstream code reads only
    ``choices[0].message.tool_calls``, so splitting the calls across separate
    choices silently drops every call after the first."""
    model = CohereModel(ModelType.COHERE_COMMAND_R, api_key="dummy")
    response = _mock_cohere_response(
        tool_calls=[
            _mock_cohere_tool_call("t1", "get_weather", '{"city": "Paris"}'),
            _mock_cohere_tool_call("t2", "get_time", '{"tz": "UTC"}'),
        ]
    )

    result = model._to_openai_response(response)

    assert len(result.choices) == 1
    assert result.choices[0].index == 0
    tool_calls = result.choices[0].message.tool_calls
    assert [tc.id for tc in tool_calls] == ["t1", "t2"]
    assert [tc.function.name for tc in tool_calls] == [
        "get_weather",
        "get_time",
    ]


def test_to_openai_response_single_tool_call_unchanged():
    r"""The common single-tool-call path still yields one choice, one call."""
    model = CohereModel(ModelType.COHERE_COMMAND_R, api_key="dummy")
    response = _mock_cohere_response(
        tool_calls=[
            _mock_cohere_tool_call("t1", "get_weather", '{"city": "Paris"}')
        ]
    )

    result = model._to_openai_response(response)

    assert len(result.choices) == 1
    assert len(result.choices[0].message.tool_calls) == 1
    assert result.choices[0].message.tool_calls[0].id == "t1"


def test_to_openai_response_text_only():
    r"""A plain text turn maps to one choice with no tool calls."""
    model = CohereModel(ModelType.COHERE_COMMAND_R, api_key="dummy")
    response = _mock_cohere_response(text="hello there")

    result = model._to_openai_response(response)

    assert len(result.choices) == 1
    assert result.choices[0].index == 0
    assert result.choices[0].message.content == "hello there"
    assert result.choices[0].message.tool_calls is None


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.COHERE_COMMAND_R,
        ModelType.COHERE_COMMAND_LIGHT,
        ModelType.COHERE_COMMAND,
        ModelType.COHERE_COMMAND_NIGHTLY,
        ModelType.COHERE_COMMAND_R_PLUS,
    ],
)
def test_cohere_model(model_type):
    model_config_dict = CohereConfig().as_dict()
    model = CohereModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)
