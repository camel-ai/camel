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
import json
import os
import time
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Type,
    Union,
)

from openai import AsyncStream, Stream
from pydantic import BaseModel

from camel.configs import XAIConfig
from camel.logger import get_logger
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
    api_keys_required,
)

if TYPE_CHECKING:
    from xai_sdk import (
        AsyncClient as XAIAsyncClient,  # type: ignore[import-untyped]
    )
    from xai_sdk import Client as XAIClient  # type: ignore[import-untyped]
    from xai_sdk.chat import (  # type: ignore[import-untyped]
        Response as XAIResponse,
    )
    from xai_sdk.proto import chat_pb2  # type: ignore[import-untyped]

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

# Map xAI SDK finish reason enum names to OpenAI-style strings.
_FINISH_REASON_MAP = {
    "REASON_STOP": "stop",
    "REASON_TOOL_CALLS": "tool_calls",
    "REASON_MAX_LEN": "length",
    "REASON_MAX_CONTEXT": "length",
    "REASON_TIME_LIMIT": "length",
}


class XAIModel(BaseModelBackend):
    r"""xAI native SDK model backend using gRPC.

    This backend uses the ``xai_sdk`` package to communicate with xAI's API
    via gRPC, providing access to Grok models with native features like
    encrypted thinking content and server-side conversation storage.

    Args:
        model_type (Union[ModelType, str]): Model for which a backend is
            created, one of the Grok series (e.g. ``"grok-3"``).
        model_config_dict (Optional[Dict[str, Any]], optional): A dictionary
            of configuration parameters. If :obj:`None`,
            :obj:`XAIConfig().as_dict()` will be used.
            (default: :obj:`None`)
        api_key (Optional[str], optional): The API key for authenticating with
            the xAI service. Falls back to the ``XAI_API_KEY`` environment
            variable. (default: :obj:`None`)
        url (Optional[str], optional): Not used for native SDK (gRPC), kept
            for interface compatibility. (default: :obj:`None`)
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
    """

    @api_keys_required(
        [
            ("api_key", "XAI_API_KEY"),
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
            model_config_dict = XAIConfig().as_dict()

        api_key = api_key or os.environ.get("XAI_API_KEY")
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

        self._client: Optional["XAIClient"] = None
        self._async_client: Optional["XAIAsyncClient"] = None

        # Store the last encrypted content for multi-turn reasoning
        self._last_encrypted_content: Optional[str] = None
        self._last_reasoning_content: Optional[str] = None

        # Conversation chaining state: use previous_response_id to avoid
        # resending full history on every turn.
        self._previous_response_id: Optional[str] = None
        self._last_message_count: int = 0

    @property
    def client(self) -> "XAIClient":
        r"""Lazy-initialize the synchronous xAI SDK client."""
        if self._client is None:
            from xai_sdk import Client

            self._client = Client(
                api_key=self._api_key,
                timeout=self._timeout,
            )
        return self._client

    @property
    def async_client(self) -> "XAIAsyncClient":
        r"""Lazy-initialize the asynchronous xAI SDK client."""
        if self._async_client is None:
            from xai_sdk import AsyncClient

            self._async_client = AsyncClient(
                api_key=self._api_key,
                timeout=self._timeout,
            )
        return self._async_client

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
        r"""Returns whether the model is in stream mode.

        Returns:
            bool: Whether the model is in stream mode.
        """
        return self.model_config_dict.get("stream", False)

    # ------------------------------------------------------------------
    # Message conversion: OpenAI format -> xAI SDK format
    # ------------------------------------------------------------------

    def _convert_openai_tool_to_xai(
        self,
        tool: Dict[str, Any],
    ) -> "chat_pb2.Tool":
        r"""Convert an OpenAI-format tool dict to xAI SDK Tool proto.

        Args:
            tool: OpenAI-format tool dict with ``type`` and ``function`` keys.

        Returns:
            chat_pb2.Tool: The xAI SDK tool proto.
        """
        from xai_sdk.proto import chat_pb2

        func = tool.get("function", {})
        parameters = func.get("parameters", {})
        if isinstance(parameters, dict):
            parameters = json.dumps(parameters)
        return chat_pb2.Tool(
            function=chat_pb2.Function(
                name=func.get("name", ""),
                description=func.get("description", ""),
                parameters=parameters,
            )
        )

    def _convert_messages(
        self,
        messages: List[OpenAIMessage],
    ) -> List[Any]:
        r"""Convert OpenAI-format messages to xAI SDK message objects.

        Handles system, user, assistant (with/without tool calls), and tool
        result messages.  For assistant messages that carry reasoning or
        encrypted content (stored from a previous response), those fields are
        injected into the protobuf message so xAI can reconstruct the
        reasoning chain.

        Args:
            messages: List of OpenAI-format message dicts.

        Returns:
            List of ``chat_pb2.Message`` objects ready for ``chat.append()``.
        """
        from xai_sdk.chat import (
            assistant as xai_assistant,
        )
        from xai_sdk.chat import (
            system as xai_system,
        )
        from xai_sdk.chat import (
            text as xai_text,
        )
        from xai_sdk.chat import (
            tool_result as xai_tool_result,
        )
        from xai_sdk.chat import (
            user as xai_user,
        )
        from xai_sdk.proto import chat_pb2

        converted: List[chat_pb2.Message] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "") or ""
            if isinstance(content, list):
                # Handle multi-part content - extract text parts
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts)

            if role == "system":
                converted.append(xai_system(content))

            elif role == "user":
                converted.append(xai_user(content))

            elif role == "assistant":
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    # Build an assistant message with tool calls via proto
                    xai_tool_calls = []
                    for tc in tool_calls:  # type: ignore[attr-defined]
                        func_data = tc.get("function", {})
                        arguments = func_data.get("arguments", "{}")
                        if not isinstance(arguments, str):
                            arguments = json.dumps(
                                arguments, ensure_ascii=False
                            )
                        xai_tool_calls.append(
                            chat_pb2.ToolCall(
                                id=tc.get("id", ""),
                                function=chat_pb2.FunctionCall(
                                    name=func_data.get("name", ""),
                                    arguments=arguments,
                                ),
                            )
                        )
                    proto_msg = chat_pb2.Message(
                        role=chat_pb2.MessageRole.ROLE_ASSISTANT,
                        content=[xai_text(content)] if content else [],
                        tool_calls=xai_tool_calls,
                    )
                    # Inject reasoning/encrypted content if present
                    reasoning = msg.get("reasoning_content", "")
                    encrypted = msg.get("encrypted_content", "")
                    if reasoning:
                        proto_msg.reasoning_content = reasoning
                    if encrypted:
                        proto_msg.encrypted_content = encrypted
                    converted.append(proto_msg)
                else:
                    proto_msg = xai_assistant(content)
                    # Inject reasoning/encrypted content if present
                    reasoning = msg.get("reasoning_content", "")
                    encrypted = msg.get("encrypted_content", "")
                    if reasoning:
                        proto_msg.reasoning_content = reasoning
                    if encrypted:
                        proto_msg.encrypted_content = encrypted
                    converted.append(proto_msg)

            elif role == "tool":
                tool_call_id = msg.get("tool_call_id", "")
                converted.append(
                    xai_tool_result(content, tool_call_id=tool_call_id)
                )

            else:
                raise ValueError(f"Unsupported message role: {role!r}")

        return converted

    # ------------------------------------------------------------------
    # Response conversion: xAI SDK -> OpenAI ChatCompletion
    # ------------------------------------------------------------------

    @staticmethod
    def _map_finish_reason(xai_reason: str) -> str:
        r"""Map xAI finish reason enum name to OpenAI-style string."""
        return _FINISH_REASON_MAP.get(xai_reason, "stop")

    def _xai_response_to_chat_completion(
        self,
        response: "XAIResponse",
    ) -> ChatCompletion:
        r"""Convert an xAI SDK Response to an OpenAI ChatCompletion.

        Preserves reasoning_content and encrypted_content from the response
        for downstream consumers and for injection into future requests.

        Args:
            response: The xAI SDK Response object.

        Returns:
            ChatCompletion: The OpenAI-compatible completion object.
        """
        from openai.types.chat.chat_completion import Choice
        from openai.types.chat.chat_completion_message import (
            ChatCompletionMessage,
        )
        from openai.types.completion_usage import CompletionUsage

        # Build tool_calls list if present
        tool_calls_list = None
        if response.tool_calls:
            from openai.types.chat.chat_completion_message_tool_call import (
                ChatCompletionMessageToolCall,
                Function,
            )

            tool_calls_list = []
            for tc in response.tool_calls:
                tool_calls_list.append(
                    ChatCompletionMessageToolCall(
                        id=tc.id,
                        type="function",
                        function=Function(
                            name=tc.function.name,
                            arguments=tc.function.arguments,
                        ),
                    )
                )

        message = ChatCompletionMessage(
            role="assistant",
            content=response.content or None,
            tool_calls=tool_calls_list,  # type: ignore[arg-type]
        )

        # Attach reasoning_content if available
        reasoning = response.reasoning_content
        if reasoning:
            message.reasoning_content = reasoning  # type: ignore[attr-defined]

        # Store encrypted content for future multi-turn requests
        encrypted = response.encrypted_content
        if encrypted:
            self._last_encrypted_content = encrypted
        if reasoning:
            self._last_reasoning_content = reasoning

        finish_reason = self._map_finish_reason(response.finish_reason)

        choice = Choice(
            index=0,
            message=message,
            finish_reason=finish_reason,  # type: ignore[arg-type]
        )

        # Build usage
        usage = None
        if response.usage:
            u = response.usage
            usage = CompletionUsage(
                prompt_tokens=u.prompt_tokens,
                completion_tokens=u.completion_tokens,
                total_tokens=u.total_tokens,
            )
            # Attach reasoning tokens if available
            if u.reasoning_tokens:
                usage.reasoning_tokens = u.reasoning_tokens  # type: ignore[attr-defined]

        return ChatCompletion.construct(
            id=response.id or "",
            choices=[choice],
            created=int(time.time()),
            model=str(self.model_type),
            object="chat.completion",
            usage=usage,
        )

    # ------------------------------------------------------------------
    # Streaming conversion: xAI SDK -> ChatCompletionChunk generators
    # ------------------------------------------------------------------

    @staticmethod
    def _make_chunk(
        chunk_id: str,
        model: str,
        delta_content: Optional[str] = None,
        delta_reasoning: Optional[str] = None,
        delta_tool_calls: Optional[List[Any]] = None,
        finish_reason: Optional[str] = None,
        usage: Any = None,
    ) -> ChatCompletionChunk:
        r"""Build a ``ChatCompletionChunk`` with proper pydantic objects."""
        from openai.types.chat.chat_completion_chunk import (
            Choice as ChunkChoice,
        )
        from openai.types.chat.chat_completion_chunk import (
            ChoiceDelta,
        )

        delta = ChoiceDelta(
            role="assistant",
            content=delta_content,
            tool_calls=delta_tool_calls,
        )
        # Attach reasoning_content as extra attribute if present
        if delta_reasoning is not None:
            delta.reasoning_content = delta_reasoning  # type: ignore[attr-defined]

        choice = ChunkChoice(
            index=0,
            delta=delta,
            finish_reason=finish_reason,  # type: ignore[arg-type]
        )
        return ChatCompletionChunk.construct(
            id=chunk_id,
            choices=[choice],
            created=int(time.time()),
            model=model,
            object="chat.completion.chunk",
            usage=usage,
        )

    def _build_delta_tool_calls(self, tool_calls: Sequence) -> List[Any]:
        r"""Convert xAI tool calls to ChoiceDeltaToolCall objects."""
        from openai.types.chat.chat_completion_chunk import (
            ChoiceDeltaToolCall,
            ChoiceDeltaToolCallFunction,
        )

        return [
            ChoiceDeltaToolCall(
                index=i,
                id=tc.id,
                type="function",
                function=ChoiceDeltaToolCallFunction(
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ),
            )
            for i, tc in enumerate(tool_calls)
        ]

    def _stream_to_chunks(
        self,
        stream_iter,
        total_messages: int = 0,
    ) -> Generator[ChatCompletionChunk, None, None]:
        r"""Convert xAI SDK stream iterator to ChatCompletionChunk generator.

        Args:
            stream_iter: Iterator from ``chat.stream()`` yielding
                ``(Response, Chunk)`` tuples.
            total_messages: Total message count for chain state bookkeeping.

        Yields:
            ChatCompletionChunk: OpenAI-compatible streaming chunks.
        """
        chunk_id = ""
        model = str(self.model_type)
        for response, chunk in stream_iter:
            chunk_id = chunk_id or (response.id if response.id else "")

            finish_reason = None
            if response.finish_reason and response.finish_reason not in (
                "REASON_INVALID",
                "",
            ):
                finish_reason = self._map_finish_reason(response.finish_reason)

            delta_tc = (
                self._build_delta_tool_calls(chunk.tool_calls)
                if chunk.tool_calls
                else None
            )

            yield self._make_chunk(
                chunk_id=chunk_id,
                model=model,
                delta_content=chunk.content or None,
                delta_reasoning=chunk.reasoning_content or None,
                delta_tool_calls=delta_tc,
                finish_reason=finish_reason,
            )

        # After stream ends, store state from the accumulated response
        if response:
            encrypted = response.encrypted_content
            reasoning = response.reasoning_content
            if encrypted:
                self._last_encrypted_content = encrypted
            if reasoning:
                self._last_reasoning_content = reasoning
            self._save_response_chain(response.id, total_messages)

            if response.usage:
                u = response.usage
                from openai.types.completion_usage import CompletionUsage

                yield self._make_chunk(
                    chunk_id=chunk_id,
                    model=model,
                    finish_reason=self._map_finish_reason(
                        response.finish_reason
                    ),
                    usage=CompletionUsage(
                        prompt_tokens=u.prompt_tokens,
                        completion_tokens=u.completion_tokens,
                        total_tokens=u.total_tokens,
                    ),
                )

    async def _astream_to_chunks(
        self,
        stream_iter,
        total_messages: int = 0,
    ) -> AsyncGenerator[ChatCompletionChunk, None]:
        r"""Async version of stream-to-chunks conversion.

        Args:
            stream_iter: Async iterator from ``chat.stream()`` yielding
                ``(Response, Chunk)`` tuples.
            total_messages: Total message count for chain state bookkeeping.

        Yields:
            ChatCompletionChunk: OpenAI-compatible streaming chunks.
        """
        chunk_id = ""
        model = str(self.model_type)
        response = None
        async for resp, chunk in stream_iter:
            response = resp
            chunk_id = chunk_id or (response.id if response.id else "")

            finish_reason = None
            if response.finish_reason and response.finish_reason not in (
                "REASON_INVALID",
                "",
            ):
                finish_reason = self._map_finish_reason(response.finish_reason)

            delta_tc = (
                self._build_delta_tool_calls(chunk.tool_calls)
                if chunk.tool_calls
                else None
            )

            yield self._make_chunk(
                chunk_id=chunk_id,
                model=model,
                delta_content=chunk.content or None,
                delta_reasoning=chunk.reasoning_content or None,
                delta_tool_calls=delta_tc,
                finish_reason=finish_reason,
            )

        if response is not None:
            encrypted = response.encrypted_content
            reasoning = response.reasoning_content
            if encrypted:
                self._last_encrypted_content = encrypted
            if reasoning:
                self._last_reasoning_content = reasoning
            self._save_response_chain(response.id, total_messages)

            if response.usage:
                u = response.usage
                from openai.types.completion_usage import CompletionUsage

                yield self._make_chunk(
                    chunk_id=chunk_id,
                    model=model,
                    finish_reason=self._map_finish_reason(
                        response.finish_reason
                    ),
                    usage=CompletionUsage(
                        prompt_tokens=u.prompt_tokens,
                        completion_tokens=u.completion_tokens,
                        total_tokens=u.total_tokens,
                    ),
                )

    # ------------------------------------------------------------------
    # Chat session creation helpers
    # ------------------------------------------------------------------

    def _build_chat_kwargs(
        self,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        r"""Build keyword arguments for ``client.chat.create()``.

        Translates the CAMEL model config dict into xAI SDK create
        parameters, and converts OpenAI-format tools to xAI Tool protos.

        Args:
            tools: Optional list of OpenAI-format tool dicts.

        Returns:
            Dict of keyword arguments for ``client.chat.create()``.
        """
        kwargs: Dict[str, Any] = {
            "model": str(self.model_type),
        }

        config = self.model_config_dict

        # Simple passthrough parameters
        for key in (
            "temperature",
            "top_p",
            "max_tokens",
            "seed",
            "frequency_penalty",
            "presence_penalty",
        ):
            val = config.get(key)
            if val is not None:
                kwargs[key] = val

        # Stop sequences
        stop = config.get("stop")
        if stop is not None:
            if isinstance(stop, str):
                stop = [stop]
            kwargs["stop"] = stop

        # xAI-specific parameters
        use_encrypted = config.get("use_encrypted_content")
        if use_encrypted is not None:
            kwargs["use_encrypted_content"] = use_encrypted

        store = config.get("store_messages")
        if store is not None:
            kwargs["store_messages"] = store
        else:
            # Default to True to enable conversation chaining
            kwargs["store_messages"] = True

        # Reasoning effort - xAI SDK accepts string literals "low" / "high"
        reasoning_effort = config.get("reasoning_effort")
        if reasoning_effort is not None:
            kwargs["reasoning_effort"] = reasoning_effort.lower()

        # Response format (structured outputs)
        response_format = config.get("response_format")
        if response_format is not None and isinstance(response_format, type):
            if issubclass(response_format, BaseModel):
                kwargs["response_format"] = response_format

        # Tool choice - xAI SDK accepts string literals
        # "auto", "none", "required"
        tool_choice = config.get("tool_choice")
        if tool_choice is not None and tools:
            if isinstance(tool_choice, str):
                kwargs["tool_choice"] = tool_choice.lower()

        # Convert tools
        if tools:
            kwargs["tools"] = [
                self._convert_openai_tool_to_xai(t) for t in tools
            ]

        return kwargs

    def _compute_delta_messages(
        self,
        messages: List[OpenAIMessage],
    ) -> List[OpenAIMessage]:
        r"""Compute the delta messages for conversation chaining.

        If we have a ``previous_response_id`` from the last turn, only the
        new messages since then need to be sent.  If the conversation was
        truncated (memory reset / context-window management), fall back to
        sending the full history.

        Args:
            messages: The full conversation history from ChatAgent.

        Returns:
            The messages to actually send in this request.
        """
        n = len(messages)

        if self._previous_response_id and n >= self._last_message_count:
            delta = messages[self._last_message_count :]
            if delta:
                # The first message in the delta may be an assistant message
                # that echoes the previous response (already known to the
                # server via previous_response_id).  Sending it again
                # duplicates the assistant turn on the server side and
                # confuses the model into repeating tool calls infinitely.
                if delta[0].get("role") == "assistant":
                    delta = delta[1:]
                if delta:
                    return delta

        # Fallback: reset chain, send everything
        self._previous_response_id = None
        self._last_message_count = 0
        return messages

    def _save_response_chain(
        self, response_id: Optional[str], total_messages: int
    ) -> None:
        r"""Persist the chain state after a successful response."""
        if response_id:
            self._previous_response_id = response_id
        self._last_message_count = total_messages

    def _inject_encrypted_content(
        self,
        messages: List[OpenAIMessage],
    ) -> List[OpenAIMessage]:
        r"""Inject stored encrypted/reasoning content into conversation
        history for multi-turn reasoning.

        When ``use_encrypted_content`` is enabled, the encrypted thinking
        traces from the previous response must be included in the assistant
        message of the conversation history so xAI can reconstruct the
        reasoning chain.

        Args:
            messages: The original OpenAI-format messages.

        Returns:
            Messages with encrypted content injected into the last assistant
            message.
        """
        if (
            not self._last_encrypted_content
            and not self._last_reasoning_content
        ):
            return messages

        # Find the last assistant message and inject content
        processed = list(messages)
        for i in range(len(processed) - 1, -1, -1):
            msg = processed[i]
            if msg.get("role") == "assistant":
                new_msg = dict(msg)
                if (
                    self._last_encrypted_content
                    and "encrypted_content" not in new_msg
                ):
                    new_msg["encrypted_content"] = self._last_encrypted_content
                if (
                    self._last_reasoning_content
                    and "reasoning_content" not in new_msg
                ):
                    new_msg["reasoning_content"] = self._last_reasoning_content
                processed[i] = new_msg  # type: ignore[call-overload]
                break

        # Clear after injection
        self._last_encrypted_content = None
        self._last_reasoning_content = None

        return processed

    def _prepare_chat(
        self,
        messages: List[OpenAIMessage],
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Type[BaseModel]] = None,
    ) -> tuple:
        r"""Shared setup for ``_run`` and ``_arun``.

        Returns:
            (chat_kwargs, messages_to_send, total_message_count)
        """
        messages = self._inject_encrypted_content(messages)
        total = len(messages)

        chat_kwargs = self._build_chat_kwargs(tools)

        if response_format:
            chat_kwargs["response_format"] = response_format
        elif self.model_config_dict.get("response_format") and isinstance(
            self.model_config_dict["response_format"], type
        ):
            chat_kwargs["response_format"] = self.model_config_dict[
                "response_format"
            ]

        # Conversation chaining: send only delta when possible
        store_enabled = chat_kwargs.get("store_messages", True)
        if store_enabled:
            messages_to_send = self._compute_delta_messages(messages)
            if self._previous_response_id:
                chat_kwargs["previous_response_id"] = (
                    self._previous_response_id
                )
        else:
            messages_to_send = messages

        return chat_kwargs, messages_to_send, total

    def _handle_response(
        self,
        response: "XAIResponse",
        total_messages: int,
    ) -> ChatCompletion:
        r"""Convert response and update chain state."""
        store_enabled = (
            self.model_config_dict.get("store_messages", None) is not False
        )
        if store_enabled:
            self._save_response_chain(response.id, total_messages)

        return self._xai_response_to_chat_completion(response)

    # ------------------------------------------------------------------
    # Core run methods
    # ------------------------------------------------------------------

    @observe()
    def _run(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, Stream[ChatCompletionChunk]]:
        r"""Runs inference using the xAI native SDK.

        Uses ``previous_response_id`` to chain conversations on xAI's
        server, sending only new (delta) messages instead of the full
        history on subsequent turns.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, Stream[ChatCompletionChunk]]:
                ``ChatCompletion`` in non-stream mode, or a
                ``ChatCompletionChunk`` generator in stream mode.
        """
        self._log_and_trace()

        chat_kwargs, messages_to_send, total = self._prepare_chat(
            messages, tools, response_format
        )

        # Sync request log with the actual payload sent to xAI
        self._sync_request_log_with_client_kwargs(
            {
                "messages": messages_to_send,
                "model": str(self.model_type),
                "previous_response_id": chat_kwargs.get(
                    "previous_response_id"
                ),
            }
        )

        chat = self.client.chat.create(**chat_kwargs)

        xai_messages = self._convert_messages(messages_to_send)
        for msg in xai_messages:
            chat.append(msg)

        if self.stream:
            return self._stream_to_chunks(chat.stream(), total)  # type: ignore[return-value]

        response = chat.sample()
        return self._handle_response(response, total)

    @observe()
    async def _arun(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
        r"""Runs async inference using the xAI native SDK.

        Args:
            messages (List[OpenAIMessage]): Message list with the chat history
                in OpenAI API format.
            response_format (Optional[Type[BaseModel]]): The format of the
                response.
            tools (Optional[List[Dict[str, Any]]]): The schema of the tools to
                use for the request.

        Returns:
            Union[ChatCompletion, AsyncStream[ChatCompletionChunk]]:
                ``ChatCompletion`` in non-stream mode, or an async
                ``ChatCompletionChunk`` generator in stream mode.
        """
        self._log_and_trace()

        chat_kwargs, messages_to_send, total = self._prepare_chat(
            messages, tools, response_format
        )

        # Sync request log with the actual payload sent to xAI
        self._sync_request_log_with_client_kwargs(
            {
                "messages": messages_to_send,
                "model": str(self.model_type),
                "previous_response_id": chat_kwargs.get(
                    "previous_response_id"
                ),
            }
        )

        chat = self.async_client.chat.create(**chat_kwargs)

        xai_messages = self._convert_messages(messages_to_send)
        for msg in xai_messages:
            chat.append(msg)

        if self.stream:
            return self._astream_to_chunks(  # type: ignore[return-value]
                await chat.stream(), total
            )

        response = await chat.sample()
        return self._handle_response(response, total)
