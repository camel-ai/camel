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

from camel.configs import WatsonXConfig
from camel.models import ModelFactory, WatsonXModel
from camel.types import ModelPlatformType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "meta-llama/llama-3-3-70b-instruct",
        "ibm/granite-3-8b-instruct",
        "mistralai/mistral-large",
    ],
)
def test_watsonx_model(model_type):
    # Skip test as it requires valid WatsonX API credentials
    pytest.skip("Skipping test that requires valid WatsonX API credentials")

    model_config_dict = WatsonXConfig().as_dict()
    model = WatsonXModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        "meta-llama/llama-3-3-70b-instruct",
        "ibm/granite-3-8b-instruct",
    ],
)
def test_watsonx_model_create(model_type):
    # Skip test as it requires valid WatsonX API credentials
    pytest.skip("Skipping test that requires valid WatsonX API credentials")

    model = ModelFactory.create(
        model_platform=ModelPlatformType.WATSONX,
        model_type=model_type,
        model_config_dict=WatsonXConfig(temperature=0.7).as_dict(),
    )
    assert model.model_type == model_type


@pytest.mark.model_backend
def test_watsonx_model_unexpected_argument():
    model_type = "meta-llama/llama-3-3-70b-instruct"
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into WatsonX model backend."
            )
        ),
    ):
        _ = WatsonXModel(model_type, model_config_dict)
