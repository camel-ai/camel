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
"""Adapters that bridge CAMEL ``ChatAgent`` instances with the τ² runtime."""

from __future__ import annotations

import logging
import textwrap
import uuid
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from camel.agents import ChatAgent
from camel.agents._types import ToolCallRequest
from camel.messages import BaseMessage, FunctionCallingMessage
from camel.responses import ChatAgentResponse
from camel.types import OpenAIBackendRole

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

logger = logging.getLogger(__name__)


@dataclass
class ToolCallRegistry:
    """Tracks tool-call identifiers so tool responses can be contextualised."""

    mapping: Dict[str, str] = field(default_factory=dict)

    def register(self, tool_call_id: str, tool_name: str) -> None:
        if not tool_call_id:
            return
        self.mapping[tool_call_id] = tool_name

    def resolve(self, tool_call_id: Optional[str]) -> str:
        if tool_call_id is None:
            return "tool"
        return self.mapping.get(tool_call_id, tool_call_id)


@dataclass
class CamelChatAgentState:
    """Mutable state passed between τ² orchestrator steps."""

    tool_registry: ToolCallRegistry = field(default_factory=ToolCallRegistry)


def _convert_request_to_tool_call(
    request: ToolCallRequest, registry: ToolCallRegistry, requestor: str
) -> ToolCall:
    call_id = request.tool_call_id or f"call_{uuid.uuid4().hex}"
    registry.register(call_id, request.tool_name)
    return ToolCall(
        id=call_id,
        name=request.tool_name,
        arguments=request.args or {},
        requestor=requestor,
    )


def _format_tool_message(
    tool_msg: ToolMessage, registry: ToolCallRegistry
) -> str:
    tool_name = registry.resolve(tool_msg.id)
    status = "ERROR" if tool_msg.error else "OK"
    content = tool_msg.content or ""
    formatted = textwrap.dedent(
        f"""
        [Tool: {tool_name} | call_id={tool_msg.id} | status={status}]
        {content}
        """
    ).strip()
    return formatted


def _flatten_tool_messages(
    message: ValidAgentInputMessage | ValidUserInputMessage,
    registry: ToolCallRegistry,
) -> Optional[str]:
    if isinstance(message, MultiToolMessage):
        observations = [
            _format_tool_message(tool_msg, registry)
            for tool_msg in message.tool_messages
        ]
        return "\n\n".join(observations)
    if isinstance(message, ToolMessage):
        return _format_tool_message(message, registry)
    return None


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


