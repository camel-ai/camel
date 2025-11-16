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
"""
please set the below os environment:
export AZURE_OPENAI_BASE_URL=""

# if `AZURE_API_VERSION` is not set, the api_version parameter must be provided
export AZURE_API_VERSION=""
export AZURE_OPENAI_API_KEY=""
"""

import pytest

from camel.configs import ChatGPTConfig
from camel.models import AzureOpenAIModel, ModelFactory
from camel.types import ModelPlatformType, ModelType
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
    ],
)
def test_openai_model(model_type):
    model_config_dict = ChatGPTConfig().as_dict()
    model = AzureOpenAIModel(
        model_type,
        model_config_dict,
        api_version="2024-02-15-preview",
        api_key="test-key",
        url="https://test.openai.azure.com/",
    )
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GPT_3_5_TURBO,
        ModelType.GPT_4,
        ModelType.GPT_4_TURBO,
        ModelType.GPT_4O,
        ModelType.GPT_4O_MINI,
    ],
)
def test_openai_model_create(model_type: ModelType):
    model = ModelFactory.create(
        model_platform=ModelPlatformType.AZURE,
        model_type=model_type,
        model_config_dict=ChatGPTConfig(temperature=0.8, n=3).as_dict(),
        api_version="2024-02-15-preview",
        api_key="test-key",
        url="https://test.openai.azure.com/",
    )
    assert model.model_type == model_type
