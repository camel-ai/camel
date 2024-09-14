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
import os
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI, Stream

from camel.configs import OPENAI_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


class OpenAIModel(BaseModelBackend):
    r"""OpenAI API in a unified BaseModelBackend interface."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for OpenAI backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of GPT_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
            api_key (Optional[str]): The API key for authenticating with the
                OpenAI service. (default: :obj:`None`)
            url (Optional[str]): The url to the OpenAI service. (default:
                :obj:`None`)
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter` will
                be used.
        """
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        self._url = url or os.environ.get("OPENAI_API_BASE_URL")
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = OpenAI(
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
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        # o1-preview and o1-mini have Beta limitations
        # reference: https://platform.openai.com/docs/guides/reasoning
        if self.model_type in [ModelType.O1_MINI, ModelType.O1_PREVIEW]:
            # Remove system message that is not supported in o1 model.
            messages = [msg for msg in messages if msg.get("role") != "system"]

            # Remove unsupported parameters and reset the fixed parameters
            del self.model_config_dict["stream"]
            del self.model_config_dict["tools"]
            del self.model_config_dict["tool_choice"]
            self.model_config_dict["temperature"] = 1.0
            self.model_config_dict["top_p"] = 1.0
            self.model_config_dict["n"] = 1.0
            self.model_config_dict["presence_penalty"] = 0.0
            self.model_config_dict["frequency_penalty"] = 0.0

        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type.value,
            **self.model_config_dict,
        )
        return response

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
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
