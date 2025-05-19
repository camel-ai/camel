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


class RekaConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Reka API.

    Reference: https://docs.reka.ai/api-reference/chat/create

    Args:
        temperature (Optional[float], optional): temperature the temperature
            to use for sampling, e.g. 0.5. (default: :obj:`None`)
        top_p (Optional[float], optional): the cumulative probability of
            tokens to generate, e.g. 0.9. (default: :obj:`None`)
        top_k (Optional[int], optional): Parameter which forces the model to
            only consider the tokens with the `top_k` highest probabilities at
            the next step. (default: :obj:`None`)
        max_tokens (Optional[int], optional): the maximum number of tokens to
            generate, e.g. 100. (default: :obj:`None`)
        stop (Optional[Union[str,list[str]]]): Stop generation if this token
            is detected. Or if one of these tokens is detected when providing
            a string list. (default: :obj:`None`)
        seed (Optional[int], optional): the random seed to use for sampling, e.
            g. 42. (default: :obj:`None`)
        presence_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on whether
            they appear in the text so far, increasing the model's likelihood
            to talk about new topics. See more information about frequency and
            presence penalties. (default: :obj:`None`)
        frequency_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on their
            existing frequency in the text so far, decreasing the model's
            likelihood to repeat the same line verbatim. See more information
            about frequency and presence penalties. (default: :obj:`None`)
        use_search_engine (Optional[bool]): Whether to consider using search
            engine to complete the request. Note that even if this is set to
            `True`, the model might decide to not use search.
            (default: :obj:`None`)
    """

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    seed: Optional[int] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    use_search_engine: Optional[bool] = None


REKA_API_PARAMS = {param for param in RekaConfig.model_fields.keys()}
