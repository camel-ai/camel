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
from typing import Dict, Optional, Union

from camel.configs.base_config import BaseConfig


class BedrockConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using OpenAI
    compatibility.

    Args:
        max_tokens (int, optional): The maximum number of tokens to generate
            in the chat completion. The total length of input tokens and
            generated tokens is limited by the model's context length.
            (default: :obj:`None`)
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`None`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`None`)
        top_k (int, optional): The number of top tokens to consider.
        stream (bool, optional): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            (default: :obj:`None`)
        tools (list[FunctionTool], optional): A list of tools the model may
            call. Currently, only functions are supported as a tool. Use this
            to provide a list of functions the model may generate JSON inputs
            for. A max of 128 functions are supported.
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
        reasoning_effort(str, optional): A parameter specifying the level of
            reasoning used by certain model types. Valid values are :obj:
            `"low"`, :obj:`"medium"`, or :obj:`"high"`. If set, it is only
            applied to the model types that support it (e.g., :obj:`o1`,
            :obj:`o1mini`, :obj:`o1preview`, :obj:`o3mini`). If not provided
            or if the model type does not support it, this parameter is
            ignored. (default: :obj:`None`)
    """

    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stream: Optional[bool] = None
    tool_choice: Optional[Union[Dict[str, str], str]] = None
    reasoning_effort: Optional[str] = None


BEDROCK_API_PARAMS = {param for param in BedrockConfig.model_fields.keys()}
