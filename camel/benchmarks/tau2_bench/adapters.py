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
r"""Adapters that bridge CAMEL ``ChatAgent`` instances with the τ² runtime."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from tau2.agent.base import AgentError, BaseAgent, ValidAgentInputMessage
from tau2.data_model.message import (
    AssistantMessage,
    Message,
    MultiToolMessage,
    SystemMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.user.base import (
    OUT_OF_SCOPE,
    STOP,
    TRANSFER,
    BaseUser,
    UserError,
    UserState,
    ValidUserInputMessage,
)

from camel.agents import ChatAgent
from camel.agents._types import ToolCallRequest
from camel.messages import BaseMessage, FunctionCallingMessage
from camel.responses import ChatAgentResponse
from camel.types import OpenAIBackendRole

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRegistry:
    r"""Tracks tool-call identifiers so tool responses remain traceable."""

    mapping: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def register(
        self, tool_call_id: str, tool_name: str, args: Optional[Dict[str, Any]] = None
    ) -> None:
        if not tool_call_id:
            return
        self.mapping[tool_call_id] = {"name": tool_name, "args": args or {}}

    def resolve(self, tool_call_id: Optional[str]) -> str:
        if tool_call_id is None:
            return "tool"
        info = self.mapping.get(tool_call_id)
        if info is None:
            return tool_call_id
        return info.get("name", tool_call_id)

    def resolve_args(self, tool_call_id: Optional[str]) -> Dict[str, Any]:
        if tool_call_id is None:
            return {}
        info = self.mapping.get(tool_call_id)
        if info is None:
            return {}
        return dict(info.get("args", {}) or {})


@dataclass
class CamelChatAgentState:
    r"""Mutable state passed between τ² orchestrator steps.

    Mirrors the original tau2 AgentState structure to ensure equivalence.
    """

    tool_registry: ToolCallRegistry = field(default_factory=ToolCallRegistry)
    system_messages: List[SystemMessage] = field(default_factory=list)
    messages: List[Message] = field(default_factory=list)


@dataclass
class TokenTracker:
    r"""Accumulates token usage for a ChatAgent-backed participant."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    fallback_total_tokens: int = 0

    def reset(self) -> None:
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.fallback_total_tokens = 0

    def add_usage(
        self, usage: Optional[Dict[str, Any]], fallback_total: Optional[int]
    ) -> None:
        if usage:
            prompt = usage.get("prompt_tokens")
            completion = usage.get("completion_tokens")
            if prompt is not None:
                self.prompt_tokens += int(prompt)
            if completion is not None:
                self.completion_tokens += int(completion)
            # Some providers only expose total tokens without a breakdown.
            if (
                prompt is None
                and completion is None
                and usage.get("total_tokens") is not None
            ):
                self.fallback_total_tokens += int(usage["total_tokens"])
            return
        if fallback_total is not None:
            self.fallback_total_tokens += int(fallback_total)

    def total_tokens(self) -> int:
        total = self.prompt_tokens + self.completion_tokens
        if total == 0:
            total = self.fallback_total_tokens
        return total

    def as_dict(self) -> Optional[Dict[str, int]]:
        total = self.total_tokens()
        data: Dict[str, int] = {}
        if self.prompt_tokens:
            data["prompt_tokens"] = self.prompt_tokens
        if self.completion_tokens:
            data["completion_tokens"] = self.completion_tokens
        if total:
            data["total_tokens"] = total
        if data:
            return data
        return None


def _convert_request_to_tool_call(
    request: ToolCallRequest, registry: ToolCallRegistry, requestor: str
) -> ToolCall:
    call_id = request.tool_call_id or f"call_{uuid.uuid4().hex}"
    registry.register(call_id, request.tool_name, request.args or {})
    return ToolCall(
        id=call_id,
        name=request.tool_name,
        arguments=request.args or {},
        requestor=requestor,
    )


