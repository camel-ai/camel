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

from typing import Sequence, Union

from camel.configs.base_config import BaseConfig
from camel.types import NOT_GIVEN, NotGiven


class SGLangConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    OpenAI API.

    Reference: https://sgl-project.github.io/references/sampling_params.html

    Args:
        stop (str or list, optional): Up to :obj:`4` sequences where the API
            will stop generating further tokens. (default: :obj:`None`)
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`1.0`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`1.0`)
        n (int, optional): How many chat completion choices to generate for
            each input message. (default: :obj:`1`)
        frequency_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on their
            existing frequency in the text so far, decreasing the model's
            likelihood to repeat the same line verbatim. See more information
            about frequency and presence penalties. (default: :obj:`0.0`)
        presence_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on whether
            they appear in the text so far, increasing the model's likelihood
            to talk about new topics. See more information about frequency and
            presence penalties. (default: :obj:`0.0`)
        stream (bool, optional): Whether to stream the generated output in
            chunks. If set to `True`, the response will be streamed as it is
            generated. (default: :obj:`False`)
        max_tokens (int, optional): The maximum number of tokens to generate
            in the chat completion. The total length of input tokens and
            generated tokens is limited by the model's context length.
            (default: :obj:`None`)
        tools (list[FunctionTool], optional): A list of tools the model may
            call. Currently, only functions are supported as a tool. Use this
            to provide a list of functions the model may generate JSON inputs
            for. A max of 128 functions are supported.
    """

    stop: Union[str, Sequence[str], NotGiven] = NOT_GIVEN
    temperature: float = 1.0
    top_p: float = 1.0
    n: int = 1
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False
    max_tokens: Union[int, NotGiven] = NOT_GIVEN


SGLANG_API_PARAMS = {param for param in SGLangConfig.model_fields.keys()}
