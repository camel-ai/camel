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

from camel.configs import (
    OPENAI_API_PARAMS_WITH_FUNCTIONS,
    AZURE_OPENAI_API_BACKEND_PARAMS,
)
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    azure_openai_api_key_required,
)


class AzureOpenAIModel(BaseModelBackend):
    r"""Azure OpenAI API in a unified BaseModelBackend interface."""

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        backend_config_dict: Dict[str, Any] = {},
    ) -> None:
        r"""Constructor for Azure OpenAI backend.

        Args:
            model_type (ModelType): Model for which a backend is created at
                Azure, one of GPT_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
            backend_config_dict (Dict[str, Any]): A dictionary that contains
                the backend configs like model_type, deployment_name,
                endpoint, api_version, etc.(default : {})
        """
        super().__init__(model_type, model_config_dict)

        self.backend_config_dict = backend_config_dict

        self.model_type = backend_config_dict.get(
            "model_type", os.environ.get("AZURE_MODEL_TYPE", None))
        self.deployment_name = backend_config_dict.get(
            "deployment_name", os.environ.get("AZURE_DEPLOYMENT_NAME", None))
        self.azure_endpoint = backend_config_dict.get(
            "azure_endpoint", os.environ.get("AZURE_ENDPOINT", None))
        self.api_version = backend_config_dict.get(
            "api_version",
            os.environ.get("AZURE_API_VERSION", "2023-10-01-preview"),
        )

        try:
            assert self.model_type is not None
        except AssertionError:
            raise ValueError("Azure model type is not provided.")
        try:
            assert self.deployment_name is not None
        except AssertionError:
            raise ValueError("Azure model deployment name is not provided.")
        try:
            assert self.api_version is not None
        except AssertionError:
            raise ValueError("Azure API version is not provided.")

        if isinstance(self.model_type, str):
            self.model_type = ModelType[self.model_type.upper()]

        self._client = AzureOpenAI(
            timeout=60,
            max_retries=3,
            api_version=self.api_version,
            azure_endpoint=self.azure_endpoint,
        )
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

    @azure_openai_api_key_required
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of Azure OpenAI chat completion.

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
        unexpected arguments to Azure OpenAI API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Azure OpenAI API.
        """
        for param in self.model_config_dict:
            if param not in OPENAI_API_PARAMS_WITH_FUNCTIONS:
                raise ValueError(f"Unexpected argument `{param}` is "
                                 "input into OpenAI model backend.")

    def check_backend_config(self):
        r"""Check whether the backend configuration contains any
        unexpected arguments to Azure OpenAI API.

        Raises:
            ValueError: If the backend configuration dictionary contains any
                unexpected arguments to Azure OpenAI API.
        """
        for param in self.backend_config_dict:
            if param not in AZURE_OPENAI_API_BACKEND_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` for "
                    "Azure OpenAI API backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)
