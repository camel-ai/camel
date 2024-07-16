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
import re
from typing import Any, Dict, List, Optional, Union

from openai import OpenAI, Stream

from camel.configs import OPENAI_API_PARAMS
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    model_api_key_required,
)


class NvidiaModel(BaseModelBackend):
    r"""Nvidia API in a unified BaseModelBackend interface."""

    # NOTE: Nemotron model doesn't support additional model config like OpenAI.

    def __init__(
        self,
        model_type: ModelType,
        model_config_dict: Dict[str, Any],
        api_key: Optional[str] = None,
    ) -> None:
        r"""Constructor for Nvidia backend.

        Args:
            model_type (ModelType): Model for which a backend is created.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into openai.ChatCompletion.create().
            api_key (Optional[str]): The API key for authenticating with the
                Nvidia service. (default: :obj:`None`)
        """
        super().__init__(model_type, model_config_dict)
        url = os.environ.get('NVIDIA_API_BASE_URL', None)
        self._api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not url or not self._api_key:
            raise ValueError("The NVIDIA API base url and key should be set.")
        self._client = OpenAI(
            timeout=60, max_retries=3, base_url=url, api_key=self._api_key
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
            # NOTE: It's a temporary setting for token counter.
            self._token_counter = OpenAITokenCounter(ModelType.GPT_3_5_TURBO)
        return self._token_counter

    @model_api_key_required
    def run(
        self,
        messages: List[OpenAIMessage],
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion.
        user/assistant messages should alternate starting with `user`.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode.
        """
        # print(messages)
        if messages[0]['role'] == 'system':
            messages[0]['role'] = 'user'
            self.system_message = messages[0]

        # Nemotron model only accept 'user' or 'assistant' as role.
        messages = [messages[0], messages[-1]]
        for message in messages:
            if message['role'] not in ['user', 'assistant']:
                message['role'] = 'user'  # type: ignore[arg-type]

        # Split options
        options = [
            op.split('\nInput:')[0][3:]
            for op in messages[1]['content'].split('\nOption ')[1:]
        ]

        # Then for each option
        responses = []
        for i, option in enumerate(options):
            response = self._client.chat.completions.create(
                messages=[
                    self.system_message,
                    {'role': 'assistant', 'content': 'Proposal: ' + option},
                ],
                model=self.model_type.value,
            )
            scores = response.choices[0].message[0].content
            pattern = r'[-+]?[0-9]*\.?[0-9]+'
            numbers = re.findall(pattern, scores)
            numbers = [float(num) for num in numbers]
            # Modify chat message
            response.choices[0].message[0].content = (
                f'I choose option {i+1}: "{option}" with scores: ' + scores
            )
            responses.append((response, sum(numbers)))

        choice = sorted(responses, key=lambda x: x[1], reverse=True)[0][0]
        del responses

        return choice

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
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
