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

from __future__ import annotations

from typing import Dict, Optional, Sequence, Type, Union

from pydantic import BaseModel

from camel.configs.base_config import BaseConfig


class XAIConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    xAI native SDK (gRPC).

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`None`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens to generate
            in the chat completion. (default: :obj:`None`)
        stop (str or list, optional): Up to :obj:`4` sequences where the API
            will stop generating further tokens. (default: :obj:`None`)
        stream (bool, optional): If True, partial message deltas will be sent
            as they become available. (default: :obj:`None`)
        response_format (object, optional): An object specifying the format
            that the model must output. Setting to a Pydantic BaseModel enables
            JSON schema mode for structured outputs.
            (default: :obj:`None`)
        tool_choice (Union[dict[str, str], str], optional): Controls which (if
            any) tool is called by the model. :obj:`"none"` means the model
            will not call any tool. :obj:`"auto"` means the model can pick
            between generating a message or calling one or more tools.
            :obj:`"required"` means the model must call one or more tools.
            (default: :obj:`None`)
        reasoning_effort (str, optional): Controls the reasoning effort for
            reasoning models. Valid values: :obj:`"low"`, :obj:`"medium"`,
            :obj:`"high"`. (default: :obj:`None`)
        use_encrypted_content (bool, optional): If True, encrypted reasoning
            traces will be returned and preserved across conversation turns.
            This is required for multi-turn reasoning with thinking models.
            (default: :obj:`None`)
        store_messages (bool, optional): If True, request/response history is
            stored on xAI's servers for up to 30 days, enabling conversation
            chaining via previous_response_id. If False, history is managed
            locally. (default: :obj:`None`)
        frequency_penalty (float, optional): Penalizes new tokens based on
            their existing frequency in the text so far. Values between
            :obj:`-2.0` and :obj:`2.0`. (default: :obj:`None`)
        presence_penalty (float, optional): Penalizes new tokens based on
            whether they appear in the text so far. Values between
            :obj:`-2.0` and :obj:`2.0`. (default: :obj:`None`)
    """

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stop: Optional[Union[str, Sequence[str]]] = None
    stream: Optional[bool] = None
    response_format: Optional[Union[Type[BaseModel], dict]] = None
    tool_choice: Optional[
        Union[Dict[str, Union[str, Dict[str, str]]], str]
    ] = None
    reasoning_effort: Optional[str] = None
    use_encrypted_content: Optional[bool] = None
    store_messages: Optional[bool] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


XAI_API_PARAMS = {param for param in XAIConfig.model_fields.keys()}
