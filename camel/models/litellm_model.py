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
from typing import Any, Dict, List, Optional

from camel.configs import LITELLM_API_PARAMS
from camel.messages import OpenAIMessage
from camel.types import ChatCompletion
from camel.utils import BaseTokenCounter, LiteLLMTokenCounter


class LiteLLMModel:
    r"""Constructor for LiteLLM backend with OpenAI compatibility."""

    # NOTE: Currently stream mode is not supported.

    def __init__(
        self,
        model_type: str,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for LiteLLM backend.

        Args:
            model_type (str): Model for which a backend is created,
                such as GPT-3.5-turbo, Claude-2, etc.
            model_config_dict (Dict[str, Any]): A dictionary of parameters for
                the model configuration.
            api_key (Optional[str]): The API key for authenticating with the
                model service. (default: :obj:`None`)
            url (Optional[str]): The url to the model service. (default:
                :obj:`None`)
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `LiteLLMTokenCounter` will
                be used.
        """
        self.model_type = model_type
        self.model_config_dict = model_config_dict
        self._client = None
        self._token_counter = token_counter
        self.check_model_config()
        self._url = url
        self._api_key = api_key

    def _convert_response_from_litellm_to_openai(
        self, response
    ) -> ChatCompletion:
        r"""Converts a response from the LiteLLM format to the OpenAI format.

        Parameters:
            response (LiteLLMResponse): The response object from LiteLLM.

        Returns:
            ChatCompletion: The response object in OpenAI's format.
        """
        return ChatCompletion.construct(
            id=response.id,
            choices=[
                {
                    "index": response.choices[0].index,
                    "message": {
                        "role": response.choices[0].message.role,
                        "content": response.choices[0].message.content,
                    },
                    "finish_reason": response.choices[0].finish_reason,
                }
            ],
            created=response.created,
            model=response.model,
            object=response.object,
            system_fingerprint=response.system_fingerprint,
            usage=response.usage,
        )

    @property
    def client(self):
        if self._client is None:
            from litellm import completion

            self._client = completion
        return self._client

    @property
    def token_counter(self) -> LiteLLMTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            LiteLLMTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = LiteLLMTokenCounter(  # type: ignore[assignment]
                self.model_type
            )
        return self._token_counter  # type: ignore[return-value]

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        r"""Runs inference of LiteLLM chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI format.

        Returns:
            ChatCompletion
        """
        response = self.client(
            api_key=self._api_key,
            base_url=self._url,
            model=self.model_type,
            messages=messages,
            **self.model_config_dict,
        )
        response = self._convert_response_from_litellm_to_openai(response)
        return response

    def check_model_config(self):
        r"""Check whether the model configuration contains any unexpected
        arguments to LiteLLM API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments.
        """
        for param in self.model_config_dict:
            if param not in LITELLM_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into LiteLLM model backend."
                )

    @property
    def token_limit(self) -> int:
        """Returns the maximum token limit for the given model.

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
