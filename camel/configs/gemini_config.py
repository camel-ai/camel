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


from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Optional

from google.generativeai import protos
from google.generativeai.types import (
    content_types,
    helper_types,
    safety_types,
)

from camel.configs.base_config import BaseConfig


@dataclass(frozen=True)
class GeminiConfig(BaseConfig):
    r"""A simple dataclass used to configure the generation parameters of
    `GenerativeModel.generate_content`.

    Arguments:
            contents: The contents serving as the model's prompt.
            generation_config: Overrides for the model's generation config.
                candidate_count:
                    Number of generated responses to return.
                stop_sequences:
                    The set of character sequences (up
                    to 5) that will stop output generation. If
                    specified, the API will stop at the first
                    appearance of a stop sequence. The stop sequence
                    will not be included as part of the response.
                max_output_tokens:
                    The maximum number of tokens to include in a
                    candidate.

                    If unset, this will default to output_token_limit specified
                    in the model's specification.
                temperature:
                    Controls the randomness of the output. Note: The
                    default value varies by model, see the `Model.temperature`
                    attribute of the `Model` returned the `genai.get_model`
                    function.

                    Values can range from [0.0,1.0], inclusive. A value closer
                    to 1.0 will produce responses that are more varied and
                    creative, while a value closer to 0.0 will typically result
                    in more straightforward responses from the model.
                top_p:
                    Optional. The maximum cumulative probability of tokens to
                    consider when sampling.

                    The model uses combined Top-k and nucleus sampling.

                    Tokens are sorted based on their assigned probabilities so
                    that only the most likely tokens are considered. Top-k
                    sampling directly limits the maximum number of tokens to
                    consider, while Nucleus sampling limits number of tokens
                    based on the cumulative probability.

                    Note: The default value varies by model, see the
                    `Model.top_p` attribute of the `Model` returned the
                    `genai.get_model` function.

                top_k (int):
                    Optional. The maximum number of tokens to consider when
                    sampling.

                    The model uses combined Top-k and nucleus sampling.

                    Top-k sampling considers the set of `top_k` most probable
                    tokens. Defaults to 40.

                    Note: The default value varies by model, see the
                    `Model.top_k` attribute of the `Model` returned the
                    `genai.get_model` function.

                response_mime_type:
                    Optional.
                    Output response mimetype of the generated candidate text.

                    Supported mimetype:
                        `text/plain`: (default) Text output.
                        `application/json`: JSON response in the candidates.

                response_schema:
                    Optional. Specifies the format of the JSON requested
                    if response_mime_type is `application/json`.

            safety_settings: Overrides for the model's safety settings.
            stream: If True, yield response chunks as they are generated.
            tools: `protos.Tools` more info coming soon.
            request_options: Options for the request.

    """

    candidate_count: Optional[int] = None
    stop_sequences: Optional[Iterable[str]] = None
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    response_mime_type: Optional[str] = None
    response_schema: Optional[protos.Schema] = None
    safety_settings: Optional[safety_types.SafetySettingOptions] = None
    stream: bool = False
    tools: Optional[content_types.FunctionLibraryType] = None
    tool_config: Optional[content_types.ToolConfigType] = None
    request_options: Optional[helper_types.RequestOptionsType] = None


@dataclass(frozen=True)
class Gemini_Gen_Config(BaseConfig):
    candidate_count: Optional[int] = None
    stop_sequences: Optional[Iterable[str]] = None
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    response_mime_type: Optional[str] = None
    response_schema: Optional[protos.Schema] = None


Gemini_API_PARAMS = {param for param in asdict(GeminiConfig()).keys()}
Gemini_Config_PARAMS = {param for param in asdict(Gemini_Gen_Config()).keys()}
