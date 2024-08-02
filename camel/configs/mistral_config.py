# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Dict, Optional, Union

from camel.configs.base_config import BaseConfig

if TYPE_CHECKING:
    from mistralai.models.chat_completion import (
        ResponseFormat,
    )

    from camel.toolkits import OpenAIFunction


@dataclass(frozen=True)
class MistralConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Mistral API.

    reference: https://github.com/mistralai/client-python/blob/9d238f88c41689821d7b08570f13b43426f97fd6/src/mistralai/client.py#L195

    Args:
        temperature (Optional[float], optional): temperature the temperature
            to use for sampling, e.g. 0.5.
        max_tokens (Optional[int], optional): the maximum number of tokens to
            generate, e.g. 100. Defaults to None.
        top_p (Optional[float], optional): the cumulative probability of
            tokens to generate, e.g. 0.9. Defaults to None.
        random_seed (Optional[int], optional): the random seed to use for
            sampling, e.g. 42. Defaults to None.
        safe_mode (bool, optional): deprecated, use safe_prompt instead.
            Defaults to False.
        safe_prompt (bool, optional): whether to use safe prompt, e.g. true.
            Defaults to False.
        response_format (Union[Dict[str, str], ResponseFormat): format of the
            response.
        tools (Optional[list[OpenAIFunction]], optional): a list of tools to
            use.
        tool_choice (str, optional): Controls which (if
            any) tool is called by the model. :obj:`"none"` means the model
            will not call any tool and instead generates a message.
            :obj:`"auto"` means the model can pick between generating a
            message or calling one or more tools.  :obj:`"any"` means the
            model must call one or more tools. :obj:`"auto"` is the default
            value.
    """

    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    random_seed: Optional[int] = None
    safe_mode: bool = False
    safe_prompt: bool = False
    response_format: Optional[Union[Dict[str, str], ResponseFormat]] = None
    tools: Optional[list[OpenAIFunction]] = None
    tool_choice: Optional[str] = "auto"

    def __post_init__(self):
        if self.tools is not None:
            object.__setattr__(
                self,
                'tools',
                [tool.get_openai_tool_schema() for tool in self.tools],
            )


MISTRAL_API_PARAMS = {param for param in asdict(MistralConfig()).keys()}
