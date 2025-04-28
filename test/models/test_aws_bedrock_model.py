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
    model = AWSBedrockModel(model_type)
    assert model.model_type == model_type
    assert model.model_config_dict == BedrockConfig().as_dict()
    assert isinstance(model.token_counter, OpenAITokenCounter)
    assert isinstance(model.model_type.value_for_tiktoken, str)
    assert isinstance(model.model_type.token_limit, int)


@pytest.mark.model_backend
def test_aws_bedrock_model_unexpected_argument():
    r"""Test AWSBedrockModel with unexpected arguments."""
    model_type = ModelType.AWS_CLAUDE_3_HAIKU
    model_config_dict = {"model_path": "claude-3-haiku"}

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Invalid parameter 'model_path' in model_config_dict. "
            "Valid parameters are: "
        )
        + ".*",  # Match any characters after the message start
    ):
        _ = AWSBedrockModel(model_type, model_config_dict)


@pytest.mark.model_backend
@pytest.mark.asyncio
async def test_aws_bedrock_async_not_implemented():
    r"""Test AWSBedrockModel async method raising NotImplementedError."""
    model = AWSBedrockModel(ModelType.AWS_CLAUDE_3_HAIKU)

    with pytest.raises(
        NotImplementedError,
        match="AWS Bedrock does not support async inference.",
    ):
        await model._arun("Test message")
