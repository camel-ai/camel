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

from openai import AzureOpenAI, Stream

from camel.configs import OPENAI_API_PARAMS_WITH_FUNCTIONS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import BaseTokenCounter, OpenAITokenCounter

azure_model_name_to_type = {
    "gpt-35-turbo": ModelType.GPT_3_5_TURBO,
    "gpt-35-turbo-16k": ModelType.GPT_3_5_TURBO_16K,
    "gpt-4": ModelType.GPT_4,
    "gpt-4-32k": ModelType.GPT_4_32K,
    "gpt-4-1106-preview": ModelType.GPT_4_TURBO,
}


class AzureOpenAIModel(BaseModelBackend):
    r"""Azure OpenAI API in a unified BaseModelBackend interface."""

    def __init__(self, model_type: ModelType,
                 model_config_dict: Dict[str, Any]) -> None:
        r"""Constructor for Azure OpenAI backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                one of AZURE series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
        """
        super().__init__(model_type, model_config_dict)
        url = os.environ.get('OPENAI_API_BASE_URL', '')
        api_version = os.environ.get(
            'AZURE_OPENAI_API_VERSION', '2023-10-01-preview'
        )
        self._client = AzureOpenAI(
            timeout=60,
            max_retries=3,
            api_version=api_version,
            azure_endpoint=url,
        )
        self._token_counter: Optional[BaseTokenCounter] = None

        self.deployment_name = os.environ.get(
            'AZURE_MODEL_DEPLOYMENT_NAME', 'gpt-3.5-turbo-1106'
        )
        assert self.deployment_name is not None, \
            "Azure model deployment name is not provided."

        self.model_name = os.environ.get('AZURE_MODEL_TOKEN_LIMIT', 8192)

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

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        response = self._client.chat.completions.create(
            messages=messages,
            model=self.deployment_name,
            **self.model_config_dict,
        )
        return response

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to OpenAI API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in OPENAI_API_PARAMS_WITH_FUNCTIONS:
                raise ValueError(f"Unexpected argument `{param}` is "
                                 "input into OpenAI model backend.")

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
