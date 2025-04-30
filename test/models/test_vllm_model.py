# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2025 @ CAMEL-AI.org. All Rights Reserved. =========
import re

import pytest

from camel.configs import VLLMConfig
from camel.models import VLLMModel
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
def test_vllm_model(model_type: ModelType):
    model = VLLMModel(model_type, api_key="vllm")
    assert model.model_type == model_type
    assert model.model_config_dict == VLLMConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type, UnifiedModelType)
    assert isinstance(model.token_limit, int)


@pytest.mark.model_backend
def test_vllm_model_unexpected_argument():
    model_type = ModelType.GPT_4
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into vLLM model backend."
            )
        ),
    ):
        _ = VLLMModel(model_type, model_config_dict, api_key="vllm")
