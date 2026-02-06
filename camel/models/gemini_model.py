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
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    Union,
    cast,
)

from openai import AsyncStream, Stream

if TYPE_CHECKING:
    from google.genai.client import Client as GenaiClient
    from google.genai.types import CachedContent
from pydantic import BaseModel

from camel.configs import GeminiConfig
from camel.logger import get_logger
from camel.messages import OpenAIMessage
from camel.models.openai_compatible_model import OpenAICompatibleModel
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelType,
)
from camel.utils import (
    BaseTokenCounter,
    api_keys_required,
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


class GeminiModel(OpenAICompatibleModel):
    r"""Gemini API in a unified OpenAICompatibleModel interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of Gemini series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into:obj:`openai.ChatCompletion.create()`. If
            :obj:`None`, :obj:`GeminiConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Gemini service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Gemini service.
            (default: :obj:`https://generativelanguage.googleapis.com/v1beta/
            openai/`)
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
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required(
        [
            ("api_key", 'GEMINI_API_KEY'),
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
            model_config_dict = GeminiConfig().as_dict()

        # Extract cache parameters before passing to parent
        self._cache_control = model_config_dict.pop("cache_control", None)
        self._cached_content = model_config_dict.pop("cached_content", None)

        api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._api_key = api_key
        url = url or os.environ.get(
            "GEMINI_API_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
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

        # Lazy-initialized native client for cache operations
        self._native_client: Optional["GenaiClient"] = None

    @property
    def native_client(self) -> "GenaiClient":
        r"""Get the native google-genai client for cache operations.

        Returns:
            genai.Client: The native Google GenAI client.
        """
        if self._native_client is None:
            from google import genai

            self._native_client = genai.Client(api_key=self._api_key)
        return self._native_client

    def create_cache(
        self,
        contents: List[Dict[str, Any]],
        ttl: str = "300s",
        display_name: Optional[str] = None,
        system_instruction: Optional[str] = None,
    ) -> str:
        r"""Create a cache for reusing content across requests.

        Args:
            contents (List[Dict[str, Any]]): The content to cache. Should be a
                list of message dicts with 'role' and 'parts' keys.
            ttl (str, optional): Time-to-live for the cache. Format: "300s"
                (5 minutes), "3600s" (1 hour), etc. (default: :obj:`"300s"`)
            display_name (str, optional): A human-readable name for the cache.
                (default: :obj:`None`)
            system_instruction (str, optional): System instruction to cache.
                (default: :obj:`None`)

        Returns:
            str: The cache name in format "cachedContents/{cache_id}".
        """
        from google.genai import types

        # Build model name - handle both ModelType enum and string
        model_name = (
            self.model_type.value
            if hasattr(self.model_type, 'value')
            else str(self.model_type)
        )
        # Ensure model name has proper prefix
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"

        config = types.CreateCachedContentConfig(
            contents=cast(Any, contents),
            ttl=ttl,
            display_name=display_name,
            system_instruction=system_instruction,
        )

        # google-genai expects contents inside config.
        cache = self.native_client.caches.create(
            model=model_name,
            config=config,
        )
        if not cache.name:
            raise RuntimeError("Gemini cache creation succeeded without name.")
        return cache.name

    def list_caches(self) -> List["CachedContent"]:
        r"""List all caches for the current API key.

        Returns:
            List[CachedContent]: A list of cached content objects.
        """
        return list(self.native_client.caches.list())

    def get_cache(self, cache_name: str) -> "CachedContent":
        r"""Get details of a specific cache.

        Args:
            cache_name (str): The cache name in format "cachedContents/{id}".

        Returns:
            CachedContent: The cached content object.
        """
        return self.native_client.caches.get(name=cache_name)

    def update_cache(self, cache_name: str, ttl: str) -> "CachedContent":
        r"""Update the TTL of an existing cache.

        Args:
            cache_name (str): The cache name in format "cachedContents/{id}".
            ttl (str): New time-to-live for the cache.

        Returns:
            CachedContent: The updated cached content object.
        """
        from google.genai import types

        config = types.UpdateCachedContentConfig(ttl=ttl)
        return self.native_client.caches.update(
            name=cache_name,
            config=config,
        )

    def delete_cache(self, cache_name: str) -> None:
        r"""Delete a cache.

        Args:
            cache_name (str): The cache name in format "cachedContents/{id}".
        """
        self.native_client.caches.delete(name=cache_name)

    @property
    def cached_content(self) -> Optional[str]:
        r"""Get the current cached content name.

        Returns:
            Optional[str]: The cache name or None if not set.
        """
        return self._cached_content

    @cached_content.setter
    def cached_content(self, value: Optional[str]) -> None:
        r"""Set or clear the cached content to use for requests.

        Args:
            value (Optional[str]): The cache name (e.g., "cachedContents/xxx")
                or None to clear.
        """
        self._cached_content = value

    @staticmethod
    def _sanitize_tools_for_gemini(
        tools: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        import copy

        sanitized_tools = copy.deepcopy(tools)

        # Remove strict and anyOf from each tool's function parameters since
        # Gemini does not support them.
        for tool in sanitized_tools:
            function_dict = tool.get('function', {})
            function_dict.pop("strict", None)

            if 'parameters' not in function_dict:
                continue
            params = function_dict['parameters']
            if 'properties' not in params:
                continue

            for prop_name, prop_value in params['properties'].items():
                if 'anyOf' in prop_value:
                    # Replace anyOf with the first type in the list.
                    first_type = prop_value['anyOf'][0]
                    params['properties'][prop_name] = first_type
                    # Preserve description if it exists.
                    if 'description' in prop_value:
                        params['properties'][prop_name]['description'] = (
                            prop_value['description']
                        )

                # Handle enum and format restrictions for Gemini API.
                if prop_value.get('type') != 'string':
                    prop_value.pop('enum', None)
                if prop_value.get('type') not in [
                    'string',
                    'integer',
                    'number',
                ]:
                    prop_value.pop('format', None)

        return sanitized_tools

    def _prepare_request_config(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        request_config = super()._prepare_request_config(
            self._sanitize_tools_for_gemini(tools) if tools else None
        )

        # Remove cache config params from base request payload.
        request_config.pop("cache_control", None)
        request_config.pop("cached_content", None)

        # OpenAI Python client's `extra_body` is merged into the request root.
        # Gemini expects extensions under the request's `extra_body` field, so
        # we wrap once more: extra_body={"extra_body": {...}}.
        raw_extra_body = request_config.get("extra_body")
        if isinstance(raw_extra_body, dict) and isinstance(
            raw_extra_body.get("extra_body"), dict
        ):
            gemini_extra_body = raw_extra_body["extra_body"]
        elif isinstance(raw_extra_body, dict):
            gemini_extra_body = raw_extra_body
        else:
            gemini_extra_body = {}

        if self._cached_content:
            google_body = gemini_extra_body.get("google")
            if not isinstance(google_body, dict):
                google_body = {}
            google_body["cached_content"] = self._cached_content
            gemini_extra_body["google"] = google_body

        if gemini_extra_body:
            request_config["extra_body"] = {"extra_body": gemini_extra_body}

        return request_config

    def _is_stale_cached_content_error(self, err: Exception) -> bool:
        if not self._cached_content:
            return False

        msg = str(err).lower()
        cache_markers = ("cached_content", "cached content", "cachedcontents")
        invalid_markers = (
            "not found",
            "not exist",
            "expired",
            "invalid",
            "no such",
            "unknown",
        )
        return any(k in msg for k in cache_markers) and any(
            k in msg for k in invalid_markers
        )

    def _process_messages(self, messages) -> List[OpenAIMessage]:
        r"""Process the messages for Gemini API to ensure no empty content,
        which is not accepted by Gemini. Also preserves thought signatures
        required for Gemini 3 Pro function calling.

        This method also merges consecutive assistant messages with single
        tool calls into a single assistant message with multiple tool calls,
        as required by Gemini's OpenAI-compatible API for parallel function
        calling.
        """
        import copy

        processed_messages: List[OpenAIMessage] = []
        i = 0
        n = len(messages)

        while i < n:
            msg = messages[i]

            # Check if this is an assistant message with a single tool_call
            # that might need to be merged with subsequent ones
            if (
                msg.get('role') == 'assistant'
                and 'tool_calls' in msg
                and isinstance(msg['tool_calls'], list)
                and len(msg['tool_calls']) == 1
            ):
                # Look ahead to check if there are more assistant messages
                # with single tool calls (interleaved with their tool results)
                j = i + 1
                has_more_tool_calls = False

                # Collect tool_call_ids we've seen so far
                first_tool_call_id = msg['tool_calls'][0].get('id')
                seen_tool_call_ids = (
                    {first_tool_call_id} if first_tool_call_id else set()
                )

                # Scan ahead to find pattern: tool_result, assistant,
                # tool_result, ...
                while j < n:
                    next_msg = messages[j]
                    next_role = next_msg.get('role')

                    if next_role == 'tool':
                        # Tool result - check if it belongs to our batch
                        if next_msg.get('tool_call_id') in seen_tool_call_ids:
                            j += 1
                            continue
                        else:
                            # Tool result for unknown call, stop scanning
                            break
                    elif (
                        next_role == 'assistant'
                        and 'tool_calls' in next_msg
                        and isinstance(next_msg['tool_calls'], list)
                        and len(next_msg['tool_calls']) == 1
                    ):
                        # Another single tool call - mark for merging
                        has_more_tool_calls = True
                        tc_id = next_msg['tool_calls'][0].get('id')
                        if tc_id:
                            seen_tool_call_ids.add(tc_id)
                        j += 1
                        continue
                    else:
                        # Something else, stop scanning
                        break

                if has_more_tool_calls:
                    # Need to merge: collect all tool calls and results
                    merged_tool_calls = []
                    tool_results = []
                    is_first = True

                    for k in range(i, j):
                        m = messages[k]
                        if m.get('role') == 'assistant' and 'tool_calls' in m:
                            tc = m['tool_calls'][0]
                            if is_first:
                                # Keep extra_content only on first tool call
                                merged_tool_calls.append(copy.deepcopy(tc))
                                is_first = False
                            else:
                                # Remove extra_content from subsequent tool
                                # calls
                                tc_copy = {
                                    k: v
                                    for k, v in tc.items()
                                    if k != 'extra_content'
                                }
                                merged_tool_calls.append(tc_copy)
                        elif m.get('role') == 'tool':
                            tool_results.append(copy.deepcopy(m))

                    # Build merged assistant message
                    merged_msg = copy.deepcopy(msg)
                    merged_msg['tool_calls'] = merged_tool_calls
                    if 'content' in merged_msg and merged_msg['content'] == '':
                        merged_msg['content'] = 'null'

                    processed_messages.append(merged_msg)
                    processed_messages.extend(tool_results)
                    i = j
                    continue

            # Regular message processing (no merging needed)
            msg_copy = copy.deepcopy(msg)
            if 'content' in msg_copy and msg_copy['content'] == '':
                msg_copy['content'] = 'null'
            processed_messages.append(msg_copy)
            i += 1

        return processed_messages

    def _preserve_thought_signatures(
        self,
        response: Union[
            ChatCompletion,
            Stream[ChatCompletionChunk],
            AsyncStream[ChatCompletionChunk],
        ],
    ) -> Union[
        ChatCompletion,
        Generator[ChatCompletionChunk, None, None],
        AsyncGenerator[ChatCompletionChunk, None],
    ]:
        r"""Preserve thought signatures from Gemini responses for future
        requests.

        According to the Gemini documentation, when a response contains tool
        calls with thought signatures, these signatures must be preserved
        exactly as received when the response is added to conversation history
        for subsequent requests.

        Args:
            response: The response from Gemini API

        Returns:
            The response with thought signatures properly preserved.
            For streaming responses, returns generators that preserve
            signatures.
        """
        # For streaming responses, we need to wrap the stream to preserve
        # thought signatures in tool calls as they come in
        if isinstance(response, Stream):
            return self._wrap_stream_with_thought_preservation(response)
        elif isinstance(response, AsyncStream):
            return self._wrap_async_stream_with_thought_preservation(response)

        # For non-streaming responses, thought signatures are already preserved
        # in _process_messages when the response becomes part of conversation
        # history
        return response

    def _wrap_stream_with_thought_preservation(
        self, stream: Stream[ChatCompletionChunk]
    ) -> Generator[ChatCompletionChunk, None, None]:
        r"""Wrap a streaming response to preserve thought signatures in tool
        calls.

        This method ensures that when Gemini streaming responses contain tool
        calls with thought signatures, these are properly preserved in the
        extra_content field for future conversation context.

        Args:
            stream: The original streaming response from Gemini

        Returns:
            A wrapped stream that preserves thought signatures
        """

        def thought_preserving_generator():
            accumulated_signatures = {}  # Store signatures by tool call index

            for chunk in stream:
                # Process chunk normally first
                processed_chunk = chunk

                # Check if this chunk contains tool call deltas with thought
                # signatures
                if (
                    hasattr(chunk, 'choices')
                    and chunk.choices
                    and hasattr(chunk.choices[0], 'delta')
                    and hasattr(chunk.choices[0].delta, 'tool_calls')
                ):
                    delta_tool_calls = chunk.choices[0].delta.tool_calls
                    if delta_tool_calls:
                        for tool_call_delta in delta_tool_calls:
                            index = tool_call_delta.index

                            # Check for thought signatures in the tool call
                            # response Gemini may include these in custom
                            # fields
                            if hasattr(tool_call_delta, 'extra_content'):
                                extra_content = tool_call_delta.extra_content
                                if (
                                    isinstance(extra_content, dict)
                                    and 'google' in extra_content
                                ):
                                    google_content = extra_content['google']
                                    if 'thought_signature' in google_content:
                                        # Store the thought signature for this
                                        # tool call
                                        accumulated_signatures[index] = (
                                            extra_content
                                        )

                            # Also check if thought signature is in function
                            # response
                            elif hasattr(
                                tool_call_delta, 'function'
                            ) and hasattr(
                                tool_call_delta.function, 'extra_content'
                            ):
                                func_extra = (
                                    tool_call_delta.function.extra_content
                                )
                                if (
                                    isinstance(func_extra, dict)
                                    and 'google' in func_extra
                                ):
                                    accumulated_signatures[index] = func_extra

                            # If we have accumulated signature for this tool
                            # call, ensure it's preserved in the chunk
                            if index in accumulated_signatures:
                                # Add extra_content to tool call delta if it
                                # doesn't exist
                                if not hasattr(
                                    tool_call_delta, 'extra_content'
                                ):
                                    tool_call_delta.extra_content = (
                                        accumulated_signatures[index]
                                    )
                                elif tool_call_delta.extra_content is None:
                                    tool_call_delta.extra_content = (
                                        accumulated_signatures[index]
                                    )

                yield processed_chunk

        return thought_preserving_generator()

    def _wrap_async_stream_with_thought_preservation(
        self, stream: AsyncStream[ChatCompletionChunk]
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        r"""Wrap an async streaming response to preserve thought signatures in
        tool calls.

        This method ensures that when Gemini async streaming responses contain
        tool calls with thought signatures, these are properly preserved in
        the extra_content field for future conversation context.

        Args:
            stream: The original async streaming response from Gemini

        Returns:
            A wrapped async stream that preserves thought signatures
        """

        async def async_thought_preserving_generator():
            accumulated_signatures = {}  # Store signatures by tool call index

            async for chunk in stream:
                # Process chunk normally first
                processed_chunk = chunk

                # Check if this chunk contains tool call deltas with thought
                # signatures
                if (
                    hasattr(chunk, 'choices')
                    and chunk.choices
                    and hasattr(chunk.choices[0], 'delta')
                    and hasattr(chunk.choices[0].delta, 'tool_calls')
                ):
                    delta_tool_calls = chunk.choices[0].delta.tool_calls
                    if delta_tool_calls:
                        for tool_call_delta in delta_tool_calls:
                            index = tool_call_delta.index

                            # Check for thought signatures in the tool call
                            # response
                            if hasattr(tool_call_delta, 'extra_content'):
                                extra_content = tool_call_delta.extra_content
                                if (
                                    isinstance(extra_content, dict)
                                    and 'google' in extra_content
                                ):
                                    google_content = extra_content['google']
                                    if 'thought_signature' in google_content:
                                        # Store the thought signature for this
                                        # tool call
                                        accumulated_signatures[index] = (
                                            extra_content
                                        )

                            # Also check if thought signature is in function
                            # response
                            elif hasattr(
                                tool_call_delta, 'function'
                            ) and hasattr(
                                tool_call_delta.function, 'extra_content'
                            ):
                                func_extra = (
                                    tool_call_delta.function.extra_content
                                )
                                if (
                                    isinstance(func_extra, dict)
                                    and 'google' in func_extra
                                ):
                                    accumulated_signatures[index] = func_extra

                            # If we have accumulated signature for this tool
                            # call, ensure it's preserved in the chunk
                            if index in accumulated_signatures:
                                # Add extra_content to tool call delta if it
                                # doesn't exist
                                if not hasattr(
                                    tool_call_delta, 'extra_content'
                                ):
                                    tool_call_delta.extra_content = (
                                        accumulated_signatures[index]
                                    )
                                elif tool_call_delta.extra_content is None:
                                    tool_call_delta.extra_content = (
                                        accumulated_signatures[index]
                                    )

                yield processed_chunk

        return async_thought_preserving_generator()

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of Gemini chat completion.

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
        """
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )
        messages = self._process_messages(messages)
        if response_format:
            if tools:
                raise ValueError(
                    "Gemini does not support function calling with "
                    "response format."
                )
            result: Union[ChatCompletion, Stream[ChatCompletionChunk]] = (
                self._request_parse(messages, response_format)
            )
        else:
            result = self._request_chat_completion(messages, tools)

        return result

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of OpenAI chat completion in async mode.

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
        self._log_and_trace()

        response_format = response_format or self.model_config_dict.get(
            "response_format", None
        )
        messages = self._process_messages(messages)
        if response_format:
            if tools:
                raise ValueError(
                    "Gemini does not support function calling with "
                    "response format."
                )
            result: Union[
                ChatCompletion, AsyncStream[ChatCompletionChunk]
            ] = await self._arequest_parse(messages, response_format)
        else:
            result = await self._arequest_chat_completion(messages, tools)

        return result

    def _request_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        request_config = self._prepare_request_config(tools)

        try:
            response = self._client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **request_config,
            )
        except Exception as err:
            print(err)
            if not self._is_stale_cached_content_error(err):
                raise
            stale_cache = self._cached_content
            logger.warning(
                "Gemini cached_content %s is unavailable; "
                "retrying without cache.",
                stale_cache,
            )
            self._cached_content = None
            request_config = self._prepare_request_config(tools)
            response = self._client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **request_config,
            )

        # Preserve thought signatures from the response for future requests
        return self._preserve_thought_signatures(response)  # type: ignore[return-value]

    async def _arequest_chat_completion(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        request_config = self._prepare_request_config(tools)

        try:
            response = await self._async_client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **request_config,
            )
        except Exception as err:
            if not self._is_stale_cached_content_error(err):
                raise
            stale_cache = self._cached_content
            logger.warning(
                "Gemini cached_content %s is unavailable; "
                "retrying without cache.",
                stale_cache,
            )
            self._cached_content = None
            request_config = self._prepare_request_config(tools)
            response = await self._async_client.chat.completions.create(
                messages=messages,
                model=self.model_type,
                **request_config,
            )

        # Preserve thought signatures from the response for future requests
        return self._preserve_thought_signatures(response)  # type: ignore[return-value]

    def _request_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        try:
            return super()._request_parse(messages, response_format, tools)
        except Exception as err:
            if not self._is_stale_cached_content_error(err):
                raise
            stale_cache = self._cached_content
            logger.warning(
                "Gemini cached_content %s is unavailable during parse; "
                "retrying without cache.",
                stale_cache,
            )
            self._cached_content = None
            return super()._request_parse(messages, response_format, tools)

    async def _arequest_parse(
        self,
        messages: List[OpenAIMessage],
        response_format: Type[BaseModel],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> ChatCompletion:
        try:
            return await super()._arequest_parse(
                messages, response_format, tools
            )
        except Exception as err:
            if not self._is_stale_cached_content_error(err):
                raise
            stale_cache = self._cached_content
            logger.warning(
                "Gemini cached_content %s is unavailable during parse; "
                "retrying without cache.",
                stale_cache,
            )
            self._cached_content = None
            return await super()._arequest_parse(
                messages, response_format, tools
            )
