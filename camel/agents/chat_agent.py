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
from __future__ import annotations

import asyncio
import json
import logging
import queue
import textwrap
import threading
import time
import uuid
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)

from openai import (
    AsyncStream,
    Stream,
)
from pydantic import BaseModel, ValidationError

from camel.agents._types import ModelResponse, ToolCallRequest
from camel.agents._utils import (
    convert_to_function_tool,
    convert_to_schema,
    get_info_dict,
    handle_logprobs,
    safe_model_dump,
)
from camel.agents.base import BaseAgent
from camel.logger import get_logger
from camel.memories import (
    AgentMemory,
    ChatHistoryMemory,
    MemoryRecord,
    ScoreBasedContextCreator,
)
from camel.messages import (
    BaseMessage,
    FunctionCallingMessage,
    OpenAIMessage,
)
from camel.models import (
    BaseModelBackend,
    ModelFactory,
    ModelManager,
    ModelProcessingError,
)
from camel.prompts import TextPrompt
from camel.responses import ChatAgentResponse
from camel.storages import JsonStorage
from camel.toolkits import FunctionTool
from camel.types import (
    ChatCompletion,
    ChatCompletionChunk,
    ModelPlatformType,
    ModelType,
    OpenAIBackendRole,
    RoleType,
)
from camel.types.agents import ToolCallingRecord
from camel.utils import (
    get_model_encoding,
    model_from_json_schema,
)
from camel.utils.commons import dependencies_required
from camel.utils.tool_result import ToolResult

if TYPE_CHECKING:
    from camel.terminators import ResponseTerminator

logger = get_logger(__name__)

# AgentOps decorator setting
try:
    import os

    if os.getenv("AGENTOPS_API_KEY") is not None:
        from agentops import track_agent
    else:
        raise ImportError
except (ImportError, AttributeError):
    from camel.utils import track_agent

# Langfuse decorator setting
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


SIMPLE_FORMAT_PROMPT = TextPrompt(
    textwrap.dedent(
        """\
        Please format the following content:
        
        {content}
        """
    )
)


class StreamContentAccumulator:
    r"""Manages content accumulation across streaming responses to ensure
    all responses contain complete cumulative content."""

    def __init__(self):
        self.base_content = ""  # Content before tool calls
        self.current_content = ""  # Current streaming content
        self.tool_status_messages = []  # Accumulated tool status messages

    def set_base_content(self, content: str):
        r"""Set the base content (usually empty or pre-tool content)."""
        self.base_content = content

    def add_streaming_content(self, new_content: str):
        r"""Add new streaming content."""
        self.current_content += new_content

    def add_tool_status(self, status_message: str):
        r"""Add a tool status message."""
        self.tool_status_messages.append(status_message)

    def get_full_content(self) -> str:
        r"""Get the complete accumulated content."""
        tool_messages = "".join(self.tool_status_messages)
        return self.base_content + tool_messages + self.current_content

    def get_content_with_new_status(self, status_message: str) -> str:
        r"""Get content with a new status message appended."""
        tool_messages = "".join([*self.tool_status_messages, status_message])
        return self.base_content + tool_messages + self.current_content

    def reset_streaming_content(self):
        r"""Reset only the streaming content, keep base and tool status."""
        self.current_content = ""


class StreamingChatAgentResponse:
    r"""A wrapper that makes streaming responses compatible with
    non-streaming code.

    This class wraps a Generator[ChatAgentResponse, None, None] and provides
    the same interface as ChatAgentResponse, so existing code doesn't need to
    change.
    """

    def __init__(self, generator: Generator[ChatAgentResponse, None, None]):
        self._generator = generator
        self._current_response: Optional[ChatAgentResponse] = None
        self._responses: List[ChatAgentResponse] = []
        self._consumed = False

    def _ensure_latest_response(self):
        r"""Ensure we have the latest response by consuming the generator."""
        if not self._consumed:
            try:
                for response in self._generator:
                    self._responses.append(response)
                    self._current_response = response
                self._consumed = True
            except StopIteration:
                self._consumed = True

    @property
    def msgs(self) -> List[BaseMessage]:
        r"""Get messages from the latest response."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.msgs
        return []

    @property
    def terminated(self) -> bool:
        r"""Get terminated status from the latest response."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.terminated
        return False

    @property
    def info(self) -> Dict[str, Any]:
        r"""Get info from the latest response."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.info
        return {}

    @property
    def msg(self):
        r"""Get the single message if there's exactly one message."""
        self._ensure_latest_response()
        if self._current_response:
            return self._current_response.msg
        return None

    def __iter__(self):
        r"""Make this object iterable."""
        if self._consumed:
            # If already consumed, iterate over stored responses
            return iter(self._responses)
        else:
            # If not consumed, consume and yield
            try:
                for response in self._generator:
                    self._responses.append(response)
                    self._current_response = response
                    yield response
                self._consumed = True
            except StopIteration:
                self._consumed = True

    def __getattr__(self, name):
        r"""Forward any other attribute access to the latest response."""
        self._ensure_latest_response()
        if self._current_response and hasattr(self._current_response, name):
            return getattr(self._current_response, name)
        raise AttributeError(
            f"'StreamingChatAgentResponse' object has no attribute '{name}'"
        )


class AsyncStreamingChatAgentResponse:
    r"""A wrapper that makes async streaming responses awaitable and
    compatible with non-streaming code.

    This class wraps an AsyncGenerator[ChatAgentResponse, None] and provides
    both awaitable and async iterable interfaces.
    """

    def __init__(
        self, async_generator: AsyncGenerator[ChatAgentResponse, None]
    ):
        self._async_generator = async_generator
        self._current_response: Optional[ChatAgentResponse] = None
        self._responses: List[ChatAgentResponse] = []
        self._consumed = False

    async def _ensure_latest_response(self):
        r"""Ensure the latest response by consuming the async generator."""
        if not self._consumed:
            try:
                async for response in self._async_generator:
                    self._responses.append(response)
                    self._current_response = response
                self._consumed = True
            except StopAsyncIteration:
                self._consumed = True

    async def _get_final_response(self) -> ChatAgentResponse:
        r"""Get the final response after consuming the entire stream."""
        await self._ensure_latest_response()
        if self._current_response:
            return self._current_response
        # Return a default response if nothing was consumed
        return ChatAgentResponse(msgs=[], terminated=False, info={})

    def __await__(self):
        r"""Make this object awaitable - returns the final response."""
        return self._get_final_response().__await__()

    def __aiter__(self):
        r"""Make this object async iterable."""
        if self._consumed:
            # If already consumed, create async iterator from stored responses
            async def _async_iter():
                for response in self._responses:
                    yield response

            return _async_iter()
        else:
            # If not consumed, consume and yield
            async def _consume_and_yield():
                try:
                    async for response in self._async_generator:
                        self._responses.append(response)
                        self._current_response = response
                        yield response
                    self._consumed = True
                except StopAsyncIteration:
                    self._consumed = True

            return _consume_and_yield()


