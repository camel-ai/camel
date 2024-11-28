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

from typing import List, Optional

from pydantic import Field

from camel.configs.base_config import BaseConfig


class PHIConfig(BaseConfig):
    r"""Defines the parameters for configuring the PHI model.

    Attributes:
        trust_remote_code (bool): Whether to trust remote code.
        Defaults to True.
        max_model_len (int): The maximum length of the model.
        Defaults to 4096.
        limit_mm_per_prompt (dict): The limit of multimodal data per prompt.
        Defaults to {"image": 2}.
        temperature (Optional[float]): The temperature to use for sampling.
        Defaults to None.
        max_tokens (Optional[int]): The maximum number of tokens to generate.
        Defaults to None.
        stop_token_ids (Optional[List[int]]):
        The token IDs to stop generation.Defaults to None.
        question (str): The question to ask the model.
        Defaults to an empty string.
        device (str): The device to use for running the model.
        Defaults to "auto".

    Example:
        >>> config = PHIConfig(temperature=0.5, max_tokens=100)
        >>> print(config.temperature)
        0.5
    """

    trust_remote_code: bool = True
    max_model_len: int = 4096
    limit_mm_per_prompt: dict = Field(default_factory=lambda: {"image": 2})
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    stop_token_ids: Optional[List[int]] = None
    question: str = ""
    device: str = "auto"

    class Config:
        arbitrary_types_allowed = True


PHI_API_PARAMS = {param for param in PHIConfig.model_fields.keys()}
