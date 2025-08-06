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

from camel.configs import CrynuxConfig
from camel.models import CrynuxModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.CRYNUX_QWEN_2_5_7B_INSTRUCT,
    ],
)
def test_crynux_model(model_type: ModelType):
    model = CrynuxModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == CrynuxConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_crynux_model_stream_property():
    model = CrynuxModel(ModelType.CRYNUX_QWEN_2_5_7B_INSTRUCT)
    assert model.stream is False