def _append_tool_messages_to_memory(
    chat_agent: ChatAgent,
    message: ValidAgentInputMessage | ValidUserInputMessage,
    registry: ToolCallRegistry,
) -> None:
    if isinstance(message, MultiToolMessage):
        tool_messages = message.tool_messages
    elif isinstance(message, ToolMessage):
        tool_messages = [message]
    else:
        return

    for tool_msg in tool_messages:
        tool_name = registry.resolve(tool_msg.id)
        tool_args = registry.resolve_args(tool_msg.id)
        func_msg = FunctionCallingMessage(
            role_name="Tool",
            role_type=chat_agent.role_type,
            meta_dict=None,
            content="",
            func_name=tool_name,
            args=tool_args,
            result=tool_msg.content,
            tool_call_id=tool_msg.id,
        )
        chat_agent.update_memory(func_msg, OpenAIBackendRole.FUNCTION)


def _build_tool_calls_payload(
    requests: Sequence[ToolCallRequest],
) -> List[Dict[str, Any]]:
    tool_calls: List[Dict[str, Any]] = []
    for request in requests:
        if not request.tool_call_id:
            request.tool_call_id = f"call_{uuid.uuid4().hex}"
        tool_calls.append(
            {
                "id": request.tool_call_id,
                "type": "function",
                "function": {
                    "name": request.tool_name,
                    "arguments": json.dumps(request.args or {}),
                },
            }
        )
    return tool_calls


def _record_external_tool_calls(
    chat_agent: ChatAgent,
    requests: Sequence[ToolCallRequest],
    content: Optional[str],
) -> None:
    tool_calls = _build_tool_calls_payload(requests)
    memory = getattr(chat_agent, "memory", None)
    history_block = getattr(memory, "_chat_history_block", None)
    storage = getattr(history_block, "storage", None)
    if storage is not None and hasattr(storage, "load") and hasattr(storage, "save"):
        record_dicts = storage.load()
        for i in range(len(record_dicts) - 1, -1, -1):
            record = record_dicts[i]
            if (
                record.get("role_at_backend")
                != OpenAIBackendRole.ASSISTANT.value
            ):
                continue
            message = record.get("message", {})
            message["tool_calls"] = tool_calls
            record["message"] = message
            storage.clear()
            storage.save(record_dicts)
            return
    assistant_msg = BaseMessage.make_assistant_message(
        role_name=chat_agent.role_name,
        content=content or "",
        meta_dict={"tool_calls": tool_calls},
    )
    chat_agent.update_memory(assistant_msg, OpenAIBackendRole.ASSISTANT)


def _step_without_user_input(chat_agent: ChatAgent) -> ChatAgentResponse:
    openai_messages, num_tokens = chat_agent.memory.get_context()
    response = chat_agent._get_model_response(  # type: ignore[attr-defined]
        openai_messages,
        num_tokens=num_tokens,
        current_iteration=0,
        response_format=None,
        tool_schemas=chat_agent._get_full_tool_schemas(),  # type: ignore[attr-defined]
        prev_num_openai_messages=0,
    )
    external_requests: Optional[List[ToolCallRequest]] = None
    if response.tool_call_requests:
        external_requests = []
        external_tools = getattr(chat_agent, "_external_tool_schemas", {})
        for request in response.tool_call_requests:
            if request.tool_name in external_tools:
                external_requests.append(request)
    chat_agent._record_final_output(  # type: ignore[attr-defined]
        response.output_messages
    )
    usage = response.usage_dict or {}
    return chat_agent._convert_to_chatagent_response(  # type: ignore[attr-defined]
        response,
        tool_call_records=[],
        num_tokens=num_tokens,
        external_tool_call_requests=external_requests,
        step_api_prompt_tokens=usage.get("prompt_tokens", 0),
        step_api_completion_tokens=usage.get("completion_tokens", 0),
        step_api_total_tokens=usage.get("total_tokens", 0),
    )


def _extract_external_requests(
    response: ChatAgentResponse,
) -> List[ToolCallRequest]:
    raw_requests = response.info.get("external_tool_call_requests")
    if not raw_requests:
        return []
    requests: List[ToolCallRequest] = []
    for entry in raw_requests:
        if isinstance(entry, ToolCallRequest):
            requests.append(entry)
            continue
        # Fallback for dict-like payloads (e.g., after serialization)
        requests.append(
            ToolCallRequest(
                tool_name=entry.get("tool_name"),
                args=entry.get("args", {}),
                tool_call_id=entry.get("tool_call_id"),
            )
        )
    return requests


