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
from typing import Any, Dict, Iterator, List, Optional, Union

from openai import OpenAI, Stream

from camel.configs import OPENAI_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import BaseTokenCounter, OpenAITokenCounter, api_key_required


class OpenAIModel(BaseModelBackend):
    r"""OpenAI API in a unified BaseModelBackend interface."""

    def __init__(
        self, model_type: ModelType, model_config_dict: Dict[str, Any]
    ) -> None:
        r"""Constructor for OpenAI backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of GPT_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
        """
        super().__init__(model_type, model_config_dict)
        url = os.environ.get('OPENAI_API_BASE_URL', None)
        self._client = OpenAI(timeout=60, max_retries=3, base_url=url)
        self._token_counter: Optional[BaseTokenCounter] = None

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(self.model_type)
        return self._token_counter

    @api_key_required
    def run(  # type: ignore[return]
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Iterator[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion,  Iterator[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Iterator[ChatCompletionChunk]` in the stream mode.
        """
        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type.value,
            **self.model_config_dict,
        )

        # Handle streaming responses by yielding each chunk as it's received
        if isinstance(response, Stream):
            print("=" * 50)
            print("OpenAI model handling as Stream")
            for chunk in response:
                yield chunk
        else:
            print("=" * 50)
            print(
                "OpenAI model handling as Single Response,output of openai response:",
                response,
            )
            return response  # Handling non-stream response

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to OpenAI API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in OPENAI_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into OpenAI model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
