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

from camel.configs import GROQ_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


class GroqModel(BaseModelBackend):
    r"""LLM API served by Groq in a unified BaseModelBackend interface."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for Groq backend.

        Args:
            model_type (str): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary of parameters for
                the model configuration.
            api_key (Optional[str]): The API key for authenticating with the
                Groq service. (default: :obj:`None`).
            url (Optional[str]): The url to the Groq service. (default:
                :obj:`None`)
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter(ModelType.
                GPT_3_5_TURBO)` will be used.
        """
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        self._url = url or "https://api.groq.com/openai/v1"
        self._api_key = api_key or os.environ.get("GROQ_API_KEY")
        self._client = OpenAI(
            timeout=60,
            max_retries=3,
            api_key=self._api_key,
            base_url=self._url,
        )
        self._token_counter = token_counter

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        # Make sure you have the access to these open-source model in
        # HuggingFace
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_3_5_TURBO)
        return self._token_counter

    @api_keys_required("GROQ_API_KEY")
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
        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type.value,
            **self.model_config_dict,
        )

        return response

    def check_model_config(self):
        r"""Check whether the model configuration contains any unexpected
        arguments to Groq API. But Groq API does not have any additional
        arguments to check.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Groq API.
        """
        for param in self.model_config_dict:
            if param not in GROQ_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Groq model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model supports streaming. But Groq API does
        not support streaming.
        """
        return False
