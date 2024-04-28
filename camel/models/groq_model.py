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
from typing import Any, Dict, List, Optional

from groq import Groq

from camel.configs import GROQ_LLAMA3_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
    CompletionUsage,
    ModelType,
)
from camel.utils import BaseTokenCounter, OpenAITokenCounter, api_key_required


class GroqModel(BaseModelBackend):
    r"""LLM API served by Groq in a unified BaseModelBackend interface."""

    def __init__(self, model_type: ModelType,
                 model_config_dict: Dict[str, Any]) -> None:
        r"""Constructor for Groq backend.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into groq.ChatCompletion.create().
        """
        super().__init__(model_type, model_config_dict)
        url = os.environ.get('GROQ_API_BASE_URL', None)
        api_key = os.environ.get('GROQ_API_KEY')
        self._client = Groq(api_key=api_key, base_url=url)
        self._token_counter: Optional[BaseTokenCounter] = None

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend. But Groq API
        does not provide any token counter.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            # Groq API does not provide any token counter, so we use the
            # OpenAI token counter as a placeholder.
            self._token_counter = OpenAITokenCounter(ModelType.GPT_3_5_TURBO)
        return self._token_counter

    @api_key_required
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:  # type: ignore
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            ChatCompletion: `ChatCompletion` in the non-stream mode, while the
            stream mode is not supported by Groq.
        """
        # Since the data structure defined in the Groq client is slightly
        # different from the one defined in the CAMEL, we need to convert the
        # data structure. In addition, the tyep ignore is used to avoid the
        # meaningless type error detected by the mypy.
        response = self._client.chat.completions.create(
            messages=messages,  # type: ignore
            model=self.model_type.value,
            **self.model_config_dict,
        )

        _choices: List[Choice] = []  # type: ignore
        for choice in response.choices:
            choice.message = ChatCompletionMessage(
                role=choice.message.role,  # type: ignore
                content=choice.message.content,
                tool_calls=choice.message.tool_calls)  # type: ignore
            _choice = Choice(**choice.__dict__)  # type: ignore
            _choices.append(_choice)
        response.choices = _choices  # type: ignore

        response.usage = CompletionUsage(
            **response.usage.__dict__)  # type: ignore
        return ChatCompletion(**response.__dict__)

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to Groq API. But Groq API does not have any
        additional arguments to check.
        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in GROQ_LLAMA3_API_PARAMS:
                raise ValueError(f"Unexpected argument `{param}` is "
                                 "input into Groq Llama3 model backend.")

    @property
    def stream(self) -> bool:
        r"""Returns whether the model supports streaming. But Groq API does
        not support streaming.
        """
        return False
