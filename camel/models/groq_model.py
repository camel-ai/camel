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
from camel.utils import (
    BaseTokenCounter,
    GroqLlama3TokenCounter,
    api_key_required,
)


class GroqModel(BaseModelBackend):
    r"""LLM API served by Groq in a unified BaseModelBackend interface."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
    ) -> None:
        r"""Constructor for Groq backend.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into groq.ChatCompletion.create().
            api_key (Optional[str]): The API key for authenticating with the
                Anthropic service. (default: :obj:`None`).
        """
        super().__init__(model_type, model_config_dict)
        url = os.environ.get('GROQ_API_BASE_URL', None)
        api_key = os.environ.get('GROQ_API_KEY')
        self._client = Groq(api_key=api_key, base_url=url)
        self._token_counter: Optional[BaseTokenCounter] = None

    def _convert_response_from_anthropic_to_openai(self, response):
        # openai ^1.0.0 format, reference openai/types/chat/chat_completion.py
        obj = ChatCompletion.construct(
            id=response.id,
            choices=[
                Choice.construct(
                    finish_reason=response.choices[0].finish_reason,
                    index=response.choices[0].index,
                    logprobs=response.choices[0].logprobs,
                    message=ChatCompletionMessage.construct(
                        content=response.choices[0].message.content,
                        role=response.choices[0].message.role,
                        function_call=None,  # It does not provide function call
                        tool_calls=response.choices[0].message.tool_calls,
                    ),
                )
            ],
            created=response.created,
            model=response.model,
            object="chat.completion",
            system_fingerprint=response.system_fingerprint,
            usage=CompletionUsage.construct(
                completion_tokens=response.usage.completion_tokens,
                prompt_tokens=response.usage.prompt_tokens,
                total_tokens=response.usage.total_tokens,
            ),
        )
        return obj

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend. But Groq API
        does not provide any token counter.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = GroqLlama3TokenCounter(self.model_type)
        return self._token_counter

    @api_key_required
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            ChatCompletion: Response in the OpenAI API format (non-stream\
                mode).
        """
        _response = self._client.chat.completions.create(
            messages=messages,  # type: ignore[arg-type]
            model=self.model_type.value,
            **self.model_config_dict,
        )

        # Format response to OpenAI format
        response = self._convert_response_from_anthropic_to_openai(_response)

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
            if param not in GROQ_LLAMA3_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Groq Llama3 model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model supports streaming. But Groq API does
        not support streaming.
        """
        return False
