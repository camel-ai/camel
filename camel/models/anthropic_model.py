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
import time
from typing import Any, Dict, List, Optional, Type, Union, cast

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs import AnthropicConfig
from camel.messages import OpenAIMessage
from camel.models.base_model import BaseModelBackend
from camel.types import ChatCompletion, ChatCompletionChunk, ModelType
from camel.utils import (
    AnthropicTokenCounter,
    BaseTokenCounter,
    api_keys_required,
    dependencies_required,
    get_current_agent_session_id,
    update_langfuse_trace,
)

ANTHROPIC_BETA_FOR_STRUCTURED_OUTPUTS = "structured-outputs-2025-11-13"

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


def strip_trailing_whitespace_from_messages(
    messages: List[OpenAIMessage],
) -> List[OpenAIMessage]:
    r"""Strip trailing whitespace from all message contents in a list of
    messages. This is necessary because the Anthropic API doesn't allow
    trailing whitespace in message content.

    Args:
        messages (List[OpenAIMessage]): List of messages to process

    Returns:
        List[OpenAIMessage]: The processed messages with trailing whitespace
            removed
    """
    if not messages:
        return messages

    # Create a deep copy to avoid modifying the original messages
    processed_messages = [dict(msg) for msg in messages]

    # Process each message
    for msg in processed_messages:
        if "content" in msg and msg["content"] is not None:
            if isinstance(msg["content"], str):
                msg["content"] = msg["content"].rstrip()
            elif isinstance(msg["content"], list):
                # Handle content that's a list of content parts (e.g., for
                # multimodal content)
                for i, part in enumerate(msg["content"]):
                    if (
                        isinstance(part, dict)
                        and "text" in part
                        and isinstance(part["text"], str)
                    ):
                        part["text"] = part["text"].rstrip()
                    elif isinstance(part, str):
                        msg["content"][i] = part.rstrip()

    return processed_messages  # type: ignore[return-value]


