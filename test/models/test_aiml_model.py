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

from camel.configs import AIMLConfig
from camel.models import AIMLModel
from camel.types import ModelType


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.AIML_MIXTRAL_8X7B,
        ModelType.AIML_MISTRAL_7B_INSTRUCT,
    ],
)
def test_aiml_model(model_type: ModelType):
    model = AIMLModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == AIMLConfig().as_dict()
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_aiml_model_unexpected_argument():
    model_type = ModelType.AIML_MIXTRAL_8X7B
    model_config_dict = {"model_path": "aiml_v1"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into AIML model backend."
            )
        ),
    ):
        _ = AIMLModel(model_type, model_config_dict)
