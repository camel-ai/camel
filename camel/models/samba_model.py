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

from camel.configs import SAMBA_API_PARAMS
from camel.messages import OpenAIMessage
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


class SambaModel:
    r"""SambaNova service interface."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for SambaNova backend.

        Args:
            model_type (ModelType): Model for which a backend is created.
                Currently only support `"llama3-405b"`
            api_key (Optional[str]): The API key for authenticating with the
                SambaNova service. (default: :obj:`None`)
            url (Optional[str]): The url to the SambaNova service. (default:
                :obj:`"https://fast-api.snova.ai/v1/chat/completions"`)
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter(ModelType.
                GPT_3_5_TURBO)` will be used.
        """
        self.model_type = model_type
        self._api_key = api_key or os.environ.get("SAMBA_API_KEY")
        self._url = url or os.environ.get(
            "SAMBA_API_BASE_URL",
            "https://fast-api.snova.ai/v1/chat/completions",
        )
        self._token_counter = token_counter
        self.model_config_dict = model_config_dict
        self.check_model_config()

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

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to SambaNova API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to SambaNova API.
        """
        for param in self.model_config_dict:
            if param not in SAMBA_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into SambaNova model backend."
                )

    @api_keys_required("SAMBA_API_KEY")
    def run(  # type: ignore[misc]
        self, messages: List[OpenAIMessage]
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs SambaNova's FastAPI service.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.

        Raises:
            ValueError: If the model is not configured to run in streaming
                mode.
        """

        if self.model_config_dict.get("stream") is True:
            return self._run_streaming(messages)
        else:
            return self._run_non_streaming(messages)

    def _run_streaming(  # type: ignore[misc]
        self, messages: List[OpenAIMessage]
    ) -> Stream[ChatCompletionChunk]:
        """Handles the streaming mode."""
        import httpx

        headers = {
            "Authorization": f"Basic {self._api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "messages": messages,
            "max_tokens": self.token_limit,
            "stop": self.model_config_dict.get("stop"),
            "model": self.model_type.value,
            "stream": True,
            "stream_options": self.model_config_dict.get("stream_options"),
        }

        with httpx.stream(
            "POST",
            self._url or "https://fast-api.snova.ai/v1/chat/completions",
            headers=headers,
            json=data,
        ) as api_response:
            stream = Stream[ChatCompletionChunk](
                cast_to=ChatCompletionChunk,
                response=api_response,
                client=OpenAI(),
            )
            for chunk in stream:
                yield chunk

    def _run_non_streaming(
        self, messages: List[OpenAIMessage]
    ) -> ChatCompletion:
        r"""Handles the non-streaming mode."""
        import json

        import httpx

        headers = {
            "Authorization": f"Basic {self._api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "messages": messages,
            "max_tokens": self.token_limit,
            "stop": self.model_config_dict.get("stop"),
            "model": self.model_type.value,
            "stream": True,
            "stream_options": self.model_config_dict.get("stream_options"),
        }

        with httpx.stream(
            "POST",
            self._url or "https://fast-api.snova.ai/v1/chat/completions",
            headers=headers,
            json=data,
        ) as api_response:
            samba_response = []
            for chunk in api_response.iter_text():
                if chunk.startswith('data: '):
                    chunk = chunk[6:]
                if '[DONE]' in chunk:
                    break
                json_data = json.loads(chunk)
                samba_response.append(json_data)
            return self._to_openai_response(samba_response)

    def _to_openai_response(
        self, samba_response: List[Dict[str, Any]]
    ) -> ChatCompletion:
        # Step 1: Combine the content from each chunk
        full_content = ""
        for chunk in samba_response:
            if chunk['choices']:
                for choice in chunk['choices']:
                    delta_content = choice['delta'].get('content', '')
                    full_content += delta_content

        # Step 2: Create the ChatCompletion object
        # Extract relevant information from the first chunk
        first_chunk = samba_response[0]

        choices = [
            dict(
                index=0,  # type: ignore[index]
                message={
                    "role": 'assistant',
                    "content": full_content.strip(),
                },
                finish_reason=samba_response[-2]['choices'][0]['finish_reason']
                or None,
            )
        ]

        obj = ChatCompletion.construct(
            id=first_chunk['id'],
            choices=choices,
            created=first_chunk['created'],
            model=first_chunk['model'],
            object="chat.completion",
            usage=None,
        )

        return obj

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for a given model.

        Returns:
            int: The maximum token limit for the given model.
        """
        return (
            self.model_config_dict.get("max_tokens")
            or self.model_type.token_limit
        )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