class AnthropicModel(BaseModelBackend):
    r"""Anthropic API in a unified BaseModelBackend interface.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of CLAUDE_* series.
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            that will be fed into Anthropic API. If :obj:`None`,
            :obj:`AnthropicConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the Anthropic service. (default: :obj:`None`)
        url (Optional[str], optional): The url to the Anthropic service.
            (default: :obj:`None`)
        token_counter (Optional[BaseTokenCounter], optional): Token counter to
            use for the model. If not provided, :obj:`AnthropicTokenCounter`
            will be used. (default: :obj:`None`)
        timeout (Optional[float], optional): The timeout value in seconds for
            API calls. If not provided, will fall back to the MODEL_TIMEOUT
            environment variable or default to 180 seconds.
            (default: :obj:`None`)
        max_retries (int, optional): Maximum number of retries for API calls.
            (default: :obj:`3`)
        client (Optional[Any], optional): A custom synchronous Anthropic client
            instance. If provided, this client will be used instead of
            creating a new one. (default: :obj:`None`)
        async_client (Optional[Any], optional): A custom asynchronous Anthropic
            client instance. If provided, this client will be used instead of
            creating a new one. (default: :obj:`None`)
        cache_control (Optional[str], optional): The cache control value for
            the request. Must be either '5m' or '1h'. (default: :obj:`None`)
        use_beta_for_structured_outputs (bool, optional): Whether to use the
            beta API for structured outputs. (default: :obj:`False`)
        **kwargs (Any): Additional arguments to pass to the client
            initialization.
    """

    @api_keys_required(
        [
            ("api_key", "ANTHROPIC_API_KEY"),
        ]
    )
    @dependencies_required('anthropic')
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
        cache_control: Optional[str] = None,
        use_beta_for_structured_outputs: bool = False,
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = AnthropicConfig().as_dict()
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        url = url or os.environ.get("ANTHROPIC_API_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))

        super().__init__(
            model_type=model_type,
            model_config_dict=model_config_dict,
            api_key=api_key,
            url=url,
            token_counter=token_counter,
            timeout=timeout,
            max_retries=max_retries,
        )

        # Initialize Anthropic clients
        from anthropic import Anthropic, AsyncAnthropic

        if client is not None:
            self._client = client
        else:
            self._client = Anthropic(
                api_key=self._api_key,
                base_url=self._url,
                timeout=self._timeout,
                max_retries=max_retries,
                **kwargs,
            )

        if async_client is not None:
            self._async_client = async_client
        else:
            self._async_client = AsyncAnthropic(
                api_key=self._api_key,
                base_url=self._url,
                timeout=self._timeout,
                max_retries=max_retries,
                **kwargs,
            )

        if cache_control and cache_control not in ["5m", "1h"]:
            raise ValueError("cache_control must be either '5m' or '1h'")

        self._cache_control_config = None
        if cache_control:
            self._cache_control_config = {
                "type": "ephemeral",
                "ttl": cache_control,
            }

        self._use_beta_for_structured_outputs = use_beta_for_structured_outputs

    @property
    def token_counter(self) -> BaseTokenCounter:
        r"""Initialize the token counter for the model backend.

        Returns:
            AnthropicTokenCounter: The token counter following the model's
                tokenization style.
        """
        if not self._token_counter:
            self._token_counter = AnthropicTokenCounter(
                model=str(self.model_type),
                api_key=self._api_key,
                base_url=self._url,
            )
        return self._token_counter

    def _convert_openai_to_anthropic_messages(
        self,
        messages: List[OpenAIMessage],
    ) -> tuple[Optional[str], List[Dict[str, Any]]]:
        r"""Convert OpenAI format messages to Anthropic format.

        Args:
            messages (List[OpenAIMessage]): Messages in OpenAI format.

        Returns:
            tuple[Optional[str], List[Dict[str, Any]]]: A tuple containing
                the system message (if any) and the list of messages in
                Anthropic format.
        """
        from anthropic.types import MessageParam

        system_message = None
        anthropic_messages: List[MessageParam] = []

        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")

            if role == "system":
                # Anthropic uses a separate system parameter
                if isinstance(content, str):
                    system_message = content
                elif isinstance(content, list):
                    # Extract text from content blocks
                    text_parts = []
                    for part in content:
                        if isinstance(part, dict) and "text" in part:
                            text_parts.append(part["text"])
                        elif isinstance(part, str):
                            text_parts.append(part)
                    system_message = "\n".join(text_parts)
            elif role == "user":
                # Convert user message
                if isinstance(content, str):
                    anthropic_messages.append(
                        MessageParam(role="user", content=content)
                    )
                elif isinstance(content, list):
                    # Handle multimodal content
                    anthropic_messages.append(
                        MessageParam(role="user", content=content)
                    )
            elif role == "assistant":
                # Convert assistant message
                assistant_content: Union[str, List[Dict[str, Any]]] = ""

                if msg.get("tool_calls"):
                    # Handle tool calls - Anthropic uses content blocks
                    content_blocks = []
                    if content:
                        content_blocks.append(
                            {"type": "text", "text": str(content)}
                        )

                    for tool_call in msg.get("tool_calls"):  # type: ignore[attr-defined]
                        tool_use_block = {
                            "type": "tool_use",
                            "id": tool_call.get("id", ""),
                            "name": tool_call.get("function", {}).get(
                                "name", ""
                            ),
                            "input": {},
                        }
                        # Parse arguments if it's a string
                        arguments = tool_call.get("function", {}).get(
                            "arguments", "{}"
                        )
                        if isinstance(arguments, str):
                            import json

                            try:
                                tool_use_block["input"] = json.loads(arguments)
                            except json.JSONDecodeError:
                                tool_use_block["input"] = {}
                        else:
                            tool_use_block["input"] = arguments
                        content_blocks.append(tool_use_block)

                    anthropic_messages.append(
                        MessageParam(role="assistant", content=content_blocks)  # type: ignore[typeddict-item]
                    )
                else:
                    if isinstance(content, str):
                        assistant_content = content
                    elif isinstance(content, list):
                        assistant_content = content
                    else:
                        assistant_content = str(content) if content else ""

                    anthropic_messages.append(
                        MessageParam(
                            role="assistant",
                            content=assistant_content,  # type: ignore[typeddict-item]
                        )
                    )
            elif role == "tool":
                # Convert tool response message
                tool_call_id = msg.get("tool_call_id", "")
                tool_content = (
                    content if isinstance(content, str) else str(content)
                )
                anthropic_messages.append(
                    MessageParam(
                        role="user",
                        content=[
                            {  # type: ignore[list-item]
                                "type": "tool_result",
                                "tool_use_id": tool_call_id,
                                "content": tool_content,
                            }
                        ],
                    )
                )

        return system_message, anthropic_messages  # type: ignore[return-value]

    def _convert_anthropic_to_openai_response(
        self, response: Any, model: str
    ) -> ChatCompletion:
        r"""Convert Anthropic API response to OpenAI ChatCompletion format.

        Args:
            response: The response object from Anthropic API.
            model (str): The model name.

        Returns:
            ChatCompletion: Response in OpenAI format.
        """
        # Extract message content
        content = ""
        tool_calls = None

        if hasattr(response, "content"):
            content_blocks = response.content
            if content_blocks:
                # Extract text content and tool calls
                text_parts = []
                tool_calls_list = []
                for block in content_blocks:
                    if hasattr(block, "type"):
                        if block.type == "text":
                            if hasattr(block, "text"):
                                text_parts.append(block.text)
                        elif block.type == "tool_use":
                            import json

                            tool_input = (
                                block.input if hasattr(block, "input") else {}
                            )
                            tool_calls_list.append(
                                {
                                    "id": block.id
                                    if hasattr(block, "id")
                                    else "",
                                    "type": "function",
                                    "function": {
                                        "name": block.name
                                        if hasattr(block, "name")
                                        else "",
                                        "arguments": json.dumps(tool_input)
                                        if isinstance(tool_input, dict)
                                        else str(tool_input),
                                    },
                                }
                            )
                    elif isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            import json

                            tool_input = block.get("input", {})
                            tool_calls_list.append(
                                {
                                    "id": block.get("id", ""),
                                    "type": "function",
                                    "function": {
                                        "name": block.get("name", ""),
                                        "arguments": json.dumps(tool_input)
                                        if isinstance(tool_input, dict)
                                        else str(tool_input),
                                    },
                                }
                            )
                content = "".join(text_parts)
                if tool_calls_list:
                    tool_calls = tool_calls_list
            else:
                content = ""
        elif isinstance(response.content, str):
            content = response.content

        # Determine finish reason
        finish_reason = None
        if hasattr(response, "stop_reason"):
            stop_reason = response.stop_reason
            if stop_reason == "end_turn":
                finish_reason = "stop"
            elif stop_reason == "max_tokens":
                finish_reason = "length"
            elif stop_reason == "stop_sequence":
                finish_reason = "stop"
            elif stop_reason == "tool_use":
                finish_reason = "tool_calls"
            else:
                finish_reason = stop_reason

        # Build message dict
        message_dict: Dict[str, Any] = {
            "role": "assistant",
            "content": content,
        }
        if tool_calls:
            message_dict["tool_calls"] = tool_calls

        # Extract usage information
        usage = None
        if hasattr(response, "usage"):
            usage = {
                "prompt_tokens": getattr(response.usage, "input_tokens", 0),
                "completion_tokens": getattr(
                    response.usage, "output_tokens", 0
                ),
                "total_tokens": (
                    getattr(response.usage, "input_tokens", 0)
                    + getattr(response.usage, "output_tokens", 0)
                ),
            }

        # Create ChatCompletion
        return ChatCompletion.construct(
            id=getattr(response, "id", f"chatcmpl-{int(time.time())}"),
            choices=[
                {
                    "index": 0,
                    "message": message_dict,
                    "finish_reason": finish_reason,
                }
            ],
            created=int(time.time()),
            model=model,
            object="chat.completion",
            usage=usage,
        )

    def _convert_anthropic_stream_to_openai_chunk(
        self, chunk: Any, model: str
    ) -> ChatCompletionChunk:
        r"""Convert Anthropic streaming chunk to OpenAI ChatCompletionChunk.

        Args:
            chunk: The streaming chunk from Anthropic API.
            model (str): The model name.

        Returns:
            ChatCompletionChunk: Chunk in OpenAI format.
        """
        delta_content = ""
        tool_calls = None
        finish_reason = None
        chunk_id = ""

        if hasattr(chunk, "type"):
            chunk_type = chunk.type
            if chunk_type == "message_start":
                # Initialize message
                if hasattr(chunk, "message") and hasattr(chunk.message, "id"):
                    chunk_id = chunk.message.id
                return ChatCompletionChunk.construct(
                    id=chunk_id,
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )
            elif chunk_type == "content_block_start":
                # Content block starting - skip for now
                return ChatCompletionChunk.construct(
                    id=chunk_id,
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )
            elif chunk_type == "content_block_delta":
                # Content delta
                if hasattr(chunk, "delta"):
                    delta_obj = chunk.delta
                    if hasattr(delta_obj, "text"):
                        delta_content = delta_obj.text
                    elif (
                        hasattr(delta_obj, "type") and delta_obj.type == "text"
                    ):
                        if hasattr(delta_obj, "text"):
                            delta_content = delta_obj.text
            elif chunk_type == "content_block_stop":
                # Content block finished - skip
                return ChatCompletionChunk.construct(
                    id=chunk_id,
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )
            elif chunk_type == "message_delta":
                # Message delta (usage info, etc.)
                if hasattr(chunk, "delta") and hasattr(
                    chunk.delta, "stop_reason"
                ):
                    stop_reason = chunk.delta.stop_reason
                    if stop_reason == "end_turn":
                        finish_reason = "stop"
                    elif stop_reason == "max_tokens":
                        finish_reason = "length"
                    elif stop_reason == "stop_sequence":
                        finish_reason = "stop"
                    elif stop_reason == "tool_use":
                        finish_reason = "tool_calls"
            elif chunk_type == "message_stop":
                # Message finished
                return ChatCompletionChunk.construct(
                    id=chunk_id,
                    choices=[
                        {"index": 0, "delta": {}, "finish_reason": "stop"}
                    ],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )

        delta: Dict[str, Any] = {}
        if delta_content:
            delta["content"] = delta_content
        if tool_calls:
            delta["tool_calls"] = tool_calls

        return ChatCompletionChunk.construct(
            id=chunk_id,
            choices=[
                {"index": 0, "delta": delta, "finish_reason": finish_reason}
            ],
            created=int(time.time()),
            model=model,
            object="chat.completion.chunk",
        )

    def _convert_openai_tools_to_anthropic(
        self, tools: Optional[List[Dict[str, Any]]]
    ) -> Optional[List[Dict[str, Any]]]:
        r"""Convert OpenAI tools format to Anthropic tools format.

        Args:
            tools (Optional[List[Dict[str, Any]]]): Tools in OpenAI format.

        Returns:
            Optional[List[Dict[str, Any]]]: Tools in Anthropic format.
        """
        if not tools:
            return None

        anthropic_tools = []
        for tool in tools:
            if "function" in tool:
                func = tool["function"]
                anthropic_tool = {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": func.get("parameters", {}),
                }
                if self._use_beta_for_structured_outputs:
                    anthropic_tool["strict"] = func.get("strict", True)
                anthropic_tools.append(anthropic_tool)

        return anthropic_tools

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference of Anthropic chat completion.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response. (Not supported by Anthropic API directly)
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

        # Strip trailing whitespace from messages
        processed_messages = strip_trailing_whitespace_from_messages(messages)

        # Convert messages to Anthropic format
        system_message, anthropic_messages = (
            self._convert_openai_to_anthropic_messages(processed_messages)
        )

        # Prepare request parameters
        request_params: Dict[str, Any] = {
            "model": str(self.model_type),
            "messages": anthropic_messages,
            "max_tokens": self.model_config_dict.get("max_tokens", 4096),
        }

        if system_message:
            # if cache_control is configured, add it to the system message
            if self._cache_control_config:
                request_params["system"] = [
                    {
                        "type": "text",
                        "text": system_message,
                        "cache_control": self._cache_control_config,
                    }
                ]
            else:
                request_params["system"] = system_message

        # if cache_control is configured, add it to the last message
        if self._cache_control_config:
            if isinstance(request_params["messages"], list):
                if isinstance(request_params["messages"][-1]["content"], str):
                    request_params["messages"][-1]["content"] = [
                        {
                            "type": "text",
                            "text": request_params["messages"][-1]["content"],
                            "cache_control": self._cache_control_config,
                        }
                    ]
                elif isinstance(
                    request_params["messages"][-1]["content"], list
                ):
                    if isinstance(
                        request_params["messages"][-1]["content"][-1], dict
                    ):
                        request_params["messages"][-1]["content"][-1][
                            "cache_control"
                        ] = self._cache_control_config

        # Add config parameters
        for key in ["temperature", "top_p", "top_k", "stop_sequences"]:
            if key in self.model_config_dict:
                request_params[key] = self.model_config_dict[key]

        # Convert tools
        anthropic_tools = self._convert_openai_tools_to_anthropic(tools)
        if anthropic_tools:
            request_params["tools"] = anthropic_tools

        # Add beta for structured outputs if configured
        if self._use_beta_for_structured_outputs:
            request_params["betas"] = [ANTHROPIC_BETA_FOR_STRUCTURED_OUTPUTS]
            create_func = self._client.beta.messages.create
        else:
            create_func = self._client.messages.create

        # Check if streaming
        is_streaming = self.model_config_dict.get("stream", False)

        if is_streaming:
            # Return streaming response
            stream = create_func(**request_params, stream=True)
            return self._wrap_anthropic_stream(stream, str(self.model_type))
        else:
            # Return non-streaming response
            response = create_func(**request_params)
            return self._convert_anthropic_to_openai_response(
                response, str(self.model_type)
            )

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs inference of Anthropic chat completion in async mode.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response. (Not supported by Anthropic API directly)
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

        # Strip trailing whitespace from messages
        processed_messages = strip_trailing_whitespace_from_messages(messages)

        # Convert messages to Anthropic format
        system_message, anthropic_messages = (
            self._convert_openai_to_anthropic_messages(processed_messages)
        )

        # Prepare request parameters
        request_params: Dict[str, Any] = {
            "model": str(self.model_type),
            "messages": anthropic_messages,
            "max_tokens": self.model_config_dict.get("max_tokens", 4096),
        }

        if system_message:
            # if cache_control is configured, add it to the system message
            if self._cache_control_config:
                request_params["system"] = [
                    {
                        "type": "text",
                        "text": system_message,
                        "cache_control": self._cache_control_config,
                    }
                ]
            else:
                request_params["system"] = system_message

        # if cache_control is configured, add it to the last message
        if self._cache_control_config:
            if isinstance(request_params["messages"], list):
                if isinstance(request_params["messages"][-1]["content"], str):
                    request_params["messages"][-1]["content"] = [
                        {
                            "type": "text",
                            "text": request_params["messages"][-1]["content"],
                            "cache_control": self._cache_control_config,
                        }
                    ]
                elif isinstance(
                    request_params["messages"][-1]["content"], list
                ):
                    if isinstance(
                        request_params["messages"][-1]["content"][-1], dict
                    ):
                        request_params["messages"][-1]["content"][-1][
                            "cache_control"
                        ] = self._cache_control_config

        # Add config parameters
        for key in ["temperature", "top_p", "top_k", "stop_sequences"]:
            if key in self.model_config_dict:
                request_params[key] = self.model_config_dict[key]

        # Convert tools
        anthropic_tools = self._convert_openai_tools_to_anthropic(tools)
        if anthropic_tools:
            request_params["tools"] = anthropic_tools

        # Add beta for structured outputs if configured
        if self._use_beta_for_structured_outputs:
            request_params["betas"] = [ANTHROPIC_BETA_FOR_STRUCTURED_OUTPUTS]
            create_func = self._async_client.beta.messages.create
        else:
            create_func = self._async_client.messages.create

        # Check if streaming
        is_streaming = self.model_config_dict.get("stream", False)

        if is_streaming:
            # Return streaming response
            stream = await create_func(**request_params, stream=True)
            return self._wrap_anthropic_async_stream(
                stream, str(self.model_type)
            )
        else:
            # Return non-streaming response
            response = await create_func(**request_params)
            return self._convert_anthropic_to_openai_response(
                response, str(self.model_type)
            )

    def _wrap_anthropic_stream(
        self, stream: Any, model: str
    ) -> Stream[ChatCompletionChunk]:
        r"""Wrap Anthropic streaming response to OpenAI Stream format.

        Args:
            stream: The streaming response from Anthropic API.
            model (str): The model name.

        Returns:
            Stream[ChatCompletionChunk]: Stream in OpenAI format.
        """

        def _generate_chunks():
            for chunk in stream:
                yield self._convert_anthropic_stream_to_openai_chunk(
                    chunk, model
                )

        return cast(Stream[ChatCompletionChunk], _generate_chunks())

    def _wrap_anthropic_async_stream(
        self, stream: Any, model: str
    ) -> AsyncStream[ChatCompletionChunk]:
        r"""Wrap Anthropic async streaming response to OpenAI AsyncStream.

        Args:
            stream: The async streaming response from Anthropic API.
            model (str): The model name.

        Returns:
            AsyncStream[ChatCompletionChunk]: AsyncStream in OpenAI format.
        """

        async def _generate_chunks():
            async for chunk in stream:
                yield self._convert_anthropic_stream_to_openai_chunk(
                    chunk, model
                )

        return cast(AsyncStream[ChatCompletionChunk], _generate_chunks())

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)
