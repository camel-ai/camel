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

from typing import List, Optional

from camel.configs.base_config import BaseConfig


class AnthropicConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Anthropic API.

    See: https://docs.anthropic.com/en/api/messages

    Args:
        max_tokens (int, optional): The maximum number of tokens to
            generate before stopping. Note that Anthropic models may stop
            before reaching this maximum. This parameter only specifies the
            absolute maximum number of tokens to generate.
            (default: :obj:`None`)
        stop_sequences (List[str], optional): Custom text sequences that will
            cause the model to stop generating. The models will normally stop
            when they have naturally completed their turn. If the model
            encounters one of these custom sequences, the response will be
            terminated and the stop_reason will be "stop_sequence".
            (default: :obj:`None`)
        temperature (float, optional): Amount of randomness injected into the
            response. Defaults to 1. Ranges from 0 to 1. Use temp closer to 0
            for analytical / multiple choice, and closer to 1 for creative
            and generative tasks. Note that even with temperature of 0.0, the
            results will not be fully deterministic. (default: :obj:`None`)
        top_p (float, optional): Use nucleus sampling. In nucleus sampling, we
            compute the cumulative distribution over all the options for each
            subsequent token in decreasing probability order and cut it off
            once it reaches a particular probability specified by `top_p`.
            You should either alter `temperature` or `top_p`,
            but not both. (default: :obj:`None`)
        top_k (int, optional): Only sample from the top K options for each
            subsequent token. Used to remove "long tail" low probability
            responses. (default: :obj:`None`)
        stream (bool, optional): Whether to incrementally stream the response
            using server-sent events. (default: :obj:`None`)
        metadata (dict, optional): An object describing
            metadata about the request. Can include user_id as an external
            identifier for the user associated with the request.
            (default: :obj:`None`)
        tool_choice (dict, optional): How the model should
            use the provided tools. The model can use a specific tool, any
            available tool, decide by itself, or not use tools at all.
            (default: :obj:`None`)
        extra_headers (Optional[dict], optional): Additional headers for the
            request. (default: :obj:`None`)
        extra_body (dict, optional): Extra body parameters to be passed to
            the Anthropic API.
    """

    max_tokens: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stream: Optional[bool] = None
    metadata: Optional[dict] = None
    tool_choice: Optional[dict] = None
    extra_headers: Optional[dict] = None
    extra_body: Optional[dict] = None


ANTHROPIC_API_PARAMS = {param for param in AnthropicConfig.model_fields.keys()}
