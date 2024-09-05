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
from typing import Any, Optional

from pydantic import model_validator

from camel.configs.base_config import BaseConfig


class GeminiConfig(BaseConfig):
    r"""A simple dataclass used to configure the generation parameters of
    `GenerativeModel.generate_content`.

    Args:
        candidate_count (int, optional): Number of responses to return.
        stop_sequences (Iterable[str], optional): The set of character
            sequences (up to 5) that will stop output generation. If specified
            the API will stop at the first appearance of a stop sequence.
            The stop sequence will not be included as part of the response.
        max_output_tokens (int, optional): The maximum number of tokens to
            include in a candidate. If unset, this will default to
            output_token_limit specified in the model's specification.
        temperature (float, optional): Controls the randomness of the output.
            Note: The default value varies by model, see the
            `Model.temperature` attribute of the `Model` returned
            the `genai.get_model` function. Values can range from [0.0,1.0],
            inclusive. A value closer to 1.0 will produce responses that are
            more varied and creative, while a value closer to 0.0 will
            typically result in more straightforward responses from the model.
        top_p (int, optional): The maximum cumulative probability of tokens to
            consider when sampling. The model uses combined Top-k and nucleus
            sampling. Tokens are sorted based on their assigned probabilities
            so that only the most likely tokens are considered. Top-k sampling
            directly limits the maximum number of tokens to consider, while
            Nucleus sampling limits number of tokens
            based on the cumulative probability. Note: The default value varies
            by model, see the `Model.top_p` attribute of the `Model` returned
            the `genai.get_model` function.
        top_k (int, optional): The maximum number of tokens to consider when
            sampling. The model uses combined Top-k and nucleus sampling.Top-k
            sampling considers the set of `top_k` most probable tokens.
            Defaults to 40. Note: The default value varies by model, see the
            `Model.top_k` attribute of the `Model` returned the
            `genai.get_model` function.
        response_mime_type (str, optional): Output response mimetype of the
            generated candidate text. Supported mimetype:
            `text/plain`: (default) Text output.
            `application/json`: JSON response in the candidates.
        response_schema (Schema, optional): Specifies the format of the
            JSON requested if response_mime_type is `application/json`.
        safety_settings (SafetySettingOptions, optional):
            Overrides for the model's safety settings.
        tools (FunctionLibraryType, optional):
            `protos.Tools` more info coming soon.
        tool_config (ToolConfigType, optional):
            more info coming soon.
        request_options (RequestOptionsType, optional):
            Options for the request.
    """

    candidate_count: Optional[int] = None
    stop_sequences: Optional[Iterable[str]] = None
    max_output_tokens: Optional[int] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    response_mime_type: Optional[str] = None
    response_schema: Optional[Any] = None
    safety_settings: Optional[Any] = None
    tool_config: Optional[Any] = None
    request_options: Optional[Any] = None

    @model_validator(mode="before")
    @classmethod
    def fields_type_checking(cls, data: Any):
        if isinstance(data, dict):
            response_schema = data.get("response_schema")
            safety_settings = data.get("safety_settings")
            tools = data.get("tools")
            tool_config = data.get("tool_config")
            request_options = data.get("request_options")

            if response_schema:
                from google.generativeai.protos import Schema
                from google.generativeai.types.content_types import (
                    FunctionLibraryType,
                    ToolConfigType,
                )
                from google.generativeai.types.helper_types import (
                    RequestOptionsType,
                )
                from google.generativeai.types.safety_types import (
                    SafetySettingOptions,
                )
        else:
            return data

        if response_schema and not isinstance(response_schema, Schema):
            raise ValueError(
                "The response_schema should be "
                "an instance of `google.generativeai.protos.Schema`."
            )

        if safety_settings and not isinstance(
            safety_settings, SafetySettingOptions
        ):
            raise ValueError(
                "The response_schema should be an instance of "
                "`google.generativeai.types.safety_types.SafetySettingOptions`."
            )

        if tools is not None:
            for tool in tools:
                if not isinstance(tool, FunctionLibraryType):
                    raise ValueError(
                        "The tool should be an instance of "
                        "`google.generativeai.types.content_types.FunctionLibraryType`."
                    )
        if tool_config and not isinstance(tool_config, ToolConfigType):
            raise ValueError(
                "The response_schema should be an instance of "
                "`google.generativeai.types.content_types.ToolConfigType`."
            )
        if request_options and not isinstance(
            request_options, RequestOptionsType
        ):
            raise ValueError(
                "The response_schema should be an instance of "
                "`google.generativeai.types.helper_types.RequestOptionsType`."
            )
        return data


Gemini_API_PARAMS = {param for param in GeminiConfig().model_fields.keys()}
