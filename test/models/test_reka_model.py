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

from camel.configs import RekaConfig
from camel.models import RekaModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.REKA_CORE,
        ModelType.REKA_EDGE,
        ModelType.REKA_FLASH,
    ],
)
def test_reka_model(model_type: ModelType):
    model = RekaModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == RekaConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


def _mock_reka_response(finish_reason):
    return SimpleNamespace(
        id="resp-1",
        model="reka-core",
        usage=SimpleNamespace(input_tokens=5, output_tokens=3),
        responses=[
            SimpleNamespace(
                message=SimpleNamespace(role="assistant", content="hi"),
                finish_reason=finish_reason,
            )
        ],
    )


@pytest.mark.parametrize(
    "reka_reason,expected",
    [
        ("stop", "stop"),
        ("length", "length"),
        ("context", "length"),
        (None, None),
    ],
)
def test_convert_reka_to_openai_response_maps_finish_reason(
    reka_reason, expected
):
    r"""Reka's finish_reason values must land in the OpenAI contract.

    Reka's own "context" (context window exhausted) is not a value OpenAI's
    finish_reason accepts; it must be reported as "length", the closest
    OpenAI analog for a token/context-budget stop.
    """
    model = object.__new__(RekaModel)
    response = _mock_reka_response(reka_reason)

    result = model._convert_reka_to_openai_response(response)

    assert result.choices[0].finish_reason == expected


def test_map_finish_reason_unknown_value_raises():
    with pytest.raises(ValueError, match="Unknown Reka finish reason"):
        RekaModel._map_finish_reason("some_new_reason")
