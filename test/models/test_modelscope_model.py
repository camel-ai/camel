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

from camel.configs import ModelScopeConfig
from camel.models import ModelScopeModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.MODELSCOPE_QWEN_2_5_7B_INSTRUCT,
        ModelType.MODELSCOPE_QWEN_2_5_14B_INSTRUCT,
        ModelType.MODELSCOPE_QWEN_2_5_32B_INSTRUCT,
        ModelType.MODELSCOPE_QWEN_2_5_72B_INSTRUCT,
        ModelType.MODELSCOPE_QWEN_2_5_CODER_7B_INSTRUCT,
        ModelType.MODELSCOPE_QWEN_2_5_CODER_14B_INSTRUCT,
        ModelType.MODELSCOPE_QWEN_2_5_CODER_32B_INSTRUCT,
        ModelType.MODELSCOPE_QWQ_32B,
        ModelType.MODELSCOPE_QWQ_32B_PREVIEW,
        ModelType.MODELSCOPE_LLAMA_3_1_8B_INSTRUCT,
        ModelType.MODELSCOPE_LLAMA_3_1_70B_INSTRUCT,
        ModelType.MODELSCOPE_LLAMA_3_1_405B_INSTRUCT,
        ModelType.MODELSCOPE_LLAMA_3_3_70B_INSTRUCT,
        ModelType.MODELSCOPE_MINISTRAL_8B_INSTRUCT,
        ModelType.MODELSCOPE_DEEPSEEK_V3_0324,
    ],
)
def test_modelscope_model(model_type: ModelType):
    model = ModelScopeModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == ModelScopeConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)
