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
import atexit
import base64
import concurrent.futures
import hashlib
import inspect
import json
import os
import random
import re
import tempfile
import textwrap
import threading
import time
import uuid
import warnings
from dataclasses import dataclass
from datetime import datetime
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
    RateLimitError,
    Stream,
)
from pydantic import BaseModel, ValidationError

from camel.agents._types import ModelResponse, ToolCallRequest
from camel.agents._utils import (
    build_default_summary_prompt,
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
    ContextRecord,
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
from camel.toolkits import FunctionTool, RegisteredAgentToolkit
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
    Constants,
    get_model_encoding,
    model_from_json_schema,
)
from camel.utils.commons import dependencies_required
from camel.utils.context_utils import ContextUtility

TOKEN_LIMIT_ERROR_MARKERS = (
    "context_length_exceeded",
    "prompt is too long",
    "exceeded your current quota",
    "tokens must be reduced",
    "context length",
    "token count",
    "context limit",
)

if TYPE_CHECKING:
    from camel.terminators import ResponseTerminator

logger = get_logger(__name__)

# Cleanup temp files on exit
_temp_files: Set[str] = set()
_temp_files_lock = threading.Lock()


def _cleanup_temp_files():
    with _temp_files_lock:
        for path in _temp_files:
            try:
                os.unlink(path)
            except Exception:
                pass


atexit.register(_cleanup_temp_files)

# AgentOps decorator setting
try:
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


@dataclass
class _ToolOutputHistoryEntry:
    tool_name: str
    tool_call_id: str
    result_text: str
    record_uuids: List[str]
    record_timestamps: List[float]
    cached: bool = False


