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
import re

import pytest

from camel.configs import SGLangConfig
from camel.models import SGLangModel
from camel.types import ModelType, UnifiedModelType
from camel.utils import OpenAITokenCounter


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
def test_sglang_model(model_type: ModelType):
    model = SGLangModel(model_type, api_key="sglang")
    assert model.model_type == model_type
    assert model.model_config_dict == SGLangConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type, UnifiedModelType)
    assert isinstance(model.token_limit, int)


@pytest.mark.model_backend
def test_sglang_model_unexpected_argument():
    model_type = ModelType.GPT_4
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into SGLang model backend."
            )
        ),
    ):
        _ = SGLangModel(model_type, model_config_dict, api_key="sglang")


@pytest.mark.model_backend
def test_sglang_function_call():
    test_tool = {
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "Test function",
            "parameters": {"type": "object", "properties": {}},
        },
    }

    model = SGLangModel(
        ModelType.GPT_4,
        model_config_dict={"tools": [test_tool]},
        api_key="sglang",
    )

    messages = [
        {"role": "user", "content": "Use test_tool and respond with result"}
    ]

    response = model.run(messages=messages)

    assert len(response.choices[0].message.tool_calls) > 0
    tool_call = response.choices[0].message.tool_calls[0]
    assert tool_call.function.name == "test_tool"
