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

from camel.configs import ZhipuAIConfig
from camel.models import ZhipuAIModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GLM_3_TURBO,
        ModelType.GLM_4,
        ModelType.GLM_4V,
        ModelType.GLM_4V_FLASH,
        ModelType.GLM_4V_PLUS_0111,
        ModelType.GLM_4_PLUS,
        ModelType.GLM_4_AIR,
        ModelType.GLM_4_AIR_0111,
        ModelType.GLM_4_AIRX,
        ModelType.GLM_4_LONG,
        ModelType.GLM_4_FLASHX,
        ModelType.GLM_4_FLASH,
        ModelType.GLM_ZERO_PREVIEW,
    ],
)
def test_zhipuai_model(model_type: ModelType):
    model = ZhipuAIModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == ZhipuAIConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)
