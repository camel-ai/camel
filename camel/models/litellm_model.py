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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from camel.configs import LITELLM_API_PARAMS
from camel.messages import OpenAIMessage
from camel.utils import LiteLLMTokenCounter

if TYPE_CHECKING:
    from litellm.utils import CustomStreamWrapper, ModelResponse


class LiteLLMModel:
    r"""Constructor for LiteLLM backend with OpenAI compatibility."""

    # NOTE: Currently "stream": True is not supported with LiteLLM due to the
    # limitation of the current camel design.

    def __init__(
        self, model_type: str, model_config_dict: Dict[str, Any]
    ) -> None:
        r"""Constructor for LiteLLM backend.

        Args:
            model_type (str): Model for which a backend is created,
                such as GPT-3.5-turbo, Claude-2, etc.
            model_config_dict (Dict[str, Any]): A dictionary of parameters for
                the model configuration.
        """
        self.model_type = model_type
        self.model_config_dict = model_config_dict
        self._client = None
        self._token_counter: Optional[LiteLLMTokenCounter] = None
        self.check_model_config()

    @property
    def client(self):
        if self._client is None:
            from litellm import completion

            self._client = completion
        return self._client

    @property
    def token_counter(self) -> LiteLLMTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            LiteLLMTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = LiteLLMTokenCounter(self.model_type)
        return self._token_counter

    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union['ModelResponse', 'CustomStreamWrapper']:
        r"""Runs inference of LiteLLM chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI format.

        Returns:
            Union[ModelResponse, CustomStreamWrapper]:
                `ModelResponse` in the non-stream mode, or
                `CustomStreamWrapper` in the stream mode.
        """
        response = self.client(
            model=self.model_type,
            messages=messages,
            **self.model_config_dict,
        )
        return response

    def check_model_config(self):
        r"""Check whether the model configuration contains any unexpected
        arguments to LiteLLM API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments.
        """
        for param in self.model_config_dict:
            if param not in LITELLM_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into LiteLLM model backend."
                )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
