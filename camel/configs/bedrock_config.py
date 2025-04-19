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
from typing import Optional

from camel.configs.base_config import BaseConfig


class BedrockConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using Bedrock
    compatibility.

    Args:
        maxTokens (int, optional): The maximum number of tokens.
        temperatue (float, optional): Controls the randomness of the output.
        top_p (float, optional): Use nucleus sampling.
        top_k (int, optional): The number of top tokens to consider.
    """

    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None


BEDROCK_API_PARAMS = {param for param in BedrockConfig.model_fields.keys()}
