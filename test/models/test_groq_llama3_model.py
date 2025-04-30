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

from camel.configs import GroqConfig
from camel.models import GroqModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.GROQ_LLAMA_3_8B,
        ModelType.GROQ_LLAMA_3_70B,
    ],
)
def test_groq_llama3_model(model_type: ModelType):
    model_config_dict = GroqConfig().as_dict()
    model = GroqModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    # LLM served by Groq does not support token counter, so Camel uses
    # OpenAITokenCounter as a placeholder.
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_groq_llama3_model_unexpected_argument():
    model_type = ModelType.GROQ_LLAMA_3_70B
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            (
                "Unexpected argument `model_path` is "
                "input into Groq model backend."
            )
        ),
    ):
        _ = GroqModel(model_type, model_config_dict)
