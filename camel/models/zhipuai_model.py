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
from camel.messages import OpenAIMessage
from zhipuai import ZhipuAI
from zhipuai.core._sse_client import StreamResponse
from camel.configs import ZHIPU_API_PARAMS
from camel.models import BaseModelBackend
from camel.types import Completion, ChatCompletionChunk, ModelType
from camel.utils import BaseTokenCounter, api_key_required, ZhipuAITokenCounter
class ZhipuAIModel(BaseModelBackend):
    r"""ZhipuAI API in a unified BaseModelBackend interface."""

    def __init__(
        self, model_type: ModelType, model_config_dict: Dict[str, Any]
    ) -> None:
        r"""Constructor for ZhipuAI backend.

        Args:
            model_type (ModelType): Model for which a backend is created,
                such as GLM_* series.
            model_config_dict (Dict[str, Any]): A dictionary that will
                be fed into zhipuai.ChatCompletion.create().
        """
        super().__init__(model_type, model_config_dict)
        url = os.environ.get('ZHIPUAI_API_BASE_URL', None)
        api_key = os.environ.get('ZHIPUAI_API_KEY', None)
        self._client = ZhipuAI(api_key=api_key,base_url=url)
        self._token_counter: Optional[BaseTokenCounter] = None

    @api_key_required
    def run(
        self,
        messages:  List[OpenAIMessage],
    ) -> Union[Completion, StreamResponse[ChatCompletionChunk]]:
        r"""Runs inference of ZhipuAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in ZhipuAI API format.

        Returns:
            Union[Completion, StreamResponse[ChatCompletionChunk]]:
                `Completion` in the non-stream mode, or
                `StreamResponse[ChatCompletionChunk]` in the stream mode.
        """
        response = self._client.chat.completions.create(
            messages=messages,
            model=self.model_type.value,
            **self.model_config_dict,
        )
        return response

    @property
    def token_counter(self) -> ZhipuAITokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            ZhipuAITokenCounter: The token counter following the model's
                tokenization style.
        """
        
        if not self._token_counter:
            self._token_counter = ZhipuAITokenCounter(self.model_type)
        return self._token_counter

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to ZhipuAI API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to ZhipuAI API.
        """
        for param in self.model_config_dict:
            if param not in ZHIPU_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into ZhipuAI model backend."
                )
        pass

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
            which sends partial results each time.
        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)

