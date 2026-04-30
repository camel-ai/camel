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
        **kwargs: Any,
    ) -> None:
        if model_config_dict is None:
            model_config_dict = AnthropicConfig().as_dict()
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        url = url or os.environ.get("ANTHROPIC_API_BASE_URL")
        timeout = timeout or float(os.environ.get("MODEL_TIMEOUT", 180))

        cache_control = model_config_dict.get("cache_control")

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

        if cache_control is not None and cache_control not in ("5m", "1h"):
            raise ValueError(
                f"Invalid cache_control value: {cache_control!r}. "
                f"Must be either '5m' or '1h'."
            )

        self._cache_control_config = None
        if cache_control:
            self._cache_control_config = {
                "type": "ephemeral",
                "ttl": cache_control,
            }
        self._tool_call_thinking_blocks: Dict[str, List[Dict[str, Any]]] = {}

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

    @property
    def supports_tool_response_format(self) -> bool:
        r"""Anthropic JSON outputs are independent from strict tool use."""
        return True

    @staticmethod
    def _get_block_value(
        block: Any,
        key: str,
        default: Any = None,
    ) -> Any:
        r"""Read a content block value from a dict or SDK object."""
        if isinstance(block, dict):
            return block.get(key, default)
        return getattr(block, key, default)

    @classmethod
    def _content_block_to_dict(
        cls,
        block: Any,
    ) -> Dict[str, Any]:
        r"""Convert an Anthropic content block to a plain dictionary."""
        if isinstance(block, dict):
            return copy.deepcopy(block)

        model_dump = getattr(block, "model_dump", None)
        if callable(model_dump):
            dumped = model_dump(exclude_none=True)
            if isinstance(dumped, dict):
                return dumped

        block_type = cls._get_block_value(block, "type")
        if not isinstance(block_type, str):
            return {}

        block_dict: Dict[str, Any] = {"type": block_type}
        for key in ("thinking", "signature", "data"):
            value = cls._get_block_value(block, key)
            if value is not None:
                block_dict[key] = value
        return block_dict

    @classmethod
    def _extract_thinking_blocks_from_message(
        cls,
        message: OpenAIMessage,
    ) -> List[Dict[str, Any]]:
        r"""Extract raw Anthropic thinking blocks from an OpenAI message."""
        raw_blocks = message.get("anthropic_thinking_blocks") or message.get(
            "thinking_blocks"
        )
        if not isinstance(raw_blocks, list):
            return []

        thinking_blocks: List[Dict[str, Any]] = []
        for block in raw_blocks:
            block_dict = cls._content_block_to_dict(block)
            if block_dict.get("type") in {"thinking", "redacted_thinking"}:
                thinking_blocks.append(block_dict)
        return thinking_blocks

    @staticmethod
    def _get_tool_call_id(tool_call: Any) -> Optional[str]:
        r"""Extract an OpenAI-style tool call ID from a dict or SDK object."""
        if isinstance(tool_call, dict):
            tool_call_id = tool_call.get("id")
        else:
            tool_call_id = getattr(tool_call, "id", None)
        return tool_call_id if isinstance(tool_call_id, str) else None

    @classmethod
    def _get_tool_call_extra_content(
        cls,
        tool_call: Any,
    ) -> Optional[Dict[str, Any]]:
        r"""Extract non-standard extra content from a tool call."""
        if isinstance(tool_call, dict):
            extra_content = tool_call.get("extra_content")
        else:
            extra_content = getattr(tool_call, "extra_content", None)
        return extra_content if isinstance(extra_content, dict) else None

    @classmethod
    def _extract_thinking_blocks_from_tool_call(
        cls,
        tool_call: Any,
    ) -> List[Dict[str, Any]]:
        r"""Extract raw Anthropic thinking blocks from tool extra content."""
        extra_content = cls._get_tool_call_extra_content(tool_call)
        if not extra_content:
            return []

        raw_blocks = extra_content.get("anthropic_thinking_blocks")
        if not isinstance(raw_blocks, list):
            return []

        thinking_blocks: List[Dict[str, Any]] = []
        for block in raw_blocks:
            block_dict = cls._content_block_to_dict(block)
            if block_dict.get("type") in {"thinking", "redacted_thinking"}:
                thinking_blocks.append(block_dict)
        return thinking_blocks

    def _get_cached_thinking_blocks_for_tool_calls(
        self,
        tool_calls: List[Any],
    ) -> List[Dict[str, Any]]:
        r"""Return cached thinking blocks for the first matching tool call."""
        for tool_call in tool_calls:
            thinking_blocks = self._extract_thinking_blocks_from_tool_call(
                tool_call
            )
            if thinking_blocks:
                return thinking_blocks

            tool_call_id = self._get_tool_call_id(tool_call)
            if tool_call_id in self._tool_call_thinking_blocks:
                return copy.deepcopy(
                    self._tool_call_thinking_blocks[tool_call_id]
                )
        return []

    def _cache_thinking_blocks_for_tool_calls(
        self,
        thinking_blocks: List[Dict[str, Any]],
        tool_calls: List[Any],
    ) -> None:
        r"""Cache raw thinking blocks for Anthropic tool-use continuation."""
        if not thinking_blocks or not tool_calls:
            return

        for tool_call in tool_calls:
            tool_call_id = self._get_tool_call_id(tool_call)
            if tool_call_id:
                self._tool_call_thinking_blocks[tool_call_id] = copy.deepcopy(
                    thinking_blocks
                )

    @staticmethod
    def _is_thinking_enabled(thinking: Any) -> bool:
        r"""Return whether an Anthropic thinking config enables thinking."""
        if thinking is None:
            return False
        if isinstance(thinking, dict):
            return thinking.get("type") != "disabled"
        return True

    def _validate_tool_choice_for_thinking(
        self,
        thinking: Any,
        tool_choice: Any,
    ) -> None:
        r"""Validate Anthropic's tool-choice limitation for thinking."""
        if not self._is_thinking_enabled(thinking) or tool_choice is None:
            return
        if isinstance(tool_choice, dict) and tool_choice.get("type") in {
            "auto",
            "none",
        }:
            return
        raise ValueError(
            "Anthropic extended thinking with tools only supports "
            "`tool_choice={'type': 'auto'}` or "
            "`tool_choice={'type': 'none'}`."
        )

    def _validate_sampling_for_thinking(self, thinking: Any) -> None:
        r"""Validate Anthropic sampling limitations for thinking."""
        if not self._is_thinking_enabled(thinking):
            return

        if self.model_config_dict.get("temperature") is not None:
            raise ValueError(
                "Anthropic extended thinking is not compatible with "
                "`temperature`."
            )
        if self.model_config_dict.get("top_k") is not None:
            raise ValueError(
                "Anthropic extended thinking is not compatible with `top_k`."
            )

        top_p = self.model_config_dict.get("top_p")
        if top_p is None:
            return
        if not isinstance(top_p, (int, float)) or not 0.95 <= top_p <= 1:
            raise ValueError(
                "Anthropic extended thinking only supports `top_p` values "
                "between 0.95 and 1."
            )

    def _build_request_output_config(
        self,
        response_format: Optional[Type[BaseModel]],
        extra_body: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        r"""Build Anthropic output_config from config and response_format."""
        output_config: Dict[str, Any] = {}

        legacy_output_config = extra_body.pop("output_config", None)
        if isinstance(legacy_output_config, dict):
            output_config.update(copy.deepcopy(legacy_output_config))

        configured_output_config = self.model_config_dict.get("output_config")
        if isinstance(configured_output_config, dict):
            output_config.update(copy.deepcopy(configured_output_config))

        if response_format is not None:
            output_config.update(self._build_output_config(response_format))

        return output_config or None

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
                    thinking_blocks = (
                        self._extract_thinking_blocks_from_message(msg)
                    )
                    if not thinking_blocks:
                        thinking_blocks = (
                            self._get_cached_thinking_blocks_for_tool_calls(
                                msg.get("tool_calls", [])  # type: ignore[arg-type]
                            )
                        )
                    content_blocks.extend(thinking_blocks)

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
                tool_call_id = str(msg.get("tool_call_id", ""))
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

    @staticmethod
    def _extract_usage(usage_obj: Any) -> Dict[str, Any]:
        r"""Extract usage information from an Anthropic usage object."""

        def _get_int(attr_name: str) -> int:
            value = getattr(usage_obj, attr_name, 0)
            return value if isinstance(value, int) else 0

        input_tokens = _get_int("input_tokens")
        output_tokens = _get_int("output_tokens")

        usage: Dict[str, Any] = {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }

        # Prompt-caching fields are included only when actually set to int.
        cache_read = getattr(usage_obj, "cache_read_input_tokens", None)
        if isinstance(cache_read, int):
            usage["cache_read_input_tokens"] = cache_read

        cache_creation = getattr(
            usage_obj, "cache_creation_input_tokens", None
        )
        if isinstance(cache_creation, int):
            usage["cache_creation_input_tokens"] = cache_creation

        cache_creation_detail = getattr(usage_obj, "cache_creation", None)
        if isinstance(cache_creation_detail, dict):
            usage["cache_creation"] = cache_creation_detail
        elif isinstance(cache_creation_detail, BaseModel):
            usage["cache_creation"] = cache_creation_detail.model_dump()

        return usage

    def _build_output_config(
        self, response_format: Type[BaseModel]
    ) -> Dict[str, Any]:
        r"""Build Anthropic output_config.format from a Pydantic model."""
        from anthropic import transform_schema

        schema = transform_schema(response_format.model_json_schema())
        return {
            "format": {
                "type": "json_schema",
                "schema": schema,
            }
        }

    @staticmethod
    def _normalize_type_list_for_anthropic_schema(schema: Any) -> Any:
        r"""Convert JSON Schema type lists to Anthropic SDK-supported anyOf."""
        if isinstance(schema, dict):
            normalized = {
                key: AnthropicModel._normalize_type_list_for_anthropic_schema(
                    value
                )
                for key, value in schema.items()
            }
            type_value = schema.get("type")
            if (
                isinstance(type_value, list)
                and "anyOf" not in schema
                and all(isinstance(item, str) for item in type_value)
            ):
                normalized.pop("type", None)
                normalized["anyOf"] = [{"type": item} for item in type_value]
            return normalized
        if isinstance(schema, list):
            return [
                AnthropicModel._normalize_type_list_for_anthropic_schema(item)
                for item in schema
            ]
        return schema

    def _convert_anthropic_to_openai_response(
        self,
        response: Any,
        model: str,
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
        reasoning_content = None
        thinking_blocks: List[Dict[str, Any]] = []

        if hasattr(response, "content"):
            content_blocks = response.content
            if content_blocks:
                # Extract text content and tool calls
                text_parts = []
                reasoning_parts = []
                tool_calls_list = []
                for block in content_blocks:
                    block_type = self._get_block_value(block, "type")
                    if block_type == "text":
                        text = self._get_block_value(block, "text", "")
                        if isinstance(text, str):
                            text_parts.append(text)
                    elif block_type == "thinking":
                        block_dict = self._content_block_to_dict(block)
                        thinking_blocks.append(block_dict)
                        thinking = block_dict.get("thinking")
                        if isinstance(thinking, str) and thinking:
                            reasoning_parts.append(thinking)
                    elif block_type == "redacted_thinking":
                        block_dict = self._content_block_to_dict(block)
                        thinking_blocks.append(block_dict)
                    elif block_type == "tool_use":
                        tool_input = self._get_block_value(block, "input", {})
                        tool_name = self._get_block_value(block, "name", "")
                        tool_id = self._get_block_value(block, "id", "")
                        tool_call = {
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": json.dumps(tool_input)
                                if isinstance(tool_input, dict)
                                else str(tool_input),
                            },
                        }
                        if thinking_blocks:
                            tool_call["extra_content"] = {
                                "anthropic_thinking_blocks": copy.deepcopy(
                                    thinking_blocks
                                )
                            }
                        tool_calls_list.append(tool_call)
                content = "".join(text_parts)
                if reasoning_parts:
                    reasoning_content = "\n".join(reasoning_parts)
                if tool_calls_list:
                    tool_calls = tool_calls_list
                    self._cache_thinking_blocks_for_tool_calls(
                        thinking_blocks, tool_calls_list
                    )
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
        if reasoning_content is not None:
            message_dict["reasoning_content"] = reasoning_content
        if thinking_blocks:
            message_dict["anthropic_thinking_blocks"] = thinking_blocks
        if tool_calls:
            message_dict["tool_calls"] = tool_calls

        # Extract usage information
        usage = None
        if hasattr(response, "usage"):
            usage = self._extract_usage(response.usage)

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
        self,
        chunk: Any,
        model: str,
        tool_call_index: Dict[str, int],
        finish_reason_sent: bool = False,
        thinking_state: Optional[Dict[str, Any]] = None,
    ) -> ChatCompletionChunk:
        r"""Convert Anthropic streaming chunk to OpenAI ChatCompletionChunk.

        Args:
            chunk: The streaming chunk from Anthropic API.
            model (str): The model name.
            tool_call_index (Dict[str, int]): A mutable dict tracking tool call
                indices by their IDs, used to maintain consistent indexing
                across streaming chunks.

        Returns:
            ChatCompletionChunk: Chunk in OpenAI format.
        """
        delta_content = ""
        delta_reasoning = ""
        tool_calls = None
        finish_reason = None
        chunk_id = ""
        usage = None
        if thinking_state is None:
            thinking_state = {}

        if hasattr(chunk, "type"):
            chunk_type = chunk.type
            if chunk_type == "message_start":
                # Initialize message
                if hasattr(chunk, "message") and hasattr(chunk.message, "id"):
                    chunk_id = chunk.message.id
                # Extract usage from message_start (contains cache
                # fields like cache_read_input_tokens)
                msg_usage = None
                if (
                    hasattr(chunk, "message")
                    and hasattr(chunk.message, "usage")
                    and chunk.message.usage
                ):
                    msg_usage = self._extract_usage(chunk.message.usage)
                return ChatCompletionChunk.construct(
                    id=chunk_id,
                    choices=[{"index": 0, "delta": {}, "finish_reason": None}],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                    usage=msg_usage,
                )
            elif chunk_type == "content_block_start":
                # Content block starting
                if hasattr(chunk, "content_block"):
                    block = chunk.content_block
                    block_type = self._get_block_value(block, "type")
                    if block_type in {"thinking", "redacted_thinking"}:
                        chunk_idx = getattr(chunk, "index", 0)
                        current_blocks = thinking_state.setdefault(
                            "current_blocks", {}
                        )
                        current_blocks[chunk_idx] = (
                            self._content_block_to_dict(block)
                        )
                    elif block_type == "tool_use":
                        # Tool use block starting
                        tool_id = self._get_block_value(block, "id", "")
                        tool_name = self._get_block_value(block, "name", "")
                        # Assign index for this tool call
                        idx = len(
                            [
                                k
                                for k in tool_call_index
                                if not k.startswith("_")
                            ]
                        )
                        tool_call_index[tool_id] = idx
                        # Also map by chunk.index for content_block_delta
                        chunk_idx = getattr(chunk, "index", 0)
                        tool_call_index[f"_chunk_{chunk_idx}"] = idx
                        self._cache_thinking_blocks_for_tool_calls(
                            thinking_state.get("thinking_blocks", []),
                            [{"id": tool_id}],
                        )
                        tool_call_delta = {
                            "index": idx,
                            "id": tool_id,
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": "",
                            },
                        }
                        thinking_blocks = thinking_state.get(
                            "thinking_blocks", []
                        )
                        if thinking_blocks:
                            tool_call_delta["extra_content"] = {
                                "anthropic_thinking_blocks": copy.deepcopy(
                                    thinking_blocks
                                )
                            }
                        tool_calls = [tool_call_delta]
                if tool_calls is None:
                    return ChatCompletionChunk.construct(
                        id=chunk_id,
                        choices=[
                            {"index": 0, "delta": {}, "finish_reason": None}
                        ],
                        created=int(time.time()),
                        model=model,
                        object="chat.completion.chunk",
                    )
            elif chunk_type == "content_block_delta":
                # Content delta
                if hasattr(chunk, "delta"):
                    delta_obj = chunk.delta
                    delta_type = getattr(delta_obj, "type", "")
                    if delta_type == "text_delta":
                        delta_content = getattr(delta_obj, "text", "")
                    elif delta_type == "thinking_delta":
                        delta_reasoning = getattr(delta_obj, "thinking", "")
                        chunk_idx = getattr(chunk, "index", 0)
                        current_blocks = thinking_state.setdefault(
                            "current_blocks", {}
                        )
                        block = current_blocks.setdefault(
                            chunk_idx,
                            {"type": "thinking", "thinking": ""},
                        )
                        block["thinking"] = (
                            block.get("thinking", "") + delta_reasoning
                        )
                    elif delta_type == "signature_delta":
                        signature = getattr(delta_obj, "signature", "")
                        chunk_idx = getattr(chunk, "index", 0)
                        current_blocks = thinking_state.setdefault(
                            "current_blocks", {}
                        )
                        block = current_blocks.setdefault(
                            chunk_idx,
                            {"type": "thinking", "thinking": ""},
                        )
                        block["signature"] = signature
                    elif delta_type == "input_json_delta":
                        # Tool input arguments delta
                        partial_json = getattr(delta_obj, "partial_json", "")
                        # Get the current tool call index from chunk.index
                        # Map Anthropic's chunk.index to our tool call index
                        chunk_idx = getattr(chunk, "index", 0)
                        mapped_idx = tool_call_index.get(
                            f"_chunk_{chunk_idx}", chunk_idx
                        )
                        tool_calls = [
                            {
                                "index": mapped_idx,
                                "function": {
                                    "arguments": partial_json,
                                },
                            }
                        ]
            elif chunk_type == "content_block_stop":
                chunk_idx = getattr(chunk, "index", 0)
                current_blocks = thinking_state.setdefault(
                    "current_blocks", {}
                )
                block = current_blocks.pop(chunk_idx, None)
                if isinstance(block, dict) and block.get("type") in {
                    "thinking",
                    "redacted_thinking",
                }:
                    thinking_state.setdefault("thinking_blocks", []).append(
                        block
                    )
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
                # Extract usage info from message_delta
                if hasattr(chunk, "usage") and chunk.usage:
                    usage = self._extract_usage(chunk.usage)
            elif chunk_type == "message_stop":
                # Message finished - only set finish_reason if not already sent
                # This prevents duplicate finish_reason triggers in chat_agent
                final_finish_reason = None if finish_reason_sent else "stop"
                return ChatCompletionChunk.construct(
                    id=chunk_id,
                    choices=[
                        {
                            "index": 0,
                            "delta": {},
                            "finish_reason": final_finish_reason,
                        }
                    ],
                    created=int(time.time()),
                    model=model,
                    object="chat.completion.chunk",
                )

        delta: Dict[str, Any] = {}
        if delta_content:
            delta["content"] = delta_content
        if delta_reasoning:
            delta["reasoning_content"] = delta_reasoning
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
            usage=usage,
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
                input_schema = func.get("parameters", {})
                if func.get("strict") is True and input_schema:
                    from anthropic import transform_schema

                    input_schema = transform_schema(
                        self._normalize_type_list_for_anthropic_schema(
                            input_schema
                        )
                    )
                anthropic_tool = {
                    "name": func.get("name", ""),
                    "description": func.get("description", ""),
                    "input_schema": input_schema,
                }
                if "strict" in func:
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
            "max_tokens": self.model_config_dict.get("max_tokens", None),
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
        if self._cache_control_config and request_params["messages"]:
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
                    if request_params["messages"][-1][
                        "content"
                    ] and isinstance(
                        request_params["messages"][-1]["content"][-1], dict
                    ):
                        request_params["messages"][-1]["content"][-1][
                            "cache_control"
                        ] = self._cache_control_config

        # Add config parameters
        for key in [
            "temperature",
            "top_p",
            "top_k",
            "stop_sequences",
            "metadata",
        ]:
            if key in self.model_config_dict:
                request_params[key] = self.model_config_dict[key]

        extra_headers = self.model_config_dict.get("extra_headers")
        if extra_headers is not None:
            request_params["extra_headers"] = extra_headers

        thinking = self.model_config_dict.get("thinking")
        if thinking is not None:
            self._validate_sampling_for_thinking(thinking)
            request_params["thinking"] = copy.deepcopy(thinking)

        # Convert tools first so we know whether tools are present
        anthropic_tools = self._convert_openai_tools_to_anthropic(tools)

        extra_body = copy.deepcopy(
            self.model_config_dict.get("extra_body") or {}
        )
        output_config = self._build_request_output_config(
            response_format, extra_body
        )
        if output_config:
            request_params["output_config"] = output_config
        if extra_body:
            request_params["extra_body"] = extra_body

        if anthropic_tools:
            request_params["tools"] = anthropic_tools
            tool_choice = self.model_config_dict.get("tool_choice")
            if tool_choice is not None:
                self._validate_tool_choice_for_thinking(thinking, tool_choice)
                request_params["tool_choice"] = tool_choice

        create_func = self._client.messages.create

        # Check if streaming
        is_streaming = self.model_config_dict.get("stream", False)

        if is_streaming:
            # Return streaming response
            stream = self._call_client(
                create_func,
                **request_params,
                stream=True,
            )
            return self._wrap_anthropic_stream(stream, str(self.model_type))
        else:
            # Return non-streaming response
            response = self._call_client(create_func, **request_params)
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
            "max_tokens": self.model_config_dict.get("max_tokens", None),
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
        if self._cache_control_config and request_params["messages"]:
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
                    if request_params["messages"][-1][
                        "content"
                    ] and isinstance(
                        request_params["messages"][-1]["content"][-1], dict
                    ):
                        request_params["messages"][-1]["content"][-1][
                            "cache_control"
                        ] = self._cache_control_config

        # Add config parameters
        for key in [
            "temperature",
            "top_p",
            "top_k",
            "stop_sequences",
            "metadata",
        ]:
            if key in self.model_config_dict:
                request_params[key] = self.model_config_dict[key]

        extra_headers = self.model_config_dict.get("extra_headers")
        if extra_headers is not None:
            request_params["extra_headers"] = extra_headers

        thinking = self.model_config_dict.get("thinking")
        if thinking is not None:
            self._validate_sampling_for_thinking(thinking)
            request_params["thinking"] = copy.deepcopy(thinking)

        # Convert tools first so we know whether tools are present
        anthropic_tools = self._convert_openai_tools_to_anthropic(tools)

        extra_body = copy.deepcopy(
            self.model_config_dict.get("extra_body") or {}
        )
        output_config = self._build_request_output_config(
            response_format, extra_body
        )
        if output_config:
            request_params["output_config"] = output_config
        if extra_body:
            request_params["extra_body"] = extra_body

        if anthropic_tools:
            request_params["tools"] = anthropic_tools
            tool_choice = self.model_config_dict.get("tool_choice")
            if tool_choice is not None:
                self._validate_tool_choice_for_thinking(thinking, tool_choice)
                request_params["tool_choice"] = tool_choice

        create_func = self._async_client.messages.create

        # Check if streaming
        is_streaming = self.model_config_dict.get("stream", False)

        if is_streaming:
            # Return streaming response
            stream = await self._acall_client(
                create_func,
                **request_params,
                stream=True,
            )
            return self._wrap_anthropic_async_stream(
                stream, str(self.model_type)
            )
        else:
            # Return non-streaming response
            response = await self._acall_client(create_func, **request_params)
            return self._convert_anthropic_to_openai_response(
                response, str(self.model_type)
            )

    def _wrap_anthropic_stream(
        self,
        stream: Any,
        model: str,
    ) -> Stream[ChatCompletionChunk]:
        r"""Wrap Anthropic streaming response to OpenAI Stream format.

        Args:
            stream: The streaming response from Anthropic API.
            model (str): The model name.

        Returns:
            Stream[ChatCompletionChunk]: Stream in OpenAI format.
        """

        def _generate_chunks():
            tool_call_index: Dict[str, int] = {}
            thinking_state: Dict[str, Any] = {}
            finish_reason_sent = False
            for chunk in stream:
                converted = self._convert_anthropic_stream_to_openai_chunk(
                    chunk,
                    model,
                    tool_call_index,
                    finish_reason_sent,
                    thinking_state,
                )
                # Track if we've sent a finish_reason to avoid duplicates
                if converted.choices:
                    choice = converted.choices[0]
                    fr = (
                        choice.get("finish_reason")
                        if isinstance(choice, dict)
                        else getattr(choice, "finish_reason", None)
                    )
                    if fr is not None:
                        finish_reason_sent = True
                yield converted

        return cast(Stream[ChatCompletionChunk], _generate_chunks())

    def _wrap_anthropic_async_stream(
        self,
        stream: Any,
        model: str,
    ) -> AsyncStream[ChatCompletionChunk]:
        r"""Wrap Anthropic async streaming response to OpenAI AsyncStream.

        Args:
            stream: The async streaming response from Anthropic API.
            model (str): The model name.

        Returns:
            AsyncStream[ChatCompletionChunk]: AsyncStream in OpenAI format.
        """

        async def _generate_chunks():
            tool_call_index: Dict[str, int] = {}
            thinking_state: Dict[str, Any] = {}
            finish_reason_sent = False
            async for chunk in stream:
                converted = self._convert_anthropic_stream_to_openai_chunk(
                    chunk,
                    model,
                    tool_call_index,
                    finish_reason_sent,
                    thinking_state,
                )
                # Track if we've sent a finish_reason to avoid duplicates
                if converted.choices:
                    choice = converted.choices[0]
                    fr = (
                        choice.get("finish_reason")
                        if isinstance(choice, dict)
                        else getattr(choice, "finish_reason", None)
                    )
                    if fr is not None:
                        finish_reason_sent = True
                yield converted

        return cast(AsyncStream[ChatCompletionChunk], _generate_chunks())

    @property
    def stream(self) -> bool:
        r"""Returns whether the model is in stream mode, which sends partial
        results each time.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)
