# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========

import os
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.messages import OpenAIMessage
from camel.models._interleaved_thinking_mixin import InterleavedThinkingMixin
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
)


class VolcanoModel(InterleavedThinkingMixin, OpenAICompatibleModel):
    r"""Volcano Engine API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into the API call. If
            :obj:`None`, :obj:`{}` will be used. (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Volcano Engine service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Volcano Engine service.
            (default: :obj:`https://ark.cn-beijing.volces.com/api/v3`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter`
            will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required(
        [
            ("api_key", "VOLCANO_API_KEY"),
        ]
    )
    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = {}

        api_key = api_key or os.environ.get("VOLCANO_API_KEY")
        url = (
            url
            or os.environ.get("VOLCANO_API_BASE_URL")
            or "https://ark.cn-beijing.volces.com/api/v3"
        )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type,
            model_config_dict,
            api_key,
            url,
            token_counter,
            timeout,
            max_retries,
            **kwargs,
        )
        # Initialize interleaved thinking state
        self._init_thinking_state()

    def _prepare_request_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        r"""Prepare the request configuration dictionary.

        Overrides the base method to remove interleaved_thinking parameter
        which is only used internally.
        """
        request_config = super()._prepare_request_config(tools)
        return self._prepare_thinking_config(request_config)

    def run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of Volcano Engine chat completion.

        Overrides the base run method to inject reasoning_content from
        previous responses into subsequent requests, as required by
        Volcano Engine's doubao-seed models with deep thinking enabled.

        Args:
            messages: Message list with the chat history in OpenAI API format.
            response_format: The format of the response.
            tools: The schema of the tools to use for the request.

        Returns:
            ChatCompletion in the non-stream mode, or
            Stream[ChatCompletionChunk] in the stream mode.
        """
        # Inject reasoning content from previous response
        processed_messages = self._inject_reasoning(messages)

        # Call parent's run
        response = super().run(processed_messages, response_format, tools)

        # Extract and store reasoning content for next request
        if isinstance(response, ChatCompletion):
            self._last_reasoning = self._extract_reasoning(response)

        return response

    async def arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs async inference of Volcano Engine chat completion.

        Overrides the base arun method to inject reasoning_content from
        previous responses into subsequent requests, as required by
        Volcano Engine's doubao-seed models with deep thinking enabled.

        Args:
            messages: Message list with the chat history in OpenAI API format.
            response_format: The format of the response.
            tools: The schema of the tools to use for the request.

        Returns:
            ChatCompletion in the non-stream mode, or
            AsyncStream[ChatCompletionChunk] in the stream mode.
        """
        # Inject reasoning content from previous response
        processed_messages = self._inject_reasoning(messages)

        # Call parent's arun
        response = await super().arun(
            processed_messages, response_format, tools
        )

        # Extract and store reasoning content for next request
        if isinstance(response, ChatCompletion):
            self._last_reasoning = self._extract_reasoning(response)

        return response
