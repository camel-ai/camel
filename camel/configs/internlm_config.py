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

from typing import Any, Dict

from pydantic import Field

from camel.configs.base_config import BaseConfig


class InternLMConfig(BaseConfig):
    """Defines the parameters for generating chat completions using InternLM.

    Args:
        operation_mode (str, optional): Operation mode for InternLM, currently
            support `"chat"`, `"write_webpage"`, `"resume_2_webpage"`,
            `"write_article"`. (default: :obj:`"chat"`)
        device_map (str, optional): Device for the model running,and it allows
            Hugging Face to automatically select the best device, whether it's
            a GPU or CPU.
        model_kwargs (dict, optional): Model configuration for InternLM model.
        tokenizer_kwargs (dict, optional): Tokenizer configuration for InternLM
            model.
    """

    import torch

    operation_mode: str = "chat"
    device_map: str = "auto"
    max_tokens: int = 4096

    model_config: Dict[str, Any] = Field(
        default={
            "torch_dtype": torch.bfloat16,
            "trust_remote_code": True,
            "do_sample": False,
            "num_beams": 3,
            "use_meta": True,
        }
    )
    tokenizer_config: Dict[str, Any] = Field(
        default={
            "trust_remote_code": True,
        }
    )

    def as_dict(self) -> Dict[str, Any]:
        config_dict = super().as_dict()
        return config_dict
