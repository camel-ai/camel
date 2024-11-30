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

from typing import List, Optional

from camel.configs.base_config import BaseConfig


class CohereConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Cohere API.

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`0.3`)
        documents (list, optional): A list of relevant documents that the
            model can cite to generate a more accurate reply. Each document is
            either a string or document object with content and metadata.
            (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens the model
            will generate as part of the response. (default: :obj:`None`)
        stop_sequences (List(str), optional): A list of up to 5 strings that
            the model will use to stop generation. If the model generates a
            string that matches any of the strings in the list, it will stop
            generating tokens and return the generated text up to that point
            not including the stop sequence. (default: :obj:`None`)
        seed (int, optional): If specified, the backend will make a best
            effort to sample tokens deterministically, such that repeated
            requests with the same seed and parameters should return the same
            result. However, determinism cannot be totally guaranteed.
            (default: :obj:`None`)
        frequency_penalty (float, optional): Min value of `0.0`, max value of
            `1.0`. Used to reduce repetitiveness of generated tokens. The
            higher the value, the stronger a penalty is applied to previously
            present tokens, proportional to how many times they have already
            appeared in the prompt or prior generation. (default: :obj:`0.0`)
        presence_penalty (float, optional): Min value of `0.0`, max value of
            `1.0`. Used to reduce repetitiveness of generated tokens. Similar
            to `frequency_penalty`, except that this penalty is applied
            equally to all tokens that have already appeared, regardless of
            their exact frequencies. (default: :obj:`0.0`)
        k (int, optional): Ensures only the top k most likely tokens are
            considered for generation at each step. Min value of `0`, max
            value of `500`. (default: :obj:`0`)
        p (float, optional): Ensures that only the most likely tokens, with
            total probability mass of `p`, are considered for generation at
            each step. If both k and p are enabled, `p` acts after `k`. Min
            value of `0.01`, max value of `0.99`. (default: :obj:`0.75`)
    """

    temperature: Optional[float] = 0.2
    documents: Optional[list] = None
    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    seed: Optional[int] = None
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    k: Optional[int] = 0
    p: Optional[float] = 0.75


COHERE_API_PARAMS = {param for param in CohereConfig().model_fields.keys()}
