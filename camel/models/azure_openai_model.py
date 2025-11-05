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
import copy
import os
import warnings
from typing import Any, Callable, Dict, List, Optional, Type, Union

from openai import AsyncAzureOpenAI, AsyncStream, AzureOpenAI, Stream
from openai.lib.streaming.chat import (
    AsyncChatCompletionStreamManager,
    ChatCompletionStreamManager,
)
from pydantic import BaseModel

from camel.configs import ChatGPTConfig
from camel.messages import OpenAIMessage
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

AzureADTokenProvider = Callable[[], str]


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


class AzureOpenAIModel(BaseModelBackend):
    r"""Azure OpenAI API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, Should be the deployment name you chose when you deployed
            an azure model.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`ChatGPTConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the OpenAI service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the OpenAI service.
            (default: :obj:`None`)
        api_version (Optional[str], optional): The api version for the model.
            (default: :obj:`None`)
        azure_ad_token (Optional[str], optional): Your Azure Active Directory
            token, https://www.microsoft.com/en-us/security/business/
            identity-access/microsoft-entra-id. (default: :obj:`None`)
        azure_ad_token_provider (Optional[AzureADTokenProvider], optional): A
            function that returns an Azure Active Directory token, will be
            invoked on every request. (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`OpenAITokenCounter`
            will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        client (Optional[Any], optional): A custom synchronous AzureOpenAI
            client instance. If provided, this client will be used instead of
            creating a new one. Useful for RL frameworks like AReaL or rLLM
            that provide Azure OpenAI-compatible clients. The client should
            implement the AzureOpenAI client interface with
            `.chat.completions.create()` and `.beta.chat.completions.parse()`
            methods. (default: :obj:`None`)
        async_client (Optional[Any], optional): A custom asynchronous
            AzureOpenAI client instance. If provided, this client will be
            used instead of creating a new one. The client should implement
            the AsyncAzureOpenAI client interface. (default: :obj:`None`)
        azure_deployment_name (Optional[str], optional): **Deprecated**.
            Use `model_type` parameter instead. This parameter is kept for
            backward compatibility and will be removed in a future version.
            (default: :obj:`None`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization. Ignored if custom clients are provided.

    References:
        https://learn.microsoft.com/en-us/azure/ai-services/openai/
    """

    def __init__(
        self,
        model_type: Union[ModelType, str],
        model_config_dict: Optional[Dict[str, Any]] = None,
        api_key: Optional[str] = None,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        token_counter: Optional[BaseTokenCounter] = None,
        api_version: Optional[str] = None,
        azure_ad_token_provider: Optional["AzureADTokenProvider"] = None,
        azure_ad_token: Optional[str] = None,
        max_retries: int = 3,
        client: Optional[Any] = None,
        async_client: Optional[Any] = None,
        azure_deployment_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        # Handle deprecated azure_deployment_name parameter
        if azure_deployment_name is not None:
            warnings.warn(
                "The 'azure_deployment_name' parameter is deprecated. "
                "Please use 'model_type' parameter instead. "
                "The 'azure_deployment_name' parameter is being ignored.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Handle deprecated AZURE_DEPLOYMENT_NAME environment variable
        if os.environ.get("AZURE_DEPLOYMENT_NAME") is not None:
            warnings.warn(
                "The 'AZURE_DEPLOYMENT_NAME' environment variable is "
                "deprecated. Please use the 'model_type' parameter "
                "instead. The 'AZURE_DEPLOYMENT_NAME' environment "
                "variable is being ignored.",
                DeprecationWarning,
                stacklevel=2,
            )

        if model_config_dict is None:
            model_config_dict = ChatGPTConfig().as_dict()
        api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        url = url or os.environ.get("AZURE_OPENAI_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))
        super().__init__(
            model_type, model_config_dict, api_key, url, token_counter, timeout
        )

        self.api_version = api_version or os.environ.get("AZURE_API_VERSION")
        self._azure_ad_token = azure_ad_token or os.environ.get(
            "AZURE_AD_TOKEN"
        )
        self.azure_ad_token_provider = azure_ad_token_provider
        if self.api_version is None:
            raise ValueError(
                "Must provide either the `api_version` argument "
                "or `AZURE_API_VERSION` environment variable."
            )

        # Use custom clients if provided, otherwise create new ones
        if client is not None:
            # Use the provided custom sync client
            self._client = client
        else:
            # Create default sync client
            if is_langfuse_available():
                from langfuse.openai import AzureOpenAI as LangfuseOpenAI

                self._client = LangfuseOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )
            else:
                self._client = AzureOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )

        if async_client is not None:
            # Use the provided custom async client
            self._async_client = async_client
        else:
            # Create default async client
            if is_langfuse_available():
                from langfuse.openai import (
                    AsyncAzureOpenAI as LangfuseAsyncOpenAI,
                )

                self._async_client = LangfuseAsyncOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )
            else:
                self._async_client = AsyncAzureOpenAI(
                    azure_endpoint=str(self._url),
                    azure_deployment=str(self.model_type),
                    api_version=self.api_version,
                    api_key=self._api_key,
                    azure_ad_token=self._azure_ad_token,
                    azure_ad_token_provider=self.azure_ad_token_provider,
                    timeout=self._timeout,
                    max_retries=max_retries,
                    **kwargs,
                )

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
        r"""Runs inference of Azure OpenAI chat completion.

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
        is_streaming = self.model_config_dict.get("stream", False)
        if response_format:
            if is_streaming:
                return self._request_stream_parse(
                    messages, response_format, tools
                )
            else:
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
        r"""Runs inference of Azure OpenAI chat completion.

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
                `ChatCompletion` in the non-stream mode, or
                `AsyncStream[ChatCompletionChunk]` in the stream mode.
                `AsyncChatCompletionStreamManager[BaseModel]` for
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
        is_streaming = self.model_config_dict.get("stream", False)
        if response_format:
            if is_streaming:
                return await self._arequest_stream_parse(
                    messages, response_format, tools
                )
            else:
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
            model=str(self.model_type),
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
            model=str(self.model_type),
            **request_config,
        )

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        request_config = copy.deepcopy(self.model_config_dict)

        request_config["response_format"] = response_format
        # Remove stream from request config since OpenAI does not support it
        # with structured response
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        return self._client.beta.chat.completions.parse(
            messages=messages,
            model=str(self.model_type),
            **request_config,
        )

    async def _arequest_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        request_config = copy.deepcopy(self.model_config_dict)

        request_config["response_format"] = response_format
        # Remove stream from request config since OpenAI does not support it
        # with structured response
        request_config.pop("stream", None)
        if tools is not None:
            request_config["tools"] = tools

        return await self._async_client.beta.chat.completions.parse(
            messages=messages,
            model=str(self.model_type),
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

        request_config = copy.deepcopy(self.model_config_dict)

        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        if tools is not None:
            request_config["tools"] = tools

        # Use the beta streaming API for structured outputs
        return self._client.beta.chat.completions.stream(
            messages=messages,
            model=str(self.model_type),
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

        request_config = copy.deepcopy(self.model_config_dict)

        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        if tools is not None:
            request_config["tools"] = tools

        # Use the beta streaming API for structured outputs
        return self._async_client.beta.chat.completions.stream(
            messages=messages,
            model=str(self.model_type),
            response_format=response_format,
            **request_config,
        )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
        which sends partial results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)
