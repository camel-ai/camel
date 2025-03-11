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

from typing import Any, ClassVar, List, Union

from camel.configs.base_config import BaseConfig
from camel.types import NotGiven


class AnthropicConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Anthropic API.

    See: https://docs.anthropic.com/en/api/messages
    Args:
        max_tokens (int, optional): The maximum number of tokens to
            generate before stopping. Note that Anthropic models may stop
            before reaching this maximum. This parameter only specifies the
            absolute maximum number of tokens to generate.
            (default: :obj:`8192`)
        stop_sequences (List[str], optional): Custom text sequences that will
            cause the model to stop generating. The models will normally stop
            when they have naturally completed their turn. If the model
            encounters one of these custom sequences, the response will be
            terminated and the stop_reason will be "stop_sequence".
            (default: :obj:`[]`)
        temperature (float, optional): Amount of randomness injected into the
            response. Defaults to 1. Ranges from 0 to 1. Use temp closer to 0
            for analytical / multiple choice, and closer to 1 for creative
            and generative tasks. Note that even with temperature of 0.0, the
            results will not be fully deterministic. (default: :obj:`1`)
        top_p (float, optional): Use nucleus sampling. In nucleus sampling, we
            compute the cumulative distribution over all the options for each
            subsequent token in decreasing probability order and cut it off
            once it reaches a particular probability specified by `top_p`.
            You should either alter `temperature` or `top_p`,
            but not both. (default: :obj:`0.7`)
        top_k (int, optional): Only sample from the top K options for each
            subsequent token. Used to remove "long tail" low probability
            responses. (default: :obj:`5`)
        stream (bool, optional): Whether to incrementally stream the response
            using server-sent events. (default: :obj:`False`)
        metadata (Union[dict, NotGiven], optional): An object describing
            metadata about the request. Can include user_id as an external
            identifier for the user associated with the request.
            (default: :obj:`NotGiven()`)
        thinking (Union[dict, NotGiven], optional): Configuration for enabling
            Claude's extended thinking. When enabled, responses include
            thinking content blocks showing Claude's thinking process.
            (default: :obj:`NotGiven()`)
        tool_choice (Union[dict, NotGiven], optional): How the model should
            use the provided tools. The model can use a specific tool, any
            available tool, decide by itself, or not use tools at all.
            (default: :obj:`NotGiven()`)
    """

    max_tokens: int = 8192
    stop_sequences: ClassVar[Union[List[str], NotGiven]] = []
    temperature: float = 1
    top_p: Union[float, NotGiven] = 0.7
    stream: bool = False
    metadata: Union[dict, NotGiven] = NotGiven()
    thinking: Union[dict, NotGiven] = NotGiven()
    tool_choice: Union[dict, NotGiven] = NotGiven()

    def as_dict(self) -> dict[str, Any]:
        config_dict = super().as_dict()
        # Create a list of keys to remove to avoid modifying dict
        keys_to_remove = [
            key
            for key, value in config_dict.items()
            if isinstance(value, NotGiven)
        ]

        for key in keys_to_remove:
            del config_dict[key]

        # remove some keys if thinking is enabled
        thinking_enabled = (
            not isinstance(self.thinking, NotGiven)
            and self.thinking["type"] == "enabled"
        )
        if thinking_enabled:
            # `top_p`, `top_k`, `temperature` must be unset when thinking is
            # enabled.
            config_dict.pop("top_k", None)
            config_dict.pop("top_p", None)
            config_dict.pop("temperature", None)
        return config_dict


ANTHROPIC_API_PARAMS = {param for param in AnthropicConfig.model_fields.keys()}
