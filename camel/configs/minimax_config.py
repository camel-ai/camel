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

from typing import Optional, Sequence, Union

from camel.configs.base_config import BaseConfig


class MinimaxConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using OpenAI
    compatibility with Minimax.

    Reference: https://api.minimax.chat/document/guides/chat-model

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0.0` and :obj:`1.0`. Higher values make the output more
            random, while lower values make it more focused and deterministic.
            Recommended to use :obj:`1.0`. Values outside this range will
            return an error. (default: :obj:`None`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`None`)
        n (int, optional): How many chat completion choices to generate for
            each input message. Only supports value :obj:`1`.
            (default: :obj:`None`)
        response_format (object, optional): An object specifying the format
            that the model must output. Setting to
            {"type": "json_object"} enables JSON mode, which guarantees the
            message the model generates is valid JSON. Important: when using
            JSON mode, you must also instruct the model to produce JSON
            yourself via a system or user message. Without this, the model
            may generate an unending stream of whitespace until the generation
            reaches the token limit, resulting in a long-running and seemingly
            "stuck" request. Also note that the message content may be
            partially cut off if finish_reason="length", which indicates the
            generation exceeded max_tokens or the conversation exceeded the
            max context length. (default: :obj:`None`)
        stream (bool, optional): If set, partial message deltas will be sent,
            like in ChatGPT. Tokens will be sent as data-only server-sent
            events as they become available, with the stream terminated by
            a data: [DONE] message. (default: :obj:`None`)
        stop (str or list, optional): Up to :obj:`4` sequences where the API
            will stop generating further tokens. (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens to generate
            in the chat completion. The total length of input tokens and
            generated tokens is limited by the model's context length.
            (default: :obj:`None`)
        user (str, optional): A unique identifier representing your end-user,
            which can help to monitor and detect abuse.
            (default: :obj:`None`)
        tool_choice (Union[dict[str, str], str], optional): Controls which (if
            any) tool is called by the model. :obj:`"none"` means the model
            will not call any tool and instead generates a message.
            :obj:`"auto"` means the model can pick between generating a
            message or calling one or more tools.  :obj:`"required"` means the
            model must call one or more tools. Specifying a particular tool
            via {"type": "function", "function": {"name": "my_function"}}
            forces the model to call that tool. :obj:`"none"` is the default
            when no tools are present. :obj:`"auto"` is the default if tools
            are present.

    Note:
        Some OpenAI parameters such as presence_penalty, frequency_penalty,
        and logit_bias will be ignored by Minimax.
    """

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[Union[str, Sequence[str]]] = None
    max_tokens: Optional[int] = None
    response_format: Optional[dict] = None
    user: Optional[str] = None
    tool_choice: Optional[Union[dict[str, str], str]] = None


MINIMAX_API_PARAMS = {param for param in MinimaxConfig.model_fields.keys()}