class StreamContentAccumulator:
    r"""Manages content accumulation across streaming responses to ensure
    all responses contain complete cumulative content."""

    def __init__(self):
        self.base_content = ""  # Content before tool calls
        self.current_content = []  # Accumulated streaming fragments
        self.tool_status_messages = []  # Accumulated tool status messages
        self.reasoning_content = []  # Accumulated reasoning content
        self.is_reasoning_phase = True  # Track if we're in reasoning phase

    def set_base_content(self, content: str):
        r"""Set the base content (usually empty or pre-tool content)."""
        self.base_content = content

    def add_streaming_content(self, new_content: str):
        r"""Add new streaming content."""
        self.current_content.append(new_content)
        self.is_reasoning_phase = (
            False  # Once we get content, we're past reasoning
        )

    def add_reasoning_content(self, new_reasoning: str):
        r"""Add new reasoning content."""
        self.reasoning_content.append(new_reasoning)

    def add_tool_status(self, status_message: str):
        r"""Add a tool status message."""
        self.tool_status_messages.append(status_message)

    def get_full_content(self) -> str:
        r"""Get the complete accumulated content."""
        tool_messages = "".join(self.tool_status_messages)
        current = "".join(self.current_content)
        return self.base_content + tool_messages + current

    def get_full_reasoning_content(self) -> str:
        r"""Get the complete accumulated reasoning content."""
        return "".join(self.reasoning_content)

    def get_content_with_new_status(self, status_message: str) -> str:
        r"""Get content with a new status message appended."""
        tool_messages = "".join([*self.tool_status_messages, status_message])
        current = "".join(self.current_content)
        return self.base_content + tool_messages + current

    def reset_streaming_content(self):
        r"""Reset only the streaming content, keep base and tool status."""
        self.current_content = []
        self.reasoning_content = []
        self.is_reasoning_phase = True


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
            for response in self._generator:
                self._responses.append(response)
                self._current_response = response
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
            yield from self._responses
        else:
            # If not consumed, consume and yield
            for response in self._generator:
                self._responses.append(response)
                self._current_response = response
                yield response
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
            async for response in self._async_generator:
                self._responses.append(response)
                self._current_response = response
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
                async for response in self._async_generator:
                    self._responses.append(response)
                    self._current_response = response
                    yield response
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
        summarize_threshold (int, optional): The percentage of the context
            window that triggers summarization. If `None`, will trigger
            summarization when the context window is full.
            (default: :obj:`None`)
        output_language (str, optional): The language to be output by the
            agent. (default: :obj:`None`)
        tools (Optional[List[Union[FunctionTool, Callable]]], optional): List
            of available :obj:`FunctionTool` or :obj:`Callable`. (default:
            :obj:`None`)
        toolkits_to_register_agent (Optional[List[RegisteredAgentToolkit]],
            optional): List of toolkit instances that inherit from
            :obj:`RegisteredAgentToolkit`. The agent will register itself with
            these toolkits, allowing them to access the agent instance. Note:
            This does NOT add the toolkit's tools to the agent. To use tools
            from these toolkits, pass them explicitly via the `tools`
            parameter. (default: :obj:`None`)
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
        pause_event (Optional[Union[threading.Event, asyncio.Event]]): Event to
            signal pause of the agent's operation. When clear, the agent will
            pause its execution. Use threading.Event for sync operations or
            asyncio.Event for async operations. (default: :obj:`None`)
        prune_tool_calls_from_memory (bool): Whether to clean tool
            call messages from memory after response generation to save token
            usage. When enabled, removes FUNCTION/TOOL role messages and
            ASSISTANT messages with tool_calls after each step.
            (default: :obj:`False`)
        enable_snapshot_clean (bool, optional): Whether to clean snapshot
            markers and references from historical tool outputs in memory.
            This removes verbose DOM markers (like [ref=...]) from older tool
            results while keeping the latest output intact for immediate use.
            (default: :obj:`False`)
        retry_attempts (int, optional): Maximum number of retry attempts for
            rate limit errors. (default: :obj:`3`)
        retry_delay (float, optional): Initial delay in seconds between
            retries. Uses exponential backoff. (default: :obj:`1.0`)
        step_timeout (Optional[float], optional): Timeout in seconds for the
            entire step operation. If None, no timeout is applied.
            (default: :obj:`None`)
        stream_accumulate (bool, optional): When True, partial streaming
            updates return accumulated content (current behavior). When False,
            partial updates return only the incremental delta. (default:
            :obj:`True`)
        summary_window_ratio (float, optional): Maximum fraction of the total
            context window that can be occupied by summary information. Used
            to limit how much of the model's context is reserved for
            summarization results. (default: :obj:`0.6`)
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
        summarize_threshold: Optional[int] = 50,
        token_limit: Optional[int] = None,
        output_language: Optional[str] = None,
        tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        toolkits_to_register_agent: Optional[
            List[RegisteredAgentToolkit]
        ] = None,
        external_tools: Optional[
            List[Union[FunctionTool, Callable, Dict[str, Any]]]
        ] = None,
        response_terminators: Optional[List[ResponseTerminator]] = None,
        scheduling_strategy: str = "round_robin",
        max_iteration: Optional[int] = None,
        agent_id: Optional[str] = None,
        stop_event: Optional[threading.Event] = None,
        tool_execution_timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD,
        mask_tool_output: bool = False,
        pause_event: Optional[Union[threading.Event, asyncio.Event]] = None,
        prune_tool_calls_from_memory: bool = False,
        enable_snapshot_clean: bool = False,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        step_timeout: Optional[float] = Constants.TIMEOUT_THRESHOLD,
        stream_accumulate: bool = True,
        summary_window_ratio: float = 0.6,
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

        self._enable_snapshot_clean = enable_snapshot_clean
        self._tool_output_history: List[_ToolOutputHistoryEntry] = []

        # Set up memory
        context_creator = ScoreBasedContextCreator(
            self.model_backend.token_counter,
            self.model_backend.token_limit,
        )

        self._memory: AgentMemory = memory or ChatHistoryMemory(
            context_creator,
            window_size=message_window_size,
            agent_id=self.agent_id,
        )

        # So we don't have to pass agent_id when we define memory
        if memory is not None:
            self._memory.agent_id = self.agent_id

        # Set up system message and initialize messages
        self._original_system_message = (
            BaseMessage.make_system_message(system_message)
            if isinstance(system_message, str)
            else system_message
        )
        self._output_language = output_language
        self._system_message = (
            self._generate_system_message_for_output_language()
        )
        self.init_messages()

        # Set up summarize threshold with validation
        if summarize_threshold is not None:
            if not (0 < summarize_threshold <= 100):
                raise ValueError(
                    f"summarize_threshold must be between 0 and 100, "
                    f"got {summarize_threshold}"
                )
            logger.info(
                f"Automatic context compression is enabled. Will trigger "
                f"summarization when context window exceeds "
                f"{summarize_threshold}% of the total token limit."
            )
        self.summarize_threshold = summarize_threshold
        self._reset_summary_state()

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

        # Register agent with toolkits that have RegisteredAgentToolkit mixin
        if toolkits_to_register_agent:
            for toolkit in toolkits_to_register_agent:
                if isinstance(toolkit, RegisteredAgentToolkit):
                    toolkit.register_agent(self)

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
        self._secure_result_store_lock = threading.Lock()
        self.pause_event = pause_event
        self.prune_tool_calls_from_memory = prune_tool_calls_from_memory
        self.retry_attempts = max(1, retry_attempts)
        self.retry_delay = max(0.0, retry_delay)
        self.step_timeout = step_timeout
        self._context_utility: Optional[ContextUtility] = None
        self._context_summary_agent: Optional["ChatAgent"] = None
        self.stream_accumulate = stream_accumulate
        self._last_tool_call_record: Optional[ToolCallingRecord] = None
        self._last_tool_call_signature: Optional[str] = None
        self._last_token_limit_tool_signature: Optional[str] = None
        self.summary_window_ratio = summary_window_ratio

    def reset(self):
        r"""Resets the :obj:`ChatAgent` to its initial state."""
        self.terminated = False
        self.init_messages()
        self._reset_summary_state()
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

    @property
    def memory(self) -> AgentMemory:
        r"""Returns the agent memory."""
        return self._memory

    @memory.setter
    def memory(self, value: AgentMemory) -> None:
        r"""Set the agent memory.

        When setting a new memory, the system message is automatically
        re-added to ensure it's not lost.

        Args:
            value (AgentMemory): The new agent memory to use.
        """
        self._memory = value
        # Ensure the new memory has the system message
        self.init_messages()

    def set_context_utility(
        self, context_utility: Optional[ContextUtility]
    ) -> None:
        r"""Set the context utility for the agent.

        This allows external components (like SingleAgentWorker) to provide
        a shared context utility instance for workflow management.

        Args:
            context_utility (ContextUtility, optional): The context utility
                to use. If None, the agent will create its own when needed.
        """
        self._context_utility = context_utility

    def _get_full_tool_schemas(self) -> List[Dict[str, Any]]:
        r"""Returns a list of tool schemas of all tools, including internal
        and external tools.
        """
        return list(self._external_tool_schemas.values()) + [
            func_tool.get_openai_tool_schema()
            for func_tool in self._internal_tools.values()
        ]

    @staticmethod
    def _is_token_limit_error(error: Exception) -> bool:
        r"""Return True when the exception message indicates a token limit."""
        error_message = str(error).lower()
        return any(
            marker in error_message for marker in TOKEN_LIMIT_ERROR_MARKERS
        )

    @staticmethod
    def _is_tool_related_record(record: MemoryRecord) -> bool:
        r"""Determine whether the given memory record
        belongs to a tool call."""
        if record.role_at_backend in {
            OpenAIBackendRole.TOOL,
            OpenAIBackendRole.FUNCTION,
        }:
            return True

        if (
            record.role_at_backend == OpenAIBackendRole.ASSISTANT
            and isinstance(record.message, FunctionCallingMessage)
        ):
            return True

        return False

    def _find_indices_to_remove_for_last_tool_pair(
        self, recent_records: List[ContextRecord]
    ) -> List[int]:
        """Find indices of records that should be removed to clean up the most
        recent incomplete tool interaction pair.

        This method identifies tool call/result pairs by tool_call_id and
        returns the exact indices to remove, allowing non-contiguous deletions.

        Logic:
        - If the last record is a tool result (TOOL/FUNCTION) with a
          tool_call_id, find the matching assistant call anywhere in history
          and return both indices.
        - If the last record is an assistant tool call without a result yet,
          return just that index.
        - For normal messages (non tool-related): remove just the last one.
        - Fallback: If no tool_call_id is available, use heuristic (last 2 if
          tool-related, otherwise last 1).

        Returns:
            List[int]: Indices to remove (may be non-contiguous).
        """
        if not recent_records:
            return []

        last_idx = len(recent_records) - 1
        last_record = recent_records[last_idx].memory_record

        # Case A: Last is an ASSISTANT tool call with no result yet
        if (
            last_record.role_at_backend == OpenAIBackendRole.ASSISTANT
            and isinstance(last_record.message, FunctionCallingMessage)
            and last_record.message.result is None
        ):
            return [last_idx]

        # Case B: Last is TOOL/FUNCTION result, try id-based pairing
        if last_record.role_at_backend in {
            OpenAIBackendRole.TOOL,
            OpenAIBackendRole.FUNCTION,
        }:
            tool_id = None
            if isinstance(last_record.message, FunctionCallingMessage):
                tool_id = last_record.message.tool_call_id

            if tool_id:
                for idx in range(len(recent_records) - 2, -1, -1):
                    rec = recent_records[idx].memory_record
                    if rec.role_at_backend != OpenAIBackendRole.ASSISTANT:
                        continue

                    # Check if this assistant message contains the tool_call_id
                    matched = False

                    # Case 1: FunctionCallingMessage (single tool call)
                    if isinstance(rec.message, FunctionCallingMessage):
                        if rec.message.tool_call_id == tool_id:
                            matched = True

                    # Case 2: BaseMessage with multiple tool_calls in meta_dict
                    elif (
                        hasattr(rec.message, "meta_dict")
                        and rec.message.meta_dict
                    ):
                        tool_calls_list = rec.message.meta_dict.get(
                            "tool_calls", []
                        )
                        if isinstance(tool_calls_list, list):
                            for tc in tool_calls_list:
                                if (
                                    isinstance(tc, dict)
                                    and tc.get("id") == tool_id
                                ):
                                    matched = True
                                    break

                    if matched:
                        # Return both assistant call and tool result indices
                        return [idx, last_idx]

            # Fallback: no tool_call_id, use heuristic
            if self._is_tool_related_record(last_record):
                # Remove last 2 (assume they are paired)
                return [last_idx - 1, last_idx] if last_idx > 0 else [last_idx]
            else:
                return [last_idx]

        # Default: non tool-related tail => remove last one
        return [last_idx]

    @staticmethod
    def _serialize_tool_args(args: Dict[str, Any]) -> str:
        try:
            return json.dumps(args, ensure_ascii=False, sort_keys=True)
        except TypeError:
            return str(args)

    @classmethod
    def _build_tool_signature(
        cls, func_name: str, args: Dict[str, Any]
    ) -> str:
        args_repr = cls._serialize_tool_args(args)
        return f"{func_name}:{args_repr}"

    def _describe_tool_call(
        self, record: Optional[ToolCallingRecord]
    ) -> Optional[str]:
        if record is None:
            return None
        args_repr = self._serialize_tool_args(record.args)
        return f"Tool `{record.tool_name}` invoked with arguments {args_repr}."

    def _update_last_tool_call_state(
        self, record: Optional[ToolCallingRecord]
    ) -> None:
        """Track the most recent tool call and its identifying signature."""
        self._last_tool_call_record = record
        if record is None:
            self._last_tool_call_signature = None
            return

        args = (
            record.args
            if isinstance(record.args, dict)
            else {"_raw": record.args}
        )
        try:
            signature = self._build_tool_signature(record.tool_name, args)
        except Exception:  # pragma: no cover - defensive guard
            signature = None
        self._last_tool_call_signature = signature

    def _format_tool_limit_notice(self) -> Optional[str]:
        record = self._last_tool_call_record
        description = self._describe_tool_call(record)
        if description is None:
            return None
        notice_lines = [
            "[Tool Call Causing Token Limit]",
            description,
        ]

        if record is not None:
            result = record.result
            if isinstance(result, bytes):
                result_repr = result.decode(errors="replace")
            elif isinstance(result, str):
                result_repr = result
            else:
                try:
                    result_repr = json.dumps(
                        result, ensure_ascii=False, sort_keys=True
                    )
                except (TypeError, ValueError):
                    result_repr = str(result)

            result_length = len(result_repr)
            notice_lines.append(f"Tool result length: {result_length}")
            if self.model_backend.token_limit != 999999999:
                notice_lines.append(
                    f"Token limit: {self.model_backend.token_limit}"
                )

        return "\n".join(notice_lines)

    @staticmethod
    def _append_user_messages_section(
        summary_content: str, user_messages: List[str]
    ) -> str:
        section_title = "- **All User Messages**:"
        sanitized_messages: List[str] = []
        for msg in user_messages:
            if not isinstance(msg, str):
                msg = str(msg)
            cleaned = " ".join(msg.strip().splitlines())
            if cleaned:
                sanitized_messages.append(cleaned)

        bullet_block = (
            "\n".join(f"- {m}" for m in sanitized_messages)
            if sanitized_messages
            else "- None noted"
        )
        user_section = f"{section_title}\n{bullet_block}"

        summary_clean = summary_content.rstrip()
        separator = "\n\n" if summary_clean else ""
        return f"{summary_clean}{separator}{user_section}"

    def _reset_summary_state(self) -> None:
        self._summary_token_count = 0  # Total tokens in summary messages

    def _calculate_next_summary_threshold(self) -> int:
        r"""Calculate the next token threshold that should trigger
        summarization.

        The threshold calculation follows a progressive strategy:
        - First time: token_limit * (summarize_threshold / 100)
        - Subsequent times: (limit - summary_token) / 2 + summary_token

        This ensures that as summaries accumulate, the threshold adapts
        to maintain a reasonable balance between context and summaries.

        Returns:
            int: The token count threshold for next summarization.
        """
        token_limit = self.model_backend.token_limit
        summary_token_count = self._summary_token_count

        # First summarization: use the percentage threshold
        if summary_token_count == 0:
            threshold = int(token_limit * self.summarize_threshold / 100)
        else:
            # Subsequent summarizations: adaptive threshold
            threshold = int(
                (token_limit - summary_token_count)
                * self.summarize_threshold
                / 100
                + summary_token_count
            )

        return threshold

    def _update_memory_with_summary(
        self, summary: str, include_summaries: bool = False
    ) -> None:
        r"""Update memory with summary result.

        This method handles memory clearing and restoration of summaries based
        on whether it's a progressive or full compression.
        """

        summary_content: str = summary

        existing_summaries = []
        if not include_summaries:
            messages, _ = self.memory.get_context()
            for msg in messages:
                content = msg.get('content', '')
                if isinstance(content, str) and content.startswith(
                    '[CONTEXT_SUMMARY]'
                ):
                    existing_summaries.append(msg)

        # Clear memory
        self.clear_memory()

        # Restore old summaries (for progressive compression)
        for old_summary in existing_summaries:
            content = old_summary.get('content', '')
            if not isinstance(content, str):
                content = str(content)
            summary_msg = BaseMessage.make_assistant_message(
                role_name="assistant", content=content
            )
            self.update_memory(summary_msg, OpenAIBackendRole.ASSISTANT)

        # Add new summary
        new_summary_msg = BaseMessage.make_assistant_message(
            role_name="assistant", content=summary_content
        )
        self.update_memory(new_summary_msg, OpenAIBackendRole.ASSISTANT)
        input_message = BaseMessage.make_assistant_message(
            role_name="assistant",
            content=(
                "Please continue the conversation from "
                "where we left it off without asking the user any further "
                "questions. Continue with the last task that you were "
                "asked to work on."
            ),
        )
        self.update_memory(input_message, OpenAIBackendRole.ASSISTANT)
        # Update token count
        try:
            summary_tokens = (
                self.model_backend.token_counter.count_tokens_from_messages(
                    [{"role": "assistant", "content": summary_content}]
                )
            )

            if include_summaries:  # Full compression - reset count
                self._summary_token_count = summary_tokens
                logger.info(
                    f"Full compression: Summary with {summary_tokens} tokens. "
                    f"Total summary tokens reset to: {summary_tokens}"
                )
            else:  # Progressive compression - accumulate
                self._summary_token_count += summary_tokens
                logger.info(
                    f"Progressive compression: New summary "
                    f"with {summary_tokens} tokens. "
                    f"Total summary tokens: "
                    f"{self._summary_token_count}"
                )
        except Exception as e:
            logger.warning(f"Failed to count summary tokens: {e}")

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

    def _serialize_tool_result(self, result: Any) -> str:
        if isinstance(result, str):
            return result
        try:
            return json.dumps(result, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(result)

    def _clean_snapshot_line(self, line: str) -> str:
        r"""Clean a single snapshot line by removing prefixes and references.

        This method handles snapshot lines in the format:
        - [prefix] "quoted text" [attributes] [ref=...]: description

        It preserves:
        - Quoted text content (including brackets inside quotes)
        - Description text after the colon

        It removes:
        - Line prefixes (e.g., "- button", "- tooltip", "generic:")
        - Attribute markers (e.g., [disabled], [ref=e47])
        - Lines with only element types
        - All indentation

        Args:
            line: The original line content.

        Returns:
            The cleaned line content, or empty string if line should be
            removed.
        """
        original = line.strip()
        if not original:
            return ''

        # Check if line is just an element type marker
        # (e.g., "- generic:", "button:")
        if re.match(r'^(?:-\s+)?\w+\s*:?\s*$', original):
            return ''

        # Remove element type prefix
        line = re.sub(r'^(?:-\s+)?\w+[\s:]+', '', original)

        # Remove bracket markers while preserving quoted text
        quoted_parts = []

        def save_quoted(match):
            quoted_parts.append(match.group(0))
            return f'__QUOTED_{len(quoted_parts)-1}__'

        line = re.sub(r'"[^"]*"', save_quoted, line)
        line = re.sub(r'\s*\[[^\]]+\]\s*', ' ', line)

        for i, quoted in enumerate(quoted_parts):
            line = line.replace(f'__QUOTED_{i}__', quoted)

        # Clean up formatting
        line = re.sub(r'\s+', ' ', line).strip()
        line = re.sub(r'\s*:\s*', ': ', line)
        line = line.lstrip(': ').strip()

        return '' if not line else line

    def _clean_snapshot_content(self, content: str) -> str:
        r"""Clean snapshot content by removing prefixes, references, and
        deduplicating lines.

        This method identifies snapshot lines (containing element keywords or
        references) and cleans them while preserving non-snapshot content.
        It also handles JSON-formatted tool outputs with snapshot fields.

        Args:
            content: The original snapshot content.

        Returns:
            The cleaned content with deduplicated lines.
        """
        try:
            import json

            data = json.loads(content)
            modified = False

            def clean_json_value(obj):
                nonlocal modified
                if isinstance(obj, dict):
                    result = {}
                    for key, value in obj.items():
                        if key == 'snapshot' and isinstance(value, str):
                            try:
                                decoded_value = value.encode().decode(
                                    'unicode_escape'
                                )
                            except (UnicodeDecodeError, AttributeError):
                                decoded_value = value

                            needs_cleaning = (
                                '- ' in decoded_value
                                or '[ref=' in decoded_value
                                or any(
                                    elem + ':' in decoded_value
                                    for elem in [
                                        'generic',
                                        'img',
                                        'banner',
                                        'list',
                                        'listitem',
                                        'search',
                                        'navigation',
                                    ]
                                )
                            )

                            if needs_cleaning:
                                cleaned_snapshot = self._clean_text_snapshot(
                                    decoded_value
                                )
                                result[key] = cleaned_snapshot
                                modified = True
                            else:
                                result[key] = value
                        else:
                            result[key] = clean_json_value(value)
                    return result
                elif isinstance(obj, list):
                    return [clean_json_value(item) for item in obj]
                else:
                    return obj

            cleaned_data = clean_json_value(data)

            if modified:
                return json.dumps(cleaned_data, ensure_ascii=False, indent=4)
            else:
                return content

        except (json.JSONDecodeError, TypeError):
            return self._clean_text_snapshot(content)

    def _clean_text_snapshot(self, content: str) -> str:
        r"""Clean plain text snapshot content.

        This method:
        - Removes all indentation
        - Deletes empty lines
        - Deduplicates all lines
        - Cleans snapshot-specific markers

        Args:
            content: The original snapshot text.

        Returns:
            The cleaned content with deduplicated lines, no indentation,
            and no empty lines.
        """
        lines = content.split('\n')
        cleaned_lines = []
        seen = set()

        for line in lines:
            stripped_line = line.strip()

            if not stripped_line:
                continue

            # Skip metadata lines (like "- /url:", "- /ref:")
            if re.match(r'^-?\s*/\w+\s*:', stripped_line):
                continue

            is_snapshot_line = '[ref=' in stripped_line or re.match(
                r'^(?:-\s+)?\w+(?:[\s:]|$)', stripped_line
            )

            if is_snapshot_line:
                cleaned = self._clean_snapshot_line(stripped_line)
                if cleaned and cleaned not in seen:
                    cleaned_lines.append(cleaned)
                    seen.add(cleaned)
            else:
                if stripped_line not in seen:
                    cleaned_lines.append(stripped_line)
                    seen.add(stripped_line)

        return '\n'.join(cleaned_lines)

    def _register_tool_output_for_cache(
        self,
        func_name: str,
        tool_call_id: str,
        result_text: str,
        records: List[MemoryRecord],
    ) -> None:
        if not records:
            return

        entry = _ToolOutputHistoryEntry(
            tool_name=func_name,
            tool_call_id=tool_call_id,
            result_text=result_text,
            record_uuids=[str(record.uuid) for record in records],
            record_timestamps=[record.timestamp for record in records],
        )
        self._tool_output_history.append(entry)
        self._process_tool_output_cache()

    def _process_tool_output_cache(self) -> None:
        if not self._enable_snapshot_clean or not self._tool_output_history:
            return

        # Only clean older results; keep the latest expanded for immediate use.
        for entry in self._tool_output_history[:-1]:
            if entry.cached:
                continue
            self._clean_snapshot_in_memory(entry)

    def _clean_snapshot_in_memory(
        self, entry: _ToolOutputHistoryEntry
    ) -> None:
        if not entry.record_uuids:
            return

        # Clean snapshot markers and references from historical tool output
        result_text = entry.result_text
        if '- ' in result_text and '[ref=' in result_text:
            cleaned_result = self._clean_snapshot_content(result_text)

            # Update the message in memory storage
            timestamp = (
                entry.record_timestamps[0]
                if entry.record_timestamps
                else time.time_ns() / 1_000_000_000
            )
            cleaned_message = FunctionCallingMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict={},
                content="",
                func_name=entry.tool_name,
                result=cleaned_result,
                tool_call_id=entry.tool_call_id,
            )

            chat_history_block = getattr(
                self.memory, "_chat_history_block", None
            )
            storage = getattr(chat_history_block, "storage", None)
            if storage is None:
                return

            existing_records = storage.load()
            updated_records = [
                record
                for record in existing_records
                if record["uuid"] not in entry.record_uuids
            ]
            new_record = MemoryRecord(
                message=cleaned_message,
                role_at_backend=OpenAIBackendRole.FUNCTION,
                timestamp=timestamp,
                agent_id=self.agent_id,
            )
            updated_records.append(new_record.to_dict())
            updated_records.sort(key=lambda record: record["timestamp"])
            storage.clear()
            storage.save(updated_records)

            logger.info(
                "Cleaned snapshot in memory for tool output '%s' (%s)",
                entry.tool_name,
                entry.tool_call_id,
            )

            entry.cached = True
            entry.record_uuids = [str(new_record.uuid)]
            entry.record_timestamps = [timestamp]

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
        return_records: bool = False,
    ) -> Optional[List[MemoryRecord]]:
        r"""Updates the agent memory with a new message.

        Args:
            message (BaseMessage): The new message to add to the stored
                messages.
            role (OpenAIBackendRole): The backend role type.
            timestamp (Optional[float], optional): Custom timestamp for the
                memory record. If `None`, the current time will be used.
                (default: :obj:`None`)
            return_records (bool, optional): When ``True`` the method returns
                the list of MemoryRecord objects written to memory.
                (default: :obj:`False`)

        Returns:
            Optional[List[MemoryRecord]]: The records that were written when
            ``return_records`` is ``True``; otherwise ``None``.
        """
        record = MemoryRecord(
            message=message,
            role_at_backend=role,
            timestamp=timestamp
            if timestamp is not None
            else time.time_ns() / 1_000_000_000,  # Nanosecond precision
            agent_id=self.agent_id,
        )
        self.memory.write_record(record)

        if return_records:
            return [record]
        return None

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

    def summarize(
        self,
        filename: Optional[str] = None,
        summary_prompt: Optional[str] = None,
        response_format: Optional[Type[BaseModel]] = None,
        working_directory: Optional[Union[str, Path]] = None,
        include_summaries: bool = False,
        add_user_messages: bool = True,
    ) -> Dict[str, Any]:
        r"""Summarize the agent's current conversation context and persist it
        to a markdown file.

        .. deprecated:: 0.2.80
            Use :meth:`asummarize` for async/await support and better
            performance in parallel summarization workflows.

        Args:
            filename (Optional[str]): The base filename (without extension) to
                use for the markdown file. Defaults to a timestamped name when
                not provided.
            summary_prompt (Optional[str]): Custom prompt for the summarizer.
                When omitted, a default prompt highlighting key decisions,
                action items, and open questions is used.
            response_format (Optional[Type[BaseModel]]): A Pydantic model
                defining the expected structure of the response. If provided,
                the summary will be generated as structured output and included
                in the result.
            include_summaries (bool): Whether to include previously generated
                summaries in the content to be summarized. If False (default),
                only non-summary messages will be summarized. If True, all
                messages including previous summaries will be summarized
                (full compression). (default: :obj:`False`)
            working_directory (Optional[str|Path]): Optional directory to save
                the markdown summary file. If provided, overrides the default
                directory used by ContextUtility.
            add_user_messages (bool): Whether add user messages to summary.
                (default: :obj:`True`)
        Returns:
            Dict[str, Any]: A dictionary containing the summary text, file
                path, status message, and optionally structured_summary if
                response_format was provided.

        See Also:
            :meth:`asummarize`: Async version for non-blocking LLM calls.
        """

        warnings.warn(
            "summarize() is synchronous. Consider using asummarize() "
            "for async/await support and better performance.",
            DeprecationWarning,
            stacklevel=2,
        )

        result: Dict[str, Any] = {
            "summary": "",
            "file_path": None,
            "status": "",
        }

        try:
            # Use external context if set, otherwise create local one
            if self._context_utility is None:
                if working_directory is not None:
                    self._context_utility = ContextUtility(
                        working_directory=str(working_directory)
                    )
                else:
                    self._context_utility = ContextUtility()
            context_util = self._context_utility

            # Get conversation directly from agent's memory
            messages, _ = self.memory.get_context()

            if not messages:
                status_message = (
                    "No conversation context available to summarize."
                )
                result["status"] = status_message
                return result

            # Convert messages to conversation text
            conversation_lines = []
            user_messages: List[str] = []
            for message in messages:
                role = message.get('role', 'unknown')
                content = message.get('content', '')

                # Skip summary messages if include_summaries is False
                if not include_summaries and isinstance(content, str):
                    # Check if this is a summary message by looking for marker
                    if content.startswith('[CONTEXT_SUMMARY]'):
                        continue

                # Handle tool call messages (assistant calling tools)
                tool_calls = message.get('tool_calls')
                if tool_calls and isinstance(tool_calls, (list, tuple)):
                    for tool_call in tool_calls:
                        # Handle both dict and object formats
                        if isinstance(tool_call, dict):
                            func_name = tool_call.get('function', {}).get(
                                'name', 'unknown_tool'
                            )
                            func_args_str = tool_call.get('function', {}).get(
                                'arguments', '{}'
                            )
                        else:
                            # Handle object format (Pydantic or similar)
                            func_name = getattr(
                                getattr(tool_call, 'function', None),
                                'name',
                                'unknown_tool',
                            )
                            func_args_str = getattr(
                                getattr(tool_call, 'function', None),
                                'arguments',
                                '{}',
                            )

                        # Parse and format arguments for readability
                        try:
                            import json

                            args_dict = json.loads(func_args_str)
                            args_formatted = ', '.join(
                                f"{k}={v}" for k, v in args_dict.items()
                            )
                        except (json.JSONDecodeError, ValueError, TypeError):
                            args_formatted = func_args_str

                        conversation_lines.append(
                            f"[TOOL CALL] {func_name}({args_formatted})"
                        )

                # Handle tool response messages
                elif role == 'tool':
                    tool_name = message.get('name', 'unknown_tool')
                    if not content:
                        content = str(message.get('content', ''))
                    conversation_lines.append(
                        f"[TOOL RESULT] {tool_name} → {content}"
                    )

                # Handle regular content messages (user/assistant/system)
                elif content:
                    content = str(content)
                    if role == 'user':
                        user_messages.append(content)
                    conversation_lines.append(f"{role}: {content}")

            conversation_text = "\n".join(conversation_lines).strip()

            if not conversation_text:
                status_message = (
                    "Conversation context is empty; skipping summary."
                )
                result["status"] = status_message
                return result

            if self._context_summary_agent is None:
                self._context_summary_agent = ChatAgent(
                    system_message=(
                        "You are a helpful assistant that summarizes "
                        "conversations"
                    ),
                    model=self.model_backend,
                    agent_id=f"{self.agent_id}_context_summarizer",
                    summarize_threshold=None,
                )
            else:
                self._context_summary_agent.reset()

            if summary_prompt:
                prompt_text = (
                    f"{summary_prompt.rstrip()}\n\n"
                    f"AGENT CONVERSATION TO BE SUMMARIZED:\n"
                    f"{conversation_text}"
                )
            else:
                prompt_text = build_default_summary_prompt(conversation_text)

            try:
                # Use structured output if response_format is provided
                if response_format:
                    response = self._context_summary_agent.step(
                        prompt_text, response_format=response_format
                    )
                else:
                    response = self._context_summary_agent.step(prompt_text)
            except Exception as step_exc:
                error_message = (
                    f"Failed to generate summary using model: {step_exc}"
                )
                logger.error(error_message)
                result["status"] = error_message
                return result

            if not response.msgs:
                status_message = (
                    "Failed to generate summary from model response."
                )
                result["status"] = status_message
                return result

            summary_content = response.msgs[-1].content.strip()
            if not summary_content:
                status_message = "Generated summary is empty."
                result["status"] = status_message
                return result

            # handle structured output if response_format was provided
            structured_output = None
            if response_format and response.msgs[-1].parsed:
                structured_output = response.msgs[-1].parsed

            # determine filename: use provided filename, or extract from
            # structured output, or generate timestamp
            if filename:
                base_filename = filename
            elif structured_output and hasattr(
                structured_output, 'task_title'
            ):
                # use task_title from structured output for filename
                task_title = structured_output.task_title
                clean_title = ContextUtility.sanitize_workflow_filename(
                    task_title
                )
                base_filename = (
                    f"{clean_title}_workflow" if clean_title else "workflow"
                )
            else:
                base_filename = f"context_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # noqa: E501

            base_filename = Path(base_filename).with_suffix("").name

            metadata = context_util.get_session_metadata()
            metadata.update(
                {
                    "agent_id": self.agent_id,
                    "message_count": len(messages),
                }
            )

            # convert structured output to custom markdown if present
            if structured_output:
                # convert structured output to custom markdown
                summary_content = context_util.structured_output_to_markdown(
                    structured_data=structured_output, metadata=metadata
                )
            if add_user_messages:
                summary_content = self._append_user_messages_section(
                    summary_content, user_messages
                )

            # Save the markdown (either custom structured or default)
            save_status = context_util.save_markdown_file(
                base_filename,
                summary_content,
                title="Conversation Summary"
                if not structured_output
                else None,
                metadata=metadata if not structured_output else None,
            )

            file_path = (
                context_util.get_working_directory() / f"{base_filename}.md"
            )
            summary_content = (
                f"[CONTEXT_SUMMARY] The following is a summary of our "
                f"conversation from a previous session: {summary_content}"
            )
            # Prepare result dictionary
            result_dict = {
                "summary": summary_content,
                "file_path": str(file_path),
                "status": save_status,
                "structured_summary": structured_output,
            }

            result.update(result_dict)
            logger.info("Conversation summary saved to %s", file_path)
            return result

        except Exception as exc:
            error_message = f"Failed to summarize conversation context: {exc}"
            logger.error(error_message)
            result["status"] = error_message
            return result

    async def asummarize(
        self,
        filename: Optional[str] = None,
        summary_prompt: Optional[str] = None,
        response_format: Optional[Type[BaseModel]] = None,
        working_directory: Optional[Union[str, Path]] = None,
        include_summaries: bool = False,
        add_user_messages: bool = True,
    ) -> Dict[str, Any]:
        r"""Asynchronously summarize the agent's current conversation context
        and persist it to a markdown file.

        This is the async version of summarize() that uses astep() for
        non-blocking LLM calls, enabling parallel summarization of multiple
        agents.

        Args:
            filename (Optional[str]): The base filename (without extension) to
                use for the markdown file. Defaults to a timestamped name when
                not provided.
            summary_prompt (Optional[str]): Custom prompt for the summarizer.
                When omitted, a default prompt highlighting key decisions,
                action items, and open questions is used.
            response_format (Optional[Type[BaseModel]]): A Pydantic model
                defining the expected structure of the response. If provided,
                the summary will be generated as structured output and included
                in the result.
            working_directory (Optional[str|Path]): Optional directory to save
                the markdown summary file. If provided, overrides the default
                directory used by ContextUtility.
            include_summaries (bool): Whether to include previously generated
                summaries in the content to be summarized. If False (default),
                only non-summary messages will be summarized. If True, all
                messages including previous summaries will be summarized
                (full compression). (default: :obj:`False`)
            add_user_messages (bool): Whether add user messages to summary.
                (default: :obj:`True`)
        Returns:
            Dict[str, Any]: A dictionary containing the summary text, file
                path, status message, and optionally structured_summary if
                response_format was provided.
        """

        result: Dict[str, Any] = {
            "summary": "",
            "file_path": None,
            "status": "",
        }

        try:
            # Use external context if set, otherwise create local one
            if self._context_utility is None:
                if working_directory is not None:
                    self._context_utility = ContextUtility(
                        working_directory=str(working_directory)
                    )
                else:
                    self._context_utility = ContextUtility()
            context_util = self._context_utility

            # Get conversation directly from agent's memory
            messages, _ = self.memory.get_context()

            if not messages:
                status_message = (
                    "No conversation context available to summarize."
                )
                result["status"] = status_message
                return result

            # Convert messages to conversation text
            conversation_lines = []
            user_messages: List[str] = []
            for message in messages:
                role = message.get('role', 'unknown')
                content = message.get('content', '')

                # Skip summary messages if include_summaries is False
                if not include_summaries and isinstance(content, str):
                    # Check if this is a summary message by looking for marker
                    if content.startswith('[CONTEXT_SUMMARY]'):
                        continue

                # Handle tool call messages (assistant calling tools)
                tool_calls = message.get('tool_calls')
                if tool_calls and isinstance(tool_calls, (list, tuple)):
                    for tool_call in tool_calls:
                        # Handle both dict and object formats
                        if isinstance(tool_call, dict):
                            func_name = tool_call.get('function', {}).get(
                                'name', 'unknown_tool'
                            )
                            func_args_str = tool_call.get('function', {}).get(
                                'arguments', '{}'
                            )
                        else:
                            # Handle object format (Pydantic or similar)
                            func_name = getattr(
                                getattr(tool_call, 'function', None),
                                'name',
                                'unknown_tool',
                            )
                            func_args_str = getattr(
                                getattr(tool_call, 'function', None),
                                'arguments',
                                '{}',
                            )

                        # Parse and format arguments for readability
                        try:
                            import json

                            args_dict = json.loads(func_args_str)
                            args_formatted = ', '.join(
                                f"{k}={v}" for k, v in args_dict.items()
                            )
                        except (json.JSONDecodeError, ValueError, TypeError):
                            args_formatted = func_args_str

                        conversation_lines.append(
                            f"[TOOL CALL] {func_name}({args_formatted})"
                        )

                # Handle tool response messages
                elif role == 'tool':
                    tool_name = message.get('name', 'unknown_tool')
                    if not content:
                        content = str(message.get('content', ''))
                    conversation_lines.append(
                        f"[TOOL RESULT] {tool_name} → {content}"
                    )

                # Handle regular content messages (user/assistant/system)
                elif content:
                    content = str(content)
                    if role == 'user':
                        user_messages.append(content)
                    conversation_lines.append(f"{role}: {content}")

            conversation_text = "\n".join(conversation_lines).strip()

            if not conversation_text:
                status_message = (
                    "Conversation context is empty; skipping summary."
                )
                result["status"] = status_message
                return result

            if self._context_summary_agent is None:
                self._context_summary_agent = ChatAgent(
                    system_message=(
                        "You are a helpful assistant that summarizes "
                        "conversations"
                    ),
                    model=self.model_backend,
                    agent_id=f"{self.agent_id}_context_summarizer",
                    summarize_threshold=None,
                )
            else:
                self._context_summary_agent.reset()

            if summary_prompt:
                prompt_text = (
                    f"{summary_prompt.rstrip()}\n\n"
                    f"AGENT CONVERSATION TO BE SUMMARIZED:\n"
                    f"{conversation_text}"
                )
            else:
                prompt_text = build_default_summary_prompt(conversation_text)

            try:
                # Use structured output if response_format is provided
                if response_format:
                    response = await self._context_summary_agent.astep(
                        prompt_text, response_format=response_format
                    )
                else:
                    response = await self._context_summary_agent.astep(
                        prompt_text
                    )

                # Handle streaming response
                if isinstance(response, AsyncStreamingChatAgentResponse):
                    # Collect final response
                    final_response = await response
                    response = final_response

            except Exception as step_exc:
                error_message = (
                    f"Failed to generate summary using model: {step_exc}"
                )
                logger.error(error_message)
                result["status"] = error_message
                return result

            if not response.msgs:
                status_message = (
                    "Failed to generate summary from model response."
                )
                result["status"] = status_message
                return result

            summary_content = response.msgs[-1].content.strip()
            if not summary_content:
                status_message = "Generated summary is empty."
                result["status"] = status_message
                return result

            # handle structured output if response_format was provided
            structured_output = None
            if response_format and response.msgs[-1].parsed:
                structured_output = response.msgs[-1].parsed

            # determine filename: use provided filename, or extract from
            # structured output, or generate timestamp
            if filename:
                base_filename = filename
            elif structured_output and hasattr(
                structured_output, 'task_title'
            ):
                # use task_title from structured output for filename
                task_title = structured_output.task_title
                clean_title = ContextUtility.sanitize_workflow_filename(
                    task_title
                )
                base_filename = (
                    f"{clean_title}_workflow" if clean_title else "workflow"
                )
            else:
                base_filename = f"context_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}"  # noqa: E501

            base_filename = Path(base_filename).with_suffix("").name

            metadata = context_util.get_session_metadata()
            metadata.update(
                {
                    "agent_id": self.agent_id,
                    "message_count": len(messages),
                }
            )

            # convert structured output to custom markdown if present
            if structured_output:
                # convert structured output to custom markdown
                summary_content = context_util.structured_output_to_markdown(
                    structured_data=structured_output, metadata=metadata
                )
            if add_user_messages:
                summary_content = self._append_user_messages_section(
                    summary_content, user_messages
                )

            # Save the markdown (either custom structured or default)
            save_status = context_util.save_markdown_file(
                base_filename,
                summary_content,
                title="Conversation Summary"
                if not structured_output
                else None,
                metadata=metadata if not structured_output else None,
            )

            file_path = (
                context_util.get_working_directory() / f"{base_filename}.md"
            )

            summary_content = (
                f"[CONTEXT_SUMMARY] The following is a summary of our "
                f"conversation from a previous session: {summary_content}"
            )

            # Prepare result dictionary
            result_dict = {
                "summary": summary_content,
                "file_path": str(file_path),
                "status": save_status,
                "structured_summary": structured_output,
            }

            result.update(result_dict)
            logger.info("Conversation summary saved to %s", file_path)
            return result

        except Exception as exc:
            error_message = f"Failed to summarize conversation context: {exc}"
            logger.error(error_message)
            result["status"] = error_message
            return result

    def clear_memory(self) -> None:
        r"""Clear the agent's memory and reset to initial state.

        Returns:
            None
        """
        self.memory.clear()

        if self.system_message is not None:
            self.memory.write_record(
                MemoryRecord(
                    message=self.system_message,
                    role_at_backend=OpenAIBackendRole.SYSTEM,
                    timestamp=time.time_ns() / 1_000_000_000,
                    agent_id=self.agent_id,
                )
            )

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
            return BaseMessage.make_system_message(language_prompt)

    def init_messages(self) -> None:
        r"""Initializes the stored messages list with the current system
        message.
        """
        self._reset_summary_state()
        self.clear_memory()

    def update_system_message(
        self,
        system_message: Union[BaseMessage, str],
        reset_memory: bool = True,
    ) -> None:
        r"""Update the system message.
        It will reset conversation with new system message.

        Args:
            system_message (Union[BaseMessage, str]): The new system message.
                Can be either a BaseMessage object or a string.
                If a string is provided, it will be converted
                into a BaseMessage object.
            reset_memory (bool):
                Whether to reinitialize conversation messages after updating
                the system message. Defaults to True.
        """
        if system_message is None:
            raise ValueError("system_message is required and cannot be None. ")
        self._original_system_message = (
            BaseMessage.make_system_message(system_message)
            if isinstance(system_message, str)
            else system_message
        )
        self._system_message = (
            self._generate_system_message_for_output_language()
        )
        if reset_memory:
            self.init_messages()

    def append_to_system_message(
        self, content: str, reset_memory: bool = True
    ) -> None:
        """Append additional context to existing system message.

        Args:
            content (str): The additional system message.
            reset_memory (bool):
                Whether to reinitialize conversation messages after appending
                additional context. Defaults to True.
        """
        original_content = (
            self._original_system_message.content
            if self._original_system_message
            else ""
        )
        new_system_message = original_content + '\n' + content
        self._original_system_message = BaseMessage.make_system_message(
            new_system_message
        )
        self._system_message = (
            self._generate_system_message_for_output_language()
        )
        if reset_memory:
            self.init_messages()

    def reset_to_original_system_message(self) -> None:
        r"""Reset system message to original, removing any appended context.

        This method reverts the agent's system message back to its original
        state, removing any workflow context or other modifications that may
        have been appended. Useful for resetting agent state in multi-turn
        scenarios.
        """
        self._system_message = self._original_system_message
        self.init_messages()

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
                "\n\nPlease respond in the following JSON format:\n{\n"
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

    def _is_called_from_registered_toolkit(self) -> bool:
        r"""Check if current step/astep call originates from a
        RegisteredAgentToolkit.

        This method uses stack inspection to detect if the current call
        is originating from a toolkit that inherits from
        RegisteredAgentToolkit. When detected, tools should be disabled to
        prevent recursive calls.

        Returns:
            bool: True if called from a RegisteredAgentToolkit, False otherwise
        """
        from camel.toolkits.base import RegisteredAgentToolkit

        try:
            for frame_info in inspect.stack():
                frame_locals = frame_info.frame.f_locals
                if 'self' in frame_locals:
                    caller_self = frame_locals['self']
                    if isinstance(caller_self, RegisteredAgentToolkit):
                        return True

        except Exception:
            return False

        return False

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
                            f"Failed to parse JSON from response: {content}"
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
                openai_messages=[openai_message],
                num_tokens=0,
                response_format=response_format,
                tool_schemas=[],
                prev_num_openai_messages=0,
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
                openai_messages=[openai_message],
                num_tokens=0,
                response_format=response_format,
                tool_schemas=[],
                prev_num_openai_messages=0,
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

        Raises:
            TimeoutError: If the step operation exceeds the configured timeout.
        """

        stream = self.model_backend.model_config_dict.get("stream", False)

        if stream:
            # Return wrapped generator that has ChatAgentResponse interface
            generator = self._stream(input_message, response_format)
            return StreamingChatAgentResponse(generator)

        # Execute with timeout if configured
        if self.step_timeout is not None:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=1
            ) as executor:
                future = executor.submit(
                    self._step_impl, input_message, response_format
                )
                try:
                    return future.result(timeout=self.step_timeout)
                except concurrent.futures.TimeoutError:
                    future.cancel()
                    raise TimeoutError(
                        f"Step timed out after {self.step_timeout}s"
                    )
        else:
            return self._step_impl(input_message, response_format)

    def _step_impl(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        r"""Implementation of non-streaming step logic."""
        # Set Langfuse session_id using agent_id for trace grouping
        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

        # Check if this call is from a RegisteredAgentToolkit to prevent tool
        # use
        disable_tools = self._is_called_from_registered_toolkit()

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

        # Add user input to memory
        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_call_records: List[ToolCallingRecord] = []
        external_tool_call_requests: Optional[List[ToolCallRequest]] = None

        accumulated_context_tokens = (
            0  # This tracks cumulative context tokens, not API usage tokens
        )

        # Initialize token usage tracker
        step_token_usage = self._create_token_usage_tracker()
        iteration_count: int = 0
        prev_num_openai_messages: int = 0

        while True:
            if self.pause_event is not None and not self.pause_event.is_set():
                # Use efficient blocking wait for threading.Event
                if isinstance(self.pause_event, threading.Event):
                    self.pause_event.wait()
                else:
                    # Fallback for asyncio.Event in sync context
                    while not self.pause_event.is_set():
                        time.sleep(0.001)

            try:
                openai_messages, num_tokens = self.memory.get_context()
                if self.summarize_threshold is not None:
                    threshold = self._calculate_next_summary_threshold()
                    summary_token_count = self._summary_token_count
                    token_limit = self.model_backend.token_limit

                    if num_tokens <= token_limit:
                        if (
                            summary_token_count
                            > token_limit * self.summary_window_ratio
                        ):
                            logger.info(
                                f"Summary tokens ({summary_token_count}) "
                                f"exceed limit, full compression."
                            )
                            # Summarize everything (including summaries)
                            summary = self.summarize(include_summaries=True)
                            self._update_memory_with_summary(
                                summary.get("summary", ""),
                                include_summaries=True,
                            )
                        elif num_tokens > threshold:
                            logger.info(
                                f"Token count ({num_tokens}) exceed threshold "
                                f"({threshold}). Triggering summarization."
                            )
                            # Only summarize non-summary content
                            summary = self.summarize(include_summaries=False)
                            self._update_memory_with_summary(
                                summary.get("summary", ""),
                                include_summaries=False,
                            )
                accumulated_context_tokens += num_tokens
            except RuntimeError as e:
                return self._step_terminate(
                    e.args[1], tool_call_records, "max_tokens_exceeded"
                )
            # Get response from model backend with token limit error handling
            try:
                response = self._get_model_response(
                    openai_messages,
                    num_tokens=num_tokens,
                    current_iteration=iteration_count,
                    response_format=response_format,
                    tool_schemas=[]
                    if disable_tools
                    else self._get_full_tool_schemas(),
                    prev_num_openai_messages=prev_num_openai_messages,
                )
            except Exception as exc:
                logger.exception("Model error: %s", exc)

                if self._is_token_limit_error(exc):
                    tool_signature = self._last_tool_call_signature
                    if (
                        tool_signature is not None
                        and tool_signature
                        == self._last_token_limit_tool_signature
                    ):
                        description = self._describe_tool_call(
                            self._last_tool_call_record
                        )
                        repeated_msg = (
                            "Context exceeded again by the same tool call."
                        )
                        if description:
                            repeated_msg += f" {description}"
                        raise RuntimeError(repeated_msg) from exc

                    user_message_count = sum(
                        1
                        for msg in openai_messages
                        if getattr(msg, "role", None) == "user"
                    )
                    if (
                        user_message_count == 1
                        and getattr(openai_messages[-1], "role", None)
                        == "user"
                    ):
                        raise RuntimeError(
                            "The provided user input alone exceeds the "
                            "context window. Please shorten the input."
                        ) from exc

                    logger.warning(
                        "Token limit exceeded error detected. "
                        "Summarizing context."
                    )

                    recent_records: List[ContextRecord]
                    try:
                        recent_records = self.memory.retrieve()
                    except Exception:  # pragma: no cover - defensive guard
                        recent_records = []

                    indices_to_remove = (
                        self._find_indices_to_remove_for_last_tool_pair(
                            recent_records
                        )
                    )
                    self.memory.remove_records_by_indices(indices_to_remove)

                    summary = self.summarize(include_summaries=False)
                    tool_notice = self._format_tool_limit_notice()
                    summary_messages = summary.get("summary", "")

                    if tool_notice:
                        summary_messages += "\n\n" + tool_notice

                    self._update_memory_with_summary(
                        summary_messages, include_summaries=False
                    )
                    self._last_token_limit_tool_signature = tool_signature
                    return self._step_impl(input_message, response_format)

                raise

            prev_num_openai_messages = len(openai_messages)
            iteration_count += 1

            # Accumulate API token usage
            self._update_token_usage_tracker(
                step_token_usage, response.usage_dict
            )

            # Terminate Agent if stop_event is set
            if self.stop_event and self.stop_event.is_set():
                # Use the _step_terminate to terminate the agent with reason
                logger.info(
                    f"Termination triggered at iteration {iteration_count}"
                )
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
                            if isinstance(self.pause_event, threading.Event):
                                self.pause_event.wait()
                            else:
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
                    logger.info(f"Max iteration reached: {iteration_count}")
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

        # Clean tool call messages from memory after response generation
        if self.prune_tool_calls_from_memory and tool_call_records:
            self.memory.clean_tool_calls()

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

        Raises:
            asyncio.TimeoutError: If the step operation exceeds the configured
                timeout.
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
            if self.step_timeout is not None:
                try:
                    return await asyncio.wait_for(
                        self._astep_non_streaming_task(
                            input_message, response_format
                        ),
                        timeout=self.step_timeout,
                    )
                except asyncio.TimeoutError:
                    raise asyncio.TimeoutError(
                        f"Async step timed out after {self.step_timeout}s"
                    )
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

        # Check if this call is from a RegisteredAgentToolkit to prevent tool
        # use
        disable_tools = self._is_called_from_registered_toolkit()

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

        self.update_memory(input_message, OpenAIBackendRole.USER)

        tool_call_records: List[ToolCallingRecord] = []
        external_tool_call_requests: Optional[List[ToolCallRequest]] = None
        accumulated_context_tokens = (
            0  # This tracks cumulative context tokens, not API usage tokens
        )

        # Initialize token usage tracker
        step_token_usage = self._create_token_usage_tracker()
        iteration_count: int = 0
        prev_num_openai_messages: int = 0

        while True:
            if self.pause_event is not None and not self.pause_event.is_set():
                if isinstance(self.pause_event, asyncio.Event):
                    await self.pause_event.wait()
                elif isinstance(self.pause_event, threading.Event):
                    # For threading.Event in async context, run in executor
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self.pause_event.wait)
            try:
                openai_messages, num_tokens = self.memory.get_context()
                if self.summarize_threshold is not None:
                    threshold = self._calculate_next_summary_threshold()
                    summary_token_count = self._summary_token_count
                    token_limit = self.model_backend.token_limit

                    if num_tokens <= token_limit:
                        if (
                            summary_token_count
                            > token_limit * self.summary_window_ratio
                        ):
                            logger.info(
                                f"Summary tokens ({summary_token_count}) "
                                f"exceed limit, full compression."
                            )
                            # Summarize everything (including summaries)
                            summary = await self.asummarize(
                                include_summaries=True
                            )
                            self._update_memory_with_summary(
                                summary.get("summary", ""),
                                include_summaries=True,
                            )
                        elif num_tokens > threshold:
                            logger.info(
                                f"Token count ({num_tokens}) exceed threshold "
                                "({threshold}). Triggering summarization."
                            )
                            # Only summarize non-summary content
                            summary = await self.asummarize(
                                include_summaries=False
                            )
                            self._update_memory_with_summary(
                                summary.get("summary", ""),
                                include_summaries=False,
                            )
                accumulated_context_tokens += num_tokens
            except RuntimeError as e:
                return self._step_terminate(
                    e.args[1], tool_call_records, "max_tokens_exceeded"
                )
            # Get response from model backend with token limit error handling
            try:
                response = await self._aget_model_response(
                    openai_messages,
                    num_tokens=num_tokens,
                    current_iteration=iteration_count,
                    response_format=response_format,
                    tool_schemas=[]
                    if disable_tools
                    else self._get_full_tool_schemas(),
                    prev_num_openai_messages=prev_num_openai_messages,
                )
            except Exception as exc:
                logger.exception("Model error: %s", exc)

                if self._is_token_limit_error(exc):
                    tool_signature = self._last_tool_call_signature
                    if (
                        tool_signature is not None
                        and tool_signature
                        == self._last_token_limit_tool_signature
                    ):
                        description = self._describe_tool_call(
                            self._last_tool_call_record
                        )
                        repeated_msg = (
                            "Context exceeded again by the same tool call."
                        )
                        if description:
                            repeated_msg += f" {description}"
                        raise RuntimeError(repeated_msg) from exc

                    user_message_count = sum(
                        1
                        for msg in openai_messages
                        if getattr(msg, "role", None) == "user"
                    )
                    if (
                        user_message_count == 1
                        and getattr(openai_messages[-1], "role", None)
                        == "user"
                    ):
                        raise RuntimeError(
                            "The provided user input alone exceeds the"
                            "context window. Please shorten the input."
                        ) from exc

                    logger.warning(
                        "Token limit exceeded error detected. "
                        "Summarizing context."
                    )

                    recent_records: List[ContextRecord]
                    try:
                        recent_records = self.memory.retrieve()
                    except Exception:  # pragma: no cover - defensive guard
                        recent_records = []

                    indices_to_remove = (
                        self._find_indices_to_remove_for_last_tool_pair(
                            recent_records
                        )
                    )
                    self.memory.remove_records_by_indices(indices_to_remove)

                    summary = await self.asummarize()

                    tool_notice = self._format_tool_limit_notice()
                    summary_messages = summary.get("summary", "")

                    if tool_notice:
                        summary_messages += "\n\n" + tool_notice
                    self._update_memory_with_summary(
                        summary_messages, include_summaries=False
                    )
                    self._last_token_limit_tool_signature = tool_signature
                    return await self._astep_non_streaming_task(
                        input_message, response_format
                    )

                raise

            prev_num_openai_messages = len(openai_messages)
            iteration_count += 1

            # Accumulate API token usage
            self._update_token_usage_tracker(
                step_token_usage, response.usage_dict
            )

            # Terminate Agent if stop_event is set
            if self.stop_event and self.stop_event.is_set():
                # Use the _step_terminate to terminate the agent with reason
                logger.info(
                    f"Termination triggered at iteration {iteration_count}"
                )
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
                            if isinstance(self.pause_event, asyncio.Event):
                                await self.pause_event.wait()
                            elif isinstance(self.pause_event, threading.Event):
                                loop = asyncio.get_event_loop()
                                await loop.run_in_executor(
                                    None, self.pause_event.wait
                                )
                        tool_call_record = await self._aexecute_tool(
                            tool_call_request
                        )
                        tool_call_records.append(tool_call_record)

                # If we found an external tool call, break the loop
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

        await self._aformat_response_if_needed(response, response_format)

        # Apply manual parsing if we used prompt-based formatting
        if used_prompt_formatting and original_response_format:
            self._apply_prompt_based_parsing(
                response, original_response_format
            )

        self._record_final_output(response.output_messages)

        # Clean tool call messages from memory after response generation
        if self.prune_tool_calls_from_memory and tool_call_records:
            self.memory.clean_tool_calls()

        self._last_token_limit_user_signature = None

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

    def _record_final_output(self, output_messages: List[BaseMessage]) -> None:
        r"""Log final messages or warnings about multiple responses."""
        if len(output_messages) == 1:
            self.record_message(output_messages[0])
        else:
            logger.warning(
                "Multiple messages returned in `step()`. Record "
                "selected message manually using `record_message()`."
            )

    @observe()
    def _get_model_response(
        self,
        openai_messages: List[OpenAIMessage],
        num_tokens: int,
        current_iteration: int = 0,
        response_format: Optional[Type[BaseModel]] = None,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
        prev_num_openai_messages: int = 0,
    ) -> ModelResponse:
        r"""Internal function for agent step model response."""
        last_error = None

        for attempt in range(self.retry_attempts):
            try:
                response = self.model_backend.run(
                    openai_messages, response_format, tool_schemas or None
                )
                if response:
                    break
            except RateLimitError as e:
                if self._is_token_limit_error(e):
                    raise
                last_error = e
                if attempt < self.retry_attempts - 1:
                    delay = min(self.retry_delay * (2**attempt), 60.0)
                    delay = random.uniform(0, delay)  # Add jitter
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}"
                        f"/{self.retry_attempts}). Retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        f"Rate limit exhausted after "
                        f"{self.retry_attempts} attempts"
                    )
            except Exception:
                logger.error(
                    f"Model error: {self.model_backend.model_type}",
                )
                raise
        else:
            # Loop completed without success
            raise ModelProcessingError(
                f"Unable to process messages: "
                f"{str(last_error) if last_error else 'Unknown error'}"
            )

        # Log success
        sanitized = self._sanitize_messages_for_logging(
            openai_messages, prev_num_openai_messages
        )
        logger.info(
            f"Model {self.model_backend.model_type} "
            f"[{current_iteration}]: {sanitized}"
        )

        if not isinstance(response, ChatCompletion):
            raise TypeError(
                f"Expected ChatCompletion, got {type(response).__name__}"
            )

        return self._handle_batch_response(response)

    @observe()
    async def _aget_model_response(
        self,
        openai_messages: List[OpenAIMessage],
        num_tokens: int,
        current_iteration: int = 0,
        response_format: Optional[Type[BaseModel]] = None,
        tool_schemas: Optional[List[Dict[str, Any]]] = None,
        prev_num_openai_messages: int = 0,
    ) -> ModelResponse:
        r"""Internal function for agent async step model response."""
        last_error = None

        for attempt in range(self.retry_attempts):
            try:
                response = await self.model_backend.arun(
                    openai_messages, response_format, tool_schemas or None
                )
                if response:
                    break
            except RateLimitError as e:
                if self._is_token_limit_error(e):
                    raise
                last_error = e
                if attempt < self.retry_attempts - 1:
                    delay = min(self.retry_delay * (2**attempt), 60.0)
                    delay = random.uniform(0, delay)  # Add jitter
                    logger.warning(
                        f"Rate limit hit (attempt {attempt + 1}"
                        f"/{self.retry_attempts}). "
                        f"Retrying in {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        f"Rate limit exhausted after "
                        f"{self.retry_attempts} attempts"
                    )
            except Exception:
                logger.error(
                    f"Model error: {self.model_backend.model_type}",
                    exc_info=True,
                )
                raise
        else:
            # Loop completed without success
            raise ModelProcessingError(
                f"Unable to process messages: "
                f"{str(last_error) if last_error else 'Unknown error'}"
            )

        # Log success
        sanitized = self._sanitize_messages_for_logging(
            openai_messages, prev_num_openai_messages
        )
        logger.info(
            f"Model {self.model_backend.model_type} "
            f"[{current_iteration}]: {sanitized}"
        )

        if not isinstance(response, ChatCompletion):
            raise TypeError(
                f"Expected ChatCompletion, got {type(response).__name__}"
            )

        return self._handle_batch_response(response)

    def _sanitize_messages_for_logging(
        self, messages, prev_num_openai_messages: int
    ):
        r"""Sanitize OpenAI messages for logging by replacing base64 image
        data with a simple message and a link to view the image.

        Args:
            messages (List[OpenAIMessage]): The OpenAI messages to sanitize.
            prev_num_openai_messages (int): The number of openai messages
                logged in the previous iteration.

        Returns:
            List[OpenAIMessage]: The sanitized OpenAI messages.
        """
        # Create a copy of messages for logging to avoid modifying the
        # original messages
        sanitized_messages = []
        for msg in messages[prev_num_openai_messages:]:
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
                                        # Sanitize img_format to prevent path
                                        # traversal
                                        safe_format = re.sub(
                                            r'[^a-zA-Z0-9]', '', img_format
                                        )[:10]
                                        img_filename = (
                                            f"image_{img_hash}.{safe_format}"
                                        )

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
                                            # Register for cleanup
                                            with _temp_files_lock:
                                                _temp_files.add(img_path)

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

            reasoning_content = getattr(
                choice.message, "reasoning_content", None
            )

            chat_message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict=meta_dict,
                content=choice.message.content or "",
                parsed=getattr(choice.message, "parsed", None),
                reasoning_content=reasoning_content,
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
                tool_name = tool_call.function.name  # type: ignore[union-attr]
                tool_call_id = tool_call.id
                args = json.loads(tool_call.function.arguments)  # type: ignore[union-attr]
                extra_content = getattr(tool_call, 'extra_content', None)

                tool_call_request = ToolCallRequest(
                    tool_name=tool_name,
                    args=args,
                    tool_call_id=tool_call_id,
                    extra_content=extra_content,
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

    @observe()
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
                with self._secure_result_store_lock:
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
            logger.warning(f"{error_msg} with result: {result}")

        return self._record_tool_calling(
            func_name,
            args,
            result,
            tool_call_id,
            mask_output=mask_flag,
            extra_content=tool_call_request.extra_content,
        )

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
            logger.warning(error_msg)
        return self._record_tool_calling(
            func_name,
            args,
            result,
            tool_call_id,
            extra_content=tool_call_request.extra_content,
        )

    def _record_tool_calling(
        self,
        func_name: str,
        args: Dict[str, Any],
        result: Any,
        tool_call_id: str,
        mask_output: bool = False,
        extra_content: Optional[Dict[str, Any]] = None,
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
            extra_content (Optional[Dict[str, Any]], optional): Additional
                content associated with the tool call.
                (default: :obj:`None`)

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
            extra_content=extra_content,
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
            extra_content=extra_content,
        )

        # Use precise timestamps to ensure correct ordering
        # This ensures the assistant message (tool call) always appears before
        # the function message (tool result) in the conversation context
        # Use time.time_ns() for nanosecond precision to avoid collisions
        current_time_ns = time.time_ns()
        base_timestamp = current_time_ns / 1_000_000_000  # Convert to seconds

        self.update_memory(
            assist_msg,
            OpenAIBackendRole.ASSISTANT,
            timestamp=base_timestamp,
            return_records=self._enable_snapshot_clean,
        )

        # Add minimal increment to ensure function message comes after
        func_records = self.update_memory(
            func_msg,
            OpenAIBackendRole.FUNCTION,
            timestamp=base_timestamp + 1e-6,
            return_records=self._enable_snapshot_clean,
        )

        # Register tool output for snapshot cleaning if enabled
        if self._enable_snapshot_clean and not mask_output and func_records:
            serialized_result = self._serialize_tool_result(result)
            self._register_tool_output_for_cache(
                func_name,
                tool_call_id,
                serialized_result,
                cast(List[MemoryRecord], func_records),
            )

        # Record information about this tool call
        tool_record = ToolCallingRecord(
            tool_name=func_name,
            args=args,
            result=result,
            tool_call_id=tool_call_id,
        )

        self._update_last_tool_call_state(tool_record)
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
                logger.info(
                    f"Termination triggered at iteration {iteration_count}"
                )
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
            if isinstance(response, Stream) or inspect.isgenerator(response):
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
                        final_reasoning = (
                            content_accumulator.get_full_reasoning_content()
                            or None
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
                            reasoning_content=final_reasoning,
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
            has_choices = bool(chunk.choices and len(chunk.choices) > 0)

            # Process chunk delta
            if has_choices:
                choice = chunk.choices[0]
                delta = choice.delta

                # Handle reasoning content streaming (for DeepSeek reasoner)
                if (
                    hasattr(delta, 'reasoning_content')
                    and delta.reasoning_content
                ):
                    content_accumulator.add_reasoning_content(
                        delta.reasoning_content
                    )
                    # Yield partial response with reasoning content
                    partial_response = (
                        self._create_streaming_response_with_accumulator(
                            content_accumulator,
                            "",  # No regular content yet
                            step_token_usage,
                            getattr(chunk, 'id', ''),
                            tool_call_records.copy(),
                            reasoning_delta=delta.reasoning_content,
                        )
                    )
                    yield partial_response

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
                        # Execute tools synchronously with
                        # optimized status updates
                        for (
                            status_response
                        ) in self._execute_tools_sync_with_status_accumulator(
                            accumulated_tool_calls,
                            tool_call_records,
                        ):
                            yield status_response

                        # Log sending status instead of adding to content
                        if tool_call_records:
                            logger.info("Sending back result to model")

                    # Record final message only if we have content AND no tool
                    # calls. If there are tool calls, _record_tool_calling
                    # will handle message recording.
                    final_content = content_accumulator.get_full_content()
                    if final_content.strip() and not accumulated_tool_calls:
                        final_reasoning = (
                            content_accumulator.get_full_reasoning_content()
                            or None
                        )
                        final_message = BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict={},
                            content=final_content,
                            reasoning_content=final_reasoning,
                        )

                        if response_format:
                            self._try_format_message(
                                final_message, response_format
                            )

                        self.record_message(final_message)
            if chunk.usage:
                # Handle final usage chunk, whether or not choices are present.
                # This happens when stream_options={"include_usage": True}
                # Update the final usage from this chunk
                self._update_token_usage_tracker(
                    step_token_usage, safe_model_dump(chunk.usage)
                )

                # Create final response with final usage
                should_finalize = stream_completed or not has_choices
                if should_finalize:
                    final_content = content_accumulator.get_full_content()
                    if final_content.strip():
                        final_reasoning = (
                            content_accumulator.get_full_reasoning_content()
                            or None
                        )
                        final_message = BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict={},
                            content=final_content,
                            reasoning_content=final_reasoning,
                        )

                        if response_format:
                            self._try_format_message(
                                final_message, response_format
                            )

                        # Create final response with final usage (not partial)
                        final_response = ChatAgentResponse(
                            msgs=[final_message],
                            terminated=False,
                            info={
                                "id": getattr(chunk, 'id', ''),
                                "usage": step_token_usage.copy(),
                                "finish_reasons": ["stop"],
                                "num_tokens": self._get_token_count(
                                    final_content
                                ),
                                "tool_calls": tool_call_records or [],
                                "external_tool_requests": None,
                                "streaming": False,
                                "partial": False,
                            },
                        )
                        yield final_response
                    break
            elif stream_completed:
                # We've seen finish_reason but no usage chunk yet; keep
                # consuming remaining chunks to capture final metadata.
                continue

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
                    'extra_content': None,
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
            # Handle extra_content if present
            if (
                hasattr(delta_tool_call, 'extra_content')
                and delta_tool_call.extra_content
            ):
                tool_call_entry['extra_content'] = (
                    delta_tool_call.extra_content
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
        tool_call_records: List[ToolCallingRecord],
    ) -> Generator[ChatAgentResponse, None, None]:
        r"""Execute multiple tools synchronously with proper content
        accumulation, using ThreadPoolExecutor for better timeout handling."""

        tool_calls_to_execute = []
        for _tool_call_index, tool_call_data in accumulated_tool_calls.items():
            if tool_call_data.get('complete', False):
                tool_calls_to_execute.append(tool_call_data)

        if not tool_calls_to_execute:
            # No tools to execute, return immediately
            return
            yield  # Make this a generator

        # Execute tools using ThreadPoolExecutor for proper timeout handling
        # Use max_workers=len() for parallel execution, with min of 1
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=max(1, len(tool_calls_to_execute))
        ) as executor:
            # Submit all tools first (parallel execution)
            futures_map = {}
            for tool_call_data in tool_calls_to_execute:
                function_name = tool_call_data['function']['name']
                try:
                    args = json.loads(tool_call_data['function']['arguments'])
                except json.JSONDecodeError:
                    args = tool_call_data['function']['arguments']

                # Log debug info
                logger.info(
                    f"Calling function: {function_name} with arguments: {args}"
                )

                # Submit tool execution (non-blocking)
                future = executor.submit(
                    self._execute_tool_from_stream_data, tool_call_data
                )
                futures_map[future] = (function_name, tool_call_data)

            # Wait for all futures to complete (or timeout)
            for future in concurrent.futures.as_completed(
                futures_map.keys(),
                timeout=self.tool_execution_timeout
                if self.tool_execution_timeout
                else None,
            ):
                function_name, tool_call_data = futures_map[future]

                try:
                    tool_call_record = future.result()
                    if tool_call_record:
                        tool_call_records.append(tool_call_record)
                        logger.info(
                            f"Function output: {tool_call_record.result}"
                        )
                except concurrent.futures.TimeoutError:
                    logger.warning(
                        f"Function '{function_name}' timed out after "
                        f"{self.tool_execution_timeout} seconds"
                    )
                    future.cancel()
                except Exception as e:
                    logger.error(
                        f"Error executing tool '{function_name}': {e}"
                    )

        # Ensure this function remains a generator (required by type signature)
        return
        yield  # This line is never reached but makes this a generator function

    def _execute_tool_from_stream_data(
        self, tool_call_data: Dict[str, Any]
    ) -> Optional[ToolCallingRecord]:
        r"""Execute a tool from accumulated stream data."""

        try:
            function_name = tool_call_data['function']['name']
            args = json.loads(tool_call_data['function']['arguments'])
            tool_call_id = tool_call_data['id']
            extra_content = tool_call_data.get('extra_content')

            if function_name in self._internal_tools:
                tool = self._internal_tools[function_name]
                try:
                    result = tool(**args)
                    # First, create and record the assistant message with tool
                    # call
                    assist_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        args=args,
                        tool_call_id=tool_call_id,
                        extra_content=extra_content,
                    )

                    # Then create the tool response message
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                        extra_content=extra_content,
                    )

                    # Record both messages with precise timestamps to ensure
                    # correct ordering
                    current_time_ns = time.time_ns()
                    base_timestamp = (
                        current_time_ns / 1_000_000_000
                    )  # Convert to seconds

                    self.update_memory(
                        assist_msg,
                        OpenAIBackendRole.ASSISTANT,
                        timestamp=base_timestamp,
                    )
                    self.update_memory(
                        func_msg,
                        OpenAIBackendRole.FUNCTION,
                        timestamp=base_timestamp + 1e-6,
                    )

                    tool_record = ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )
                    self._update_last_tool_call_state(tool_record)
                    return tool_record

                except Exception as e:
                    error_msg = (
                        f"Error executing tool '{function_name}': {e!s}"
                    )
                    result = {"error": error_msg}
                    logger.warning(error_msg)

                    # Record error response
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                        extra_content=extra_content,
                    )

                    self.update_memory(func_msg, OpenAIBackendRole.FUNCTION)

                    tool_record = ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )
                    self._update_last_tool_call_state(tool_record)
                    return tool_record
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
            extra_content = tool_call_data.get('extra_content')

            if function_name in self._internal_tools:
                # Create the tool call message
                assist_msg = FunctionCallingMessage(
                    role_name=self.role_name,
                    role_type=self.role_type,
                    meta_dict=None,
                    content="",
                    func_name=function_name,
                    args=args,
                    tool_call_id=tool_call_id,
                    extra_content=extra_content,
                )
                assist_ts = time.time_ns() / 1_000_000_000
                self.update_memory(
                    assist_msg,
                    OpenAIBackendRole.ASSISTANT,
                    timestamp=assist_ts,
                )

                tool = self._internal_tools[function_name]
                try:
                    # Try different invocation paths in order of preference
                    if hasattr(tool, 'func') and hasattr(
                        tool.func, 'async_call'
                    ):
                        # Case: FunctionTool wrapping an MCP tool
                        result = await tool.func.async_call(**args)

                    elif hasattr(tool, 'async_call') and callable(
                        tool.async_call
                    ):
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

                    # Create the tool response message
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                        extra_content=extra_content,
                    )
                    func_ts = time.time_ns() / 1_000_000_000
                    self.update_memory(
                        func_msg,
                        OpenAIBackendRole.FUNCTION,
                        timestamp=func_ts,
                    )

                    tool_record = ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )
                    self._update_last_tool_call_state(tool_record)
                    return tool_record

                except Exception as e:
                    error_msg = (
                        f"Error executing async tool '{function_name}': {e!s}"
                    )
                    result = {"error": error_msg}
                    logger.warning(error_msg)

                    # Record error response
                    func_msg = FunctionCallingMessage(
                        role_name=self.role_name,
                        role_type=self.role_type,
                        meta_dict=None,
                        content="",
                        func_name=function_name,
                        result=result,
                        tool_call_id=tool_call_id,
                        extra_content=extra_content,
                    )
                    func_ts = time.time_ns() / 1_000_000_000
                    self.update_memory(
                        func_msg,
                        OpenAIBackendRole.FUNCTION,
                        timestamp=func_ts,
                    )

                    tool_record = ToolCallingRecord(
                        tool_name=function_name,
                        args=args,
                        result=result,
                        tool_call_id=tool_call_id,
                    )
                    self._update_last_tool_call_state(tool_record)
                    return tool_record
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
        last_response = None
        async for response in self._astream_response(
            openai_messages, num_tokens, response_format
        ):
            last_response = response
            yield response

        # Clean tool call messages from memory after response generation
        if self.prune_tool_calls_from_memory and last_response:
            # Extract tool_calls from the last response info
            tool_calls = last_response.info.get("tool_calls", [])
            if tool_calls:
                self.memory.clean_tool_calls()

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
                logger.info(
                    f"Termination triggered at iteration {iteration_count}"
                )
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
                        final_reasoning = (
                            content_accumulator.get_full_reasoning_content()
                            or None
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
                            reasoning_content=final_reasoning,
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
                # Include extra_content if present
                if tool_call_data.get('extra_content'):
                    tool_call_dict["extra_content"] = tool_call_data[
                        "extra_content"
                    ]
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
        content accumulator.
        """

        tool_calls_complete = False
        stream_completed = False

        async for chunk in stream:
            has_choices = bool(chunk.choices and len(chunk.choices) > 0)

            # Process chunk delta
            if has_choices:
                choice = chunk.choices[0]
                delta = choice.delta

                # Handle reasoning content streaming (for DeepSeek reasoner)
                if (
                    hasattr(delta, 'reasoning_content')
                    and delta.reasoning_content
                ):
                    content_accumulator.add_reasoning_content(
                        delta.reasoning_content
                    )
                    # Yield partial response with reasoning content
                    partial_response = (
                        self._create_streaming_response_with_accumulator(
                            content_accumulator,
                            "",  # No regular content yet
                            step_token_usage,
                            getattr(chunk, 'id', ''),
                            tool_call_records.copy(),
                            reasoning_delta=delta.reasoning_content,
                        )
                    )
                    yield partial_response

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

                        # Log sending status instead of adding to content
                        if tool_call_records:
                            logger.info("Sending back result to model")

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
            if chunk.usage:
                # Handle final usage chunk, whether or not choices are present.
                # This happens when stream_options={"include_usage": True}
                # Update the final usage from this chunk
                self._update_token_usage_tracker(
                    step_token_usage, safe_model_dump(chunk.usage)
                )

                # Create final response with final usage
                should_finalize = stream_completed or not has_choices
                if should_finalize:
                    final_content = content_accumulator.get_full_content()
                    if final_content.strip():
                        final_reasoning = (
                            content_accumulator.get_full_reasoning_content()
                            or None
                        )
                        final_message = BaseMessage(
                            role_name=self.role_name,
                            role_type=self.role_type,
                            meta_dict={},
                            content=final_content,
                            reasoning_content=final_reasoning,
                        )

                        if response_format:
                            self._try_format_message(
                                final_message, response_format
                            )

                        # Create final response with final usage (not partial)
                        final_response = ChatAgentResponse(
                            msgs=[final_message],
                            terminated=False,
                            info={
                                "id": getattr(chunk, 'id', ''),
                                "usage": step_token_usage.copy(),
                                "finish_reasons": ["stop"],
                                "num_tokens": self._get_token_count(
                                    final_content
                                ),
                                "tool_calls": tool_call_records or [],
                                "external_tool_requests": None,
                                "streaming": False,
                                "partial": False,
                            },
                        )
                        yield final_response
                    break
            elif stream_completed:
                continue

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

                # Log debug info instead of adding to content
                logger.info(
                    f"Calling function: {function_name} with arguments: {args}"
                )

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

                        # Log debug info instead of adding to content
                        logger.info(f"Function output: {result_str}")

                except Exception as e:
                    if isinstance(e, asyncio.TimeoutError):
                        # Log timeout info instead of adding to content
                        logger.warning(
                            f"Function timed out after "
                            f"{self.tool_execution_timeout} seconds"
                        )
                    else:
                        logger.error(f"Error in async tool execution: {e}")
                    continue

        # Ensure this function remains an async generator
        return
        # This line is never reached but makes this an async generator function
        yield

    def _create_streaming_response_with_accumulator(
        self,
        accumulator: StreamContentAccumulator,
        new_content: str,
        step_token_usage: Dict[str, int],
        response_id: str = "",
        tool_call_records: Optional[List[ToolCallingRecord]] = None,
        reasoning_delta: Optional[str] = None,
    ) -> ChatAgentResponse:
        r"""Create a streaming response using content accumulator."""

        # Add new content; only build full content when needed
        if new_content:
            accumulator.add_streaming_content(new_content)

        if self.stream_accumulate:
            message_content = accumulator.get_full_content()
        else:
            message_content = new_content

        # Build meta_dict with reasoning information
        meta_dict: Dict[str, Any] = {}

        # Add reasoning content info
        full_reasoning = accumulator.get_full_reasoning_content()
        reasoning_payload: Optional[str] = None
        if full_reasoning:
            reasoning_payload = (
                full_reasoning
                if self.stream_accumulate
                else reasoning_delta or ""
            )
            if reasoning_payload:
                meta_dict["is_reasoning"] = accumulator.is_reasoning_phase
            else:
                reasoning_payload = None

        message = BaseMessage(
            role_name=self.role_name,
            role_type=self.role_type,
            meta_dict=meta_dict,
            content=message_content,
            reasoning_content=reasoning_payload,
        )

        return ChatAgentResponse(
            msgs=[message],
            terminated=False,
            info={
                "id": response_id,
                "usage": step_token_usage.copy(),
                "finish_reasons": ["streaming"],
                "num_tokens": self._get_token_count(message_content),
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
        # If with_memory is True, set system_message to None (it will be
        # copied from memory below, including any workflow context)
        # If with_memory is False, use the current system message
        # (which may include appended workflow context)
        # To avoid duplicated system memory.
        system_message = None if with_memory else self._system_message

        # Clone tools and collect toolkits that need registration
        cloned_tools, toolkits_to_register = self._clone_tools()

        new_agent = ChatAgent(
            system_message=system_message,
            model=self.model_backend.models,  # Pass the existing model_backend
            memory=None,  # clone memory later
            message_window_size=getattr(self.memory, "window_size", None),
            token_limit=getattr(
                self.memory.get_context_creator(), "token_limit", None
            ),
            output_language=self._output_language,
            tools=cast(List[Union[FunctionTool, Callable]], cloned_tools),
            toolkits_to_register_agent=toolkits_to_register,
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
            prune_tool_calls_from_memory=self.prune_tool_calls_from_memory,
            stream_accumulate=self.stream_accumulate,
        )

        # Copy memory if requested
        if with_memory:
            # Get all records from the current memory
            context_records = self.memory.retrieve()
            # Write them to the new agent's memory
            for context_record in context_records:
                new_agent.memory.write_record(context_record.memory_record)

        return new_agent

    def _clone_tools(
        self,
    ) -> Tuple[List[FunctionTool], List[RegisteredAgentToolkit]]:
        r"""Clone tools and return toolkits that need agent registration.

        This method handles stateful toolkits by cloning them if they have
        a clone_for_new_session method, and collecting RegisteredAgentToolkit
        instances for later registration.

        Returns:
            Tuple containing:
            - List of cloned tools/functions
            - List of RegisteredAgentToolkit instances need registration
        """
        cloned_tools = []
        toolkits_to_register = []
        cloned_toolkits = {}
        # Cache for cloned toolkits by original toolkit id

        for tool in self._internal_tools.values():
            # Check if this tool is a method bound to a toolkit instance
            if hasattr(tool.func, '__self__'):
                toolkit_instance = tool.func.__self__
                toolkit_id = id(toolkit_instance)

                if toolkit_id not in cloned_toolkits:
                    # Check if the toolkit has a clone method
                    if hasattr(toolkit_instance, 'clone_for_new_session'):
                        try:
                            import uuid

                            new_session_id = str(uuid.uuid4())[:8]
                            new_toolkit = (
                                toolkit_instance.clone_for_new_session(
                                    new_session_id
                                )
                            )

                            # If this is a RegisteredAgentToolkit,
                            # add it to registration list
                            if isinstance(new_toolkit, RegisteredAgentToolkit):
                                toolkits_to_register.append(new_toolkit)

                            cloned_toolkits[toolkit_id] = new_toolkit
                        except Exception as e:
                            logger.warning(
                                f"Failed to clone toolkit {toolkit_instance.__class__.__name__}: {e}"  # noqa:E501
                            )
                            # Use original toolkit if cloning fails
                            cloned_toolkits[toolkit_id] = toolkit_instance
                    else:
                        # Toolkit doesn't support cloning, use original
                        cloned_toolkits[toolkit_id] = toolkit_instance

                # Get the method from the cloned (or original) toolkit
                toolkit = cloned_toolkits[toolkit_id]
                method_name = tool.func.__name__

                # Check if toolkit was actually cloned or just reused
                toolkit_was_cloned = toolkit is not toolkit_instance

                if hasattr(toolkit, method_name):
                    new_method = getattr(toolkit, method_name)

                    # If toolkit wasn't cloned (stateless), preserve the
                    # original function to maintain any enhancements/wrappers
                    if not toolkit_was_cloned:
                        # Toolkit is stateless, safe to reuse original function
                        cloned_tools.append(
                            FunctionTool(
                                func=tool.func,
                                openai_tool_schema=tool.get_openai_tool_schema(),
                            )
                        )
                        continue

                    # Toolkit was cloned, use the new method
                    # Wrap cloned method into a new FunctionTool,
                    # preserving schema
                    try:
                        new_tool = FunctionTool(
                            func=new_method,
                            openai_tool_schema=tool.get_openai_tool_schema(),
                        )
                        cloned_tools.append(new_tool)
                    except Exception as e:
                        # If wrapping fails, fallback to wrapping the original
                        # function with its schema to maintain consistency
                        logger.warning(
                            f"Failed to wrap cloned toolkit "
                            f"method '{method_name}' "
                            f"with FunctionTool: {e}. Using original "
                            f"function with preserved schema instead."
                        )
                        cloned_tools.append(
                            FunctionTool(
                                func=tool.func,
                                openai_tool_schema=tool.get_openai_tool_schema(),
                            )
                        )
                else:
                    # Fallback to original function wrapped in FunctionTool
                    cloned_tools.append(
                        FunctionTool(
                            func=tool.func,
                            openai_tool_schema=tool.get_openai_tool_schema(),
                        )
                    )
            else:
                # Not a toolkit method, preserve FunctionTool schema directly
                cloned_tools.append(
                    FunctionTool(
                        func=tool.func,
                        openai_tool_schema=tool.get_openai_tool_schema(),
                    )
                )

        return cloned_tools, toolkits_to_register

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
