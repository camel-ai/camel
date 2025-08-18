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

import pytest

from camel.configs import ChatGPTConfig
from camel.models import OpenAIModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GPT_3_5_TURBO,
        ModelType.GPT_4,
        ModelType.GPT_4_TURBO,
        ModelType.GPT_4O,
        ModelType.GPT_4O_MINI,
        ModelType.O1,
        ModelType.O1_PREVIEW,
        ModelType.O1_MINI,
        ModelType.GPT_4_5_PREVIEW,
        ModelType.GPT_5,
        ModelType.O3,
        ModelType.O3_PRO,
        ModelType.O3_MINI,
        ModelType.O4_MINI,
        ModelType.GPT_4_1,
        ModelType.GPT_4_1_MINI,
        ModelType.GPT_4_1_NANO,
    ],
)
def test_openai_model(model_type: ModelType):
    model = OpenAIModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == ChatGPTConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)
