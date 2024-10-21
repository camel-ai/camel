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

from typing import Sequence, Union

from openai._types import NOT_GIVEN, NotGiven

from camel.configs.base_config import BaseConfig


class NexaConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using Nexa API

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`0.7`)
        max_tokens (int, optional): The maximum number of new tokens to
            generate in the chat completion. The total length of input tokens
            and generated tokens is limited by the model's context length.
            (default: :obj:`1024`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`1.0`)
        stream (bool, optional): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            (default: :obj:`False`)
        stop (str or list, optional): List of stop words for early stopping
            generating further tokens. (default: :obj:`None`)

    """

    temperature: float = 0.7
    max_tokens: int = 1024
    top_p: float = 1.0
    stream: bool = False
    stop: Union[str, Sequence[str], NotGiven] = NOT_GIVEN


NEXA_API_PARAMS = {param for param in NexaConfig.model_fields.keys()}
