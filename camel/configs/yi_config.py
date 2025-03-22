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
from __future__ import annotations

from typing import Optional, Union

from camel.configs.base_config import BaseConfig
from camel.types import NOT_GIVEN, NotGiven


class YiConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Yi API. You can refer to the following link for more details:
    https://platform.lingyiwanwu.com/docs/api-reference

    Args:
        tool_choice (Union[dict[str, str], str], optional): Controls which (if
            any) tool is called by the model. :obj:`"none"` means the model
            will not call any tool and instead generates a message.
            :obj:`"auto"` means the model can pick between generating a
            message or calling one or more tools. :obj:`"required"` or
            specifying a particular tool via
            {"type": "function", "function": {"name": "some_function"}}
            can be used to guide the model to use tools more strongly.
            (default: :obj:`None`)
        max_tokens (int, optional): Specifies the maximum number of tokens
            the model can generate. This sets an upper limit, but does not
            guarantee that this number will always be reached.
            (default: :obj:`5000`)
        top_p (float, optional): Controls the randomness of the generated
            results. Lower values lead to less randomness, while higher
            values increase randomness. (default: :obj:`0.9`)
        temperature (float, optional): Controls the diversity and focus of
            the generated results. Lower values make the output more focused,
            while higher values make it more diverse. (default: :obj:`0.3`)
        stream (bool, optional): If True, enables streaming output.
            (default: :obj:`False`)
    """

    tool_choice: Optional[Union[dict[str, str], str]] = None
    max_tokens: Union[int, NotGiven] = NOT_GIVEN
    top_p: float = 0.9
    temperature: float = 0.3
    stream: bool = False


YI_API_PARAMS = {param for param in YiConfig.model_fields.keys()}
