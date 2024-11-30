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
from camel.types import NOT_GIVEN, NotGiven


class SGLANGConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    OpenAI API.

    Reference: https://sgl-project.github.io/references/sampling_params.html

    Args:
        stop (str or list, optional): Up to :obj:`4` sequences where the API
            will stop generating further tokens. (default: :obj:`None`)
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`1.0`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`1.0`)
        n (int, optional): How many chat completion choices to generate for
            each input message. (default: :obj:`1`)
        frequency_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on their
            existing frequency in the text so far, decreasing the model's
            likelihood to repeat the same line verbatim. See more information
            about frequency and presence penalties. (default: :obj:`0.0`)
        presence_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on whether
            they appear in the text so far, increasing the model's likelihood
            to talk about new topics. See more information about frequency and
            presence penalties. (default: :obj:`0.0`)
        stop_token_ids (list, optional): A list of token IDs where the model
            will stop generating tokens (default: :obj:`[]`).
        max_new_tokens (int, optional): Maximum number of new tokens to
            generate. (default: :obj:`128`)
        ignore_eos (bool, optional): Whether to ignore the EOS token during
            generation. (default: :obj:`False`)
        skip_special_tokens (bool, optional): Whether to skip special tokens
            during detokenization. (default: :obj:`True`)
        spaces_between_special_tokens (bool, optional):
            Whether to add spaces between special tokens during detokenization.
            (default: :obj:`True`)
        regex (str, optional): A regular expression to constrain the output
            tokens. (default: :obj:`None`)
        json_schema (str, optional): JSON schema to constrain the output
            structure. (default: :obj:`None`)
        min_new_tokens (int, optional): Minimum number of new tokens to
            generate. (default: :obj:`0`)
        top_k (int, optional): The number of highest probability tokens to
            consider during sampling. Setting it to a positive integer limits
            the number of tokens to sample from. A value of `-1` means no
            limit. (default: :obj:`-1`)
        min_p (float, optional): Minimum probability for nucleus sampling.
            Any token with a probability lower than `min_p` will be ignored.
            (default: :obj:`0.0`)
        repetition_penalty (float, optional): A penalty for repeating tokens.
            Values greater than `1.0` discourage repetition, and values less
            than `1.0` encourage repetition. (default: :obj:`1.0`)
        logprob_start_len (int or list, optional): The starting token position
            for returning logprobs. If `None`, only the logprobs for output
            tokens will be returned. (default: :obj:`None`)
        top_logprobs_num (int or list, optional): The number of top logprobs to
            return at each position in the output sequence. If `None`, no
            logprobs are returned. (default: :obj:`None`)
        return_text_in_logprobs (bool, optional): Whether to include the
            generated text in the logprobs output. (default: :obj:`False`)
        stream (bool, optional): Whether to stream the generated output in
            chunks. If set to `True`, the response will be streamed as it is
            generated. (default: :obj:`False`)
        max_tokens (int, optional): The maximum number of tokens to generate
            in the chat completion. The total length of input tokens and
            generated tokens is limited by the model's context length.
            (default: :obj:`None`)
    """

    stop: Union[str, Sequence[str], NotGiven] = NOT_GIVEN
    temperature: float = 1.0
    top_p: float = 1.0
    n: int = 1
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_token_ids: Optional[Sequence[int]] = []
    max_new_tokens: int = 128
    ignore_eos: bool = False
    skip_special_tokens: bool = True
    spaces_between_special_tokens: bool = True
    regex: Optional[str] = None
    json_schema: Optional[str] = None
    min_new_tokens: int = 0
    top_k: int = -1
    min_p: float = 0.0
    repetition_penalty: float = 1.0
    logprob_start_len: Optional[Union[Sequence[int], int]] = None
    top_logprobs_num: Optional[Union[Sequence[int], int]] = None
    return_text_in_logprobs: bool = False
    stream: bool = False
    max_tokens: Union[int, NotGiven] = NOT_GIVEN


SGLANG_API_PARAMS = {param for param in SGLANGConfig.model_fields.keys()}