@track_agent(name="ChatAgent")
class ChatAgent(BaseAgent):
    r"""Class for managing conversations of CAMEL Chat Agents.

    Args:
        system_message (Union[BaseMessage, str], optional): The system message
            for the chat agent. (default: :obj:`None`)
        model (Union[BaseModelBackend, Tuple[str, str], str, ModelType,
            Tuple[ModelPlatformType, ModelType], List[BaseModelBackend],
            List[str], List[ModelType], List[Tuple[str, str]],
            List[Tuple[ModelPlatformType, ModelType]]], optional):
            The model backend(s) to use. Can be a single instance,
            a specification (string, enum, tuple), or a list of instances
            or specifications to be managed by `ModelManager`. If a list of
            specifications (not `BaseModelBackend` instances) is provided,
            they will be instantiated using `ModelFactory`. (default:
            :obj:`ModelPlatformType.DEFAULT` with `ModelType.DEFAULT`)
        memory (AgentMemory, optional): The agent memory for managing chat
            messages. If `None`, a :obj:`ChatHistoryMemory` will be used.
            (default: :obj:`None`)
        message_window_size (int, optional): The maximum number of previous
            messages to include in the context window. If `None`, no windowing
            is performed. (default: :obj:`None`)
        token_limit (int, optional): The maximum number of tokens in a context.
            The context will be automatically pruned to fulfill the limitation.
            If `None`, it will be set according to the backend model.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agent. (default: :obj:`None`)
        tools (Optional[List[Union[FunctionTool, Callable]]], optional): List
            of available :obj:`FunctionTool` or :obj:`Callable`. (default:
            :obj:`None`)
        external_tools (Optional[List[Union[FunctionTool, Callable,
            Dict[str, Any]]]], optional): List of external tools
            (:obj:`FunctionTool` or :obj:`Callable` or :obj:`Dict[str, Any]`)
            bind to one chat agent. When these tools are called, the agent will
            directly return the request instead of processing it.
            (default: :obj:`None`)
        response_terminators (List[ResponseTerminator], optional): List of
            :obj:`ResponseTerminator` bind to one chat agent.
            (default: :obj:`None`)
        scheduling_strategy (str): name of function that defines how to select
            the next model in ModelManager. (default: :str:`round_robin`)
        max_iteration (Optional[int], optional): Maximum number of model
            calling iterations allowed per step. If `None` (default), there's
            no explicit limit. If `1`, it performs a single model call. If `N
            > 1`, it allows up to N model calls. (default: :obj:`None`)
        agent_id (str, optional): The ID of the agent. If not provided, a
            random UUID will be generated. (default: :obj:`None`)
        stop_event (Optional[threading.Event], optional): Event to signal
            termination of the agent's operation. When set, the agent will
            terminate its execution. (default: :obj:`None`)
        tool_execution_timeout (Optional[float], optional): Timeout
            for individual tool execution. If None, wait indefinitely.
        mask_tool_output (Optional[bool]): Whether to return a sanitized
            placeholder instead of the raw tool output. (default: :obj:`False`)
        pause_event (Optional[asyncio.Event]): Event to signal pause of the
            agent's operation. When clear, the agent will pause its execution.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        system_message: Optional[Union[BaseMessage, str]] = None,
        model: Optional[
            Union[
                BaseModelBackend,
                ModelManager,
                Tuple[str, str],
                str,
                ModelType,
                Tuple[ModelPlatformType, ModelType],
                List[BaseModelBackend],
                List[str],
                List[ModelType],
                List[Tuple[str, str]],
                List[Tuple[ModelPlatformType, ModelType]],
            ]
        ] = None,
        memory: Optional[AgentMemory] = None,
        message_window_size: Optional[int] = None,
        token_limit: Optional[int] = None,
        output_language: Optional[str] = None,
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        external_tools: Optional[
            List[Union[FunctionTool, Callable, Dict[str, Any]]]
        ] = None,
        response_terminators: Optional[List[ResponseTerminator]] = None,
        scheduling_strategy: str = "round_robin",
        max_iteration: Optional[int] = None,
        agent_id: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
        tool_execution_timeout: Optional[float] = None,
        mask_tool_output: bool = False,
        pause_event: Optional[asyncio.Event] = None,
    ) -> None:
        if isinstance(model, ModelManager):
            self.model_backend = model
        else:
            # Resolve model backends and set up model manager
            resolved_models = self._resolve_models(model)
            self.model_backend = ModelManager(
                resolved_models,
                scheduling_strategy=scheduling_strategy,
            )
        self.model_type = self.model_backend.model_type

        # Assign unique ID
        self.agent_id = agent_id if agent_id else str(uuid.uuid4())

        # Set up memory
        context_creator = ScoreBasedContextCreator(
            self.model_backend.token_counter,
            token_limit or self.model_backend.token_limit,
        )

        self.memory: AgentMemory = memory or ChatHistoryMemory(
            context_creator,
            window_size=message_window_size,
            agent_id=self.agent_id,
        )

        # So we don't have to pass agent_id when we define memory
        if memory is not None:
            memory.agent_id = self.agent_id

        # Set up system message and initialize messages
        self._original_system_message = (
            BaseMessage.make_assistant_message(
                role_name="Assistant", content=system_message
            )
            if isinstance(system_message, str)
            else system_message
        )
        self._output_language = output_language
        self._system_message = (
            self._generate_system_message_for_output_language()
        )
        self.init_messages()

        # Set up role name and role type
        self.role_name: str = (
            getattr(self.system_message, "role_name", None) or "assistant"
        )
        self.role_type: RoleType = (
            getattr(self.system_message, "role_type", None)
            or RoleType.ASSISTANT
        )

        # Set up tools
        self._internal_tools = {
            tool.get_function_name(): tool
            for tool in [
                convert_to_function_tool(tool) for tool in (tools or [])
            ]
        }

        self._external_tool_schemas = {
            tool_schema["function"]["name"]: tool_schema
            for tool_schema in [
                convert_to_schema(tool) for tool in (external_tools or [])
            ]
        }

        # Set up other properties
        self.terminated = False
        self.response_terminators = response_terminators or []
        self.max_iteration = max_iteration
        self.stop_event = stop_event
        self.tool_execution_timeout = tool_execution_timeout
        self.mask_tool_output = mask_tool_output
        self._secure_result_store: Dict[str, Any] = {}
        self._pending_images: List[str] = []
        self._image_retry_count: Dict[str, int] = {}
        # Store images to attach to next user message
        self.pause_event = pause_event

    def reset(self):
        r"""Resets the :obj:`ChatAgent` to its initial state."""
        self.terminated = False
        self.init_messages()
        self._pending_images = []
        self._image_retry_count = {}
        for terminator in self.response_terminators:
            terminator.reset()

    def _resolve_models(
        self,
        model: Optional[
            Union[
                BaseModelBackend,
                Tuple[str, str],
                str,
                ModelType,
                Tuple[ModelPlatformType, ModelType],
                List[BaseModelBackend],
                List[str],
                List[ModelType],
                List[Tuple[str, str]],
                List[Tuple[ModelPlatformType, ModelType]],
            ]
        ],
    ) -> Union[BaseModelBackend, List[BaseModelBackend]]:
        r"""Resolves model specifications into model backend instances.

        This method handles various input formats for model specifications and
        returns the appropriate model backend(s).

        Args:
            model: Model specification in various formats including single
                model, list of models, or model type specifications.

        Returns:
            Union[BaseModelBackend, List[BaseModelBackend]]: Resolved model
                backend(s).

        Raises:
            TypeError: If the model specification format is not supported.
        """
        if model is None:
            # Default single model if none provided
            return ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )
        elif isinstance(model, BaseModelBackend):
            # Already a single pre-instantiated model
            return model
        elif isinstance(model, list):
            return self._resolve_model_list(model)
        elif isinstance(model, (ModelType, str)):
            # Single string or ModelType -> use default platform
            model_platform = ModelPlatformType.DEFAULT
            model_type = model
            logger.warning(
                f"Model type '{model_type}' provided without a platform. "
                f"Using platform '{model_platform}'. Note: platform "
                "is not automatically inferred based on model type."
            )
            return ModelFactory.create(
                model_platform=model_platform,
                model_type=model_type,
            )
        elif isinstance(model, tuple) and len(model) == 2:
            # Single tuple (platform, type)
            model_platform, model_type = model  # type: ignore[assignment]
            return ModelFactory.create(
                model_platform=model_platform,
                model_type=model_type,
            )
        else:
            raise TypeError(
                f"Unsupported type for model parameter: {type(model)}"
            )

    def _resolve_model_list(
        self, model_list: list
    ) -> Union[BaseModelBackend, List[BaseModelBackend]]:
        r"""Resolves a list of model specifications into model backend
        instances.

        Args:
            model_list (list): List of model specifications in various formats.

        Returns:
            Union[BaseModelBackend, List[BaseModelBackend]]: Resolved model
                backend(s).

        Raises:
            TypeError: If the list elements format is not supported.
        """
        if not model_list:  # Handle empty list
            logger.warning(
                "Empty list provided for model, using default model."
            )
            return ModelFactory.create(
                model_platform=ModelPlatformType.DEFAULT,
                model_type=ModelType.DEFAULT,
            )
        elif isinstance(model_list[0], BaseModelBackend):
            # List of pre-instantiated models
            return model_list  # type: ignore[return-value]
        elif isinstance(model_list[0], (str, ModelType)):
            # List of strings or ModelTypes -> use default platform
            model_platform = ModelPlatformType.DEFAULT
            logger.warning(
                f"List of model types {model_list} provided without "
                f"platforms. Using platform '{model_platform}' for all. "
                "Note: platform is not automatically inferred based on "
                "model type."
            )
            resolved_models_list = []
            for model_type_item in model_list:
                resolved_models_list.append(
                    ModelFactory.create(
                        model_platform=model_platform,
                        model_type=model_type_item,  # type: ignore[arg-type]
                    )
                )
            return resolved_models_list
        elif isinstance(model_list[0], tuple) and len(model_list[0]) == 2:
            # List of tuples (platform, type)
            resolved_models_list = []
            for model_spec in model_list:
                platform, type_ = (  # type: ignore[index]
                    model_spec[0],
                    model_spec[1],
                )
                resolved_models_list.append(
                    ModelFactory.create(
                        model_platform=platform, model_type=type_
                    )
                )
            return resolved_models_list
        else:
            raise TypeError(
                "Unsupported type for list elements in model: "
                f"{type(model_list[0])}"
            )

    @property
    def system_message(self) -> Optional[BaseMessage]:
        r"""Returns the system message for the agent."""
        return self._system_message

    @property
    def tool_dict(self) -> Dict[str, FunctionTool]:
        r"""Returns a dictionary of internal tools."""
        return self._internal_tools

    @property
    def output_language(self) -> Optional[str]:
        r"""Returns the output language for the agent."""
        return self._output_language

    @output_language.setter
    def output_language(self, value: str) -> None:
        r"""Set the output language for the agent.

        Note that this will clear the message history.
        """
        self._output_language = value
        self._system_message = (
            self._generate_system_message_for_output_language()
        )
        self.init_messages()

    def _get_full_tool_schemas(self) -> List[Dict[str, Any]]:
        r"""Returns a list of tool schemas of all tools, including internal
        and external tools.
        """
        return list(self._external_tool_schemas.values()) + [
            func_tool.get_openai_tool_schema()
            for func_tool in self._internal_tools.values()
        ]

    def _get_external_tool_names(self) -> Set[str]:
        r"""Returns a set of external tool names."""
        return set(self._external_tool_schemas.keys())

    def add_tool(self, tool: Union[FunctionTool, Callable]) -> None:
        r"""Add a tool to the agent."""
        new_tool = convert_to_function_tool(tool)
        self._internal_tools[new_tool.get_function_name()] = new_tool

    def add_tools(self, tools: List[Union[FunctionTool, Callable]]) -> None:
        r"""Add a list of tools to the agent."""
        for tool in tools:
            self.add_tool(tool)

    def add_external_tool(
        self, tool: Union[FunctionTool, Callable, Dict[str, Any]]
    ) -> None:
        new_tool_schema = convert_to_schema(tool)
        self._external_tool_schemas[new_tool_schema["name"]] = new_tool_schema

    def remove_tool(self, tool_name: str) -> bool:
        r"""Remove a tool from the agent by name.

        Args:
            tool_name (str): The name of the tool to remove.

        Returns:
            bool: Whether the tool was successfully removed.
        """
        if tool_name in self._internal_tools:
            del self._internal_tools[tool_name]
            return True
        return False

    def remove_tools(self, tool_names: List[str]) -> None:
        r"""Remove a list of tools from the agent by name."""
        for tool_name in tool_names:
            self.remove_tool(tool_name)

    def remove_external_tool(self, tool_name: str) -> bool:
        r"""Remove an external tool from the agent by name.

        Args:
            tool_name (str): The name of the tool to remove.

        Returns:
            bool: Whether the tool was successfully removed.
        """
        if tool_name in self._external_tool_schemas:
            del self._external_tool_schemas[tool_name]
            return True
        return False

    def update_memory(
        self,
        message: BaseMessage,
        role: OpenAIBackendRole,
        timestamp: Optional[float] = None,
    ) -> None:
        r"""Updates the agent memory with a new message.

        If the single *message* exceeds the model's context window, it will
        be **automatically split into multiple smaller chunks** before being
        written into memory. This prevents later failures in
        `ScoreBasedContextCreator` where an over-sized message cannot fit
        into the available token budget at all.

        This slicing logic handles both regular text messages (in the
        `content` field) and long tool call results (in the `result` field of
        a `FunctionCallingMessage`).

        Args:
            message (BaseMessage): The new message to add to the stored
                messages.
            role (OpenAIBackendRole): The backend role type.
            timestamp (Optional[float], optional): Custom timestamp for the
                memory record. If `None`, the current time will be used.
                (default: :obj:`None`)
                    (default: obj:`None`)
        """
        import math
        import time
        import uuid as _uuid

        # 1. Helper to write a record to memory
        def _write_single_record(
            message: BaseMessage, role: OpenAIBackendRole, timestamp: float
        ):
            self.memory.write_record(
                MemoryRecord(
                    message=message,
                    role_at_backend=role,
                    timestamp=timestamp,
                    agent_id=self.agent_id,
                )
            )

        base_ts = (
            timestamp
            if timestamp is not None
            else time.time_ns() / 1_000_000_000
        )

        # 2. Get token handling utilities, fallback if unavailable
        try:
            context_creator = self.memory.get_context_creator()
            token_counter = context_creator.token_counter
            token_limit = context_creator.token_limit
        except AttributeError:
            _write_single_record(message, role, base_ts)
            return

        # 3. Check if slicing is necessary
        try:
            current_tokens = token_counter.count_tokens_from_messages(
                [message.to_openai_message(role)]
            )
            _, ctx_tokens = self.memory.get_context()
            remaining_budget = max(0, token_limit - ctx_tokens)

            if current_tokens <= remaining_budget:
                _write_single_record(message, role, base_ts)
                return
        except Exception as e:
            logger.warning(
                f"Token calculation failed before chunking, "
                f"writing message as-is. Error: {e}"
            )
            _write_single_record(message, role, base_ts)
            return

        # 4. Perform slicing
        logger.warning(
            f"Message with {current_tokens} tokens exceeds remaining budget "
            f"of {remaining_budget}. Slicing into smaller chunks."
        )

        text_to_chunk: Optional[str] = None
        is_function_result = False

        if isinstance(message, FunctionCallingMessage) and isinstance(
            message.result, str
        ):
            text_to_chunk = message.result
            is_function_result = True
        elif isinstance(message.content, str):
            text_to_chunk = message.content

        if not text_to_chunk or not text_to_chunk.strip():
            _write_single_record(message, role, base_ts)
            return
        # Encode the entire text to get a list of all token IDs
        try:
            all_token_ids = token_counter.encode(text_to_chunk)
        except Exception as e:
            logger.error(f"Failed to encode text for chunking: {e}")
            _write_single_record(message, role, base_ts)  # Fallback
            return

        if not all_token_ids:
            _write_single_record(message, role, base_ts)  # Nothing to chunk
            return

        # 1.  Base chunk size: one-tenth of the smaller of (a) total token
        # limit and (b) current remaining budget.  This prevents us from
        # creating chunks that are guaranteed to overflow the
        # immediate context window.
        base_chunk_size = max(1, remaining_budget) // 10

        # 2.  Each chunk gets a textual prefix such as:
        #        "[chunk 3/12 of a long message]\n"
        #     The prefix itself consumes tokens, so if we do not subtract its
        #     length the *total* tokens of the outgoing message (prefix + body)
        #     can exceed the intended bound.  We estimate the prefix length
        #     with a representative example that is safely long enough for the
        #     vast majority of cases (three-digit indices).
        sample_prefix = "[chunk 1/1000 of a long message]\n"
        prefix_token_len = len(token_counter.encode(sample_prefix))

        # 3.  The real capacity for the message body is therefore the base
        #     chunk size minus the prefix length.  Fallback to at least one
        #     token to avoid zero or negative sizes.
        chunk_body_limit = max(1, base_chunk_size - prefix_token_len)

        # 4.  Calculate how many chunks we will need with this body size.
        num_chunks = math.ceil(len(all_token_ids) / chunk_body_limit)
        group_id = str(_uuid.uuid4())

        for i in range(num_chunks):
            start_idx = i * chunk_body_limit
            end_idx = start_idx + chunk_body_limit
            chunk_token_ids = all_token_ids[start_idx:end_idx]

            chunk_body = token_counter.decode(chunk_token_ids)

            prefix = f"[chunk {i + 1}/{num_chunks} of a long message]\n"
            new_body = prefix + chunk_body

            if is_function_result and isinstance(
                message, FunctionCallingMessage
            ):
                new_msg: BaseMessage = FunctionCallingMessage(
                    role_name=message.role_name,
                    role_type=message.role_type,
                    meta_dict=message.meta_dict,
                    content=message.content,
                    func_name=message.func_name,
                    args=message.args,
                    result=new_body,
                    tool_call_id=message.tool_call_id,
                )
            else:
                new_msg = message.create_new_instance(new_body)

            meta = (new_msg.meta_dict or {}).copy()
            meta.update(
                {
                    "chunk_idx": i + 1,
                    "chunk_total": num_chunks,
                    "chunk_group_id": group_id,
                }
            )
            new_msg.meta_dict = meta

            # Increment timestamp slightly to maintain order
            _write_single_record(new_msg, role, base_ts + i * 1e-6)

    def load_memory(self, memory: AgentMemory) -> None:
        r"""Load the provided memory into the agent.

        Args:
            memory (AgentMemory): The memory to load into the agent.

        Returns:
            None
        """

        for context_record in memory.retrieve():
            self.memory.write_record(context_record.memory_record)
        logger.info(f"Memory loaded from {memory}")

    def load_memory_from_path(self, path: str) -> None:
        r"""Loads memory records from a JSON file filtered by this agent's ID.

        Args:
            path (str): The file path to a JSON memory file that uses
                JsonStorage.

        Raises:
            ValueError: If no matching records for the agent_id are found
                (optional check; commented out below).
        """
        json_store = JsonStorage(Path(path))
        all_records = json_store.load()

        if not all_records:
            raise ValueError(
                f"No records found for agent_id={self.agent_id} in {path}"
            )

        for record_dict in all_records:
            # Validate the record dictionary before conversion
            required_keys = ['message', 'role_at_backend', 'agent_id']
            if not all(key in record_dict for key in required_keys):
                logger.warning(
                    f"Skipping invalid record: missing required "
                    f"keys in {record_dict}"
                )
                continue

            # Validate message structure in the record
            if (
                not isinstance(record_dict['message'], dict)
                or '__class__' not in record_dict['message']
            ):
                logger.warning(
                    f"Skipping invalid record: malformed message "
                    f"structure in {record_dict}"
                )
                continue

            try:
                record = MemoryRecord.from_dict(record_dict)
                self.memory.write_records([record])
            except Exception as e:
                logger.warning(
                    f"Error converting record to MemoryRecord: {e}. "
                    f"Record: {record_dict}"
                )
        logger.info(f"Memory loaded from {path}")

    def save_memory(self, path: str) -> None:
        r"""Retrieves the current conversation data from memory and writes it
        into a JSON file using JsonStorage.

        Args:
            path (str): Target file path to store JSON data.
        """
        json_store = JsonStorage(Path(path))
        context_records = self.memory.retrieve()
        to_save = [cr.memory_record.to_dict() for cr in context_records]
        json_store.save(to_save)
        logger.info(f"Memory saved to {path}")

    def clear_memory(self) -> None:
        r"""Clear the agent's memory and reset to initial state.

        Returns:
            None
        """
        self.memory.clear()
        if self.system_message is not None:
            self.update_memory(self.system_message, OpenAIBackendRole.SYSTEM)

    def _generate_system_message_for_output_language(
        self,
    ) -> Optional[BaseMessage]:
        r"""Generate a new system message with the output language prompt.

        The output language determines the language in which the output text
        should be generated.

        Returns:
            BaseMessage: The new system message.
        """
        if not self._output_language:
            return self._original_system_message

        language_prompt = (
            "\nRegardless of the input language, "
            f"you must output text in {self._output_language}."
        )

        if self._original_system_message is not None:
            content = self._original_system_message.content + language_prompt
            return self._original_system_message.create_new_instance(content)
        else:
            return BaseMessage.make_assistant_message(
                role_name="Assistant",
                content=language_prompt,
            )

    def init_messages(self) -> None:
        r"""Initializes the stored messages list with the current system
        message.
        """
        import time

        self.memory.clear()
        # avoid UserWarning: The `ChatHistoryMemory` is empty.
        if self.system_message is not None:
            self.memory.write_record(
                MemoryRecord(
                    message=self.system_message,
                    role_at_backend=OpenAIBackendRole.SYSTEM,
                    timestamp=time.time_ns() / 1_000_000_000,
                    agent_id=self.agent_id,
                )
            )

    def record_message(self, message: BaseMessage) -> None:
        r"""Records the externally provided message into the agent memory as if
        it were an answer of the :obj:`ChatAgent` from the backend. Currently,
        the choice of the critic is submitted with this method.

        Args:
            message (BaseMessage): An external message to be recorded in the
                memory.
        """
        self.update_memory(message, OpenAIBackendRole.ASSISTANT)

    def _try_format_message(
        self, message: BaseMessage, response_format: Type[BaseModel]
    ) -> bool:
        r"""Try to format the message if needed.

        Returns:
            bool: Whether the message is formatted successfully (or no format
                is needed).
        """
        if message.parsed:
            return True

        try:
            message.parsed = response_format.model_validate_json(
                message.content
            )
            return True
        except ValidationError:
            return False

    def _check_tools_strict_compatibility(self) -> bool:
        r"""Check if all tools are compatible with OpenAI strict mode.

        Returns:
            bool: True if all tools are strict mode compatible,
                False otherwise.
        """
        tool_schemas = self._get_full_tool_schemas()
        for schema in tool_schemas:
            if not schema.get("function", {}).get("strict", True):
                return False
        return True

    def _convert_response_format_to_prompt(
        self, response_format: Type[BaseModel]
    ) -> str:
        r"""Convert a Pydantic response format to a prompt instruction.

        Args:
            response_format (Type[BaseModel]): The Pydantic model class.

        Returns:
            str: A prompt instruction requesting the specific format.
        """
        try:
            # Get the JSON schema from the Pydantic model
            schema = response_format.model_json_schema()

            # Create a prompt based on the schema
            format_instruction = (
                "\n\nPlease respond in the following JSON format:\n" "{\n"
            )

            properties = schema.get("properties", {})
            for field_name, field_info in properties.items():
                field_type = field_info.get("type", "string")
                description = field_info.get("description", "")

                if field_type == "array":
                    format_instruction += (
                        f'    "{field_name}": ["array of values"]'
                    )
                elif field_type == "object":
                    format_instruction += f'    "{field_name}": {{"object"}}'
                elif field_type == "boolean":
                    format_instruction += f'    "{field_name}": true'
                elif field_type == "number":
                    format_instruction += f'    "{field_name}": 0'
                else:
                    format_instruction += f'    "{field_name}": "string value"'

                if description:
                    format_instruction += f'  // {description}'

                # Add comma if not the last item
                if field_name != list(properties.keys())[-1]:
                    format_instruction += ","
                format_instruction += "\n"

            format_instruction += "}"
            return format_instruction

        except Exception as e:
            logger.warning(
                f"Failed to convert response_format to prompt: {e}. "
                f"Using generic format instruction."
            )
            return (
                "\n\nPlease respond in a structured JSON format "
                "that matches the requested schema."
            )

    def _handle_response_format_with_non_strict_tools(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Tuple[Union[BaseMessage, str], Optional[Type[BaseModel]], bool]:
        r"""Handle response format when tools are not strict mode compatible.

        Args:
            input_message: The original input message.
            response_format: The requested response format.

        Returns:
            Tuple: (modified_message, modified_response_format,
                   used_prompt_formatting)
        """
        if response_format is None:
            return input_message, response_format, False

        # Check if tools are strict mode compatible
        if self._check_tools_strict_compatibility():
            return input_message, response_format, False

        # Tools are not strict compatible, convert to prompt
        logger.info(
            "Non-strict tools detected. Converting response_format to "
            "prompt-based formatting."
        )

        format_prompt = self._convert_response_format_to_prompt(
            response_format
        )

        # Modify the message to include format instruction
        modified_message: Union[BaseMessage, str]
        if isinstance(input_message, str):
            modified_message = input_message + format_prompt
        else:
            modified_message = input_message.create_new_instance(
                input_message.content + format_prompt
            )

        # Return None for response_format to avoid strict mode conflicts
        # and True to indicate we used prompt formatting
        return modified_message, None, True

    def _apply_prompt_based_parsing(
        self,
        response: ModelResponse,
        original_response_format: Type[BaseModel],
    ) -> None:
        r"""Apply manual parsing when using prompt-based formatting.

        Args:
            response: The model response to parse.
            original_response_format: The original response format class.
        """
        for message in response.output_messages:
            if message.content:
                try:
                    # Try to extract JSON from the response content
                    import json
                    import re

                    from pydantic import ValidationError

                    # Try to find JSON in the content
                    content = message.content.strip()

                    # Try direct parsing first
                    try:
                        parsed_json = json.loads(content)
                        message.parsed = (
                            original_response_format.model_validate(
                                parsed_json
                            )
                        )
                        continue
                    except (json.JSONDecodeError, ValidationError):
                        pass

                    # Try to extract JSON from text
                    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    json_matches = re.findall(json_pattern, content, re.DOTALL)

                    for json_str in json_matches:
                        try:
                            parsed_json = json.loads(json_str)
                            message.parsed = (
                                original_response_format.model_validate(
                                    parsed_json
                                )
                            )
                            # Update content to just the JSON for consistency
                            message.content = json.dumps(parsed_json)
                            break
                        except (json.JSONDecodeError, ValidationError):
                            continue

                    if not message.parsed:
                        logger.warning(
                            f"Failed to parse JSON from response: "
                            f"{content}"
                        )

                except Exception as e:
                    logger.warning(f"Error during prompt-based parsing: {e}")

    def _format_response_if_needed(
        self,
        response: ModelResponse,
        response_format: Optional[Type[BaseModel]] = None,
    ) -> None:
        r"""Format the response if needed.

        This function won't format the response under the following cases:
        1. The response format is None (not provided)
        2. The response is empty
        """
        if response_format is None:
            return

        for message in response.output_messages:
            if self._try_format_message(message, response_format):
                continue

            prompt = SIMPLE_FORMAT_PROMPT.format(content=message.content)
            openai_message: OpenAIMessage = {"role": "user", "content": prompt}
            # Explicitly set the tools to empty list to avoid calling tools
            response = self._get_model_response(
                [openai_message], 0, response_format, []
            )
            message.content = response.output_messages[0].content
            if not self._try_format_message(message, response_format):
                logger.warning(f"Failed to parse response: {message.content}")
                logger.warning(
                    "To improve reliability, consider using models "
                    "that are better equipped to handle structured output"
                )

    async def _aformat_response_if_needed(
        self,
        response: ModelResponse,
        response_format: Optional[Type[BaseModel]] = None,
    ) -> None:
        r"""Format the response if needed."""

        if response_format is None:
            return

        for message in response.output_messages:
            self._try_format_message(message, response_format)
            if message.parsed:
                continue

            prompt = SIMPLE_FORMAT_PROMPT.format(content=message.content)
            openai_message: OpenAIMessage = {"role": "user", "content": prompt}
            response = await self._aget_model_response(
                [openai_message], 0, response_format, []
            )
            message.content = response.output_messages[0].content
            self._try_format_message(message, response_format)

    @observe()
    def step(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Union[ChatAgentResponse, StreamingChatAgentResponse]:
        r"""Executes a single step in the chat session, generating a response
        to the input message.

        Args:
            input_message (Union[BaseMessage, str]): The input message for the
                agent. If provided as a BaseMessage, the `role` is adjusted to
                `user` to indicate an external message.
            response_format (Optional[Type[BaseModel]], optional): A Pydantic
                model defining the expected structure of the response. Used to
                generate a structured response if provided. (default:
                :obj:`None`)

        Returns:
            Union[ChatAgentResponse, StreamingChatAgentResponse]: If stream is
                False, returns a ChatAgentResponse. If stream is True, returns
                a StreamingChatAgentResponse that behaves like
                ChatAgentResponse but can also be iterated for
                streaming updates.
        """

        stream = self.model_backend.model_config_dict.get("stream", False)

        if stream:
            # Return wrapped generator that has ChatAgentResponse interface
            generator = self._stream(input_message, response_format)
            return StreamingChatAgentResponse(generator)

        # Set Langfuse session_id using agent_id for trace grouping
        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

        # Handle response format compatibility with non-strict tools
        original_response_format = response_format
        input_message, response_format, used_prompt_formatting = (
            self._handle_response_format_with_non_strict_tools(
                input_message, response_format
            )
        )

        # Convert input message to BaseMessage if necessary
        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        # Attach any pending images from previous tool calls
        image_list = self._process_pending_images()
        if image_list:
            # Create new message with images attached
            input_message = BaseMessage.make_user_message(
                role_name="User",
                content=input_message.content,
                image_list=image_list,
            )

        # Add user input to memory
        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_call_records: List[ToolCallingRecord] = []
        external_tool_call_requests: Optional[List[ToolCallRequest]] = None

        accumulated_context_tokens = (
            0  # This tracks cumulative context tokens, not API usage tokens
        )

        # Initialize token usage tracker
        step_token_usage = self._create_token_usage_tracker()
        iteration_count = 0

        while True:
            if self.pause_event is not None and not self.pause_event.is_set():
                while not self.pause_event.is_set():
                    time.sleep(0.001)

            try:
                openai_messages, num_tokens = self.memory.get_context()
                accumulated_context_tokens += num_tokens
            except RuntimeError as e:
                return self._step_terminate(
                    e.args[1], tool_call_records, "max_tokens_exceeded"
                )
            # Get response from model backend
            response = self._get_model_response(
                openai_messages,
                accumulated_context_tokens,  # Cumulative context tokens
                response_format,
                self._get_full_tool_schemas(),
            )
            iteration_count += 1

            # Accumulate API token usage
            self._update_token_usage_tracker(
                step_token_usage, response.usage_dict
            )

            # Terminate Agent if stop_event is set
            if self.stop_event and self.stop_event.is_set():
                # Use the _step_terminate to terminate the agent with reason
                return self._step_terminate(
                    accumulated_context_tokens,
                    tool_call_records,
                    "termination_triggered",
                )

            if tool_call_requests := response.tool_call_requests:
                # Process all tool calls
                for tool_call_request in tool_call_requests:
                    if (
                        tool_call_request.tool_name
                        in self._external_tool_schemas
                    ):
                        if external_tool_call_requests is None:
                            external_tool_call_requests = []
                        external_tool_call_requests.append(tool_call_request)
                    else:
                        if (
                            self.pause_event is not None
                            and not self.pause_event.is_set()
                        ):
                            while not self.pause_event.is_set():
                                time.sleep(0.001)
                        result = self._execute_tool(tool_call_request)
                        tool_call_records.append(result)

                # If we found external tool calls, break the loop
                if external_tool_call_requests:
                    break

                if (
                    self.max_iteration is not None
                    and iteration_count >= self.max_iteration
                ):
                    break

                # If we're still here, continue the loop
                continue

            break

        self._format_response_if_needed(response, response_format)

        # Apply manual parsing if we used prompt-based formatting
        if used_prompt_formatting and original_response_format:
            self._apply_prompt_based_parsing(
                response, original_response_format
            )

        self._record_final_output(response.output_messages)

        return self._convert_to_chatagent_response(
            response,
            tool_call_records,
            accumulated_context_tokens,
            external_tool_call_requests,
            step_token_usage["prompt_tokens"],
            step_token_usage["completion_tokens"],
            step_token_usage["total_tokens"],
        )

    @property
    def chat_history(self) -> List[OpenAIMessage]:
        openai_messages, _ = self.memory.get_context()
        return openai_messages

    @observe()
    async def astep(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Union[ChatAgentResponse, AsyncStreamingChatAgentResponse]:
        r"""Performs a single step in the chat session by generating a response
        to the input message. This agent step can call async function calls.

        Args:
            input_message (Union[BaseMessage, str]): The input message to the
                agent. For BaseMessage input, its `role` field that specifies
                the role at backend may be either `user` or `assistant` but it
                will be set to `user` anyway since for the self agent any
                incoming message is external. For str input, the `role_name`
                would be `User`.
            response_format (Optional[Type[BaseModel]], optional): A pydantic
                model class that includes value types and field descriptions
                used to generate a structured response by LLM. This schema
                helps in defining the expected output format. (default:
                :obj:`None`)
        Returns:
            Union[ChatAgentResponse, AsyncStreamingChatAgentResponse]:
                If stream is False, returns a ChatAgentResponse. If stream is
                True, returns an AsyncStreamingChatAgentResponse that can be
                awaited for the final result or async iterated for streaming
                updates.
        """

        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

        stream = self.model_backend.model_config_dict.get("stream", False)
        if stream:
            # Return wrapped async generator that is awaitable
            async_generator = self._astream(input_message, response_format)
            return AsyncStreamingChatAgentResponse(async_generator)
        else:
            return await self._astep_non_streaming_task(
                input_message, response_format
            )

    async def _astep_non_streaming_task(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        r"""Internal async method for non-streaming astep logic."""

        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

        # Handle response format compatibility with non-strict tools
        original_response_format = response_format
        input_message, response_format, used_prompt_formatting = (
            self._handle_response_format_with_non_strict_tools(
                input_message, response_format
            )
        )

        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        # Attach any pending images from previous tool calls
        image_list = self._process_pending_images()
        if image_list:
            # Create new message with images attached
            input_message = BaseMessage.make_user_message(
                role_name="User",
                content=input_message.content,
                image_list=image_list,
            )

        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_call_records: List[ToolCallingRecord] = []
        external_tool_call_requests: Optional[List[ToolCallRequest]] = None
        accumulated_context_tokens = (
            0  # This tracks cumulative context tokens, not API usage tokens
        )

        # Initialize token usage tracker
        step_token_usage = self._create_token_usage_tracker()
        iteration_count = 0
        while True:
            if self.pause_event is not None and not self.pause_event.is_set():
                await self.pause_event.wait()
            try:
                openai_messages, num_tokens = self.memory.get_context()
                accumulated_context_tokens += num_tokens
            except RuntimeError as e:
                return self._step_terminate(
                    e.args[1], tool_call_records, "max_tokens_exceeded"
                )

            response = await self._aget_model_response(
                openai_messages,
                accumulated_context_tokens,
                response_format,
                self._get_full_tool_schemas(),
            )
            iteration_count += 1

            # Accumulate API token usage
            self._update_token_usage_tracker(
                step_token_usage, response.usage_dict
            )

            # Terminate Agent if stop_event is set
            if self.stop_event and self.stop_event.is_set():
                # Use the _step_terminate to terminate the agent with reason
                return self._step_terminate(
                    accumulated_context_tokens,
                    tool_call_records,
                    "termination_triggered",
                )

            if tool_call_requests := response.tool_call_requests:
                # Process all tool calls
                new_images_from_tools = []
                for tool_call_request in tool_call_requests:
                    if (
                        tool_call_request.tool_name
                        in self._external_tool_schemas
                    ):
                        if external_tool_call_requests is None:
                            external_tool_call_requests = []
                        external_tool_call_requests.append(tool_call_request)
                    else:
                        if (
                            self.pause_event is not None
                            and not self.pause_event.is_set()
                        ):
                            await self.pause_event.wait()
                        tool_call_record = await self._aexecute_tool(
                            tool_call_request
                        )
                        tool_call_records.append(tool_call_record)

                        # Check if this tool call produced images
                        if (
                            hasattr(tool_call_record, 'images')
                            and tool_call_record.images
                        ):
                            new_images_from_tools.extend(
                                tool_call_record.images
                            )

                # If we found an external tool call, break the loop
                if external_tool_call_requests:
                    break

                # If tools produced images
                # send them to the model as a user message
                if new_images_from_tools:
                    # Convert base64 images to PIL Images
                    image_list = []
                    for img_data in new_images_from_tools:
                        try:
                            import base64
                            import io

                            from PIL import Image

                            # Extract base64 data from data URL format
                            if img_data.startswith("data:image"):
                                # Format:
                                # "data:image/png;base64,iVBORw0KGgo..."
                                base64_data = img_data.split(',', 1)[1]
                            else:
                                # Raw base64 data
                                base64_data = img_data

                            # Decode and create PIL Image
                            image_bytes = base64.b64decode(base64_data)
                            pil_image = Image.open(io.BytesIO(image_bytes))
                            # Convert to ensure proper
                            # Image.Image type for compatibility
                            pil_image_tool_result: Image.Image = (
                                pil_image.convert('RGB')
                            )
                            image_list.append(pil_image_tool_result)

                        except Exception as e:
                            logger.warning(
                                f"Failed to convert "
                                f"base64 image to PIL for immediate use: {e}"
                            )
                            continue

                    # If we have valid images
                    # create a user message with images
                    if image_list:
                        # Create a user message with images
                        # to provide visual context immediately
                        image_message = BaseMessage.make_user_message(
                            role_name="User",
                            content="[Visual content from tool execution - please analyze and continue]",  # noqa: E501
                            image_list=image_list,
                        )

                        self.update_memory(
                            image_message, OpenAIBackendRole.USER
                        )

                if (
                    self.max_iteration is not None
                    and iteration_count >= self.max_iteration
                ):
                    break

                # If we're still here, continue the loop
                continue

            break

        await self._aformat_response_if_needed(response, response_format)

        # Apply manual parsing if we used prompt-based formatting
        if used_prompt_formatting and original_response_format:
            self._apply_prompt_based_parsing(
                response, original_response_format
            )

        self._record_final_output(response.output_messages)

        return self._convert_to_chatagent_response(
            response,
            tool_call_records,
            accumulated_context_tokens,
            external_tool_call_requests,
            step_token_usage["prompt_tokens"],
            step_token_usage["completion_tokens"],
            step_token_usage["total_tokens"],
        )

    def _create_token_usage_tracker(self) -> Dict[str, int]:
        r"""Creates a fresh token usage tracker for a step.

        Returns:
            Dict[str, int]: A dictionary for tracking token usage.
        """
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def _update_token_usage_tracker(
        self, tracker: Dict[str, int], usage_dict: Dict[str, int]
    ) -> None:
        r"""Updates a token usage tracker with values from a usage dictionary.

        Args:
            tracker (Dict[str, int]): The token usage tracker to update.
            usage_dict (Dict[str, int]): The usage dictionary with new values.
        """
        tracker["prompt_tokens"] += usage_dict.get("prompt_tokens", 0)
        tracker["completion_tokens"] += usage_dict.get("completion_tokens", 0)
        tracker["total_tokens"] += usage_dict.get("total_tokens", 0)

    def _convert_to_chatagent_response(
        self,
        response: ModelResponse,
        tool_call_records: List[ToolCallingRecord],
        num_tokens: int,  # Context tokens from the last call in step
        external_tool_call_requests: Optional[List[ToolCallRequest]],
        step_api_prompt_tokens: int = 0,
        step_api_completion_tokens: int = 0,
        step_api_total_tokens: int = 0,
    ) -> ChatAgentResponse:
        r"""Parse the final model response into the chat agent response."""
        # Create usage_dict for the current step's API calls
        step_api_usage_dict = {
            "prompt_tokens": step_api_prompt_tokens,
            "completion_tokens": step_api_completion_tokens,
            "total_tokens": step_api_total_tokens,
        }

        info = self._step_get_info(
            response.output_messages,
            response.finish_reasons,
            step_api_usage_dict,  # Pass step-specific API usage here
            response.response_id,
            tool_call_records,
            num_tokens,  # This is context tokens, not API usage
            external_tool_call_requests,
        )

        return ChatAgentResponse(
            msgs=response.output_messages,
            terminated=self.terminated,
            info=info,
        )

    def _process_pending_images(self) -> List:
        r"""Process pending images with retry logic and return PIL Image list.

        Returns:
            List: List of successfully converted PIL Images.
        """
        if not self._pending_images:
            return []

        image_list = []
        successfully_processed = []
        failed_images = []

        for img_data in self._pending_images:
            # Track retry count
            retry_count = self._image_retry_count.get(img_data, 0)

            # Remove images that have failed too many times (max 3 attempts)
            if retry_count >= 3:
                failed_images.append(img_data)
                logger.warning(
                    f"Removing image after {retry_count} failed attempts"
                )
                continue

            try:
                import base64
                import io

                from PIL import Image

                # Extract base64 data from data URL format
                if img_data.startswith("data:image"):
                    # Format: "data:image/png;base64,iVBORw0KGgo..."
                    base64_data = img_data.split(',', 1)[1]
                else:
                    # Raw base64 data
                    base64_data = img_data

                # Decode and create PIL Image
                image_bytes = base64.b64decode(base64_data)
                pil_image = Image.open(io.BytesIO(image_bytes))
                pil_image_converted: Image.Image = pil_image.convert('RGB')
                image_list.append(pil_image_converted)
                successfully_processed.append(img_data)

            except Exception as e:
                # Increment retry count for failed conversion
                self._image_retry_count[img_data] = retry_count + 1
                logger.warning(
                    f"Failed to convert base64 image to PIL "
                    f"(attempt {retry_count + 1}/3): {e}"
                )
                continue

        # Clean up processed and failed images
        for img in successfully_processed + failed_images:
            self._pending_images.remove(img)
            # Clean up retry count for processed/removed images
            self._image_retry_count.pop(img, None)

        return image_list

    def _record_final_output(self, output_messages: List[BaseMessage]) -> None:
        r"""Log final messages or warnings about multiple responses."""
        if len(output_messages) == 1:
            self.record_message(output_messages[0])
        else:
            logger.warning(
                "Multiple messages returned in `step()`. Record "
                "selected message manually using `record_message()`."
            )

    def _is_vision_error(self, exc: Exception) -> bool:
        r"""Check if the exception is likely related to vision/image is not
        supported by the model."""
        # TODO: more robust vision error detection
        error_msg = str(exc).lower()
        vision_keywords = [
            'vision',
            'image',
            'multimodal',
            'unsupported',
            'invalid content type',
            'image_url',
            'visual',
        ]
        return any(keyword in error_msg for keyword in vision_keywords)

    def _has_images(self, messages: List[OpenAIMessage]) -> bool:
        r"""Check if any message contains images."""
        for msg in messages:
            content = msg.get('content')
            if isinstance(content, list):
                for item in content:
                    if (
                        isinstance(item, dict)
                        and item.get('type') == 'image_url'
                    ):
                        return True
        return False

    def _strip_images_from_messages(
        self, messages: List[OpenAIMessage]
    ) -> List[OpenAIMessage]:
        r"""Remove images from messages, keeping only text content."""
        stripped_messages = []
        for msg in messages:
            content = msg.get('content')
            if isinstance(content, list):
                # Extract only text content from multimodal messages
                text_content = ""
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        text_content += item.get('text', '')

                # Create new message with only text content
                new_msg = msg.copy()
                new_msg['content'] = (
                    text_content
                    or "[Image content removed - model doesn't support vision]"
                )
                stripped_messages.append(new_msg)
            else:
                # Regular text message, keep as is
                stripped_messages.append(msg)
        return stripped_messages

    def _get_model_response(
        self,
        openai_messages: List[OpenAIMessage],
        num_tokens: int,
        response_format: Optional[Type[BaseModel]] = None,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelResponse:
        r"""Internal function for agent step model response."""

        response = None
        try:
            response = self.model_backend.run(
                openai_messages, response_format, tool_schemas or None
            )
        except Exception as exc:
            # Try again without images if the error might be vision-related
            if self._is_vision_error(exc) and self._has_images(
                openai_messages
            ):
                logger.warning(
                    "Model appears to not support vision. Retrying without images."  # noqa: E501
                )
                try:
                    stripped_messages = self._strip_images_from_messages(
                        openai_messages
                    )
                    response = self.model_backend.run(
                        stripped_messages,
                        response_format,
                        tool_schemas or None,
                    )
                except Exception:
                    pass  # Fall through to original error handling

            if not response:
                logger.error(
                    f"An error occurred while running model "
                    f"{self.model_backend.model_type}, "
                    f"index: {self.model_backend.current_model_index}",
                    exc_info=exc,
                )
                error_info = str(exc)

        if not response and self.model_backend.num_models > 1:
            raise ModelProcessingError(
                "Unable to process messages: none of the provided models "
                "run successfully."
            )
        elif not response:
            raise ModelProcessingError(
                f"Unable to process messages: the only provided model "
                f"did not run successfully. Error: {error_info}"
            )

        sanitized_messages = self._sanitize_messages_for_logging(
            openai_messages
        )
        logger.info(
            f"Model {self.model_backend.model_type}, "
            f"index {self.model_backend.current_model_index}, "
            f"processed these messages: {sanitized_messages}"
        )
        if not isinstance(response, ChatCompletion):
            raise TypeError(
                f"Expected response to be a `ChatCompletion` object, but "
                f"got {type(response).__name__} instead."
            )
        return self._handle_batch_response(response)

    async def _aget_model_response(
        self,
        openai_messages: List[OpenAIMessage],
        num_tokens: int,
        response_format: Optional[Type[BaseModel]] = None,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
    ) -> ModelResponse:
        r"""Internal function for agent step model response."""

        response = None
        try:
            response = await self.model_backend.arun(
                openai_messages, response_format, tool_schemas or None
            )
        except Exception as exc:
            # Try again without images if the error might be vision-related
            if self._is_vision_error(exc) and self._has_images(
                openai_messages
            ):
                logger.warning(
                    "Model appears to not support vision. Retrying without images."  # noqa: E501
                )
                try:
                    stripped_messages = self._strip_images_from_messages(
                        openai_messages
                    )
                    response = await self.model_backend.arun(
                        stripped_messages,
                        response_format,
                        tool_schemas or None,
                    )
                except Exception:
                    pass  # Fall through to original error handling

            if not response:
                logger.error(
                    f"An error occurred while running model "
                    f"{self.model_backend.model_type}, "
                    f"index: {self.model_backend.current_model_index}",
                    exc_info=exc,
                )
                error_info = str(exc)

        if not response and self.model_backend.num_models > 1:
            raise ModelProcessingError(
                "Unable to process messages: none of the provided models "
                "run successfully."
            )
        elif not response:
            raise ModelProcessingError(
                f"Unable to process messages: the only provided model "
                f"did not run successfully. Error: {error_info}"
            )

        sanitized_messages = self._sanitize_messages_for_logging(
            openai_messages
        )
        logger.info(
            f"Model {self.model_backend.model_type}, "
            f"index {self.model_backend.current_model_index}, "
            f"processed these messages: {sanitized_messages}"
        )
        if not isinstance(response, ChatCompletion):
            raise TypeError(
                f"Expected response to be a `ChatCompletion` object, but "
                f"got {type(response).__name__} instead."
            )
        return self._handle_batch_response(response)

    def _sanitize_messages_for_logging(self, messages):
        r"""Sanitize OpenAI messages for logging by replacing base64 image
        data with a simple message and a link to view the image.

        Args:
            messages (List[OpenAIMessage]): The OpenAI messages to sanitize.

        Returns:
            List[OpenAIMessage]: The sanitized OpenAI messages.
        """
        import hashlib
        import os
        import re
        import tempfile

        # Create a copy of messages for logging to avoid modifying the
        # original messages
        sanitized_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                sanitized_msg = msg.copy()
                # Check if content is a list (multimodal content with images)
                if isinstance(sanitized_msg.get('content'), list):
                    content_list = []
                    for item in sanitized_msg['content']:
                        if (
                            isinstance(item, dict)
                            and item.get('type') == 'image_url'
                        ):
                            # Handle image URL
                            image_url = item.get('image_url', {}).get(
                                'url', ''
                            )
                            if image_url and image_url.startswith(
                                'data:image'
                            ):
                                # Extract image data and format
                                match = re.match(
                                    r'data:image/([^;]+);base64,(.+)',
                                    image_url,
                                )
                                if match:
                                    img_format, base64_data = match.groups()

                                    # Create a hash of the image data to use
                                    # as filename
                                    img_hash = hashlib.md5(
                                        base64_data[:100].encode()
                                    ).hexdigest()[:10]
                                    img_filename = (
                                        f"image_{img_hash}.{img_format}"
                                    )

                                    # Save image to temp directory for viewing
                                    try:
                                        import base64

                                        temp_dir = tempfile.gettempdir()
                                        img_path = os.path.join(
                                            temp_dir, img_filename
                                        )

                                        # Only save if file doesn't exist
                                        if not os.path.exists(img_path):
                                            with open(img_path, 'wb') as f:
                                                f.write(
                                                    base64.b64decode(
                                                        base64_data
                                                    )
                                                )

                                        # Create a file:// URL that can be
                                        # opened
                                        file_url = f"file://{img_path}"

                                        content_list.append(
                                            {
                                                'type': 'image_url',
                                                'image_url': {
                                                    'url': f'{file_url}',
                                                    'detail': item.get(
                                                        'image_url', {}
                                                    ).get('detail', 'auto'),
                                                },
                                            }
                                        )
                                    except Exception as e:
                                        # If saving fails, fall back to simple
                                        # message
                                        content_list.append(
                                            {
                                                'type': 'image_url',
                                                'image_url': {
                                                    'url': '[base64 '
                                                    + 'image - error saving: '
                                                    + str(e)
                                                    + ']',
                                                    'detail': item.get(
                                                        'image_url', {}
                                                    ).get('detail', 'auto'),
                                                },
                                            }
                                        )
                                else:
                                    # If regex fails, fall back to simple
                                    # message
                                    content_list.append(
                                        {
                                            'type': 'image_url',
                                            'image_url': {
                                                'url': '[base64 '
                                                + 'image - invalid format]',
                                                'detail': item.get(
                                                    'image_url', {}
                                                ).get('detail', 'auto'),
                                            },
                                        }
                                    )
                            else:
                                content_list.append(item)
                        else:
                            content_list.append(item)
                    sanitized_msg['content'] = content_list
                sanitized_messages.append(sanitized_msg)
            else:
                sanitized_messages.append(msg)
        return sanitized_messages

    def _step_get_info(
        self,
        output_messages: List[BaseMessage],
        finish_reasons: List[str],
        usage_dict: Dict[str, int],
        response_id: str,
        tool_calls: List[ToolCallingRecord],
        num_tokens: int,
        external_tool_call_requests: Optional[List[ToolCallRequest]] = None,
    ) -> Dict[str, Any]:
        r"""Process the output of a chat step and gather information about the
        step.

        This method checks for termination conditions, updates the agent's
        state, and collects information about the chat step, including tool
        calls and termination reasons.

        Args:
            output_messages (List[BaseMessage]): The messages generated in
                this step.
            finish_reasons (List[str]): The reasons for finishing the
                generation for each message.
            usage_dict (Dict[str, int]): Dictionary containing token usage
                information.
            response_id (str): The ID of the response from the model.
            tool_calls (List[ToolCallingRecord]): Records of function calls
                made during this step.
            num_tokens (int): The number of tokens used in this step.
            external_tool_call_request (Optional[ToolCallRequest]): The
                request for external tool call.

        Returns:
            Dict[str, Any]: A dictionary containing information about the chat
                step, including termination status, reasons, and tool call
                information.

        Note:
            This method iterates over all response terminators and checks if
            any of them signal termination. If a terminator signals
            termination, the agent's state is updated accordingly, and the
            termination reason is recorded.
        """
        termination = [
            terminator.is_terminated(output_messages)
            for terminator in self.response_terminators
        ]
        # Terminate the agent if any of the terminator terminates
        self.terminated, termination_reason = next(
            (
                (terminated, termination_reason)
                for terminated, termination_reason in termination
                if terminated
            ),
            (False, None),
        )
        # For now only retain the first termination reason
        if self.terminated and termination_reason is not None:
            finish_reasons = [termination_reason] * len(finish_reasons)

        return get_info_dict(
            response_id,
            usage_dict,
            finish_reasons,
            num_tokens,
            tool_calls,
            external_tool_call_requests,
        )

    def _handle_batch_response(
        self, response: ChatCompletion
    ) -> ModelResponse:
        r"""Process a batch response from the model and extract the necessary
        information.

        Args:
            response (ChatCompletion): Model response.

        Returns:
            _ModelResponse: parsed model response.
        """
        output_messages: List[BaseMessage] = []
        for choice in response.choices:
            # Skip messages with no meaningful content
            if (
                choice.message.content is None
                or choice.message.content.strip() == ""
            ) and not choice.message.tool_calls:
                continue

            meta_dict = {}
            if logprobs_info := handle_logprobs(choice):
                meta_dict["logprobs_info"] = logprobs_info

            chat_message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict=meta_dict,
                content=choice.message.content or "",
                parsed=getattr(choice.message, "parsed", None),
            )

            output_messages.append(chat_message)

        finish_reasons = [
            str(choice.finish_reason) for choice in response.choices
        ]

        usage = {}
        if response.usage is not None:
            usage = safe_model_dump(response.usage)

        tool_call_requests: Optional[List[ToolCallRequest]] = None
        if tool_calls := response.choices[0].message.tool_calls:
            tool_call_requests = []
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_call_id = tool_call.id
                args = json.loads(tool_call.function.arguments)
                tool_call_request = ToolCallRequest(
                    tool_name=tool_name, args=args, tool_call_id=tool_call_id
                )
                tool_call_requests.append(tool_call_request)

        return ModelResponse(
            response=response,
            tool_call_requests=tool_call_requests,
            output_messages=output_messages,
            finish_reasons=finish_reasons,
            usage_dict=usage,
            response_id=response.id or "",
        )

    def _step_terminate(
        self,
        num_tokens: int,
        tool_calls: List[ToolCallingRecord],
        termination_reason: str,
    ) -> ChatAgentResponse:
        r"""Create a response when the agent execution is terminated.

        This method is called when the agent needs to terminate its execution
        due to various reasons such as token limit exceeded, or other
        termination conditions. It creates a response with empty messages but
        includes termination information in the info dictionary.

        Args:
            num_tokens (int): Number of tokens in the messages.
            tool_calls (List[ToolCallingRecord]): List of information
                objects of functions called in the current step.
            termination_reason (str): String describing the reason for
                termination.

        Returns:
            ChatAgentResponse: A response object with empty message list,
                terminated flag set to True, and an info dictionary containing
                termination details, token counts, and tool call information.
        """
        self.terminated = True

        info = get_info_dict(
            None,
            None,
            [termination_reason],
            num_tokens,
            tool_calls,
        )

        return ChatAgentResponse(
            msgs=[],
            terminated=self.terminated,
            info=info,
        )

    def _execute_tool(
        self,
        tool_call_request: ToolCallRequest,
    ) -> ToolCallingRecord:
        r"""Execute the tool with arguments following the model's response.

        Args:
            tool_call_request (_ToolCallRequest): The tool call request.

        Returns:
            FunctionCallingRecord: A struct for logging information about this
                function call.
        """
        func_name = tool_call_request.tool_name
        args = tool_call_request.args
        tool_call_id = tool_call_request.tool_call_id
        tool = self._internal_tools[func_name]
        try:
            raw_result = tool(**args)
            if self.mask_tool_output:
                self._secure_result_store[tool_call_id] = raw_result
                result = (
                    "[The tool has been executed successfully, but the output"
                    " from the tool is masked. You can move forward]"
                )
                mask_flag = True
            else:
                result = raw_result
                mask_flag = False
        except Exception as e:
            # Capture the error message to prevent framework crash
            error_msg = f"Error executing tool '{func_name}': {e!s}"
            result = f"Tool execution failed: {error_msg}"
            mask_flag = False
            logging.warning(error_msg)

        # Check if result is a ToolResult with images
        images_to_attach = None
        if isinstance(result, ToolResult):
            images_to_attach = result.images
            result = str(result)  # Use string representation for storage

        tool_record = self._record_tool_calling(
            func_name, args, result, tool_call_id, mask_output=mask_flag
        )

        # Store images for later attachment to next user message
        if images_to_attach:
            tool_record.images = images_to_attach
            # Add images with duplicate prevention
            for img in images_to_attach:
                if img not in self._pending_images:
                    self._pending_images.append(img)

        return tool_record

    async def _aexecute_tool(
        self,
        tool_call_request: ToolCallRequest,
    ) -> ToolCallingRecord:
        func_name = tool_call_request.tool_name
        args = tool_call_request.args
        tool_call_id = tool_call_request.tool_call_id
        tool = self._internal_tools[func_name]
        import asyncio

        try:
            # Try different invocation paths in order of preference
            if hasattr(tool, 'func') and hasattr(tool.func, 'async_call'):
                # Case: FunctionTool wrapping an MCP tool
                result = await tool.func.async_call(**args)

            elif hasattr(tool, 'async_call') and callable(tool.async_call):
                # Case: tool itself has async_call
                result = await tool.async_call(**args)

            elif hasattr(tool, 'func') and asyncio.iscoroutinefunction(
                tool.func
            ):
                # Case: tool wraps a direct async function
                result = await tool.func(**args)

            elif asyncio.iscoroutinefunction(tool):
                # Case: tool is itself a coroutine function
                result = await tool(**args)

            else:
                # Fallback: synchronous call
                result = tool(**args)

        except Exception as e:
            # Capture the error message to prevent framework crash
            error_msg = f"Error executing async tool '{func_name}': {e!s}"
            result = f"Tool execution failed: {error_msg}"
            logging.warning(error_msg)

        # Check if result is a ToolResult with images
        images_to_attach = None
        if isinstance(result, ToolResult):
            images_to_attach = result.images
            result = str(result)  # Use string representation for storage

        tool_record = self._record_tool_calling(
            func_name, args, result, tool_call_id
        )

        # Store images for later attachment to next user message
        if images_to_attach:
            tool_record.images = images_to_attach
            # Add images with duplicate prevention
            for img in images_to_attach:
                if img not in self._pending_images:
                    self._pending_images.append(img)

        return tool_record

    def _record_tool_calling(
        self,
        func_name: str,
        args: Dict[str, Any],
        result: Any,
        tool_call_id: str,
        mask_output: bool = False,
    ):
        r"""Record the tool calling information in the memory, and return the
        tool calling record.

        Args:
            func_name (str): The name of the tool function called.
            args (Dict[str, Any]): The arguments passed to the tool.
            result (Any): The result returned by the tool execution.
            tool_call_id (str): A unique identifier for the tool call.
            mask_output (bool, optional): Whether to return a sanitized
                placeholder instead of the raw tool output.
                (default: :obj:`False`)

        Returns:
            ToolCallingRecord: A struct containing information about
            this tool call.
        """
        assist_msg = FunctionCallingMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=None,
            content="",
            func_name=func_name,
            args=args,
            tool_call_id=tool_call_id,
        )
        func_msg = FunctionCallingMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=None,
            content="",
            func_name=func_name,
            result=result,
            tool_call_id=tool_call_id,
            mask_output=mask_output,
        )

        # Use precise timestamps to ensure correct ordering
        # This ensures the assistant message (tool call) always appears before
        # the function message (tool result) in the conversation context
        # Use time.time_ns() for nanosecond precision to avoid collisions
        import time

        current_time_ns = time.time_ns()
        base_timestamp = current_time_ns / 1_000_000_000  # Convert to seconds

        self.update_memory(
            assist_msg, OpenAIBackendRole.ASSISTANT, timestamp=base_timestamp
        )

        # Add minimal increment to ensure function message comes after
        self.update_memory(
            func_msg,
            OpenAIBackendRole.FUNCTION,
            timestamp=base_timestamp + 1e-6,
        )

        # Record information about this tool call
        tool_record = ToolCallingRecord(
            tool_name=func_name,
            args=args,
            result=result,
            tool_call_id=tool_call_id,
        )

        return tool_record

    def _stream(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Generator[ChatAgentResponse, None, None]:
        r"""Executes a streaming step in the chat session, yielding
        intermediate responses as they are generated.

        Args:
            input_message (Union[BaseMessage, str]): The input message for the
                agent.
            response_format (Optional[Type[BaseModel]], optional): A Pydantic
                model defining the expected structure of the response.

        Yields:
            ChatAgentResponse: Intermediate responses containing partial
                content, tool calls, and other information as they become
                available.
        """
        # Convert input message to BaseMessage if necessary
        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        # Add user input to memory
        self.update_memory(input_message, OpenAIBackendRole.USER)

        # Get context for streaming
        try:
            openai_messages, num_tokens = self.memory.get_context()
        except RuntimeError as e:
            yield self._step_terminate(e.args[1], [], "max_tokens_exceeded")
            return

        # Start streaming response
        yield from self._stream_response(
            openai_messages, num_tokens, response_format
        )

    def _get_token_count(self, content: str) -> int:
        r"""Get token count for content with fallback."""
        if hasattr(self.model_backend, 'token_counter'):
            return len(self.model_backend.token_counter.encode(content))
        else:
            return len(content.split())

    def _stream_response(
        self,
        openai_messages: List[OpenAIMessage],
        num_tokens: int,
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Generator[ChatAgentResponse, None, None]:
        r"""Internal method to handle streaming responses with tool calls."""

        tool_call_records: List[ToolCallingRecord] = []
        accumulated_tool_calls: Dict[str, Any] = {}
        step_token_usage = self._create_token_usage_tracker()

        # Create content accumulator for proper content management
        content_accumulator = StreamContentAccumulator()
        iteration_count = 0
        while True:
            # Check termination condition
            if self.stop_event and self.stop_event.is_set():
                yield self._step_terminate(
                    num_tokens, tool_call_records, "termination_triggered"
                )
                return

            # Get streaming response from model
            try:
                response = self.model_backend.run(
                    openai_messages,
                    response_format,
                    self._get_full_tool_schemas() or None,
                )
                iteration_count += 1
            except Exception as exc:
                logger.error(
                    f"Error in streaming model response: {exc}", exc_info=exc
                )
                yield self._create_error_response(str(exc), tool_call_records)
                return

            # Handle streaming response
            if isinstance(response, Stream):
                (
                    stream_completed,
                    tool_calls_complete,
                ) = yield from self._process_stream_chunks_with_accumulator(
                    response,
                    content_accumulator,
                    accumulated_tool_calls,
                    tool_call_records,
                    step_token_usage,
                    response_format,
                )

                if tool_calls_complete:
                    # Clear completed tool calls
                    accumulated_tool_calls.clear()

                    # If we executed tools and not in
                    # single iteration mode, continue
                    if tool_call_records and (
                        self.max_iteration is None
                        or iteration_count < self.max_iteration
                    ):
                        # Update messages with tool results for next iteration
                        try:
                            openai_messages, num_tokens = (
                                self.memory.get_context()
                            )
                        except RuntimeError as e:
                            yield self._step_terminate(
                                e.args[1],
                                tool_call_records,
                                "max_tokens_exceeded",
                            )
                            return
                        # Reset streaming content for next iteration
                        content_accumulator.reset_streaming_content()
                        continue
                    else:
                        break
                else:
                    # Stream completed without tool calls
                    accumulated_tool_calls.clear()
                    break
            elif hasattr(response, '__enter__') and hasattr(
                response, '__exit__'
            ):
                # Handle structured output stream (ChatCompletionStreamManager)
                with response as stream:
                    parsed_object = None

                    for event in stream:
                        if event.type == "content.delta":
                            if getattr(event, "delta", None):
                                # Use accumulator for proper content management
                                partial_response = self._create_streaming_response_with_accumulator(  # noqa: E501
                                    content_accumulator,
                                    getattr(event, "delta", ""),
                                    step_token_usage,
                                    tool_call_records=tool_call_records.copy(),
                                )
                                yield partial_response

                        elif event.type == "content.done":
                            parsed_object = getattr(event, "parsed", None)
                            break
                        elif event.type == "error":
                            logger.error(
                                f"Error in structured stream: "
                                f"{getattr(event, 'error', '')}"
                            )
                            yield self._create_error_response(
                                str(getattr(event, 'error', '')),
                                tool_call_records,
                            )
                            return

                    # Get final completion and record final message
                    try:
                        final_completion = stream.get_final_completion()
                        final_content = (
                            final_completion.choices[0].message.content or ""
                        )

                        final_message = BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict={},
                            content=final_content,
                            parsed=cast(
                                "BaseModel | dict[str, Any] | None",
                                parsed_object,
                            ),  # type: ignore[arg-type]
                        )

                        self.record_message(final_message)

                        # Create final response
                        final_response = ChatAgentResponse(
                            msgs=[final_message],
                            terminated=False,
                            info={
                                "id": final_completion.id or "",
                                "usage": safe_model_dump(
                                    final_completion.usage
                                )
                                if final_completion.usage
                                else {},
                                "finish_reasons": [
                                    choice.finish_reason or "stop"
                                    for choice in final_completion.choices
                                ],
                                "num_tokens": self._get_token_count(
                                    final_content
                                ),
                                "tool_calls": tool_call_records,
                                "external_tool_requests": None,
                                "streaming": False,
                                "partial": False,
                            },
                        )
                        yield final_response
                        break

                    except Exception as e:
                        logger.error(f"Error getting final completion: {e}")
                        yield self._create_error_response(
                            str(e), tool_call_records
                        )
                        return
            else:
                # Handle non-streaming response (fallback)
                model_response = self._handle_batch_response(response)
                yield self._convert_to_chatagent_response(
                    model_response,
                    tool_call_records,
                    num_tokens,
                    None,
                    model_response.usage_dict.get("prompt_tokens", 0),
                    model_response.usage_dict.get("completion_tokens", 0),
                    model_response.usage_dict.get("total_tokens", 0),
                )
                accumulated_tool_calls.clear()
                break

    def _process_stream_chunks_with_accumulator(
        self,
        stream: Stream[ChatCompletionChunk],
        content_accumulator: StreamContentAccumulator,
        accumulated_tool_calls: Dict[str, Any],
        tool_call_records: List[ToolCallingRecord],
        step_token_usage: Dict[str, int],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> Generator[ChatAgentResponse, None, Tuple[bool, bool]]:
        r"""Process streaming chunks with content accumulator."""

        tool_calls_complete = False
        stream_completed = False

        for chunk in stream:
            # Update token usage if available
            if chunk.usage:
                self._update_token_usage_tracker(
                    step_token_usage, safe_model_dump(chunk.usage)
                )

            # Process chunk delta
            if chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                delta = choice.delta

                # Handle content streaming
                if delta.content:
                    # Use accumulator for proper content management
                    partial_response = (
                        self._create_streaming_response_with_accumulator(
                            content_accumulator,
                            delta.content,
                            step_token_usage,
                            getattr(chunk, 'id', ''),
                            tool_call_records.copy(),
                        )
                    )
                    yield partial_response

                # Handle tool calls streaming
                if delta.tool_calls:
                    tool_calls_complete = self._accumulate_tool_calls(
                        delta.tool_calls, accumulated_tool_calls
                    )

                # Check if stream is complete
                if choice.finish_reason:
                    stream_completed = True

                    # If we have complete tool calls, execute them with
                    # sync status updates
                    if accumulated_tool_calls:
                        # Record assistant message with tool calls first
                        self._record_assistant_tool_calls_message(
                            accumulated_tool_calls,
                            content_accumulator.get_full_content(),
                        )

                        # Execute tools synchronously with
                        # optimized status updates
                        for (
                            status_response
                        ) in self._execute_tools_sync_with_status_accumulator(
                            accumulated_tool_calls,
                            content_accumulator,
                            step_token_usage,
                            tool_call_records,
                        ):
                            yield status_response

                        # Yield "Sending back result to model" status
                        if tool_call_records:
                            sending_status = self._create_tool_status_response_with_accumulator(  # noqa: E501
                                content_accumulator,
                                "\n------\n\nSending back result to model\n\n",
                                "tool_sending",
                                step_token_usage,
                            )
                            yield sending_status

                    # Record final message only if we have content AND no tool
                    # calls. If there are tool calls, _record_tool_calling
                    # will handle message recording.
                    final_content = content_accumulator.get_full_content()
                    if final_content.strip() and not accumulated_tool_calls:
                        final_message = BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict={},
                            content=final_content,
                        )

                        if response_format:
                            self._try_format_message(
                                final_message, response_format
                            )

                        self.record_message(final_message)
                    break

        return stream_completed, tool_calls_complete

    def _accumulate_tool_calls(
        self,
        tool_call_deltas: List[Any],
        accumulated_tool_calls: Dict[str, Any],
    ) -> bool:
        r"""Accumulate tool call chunks and return True when
        any tool call is complete.

        Args:
            tool_call_deltas (List[Any]): List of tool call deltas.
            accumulated_tool_calls (Dict[str, Any]): Dictionary of accumulated
                tool calls.

        Returns:
            bool: True if any tool call is complete, False otherwise.
        """

        for delta_tool_call in tool_call_deltas:
            index = delta_tool_call.index
            tool_call_id = getattr(delta_tool_call, 'id', None)

            # Initialize tool call entry if not exists
            if index not in accumulated_tool_calls:
                accumulated_tool_calls[index] = {
                    'id': '',
                    'type': 'function',
                    'function': {'name': '', 'arguments': ''},
                    'complete': False,
                }

            tool_call_entry = accumulated_tool_calls[index]

            # Accumulate tool call data
            if tool_call_id:
                tool_call_entry['id'] = (
                    tool_call_id  # Set full ID, don't append
                )

            if (
                hasattr(delta_tool_call, 'function')
                and delta_tool_call.function
            ):
                if delta_tool_call.function.name:
                    tool_call_entry['function']['name'] += (
                        delta_tool_call.function.name
                    )  # Append incremental name
                if delta_tool_call.function.arguments:
                    tool_call_entry['function']['arguments'] += (
                        delta_tool_call.function.arguments
                    )

        # Check if any tool calls are complete
        any_complete = False
        for _index, tool_call_entry in accumulated_tool_calls.items():
            if (
                tool_call_entry['id']
                and tool_call_entry['function']['name']
                and tool_call_entry['function']['arguments']
                and tool_call_entry['function']['name'] in self._internal_tools
            ):
                try:
                    # Try to parse arguments to check completeness
                    json.loads(tool_call_entry['function']['arguments'])
                    tool_call_entry['complete'] = True
                    any_complete = True
                except json.JSONDecodeError:
                    # Arguments not complete yet
                    tool_call_entry['complete'] = False

        return any_complete

    def _execute_tools_sync_with_status_accumulator(
        self,
        accumulated_tool_calls: Dict[str, Any],
        content_accumulator: StreamContentAccumulator,
        step_token_usage: Dict[str, int],
        tool_call_records: List[ToolCallingRecord],
    ) -> Generator[ChatAgentResponse, None, None]:
        r"""Execute multiple tools synchronously with
        proper content accumulation, using threads+queue for
        non-blocking status streaming."""

        def tool_worker(tool_func, args, result_queue, tool_call_data):
            try:
                tool_call_record = self._execute_tool_from_stream_data(
                    tool_call_data
                )
                result_queue.put(tool_call_record)
            except Exception as e:
                logger.error(f"Error in threaded tool execution: {e}")
                result_queue.put(None)

        tool_calls_to_execute = []
        for _tool_call_index, tool_call_data in accumulated_tool_calls.items():
            if tool_call_data.get('complete', False):
                tool_calls_to_execute.append(tool_call_data)

        # Phase 2: Execute tools in threads and yield status while waiting
        for tool_call_data in tool_calls_to_execute:
            function_name = tool_call_data['function']['name']
            try:
                args = json.loads(tool_call_data['function']['arguments'])
            except json.JSONDecodeError:
                args = tool_call_data['function']['arguments']
            result_queue: queue.Queue[Optional[ToolCallingRecord]] = (
                queue.Queue()
            )
            thread = threading.Thread(
                target=tool_worker,
                args=(
                    self._internal_tools[function_name],
                    args,
                    result_queue,
                    tool_call_data,
                ),
            )
            thread.start()

            status_message = (
                f"\nCalling function: {function_name} "
                f"with arguments:\n{args}\n"
            )
            status_status = self._create_tool_status_response_with_accumulator(
                content_accumulator,
                status_message,
                "tool_calling",
                step_token_usage,
            )
            yield status_status
            # wait for tool thread to finish with optional timeout
            thread.join(self.tool_execution_timeout)

            # If timeout occurred, mark as error and continue
            if thread.is_alive():
                timeout_msg = (
                    f"\nFunction '{function_name}' timed out after "
                    f"{self.tool_execution_timeout} seconds.\n---------\n"
                )
                timeout_status = (
                    self._create_tool_status_response_with_accumulator(
                        content_accumulator,
                        timeout_msg,
                        "tool_timeout",
                        step_token_usage,
                    )
                )
                yield timeout_status
                logger.error(timeout_msg.strip())
                # Detach thread (it may still finish later). Skip recording.
                continue

            # Tool finished, get result
            tool_call_record = result_queue.get()
            if tool_call_record:
                tool_call_records.append(tool_call_record)
                raw_result = tool_call_record.result
                result_str = str(raw_result)
                status_message = (
                    f"\nFunction output: {result_str}\n---------\n"
                )
                output_status = (
                    self._create_tool_status_response_with_accumulator(
                        content_accumulator,
                        status_message,
                        "tool_output",
                        step_token_usage,
                        [tool_call_record],
                    )
                )
                yield output_status
            else:
                # Error already logged
                continue

    def _execute_tool_from_stream_data(
        self, tool_call_data: Dict[str, Any]
    ) -> Optional[ToolCallingRecord]:
        r"""Execute a tool from accumulated stream data."""

        try:
            function_name = tool_call_data['function']['name']
            args = json.loads(tool_call_data['function']['arguments'])
            tool_call_id = tool_call_data['id']

            if function_name in self._internal_tools:
                tool = self._internal_tools[function_name]
                try:
                    result = tool(**args)

                    # Only record the tool response message, not the assistant
                    # message assistant message with tool_calls was already
                    # recorded in _record_assistant_tool_calls_message
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                    )

                    self.update_memory(func_msg, OpenAIBackendRole.FUNCTION)

                    return ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )

                except Exception as e:
                    error_msg = (
                        f"Error executing tool '{function_name}': {e!s}"
                    )
                    result = {"error": error_msg}
                    logging.warning(error_msg)

                    # Record error response
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                    )

                    self.update_memory(func_msg, OpenAIBackendRole.FUNCTION)

                    return ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )
            else:
                logger.warning(
                    f"Tool '{function_name}' not found in internal tools"
                )
                return None

        except Exception as e:
            logger.error(f"Error processing tool call: {e}")
            return None

    async def _aexecute_tool_from_stream_data(
        self, tool_call_data: Dict[str, Any]
    ) -> Optional[ToolCallingRecord]:
        r"""Async execute a tool from accumulated stream data."""

        try:
            function_name = tool_call_data['function']['name']
            args = json.loads(tool_call_data['function']['arguments'])
            tool_call_id = tool_call_data['id']

            if function_name in self._internal_tools:
                tool = self._internal_tools[function_name]
                try:
                    result = await tool.async_call(**args)

                    # Only record the tool response message, not the assistant
                    # message assistant message with tool_calls was already
                    # recorded in _record_assistant_tool_calls_message
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                    )

                    self.update_memory(func_msg, OpenAIBackendRole.FUNCTION)

                    return ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )

                except Exception as e:
                    error_msg = (
                        f"Error executing async tool '{function_name}': {e!s}"
                    )
                    result = {"error": error_msg}
                    logging.warning(error_msg)

                    # Record error response
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                    )

                    self.update_memory(func_msg, OpenAIBackendRole.FUNCTION)

                    return ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )
            else:
                logger.warning(
                    f"Tool '{function_name}' not found in internal tools"
                )
                return None

        except Exception as e:
            logger.error(f"Error processing async tool call: {e}")
            return None

    def _create_error_response(
        self, error_message: str, tool_call_records: List[ToolCallingRecord]
    ) -> ChatAgentResponse:
        r"""Create an error response for streaming."""

        error_msg = BaseMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict={},
            content=f"Error: {error_message}",
        )

        return ChatAgentResponse(
            msgs=[error_msg],
            terminated=True,
            info={
                "error": error_message,
                "tool_calls": tool_call_records,
                "streaming": True,
            },
        )

    async def _astream(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> AsyncGenerator[ChatAgentResponse, None]:
        r"""Asynchronous version of stream method."""

        # Convert input message to BaseMessage if necessary
        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )

        # Add user input to memory
        self.update_memory(input_message, OpenAIBackendRole.USER)

        # Get context for streaming
        try:
            openai_messages, num_tokens = self.memory.get_context()
        except RuntimeError as e:
            yield self._step_terminate(e.args[1], [], "max_tokens_exceeded")
            return

        # Start async streaming response
        async for response in self._astream_response(
            openai_messages, num_tokens, response_format
        ):
            yield response

    async def _astream_response(
        self,
        openai_messages: List[OpenAIMessage],
        num_tokens: int,
        response_format: Optional[Type[BaseModel]] = None,
    ) -> AsyncGenerator[ChatAgentResponse, None]:
        r"""Async method to handle streaming responses with tool calls."""

        tool_call_records: List[ToolCallingRecord] = []
        accumulated_tool_calls: Dict[str, Any] = {}
        step_token_usage = self._create_token_usage_tracker()

        # Create content accumulator for proper content management
        content_accumulator = StreamContentAccumulator()
        iteration_count = 0
        while True:
            # Check termination condition
            if self.stop_event and self.stop_event.is_set():
                yield self._step_terminate(
                    num_tokens, tool_call_records, "termination_triggered"
                )
                return

            # Get async streaming response from model
            try:
                response = await self.model_backend.arun(
                    openai_messages,
                    response_format,
                    self._get_full_tool_schemas() or None,
                )
                iteration_count += 1
            except Exception as exc:
                logger.error(
                    f"Error in async streaming model response: {exc}",
                    exc_info=exc,
                )
                yield self._create_error_response(str(exc), tool_call_records)
                return

            # Handle streaming response
            if isinstance(response, AsyncStream):
                stream_completed = False
                tool_calls_complete = False

                # Process chunks and forward them
                async for (
                    item
                ) in self._aprocess_stream_chunks_with_accumulator(
                    response,
                    content_accumulator,
                    accumulated_tool_calls,
                    tool_call_records,
                    step_token_usage,
                    response_format,
                ):
                    if isinstance(item, tuple):
                        # This is the final return value (stream_completed,
                        # tool_calls_complete)
                        stream_completed, tool_calls_complete = item
                        break
                    else:
                        # This is a ChatAgentResponse to be yielded
                        yield item

                if tool_calls_complete:
                    # Clear completed tool calls
                    accumulated_tool_calls.clear()

                    # If we executed tools and not in
                    # single iteration mode, continue
                    if tool_call_records and (
                        self.max_iteration is None
                        or iteration_count < self.max_iteration
                    ):
                        # Update messages with tool results for next iteration
                        try:
                            openai_messages, num_tokens = (
                                self.memory.get_context()
                            )
                        except RuntimeError as e:
                            yield self._step_terminate(
                                e.args[1],
                                tool_call_records,
                                "max_tokens_exceeded",
                            )
                            return
                        # Reset streaming content for next iteration
                        content_accumulator.reset_streaming_content()
                        continue
                    else:
                        break
                else:
                    # Stream completed without tool calls
                    accumulated_tool_calls.clear()
                    break
            elif hasattr(response, '__aenter__') and hasattr(
                response, '__aexit__'
            ):
                # Handle structured output stream
                # (AsyncChatCompletionStreamManager)
                async with response as stream:
                    parsed_object = None

                    async for event in stream:
                        if event.type == "content.delta":
                            if getattr(event, "delta", None):
                                # Use accumulator for proper content management
                                partial_response = self._create_streaming_response_with_accumulator(  # noqa: E501
                                    content_accumulator,
                                    getattr(event, "delta", ""),
                                    step_token_usage,
                                    tool_call_records=tool_call_records.copy(),
                                )
                                yield partial_response

                        elif event.type == "content.done":
                            parsed_object = getattr(event, "parsed", None)
                            break
                        elif event.type == "error":
                            logger.error(
                                f"Error in async structured stream: "
                                f"{getattr(event, 'error', '')}"
                            )
                            yield self._create_error_response(
                                str(getattr(event, 'error', '')),
                                tool_call_records,
                            )
                            return

                    # Get final completion and record final message
                    try:
                        final_completion = await stream.get_final_completion()
                        final_content = (
                            final_completion.choices[0].message.content or ""
                        )

                        final_message = BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict={},
                            content=final_content,
                            parsed=cast(
                                "BaseModel | dict[str, Any] | None",
                                parsed_object,
                            ),  # type: ignore[arg-type]
                        )

                        self.record_message(final_message)

                        # Create final response
                        final_response = ChatAgentResponse(
                            msgs=[final_message],
                            terminated=False,
                            info={
                                "id": final_completion.id or "",
                                "usage": safe_model_dump(
                                    final_completion.usage
                                )
                                if final_completion.usage
                                else {},
                                "finish_reasons": [
                                    choice.finish_reason or "stop"
                                    for choice in final_completion.choices
                                ],
                                "num_tokens": self._get_token_count(
                                    final_content
                                ),
                                "tool_calls": tool_call_records,
                                "external_tool_requests": None,
                                "streaming": False,
                                "partial": False,
                            },
                        )
                        yield final_response
                        break

                    except Exception as e:
                        logger.error(
                            f"Error getting async final completion: {e}"
                        )
                        yield self._create_error_response(
                            str(e), tool_call_records
                        )
                        return
            else:
                # Handle non-streaming response (fallback)
                model_response = self._handle_batch_response(response)
                yield self._convert_to_chatagent_response(
                    model_response,
                    tool_call_records,
                    num_tokens,
                    None,
                    model_response.usage_dict.get("prompt_tokens", 0),
                    model_response.usage_dict.get("completion_tokens", 0),
                    model_response.usage_dict.get("total_tokens", 0),
                )
                accumulated_tool_calls.clear()
                break

    def _record_assistant_tool_calls_message(
        self, accumulated_tool_calls: Dict[str, Any], content: str = ""
    ) -> None:
        r"""Record the assistant message that contains tool calls.

        This method creates and records an assistant message that includes
        the tool calls information, which is required by OpenAI's API format.
        """
        # Create a BaseMessage with tool_calls information in meta_dict
        # This will be converted to the proper OpenAI format when needed
        tool_calls_list = []
        for tool_call_data in accumulated_tool_calls.values():
            if tool_call_data.get('complete', False):
                tool_call_dict = {
                    "id": tool_call_data["id"],
                    "type": "function",
                    "function": {
                        "name": tool_call_data["function"]["name"],
                        "arguments": tool_call_data["function"]["arguments"],
                    },
                }
                tool_calls_list.append(tool_call_dict)

        # Create an assistant message with tool calls
        assist_msg = BaseMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict={"tool_calls": tool_calls_list},
            content=content or "",
        )

        # Record this assistant message
        self.update_memory(assist_msg, OpenAIBackendRole.ASSISTANT)

    async def _aprocess_stream_chunks_with_accumulator(
        self,
        stream: AsyncStream[ChatCompletionChunk],
        content_accumulator: StreamContentAccumulator,
        accumulated_tool_calls: Dict[str, Any],
        tool_call_records: List[ToolCallingRecord],
        step_token_usage: Dict[str, int],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> AsyncGenerator[Union[ChatAgentResponse, Tuple[bool, bool]], None]:
        r"""Async version of process streaming chunks with
        content accumulator."""

        tool_calls_complete = False
        stream_completed = False

        async for chunk in stream:
            # Update token usage if available
            if chunk.usage:
                self._update_token_usage_tracker(
                    step_token_usage, safe_model_dump(chunk.usage)
                )

            # Process chunk delta
            if chunk.choices and len(chunk.choices) > 0:
                choice = chunk.choices[0]
                delta = choice.delta

                # Handle content streaming
                if delta.content:
                    # Use accumulator for proper content management
                    partial_response = (
                        self._create_streaming_response_with_accumulator(
                            content_accumulator,
                            delta.content,
                            step_token_usage,
                            getattr(chunk, 'id', ''),
                            tool_call_records.copy(),
                        )
                    )
                    yield partial_response

                # Handle tool calls streaming
                if delta.tool_calls:
                    tool_calls_complete = self._accumulate_tool_calls(
                        delta.tool_calls, accumulated_tool_calls
                    )

                # Check if stream is complete
                if choice.finish_reason:
                    stream_completed = True

                    # If we have complete tool calls, execute them with
                    # async status updates
                    if accumulated_tool_calls:
                        # Record assistant message with
                        # tool calls first
                        self._record_assistant_tool_calls_message(
                            accumulated_tool_calls,
                            content_accumulator.get_full_content(),
                        )

                        # Execute tools asynchronously with real-time
                        # status updates
                        async for (
                            status_response
                        ) in self._execute_tools_async_with_status_accumulator(
                            accumulated_tool_calls,
                            content_accumulator,
                            step_token_usage,
                            tool_call_records,
                        ):
                            yield status_response

                        # Yield "Sending back result to model" status
                        if tool_call_records:
                            sending_status = self._create_tool_status_response_with_accumulator(  # noqa: E501
                                content_accumulator,
                                "\n------\n\nSending back result to model\n\n",
                                "tool_sending",
                                step_token_usage,
                            )
                            yield sending_status

                    # Record final message only if we have content AND no tool
                    # calls. If there are tool calls, _record_tool_calling
                    # will handle message recording.
                    final_content = content_accumulator.get_full_content()
                    if final_content.strip() and not accumulated_tool_calls:
                        final_message = BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict={},
                            content=final_content,
                        )

                        if response_format:
                            self._try_format_message(
                                final_message, response_format
                            )

                        self.record_message(final_message)
                    break

        # Yield the final status as a tuple
        yield (stream_completed, tool_calls_complete)

    async def _execute_tools_async_with_status_accumulator(
        self,
        accumulated_tool_calls: Dict[str, Any],
        content_accumulator: StreamContentAccumulator,
        step_token_usage: Dict[str, int],
        tool_call_records: List[ToolCallingRecord],
    ) -> AsyncGenerator[ChatAgentResponse, None]:
        r"""Execute multiple tools asynchronously with
        proper content accumulation."""
        import asyncio

        # Phase 1: Start all tools and yield "Calling function"
        # statuses immediately
        tool_tasks = []
        for _tool_call_index, tool_call_data in accumulated_tool_calls.items():
            if tool_call_data.get('complete', False):
                function_name = tool_call_data['function']['name']
                try:
                    args = json.loads(tool_call_data['function']['arguments'])
                except json.JSONDecodeError:
                    args = tool_call_data['function']['arguments']

                status_message = (
                    f"\nCalling function: {function_name} "
                    f"with arguments:\n{args}\n"
                )

                # Immediately yield "Calling function" status
                calling_status = (
                    self._create_tool_status_response_with_accumulator(
                        content_accumulator,
                        status_message,
                        "tool_calling",
                        step_token_usage,
                    )
                )
                yield calling_status

                # Start tool execution asynchronously (non-blocking)
                if self.tool_execution_timeout is not None:
                    task = asyncio.create_task(
                        asyncio.wait_for(
                            self._aexecute_tool_from_stream_data(
                                tool_call_data
                            ),
                            timeout=self.tool_execution_timeout,
                        )
                    )
                else:
                    task = asyncio.create_task(
                        self._aexecute_tool_from_stream_data(tool_call_data)
                    )
                tool_tasks.append((task, tool_call_data))

        # Phase 2: Wait for tools to complete and yield results as they finish
        if tool_tasks:
            # Use asyncio.as_completed for true async processing
            for completed_task in asyncio.as_completed(
                [task for task, _ in tool_tasks]
            ):
                try:
                    tool_call_record = await completed_task
                    if tool_call_record:
                        # Add to the shared tool_call_records list
                        tool_call_records.append(tool_call_record)

                        # Create output status message
                        raw_result = tool_call_record.result
                        result_str = str(raw_result)
                        status_message = (
                            f"\nFunction output: {result_str}\n---------\n"
                        )

                        # Yield "Function output" status as soon as this
                        # tool completes
                        output_status = (
                            self._create_tool_status_response_with_accumulator(
                                content_accumulator,
                                status_message,
                                "tool_output",
                                step_token_usage,
                                [tool_call_record],
                            )
                        )
                        yield output_status

                except Exception as e:
                    if isinstance(e, asyncio.TimeoutError):
                        timeout_msg = (
                            f"\nFunction timed out after "
                            f"{self.tool_execution_timeout} seconds.\n"
                            f"---------\n"
                        )
                        timeout_status = (
                            self._create_tool_status_response_with_accumulator(
                                content_accumulator,
                                timeout_msg,
                                "tool_timeout",
                                step_token_usage,
                            )
                        )
                        yield timeout_status
                        logger.error("Async tool execution timeout")
                    else:
                        logger.error(f"Error in async tool execution: {e}")
                    continue

    def _create_tool_status_response_with_accumulator(
        self,
        accumulator: StreamContentAccumulator,
        status_message: str,
        status_type: str,
        step_token_usage: Dict[str, int],
        tool_calls: Optional[List[ToolCallingRecord]] = None,
    ) -> ChatAgentResponse:
        r"""Create a tool status response using content accumulator."""

        # Add this status message to accumulator and get full content
        accumulator.add_tool_status(status_message)
        full_content = accumulator.get_full_content()

        message = BaseMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict={},
            content=full_content,
        )

        return ChatAgentResponse(
            msgs=[message],
            terminated=False,
            info={
                "id": "",
                "usage": step_token_usage.copy(),
                "finish_reasons": [status_type],
                "num_tokens": self._get_token_count(full_content),
                "tool_calls": tool_calls or [],
                "external_tool_requests": None,
                "streaming": True,
                "tool_status": status_type,
                "partial": True,
            },
        )

    def _create_streaming_response_with_accumulator(
        self,
        accumulator: StreamContentAccumulator,
        new_content: str,
        step_token_usage: Dict[str, int],
        response_id: str = "",
        tool_call_records: Optional[List[ToolCallingRecord]] = None,
    ) -> ChatAgentResponse:
        r"""Create a streaming response using content accumulator."""

        # Add new content to accumulator and get full content
        accumulator.add_streaming_content(new_content)
        full_content = accumulator.get_full_content()

        message = BaseMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict={},
            content=full_content,
        )

        return ChatAgentResponse(
            msgs=[message],
            terminated=False,
            info={
                "id": response_id,
                "usage": step_token_usage.copy(),
                "finish_reasons": ["streaming"],
                "num_tokens": self._get_token_count(full_content),
                "tool_calls": tool_call_records or [],
                "external_tool_requests": None,
                "streaming": True,
                "partial": True,
            },
        )

    def get_usage_dict(
        self, output_messages: List[BaseMessage], prompt_tokens: int
    ) -> Dict[str, int]:
        r"""Get usage dictionary when using the stream mode.

        Args:
            output_messages (list): List of output messages.
            prompt_tokens (int): Number of input prompt tokens.

        Returns:
            dict: Usage dictionary.
        """
        encoding = get_model_encoding(self.model_type.value_for_tiktoken)
        completion_tokens = sum(
            len(encoding.encode(message.content))
            for message in output_messages
        )
        return dict(
            completion_tokens=completion_tokens,
            prompt_tokens=prompt_tokens,
            total_tokens=completion_tokens + prompt_tokens,
        )

    def add_model_scheduling_strategy(self, name: str, strategy_fn: Callable):
        r"""Add a scheduling strategy method provided by user to ModelManger.

        Args:
            name (str): The name of the strategy.
            strategy_fn (Callable): The scheduling strategy function.
        """
        self.model_backend.add_strategy(name, strategy_fn)

    def clone(self, with_memory: bool = False) -> ChatAgent:
        r"""Creates a new instance of :obj:`ChatAgent` with the same
        configuration as the current instance.

        Args:
            with_memory (bool): Whether to copy the memory (conversation
                history) to the new agent. If True, the new agent will have
                the same conversation history. If False, the new agent will
                have a fresh memory with only the system message.
                (default: :obj:`False`)

        Returns:
            ChatAgent: A new instance of :obj:`ChatAgent` with the same
                configuration.
        """
        # Create a new instance with the same configuration
        # If with_memory is True, set system_message to None
        # If with_memory is False, use the original system message
        # To avoid duplicated system memory.
        system_message = None if with_memory else self._original_system_message

        new_agent = ChatAgent(
            system_message=system_message,
            model=self.model_backend.models,  # Pass the existing model_backend
            memory=None,  # clone memory later
            message_window_size=getattr(self.memory, "window_size", None),
            token_limit=getattr(
                self.memory.get_context_creator(), "token_limit", None
            ),
            output_language=self._output_language,
            tools=self._clone_tools(),
            external_tools=[
                schema for schema in self._external_tool_schemas.values()
            ],
            response_terminators=self.response_terminators,
            scheduling_strategy=(
                self.model_backend.scheduling_strategy.__name__
            ),
            max_iteration=self.max_iteration,
            stop_event=self.stop_event,
            tool_execution_timeout=self.tool_execution_timeout,
            pause_event=self.pause_event,
        )

        # Copy memory if requested
        if with_memory:
            # Get all records from the current memory
            context_records = self.memory.retrieve()
            # Write them to the new agent's memory
            for context_record in context_records:
                new_agent.memory.write_record(context_record.memory_record)

        return new_agent

    def _clone_tools(self) -> List[Union[FunctionTool, Callable]]:
        r"""Clone tools for new agent instance,
        handling stateful toolkits properly."""
        cloned_tools = []
        hybrid_browser_toolkits = {}  # Cache for created toolkits

        for tool in self._internal_tools.values():
            # Check if this is a HybridBrowserToolkit method
            if (
                hasattr(tool.func, '__self__')
                and tool.func.__self__.__class__.__name__
                == 'HybridBrowserToolkit'
            ):
                toolkit_instance = tool.func.__self__
                toolkit_id = id(toolkit_instance)

                # Check if we already created a clone for this toolkit
                if toolkit_id not in hybrid_browser_toolkits:
                    try:
                        import uuid

                        new_session_id = str(uuid.uuid4())[:8]
                        new_toolkit = toolkit_instance.clone_for_new_session(
                            new_session_id
                        )
                        hybrid_browser_toolkits[toolkit_id] = new_toolkit
                    except Exception as e:
                        logger.warning(
                            f"Failed to clone HybridBrowserToolkit: {e}"
                        )
                        # Fallback to original function
                        cloned_tools.append(tool.func)
                        continue

                # Get the corresponding method from the cloned toolkit
                new_toolkit = hybrid_browser_toolkits[toolkit_id]
                method_name = tool.func.__name__
                if hasattr(new_toolkit, method_name):
                    new_method = getattr(new_toolkit, method_name)
                    cloned_tools.append(new_method)
                else:
                    # Fallback to original function
                    cloned_tools.append(tool.func)
            else:
                # Regular tool or other stateless toolkit
                # just use the original function
                cloned_tools.append(tool.func)

        return cloned_tools

    def __repr__(self) -> str:
        r"""Returns a string representation of the :obj:`ChatAgent`.

        Returns:
            str: The string representation of the :obj:`ChatAgent`.
        """
        return (
            f"ChatAgent({self.role_name}, {self.role_type}, {self.model_type})"
        )

    @dependencies_required("mcp")
    def to_mcp(
        self,
        name: str = "CAMEL-ChatAgent",
        description: str = "A helpful assistant using the CAMEL AI framework.",
        dependencies: Optional[List[str]] = None,
        host: str = "localhost",
        port: int = 8000,
    ):
        r"""Expose this ChatAgent as an MCP server.

        Args:
            name (str): Name of the MCP server.
                (default: :obj:`CAMEL-ChatAgent`)
            description (Optional[List[str]]): Description of the agent. If
                None, a generic description is used. (default: :obj:`A helpful
                assistant using the CAMEL AI framework.`)
            dependencies (Optional[List[str]]): Additional
                dependencies for the MCP server. (default: :obj:`None`)
            host (str): Host to bind to for HTTP transport.
                (default: :obj:`localhost`)
            port (int): Port to bind to for HTTP transport.
                (default: :obj:`8000`)

        Returns:
            FastMCP: An MCP server instance that can be run.
        """
        from mcp.server.fastmcp import FastMCP

        # Combine dependencies
        all_dependencies = ["camel-ai[all]"]
        if dependencies:
            all_dependencies.extend(dependencies)

        mcp_server = FastMCP(
            name,
            dependencies=all_dependencies,
            host=host,
            port=port,
        )

        # Store agent reference
        agent_instance = self

        # Define functions first
        async def step(message, response_format=None):
            r"""Execute a single step in the chat session with the agent."""
            format_cls = None
            if response_format:
                format_cls = model_from_json_schema(
                    "DynamicResponseFormat", response_format
                )
            response = await agent_instance.astep(message, format_cls)
            return {
                "status": "success",
                "messages": [msg.to_dict() for msg in response.msgs],
                "terminated": response.terminated,
                "info": response.info,
            }

        # Reset tool
        def reset():
            r"""Reset the chat agent to its initial state."""
            agent_instance.reset()
            return {"status": "success", "message": "Agent reset successfully"}

        # Set language tool
        def set_output_language(language):
            r"""Set the output language for the chat agent."""
            agent_instance.output_language = language
            return {
                "status": "success",
                "message": f"Output language set to '{language}'",
            }

        # Agent info resource and tool
        def get_agent_info():
            r"""Get information about the agent."""
            info = {
                "agent_id": agent_instance.agent_id,
                "model_type": str(agent_instance.model_type),
                "role_name": agent_instance.role_name,
                "role_type": str(agent_instance.role_type),
                "output_language": agent_instance.output_language or "None",
                "description": description,
            }
            return info

        # Chat history resource and tool
        def get_chat_history():
            r"""Get the chat history for the agent."""
            # Convert messages to simple serializable format
            messages = []
            for msg in agent_instance.chat_history:
                # Create a simplified version of each message
                msg_dict = {
                    "role": msg.get("role", ""),
                    "content": msg.get("content", ""),
                }
                # Include function calls if present
                if "function_call" in msg:
                    msg_dict["function_call"] = {
                        "name": msg["function_call"].get("name", ""),
                        "arguments": msg["function_call"].get("arguments", ""),
                    }
                messages.append(msg_dict)
            return messages

        # Available tools resource and tool
        def get_available_tools():
            r"""Get a list of available internal tools."""
            tool_info = {}
            for name, tool in agent_instance.tool_dict.items():
                tool_info[name] = {
                    "name": name,
                    "description": tool.get_function_description() or "",
                    "parameters": [
                        {"name": param_name, "type": str(param_type)}
                        for param_name, param_type in tool.parameters.items()
                    ],
                }
            return tool_info

        # Now register everything using decorators
        mcp_server.tool()(step)
        mcp_server.tool()(reset)
        mcp_server.tool()(set_output_language)

        mcp_server.resource("agent://")(get_agent_info)
        mcp_server.tool()(get_agent_info)

        mcp_server.resource("history://")(get_chat_history)
        mcp_server.tool()(get_chat_history)

        mcp_server.resource("tools://")(get_available_tools)
        mcp_server.tool()(get_available_tools)

        return mcp_server
