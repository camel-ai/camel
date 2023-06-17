# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
import pytest

from camel.configs import ChatGPTConfig
from camel.models import OpenAIModel
from camel.typing import ModelType


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", [
    ModelType.GPT_3_5_TURBO,
    ModelType.GPT_3_5_TURBO_16K,
    ModelType.GPT_4,
])
def test_openai_model(model_type):
    model_config_dict = ChatGPTConfig().__dict__
    model = OpenAIModel(model_type, model_config_dict)

    messages = [
        {
            "role": "system",
            "content": "Initialize system",
        },
        {
            "role": "user",
            "content": "Hello",
        },
    ]

    response = model.run(messages)
    assert isinstance(response, dict)
    assert "choices" in response
    assert isinstance(response["choices"], list)
    assert len(response["choices"]) > 0
    assert isinstance(response["choices"][0], dict)
    assert "message" in response["choices"][0]
    assert isinstance(response["choices"][0]["message"], dict)
    assert "role" in response["choices"][0]["message"]
    assert response["choices"][0]["message"]["role"] == "assistant"
