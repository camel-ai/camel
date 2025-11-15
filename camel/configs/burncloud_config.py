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
from typing import Optional, Sequence, Union

from camel.configs.base_config import BaseConfig
from camel.types import NotGiven


class BurnCloudConfig(BaseConfig):
    r"""Defines parameters for BurnCloud's OpenAI-compatible chat completions.

    Reference: https://docs.burncloud.com/books/api

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass.
        n (int, optional): How many chat completion choices to generate for
            each input message.
        response_format (object, optional): Response schema enforced by the
            model. Setting to {"type": "json_object"} enables JSON mode.
        stream (bool, optional): If True, partial deltas will be sent as
            server-sent events while tokens stream back.
        stop (str or list, optional): Up to :obj:`4` sequences where the API
            will stop generating further tokens.
        max_tokens (int, optional): Maximum number of tokens to generate in
            the chat completion. Total input + output tokens must stay within
            the model context window.
        presence_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on their
            appearance so far, encouraging new topics.
        frequency_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on existing
            frequency, reducing repetition.
        user (str, optional): Unique identifier for the end-user, useful for
            abuse monitoring.
        tools (list[FunctionTool], optional): Tool definitions the model can
            call. Currently supports function tools.
        tool_choice (Union[dict[str, str], str], optional): Controls which, if
            any, tool gets invoked by the model.
    """

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = None
    stop: Optional[Union[str, Sequence[str], NotGiven]] = None
    max_tokens: Optional[Union[int, NotGiven]] = None
    presence_penalty: Optional[float] = None
    response_format: Optional[Union[dict, NotGiven]] = None
    frequency_penalty: Optional[float] = None
    user: Optional[str] = None
    tool_choice: Optional[Union[dict[str, str], str]] = None


BURNCLOUD_API_PARAMS = {param for param in BurnCloudConfig.model_fields.keys()}
