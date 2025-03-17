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

from camel.configs import QwenConfig
from camel.models import QwenModel
from camel.types import ModelType


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.QWEN_MAX,
        ModelType.QWEN_PLUS,
        ModelType.QWEN_TURBO,
        ModelType.QWEN_LONG,
        ModelType.QWEN_VL_MAX,
        ModelType.QWEN_VL_PLUS,
        ModelType.QWEN_MATH_PLUS,
        ModelType.QWEN_MATH_TURBO,
        ModelType.QWEN_CODER_TURBO,
        ModelType.QWEN_2_5_CODER_32B,
        ModelType.QWEN_2_5_VL_72B,
        ModelType.QWEN_2_5_72B,
        ModelType.QWEN_2_5_32B,
        ModelType.QWEN_2_5_14B,
        ModelType.QWEN_QWQ_32B,
        ModelType.QWEN_QVQ_72B,
        ModelType.QWEN_QWQ_PLUS,
    ],
)
def test_qwen_model(model_type: ModelType):
    model = QwenModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == QwenConfig().as_dict()
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_qwen_model_unexpected_argument():
    model_type = ModelType.QWEN_MAX
    model_config_dict = {"model_path": "qwen-max"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into Qwen model backend."
            )
        ),
    ):
        _ = QwenModel(model_type, model_config_dict)
