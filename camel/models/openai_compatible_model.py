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
from json import JSONDecodeError
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from openai import AsyncOpenAI, AsyncStream, BadRequestError, OpenAI, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from pydantic import BaseModel, ValidationError

from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models._utils import (
    pydantic_to_json_schema_response_format,
    with_response_format_system_message,
)
from camel.models.base_model import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
    StructuredOutputMode,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    is_langfuse_available,
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

    @property
    def structured_output_mode(self) -> StructuredOutputMode:
        r"""Declares the structured output capability of this model.

        Subclasses should override to declare their platform's capability.
        Default is :obj:`StructuredOutputMode.JSON_SCHEMA`.

        Returns:
            StructuredOutputMode: The structured output mode for this model.
        """
        return StructuredOutputMode.JSON_SCHEMA

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
            Union[ChatCompletion, Stream[ChatCompletionChunk],
                ChatCompletionStreamManager[BaseModel]]:
                `ChatCompletion` in the non-stream mode, or
                `Stream[ChatCompletionChunk]` in the stream mode, or
                `ChatCompletionStreamManager[BaseModel]` for structured
                output streaming.
        """
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        if response_format:
            mode = self.structured_output_mode

            # JSON_OBJECT / PROMPT_ONLY inject schema into the prompt, which
            # conflicts with tool calling.  When tools are present, skip
            # structured output and let tool_calls carry the structure.
            if tools and mode in (
                StructuredOutputMode.JSON_OBJECT,
                StructuredOutputMode.PROMPT_ONLY,
            ):
                return self._request_chat_completion(messages, tools)

            is_streaming = self.model_config_dict.get("stream", False)

            attempts: List[Tuple[str, Callable[..., Any]]]

            if mode == StructuredOutputMode.JSON_SCHEMA:
                if is_streaming:
                    return self._request_stream_parse(
                        messages, response_format, tools
                    )
                attempts = [
                    ("parse", self._request_parse),
                    ("json_schema", self._request_json_schema),
                    ("json_object", self._request_json_object),
                    ("prompt_only", self._request_prompt_only),
                ]
            elif mode == StructuredOutputMode.JSON_OBJECT:
                attempts = [
                    ("json_object", self._request_json_object),
                    ("prompt_only", self._request_prompt_only),
                ]
            else:
                attempts = [
                    ("prompt_only", self._request_prompt_only),
                ]

            for i, (name, fn) in enumerate(attempts):
                try:
                    return fn(messages, response_format, tools)
                except BadRequestError as e:
                    if i == len(attempts) - 1:
                        raise
                    logger.warning(
                        "%s failed for model %s: %s. " "Falling back to %s.",
                        name,
                        self.model_type,
                        e,
                        attempts[i + 1][0],
                    )
                except (ValidationError, JSONDecodeError) as e:
                    if name != "parse" or i == len(attempts) - 1:
                        raise
                    logger.warning(
                        "%s failed for model %s: %s. " "Falling back to %s.",
                        name,
                        self.model_type,
                        e,
                        attempts[i + 1][0],
                    )

        return self._request_chat_completion(messages, tools)

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
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        if response_format:
            mode = self.structured_output_mode

            if tools and mode in (
                StructuredOutputMode.JSON_OBJECT,
                StructuredOutputMode.PROMPT_ONLY,
            ):
                return await self._arequest_chat_completion(messages, tools)

            is_streaming = self.model_config_dict.get("stream", False)

            attempts: List[Tuple[str, Callable[..., Any]]]

            if mode == StructuredOutputMode.JSON_SCHEMA:
                if is_streaming:
                    return await self._arequest_stream_parse(
                        messages, response_format, tools
                    )
                attempts = [
                    ("parse", self._arequest_parse),
                    ("json_schema", self._arequest_json_schema),
                    ("json_object", self._arequest_json_object),
                    ("prompt_only", self._arequest_prompt_only),
                ]
            elif mode == StructuredOutputMode.JSON_OBJECT:
                attempts = [
                    ("json_object", self._arequest_json_object),
                    ("prompt_only", self._arequest_prompt_only),
                ]
            else:
                attempts = [
                    ("prompt_only", self._arequest_prompt_only),
                ]

            for i, (name, fn) in enumerate(attempts):
                try:
                    return await fn(messages, response_format, tools)
                except BadRequestError as e:
                    if i == len(attempts) - 1:
                        raise
                    logger.warning(
                        "%s failed for model %s: %s. " "Falling back to %s.",
                        name,
                        self.model_type,
                        e,
                        attempts[i + 1][0],
                    )
                except (ValidationError, JSONDecodeError) as e:
                    if name != "parse" or i == len(attempts) - 1:
                        raise
                    logger.warning(
                        "%s failed for model %s: %s. " "Falling back to %s.",
                        name,
                        self.model_type,
                        e,
                        attempts[i + 1][0],
                    )

        return await self._arequest_chat_completion(messages, tools)

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        request_config = self._prepare_request_config(tools)

        return self._call_client(
            self._client.chat.completions.create,
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        request_config = self._prepare_request_config(tools)

        return await self._acall_client(
            self._async_client.chat.completions.create,
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
        r"""Request structured output via ``chat.completions.parse()``"""
        request_config = self._prepare_request_config(tools)
        request_config["response_format"] = response_format
        request_config.pop("stream", None)

        return self._call_client(
            self._client.chat.completions.parse,
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Async variant of :meth:`_request_parse`."""
        request_config = self._prepare_request_config(tools)
        request_config["response_format"] = response_format
        request_config.pop("stream", None)

        return await self._acall_client(
            self._async_client.chat.completions.parse,
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    def _request_json_schema(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Request structured output via ``chat.completions.create()`` with a
        ``json_schema`` response_format dict.
        """
        request_config = self._prepare_request_config(tools)
        request_config["response_format"] = (
            pydantic_to_json_schema_response_format(response_format)
        )

        return self._call_client(
            self._client.chat.completions.create,
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_json_schema(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Async variant of :meth:`_request_json_schema`."""
        request_config = self._prepare_request_config(tools)
        request_config["response_format"] = (
            pydantic_to_json_schema_response_format(response_format)
        )

        return await self._acall_client(
            self._async_client.chat.completions.create,
            messages=messages,
            model=self.model_type,
            **request_config,
        )

    def _request_json_object(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Inject the schema into the prompt, then call
        ``chat.completions.create()`` with ``{"type": "json_object"}``.
        """
        request_config = self._prepare_request_config(tools)
        request_messages = with_response_format_system_message(
            messages, response_format
        )
        request_config["response_format"] = {"type": "json_object"}

        return self._call_client(
            self._client.chat.completions.create,
            messages=request_messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_json_object(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Async variant of :meth:`_request_json_object`."""
        request_config = self._prepare_request_config(tools)
        request_messages = with_response_format_system_message(
            messages, response_format
        )
        request_config["response_format"] = {"type": "json_object"}

        return await self._acall_client(
            self._async_client.chat.completions.create,
            messages=request_messages,
            model=self.model_type,
            **request_config,
        )

    def _request_prompt_only(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
        inject_schema: bool = True,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Call ``chat.completions.create()`` without ``response_format``.

        Args:
            inject_schema: If ``True`` (default), merge the JSON schema
                instruction into a request-scoped system message.
        """
        request_config = self._prepare_request_config(tools)
        request_messages = messages

        if inject_schema:
            request_messages = with_response_format_system_message(
                messages, response_format
            )

        return self._call_client(
            self._client.chat.completions.create,
            messages=request_messages,
            model=self.model_type,
            **request_config,
        )

    async def _arequest_prompt_only(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
        inject_schema: bool = True,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Async variant of :meth:`_request_prompt_only`."""
        request_config = self._prepare_request_config(tools)
        request_messages = messages

        if inject_schema:
            request_messages = with_response_format_system_message(
                messages, response_format
            )

        return await self._acall_client(
            self._async_client.chat.completions.create,
            messages=request_messages,
            model=self.model_type,
            **request_config,
        )

    def _request_stream_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletionStreamManager[BaseModel]:
        r"""Request streaming structured output parsing.

        Note: This uses OpenAI's streaming API for structured outputs.
        """
        request_config = self._prepare_request_config(tools)
        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        # Use the beta streaming API for structured outputs
        return self._call_client(
            self._client.beta.chat.completions.stream,
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

        Note: This uses OpenAI's streaming API for structured outputs.
        """
        request_config = self._prepare_request_config(tools)
        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        # Use the beta streaming API for structured outputs
        return await self._acall_client(
            self._async_client.beta.chat.completions.stream,
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
