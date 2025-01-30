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


class MoonshotConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Moonshot API. You can refer to the following link for more details:
    https://platform.moonshot.cn/docs/api-reference

    Args:
        stream (bool, optional): Whether to stream the response.
            (default: :obj:`False`)
        temperature (float, optional): Controls randomness in the response.
            Lower values make the output more focused and deterministic.
            (default: :obj:`0.3`)
        max_tokens (int, optional): The maximum number of tokens to generate.
            (default: :obj:`None`)
        tools (list, optional): List of tools that model can use for function
            calling. Each tool should be a dictionary containing type, function
            name, description, and parameters.
            (default: :obj:`None`)
    """

    stream: bool = False
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    tools: Optional[list] = None


MOONSHOT_API_PARAMS = {param for param in MoonshotConfig.model_fields.keys()}
