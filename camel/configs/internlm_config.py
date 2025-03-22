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

from typing import Optional, Union

from camel.configs.base_config import BaseConfig


class InternLMConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    InternLM API. You can refer to the following link for more details:
    https://internlm.intern-ai.org.cn/api/document

    Args:
        stream (bool, optional): Whether to stream the response.
            (default: :obj:`False`)
        temperature (float, optional): Controls the diversity and focus of
            the generated results. Lower values make the output more focused,
            while higher values make it more diverse. (default: :obj:`0.8`)
        top_p (float, optional): Controls the diversity and focus of the
            generated results. Higher values make the output more diverse,
            while lower values make it more focused. (default: :obj:`0.9`)
        max_tokens (Union[int, NotGiven], optional): Allows the model to
            generate the maximum number of tokens.
            (default: :obj:`NOT_GIVEN`)
        tools (list, optional): Specifies an array of tools that the model can
            call. It can contain one or more tool objects. During a function
            call process, the model will select one tool from the array.
            (default: :obj:`None`)
        tool_choice (Union[dict[str, str], str], optional): Controls which (if
            any) tool is called by the model. :obj:`"none"` means the model
            will not call any tool and instead generates a message.
            :obj:`"auto"` means the model can pick between generating a
            message or calling one or more tools.  :obj:`"required"` means the
            model must call one or more tools. Specifying a particular tool
            via {"type": "function", "function": {"name": "my_function"}}
            forces the model to call that tool. :obj:`"none"` is the default
            when no tools are present. :obj:`"auto"` is the default if tools
            are present.
    """

    stream: bool = False
    temperature: float = 0.8
    top_p: float = 0.9
    max_tokens: Optional[int] = None
    tool_choice: Optional[Union[dict[str, str], str]] = None


INTERNLM_API_PARAMS = {param for param in InternLMConfig.model_fields.keys()}
