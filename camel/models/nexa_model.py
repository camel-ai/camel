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
import subprocess
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI, Stream

from camel.configs import NEXA_API_PARAMS, NexaConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import BaseTokenCounter, OpenAITokenCounter


class NexaModel(BaseModelBackend):
    """Nexa service interface."""

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        """Constructor for Nexa backend.

        Args:
            model_type (Union[ModelType, str]): Model for which a backend is
                created.
            model_config_dict (Optional[Dict[str, Any]], optional): A
            dictionary that will be fed into the API call. If None, default
                configuration will be used. (default: None)
            api_key (Optional[str], optional): The API key for the model
                service. (default: None)
            url (Optional[str], optional): The url to the model service. If not
                provided, environment variable or default URL will be used.
                (default: None)
            token_counter (Optional[BaseTokenCounter], optional): Token counter
                to use for the model. If not provided,
                OpenAITokenCounter(ModelType.GPT_4O_MINI) will be used.
                (default: None)
        """
        if model_config_dict is None:
            model_config_dict = NexaConfig().as_dict()
        url = url or os.environ.get("NEXA_BASE_URL")
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter
        )

        if not self._url:
            self._start_server()

        self._client = OpenAI(
            timeout=60,
            max_retries=3,
            base_url=self._url,
            api_key=self._api_key,
        )

    def _start_server(self) -> None:
        """Starts the Nexa server in a subprocess."""
        try:
            subprocess.Popen(
                [
                    "nexa",
                    "server",
                    self.model_type,
                    "--port",
                    "8000",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print(
                f"Nexa server started on http://localhost:8000 "
                f"for {self.model_type} model."
            )
        except Exception as e:
            print(f"Failed to start Nexa server: {e}.")

    @property
    def token_counter(self) -> BaseTokenCounter:
        """Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    def check_model_config(self):
        """Check whether the model configuration contains any
        unexpected arguments to Nexa API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Nexa API.
        """
        for param in self.model_config_dict:
            if param not in NEXA_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Nexa model backend."
                )

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        """Runs inference of Nexa chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        try:
            response = self._client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **self.model_config_dict,
            )
            return response
        except Exception as e:
            raise Exception(f"Error calling Nexa API: {e!s}")

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
            "Must set `max_tokens` as an integer in `model_config_dict`"
            " when setting up the model. Using 4096 as default value."
        )
        return 4096

    @property
    def stream(self) -> bool:
        """Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