def _extract_usage_payload(
    response: ChatAgentResponse,
) -> tuple[Optional[Dict[str, Any]], Optional[int]]:
    info = response.info or {}
    usage = info.get("usage")
    if not isinstance(usage, dict):
        usage = None

    fallback_total: Optional[int] = None
    if usage:
        prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        if prompt is None and completion is None:
            total = usage.get("total_tokens")
            if isinstance(total, (int, float)):
                fallback_total = int(total)
    else:
        num_tokens = info.get("num_tokens")
        if isinstance(num_tokens, (int, float)):
            fallback_total = int(num_tokens)

    return usage, fallback_total


class CamelTau2Agent(BaseAgent[CamelChatAgentState]):
    r"""Wraps a CAMEL ``ChatAgent`` so τ² can treat it as a native agent.

    This implementation mirrors the original tau2 LLMAgent behavior by
    building messages directly from state and calling the model backend,
    ensuring exact equivalence with the original benchmark.
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        tool_schemas: Sequence[dict],
        system_prompt: str,
    ):
        super().__init__()
        self._chat_agent = chat_agent
        self._system_prompt = system_prompt
        self._tool_schemas = list(tool_schemas)
        self._install_external_tools(tool_schemas)
        self._token_tracker = TokenTracker()

    def _install_external_tools(self, tool_schemas: Sequence[dict]) -> None:
        existing_tools = list(self._chat_agent.tool_dict.keys())
        if existing_tools:
            self._chat_agent.remove_tools(existing_tools)
        for schema in tool_schemas:
            self._chat_agent.add_external_tool(schema)
        if tool_schemas:
            self._ensure_tool_choice()

    def _ensure_tool_choice(self) -> None:
        backend = getattr(self._chat_agent, "model_backend", None)
        if backend is None:
            return
        config = dict(getattr(backend, "model_config_dict", {}))
        if "tool_choice" not in config:
            config["tool_choice"] = "auto"
            backend.model_config_dict = config

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> CamelChatAgentState:
        # Don't reset ChatAgent's memory; we build context directly
        self._token_tracker.reset()
        state = CamelChatAgentState(
            tool_registry=ToolCallRegistry(),
            system_messages=[
                SystemMessage(role="system", content=self._system_prompt)
            ],
            messages=list(message_history) if message_history else [],
        )
        # Register any existing tool calls from message history
        if message_history:
            for msg in message_history:
                if isinstance(msg, AssistantMessage) and msg.tool_calls:
                    for tc in msg.tool_calls:
                        state.tool_registry.register(tc.id, tc.name, tc.arguments)
        return state

    def _build_openai_messages_from_state(
        self, state: CamelChatAgentState
    ) -> List[Dict[str, Any]]:
        r"""Build OpenAI-format messages from state.

        This mirrors the original tau2 LLMAgent behavior:
        messages = state.system_messages + state.messages
        """
        openai_messages: List[Dict[str, Any]] = []

        # Add system message first
        for sys_msg in state.system_messages:
            openai_messages.append({
                "role": "system",
                "content": sys_msg.content,
            })

        # Add conversation messages (no role flipping for agent)
        for message in state.messages:
            if isinstance(message, UserMessage):
                openai_messages.append({
                    "role": "user",
                    "content": message.content,
                })
            elif isinstance(message, AssistantMessage):
                msg_dict: Dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content,
                }
                if message.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in message.tool_calls
                    ]
                openai_messages.append(msg_dict)
            elif isinstance(message, ToolMessage):
                openai_messages.append({
                    "role": "tool",
                    "content": message.content,
                    "tool_call_id": message.id,
                })

        return openai_messages

    def generate_next_message(
        self,
        message: ValidAgentInputMessage,
        state: CamelChatAgentState,
    ) -> tuple[AssistantMessage, CamelChatAgentState]:
        # Update state with incoming message (mirrors original behavior)
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)

        # Build context directly from state (mirrors original exactly)
        openai_messages = self._build_openai_messages_from_state(state)

        # Get tool schemas
        tool_schemas = self._chat_agent._get_full_tool_schemas()

        # Make direct model call (bypassing ChatAgent memory management)
        backend = self._chat_agent.model_backend
        response = backend.run(openai_messages, tools=tool_schemas or None)

        # Extract usage info
        usage_dict = None
        if hasattr(response, "usage") and response.usage:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        self._token_tracker.add_usage(usage_dict, None)

        # Convert response to AssistantMessage
        assistant_msg = self._response_to_assistant_message_from_completion(
            response, state.tool_registry, usage_dict
        )

        # Update state with response
        state.messages.append(assistant_msg)
        return assistant_msg, state

    def _response_to_assistant_message_from_completion(
        self,
        response: Any,
        registry: ToolCallRegistry,
        usage: Optional[Dict[str, Any]],
    ) -> AssistantMessage:
        r"""Convert model completion response to AssistantMessage."""
        choice = response.choices[0]
        content = choice.message.content
        tool_calls_raw = choice.message.tool_calls

        if tool_calls_raw:
            tool_calls = []
            for tc in tool_calls_raw:
                # Register the tool call
                registry.register(tc.id, tc.function.name, json.loads(tc.function.arguments))
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                        requestor="assistant",
                    )
                )
            return AssistantMessage(
                role="assistant",
                content=content,
                tool_calls=tool_calls,
                usage=usage,
            )

        if content is None:
            raise AgentError("Assistant response did not contain content.")

        return AssistantMessage(
            role="assistant",
            content=content,
            usage=usage,
        )

    @classmethod
    def is_stop(cls, message: AssistantMessage) -> bool:
        if message.is_tool_call():
            return False
        if not message.content:
            return False
        return STOP in message.content

    def stop(
        self,
        message: Optional[ValidAgentInputMessage] = None,
        state: Optional[CamelChatAgentState] = None,
    ) -> None:
        # Nothing to clean up; ChatAgent clones are short-lived per task.
        return None

    def set_seed(self, seed: int) -> None:
        backend = getattr(self._chat_agent, "model_backend", None)
        if backend is None:
            return
        config = dict(getattr(backend, "model_config_dict", {}))
        config["seed"] = seed
        backend.model_config_dict = config

    def get_token_usage(self) -> Optional[Dict[str, int]]:
        return self._token_tracker.as_dict()


class CamelTau2User(BaseUser):
    r"""ChatAgent-powered replacement for τ²'s default user simulator.

    This implementation mirrors the original tau2 UserSimulator behavior by
    using state.flip_roles() to build the LLM context on each call, ensuring
    exact equivalence with the original benchmark.
    """

    def __init__(
        self,
        chat_agent: ChatAgent,
        tool_schemas: Sequence[dict],
        system_prompt: str,
    ):
        super().__init__(instructions=None, llm=None, llm_args=None)
        self._chat_agent = chat_agent
        self._system_prompt = system_prompt
        self._tool_schemas = list(tool_schemas)
        self._install_external_tools()
        self._registry = ToolCallRegistry()
        self._token_tracker = TokenTracker()

    def _install_external_tools(self) -> None:
        existing_tools = list(self._chat_agent.tool_dict.keys())
        if existing_tools:
            self._chat_agent.remove_tools(existing_tools)
        for schema in self._tool_schemas:
            self._chat_agent.add_external_tool(schema)
        if self._tool_schemas:
            self._ensure_tool_choice()

    def _ensure_tool_choice(self) -> None:
        backend = getattr(self._chat_agent, "model_backend", None)
        if backend is None:
            return
        config = dict(getattr(backend, "model_config_dict", {}))
        if "tool_choice" not in config:
            config["tool_choice"] = "auto"
            backend.model_config_dict = config

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> UserState:
        # Don't reset ChatAgent's memory; we rebuild context each call
        self._token_tracker.reset()
        self._registry = ToolCallRegistry()
        state = UserState(
            system_messages=[
                SystemMessage(role="system", content=self._system_prompt)
            ],
            messages=list(message_history) if message_history else [],
        )
        return state

    def _build_openai_messages_from_state(
        self, state: UserState
    ) -> List[Dict[str, Any]]:
        r"""Build OpenAI-format messages from state using flip_roles().

        This mirrors the original tau2 UserSimulator behavior exactly:
        - UserMessage → AssistantMessage (preserving tool_calls)
        - AssistantMessage (no tool_calls) → UserMessage
        - ToolMessage (requestor=user) → ToolMessage
        """
        openai_messages: List[Dict[str, Any]] = []

        # Add system message first
        for sys_msg in state.system_messages:
            openai_messages.append({
                "role": "system",
                "content": sys_msg.content,
            })

        # Apply flip_roles() logic from original tau2
        for message in state.messages:
            if isinstance(message, UserMessage):
                # User's message becomes assistant in LLM context
                msg_dict: Dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content,
                }
                if message.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in message.tool_calls
                    ]
                openai_messages.append(msg_dict)
            elif isinstance(message, AssistantMessage):
                # Agent's message becomes user in LLM context
                if message.is_tool_call():
                    # Original tau2 raises error for this case
                    raise ValueError(
                        f"Tool calls not supported in flipped messages: {message}"
                    )
                openai_messages.append({
                    "role": "user",
                    "content": message.content,
                })
            elif isinstance(message, ToolMessage):
                # Only include tool messages for user (requestor=user)
                if message.requestor == "user":
                    openai_messages.append({
                        "role": "tool",
                        "content": message.content,
                        "tool_call_id": message.id,
                    })
                # Tool messages for assistant are not included in user's context

        return openai_messages

    def generate_next_message(
        self,
        message: ValidUserInputMessage,
        state: UserState,
    ) -> tuple[UserMessage, UserState]:
        # Update state with incoming message (mirrors original behavior)
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)

        # Build context using flip_roles() logic (mirrors original exactly)
        openai_messages = self._build_openai_messages_from_state(state)

        # Get tool schemas
        tool_schemas = self._chat_agent._get_full_tool_schemas()

        # Make direct model call (bypassing ChatAgent memory management)
        backend = self._chat_agent.model_backend
        response = backend.run(openai_messages, tools=tool_schemas or None)

        # Extract usage info
        usage_dict = None
        if hasattr(response, "usage") and response.usage:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        self._token_tracker.add_usage(usage_dict, None)

        # Convert response to UserMessage
        user_message = self._response_to_user_message_from_completion(
            response, usage_dict
        )

        # Update state with response
        state.messages.append(user_message)
        return user_message, state

    def _response_to_user_message_from_completion(
        self,
        response: Any,
        usage: Optional[Dict[str, Any]],
    ) -> UserMessage:
        r"""Convert model completion response to UserMessage."""
        choice = response.choices[0]
        content = choice.message.content
        tool_calls_raw = choice.message.tool_calls

        if tool_calls_raw:
            tool_calls = [
                ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=json.loads(tc.function.arguments),
                    requestor="user",
                )
                for tc in tool_calls_raw
            ]
            return UserMessage(
                role="user",
                content=content,
                tool_calls=tool_calls,
                usage=usage,
            )

        if content is None:
            raise UserError("User simulator produced no textual reply.")

        return UserMessage(role="user", content=content, usage=usage)

    @classmethod
    def is_stop(cls, message: UserMessage) -> bool:
        if message.is_tool_call() or not message.content:
            return False
        tokens = (STOP, TRANSFER, OUT_OF_SCOPE)
        return any(token in message.content for token in tokens)

    def set_seed(self, seed: int) -> None:
        backend = getattr(self._chat_agent, "model_backend", None)
        if backend is None:
            return
        config = dict(getattr(backend, "model_config_dict", {}))
        config["seed"] = seed
        backend.model_config_dict = config

    def get_token_usage(self) -> Optional[Dict[str, int]]:
        return self._token_tracker.as_dict()
