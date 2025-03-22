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

from typing import Any, Optional, Sequence, Type, Union

from pydantic import BaseModel

from camel.configs.base_config import BaseConfig
from camel.types import NOT_GIVEN


class SiliconFlowConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    SiliconFlow API.

    Args:
        temperature (float, optional): Determines the degree of randomness
            in the response. (default: :obj:`None`)
        top_p (float, optional): The top_p (nucleus) parameter is used to
            dynamically adjust the number of choices for each predicted token
            based on the cumulative probabilities. (default: :obj:`None`)
        n (int, optional): Number of generations to return.
            (default: :obj:`None`)
        response_format (object, optional): An object specifying the format
            that the model must output. (default: :obj:`None`)
        stream (bool, optional): If set, tokens are returned as Server-Sent
            Events as they are made available. (default: :obj:`None`)
        stop (str or list, optional): Up to :obj:`4` sequences where the API
            will stop generating further tokens. (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens to generate.
            (default: :obj:`None`)
        frequency_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on their
            existing frequency in the text so far, decreasing the model's
            likelihood to repeat the same line verbatim. See more information
            about frequency and presence penalties. (default: :obj:`None`)
        tools (list[FunctionTool], optional): A list of tools the model may
            call. Currently, only functions are supported as a tool. Use this
            to provide a list of functions the model may generate JSON inputs
            for. A max of 128 functions are supported. (default: :obj:`None`)
    """

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[Union[str, Sequence[str]]] = None
    max_tokens: Optional[int] = None
    response_format: Optional[Union[Type[BaseModel], dict]] = None
    frequency_penalty: Optional[float] = None

    def as_dict(self) -> dict[str, Any]:
        r"""Convert the current configuration to a dictionary.

        This method converts the current configuration object to a dictionary
        representation, which can be used for serialization or other purposes.

        Returns:
            dict[str, Any]: A dictionary representation of the current
                configuration.
        """
        config_dict = self.model_dump()
        if self.tools:
            from camel.toolkits import FunctionTool

            tools_schema = []
            for tool in self.tools:
                if not isinstance(tool, FunctionTool):
                    raise ValueError(
                        f"The tool {tool} should "
                        "be an instance of `FunctionTool`."
                    )
                tools_schema.append(tool.get_openai_tool_schema())
        config_dict["tools"] = NOT_GIVEN
        return config_dict


SILICONFLOW_API_PARAMS = {
    param for param in SiliconFlowConfig.model_fields.keys()
}
