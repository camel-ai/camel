# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
from __future__ import annotations

from typing import List, Optional

from camel.configs.base_config import BaseConfig


class FunctionGemmaConfig(BaseConfig):
    r"""Defines the parameters for generating completions using FunctionGemma
    via Ollama's native API.

    FunctionGemma uses a custom chat template format for function calling
    that differs from OpenAI's format. This config is used with Ollama's
    /api/generate endpoint.

    Reference: https://github.com/ollama/ollama/blob/main/docs/api.md

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`None`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. (default: :obj:`0.95`)
        top_k (int, optional): Limits the next token selection to the K most
            probable tokens. (default: :obj:`64`)
        num_predict (int, optional): Maximum number of tokens to generate.
            (default: :obj:`None`)
        stop (list, optional): Sequences where the model will stop generating
            further tokens. (default: :obj:`None`)
        seed (int, optional): Random seed for reproducibility.
            (default: :obj:`None`)
    """

    temperature: Optional[float] = None
    top_p: Optional[float] = 0.95
    top_k: Optional[int] = 64
    num_predict: Optional[int] = None
    stop: Optional[List[str]] = None
    seed: Optional[int] = None


FUNCTION_GEMMA_API_PARAMS = {
    param for param in FunctionGemmaConfig.model_fields.keys()
}
