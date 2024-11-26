# =========== Copyright 2024 @ CAMEL-AI.org. All Rights Reserved. ===========
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
# =========== Copyright 2024 @ CAMEL-AI.org. All Rights Reserved. ===========

import os
import re

import pytest

from camel.configs import NvidiaConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils import BaseTokenCounter

# Test configurations
TEST_JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImlzcyI6InVzZXJfaXNzdWVyIn0.eyJzdWIiOiJ0ZXN0IiwiaXNzIjoidXNlcl9pc3N1ZXIifQ.YZnNXUz9rzqRYg4jgzl4qjBRPtbGwVxuL"

@pytest.mark.model_backend
def test_nvidia_model():
    """Test basic NVIDIA model initialization and configuration.
    
    This test verifies:
    1. Model creation with default configuration
    2. Model type assignment
    3. Configuration dictionary validation
    4. Token counter initialization
    5. Token limit validation
    """
    model_type = ModelType.NVIDIA_LLAMA3_CHATQA_70B
    model_config_dict = NvidiaConfig().as_dict()
    
    # Set test API key
    os.environ["OPENAI_API_KEY"] = TEST_JWT
    
    model = ModelFactory.create(
        model_platform=ModelPlatformType.NVIDIA,
        model_type=model_type,
        model_config_dict=model_config_dict
    )
    assert model.model_type == model_type
    assert model.model_config_dict == model_config_dict
    assert isinstance(model._token_counter, BaseTokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_nvidia_model_unexpected_argument():
    """Test error handling for unexpected model configuration arguments.
    
    This test verifies that the model properly handles and raises errors
    when given unexpected configuration parameters.
    """
    model_type = ModelType.NVIDIA_LLAMA3_CHATQA_70B
    model_config_dict = {"model_path": "vicuna-7b-v1.5"}

    with pytest.raises(
        ValueError,
        match=re.escape("Unexpected parameter 'model_path' for NVIDIA API."),
    ):
        _ = ModelFactory.create(
            model_platform=ModelPlatformType.NVIDIA,
            model_type=model_type,
            model_config_dict=model_config_dict
        )
