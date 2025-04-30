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

from typing import Dict, List, Literal, Optional

from camel.configs.base_config import BaseConfig


class WatsonXConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    IBM WatsonX API.

    See: https://ibm.github.io/watsonx-ai-python-sdk/fm_schema.html

    Args:
        frequency_penalty (float, optional): Number between -2.0 and 2.0.
            Positive values penalize new tokens based on their existing
            frequency in the text so far, decreasing the model's likelihood
            to repeat the same line verbatim.
            (default: :obj:`None`)
        logprobs (bool, optional): Whether to return log probabilities of the
            output tokens or not. If true, returns the log probabilities of
            each output token returned in the content of message.
            (default: :obj:`None`)
        top_logprobs (int, optional): An integer between 0 and 20 specifying
            the number of most likely tokens to return at each token position,
            each with an associated log probability.
            (default: :obj:`None`)
        presence_penalty (float, optional): Number between -2.0 and 2.0.
            Positive values penalize new tokens based on whether they appear
            in the text so far, increasing the model's likelihood to talk
            about new topics.
            (default: :obj:`None`)
        temperature (float, optional): What sampling temperature to use,
            between 0 and 2. Higher values like 0.8 will make the output
            more random, while lower values like 0.2 will make it more focused
            and deterministic. We generally recommend altering this or top_p
            but not both.
            (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens to generate
            in the chat completion. The total length of input tokens and
            generated tokens is limited by the model's context length.
            (default: :obj:`None`)
        time_limit (int, optional): The maximum amount of time in seconds
            that the API will spend generating a response.
            (default: :obj:`None`)
        top_p (float, optional): Controls the randomness of the generated
            results. Lower values lead to less randomness, while higher
            values increase randomness. (default: :obj:`None`)
        n (int, optional): How many chat completion choices to generate for
            each input message. Note that you will be charged based on the
            total number of tokens generated.
            (default: :obj:`None`)
        logit_biaslogit_bias (Optional[dict], optional): Modify probability
            of specific tokens appearing in the completion.
            (default: :obj:`None`)
        seed (int, optional): If specified, the system will make a best effort
            to sample deterministically, such that repeated requests with the
            same seed and parameters should return the same result.
            (default: :obj:`None`)
        stop (List[str], optional): Up to 4 sequences where the API will stop
            generating further tokens.
            (default: :obj:`None`)
        tool_choice_options (Literal["none", "auto"], optional): The options
            for the tool choice.
            (default: :obj:`"auto"`)
    """

    frequency_penalty: Optional[float] = None
    logprobs: Optional[bool] = None
    top_logprobs: Optional[int] = None
    presence_penalty: Optional[float] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    time_limit: Optional[int] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    logit_bias: Optional[Dict] = None
    seed: Optional[int] = None
    stop: Optional[List[str]] = None
    tool_choice_options: Literal["none", "auto"] = "auto"


WATSONX_API_PARAMS = {param for param in WatsonXConfig.model_fields.keys()}
