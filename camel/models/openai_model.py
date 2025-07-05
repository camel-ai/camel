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
import warnings
from typing import Any, Dict, List, Optional, Type, Union

from openai import AsyncOpenAI, AsyncStream, OpenAI, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from pydantic import BaseModel

from camel.configs import OPENAI_API_PARAMS, ChatGPTConfig
from camel.messages import OpenAIMessage
from camel.models import BaseModelBackend
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    OpenAITokenCounter,
    api_keys_required,
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


UNSUPPORTED_PARAMS = {
    "temperature",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "logprobs",
    "top_logprobs",
    "logit_bias",
}


class OpenAIModel(BaseModelBackend):
    r"""OpenAI API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of GPT_* series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating
            with the OpenAI service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the OpenAI service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter` will
            be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        **kwargs (Any): Additional arguments to pass to the
            OpenAI client initialization. These can include parameters like
            'organization', 'default_headers', 'http_client', etc.
    """

    @api_keys_required(
        [
            ("api_key", "OPENAI_API_KEY"),
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
            model_config_dict = ChatGPTConfig().as_dict()
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        url = url or os.environ.get("OPENAI_API_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))

        # Store additional client args for later use
        self._max_retries = max_retries

        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter, timeout
        )

        if is_langfuse_available():
            from langfuse.openai import AsyncOpenAI as LangfuseAsyncOpenAI
            from langfuse.openai import OpenAI as LangfuseOpenAI

            # Create Langfuse client with base parameters and additional
            # arguments
            self._client = LangfuseOpenAI(
                timeout=self._timeout,
                max_retries=self._max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )
            self._async_client = LangfuseAsyncOpenAI(
                timeout=self._timeout,
                max_retries=self._max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )
        else:
            # Create client with base parameters and additional arguments
            self._client = OpenAI(
                timeout=self._timeout,
                max_retries=self._max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )
            self._async_client = AsyncOpenAI(
                timeout=self._timeout,
                max_retries=self._max_retries,
                base_url=self._url,
                api_key=self._api_key,
                **kwargs,
            )

    def _sanitize_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        r"""Sanitize the model configuration for O1 models."""

        if self.model_type in [
            ModelType.O1,
            ModelType.O1_MINI,
            ModelType.O1_PREVIEW,
            ModelType.O3_MINI,
            ModelType.O3,
            ModelType.O4_MINI,
            ModelType.O3_PRO,
        ]:
            warnings.warn(
                "Warning: You are using an reasoning model (O series), "
                "which has certain limitations, reference: "
                "`https://platform.openai.com/docs/guides/reasoning`.",
                UserWarning,
            )
            return {
                k: v
                for k, v in config_dict.items()
                if k not in UNSUPPORTED_PARAMS
            }
        return config_dict

    def _adapt_messages_for_o1_models(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        r"""Adjust message roles to comply with O1 model requirements by
        converting 'system' or 'developer' to 'user' role.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.

        Returns:
            processed_messages (List[OpenAIMessage]): Return a new list of
                messages to avoid mutating input.
        """

        # Define supported O1 model types as a class constant would be better
        O1_MODEL_TYPES = {ModelType.O1_MINI, ModelType.O1_PREVIEW}

        if self.model_type not in O1_MODEL_TYPES:
            return messages.copy()

        # Issue warning only once using class state
        if not hasattr(self, "_o1_warning_issued"):
            warnings.warn(
                "O1 models (O1_MINI/O1_PREVIEW) have role limitations: "
                "System or Developer messages will be converted to user role."
                "Reference: https://community.openai.com/t/"
                "developer-role-not-accepted-for-o1-o1-mini-o3-mini/1110750/7",
                UserWarning,
                stacklevel=2,
            )
            self._o1_warning_issued = True

        # Create new message list to avoid mutating input
        processed_messages = []
        for message in messages:
            processed_message = message.copy()
            if (
                processed_message["role"] == "system"
                or processed_message["role"] == "developer"
            ):
                processed_message["role"] = "user"  # type: ignore[arg-type]
            processed_messages.append(processed_message)

        return processed_messages

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
                `ChatCompletion` in the non-stream mode,
                `Stream[ChatCompletionChunk]`in the stream mode,
                or `ChatCompletionStreamManager[BaseModel]` for
                structured output streaming.
        """

        # Update Langfuse trace with current agent session and metadata
        agent_session_id = get_current_agent_session_id()
        if agent_session_id:
            update_langfuse_trace(
                session_id=agent_session_id,
                metadata={
                    "source": "camel",
                    "agent_id": agent_session_id,
                    "agent_type": "camel_chat_agent",
                    "model_type": str(self.model_type),
                },
                tags=["CAMEL-AI", str(self.model_type)],
            )

        messages = self._adapt_messages_for_o1_models(messages)
        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        # Check if streaming is enabled
        is_streaming = self.model_config_dict.get("stream", False)

        if response_format:
            result: Union[ChatCompletion, Stream[ChatCompletionChunk]] = (
                self._request_parse(messages, response_format, tools)
            )
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
                `AsyncStream[ChatCompletionChunk]` in the stream mode, or
                `AsyncChatCompletionStreamManager[BaseModel]` for
                structured output streaming.
        """

        # Update Langfuse trace with current agent session and metadata
        agent_session_id = get_current_agent_session_id()
        if agent_session_id:
            update_langfuse_trace(
                session_id=agent_session_id,
                metadata={
                    "source": "camel",
                    "agent_id": agent_session_id,
                    "agent_type": "camel_chat_agent",
                    "model_type": str(self.model_type),
                },
                tags=["CAMEL-AI", str(self.model_type)],
            )

        messages = self._adapt_messages_for_o1_models(messages)
        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )

        # Check if streaming is enabled
        is_streaming = self.model_config_dict.get("stream", False)

        if response_format:
            result: Union[
                ChatCompletion, AsyncStream[ChatCompletionChunk]
            ] = await self._arequest_parse(messages, response_format, tools)
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
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        if tools:
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

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
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        if tools:
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

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

        request_config["response_format"] = response_format
        # Remove stream from request config since OpenAI does not support it
        # with structured response
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

        return self._client.beta.chat.completions.parse(
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
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        request_config["response_format"] = response_format
        # Remove stream from request config since OpenAI does not support it
        # with structured response
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

        return await self._async_client.beta.chat.completions.parse(
            messages=messages,
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

        Note: This uses OpenAI's beta streaming API for structured outputs.
        """
        import copy

        request_config = copy.deepcopy(self.model_config_dict)

        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        if tools is not None:
            request_config["tools"] = tools

        request_config = self._sanitize_config(request_config)

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

        request_config = self._sanitize_config(request_config)

        # Use the beta streaming API for structured outputs
        return self._async_client.beta.chat.completions.stream(
            messages=messages,
            model=self.model_type,
            response_format=response_format,
            **request_config,
        )

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
