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

from typing import Any, Dict, Optional, Union

from camel.configs.base_config import BaseConfig


class SambaFastAPIConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    SambaNova Fast API.

    Args:
        max_tokens (Optional[int], optional): the maximum number of tokens to
            generate, e.g. 100.
            (default: :obj:`2048`)
        stop (Optional[Union[str,list[str]]]): Stop generation if this token
            is detected. Or if one of these tokens is detected when providing
            a string list.
            (default: :obj:`None`)
        stream (Optional[bool]): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            Currently SambaNova Fast API only support stream mode.
            (default: :obj:`True`)
        stream_options (Optional[Dict]): Additional options for streaming.
            (default: :obj:`{"include_usage": True}`)
    """

    max_tokens: Optional[int] = 2048
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = True
    stream_options: Optional[Dict] = {"include_usage": True}  # noqa: RUF012

    def as_dict(self) -> dict[str, Any]:
        config_dict = super().as_dict()
        if "tools" in config_dict:
            del config_dict["tools"]  # SambaNova does not support tool calling
        return config_dict


SAMBA_FAST_API_PARAMS = {
    param for param in SambaFastAPIConfig().model_fields.keys()
}


class SambaVerseAPIConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    SambaVerse API.

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`0.7`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`0.95`)
        top_k (int, optional): Only sample from the top K options for each
            subsequent token. Used to remove "long tail" low probability
            responses.
            (default: :obj:`50`)
        max_tokens (Optional[int], optional): The maximum number of tokens to
            generate, e.g. 100.
            (default: :obj:`2048`)
        repetition_penalty (Optional[float], optional): The parameter for
            repetition penalty. 1.0 means no penalty.
            (default: :obj:`1.0`)
        stop (Optional[Union[str,list[str]]]): Stop generation if this token
            is detected. Or if one of these tokens is detected when providing
            a string list.
            (default: :obj:`""`)
        stream (Optional[bool]): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            Currently SambaVerse API doesn't support stream mode.
            (default: :obj:`False`)
    """

    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.95
    top_k: Optional[int] = 50
    max_tokens: Optional[int] = 2048
    repetition_penalty: Optional[float] = 1.0
    stop: Optional[Union[str, list[str]]] = ""
    stream: Optional[bool] = False

    def as_dict(self) -> dict[str, Any]:
        config_dict = super().as_dict()
        if "tools" in config_dict:
            del config_dict["tools"]  # SambaNova does not support tool calling
        return config_dict


SAMBAVERSE_API_PARAMS = {
    param for param in SambaVerseAPIConfig().model_fields.keys()
}