class CamelTau2Agent(BaseAgent[CamelChatAgentState]):
    """Wraps a CAMEL ``ChatAgent`` so τ² can treat it as a native agent."""

    def __init__(
        self,
        chat_agent: ChatAgent,
        tool_schemas: Sequence[dict],
    ):
        super().__init__()
        self._chat_agent = chat_agent
        self._install_external_tools(tool_schemas)

    def _install_external_tools(self, tool_schemas: Sequence[dict]) -> None:
        existing_tools = list(self._chat_agent.tool_dict.keys())
        if existing_tools:
            self._chat_agent.remove_tools(existing_tools)
        for schema in tool_schemas:
            self._chat_agent.add_external_tool(schema)

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> CamelChatAgentState:
        state = CamelChatAgentState()
        self._chat_agent.reset()
        if message_history:
            self._rehydrate_history(message_history, state)
        return state

    def _rehydrate_history(
        self,
        history: Iterable[Message],
        state: CamelChatAgentState,
    ) -> None:
        for message in history:
            if isinstance(message, UserMessage):
                if not message.content:
                    continue
                user_msg = BaseMessage.make_user_message(
                    role_name="User",
                    content=message.content,
                )
                self._chat_agent.update_memory(
                    user_msg, OpenAIBackendRole.USER
                )
            elif isinstance(message, AssistantMessage):
                if message.is_tool_call():
                    for tool_call in message.tool_calls or []:
                        state.tool_registry.register(
                            tool_call.id, tool_call.name
                        )
                        func_msg = FunctionCallingMessage(
                            role_name=self._chat_agent.role_name,
                            role_type=self._chat_agent.role_type,
                            meta_dict=None,
                            content="",
                            func_name=tool_call.name,
                            args=tool_call.arguments,
                            tool_call_id=tool_call.id,
                        )
                        self._chat_agent.update_memory(
                            func_msg, OpenAIBackendRole.ASSISTANT
                        )
                elif message.content:
                    assistant_msg = BaseMessage.make_assistant_message(
                        role_name=self._chat_agent.role_name,
                        content=message.content,
                    )
                    self._chat_agent.record_message(assistant_msg)
            elif isinstance(message, ToolMessage):
                observation = _format_tool_message(
                    message, state.tool_registry
                )
                tool_as_user = BaseMessage.make_user_message(
                    role_name="Tool",
                    content=observation,
                )
                self._chat_agent.update_memory(
                    tool_as_user, OpenAIBackendRole.USER
                )

    def generate_next_message(
        self,
        message: ValidAgentInputMessage,
        state: CamelChatAgentState,
    ) -> tuple[AssistantMessage, CamelChatAgentState]:
        observation = _flatten_tool_messages(message, state.tool_registry)
        if observation is None:
            # Regular user utterance
            prompt = message.content or ""
        else:
            prompt = observation
        response = self._chat_agent.step(prompt)
        assistant_msg = self._response_to_assistant_message(
            response, state.tool_registry
        )
        return assistant_msg, state

    def _response_to_assistant_message(
        self,
        response: ChatAgentResponse,
        registry: ToolCallRegistry,
    ) -> AssistantMessage:
        external_requests = _extract_external_requests(response)
        if external_requests:
            tool_calls = [
                _convert_request_to_tool_call(req, registry, "assistant")
                for req in external_requests
            ]
            return AssistantMessage(role="assistant", tool_calls=tool_calls)

        if not response.msgs:
            raise AgentError("ChatAgent returned an empty response.")

        content = response.msg.content
        if content is None:
            raise AgentError("Assistant response did not contain content.")
        return AssistantMessage(
            role="assistant",
            content=content,
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


class CamelTau2User(BaseUser):
    """ChatAgent-powered replacement for τ²'s default user simulator."""

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

    def _install_external_tools(self) -> None:
        existing_tools = list(self._chat_agent.tool_dict.keys())
        if existing_tools:
            self._chat_agent.remove_tools(existing_tools)
        for schema in self._tool_schemas:
            self._chat_agent.add_external_tool(schema)

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> UserState:
        self._chat_agent.reset()
        state = UserState(
            system_messages=[
                SystemMessage(role="system", content=self._system_prompt)
            ],
            messages=message_history or [],
        )
        if message_history:
            self._rehydrate_history(message_history)
        return state

    def _rehydrate_history(self, history: Iterable[Message]) -> None:
        for message in history:
            if isinstance(message, AssistantMessage) and message.content:
                assistant_msg = BaseMessage.make_user_message(
                    role_name="Agent", content=message.content
                )
                self._chat_agent.update_memory(
                    assistant_msg, OpenAIBackendRole.USER
                )
            elif isinstance(message, ToolMessage):
                observation = _format_tool_message(message, self._registry)
                tool_msg = BaseMessage.make_user_message(
                    role_name="Tool",
                    content=observation,
                )
                self._chat_agent.update_memory(
                    tool_msg, OpenAIBackendRole.USER
                )
            elif isinstance(message, UserMessage) and message.content:
                reply = BaseMessage.make_assistant_message(
                    role_name="User", content=message.content
                )
                self._chat_agent.record_message(reply)

    def generate_next_message(
        self,
        message: ValidUserInputMessage,
        state: UserState,
    ) -> tuple[UserMessage, UserState]:
        # Keep state history aligned with τ² expectations
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)

        observation = _flatten_tool_messages(message, self._registry)
        if observation is None:
            prompt = message.content or ""
        else:
            prompt = observation

        response = self._chat_agent.step(prompt)
        user_message = self._response_to_user_message(
            response, self._registry
        )
        state.messages.append(user_message)
        return user_message, state

    def _response_to_user_message(
        self,
        response: ChatAgentResponse,
        registry: ToolCallRegistry,
    ) -> UserMessage:
        external_requests = _extract_external_requests(response)
        if external_requests:
            tool_calls = [
                _convert_request_to_tool_call(req, registry, "user")
                for req in external_requests
            ]
            return UserMessage(role="user", content=None, tool_calls=tool_calls)

        if not response.msgs:
            raise UserError("User ChatAgent returned an empty response.")
        content = response.msg.content
        if content is None:
            raise UserError("User ChatAgent produced no textual reply.")

        return UserMessage(role="user", content=content)

    @classmethod
    def is_stop(cls, message: UserMessage) -> bool:
        if message.is_tool_call() or not message.content:
            return False
        return any(
            token in message.content for token in (STOP, TRANSFER, OUT_OF_SCOPE)
        )

    def set_seed(self, seed: int) -> None:
        backend = getattr(self._chat_agent, "model_backend", None)
        if backend is None:
            return
        config = dict(getattr(backend, "model_config_dict", {}))
        config["seed"] = seed
        backend.model_config_dict = config
