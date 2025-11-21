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
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Type,
    Union,
)

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs import GeminiConfig
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
        api_key = api_key or os.environ.get("GEMINI_API_KEY")
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

    def _process_messages(self, messages) -> List[OpenAIMessage]:
        r"""Process the messages for Gemini API to ensure no empty content,
        which is not accepted by Gemini. Also preserves thought signatures
        required for Gemini 3 Pro function calling and adds fallback signatures
        when they are missing.
        """
        import copy

        processed_messages = []
        for msg in messages:
            # Use deep copy to preserve all nested structures including
            # thought signatures in extra_content
            msg_copy = copy.deepcopy(msg)
            if 'content' in msg_copy and msg_copy['content'] == '':
                msg_copy['content'] = 'null'
            processed_messages.append(msg_copy)
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
        import copy

        request_config = copy.deepcopy(self.model_config_dict)
        # Remove strict and anyOf from each tool's function parameters since
        # Gemini does not support them
        if tools:
            for tool in tools:
                function_dict = tool.get('function', {})
                function_dict.pop("strict", None)

                # Process parameters to remove anyOf and handle enum/format
                if 'parameters' in function_dict:
                    params = function_dict['parameters']
                    if 'properties' in params:
                        for prop_name, prop_value in params[
                            'properties'
                        ].items():
                            if 'anyOf' in prop_value:
                                # Replace anyOf with the first type in the list
                                first_type = prop_value['anyOf'][0]
                                params['properties'][prop_name] = first_type
                                # Preserve description if it exists
                                if 'description' in prop_value:
                                    params['properties'][prop_name][
                                        'description'
                                    ] = prop_value['description']

                            # Handle enum and format restrictions for Gemini
                            # API enum: only allowed for string type
                            if prop_value.get('type') != 'string':
                                prop_value.pop('enum', None)

                            # format: only allowed for string, integer, and
                            # number types
                            if prop_value.get('type') not in [
                                'string',
                                'integer',
                                'number',
                            ]:
                                prop_value.pop('format', None)

            request_config["tools"] = tools

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
        import copy

        request_config = copy.deepcopy(self.model_config_dict)
        # Remove strict and anyOf from each tool's function parameters since
        # Gemini does not support them
        if tools:
            for tool in tools:
                function_dict = tool.get('function', {})
                function_dict.pop("strict", None)

                # Process parameters to remove anyOf and handle enum/format
                if 'parameters' in function_dict:
                    params = function_dict['parameters']
                    if 'properties' in params:
                        for prop_name, prop_value in params[
                            'properties'
                        ].items():
                            if 'anyOf' in prop_value:
                                # Replace anyOf with the first type in the list
                                first_type = prop_value['anyOf'][0]
                                params['properties'][prop_name] = first_type
                                # Preserve description if it exists
                                if 'description' in prop_value:
                                    params['properties'][prop_name][
                                        'description'
                                    ] = prop_value['description']

                            # Handle enum and format restrictions for Gemini
                            # API enum: only allowed for string type
                            if prop_value.get('type') != 'string':
                                prop_value.pop('enum', None)

                            # format: only allowed for string, integer, and
                            # number types
                            if prop_value.get('type') not in [
                                'string',
                                'integer',
                                'number',
                            ]:
                                prop_value.pop('format', None)

            request_config["tools"] = tools

        response = await self._async_client.chat.completions.create(
            messages=messages,
            model=self.model_type,
            **request_config,
        )

        # Preserve thought signatures from the response for future requests
        return self._preserve_thought_signatures(response)  # type: ignore[return-value]
