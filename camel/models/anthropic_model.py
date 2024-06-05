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
from typing import Any, Dict, Optional

from anthropic import Anthropic
from anthropic._types import NOT_GIVEN

from camel.configs import ANTHROPIC_API_PARAMS
from camel.models.base_model import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import AnthropicTokenCounter, BaseTokenCounter


class AnthropicModel(BaseModelBackend):
    r"""Anthropic API in a unified BaseModelBackend interface."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
    ) -> None:
        r"""Constructor for Anthropic backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of GPT_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
            api_key (Optional[str]): The API key for authenticating with the
                Anthropic service. (default: :obj:`None`)
        """
        super().__init__(model_type, model_config_dict)
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self._api_key)
        self._token_counter: Optional[BaseTokenCounter] = None

    def _convert_response_from_anthropic_to_openai(self, response):
        # openai ^1.0.0 format, reference openai/types/chat/chat_completion.py
        obj = ChatCompletion.construct(
            id=None,
            choices=[
                dict(
                    index=0,
                    message={
                        "role": "assistant",
                        "content": response.content[0].text,
                    },
                    finish_reason=response.stop_reason,
                )
            ],
            created=None,
            model=response.model,
            object="chat.completion",
        )
        return obj

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = AnthropicTokenCounter(self.model_type)
        return self._token_counter

    def count_tokens_from_prompt(self, prompt: str) -> int:
        r"""Count the number of tokens from a prompt.

        Args:
            prompt (str): The prompt string.

        Returns:
            int: The number of tokens in the prompt.
        """
        return self.client.count_tokens(prompt)

    def run(
        self,
        messages,
    ):
        r"""Run inference of Anthropic chat completion.

        Args:
            messages (List[Dict]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Dict[str, Any]: Response in the OpenAI API format.
        """

        if messages[0]["role"] == "system":
            sys_msg = messages.pop(0)["content"]
        else:
            sys_msg = NOT_GIVEN
        response = self.client.messages.create(
            model=self.model_type.value,
            system=sys_msg,
            messages=messages,
            **self.model_config_dict,
        )

        # format response to openai format
        response = self._convert_response_from_anthropic_to_openai(response)

        return response

    def check_model_config(self):
        r"""Check whether the model configuration is valid for anthropic
        model backends.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API, or it does not contain
                :obj:`model_path` or :obj:`server_url`.
        """
        for param in self.model_config_dict:
            if param not in ANTHROPIC_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Anthropic model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)
