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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from mistralai.models.chat_completion import ChatCompletionResponse

from camel.configs import MISTRAL_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ModelType
from camel.utils import BaseTokenCounter, OpenAITokenCounter, api_keys_required


class MistralModel(BaseModelBackend):
    r"""Mistral API in a unified BaseModelBackend interface."""

    # TODO: Support tool calling and stream mode.

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for Mistral backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of MISTRAL_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into `MistralClient.chat`.
            api_key (Optional[str]): The API key for authenticating with the
                mistral service. (default: :obj:`None`)
            url (Optional[str]): The url to the mistral service.
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter(ModelType.
                GPT_3_5_TURBO)` will be used.
        """
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        self._api_key = api_key or os.environ.get("MISTRAL_API_KEY")

        from mistralai.client import MistralClient

        self._client = MistralClient(api_key=self._api_key)
        self._token_counter: Optional[BaseTokenCounter] = None

    def _convert_response_from_mistral_to_openai(
        self, response: 'ChatCompletionResponse'
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
            self._token_counter = OpenAITokenCounter(ModelType.GPT_3_5_TURBO)
        return self._token_counter

    @api_keys_required("MISTRAL_API_KEY")
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        r"""Runs inference of Mistral chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            ChatCompletion
        """
        response = self._client.chat(
            messages=messages,
            model=self.model_type.value,
            **self.model_config_dict,
        )

        response = self._convert_response_from_mistral_to_openai(response)  # type:ignore[assignment]

        return response  # type:ignore[return-value]

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
        r"""Returns whether the model is in stream mode, which sends partial
        results each time. Mistral doesn't support stream mode.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return False