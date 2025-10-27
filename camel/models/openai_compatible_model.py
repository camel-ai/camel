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
from json import JSONDecodeError
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncOpenAI, AsyncStream, BadRequestError, OpenAI, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from pydantic import BaseModel, ValidationError

from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models._utils import try_modify_message_with_format
from camel.models.base_model import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    get_current_agent_session_id,
    is_langfuse_available,
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


logger = get_logger(__name__)


class OpenAICompatibleModel(BaseModelBackend):
    r"""Constructor for model backend supporting OpenAI compatibility.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`{}` will be used. (default: :obj:`None`)
        api_key (str): The API key for authenticating with the model service.
        url (str): The url to the model service.
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter(
            ModelType.GPT_4O_MINI)` will be used.
            (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        client (Optional[Any], optional): A custom synchronous
            OpenAI-compatible client instance. If provided, this client will
            be used instead of creating a new one. Useful for RL frameworks
            like AReaL or rLLM that provide OpenAI-compatible clients (e.g.,
            ArealOpenAI). The client should implement the OpenAI client
            interface with `.chat.completions.create()` and `.beta.chat.
            completions.parse()` methods. (default: :obj:`None`)
        async_client (Optional[Any], optional): A custom asynchronous
            OpenAI-compatible client instance. If provided, this client will
            be used instead of creating a new one. The client should implement
            the AsyncOpenAI client interface. (default: :obj:`None`)
        **kwargs (Any): Additional arguments to pass to the
            OpenAI client initialization. These can include parameters like
            'organization', 'default_headers', 'http_client', etc.
            Ignored if custom clients are provided.
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        **kwargs: Any,
    ) -> None:
        api_key = api_key or os.environ.get("OPENAI_COMPATIBILITY_API_KEY")
        url = url or os.environ.get("OPENAI_COMPATIBILITY_API_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))

        super().__init__(
            model_type,
            model_config_dict,
            api_key,
            url,
            token_counter,
            timeout,
            max_retries,
        )

        # Use custom clients if provided, otherwise create new ones
        if client is not None:
            # Use the provided custom sync client
            self._client = client
        else:
            # Create default sync client
            if is_langfuse_available():
                from langfuse.openai import OpenAI as LangfuseOpenAI

                self._client = LangfuseOpenAI(
                    timeout=self._timeout,
                    max_retries=max_retries,
                    base_url=self._url,
                    api_key=self._api_key,
                    **kwargs,
                )
            else:
                self._client = OpenAI(
                    timeout=self._timeout,
                    max_retries=max_retries,
                    base_url=self._url,
                    api_key=self._api_key,
                    **kwargs,
                )

        if async_client is not None:
            # Use the provided custom async client
            self._async_client = async_client
        else:
            # Create default async client
            if is_langfuse_available():
                from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI

                self._async_client = LangfuseAsyncOpenAI(
                    timeout=self._timeout,
                    max_retries=max_retries,
                    base_url=self._url,
                    api_key=self._api_key,
                    **kwargs,
                )
            else:
                self._async_client = AsyncOpenAI(
                    timeout=self._timeout,
                    max_retries=max_retries,
                    base_url=self._url,
                    api_key=self._api_key,
                    **kwargs,
                )

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        Stream[ChatCompletionChunk],
        ChatCompletionStreamManager[BaseModel],
    ]:
        r"""Runs inference of OpenAI chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode.
                `ChatCompletionStreamManager[BaseModel]` for
                structured output streaming.
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

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        # Check if streaming is enabled
        is_streaming = self.model_config_dict.get("stream", False)

        if response_format:
            if is_streaming:
                # Use streaming parse for structured output
                return self._request_stream_parse(
                    messages, response_format, tools
                )
            else:
                # Use non-streaming parse for structured output
                return self._request_parse(messages, response_format, tools)
        else:
            result = self._request_chat_completion(messages, tools)

        return result

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[
        ChatCompletion,
        AsyncStream[ChatCompletionChunk],
        AsyncChatCompletionStreamManager[BaseModel],
    ]:
        r"""Runs inference of OpenAI chat completion in async mode.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk],
                AsyncChatCompletionStreamManager[BaseModel]]:
                `ChatCompletion` in the non-stream mode,
                `AsyncStream[ChatCompletionChunk]` in the stream mode,
                or `AsyncChatCompletionStreamManager[BaseModel]` for
                structured output streaming.
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

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        # Check if streaming is enabled
        is_streaming = self.model_config_dict.get("stream", False)

        if response_format:
            if is_streaming:
                # Use streaming parse for structured output
                return await self._arequest_stream_parse(
                    messages, response_format, tools
                )
            else:
                # Use non-streaming parse for structured output
                return await self._arequest_parse(
                    messages, response_format, tools
                )
        else:
            result = await self._arequest_chat_completion(messages, tools)

        return result

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        request_config = self.model_config_dict.copy()

        if tools:
            request_config["tools"] = tools

        return self._client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        request_config = self.model_config_dict.copy()

        if tools:
            request_config["tools"] = tools

        return await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        import copy

        request_config = copy.deepcopy(self.model_config_dict)
        # Remove stream from request_config since OpenAI does not support it
        # when structured response is used
        request_config["response_format"] = response_format
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        try:
            return self._client.beta.chat.completions.parse(
                messages=messages,
                model=self.model_type,
                **request_config,
            )
        except (ValidationError, JSONDecodeError, BadRequestError) as e:
            logger.warning(
                f"Format validation error: {e}. "
                f"Attempting fallback with JSON format."
            )
            try_modify_message_with_format(messages[-1], response_format)
            request_config["response_format"] = {"type": "json_object"}
            try:
                return self._client.beta.chat.completions.parse(
                    messages=messages,
                    model=self.model_type,
                    **request_config,
                )
            except Exception as e:
                logger.error(f"Fallback attempt also failed: {e}")
                raise

    async def _arequest_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        import copy

        request_config = copy.deepcopy(self.model_config_dict)
        # Remove stream from request_config since OpenAI does not support it
        # when structured response is used
        request_config["response_format"] = response_format
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        try:
            return await self._async_client.beta.chat.completions.parse(
                messages=messages,
                model=self.model_type,
                **request_config,
            )
        except (ValidationError, JSONDecodeError, BadRequestError) as e:
            logger.warning(
                f"Format validation error: {e}. "
                f"Attempting fallback with JSON format."
            )
            try_modify_message_with_format(messages[-1], response_format)
            request_config["response_format"] = {"type": "json_object"}
            try:
                return await self._async_client.beta.chat.completions.parse(
                    messages=messages,
                    model=self.model_type,
                    **request_config,
                )
            except Exception as e:
                logger.error(f"Fallback attempt also failed: {e}")
                raise

    def _request_stream_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletionStreamManager[BaseModel]:
        r"""Request streaming structured output parsing.

        Note: This uses OpenAI's beta streaming API for structured outputs.
        """
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        if tools is not None:
            request_config["tools"] = tools

        # Use the beta streaming API for structured outputs
        return self._client.beta.chat.completions.stream(
            messages=messages,
            model=self.model_type,
            response_format=response_format,
            **request_config,
        )

    async def _arequest_stream_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncChatCompletionStreamManager[BaseModel]:
        r"""Request async streaming structured output parsing.

        Note: This uses OpenAI's beta streaming API for structured outputs.
        """
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        if tools is not None:
            request_config["tools"] = tools

        # Use the beta streaming API for structured outputs
        return self._async_client.beta.chat.completions.stream(
            messages=messages,
            model=self.model_type,
            response_format=response_format,
            **request_config,
        )

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            OpenAITokenCounter: The token counter following the model's
                tokenization style.
        """

        if not self._token_counter:
            self._token_counter = OpenAITokenCounter(ModelType.GPT_4O_MINI)
        return self._token_counter

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get('stream', False)
