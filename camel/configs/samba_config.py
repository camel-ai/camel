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

from typing import Any, Optional, Sequence, Union

from pydantic import Field

from camel.configs.base_config import BaseConfig
from camel.types import NOT_GIVEN, NotGiven


class SambaVerseAPIConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    SambaVerse API.

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
        top_k (int, optional): Only sample from the top K options for each
            subsequent token. Used to remove "long tail" low probability
            responses.
            (default: :obj:`None`)
        max_tokens (Optional[int], optional): The maximum number of tokens to
            generate, e.g. 100.
            (default: :obj:`None`)
        repetition_penalty (Optional[float], optional): The parameter for
            repetition penalty. 1.0 means no penalty.
            (default: :obj:`None`)
        stop (Optional[Union[str,list[str]]]): Stop generation if this token
            is detected. Or if one of these tokens is detected when providing
            a string list.
            (default: :obj:`None`)
        stream (Optional[bool]): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            Currently SambaVerse API doesn't support stream mode.
            (default: :obj:`None`)
    """

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    max_tokens: Optional[int] = None
    repetition_penalty: Optional[float] = None
    stop: Optional[Union[str, list[str]]] = None
    stream: Optional[bool] = None

    def as_dict(self) -> dict[str, Any]:
        config_dict = super().as_dict()
        if "tools" in config_dict:
            del config_dict["tools"]  # SambaNova does not support tool calling
        return config_dict


SAMBA_VERSE_API_PARAMS = {
    param for param in SambaVerseAPIConfig().model_fields.keys()
}


class SambaCloudAPIConfig(BaseConfig):
    r"""Defines the parameters for generating chat completions using the
    OpenAI API.

    Args:
        temperature (float, optional): Sampling temperature to use, between
            :obj:`0` and :obj:`2`. Higher values make the output more random,
            while lower values make it more focused and deterministic.
            (default: :obj:`0.2`)
        top_p (float, optional): An alternative to sampling with temperature,
            called nucleus sampling, where the model considers the results of
            the tokens with top_p probability mass. So :obj:`0.1` means only
            the tokens comprising the top 10% probability mass are considered.
            (default: :obj:`1.0`)
        n (int, optional): How many chat completion choices to generate for
            each input message. (default: :obj:`1`)
        response_format (object, optional): An object specifying the format
            that the model must output. Compatible with GPT-4 Turbo and all
            GPT-3.5 Turbo models newer than gpt-3.5-turbo-1106. Setting to
            {"type": "json_object"} enables JSON mode, which guarantees the
            message the model generates is valid JSON. Important: when using
            JSON mode, you must also instruct the model to produce JSON
            yourself via a system or user message. Without this, the model
            may generate an unending stream of whitespace until the generation
            reaches the token limit, resulting in a long-running and seemingly
            "stuck" request. Also note that the message content may be
            partially cut off if finish_reason="length", which indicates the
            generation exceeded max_tokens or the conversation exceeded the
            max context length.
        stream (bool, optional): If True, partial message deltas will be sent
            as data-only server-sent events as they become available.
            (default: :obj:`False`)
        stop (str or list, optional): Up to :obj:`4` sequences where the API
            will stop generating further tokens. (default: :obj:`None`)
        max_tokens (int, optional): The maximum number of tokens to generate
            in the chat completion. The total length of input tokens and
            generated tokens is limited by the model's context length.
            (default: :obj:`None`)
        presence_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on whether
            they appear in the text so far, increasing the model's likelihood
            to talk about new topics. See more information about frequency and
            presence penalties. (default: :obj:`0.0`)
        frequency_penalty (float, optional): Number between :obj:`-2.0` and
            :obj:`2.0`. Positive values penalize new tokens based on their
            existing frequency in the text so far, decreasing the model's
            likelihood to repeat the same line verbatim. See more information
            about frequency and presence penalties. (default: :obj:`0.0`)
        logit_bias (dict, optional): Modify the likelihood of specified tokens
            appearing in the completion. Accepts a json object that maps tokens
            (specified by their token ID in the tokenizer) to an associated
            bias value from :obj:`-100` to :obj:`100`. Mathematically, the bias
            is added to the logits generated by the model prior to sampling.
            The exact effect will vary per model, but values between:obj:` -1`
            and :obj:`1` should decrease or increase likelihood of selection;
            values like :obj:`-100` or :obj:`100` should result in a ban or
            exclusive selection of the relevant token. (default: :obj:`{}`)
        user (str, optional): A unique identifier representing your end-user,
            which can help OpenAI to monitor and detect abuse.
            (default: :obj:`""`)
        tools (list[FunctionTool], optional): A list of tools the model may
            call. Currently, only functions are supported as a tool. Use this
            to provide a list of functions the model may generate JSON inputs
            for. A max of 128 functions are supported.
        tool_choice (Union[dict[str, str], str], optional): Controls which (if
            any) tool is called by the model. :obj:`"none"` means the model
            will not call any tool and instead generates a message.
            :obj:`"auto"` means the model can pick between generating a
            message or calling one or more tools.  :obj:`"required"` means the
            model must call one or more tools. Specifying a particular tool
            via {"type": "function", "function": {"name": "my_function"}}
            forces the model to call that tool. :obj:`"none"` is the default
            when no tools are present. :obj:`"auto"` is the default if tools
            are present.
    """

    temperature: float = 0.2  # openai default: 1.0
    top_p: float = 1.0
    n: int = 1
    stream: bool = False
    stop: Union[str, Sequence[str], NotGiven] = NOT_GIVEN
    max_tokens: Union[int, NotGiven] = NOT_GIVEN
    presence_penalty: float = 0.0
    response_format: Union[dict, NotGiven] = NOT_GIVEN
    frequency_penalty: float = 0.0
    logit_bias: dict = Field(default_factory=dict)
    user: str = ""
    tool_choice: Optional[Union[dict[str, str], str]] = None


SAMBA_CLOUD_API_PARAMS = {
    param for param in SambaCloudAPIConfig().model_fields.keys()
}
