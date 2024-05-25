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

from mistralai.client import MistralClient
from mistralai.models.chat_completion import (
    ChatCompletionResponse,
    ChatMessage,
    FunctionCall,
    ToolCall,
)

from camel.configs import MISTRAL_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import BaseTokenCounter, MistralTokenCounter, api_key_required


class MistralModel(BaseModelBackend):
    r"""Mistral API in a unified BaseModelBackend interface."""

    import mistralai

    def __init__(
        self, model_type: ModelType, model_config_dict: Dict[str, Any]
    ) -> None:
        r"""Constructor for Mistral backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of MISTRAL_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into `MistralClient.chat`.
        """
        super().__init__(model_type, model_config_dict)
        self._client = MistralClient()
        self._token_counter: Optional[BaseTokenCounter] = None

    def _convert_response_from_mistral_to_openai(
        self, response: ChatCompletionResponse
    ) -> ChatCompletion:
        # openai ^1.0.0 format, reference openai/types/chat/chat_completion.py
        obj = ChatCompletion.construct(
            id=response.id,
            choices=[
                dict(
                    index=response.choices[0].index,
                    message={
                        "role": response.choices[0].message.role,
                        "content": response.choices[0].message.content,
                        "function_call": dict(
                            name=response.choices[0]
                            .message.tool_calls[0]
                            .function.name,
                            arguments=response.choices[0]
                            .message.tool_calls[0]
                            .function.arguments,
                        )
                        if response.choices[0].message.tool_calls is not None
                        else None,
                    },
                    finish_reason=response.choices[0].finish_reason
                    if response.choices[0].message.tool_calls is None
                    else "function_call",
                )
            ],
            created=response.created,
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
            self._token_counter = MistralTokenCounter(self.model_type)
        return self._token_counter

    @api_key_required
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        r"""Runs inference of Mistral chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        for message in messages:
            if message["role"] == "function":
                message["role"] = "tool"
            if "function_call" in message.keys():
                name = message["function_call"]["name"]
                arguments = message["function_call"]["arguments"]
                message["tool_calls"] = [
                    ToolCall(
                        function=FunctionCall(name=name, arguments=arguments)
                    )
                ]
        mistral_messages = [ChatMessage(**message) for message in messages]
        response = self._client.chat(
            messages=mistral_messages,
            model=self.model_type.value,
            **self.model_config_dict,
        )

        response = self._convert_response_from_mistral_to_openai(response)

        return response

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to Mistral API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Mistral API.
        """
        for param in self.model_config_dict:
            if param not in MISTRAL_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Mistral model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
