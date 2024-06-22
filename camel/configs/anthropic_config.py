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

from dataclasses import asdict, dataclass

from anthropic import NOT_GIVEN, NotGiven

from camel.configs.base_config import BaseConfig


@dataclass(frozen=True)
class AnthropicConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Anthropic API.

    See: https://docs.anthropic.com/claude/reference/complete_post
    Args:
        max_tokens (int, optional): The maximum number of tokens to
            generate before stopping. Note that Anthropic models may stop
            before reaching this maximum. This parameter only specifies the
            absolute maximum number of tokens to generate.
            (default: :obj:`256`)
        stop_sequences (List[str], optional): Sequences that will cause the
            model to stop generating completion text. Anthropic models stop
            on "\n\nHuman:", and may include additional built-in stop sequences
            in the future. By providing the stop_sequences parameter, you may
            include additional strings that will cause the model to stop
            generating.
        temperature (float, optional): Amount of randomness injected into the
            response. Defaults to 1. Ranges from 0 to 1. Use temp closer to 0
            for analytical / multiple choice, and closer to 1 for creative
            and generative tasks.
            (default: :obj:`1`)
        top_p (float, optional): Use nucleus sampling. In nucleus sampling, we
            compute the cumulative distribution over all the options for each
            subsequent token in decreasing probability order and cut it off
            once it reaches a particular probability specified by `top_p`.
            You should either alter `temperature` or `top_p`,
            but not both.
            (default: :obj:`0.7`)
        top_k (int, optional): Only sample from the top K options for each
            subsequent token. Used to remove "long tail" low probability
            responses.
            (default: :obj:`5`)
        metadata: An object describing metadata about the request.
        stream (bool, optional): Whether to incrementally stream the response
          using server-sent events.
            (default: :obj:`False`)

    """

    max_tokens: int = 256
    stop_sequences: list[str] | NotGiven = NOT_GIVEN
    temperature: float = 1
    top_p: float | NotGiven = NOT_GIVEN
    top_k: int | NotGiven = NOT_GIVEN
    metadata: NotGiven = NOT_GIVEN
    stream: bool = False


ANTHROPIC_API_PARAMS = {param for param in asdict(AnthropicConfig()).keys()}
