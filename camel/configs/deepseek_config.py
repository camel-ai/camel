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

from typing import Any, Optional, Sequence, Type, Union

from pydantic import BaseModel

from camel.configs.base_config import BaseConfig
from camel.types import NOT_GIVEN, NotGiven


class DeepSeekConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    DeepSeek API.

    Args:
        temperature (float, optional): The sampling temperature to use,
            between 0 and 2. Higher values like 0.8 will make the output
            more random, while lower values like 0.2 will make it more
            focused and deterministic. We generally recommend altering
            this or top_p but not both. Defaults to 1.
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results
            of the tokens with top_p probability mass. So 0.1 means only
            the tokens comprising the top 10% probability mass are
            considered. We generally recommend altering this or temperature
            but not both. Defaults to 1.
        response_format (Union[Dict[str, str], ResponseFormat], optional):
            The format that the model must output. Setting to
            {"type": "json_object"} enables JSON Output, which guarantees
            the message the model generates is valid JSON. Important: When
            using JSON Output, you must also instruct the model to produce
            JSON yourself via a system or user message. Without this, the
            model may generate an unending stream of whitespace until the
            generation reaches the token limit, resulting in a long-running
            and seemingly "stuck" request. Also note that the message
            content may be partially cut off if finish_reason="length",
            which indicates the generation exceeded max_tokens or the
            conversation exceeded the max context length. Possible values:
            ["text", "json_object"]. Defaults to "text".
        stream (bool, optional): If set, partial message deltas will be sent.
            Tokens will be sent as data-only server-sent events (SSE) as
            they become available, with the stream terminated by a
            data: [DONE] message. Defaults to False.
        stream_options (bool, optional): Options for streaming response.
            Only set this when you set stream: true. include_usage
            (boolean) If set, an additional chunk will be streamed before
            the data: [DONE] message. The usage field on this chunk shows
            the token usage statistics for the entire request, and the
            choices field will always be an empty array. All other chunks
            will also include a usage field, but with a null value.
            Defaults to False.
        stop (Union[str, list[str]], optional): Up to 16 sequences where
            the API will stop generating further tokens. Defaults to None.
        max_tokens (int, optional): The maximum number of tokens that can
            be generated in the chat completion. The total length of input
            tokens and generated tokens is limited by the model's context
            length. Defaults to None.
        presence_penalty (float, optional): Number between -2.0 and 2.0.
            Positive values penalize new tokens based on whether they
            appear in the text so far, increasing the model's likelihood
            to talk about new topics. Defaults to 0.
        frequency_penalty (float, optional): Number between -2.0 and 2.0.
            Positive values penalize new tokens based on their existing
            frequency in the text so far, decreasing the model's likelihood
            to repeat the same line verbatim. Defaults to 0.
        tools (list[FunctionTool], optional): A list of tools the model may
            call. Currently, only functions are supported as a tool. Use
            this to provide a list of functions the model may generate JSON
            inputs for. A max of 128 functions are supported. Defaults to
            None.
        tool_choice (Union[dict[str, str], str], optional): Controls which
            (if any) tool is called by the model. "none" means the model
            will not call any tool and instead generates a message. "auto"
            means the model can pick between generating a message or calling
            one or more tools. "required" means the model must call one or
            more tools. Specifying a particular tool via
            {"type": "function", "function": {"name": "my_function"}} forces
            the model to call that tool. "none" is the default when no tools
            are present. "auto" is the default if tools are present.
            Defaults to "auto".
        logprobs (bool, optional): Whether to return log probabilities of
            the output tokens or not. If true, returns the log probabilities
            of each output token returned in the content of message.
            Defaults to False.
        top_logprobs (int, optional): An integer between 0 and 20 specifying
            the number of most likely tokens to return at each token
            position, each with an associated log probability. logprobs
            must be set to true if this parameter is used. Defaults to None.
    """

    temperature: float = 0.2  # deepseek default: 1.0
    top_p: float = 1.0
    stream: bool = False
    stop: Union[str, Sequence[str], NotGiven] = NOT_GIVEN
    max_tokens: Union[int, NotGiven] = NOT_GIVEN
    presence_penalty: float = 0.0
    response_format: Union[Type[BaseModel], dict, NotGiven] = NOT_GIVEN
    frequency_penalty: float = 0.0
    tool_choice: Optional[Union[dict[str, str], str]] = None

    def as_dict(self) -> dict[str, Any]:
        r"""Convert the current configuration to a dictionary.

        This method converts the current configuration object to a dictionary
        representation, which can be used for serialization or other purposes.

        Returns:
            dict[str, Any]: A dictionary representation of the current
                configuration.
        """
        config_dict = self.model_dump()
        if self.tools:
            from camel.toolkits import FunctionTool

            tools_schema = []
            for tool in self.tools:
                if not isinstance(tool, FunctionTool):
                    raise ValueError(
                        f"The tool {tool} should "
                        "be an instance of `FunctionTool`."
                    )
                tools_schema.append(tool.get_openai_tool_schema())
        config_dict["tools"] = NOT_GIVEN
        return config_dict


DEEPSEEK_API_PARAMS = {param for param in DeepSeekConfig.model_fields.keys()}
