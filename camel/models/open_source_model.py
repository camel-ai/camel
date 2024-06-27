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
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI, Stream

from camel.configs import OPENAI_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import BaseTokenCounter, OpenSourceTokenCounter


class OpenSourceModel(BaseModelBackend):
    r"""Class for interace with OpenAI-API-compatible servers running
    open-source models.
    """

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
        url: Optional[str] = None,
    ) -> None:
        r"""Constructor for model backends of Open-source models.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into :obj:`openai.ChatCompletion.create()`.
            api_key (Optional[str]): The API key for authenticating with the
                model service. (ignored for open-source models)
            url (Optional[str]): The url to the model service.
        """
        super().__init__(model_type, model_config_dict, api_key, url)
        self._token_counter: Optional[BaseTokenCounter] = None

        # Check whether the input model type is open-source
        if not model_type.is_open_source:
            raise ValueError(
                f"Model `{model_type}` is not a supported open-source model."
            )

        # Check whether input model path is empty
        model_path: Optional[str] = self.model_config_dict.get(
            "model_path", None
        )
        if not model_path:
            raise ValueError("Path to open-source model is not provided.")
        self.model_path: str = model_path

        # Check whether the model name matches the model type
        self.model_name: str = self.model_path.split('/')[-1]
        if not self.model_type.validate_model_name(self.model_name):
            raise ValueError(
                f"Model name `{self.model_name}` does not match model type "
                f"`{self.model_type.value}`."
            )

        # Load the server URL and check whether it is None
        server_url: Optional[str] = url or self.model_config_dict.get(
            "server_url", None
        )
        if not server_url:
            raise ValueError(
                "URL to server running open-source LLM is not provided."
            )
        self.server_url: str = server_url
        self._client = OpenAI(
            base_url=self.server_url,
            timeout=60,
            max_retries=3,
            api_key="fake_key",
        )

        # Replace `model_config_dict` with only the params to be
        # passed to OpenAI API
        self.model_config_dict = self.model_config_dict["api_params"].__dict__

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            BaseTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = OpenSourceTokenCounter(
                self.model_type, self.model_path
            )
        return self._token_counter

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI-API-style chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
        """
        messages_openai: List[OpenAIMessage] = messages
        response = self._client.chat.completions.create(
            messages=messages_openai,
            model=self.model_name,
            **self.model_config_dict,
        )
        return response

    def check_model_config(self):
        r"""Check whether the model configuration is valid for open-source
        model backends.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to OpenAI API, or it does not contain
                :obj:`model_path` or :obj:`server_url`.
        """
        if (
            "model_path" not in self.model_config_dict
            or "server_url" not in self.model_config_dict
        ):
            raise ValueError(
                "Invalid configuration for open-source model backend with "
                ":obj:`model_path` or :obj:`server_url` missing."
            )

        for param in self.model_config_dict["api_params"].__dict__:
            if param not in OPENAI_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into open-source model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
