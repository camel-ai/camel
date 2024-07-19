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
from typing import List, Optional

from openai import OpenAI

from camel.messages import OpenAIMessage
from camel.types import ChatCompletion, ModelType
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    model_api_key_required,
)


class NvidiaModelV2:
    r"""Nvidia API in a unified BaseModelBackend interface."""

    # NOTE: Nemotron model doesn't support additional model config like OpenAI.

    def __init__(
        self,
        model_type: ModelType,
        api_key: Optional[str] = None,
    ) -> None:
        r"""Constructor for Nvidia backend.

        Args:
            model_type (ModelType): Model for which a backend is created.
            api_key (Optional[str]): The API key for authenticating with the
                Nvidia service. (default: :obj:`None`)
        """
        self.model_type = model_type
        url = os.environ.get('NVIDIA_API_BASE_URL', None)
        self._api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not url or not self._api_key:
            raise ValueError(
                "NVIDIA_API_BASE_URL and NVIDIA_API_KEY should be set."
            )
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
    ) -> ChatCompletion:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list.

        Returns:
            ChatCompletion.
        """
        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type.value,
        )
        return response
