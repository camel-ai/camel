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

from typing import Any, Optional, Union

from camel.configs.base_config import BaseConfig


class SambaConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    SambaNova API.

    Args:
        max_tokens (Optional[int], optional): the maximum number of tokens to
            generate, e.g. 100. Defaults to `None`.
        stop (Optional[Union[str,list[str]]]): Stop generation if this token
            is detected. Or if one of these tokens is detected when providing
            a string list. Defaults to `None`.
        stream (Optional[bool]): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            Currently SambaNova only support stream mode. Defaults to `True`.
    """

    max_tokens: Optional[int] = None
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = True

    def as_dict(self) -> dict[str, Any]:
        config_dict = super().as_dict()
        config_dict.pop("tools", None)  # Tool calling is not support
        return config_dict


SAMBA_API_PARAMS = {param for param in SambaConfig().model_fields.keys()}
