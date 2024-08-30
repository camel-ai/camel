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

from typing import Any

from camel.configs.base_config import BaseConfig


class InternLMConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    OpenAI API.

    Args:
        operation_mode (str, optional): Operation mode for InternLM, currently 
            support `"chat"`, `"write_webpage"`, `"resume_2_webpage"`, `"write_article"`. (default: :obj:`chat`)
        device (str, optional): Device for the model running, currently 
            support `"cuda"`,`"cpu"` . (default: :obj:`cuda`)
    """
    operation_mode: str = "chat"
    device: str = "cuda"

    def as_dict(self) -> dict[str, Any]:
        config_dict = super().as_dict()
        config_dict.pop("tools", None)  # Tool calling is not support
        return config_dict


INTERNLM_API_PARAMS = {
    param for param in InternLMConfig.model_fields.keys()
}
