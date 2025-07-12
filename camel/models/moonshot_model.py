# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

import os
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncStream
from pydantic import BaseModel

from camel.configs import MOONSHOT_API_PARAMS, MoonshotConfig
from camel.messages import OpenAIMessage
from camel.models._utils import try_modify_message_with_format
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
    get_current_agent_session_id,
    update_langfuse_trace,
)

if os.environ.get("LANGFUSE_ENABLED", "False").lower() == "true":
    try:
        from langfuse.decorators import observe
    except ImportError:
        from camel.utils import observe
elif os.environ.get("TRACEROOT_ENABLED", "False").lower() == "true":
    try:
        from traceroot import trace as observe  # type: ignore[import]
    except ImportError:
        from camel.utils import observe
else:
    from camel.utils import observe


class MoonshotModel(OpenAICompatibleModel):
    r"""Moonshot API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of Moonshot series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into :obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`MoonshotConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Moonshot service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Moonshot service.
            (default: :obj:`https://api.moonshot.cn/v1`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required([("api_key", "MOONSHOT_API_KEY")])
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
            model_config_dict = MoonshotConfig().as_dict()
        api_key = api_key or os.environ.get("MOONSHOT_API_KEY")
        url = url or os.environ.get(
            "MOONSHOT_API_BASE_URL",
            "https://api.moonshot.cn/v1",
        )
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
            **kwargs,
        )

    def _prepare_request(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        r"""Prepare the request configuration for Moonshot API.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Dict[str, Any]: The prepared request configuration.
        """
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        if tools:
            request_config["tools"] = tools
        elif response_format:
            # Use the same approach as DeepSeek for structured output
            try_modify_message_with_format(messages[-1], response_format)
            request_config["response_format"] = {"type": "json_object"}

        return request_config

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of Moonshot chat completion asynchronously.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
        """

        # Update Langfuse trace with current agent session and metadata
        agent_session_id = get_current_agent_session_id()
        if agent_session_id:
            update_langfuse_trace(
                session_id=agent_session_id,
                metadata={
                    "agent_id": agent_session_id,
                    "model_type": str(self.model_type),
                },
                tags=["CAMEL-AI", str(self.model_type)],
            )

        request_config = self._prepare_request(
            messages, response_format, tools
        )

        return await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    def check_model_config(self):
        r"""Check whether the model configuration contains any
        unexpected arguments to Moonshot API.

        Raises:
            ValueError: If the model configuration dictionary contains any
                unexpected arguments to Moonshot API.
        """
        for param in self.model_config_dict:
            if param not in MOONSHOT_API_PARAMS:
                raise ValueError(
                    f"Unexpected argument `{param}` is "
                    "input into Moonshot model backend."
                )
