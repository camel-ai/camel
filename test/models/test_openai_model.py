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
import re
from unittest.mock import patch

import pytest
import requests

from camel.configs import ChatGPTConfig, OpenSourceConfig
from camel.models import OpenAIModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", [
    ModelType.GPT_3_5_TURBO,
    ModelType.GPT_3_5_TURBO_16K,
    ModelType.GPT_4,
    ModelType.GPT_4_32K,
    ModelType.GPT_4_TURBO,
    ModelType.GPT_4_TURBO_VISION,
])
def test_openai_model(model_type):
    model_config_dict = ChatGPTConfig().__dict__
    model = OpenAIModel(model_type, model_config_dict)
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_openai_model_unexpected_argument():
    model_type = ModelType.GPT_4
    model_config = OpenSourceConfig(
        model_path="vicuna-7b-v1.5",
        server_url="http://localhost:8000/v1",
    )
    model_config_dict = model_config.__dict__

    with pytest.raises(
            ValueError, match=re.escape(("Unexpected argument `model_path` is "
                                         "input into OpenAI model backend."))):
        _ = OpenAIModel(model_type, model_config_dict)


# Used to obtain model information
def get_model_info():
    response = requests.get("http://server.com/model-info")
    return response.json()


@pytest.mark.model_backend
@pytest.mark.parametrize("model_type", list(ModelType))
def test_backend_model_matches_settings(model_type):
    # Create a data that simulates the response
    mock_response_data = {
        'model_type': model_type.value,
        'token_limit': model_type.token_limit
    }

    # Use patch to simulate requests.get method
    with patch('requests.get') as mock_get:
        # Set the value returned by the mock object
        mock_get.return_value.json.return_value = mock_response_data

        # Call the get_model_info function
        model_info = get_model_info()

        # Assert to ensure that the returned data is as expected
        assert model_info[
            'model_type'] == model_type.value, \
            "Model type does not match"
        assert model_info[
            'token_limit'] == model_type.token_limit, \
            "Token limit does not match"
