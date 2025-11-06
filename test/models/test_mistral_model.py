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

from camel.configs import MistralConfig
from camel.models import MistralModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


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
