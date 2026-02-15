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

from typing import Optional

from camel.configs.base_config import BaseConfig


class VolcanoConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Volcano Engine API.

    Args:
        temperature (Optional[float], optional): Sampling temperature to use.
            (default: :obj:`None`)
        max_tokens (Optional[int], optional): The maximum number of tokens to
            generate in the chat completion.
            (default: :obj:`None`)
        stream (Optional[bool], optional): Whether to stream the response.
            (default: :obj:`None`)
        interleaved_thinking (Optional[bool], optional): Whether to enable
            interleaved thinking mode for doubao-seed models. When enabled,
            the model performs step-by-step reasoning while dynamically
            invoking tools.
            (default: :obj:`None`)
    """

    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = None
    interleaved_thinking: Optional[bool] = None


VOLCANO_API_PARAMS = {param for param in VolcanoConfig.model_fields.keys()}
