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
    model: str = "microsoft/Phi-3.5-vision-instruct"
    trust_remote_code: bool = True
    max_model_len: int = 4096
    limit_mm_per_prompt: dict = Field(default_factory=lambda: {"image": 2})
    temperature: float = 0.0
    max_tokens: int = 128
    stop_token_ids: Optional[List[int]] = None
    method: str = "generate"
    image_urls: List[str] = Field(default_factory=list)
    question: str = ""

    class Config:
        arbitrary_types_allowed = True


PHI_API_PARAMS = {param for param in PHIConfig.model_fields.keys()}
