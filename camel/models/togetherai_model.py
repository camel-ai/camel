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

from camel.configs import TOGETHERAI_API_PARAMS
from camel.messages import OpenAIMessage
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


class TogetherAIModel:
    r"""Constructor for Together AI backend with OpenAI compatibility.
    TODO: Add function calling support
    """

    def __init__(
        self,
        model_type: str,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for TogetherAI backend.

        Args:
            model_type (str): Model for which a backend is created, supported
                model can be found here: https://docs.together.ai/docs/chat-models
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
            api_key (Optional[str]): The API key for authenticating with the
                Together service. (default: :obj:`None`)
            url (Optional[str]): The url to the Together AI service. (default:
                :obj:`"https://api.together.xyz/v1"`)
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter(ModelType.
                GPT_4O_MINI)` will be used.
        """
        self.model_type = model_type
        self.model_config_dict = model_config_dict
        self._token_counter = token_counter
        self._api_key = api_key or os.environ.get("TOGETHER_API_KEY")
        self._url = url or os.environ.get("TOGETHER_API_BASE_URL")

        self._client = OpenAI(
            timeout=60,
            max_retries=3,
            api_key=self._api_key,
            base_url=self._url or "https://api.together.xyz/v1",
        )

    @api_keys_required("TOGETHER_API_KEY")
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
        # Use OpenAI cilent as interface call Together AI
        # Reference: https://docs.together.ai/docs/openai-api-compatibility
        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **self.model_config_dict,
        )
        return response

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            OpenAITokenCounter: The token counter following the model's
                tokenization style.
        """

        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to TogetherAI API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to TogetherAI API.
        """
        for param in self.model_config_dict:
            if param not in TOGETHERAI_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into TogetherAI model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for the given model.

        Returns:
            int: The maximum token limit for the given model.
        """
        max_tokens = self.model_config_dict.get("max_tokens")
        if isinstance(max_tokens, int):
            return max_tokens
        print(
            "Must set `max_tokens` as an integer in `model_config_dict` when"
            " setting up the model. Using 4096 as default value."
        )
        return 4096
