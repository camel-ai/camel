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

from typing import Optional, Sequence, Type, Union

from pydantic import BaseModel

from camel.configs.base_config import BaseConfig


class DeepSeekConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    DeepSeek API.

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`None`)
        top_p (float, optional): Controls the diversity and focus of the
            generated results. Higher values make the output more diverse,
            while lower values make it more focused. (default: :obj:`None`)
        response_format (object, optional): Specifies the format of the
            returned content. The available values are `{"type": "text"}` or
            `{"type": "json_object"}`. Setting it to `{"type": "json_object"}`
            will output a standard JSON string.
            (default: :obj:`None`)
        stream (bool, optional): If set, partial message deltas will be sent.
            Tokens will be sent as data-only server-sent events (SSE) as
            they become available, with the stream terminated by a
            data: [DONE] message. (default: :obj:`None`)
        stop (Union[str, list[str]], optional): Up to 16 sequences where
            the API will stop generating further tokens. (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens that can
            be generated in the chat completion. The total length of input
            tokens and generated tokens is limited by the model's context
            length. (default: :obj:`None`)
        presence_penalty (float, optional): Number between -2.0 and 2.0.
            Positive values penalize new tokens based on whether they
            appear in the text so far, increasing the model's likelihood
            to talk about new topics. (default: :obj:`None`)
        frequency_penalty (float, optional): Number between -2.0 and 2.0.
            Positive values penalize new tokens based on their existing
            frequency in the text so far, decreasing the model's likelihood
            to repeat the same line verbatim. (default: :obj:`None`)
        tools (list[FunctionTool], optional): A list of tools the model may
            call. Currently, only functions are supported as a tool. Use
            this to provide a list of functions the model may generate JSON
            inputs for. A max of 128 functions are supported.
            (default: :obj:`None`)
        tool_choice (Union[dict[str, str], str], optional): Controls which
            (if any) tool is called by the model. "none" means the model
            will not call any tool and instead generates a message. "auto"
            means the model can pick between generating a message or calling
            one or more tools. "required" means the model must call one or
            more tools. Specifying a particular tool via
            {"type": "function", "function": {"name": "my_function"}} forces
            the model to call that tool. "none" is the default when no tools
            are present. "auto" is the default if tools are present.
            (default: :obj:`None`)
        logprobs (bool, optional): Whether to return log probabilities of
            the output tokens or not. If true, returns the log probabilities
            of each output token returned in the content of message.
            (default: :obj:`None`)
        top_logprobs (int, optional): An integer between 0 and 20 specifying
            the number of most likely tokens to return at each token
            position, each with an associated log probability. logprobs
            must be set to true if this parameter is used.
            (default: :obj:`None`)
        include_usage (bool, optional): When streaming, specifies whether to
            include usage information in `stream_options`.
            (default: :obj:`None`)
    """

    temperature: Optional[float] = None  # deepseek default: 1.0
    top_p: Optional[float] = None
    stream: Optional[bool] = None
    stop: Optional[Union[str, Sequence[str]]] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[Union[Type[BaseModel], dict]] = None
    frequency_penalty: Optional[float] = None
    tool_choice: Optional[Union[dict[str, str], str]] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None

    def __init__(self, include_usage: bool = True, **kwargs):
        super().__init__(**kwargs)
        # Only set stream_options when stream is True
        # Otherwise, it will raise error when calling the API
        if self.stream:
            self.stream_options = {"include_usage": include_usage}


DEEPSEEK_API_PARAMS = {param for param in DeepSeekConfig.model_fields.keys()}
