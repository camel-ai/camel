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

import json
import logging
import textwrap
import threading
import uuid
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
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

if TYPE_CHECKING:
    from camel.terminators import ResponseTerminator

logger = logging.getLogger(__name__)

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

    def reset(self):
        r"""Resets the :obj:`ChatAgent` to its initial state."""
        self.terminated = False
        self.init_messages()
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
                platform, type_ = model_spec[0], model_spec[1]  # type: ignore[index]
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
    ) -> ChatAgentResponse:
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
            ChatAgentResponse: Contains output messages, a termination status
                flag, and session information.
        """

        # Set Langfuse session_id using agent_id for trace grouping
        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

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
        iteration_count = 0

        while True:
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
                        tool_call_records.append(
                            self._execute_tool(tool_call_request)
                        )

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
    ) -> ChatAgentResponse:
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
            ChatAgentResponse: A struct containing the output messages,
                a boolean indicating whether the chat session has terminated,
                and information about the chat session.
        """
        try:
            from camel.utils.langfuse import set_current_agent_session_id

            set_current_agent_session_id(self.agent_id)
        except ImportError:
            pass  # Langfuse not available

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
        iteration_count = 0
        while True:
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
        self._record_final_output(response.output_messages)

        # Create token usage tracker for this step
        step_token_usage = self._create_token_usage_tracker()

        # Update with response usage
        self._update_token_usage_tracker(step_token_usage, response.usage_dict)

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

        if isinstance(response, ChatCompletion):
            return self._handle_batch_response(response)
        else:
            return self._handle_stream_response(response, num_tokens)

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

        if isinstance(response, ChatCompletion):
            return self._handle_batch_response(response)
        else:
            return await self._ahandle_stream_response(response, num_tokens)

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

    def _handle_stream_response(
        self,
        response: Stream[ChatCompletionChunk],
        prompt_tokens: int,
    ) -> ModelResponse:
        r"""Process a stream response from the model and extract the necessary
        information.

        Args:
            response (dict): Model response.
            prompt_tokens (int): Number of input prompt tokens.

        Returns:
            _ModelResponse: a parsed model response.
        """
        content_dict: defaultdict = defaultdict(lambda: "")
        finish_reasons_dict: defaultdict = defaultdict(lambda: "")
        output_messages: List[BaseMessage] = []
        response_id: str = ""
        # All choices in one response share one role
        for chunk in response:
            # Some model platforms like siliconflow may return None for the
            # chunk.id
            response_id = chunk.id if chunk.id else str(uuid.uuid4())
            self._handle_chunk(
                chunk, content_dict, finish_reasons_dict, output_messages
            )
        finish_reasons = [
            finish_reasons_dict[i] for i in range(len(finish_reasons_dict))
        ]
        usage_dict = self.get_usage_dict(output_messages, prompt_tokens)

        # TODO: Handle tool calls
        return ModelResponse(
            response=response,
            tool_call_requests=None,
            output_messages=output_messages,
            finish_reasons=finish_reasons,
            usage_dict=usage_dict,
            response_id=response_id,
        )

    async def _ahandle_stream_response(
        self,
        response: AsyncStream[ChatCompletionChunk],
        prompt_tokens: int,
    ) -> ModelResponse:
        r"""Process a stream response from the model and extract the necessary
        information.

        Args:
            response (dict): Model response.
            prompt_tokens (int): Number of input prompt tokens.

        Returns:
            _ModelResponse: a parsed model response.
        """
        content_dict: defaultdict = defaultdict(lambda: "")
        finish_reasons_dict: defaultdict = defaultdict(lambda: "")
        output_messages: List[BaseMessage] = []
        response_id: str = ""
        # All choices in one response share one role
        async for chunk in response:
            # Some model platforms like siliconflow may return None for the
            # chunk.id
            response_id = chunk.id if chunk.id else str(uuid.uuid4())
            self._handle_chunk(
                chunk, content_dict, finish_reasons_dict, output_messages
            )
        finish_reasons = [
            finish_reasons_dict[i] for i in range(len(finish_reasons_dict))
        ]
        usage_dict = self.get_usage_dict(output_messages, prompt_tokens)

        # TODO: Handle tool calls
        return ModelResponse(
            response=response,
            tool_call_requests=None,
            output_messages=output_messages,
            finish_reasons=finish_reasons,
            usage_dict=usage_dict,
            response_id=response_id,
        )

    def _handle_chunk(
        self,
        chunk: ChatCompletionChunk,
        content_dict: defaultdict,
        finish_reasons_dict: defaultdict,
        output_messages: List[BaseMessage],
    ) -> None:
        r"""Handle a chunk of the model response."""
        for choice in chunk.choices:
            index = choice.index
            delta = choice.delta
            if delta.content is not None:
                content_dict[index] += delta.content

            if not choice.finish_reason:
                continue

            finish_reasons_dict[index] = choice.finish_reason
            chat_message = BaseMessage(
                role_name=self.role_name,
                role_type=self.role_type,
                meta_dict=dict(),
                content=content_dict[index],
            )
            output_messages.append(chat_message)

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
            result = tool(**args)
        except Exception as e:
            # Capture the error message to prevent framework crash
            error_msg = f"Error executing tool '{func_name}': {e!s}"
            result = {"error": error_msg}
            logging.warning(error_msg)

        return self._record_tool_calling(func_name, args, result, tool_call_id)

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
            result = {"error": error_msg}
            logging.warning(error_msg)

        return self._record_tool_calling(func_name, args, result, tool_call_id)

    def _record_tool_calling(
        self,
        func_name: str,
        args: Dict[str, Any],
        result: Any,
        tool_call_id: str,
    ):
        r"""Record the tool calling information in the memory, and return the
        tool calling record.
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
            tools=list(self._internal_tools.values()),
            external_tools=[
                schema for schema in self._external_tool_schemas.values()
            ],
            response_terminators=self.response_terminators,
            scheduling_strategy=self.model_backend.scheduling_strategy.__name__,
            max_iteration=self.max_iteration,
            stop_event=self.stop_event,
        )

        # Copy memory if requested
        if with_memory:
            # Get all records from the current memory
            context_records = self.memory.retrieve()
            # Write them to the new agent's memory
            for context_record in context_records:
                new_agent.memory.write_record(context_record.memory_record)

        return new_agent

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
