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
import os
import warnings
from typing import Any, Dict, List, Optional, Union

from openai import AsyncOpenAI, OpenAI, Stream
from outlines.models.openai import OpenAIConfig

from camel.configs import OPENAI_API_PARAMS, ChatGPTConfig, ResponseFormat
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    NOT_GIVEN,
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
    ParsedChatCompletion,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


# Function to add `model_config` if missing
# Required by outlines with OpenAI pydantic object
def ensure_model_config(cls):
    from pydantic import ConfigDict

    if "extra" not in cls.model_config:
        cls.model_config = ConfigDict(extra="forbid")
    return cls


class OpenAIModel(BaseModelBackend):
    r"""OpenAI API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of GPT_* series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the OpenAI service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the OpenAI service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter` will
            be used. (default: :obj:`None`)
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = ChatGPTConfig().as_dict()
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        url = url or os.environ.get("OPENAI_API_BASE_URL")
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        self._client = OpenAI(
            timeout=60,
            max_retries=3,
            base_url=self._url,
            api_key=self._api_key,
        )
        self._async_client = AsyncOpenAI(
            timeout=60,
            max_retries=3,
            base_url=self._url,
            api_key=self._api_key,
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(self.model_type)
        return self._token_counter

    @api_keys_required("OPENAI_API_KEY")
    def run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[ResponseFormat] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[ResponseFormat], optional): A pydantic
                response format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        # o1-preview and o1-mini have Beta limitations
        # reference: https://platform.openai.com/docs/guides/reasoning
        if self.model_type in [ModelType.O1_MINI, ModelType.O1_PREVIEW]:
            warnings.warn(
                "Warning: You are using an O1 model (O1_MINI or O1_PREVIEW), "
                "which has certain limitations, reference: "
                "`https://platform.openai.com/docs/guides/reasoning`.",
                UserWarning,
            )

            # Remove system message that is not supported in o1 model.
            messages = [msg for msg in messages if msg.get("role") != "system"]

            # Check and remove unsupported parameters and reset the fixed
            # parameters
            unsupported_keys = ["stream", "tools", "tool_choice"]
            for key in unsupported_keys:
                if key in self.model_config_dict:
                    del self.model_config_dict[key]

            self.model_config_dict["temperature"] = 1.0
            self.model_config_dict["top_p"] = 1.0
            self.model_config_dict["n"] = 1
            self.model_config_dict["presence_penalty"] = 0.0
            self.model_config_dict["frequency_penalty"] = 0.0

        # Structured output
        response_format = response_format or self.model_config_dict.get(
            "response_format"
        )
        if response_format is not None and response_format != NOT_GIVEN:
            # Original implementation without outlines
            if response_format.method == "openai":
                # stream is not supported in beta.chat.completions.parse
                if "stream" in self.model_config_dict:
                    del self.model_config_dict["stream"]

                response = self._client.beta.chat.completions.parse(
                    messages=messages,
                    model=self.model_type,
                    **self.model_config_dict,
                )
                return self._to_chat_completion(response)

            if response_format.method == "outlines":
                from outlines import generate, models

                # copy from model_config_dict
                config = self._from_model_config_dict(self.model_config_dict)
                outlines_model = models.OpenAI(self._async_client, config)

                match response_format.type:
                    case "json" if response_format.pydantic_object:
                        generator = generate.json(
                            outlines_model,
                            ensure_model_config(
                                response_format.pydantic_object
                            ),
                        )
                    case "choice" if response_format.choices:
                        generator = generate.choice(
                            outlines_model, response_format.choices
                        )
                    case "regex":
                        generator = generate.regex(
                            outlines_model, response_format.regex
                        )
                    case _:
                        raise NotImplementedError(
                            f"Unsupported response format type: "
                            f"{response_format.type}"
                        )

                # TODO: add user message to the messages
                usr_msg_content = str(messages[0]["content"])
                result = generator(usr_msg_content)

        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **self.model_config_dict,
        )

        # TODO: currently, the outlines API doesnot return ChatCompletion
        # object, get around this by this.

        if response_format:
            response.choices[0].message.content = str(result)

        return response

    def _to_chat_completion(
        self, response: "ParsedChatCompletion"
    ) -> ChatCompletion:
        # TODO: Handle n > 1 or warn consumers it's not supported
        choice = dict(
            index=response.choices[0].index,
            message={
                "role": response.choices[0].message.role,
                "content": response.choices[0].message.content,
                "tool_calls": response.choices[0].message.tool_calls,
                "parsed": response.choices[0].message.parsed,
            },
            finish_reason=response.choices[0].finish_reason,
        )

        obj = ChatCompletion.construct(
            id=response.id,
            choices=[choice],
            created=response.created,
            model=response.model,
            object="chat.completion",
            usage=response.usage,
        )
        return obj

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to OpenAI API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in OPENAI_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into OpenAI model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)

    def _from_model_config_dict(
        self, model_config_dict: Dict[str, Any]
    ) -> OpenAIConfig:
        r"""Convert the model config dict to the Outlines OpenAIConfig."""
        # remove tools, stream, tool_choice from the model config
        outlines_config_dict = model_config_dict.copy()
        outlines_config_dict.pop("tools", None)
        outlines_config_dict.pop("stream", None)
        outlines_config_dict.pop("tool_choice", None)
        outlines_config_dict["model"] = self.model_type.lower()
        return OpenAIConfig(**outlines_config_dict)
