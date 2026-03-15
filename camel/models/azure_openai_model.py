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
import copy
import json
import os
import warnings
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    List,
    Literal,
    Optional,
    Type,
    Union,
    cast,
)

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
        api_mode (Literal["chat_completions", "responses"], optional):
            Azure OpenAI API mode to use. Supported values:
            `"chat_completions"` (default) and `"responses"`. The
            `"responses"` mode uses the Azure OpenAI Responses API, which
            supports stateful response chaining via
            `previous_response_id`. (default: :obj:`"chat_completions"`)
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
        api_mode: Literal["chat_completions", "responses"] = (
            "chat_completions"
        ),
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

        if api_mode not in {"chat_completions", "responses"}:
            raise ValueError(
                "api_mode must be 'chat_completions' or 'responses', "
                f"got: {api_mode}"
            )
        self._api_mode = api_mode
        self._responses_previous_response_id_by_session: Dict[str, str] = {}
        self._responses_last_message_count_by_session: Dict[str, int] = {}

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
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )
        is_streaming = self.model_config_dict.get("stream", False)
        if response_format:
            if is_streaming:
                if self._api_mode == "responses":
                    return cast(
                        Stream[ChatCompletionChunk],
                        self._request_responses_stream(
                            messages, response_format, tools
                        ),
                    )
                return self._request_stream_parse(
                    messages, response_format, tools
                )
            else:
                if self._api_mode == "responses":
                    return self._request_responses(
                        messages, response_format, tools
                    )
                return self._request_parse(messages, response_format, tools)
        else:
            result: Union[ChatCompletion, Stream[ChatCompletionChunk]]
            if self._api_mode == "responses":
                if is_streaming:
                    result = cast(
                        Stream[ChatCompletionChunk],
                        self._request_responses_stream(messages, None, tools),
                    )
                else:
                    result = self._request_responses(messages, None, tools)
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
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )
        is_streaming = self.model_config_dict.get("stream", False)
        if response_format:
            if is_streaming:
                if self._api_mode == "responses":
                    return cast(
                        AsyncStream[ChatCompletionChunk],
                        await self._arequest_responses_stream(
                            messages, response_format, tools
                        ),
                    )
                return await self._arequest_stream_parse(
                    messages, response_format, tools
                )
            else:
                if self._api_mode == "responses":
                    return await self._arequest_responses(
                        messages, response_format, tools
                    )
                return await self._arequest_parse(
                    messages, response_format, tools
                )
        else:
            async_result: Union[
                ChatCompletion,
                AsyncStream[ChatCompletionChunk],
            ]
            if self._api_mode == "responses":
                if is_streaming:
                    async_result = cast(
                        AsyncStream[ChatCompletionChunk],
                        await self._arequest_responses_stream(
                            messages, None, tools
                        ),
                    )
                else:
                    async_result = await self._arequest_responses(
                        messages, None, tools
                    )
            else:
                async_result = await self._arequest_chat_completion(
                    messages, tools
                )

        return async_result

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        request_config = self._prepare_request_config(tools)

        return self._call_client(
            self._client.chat.completions.create,
            messages=messages,
            model=str(self.model_type),
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
            model=str(self.model_type),
            **request_config,
        )

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        request_config = self._prepare_request_config(tools)
        request_config["response_format"] = response_format
        # Remove stream from request config since OpenAI does not support it
        # with structured response
        request_config.pop("stream", None)

        return self._call_client(
            self._client.beta.chat.completions.parse,
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
        request_config = self._prepare_request_config(tools)
        request_config["response_format"] = response_format
        # Remove stream from request config since OpenAI does not support it
        # with structured response
        request_config.pop("stream", None)

        return await self._acall_client(
            self._async_client.beta.chat.completions.parse,
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
        request_config = self._prepare_request_config(tools)
        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        # Use the beta streaming API for structured outputs
        return self._call_client(
            self._client.beta.chat.completions.stream,
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
        request_config = self._prepare_request_config(tools)
        # Remove stream from config as it's handled by the stream method
        request_config.pop("stream", None)

        # Use the beta streaming API for structured outputs
        return self._call_client(
            self._async_client.beta.chat.completions.stream,
            messages=messages,
            model=str(self.model_type),
            response_format=response_format,
            **request_config,
        )

    def _prepare_responses_request_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Type[BaseModel]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        r"""Prepare request configuration for the Azure Responses API.

        Translates chat-completions style parameters to Responses API
        style and adds structured-output schema.

        Args:
            tools (Optional[List[Dict[str, Any]]]): Tool schemas to include.
                (default: :obj:`None`)
            response_format (Optional[Type[BaseModel]]): Pydantic model for
                structured output. (default: :obj:`None`)
            stream (bool): Whether to enable streaming.
                (default: :obj:`False`)

        Returns:
            Dict[str, Any]: Request configuration for the Responses API.
        """
        request_config = self._prepare_request_config(tools)

        max_tokens = request_config.pop("max_tokens", None)
        if (
            max_tokens is not None
            and "max_output_tokens" not in request_config
        ):
            request_config["max_output_tokens"] = max_tokens

        if request_config.get("n") not in (None, 1):
            warnings.warn(
                "Azure OpenAI Responses API does not support `n`; "
                "ignoring configured value.",
                UserWarning,
            )
        request_config.pop("n", None)

        request_config.pop("response_format", None)
        request_config.pop("stream_options", None)
        request_config["stream"] = stream
        if "store" not in request_config:
            request_config["store"] = True
        elif request_config.get("store") is False:
            warnings.warn(
                "Setting `store=False` will disable "
                "`previous_response_id` chaining.",
                UserWarning,
            )

        if request_config.get("tools"):
            request_config["tools"] = self._normalize_tools_for_responses_api(
                request_config["tools"]
            )

        if response_format is not None:
            schema = copy.deepcopy(response_format.model_json_schema())
            self._enforce_object_additional_properties_false(schema)
            request_config["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": response_format.__name__,
                    "schema": schema,
                }
            }

        return request_config

    @staticmethod
    def _normalize_tools_for_responses_api(
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        r"""Convert chat-completions style function tools to Responses style.

        Input:
            {"type":"function","function":{"name":"foo",...}}
        Output:
            {"type":"function","name":"foo",...}
        """
        normalized_tools: List[Dict[str, Any]] = []
        for tool in tools:
            if (
                isinstance(tool, dict)
                and tool.get("type") == "function"
                and isinstance(tool.get("function"), dict)
            ):
                normalized_tools.append(
                    {"type": "function", **tool["function"]}
                )
            else:
                normalized_tools.append(tool)
        return normalized_tools

    @staticmethod
    def _enforce_object_additional_properties_false(schema: Any) -> None:
        r"""Recursively enforce strict object schema for Responses API."""
        if isinstance(schema, dict):
            if (
                schema.get("type") == "object"
                and "additionalProperties" not in schema
            ):
                schema["additionalProperties"] = False

            for value in schema.values():
                AzureOpenAIModel._enforce_object_additional_properties_false(
                    value
                )
        elif isinstance(schema, list):
            for item in schema:
                AzureOpenAIModel._enforce_object_additional_properties_false(
                    item
                )

    def _get_response_chain_session_key(self) -> str:
        return get_current_agent_session_id() or "__default__"

    def _clear_response_chain_state(self, session_key: str) -> None:
        self._responses_previous_response_id_by_session.pop(session_key, None)
        self._responses_last_message_count_by_session.pop(session_key, None)

    @staticmethod
    def _responses_chain_enabled(request_config: Dict[str, Any]) -> bool:
        return request_config.get("store") is not False

    def _prepare_responses_input_and_chain(
        self,
        messages: List[OpenAIMessage],
        chain_enabled: bool = True,
    ) -> Dict[str, Any]:
        r"""Prepare input items and response-chain state for the Responses API.

        Args:
            messages (List[OpenAIMessage]): Full message history.
            chain_enabled (bool): Whether to use response chaining via
                `previous_response_id`. (default: :obj:`True`)

        Returns:
            Dict[str, Any]: Dict with keys ``session_key``,
                ``previous_response_id``, ``input_messages``, and
                ``message_count``.
        """
        session_key = self._get_response_chain_session_key()
        if chain_enabled:
            previous_response_id = (
                self._responses_previous_response_id_by_session.get(
                    session_key
                )
            )
            last_message_count = (
                self._responses_last_message_count_by_session.get(
                    session_key, 0
                )
            )
        else:
            self._clear_response_chain_state(session_key)
            previous_response_id = None
            last_message_count = 0

        if len(messages) < last_message_count:
            previous_response_id = None
            last_message_count = 0
            self._clear_response_chain_state(session_key)

        if previous_response_id and last_message_count > 0:
            delta_messages = messages[last_message_count:]
            input_messages = (
                delta_messages if delta_messages else [messages[-1]]
            )
        else:
            input_messages = messages

        input_items = self._convert_messages_to_responses_input(input_messages)

        return {
            "session_key": session_key,
            "previous_response_id": previous_response_id,
            "input_messages": input_items,
            "message_count": len(messages),
        }

    @staticmethod
    def _convert_messages_to_responses_input(
        messages: List[OpenAIMessage],
    ) -> List[Dict[str, Any]]:
        r"""Convert chat-completions style messages to Responses input items.

        Rewrites tool-calling history so it is understood by the Responses API:

        - An assistant message with ``tool_calls`` becomes one or more
          ``function_call`` items (plus an optional assistant message when
          ``content`` is non-empty).
        - A tool message becomes a ``function_call_output`` item.

        Args:
            messages (List[OpenAIMessage]): Messages in OpenAI
                chat-completions format.

        Returns:
            List[Dict[str, Any]]: Input items for the Responses API.
        """
        input_items: List[Dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")

            if role == "tool":
                input_items.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.get("tool_call_id", "null"),
                        "output": content
                        if isinstance(content, str)
                        else str(content),
                    }
                )
                continue

            if role == "assistant" and message.get("tool_calls"):
                if content not in (None, "", []):
                    input_items.append(
                        {
                            "role": "assistant",
                            "content": content,
                        }
                    )

                tool_calls = message.get("tool_calls", [])
                if not isinstance(tool_calls, list):
                    tool_calls = [tool_calls]
                for tool_call in tool_calls:
                    function_data = (
                        tool_call.get("function", {})
                        if isinstance(tool_call, dict)
                        else {}
                    )
                    if not isinstance(function_data, dict):
                        continue
                    arguments = function_data.get("arguments", "{}")
                    if not isinstance(arguments, str):
                        arguments = json.dumps(arguments, ensure_ascii=False)
                    input_items.append(
                        {
                            "type": "function_call",
                            "call_id": (
                                tool_call.get("id", "null")
                                if isinstance(tool_call, dict)
                                else "null"
                            ),
                            "name": function_data.get("name", ""),
                            "arguments": arguments,
                        }
                    )
                continue

            input_items.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return input_items

    def _save_response_chain_state(
        self,
        session_key: str,
        response_id: Optional[str],
        message_count: int,
    ) -> None:
        if response_id:
            self._responses_previous_response_id_by_session[session_key] = (
                response_id
            )
        self._responses_last_message_count_by_session[session_key] = (
            message_count
        )

    def _request_responses(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Call the Azure OpenAI Responses API (non-streaming).

        Args:
            messages (List[OpenAIMessage]): Message history.
            response_format (Optional[Type[BaseModel]]): Pydantic model for
                structured output. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]]): Tool schemas.
                (default: :obj:`None`)

        Returns:
            ChatCompletion: The model response in chat-completions format.
        """
        from camel.models.openai_responses_adapter import (
            response_to_chat_completion,
        )

        request_config = self._prepare_responses_request_config(
            tools=tools, response_format=response_format, stream=False
        )
        chain_enabled = self._responses_chain_enabled(request_config)
        chain_state = self._prepare_responses_input_and_chain(
            messages, chain_enabled=chain_enabled
        )
        if chain_enabled and chain_state["previous_response_id"]:
            request_config["previous_response_id"] = chain_state[
                "previous_response_id"
            ]
        response = self._client.responses.create(
            input=chain_state["input_messages"],
            model=str(self.model_type),
            **request_config,
        )
        if chain_enabled:
            self._save_response_chain_state(
                session_key=chain_state["session_key"],
                response_id=getattr(response, "id", None)
                if not isinstance(response, dict)
                else response.get("id"),
                message_count=chain_state["message_count"],
            )
        return response_to_chat_completion(
            response=response,
            model=str(self.model_type),
            response_format=response_format,
        )

    async def _arequest_responses(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        r"""Call the Azure OpenAI Responses API asynchronously (non-streaming).

        Args:
            messages (List[OpenAIMessage]): Message history.
            response_format (Optional[Type[BaseModel]]): Pydantic model for
                structured output. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]]): Tool schemas.
                (default: :obj:`None`)

        Returns:
            ChatCompletion: The model response in chat-completions format.
        """
        from camel.models.openai_responses_adapter import (
            response_to_chat_completion,
        )

        request_config = self._prepare_responses_request_config(
            tools=tools, response_format=response_format, stream=False
        )
        chain_enabled = self._responses_chain_enabled(request_config)
        chain_state = self._prepare_responses_input_and_chain(
            messages, chain_enabled=chain_enabled
        )
        if chain_enabled and chain_state["previous_response_id"]:
            request_config["previous_response_id"] = chain_state[
                "previous_response_id"
            ]
        response = await self._async_client.responses.create(
            input=chain_state["input_messages"],
            model=str(self.model_type),
            **request_config,
        )
        if chain_enabled:
            self._save_response_chain_state(
                session_key=chain_state["session_key"],
                response_id=getattr(response, "id", None)
                if not isinstance(response, dict)
                else response.get("id"),
                message_count=chain_state["message_count"],
            )
        return response_to_chat_completion(
            response=response,
            model=str(self.model_type),
            response_format=response_format,
        )

    def _request_responses_stream(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Generator[ChatCompletionChunk, None, None]:
        r"""Call the Azure OpenAI Responses API with streaming.

        Args:
            messages (List[OpenAIMessage]): Message history.
            response_format (Optional[Type[BaseModel]]): Pydantic model for
                structured output. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]]): Tool schemas.
                (default: :obj:`None`)

        Yields:
            ChatCompletionChunk: Streaming response chunks.
        """
        from camel.models.openai_responses_adapter import (
            iter_response_events_to_chat_chunks,
        )

        request_config = self._prepare_responses_request_config(
            tools=tools, response_format=response_format, stream=True
        )
        chain_enabled = self._responses_chain_enabled(request_config)
        chain_state = self._prepare_responses_input_and_chain(
            messages, chain_enabled=chain_enabled
        )
        if chain_enabled and chain_state["previous_response_id"]:
            request_config["previous_response_id"] = chain_state[
                "previous_response_id"
            ]
        event_stream = self._client.responses.create(
            input=chain_state["input_messages"],
            model=str(self.model_type),
            **request_config,
        )

        def _on_response_completed(response_id: str) -> None:
            if chain_enabled:
                self._save_response_chain_state(
                    session_key=chain_state["session_key"],
                    response_id=response_id,
                    message_count=chain_state["message_count"],
                )

        return iter_response_events_to_chat_chunks(
            event_stream=event_stream,
            model=str(self.model_type),
            on_response_completed=_on_response_completed,
        )

    async def _arequest_responses_stream(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        r"""Call the Azure OpenAI Responses API asynchronously with streaming.

        Args:
            messages (List[OpenAIMessage]): Message history.
            response_format (Optional[Type[BaseModel]]): Pydantic model for
                structured output. (default: :obj:`None`)
            tools (Optional[List[Dict[str, Any]]]): Tool schemas.
                (default: :obj:`None`)

        Returns:
            AsyncGenerator[ChatCompletionChunk, None]: Async generator of
                streaming response chunks.
        """
        from camel.models.openai_responses_adapter import (
            aiter_response_events_to_chat_chunks,
        )

        request_config = self._prepare_responses_request_config(
            tools=tools, response_format=response_format, stream=True
        )
        chain_enabled = self._responses_chain_enabled(request_config)
        chain_state = self._prepare_responses_input_and_chain(
            messages, chain_enabled=chain_enabled
        )
        if chain_enabled and chain_state["previous_response_id"]:
            request_config["previous_response_id"] = chain_state[
                "previous_response_id"
            ]
        event_stream = await self._async_client.responses.create(
            input=chain_state["input_messages"],
            model=str(self.model_type),
            **request_config,
        )

        def _on_response_completed(response_id: str) -> None:
            if chain_enabled:
                self._save_response_chain_state(
                    session_key=chain_state["session_key"],
                    response_id=response_id,
                    message_count=chain_state["message_count"],
                )

        return aiter_response_events_to_chat_chunks(
            event_stream=event_stream,
            model=str(self.model_type),
            on_response_completed=_on_response_completed,
        )

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode,
        which sends partial results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)
