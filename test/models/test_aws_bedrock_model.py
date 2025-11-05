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

from camel.configs import BedrockConfig
from camel.models import AWSBedrockModel
from camel.types import ModelType
from camel.utils import OpenAITokenCounter


@pytest.mark.model_backend
@pytest.mark.parametrize(
    "model_type",
    [
        ModelType.AWS_CLAUDE_3_7_SONNET,
        ModelType.AWS_CLAUDE_3_5_SONNET,
        ModelType.AWS_CLAUDE_3_HAIKU,
        ModelType.AWS_CLAUDE_3_SONNET,
        ModelType.AWS_DEEPSEEK_R1,
        ModelType.AWS_LLAMA_3_3_70B_INSTRUCT,
        ModelType.AWS_LLAMA_3_2_90B_INSTRUCT,
        ModelType.AWS_LLAMA_3_2_11B_INSTRUCT,
    ],
)
def test_aws_bedrock_model(model_type: ModelType):
    r"""Test AWSBedrockModel initialization with different model types."""
    model = AWSBedrockModel(
        model_type,
        api_key="dummy_key",
        url="http://dummy.url",
    )
    assert model.model_type == model_type
    assert model.model_config_dict == BedrockConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_aws_bedrock_async_supported():
    r"""Test AWSBedrockModel async method is now supported.

    This test verifies that async inference is supported by ensuring
    it doesn't raise NotImplementedError. Instead, it should attempt
    to make a connection and fail with APIConnectionError due to
    invalid credentials in the test environment.
    """
    from openai import APIConnectionError

    model = AWSBedrockModel(
        ModelType.AWS_CLAUDE_3_HAIKU,
        api_key="dummy_key",
        url="http://dummy.url",
    )

    # Async should now be supported, so it should attempt to connect
    # and fail with a connection error (not NotImplementedError)
    with pytest.raises(APIConnectionError):
        await model._arun([{"role": "user", "content": "Test message"}])
