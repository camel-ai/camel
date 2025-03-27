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

from typing import List, Optional, Union

from camel.configs.base_config import BaseConfig


class MoonshotConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Moonshot API. You can refer to the following link for more details:
    https://platform.moonshot.cn/docs/api-reference

    Args:
        temperature (float, optional): Controls randomness in the response.
            Lower values make the output more focused and deterministic.
            (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens to generate.
            (default: :obj:`None`)
        stream (bool, optional): Whether to stream the response.
            (default: :obj:`False`)
        tools (list, optional): List of tools that the model can use for
            function calling. Each tool should be a dictionary containing
            type, function name, description, and parameters.
            (default: :obj:`None`)
        top_p (float, optional): Controls diversity via nucleus sampling.
            (default: :obj:`None`)
        n (int, optional): How many chat completion choices to generate for
            each input message.(default: :obj:`None`)
        presence_penalty (float, optional): Penalty for new tokens based on
            whether they appear in the text so far.
            (default: :obj:`None`)
        frequency_penalty (float, optional): Penalty for new tokens based on
            their frequency in the text so far.
            (default: :obj:`None`)
        stop (Optional[Union[str, List[str]]], optional): Up to 4 sequences
            where the API will stop generating further tokens.
            (default: :obj:`None`)
    """

    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = None
    tools: Optional[list] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    stop: Optional[Union[str, List[str]]] = None


MOONSHOT_API_PARAMS = {param for param in MoonshotConfig.model_fields.keys()}
