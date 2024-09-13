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
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional, Union

import httpx
from openai import OpenAI, Stream

from camel.configs import (
    SAMBA_CLOUD_API_PARAMS,
    SAMBA_FAST_API_PARAMS,
    SAMBA_VERSE_API_PARAMS,
)
from camel.messages import OpenAIMessage
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    CompletionUsage,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
)


class SambaModel:
    r"""SambaNova service interface."""

    def __init__(
        self,
        model_type: str,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        r"""Constructor for SambaNova backend.

        Args:
            model_type (str): Model for which a SambaNova backend is
                created. Supported models via Fast API: `https://sambanova.ai/
                fast-api?api_ref=128521`. Supported models via SambaVerse API
                is listed in `https://sambaverse.sambanova.ai/models`.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into API request.
            api_key (Optional[str]): The API key for authenticating with the
                SambaNova service. (default: :obj:`None`)
            url (Optional[str]): The url to the SambaNova service. Current
                support SambaNova Fast API: :obj:`"https://fast-api.snova.ai/
                v1/chat/ completions"`, SambaVerse API: :obj:`"https://
                sambaverse.sambanova.ai/api/predict"` and SambaNova Cloud:
                :obj:`"https://api.sambanova.ai/v1"`
                (default::obj:`"https://fast-api.snova.ai/v1/chat/completions"`)
            token_counter (Optional[BaseTokenCounter]): Token counter to use
                for the model. If not provided, `OpenAITokenCounter(ModelType.
                GPT_4O_MINI)` will be used.
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

        if self._url == "https://api.sambanova.ai/v1":
            self._client = OpenAI(
                timeout=60,
                max_retries=3,
                base_url=self._url,
                api_key=self._api_key,
            )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to SambaNova API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to SambaNova API.
        """
        if self._url == "https://fast-api.snova.ai/v1/chat/completions":
            for param in self.model_config_dict:
                if param not in SAMBA_FAST_API_PARAMS:
                    raise ValueError(
                        f"Unexpected argument `{param}` is "
                        "input into SambaNova Fast API."
                    )
        elif self._url == "https://sambaverse.sambanova.ai/api/predict":
            for param in self.model_config_dict:
                if param not in SAMBA_VERSE_API_PARAMS:
                    raise ValueError(
                        f"Unexpected argument `{param}` is "
                        "input into SambaVerse API."
                    )

        elif self._url == "https://api.sambanova.ai/v1":
            for param in self.model_config_dict:
                if param not in SAMBA_CLOUD_API_PARAMS:
                    raise ValueError(
                        f"Unexpected argument `{param}` is "
                        "input into SambaCloud API."
                    )

        else:
            raise ValueError(
                f"{self._url} is not supported, please check the url to the"
                " SambaNova service"
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
        """

        if self.model_config_dict.get("stream") is True:
            return self._run_streaming(messages)
        else:
            return self._run_non_streaming(messages)

    def _run_streaming(  # type: ignore[misc]
        self, messages: List[OpenAIMessage]
    ) -> Stream[ChatCompletionChunk]:
        r"""Handles streaming inference with SambaNova's API.

        Args:
            messages (List[OpenAIMessage]): A list of messages representing the
                chat history in OpenAI API format.

        Returns:
            Stream[ChatCompletionChunk]: A generator yielding
                `ChatCompletionChunk` objects as they are received from the
                API.

        Raises:
            RuntimeError: If the HTTP request fails.
        """

        # Handle SambaNova's Fast API
        if self._url == "https://fast-api.snova.ai/v1/chat/completions":
            headers = {
                "Authorization": f"Basic {self._api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "messages": messages,
                "max_tokens": self.token_limit,
                "stop": self.model_config_dict.get("stop"),
                "model": self.model_type,
                "stream": True,
                "stream_options": self.model_config_dict.get("stream_options"),
            }

            try:
                with httpx.stream(
                    "POST",
                    self._url,
                    headers=headers,
                    json=data,
                ) as api_response:
                    stream = Stream[ChatCompletionChunk](
                        cast_to=ChatCompletionChunk,
                        response=api_response,
                        client=OpenAI(api_key="required_but_not_used"),
                    )
                    for chunk in stream:
                        yield chunk
            except httpx.HTTPError as e:
                raise RuntimeError(f"HTTP request failed: {e!s}")

        # Handle SambaNova's Cloud API
        elif self._url == "https://api.sambanova.ai/v1":
            response = self._client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **self.model_config_dict,
            )
            return response

        elif self._url == "https://sambaverse.sambanova.ai/api/predict":
            raise ValueError(
                "https://sambaverse.sambanova.ai/api/predict doesn't support"
                " stream mode"
            )

    def _run_non_streaming(
        self, messages: List[OpenAIMessage]
    ) -> ChatCompletion:
        r"""Handles non-streaming inference with SambaNova's API.

        Args:
            messages (List[OpenAIMessage]): A list of messages representing the
                message in OpenAI API format.

        Returns:
            ChatCompletion: A `ChatCompletion` object containing the complete
                response from the API.

        Raises:
            RuntimeError: If the HTTP request fails.
            ValueError: If the JSON response cannot be decoded or is missing
                expected data.
        """

        # Handle SambaNova's Fast API
        if self._url == "https://fast-api.snova.ai/v1/chat/completions":
            headers = {
                "Authorization": f"Basic {self._api_key}",
                "Content-Type": "application/json",
            }

            data = {
                "messages": messages,
                "max_tokens": self.token_limit,
                "stop": self.model_config_dict.get("stop"),
                "model": self.model_type,
                "stream": True,
                "stream_options": self.model_config_dict.get("stream_options"),
            }

            try:
                with httpx.stream(
                    "POST",
                    self._url,
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
                    return self._fastapi_to_openai_response(samba_response)
            except httpx.HTTPError as e:
                raise RuntimeError(f"HTTP request failed: {e!s}")
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to decode JSON response: {e!s}")

        # Handle SambaNova's Cloud API
        elif self._url == "https://api.sambanova.ai/v1":
            response = self._client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **self.model_config_dict,
            )
            return response

        # Handle SambaNova's Sambaverse API
        else:
            headers = {
                "Content-Type": "application/json",
                "key": str(self._api_key),
                "modelName": self.model_type,
            }

            data = {
                "instance": json.dumps(
                    {
                        "conversation_id": str(uuid.uuid4()),
                        "messages": messages,
                    }
                ),
                "params": {
                    "do_sample": {"type": "bool", "value": "true"},
                    "max_tokens_to_generate": {
                        "type": "int",
                        "value": str(self.model_config_dict.get("max_tokens")),
                    },
                    "process_prompt": {"type": "bool", "value": "true"},
                    "repetition_penalty": {
                        "type": "float",
                        "value": str(
                            self.model_config_dict.get("repetition_penalty")
                        ),
                    },
                    "return_token_count_only": {
                        "type": "bool",
                        "value": "false",
                    },
                    "select_expert": {
                        "type": "str",
                        "value": self.model_type.split('/')[1],
                    },
                    "stop_sequences": {
                        "type": "str",
                        "value": self.model_config_dict.get("stop_sequences"),
                    },
                    "temperature": {
                        "type": "float",
                        "value": str(
                            self.model_config_dict.get("temperature")
                        ),
                    },
                    "top_k": {
                        "type": "int",
                        "value": str(self.model_config_dict.get("top_k")),
                    },
                    "top_p": {
                        "type": "float",
                        "value": str(self.model_config_dict.get("top_p")),
                    },
                },
            }

            try:
                # Send the request and handle the response
                with httpx.Client() as client:
                    response = client.post(
                        self._url,  # type: ignore[arg-type]
                        headers=headers,
                        json=data,
                    )

                raw_text = response.text
                # Split the string into two dictionaries
                dicts = raw_text.split('}\n{')

                # Keep only the last dictionary
                last_dict = '{' + dicts[-1]

                # Parse the dictionary
                last_dict = json.loads(last_dict)
                return self._sambaverse_to_openai_response(last_dict)  # type: ignore[arg-type]

            except httpx.HTTPStatusError:
                raise RuntimeError(f"HTTP request failed: {raw_text}")

    def _fastapi_to_openai_response(
        self, samba_response: List[Dict[str, Any]]
    ) -> ChatCompletion:
        r"""Converts SambaNova Fast API response chunks into an
            OpenAI-compatible response.

        Args:
            samba_response (List[Dict[str, Any]]): A list of dictionaries
                representing partial responses from the SambaNova Fast API.

        Returns:
            ChatCompletion: A `ChatCompletion` object constructed from the
                aggregated response data.
        """

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
                finish_reason=samba_response[-1]['choices'][0]['finish_reason']
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

    def _sambaverse_to_openai_response(
        self, samba_response: Dict[str, Any]
    ) -> ChatCompletion:
        r"""Converts SambaVerse API response into an OpenAI-compatible
        response.

        Args:
            samba_response (Dict[str, Any]): A dictionary representing
                responses from the SambaVerse API.

        Returns:
            ChatCompletion: A `ChatCompletion` object constructed from the
                aggregated response data.
        """
        choices = [
            dict(
                index=0,
                message={
                    "role": 'assistant',
                    "content": samba_response['result']['responses'][0][
                        'completion'
                    ],
                },
                finish_reason=samba_response['result']['responses'][0][
                    'stop_reason'
                ],
            )
        ]

        obj = ChatCompletion.construct(
            id=None,
            choices=choices,
            created=int(time.time()),
            model=self.model_type,
            object="chat.completion",
            # SambaVerse API only provide `total_tokens`
            usage=CompletionUsage(
                completion_tokens=0,
                prompt_tokens=0,
                total_tokens=int(
                    samba_response['result']['responses'][0][
                        'total_tokens_count'
                    ]
                ),
            ),
        )

        return obj

    @property
    def token_limit(self) -> int:
        r"""Returns the maximum token limit for the given model.

        Returns:
            int: The maximum token limit for the given model.
        """
        max_tokens = self.model_config_dict["max_tokens"]
        return max_tokens

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
