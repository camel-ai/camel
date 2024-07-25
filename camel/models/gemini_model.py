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
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from camel.configs import Gemini_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionMessage,
    Choice,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    GeminiTokenCounter,
    api_keys_required,
)

if TYPE_CHECKING:
    from google.generativeai.types import ContentsType, GenerateContentResponse


class GeminiModel(BaseModelBackend):
    r"""Gemini API in a unified BaseModelBackend interface."""

    # NOTE: Currently "stream": True is not supported with Gemini due to the
    # limitation of the current camel design.

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for Gemini backend.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into generate_content().
            api_key (Optional[str]): The API key for authenticating with the
                gemini service. (default: :obj:`None`)
            url (Optional[str]): The url to the gemini service.
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `GeminiTokenCounter` will be
                used.
        """
        import os

        import google.generativeai as genai
        from google.generativeai.types.generation_types import GenerationConfig

        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )
        self._api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        genai.configure(api_key=self._api_key)
        self._client = genai.GenerativeModel(self.model_type.value)

        keys = list(self.model_config_dict.keys())
        generation_config_dict = {
            k: self.model_config_dict.pop(k)
            for k in keys
            if hasattr(GenerationConfig, k)
        }
        generation_config = genai.types.GenerationConfig(
            **generation_config_dict
        )
        self.model_config_dict["generation_config"] = generation_config

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = GeminiTokenCounter(self.model_type)
        return self._token_counter

    @api_keys_required("GOOGLE_API_KEY")
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> ChatCompletion:
        r"""Runs inference of Gemini model.
        This method can handle multimodal input

        Args:
            messages: Message list or Message with the chat history
                in OpenAi format.

        Returns:
            response: A ChatCompletion object formatted for the OpenAI API.
        """
        response = self._client.generate_content(
            contents=self.to_gemini_req(messages),
            **self.model_config_dict,
        )
        response.resolve()
        return self.to_openai_response(response)

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to Gemini API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        if self.model_config_dict is not None:
            for param in self.model_config_dict:
                if param not in Gemini_API_PARAMS:
                    raise ValueError(
                        f"Unexpected argument `{param}` is "
                        "input into Gemini model backend."
                    )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)

    def to_gemini_req(self, messages: List[OpenAIMessage]) -> 'ContentsType':
        r"""Converts the request from the OpenAI API format to
            the Gemini API request format.

        Args:
            messages: The request object from the OpenAI API.

        Returns:
            converted_messages: A list of messages formatted for Gemini API.
        """
        # role reference
        # https://ai.google.dev/api/python/google/generativeai/protos/Content
        converted_messages = []
        for message in messages:
            role = message.get('role')
            if role == 'assistant':
                role_to_gemini = 'model'
            else:
                role_to_gemini = 'user'
            converted_message = {
                "role": role_to_gemini,
                "parts": message.get("content"),
            }
            converted_messages.append(converted_message)
        return converted_messages

    def to_openai_response(
        self,
        response: 'GenerateContentResponse',
    ) -> ChatCompletion:
        r"""Converts the response from the Gemini API to the OpenAI API
        response format.

        Args:
            response: The response object returned by the Gemini API

        Returns:
            openai_response: A ChatCompletion object formatted for
                the OpenAI API.
        """
        import time
        import uuid

        openai_response = ChatCompletion(
            id=f"chatcmpl-{uuid.uuid4().hex!s}",
            object="chat.completion",
            created=int(time.time()),
            model=self.model_type.value,
            choices=[],
        )
        for i, candidate in enumerate(response.candidates):
            content = ""
            if candidate.content and len(candidate.content.parts) > 0:
                content = candidate.content.parts[0].text
            finish_reason = candidate.finish_reason
            finish_reason_mapping = {
                "FinishReason.STOP": "stop",
                "FinishReason.SAFETY": "content_filter",
                "FinishReason.RECITATION": "content_filter",
                "FinishReason.MAX_TOKENS": "length",
            }
            finish_reason = finish_reason_mapping.get(finish_reason, "stop")
            choice = Choice(
                index=i,
                message=ChatCompletionMessage(
                    role="assistant", content=content
                ),
                finish_reason=finish_reason,
            )
        openai_response.choices.append(choice)
        return openai_response
