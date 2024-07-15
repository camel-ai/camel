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
from typing import List, Optional, Union

from anthropic._types import Literal

from camel.configs.base_config import BaseConfig


@dataclass(frozen=True)
class GroqLLAMA3Config(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    Anthropic API. And Camel does not support stream mode for GroqLLAMA3.

    See: https://console.groq.com/docs/text-chat
    Args:
        max_tokens (int, optional): The maximum number of tokens to generate
            before stopping. Note that Anthropic models may stop before
            reaching this maximum. This parameter only specifies the absolute
            maximum number of tokens to generate.
            (default: :obj:`256`)
        stop (str or List[str], optional): Up to 4 sequences where the API will
            stop generating further tokens. The returned text will not contain
            the stop sequence. (default: :obj:`None)
        temperature (float, optional): Amount of randomness injected into the
            response. Defaults to 1. Ranges from 0 to 1. Use temp closer to 0
            for analytical / multiple choice, and closer to 1 for creative
            and generative tasks.
            (default: :obj:`1`)
        stream (bool, optional): Whether to incrementally stream the response
            using server-sent events. Camel does not support stream mode for
            Groq Llama3.
            (default: :obj:`False`)
    """

    max_tokens: int = 4096  # since the Llama3 usually has a context
    # window of 8192 tokens, the default is set to 4096
    stop: Optional[Union[str, List[str]]] = None
    temperature: float = 1  # Camel does not suggest modifying the `top_p`
    # Camel does not support stream mode for Groq Llama3, the default value of
    # `stream` is False
    stream: Literal[False] = False


GROQ_LLAMA3_API_PARAMS = {param for param in asdict(GroqLLAMA3Config()).keys()}
