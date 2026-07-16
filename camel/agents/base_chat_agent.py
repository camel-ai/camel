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
"""Minimal append-only chat agent for reproducible training rollouts."""

from __future__ import annotations

import asyncio
import copy
import functools
import json
import random
import time
import uuid
from enum import StrEnum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

from openai import RateLimitError
from pydantic import BaseModel

from camel.agents._types import ModelResponse, ToolCallRequest
from camel.agents._utils import (
    convert_to_function_tool,
    get_info_dict,
    handle_logprobs,
    safe_model_dump,
)
from camel.agents.base import BaseAgent
from camel.logger import get_logger
from camel.memories import (
    AgentMemory,
    BaseContextCreator,
    ChatHistoryMemory,
    ContextRecord,
    MemoryRecord,
)
from camel.messages import BaseMessage, OpenAIMessage
from camel.models import BaseModelBackend, ModelManager, ModelProcessingError
from camel.responses import ChatAgentResponse
from camel.toolkits import FunctionTool, RegisteredAgentToolkit
from camel.types import ChatCompletion, OpenAIBackendRole, RoleType
from camel.types.agents import ToolCallingRecord
from camel.utils import BaseTokenCounter
from camel.utils.agent_context import set_current_agent_id
from camel.utils.tool_result import ToolResult

logger = get_logger(__name__)

_RAW_OPENAI_MESSAGE_KEY = "_base_chat_agent_raw_openai_message"


class _AppendOnlyContextCreator(BaseContextCreator):
    """Return memory records in storage order without filtering or sorting."""

    def __init__(
        self,
        token_limit: int,
        token_counter: Optional[BaseTokenCounter] = None,
    ) -> None:
        """Create exact-order context with optional token counting."""
        self._token_limit = token_limit
        self._token_counter = token_counter

    @property
    def token_counter(self) -> BaseTokenCounter:
        """Return the configured counter or fail when none is available."""
        if self._token_counter is None:
            raise RuntimeError("No local token counter is configured")
        return self._token_counter

    @property
    def token_limit(self) -> int:
        """Return the model context limit associated with this creator."""
        return self._token_limit

    def create_context(
        self, records: List[ContextRecord]
    ) -> Tuple[List[OpenAIMessage], int]:
        """Convert every record to its exact stored OpenAI message."""
        messages: List[OpenAIMessage] = []
        for record in records:
            memory_record = record.memory_record
            meta = memory_record.message.meta_dict or {}
            raw_message = meta.get(_RAW_OPENAI_MESSAGE_KEY)
            if isinstance(raw_message, dict):
                messages.append(copy.deepcopy(raw_message))
            else:
                messages.append(memory_record.to_openai_message())

        num_tokens = (
            self._token_counter.count_tokens_from_messages(messages)
            if self._token_counter is not None and messages
            else 0
        )
        return messages, num_tokens


class TerminationReason(StrEnum):
    """Why a training step ended.

    Values and cause-chain behaviour mirror
    ``strands_env.core.types.TerminationReason`` without introducing a Strands
    runtime dependency into CAMEL.
    """

    NOT_TERMINATED = "not_terminated"
    TASK_COMPLETE = "task_complete"
    MAX_TOKENS_REACHED = "max_tokens_reached"
    CONTEXT_WINDOW_OVERFLOW = "context_window_overflow"
    MAX_TOOL_ITERATIONS_REACHED = "max_tool_iterations_reached"
    MAX_TOOL_CALLS_REACHED = "max_tool_calls_reached"
    MAX_MESSAGES_REACHED = "max_messages_reached"
    RECURSION_DEPTH_EXCEEDED = "recursion_depth_exceeded"
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    UNCLASSIFIED_ERROR = "unclassified_error"

    @staticmethod
    def _cause_chain(error: BaseException):
        """Yield each unique exception through explicit and implicit causes."""
        seen: set[int] = set()
        current: Optional[BaseException] = error
        while current is not None and id(current) not in seen:
            seen.add(id(current))
            yield current
            current = current.__cause__ or current.__context__

    @classmethod
    def from_error(cls, error: Optional[BaseException]) -> "TerminationReason":
        """Classify an exception and its causes into a training termination."""
        if error is None:
            return cls.TASK_COMPLETE

        chain = list(cls._cause_chain(error))
        names = " ".join(type(exc).__name__.lower() for exc in chain)
        if "contextwindow" in names or "contextlength" in names:
            return cls.CONTEXT_WINDOW_OVERFLOW
        if "maxtoken" in names:
            return cls.MAX_TOKENS_REACHED
        if "maxtooliteration" in names:
            return cls.MAX_TOOL_ITERATIONS_REACHED
        if "maxtoolcall" in names:
            return cls.MAX_TOOL_CALLS_REACHED
        if "maxmessage" in names:
            return cls.MAX_MESSAGES_REACHED
        if any(isinstance(exc, RecursionError) for exc in chain):
            return cls.RECURSION_DEPTH_EXCEEDED
        if "timeout" in names:
            return cls.TIMEOUT
        if any(
            marker in names
            for marker in ("connection", "disconnected", "connecterror")
        ):
            return cls.CONNECTION_ERROR
        return cls.UNCLASSIFIED_ERROR


class BaseChatAgent(BaseAgent):
    """An async-only CAMEL agent with raw append-only memory.

    This class deliberately inherits directly from :class:`BaseAgent`. It has
    an ``AgentMemory`` but bypasses score-based context processing, windows,
    pruning, and automatic summarization. Internal CAMEL ``FunctionTool``
    objects and async MCP tools remain supported.
    """

    def __init__(
        self,
        system_message: Optional[Union[BaseMessage, str]] = None,
        model: Optional[Union[BaseModelBackend, ModelManager]] = None,
        memory: Optional[AgentMemory] = None,
        tools: Optional[List[Union[FunctionTool, Callable[..., Any]]]] = None,
        toolkits_to_register_agent: Optional[
            List[RegisteredAgentToolkit]
        ] = None,
        token_limit: Optional[int] = None,
        max_iteration: Optional[int] = None,
        agent_id: Optional[str] = None,
        tool_execution_timeout: Optional[float] = None,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        step_timeout: Optional[float] = None,
    ) -> None:
        """Configure an async agent whose ``AgentMemory`` is never processed.

        Tools are normalized to CAMEL ``FunctionTool`` objects. ``token_limit``
        defaults to the model limit, while tool and whole-step timeouts remain
        optional so training frameworks can choose their own limits.
        """
        if model is None:
            raise ValueError("BaseChatAgent requires a model backend")
        if not isinstance(model, (BaseModelBackend, ModelManager)):
            raise TypeError("model must be a BaseModelBackend or ModelManager")
        self.model_backend = (
            model if isinstance(model, ModelManager) else ModelManager(model)
        )
        if self.model_backend.model_config_dict.get("stream", False):
            raise ValueError(
                "BaseChatAgent only supports non-streaming models"
            )

        self.agent_id = agent_id or str(uuid.uuid4())
        self._original_system_message = (
            BaseMessage.make_system_message(system_message)
            if isinstance(system_message, str)
            else system_message
        )
        self.role_name = (
            getattr(self._original_system_message, "role_name", None)
            or "assistant"
        )
        self.role_type = (
            getattr(self._original_system_message, "role_type", None)
            or RoleType.ASSISTANT
        )

        self._internal_tools: Dict[str, FunctionTool] = {
            tool.get_function_name(): tool
            for tool in [
                convert_to_function_tool(tool) for tool in (tools or [])
            ]
        }
        for toolkit in toolkits_to_register_agent or []:
            toolkit.register_agent(self)

        self._token_limit = (
            token_limit
            if token_limit is not None
            else self.model_backend.token_limit
        )
        try:
            token_counter = self.model_backend.token_counter
        except (NotImplementedError, RuntimeError):
            token_counter = None
        self._context_creator = _AppendOnlyContextCreator(
            token_limit=self._token_limit,
            token_counter=token_counter,
        )
        self._memory = memory or ChatHistoryMemory(
            context_creator=self._context_creator,
            window_size=None,
            agent_id=self.agent_id,
        )
        self._memory.agent_id = self.agent_id
        self.max_iteration = max_iteration
        self.tool_execution_timeout = tool_execution_timeout
        self.retry_attempts = max(1, retry_attempts)
        self.retry_delay = max(0.0, retry_delay)
        self.step_timeout = step_timeout
        self.terminated = False
        self.termination_reason = TerminationReason.NOT_TERMINATED
        self.last_error: Optional[BaseException] = None
        self.meta_info_record: Dict[str, Any] = {}
        self.reset()

    def step(self, *args: Any, **kwargs: Any) -> Any:
        """Reject synchronous use; training rollouts must call ``astep``."""
        raise NotImplementedError("BaseChatAgent is async-only; use astep()")

    def reset(self) -> None:
        """Clear the trajectory and reset all stateful model backends."""
        self.memory.clear()
        if self._original_system_message is not None:
            self._write_openai_message(
                self._original_system_message.to_openai_system_message()
            )
        self.terminated = False
        self.termination_reason = TerminationReason.NOT_TERMINATED
        self.last_error = None
        self.meta_info_record = self._new_meta_info()
        for backend in self.model_backend.models:
            reset = getattr(backend, "reset", None)
            if callable(reset):
                reset()

    @property
    def memory(self) -> AgentMemory:
        """Return the canonical append-only agent memory."""
        return self._memory

    @property
    def message_list(self) -> List[OpenAIMessage]:
        """Return the exact unprocessed messages currently stored in memory."""
        messages, _ = self._context_creator.create_context(
            self.memory.retrieve()
        )
        return messages

    @property
    def chat_history(self) -> List[OpenAIMessage]:
        """Return a defensive view of the raw training trajectory."""
        return self.message_list

    def _write_openai_message(self, message: OpenAIMessage) -> None:
        """Append one exact OpenAI message to ``AgentMemory``."""
        raw_message = copy.deepcopy(dict(message))
        role = str(raw_message.get("role", "assistant"))
        backend_role = {
            "system": OpenAIBackendRole.SYSTEM,
            "developer": OpenAIBackendRole.DEVELOPER,
            "user": OpenAIBackendRole.USER,
            "assistant": OpenAIBackendRole.ASSISTANT,
            "tool": OpenAIBackendRole.TOOL,
        }.get(role, OpenAIBackendRole.ASSISTANT)
        role_type = {
            "system": RoleType.SYSTEM,
            "developer": RoleType.SYSTEM,
            "user": RoleType.USER,
        }.get(role, RoleType.ASSISTANT)
        content = raw_message.get("content")
        stored_message = BaseMessage(
            role_name=role,
            role_type=role_type,
            meta_dict={_RAW_OPENAI_MESSAGE_KEY: raw_message},
            content=content if isinstance(content, str) else "",
            reasoning_content=raw_message.get("reasoning_content"),
        )
        self.memory.write_record(
            MemoryRecord(
                message=stored_message,
                role_at_backend=backend_role,
                timestamp=time.time_ns() / 1_000_000_000,
                agent_id=self.agent_id,
            )
        )

    @property
    def tool_dict(self) -> Dict[str, FunctionTool]:
        """Return registered internal tools by function name."""
        return self._internal_tools

    @staticmethod
    def _new_meta_info() -> Dict[str, Any]:
        """Create zeroed usage, tool, termination, and error metadata."""
        return {
            "iteration_count": 0,
            "termination_reason": TerminationReason.NOT_TERMINATED,
            "max_tool_calls_per_turn": 0,
            "total_tool_calls": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "error_type": None,
            "error_message": None,
        }

    def _get_full_tool_schemas(self) -> List[Dict[str, Any]]:
        """Return OpenAI schemas for every registered internal or MCP tool."""
        return [
            tool.get_openai_tool_schema()
            for tool in self._internal_tools.values()
        ]

    @staticmethod
    def _create_token_usage_tracker() -> Dict[str, int]:
        """Create counters accumulated across all model calls in one step."""
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    @staticmethod
    def _update_token_usage_tracker(
        tracker: Dict[str, int], usage: Dict[str, Any]
    ) -> None:
        """Add one completion's reported token usage into step totals."""
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            tracker[key] += int(usage.get(key) or 0)

    def _set_termination(
        self,
        reason: TerminationReason,
        error: Optional[BaseException] = None,
    ) -> None:
        """Record the final reason and optional exception in training state."""
        self.termination_reason = reason
        self.meta_info_record["termination_reason"] = reason
        self.last_error = error
        if error is not None:
            self.meta_info_record["error_type"] = type(error).__name__
            self.meta_info_record["error_message"] = str(error)

    async def astep(
        self,
        input_message: Union[BaseMessage, str],
        response_format: Optional[Type[BaseModel]] = None,
    ) -> ChatAgentResponse:
        """Append one user turn and run model/tool turns to termination.

        ``step_timeout`` wraps the complete operation, including model retries
        and sequential tool calls.
        """
        set_current_agent_id(self.agent_id)
        self.meta_info_record = self._new_meta_info()
        self.termination_reason = TerminationReason.NOT_TERMINATED
        self.last_error = None
        self.terminated = False

        if isinstance(input_message, str):
            input_message = BaseMessage.make_user_message(
                role_name="User", content=input_message
            )
        self._write_openai_message(input_message.to_openai_user_message())

        task = self._run_loop(response_format)
        try:
            if self.step_timeout is None:
                return await task
            return await asyncio.wait_for(task, timeout=self.step_timeout)
        except BaseException as error:
            if self.termination_reason is TerminationReason.NOT_TERMINATED:
                self._set_termination(
                    TerminationReason.from_error(error), error
                )
            raise

    async def _run_loop(
        self, response_format: Optional[Type[BaseModel]]
    ) -> ChatAgentResponse:
        """Run model and sequential tool turns until the step terminates.

        Each raw assistant response is stored before its requested tools run;
        every tool result is then appended in request order before the next
        model call.
        """
        tool_call_records: List[ToolCallingRecord] = []
        usage = self._create_token_usage_tracker()
        response: Optional[ModelResponse] = None
        last_prompt_tokens = 0

        while True:
            response = await self._aget_model_response(
                self.message_list,
                response_format=response_format,
                tool_schemas=self._get_full_tool_schemas(),
            )
            self.meta_info_record["iteration_count"] += 1

            raw_assistant = response.response.choices[0].message.model_dump(
                exclude_none=True
            )
            raw_assistant["role"] = "assistant"
            self._write_openai_message(raw_assistant)
            self._update_token_usage_tracker(usage, response.usage_dict)
            for key in usage:
                self.meta_info_record[key] = usage[key]
            last_prompt_tokens = int(
                response.usage_dict.get("prompt_tokens") or 0
            )

            if (
                self._token_limit is not None
                and last_prompt_tokens > self._token_limit
            ):
                self.terminated = True
                self._set_termination(
                    TerminationReason.CONTEXT_WINDOW_OVERFLOW
                )
                break

            requests = list(response.tool_call_requests or [])
            if not requests:
                if "length" in response.finish_reasons:
                    self.terminated = True
                    self._set_termination(TerminationReason.MAX_TOKENS_REACHED)
                else:
                    self._set_termination(TerminationReason.TASK_COMPLETE)
                break

            self.meta_info_record["max_tool_calls_per_turn"] = max(
                self.meta_info_record["max_tool_calls_per_turn"], len(requests)
            )
            records = await self._aexecute_tools(requests)
            for record in records:
                tool_call_records.append(record)
                self._write_openai_message(
                    {
                        "role": "tool",
                        "tool_call_id": record.tool_call_id,
                        "content": self._tool_result_content(record.result),
                    }
                )
            self.meta_info_record["total_tool_calls"] = len(tool_call_records)

            if (
                self.max_iteration is not None
                and self.meta_info_record["iteration_count"]
                >= self.max_iteration
            ):
                self.terminated = True
                self._set_termination(
                    TerminationReason.MAX_TOOL_ITERATIONS_REACHED
                )
                break

        assert response is not None
        info = get_info_dict(
            response.response_id,
            usage,
            response.finish_reasons,
            last_prompt_tokens,
            tool_call_records,
        )
        info["training"] = copy.deepcopy(self.meta_info_record)
        return ChatAgentResponse(
            msgs=response.output_messages,
            terminated=self.terminated,
            info=info,
        )

    async def _aget_model_response(
        self,
        messages: List[OpenAIMessage],
        response_format: Optional[Type[BaseModel]],
        tool_schemas: List[Dict[str, Any]],
    ) -> ModelResponse:
        """Call the backend with rate-limit retries and parse one response."""
        last_error: Optional[BaseException] = None
        for attempt in range(self.retry_attempts):
            try:
                raw = await self.model_backend.arun(
                    messages, response_format, tool_schemas or None
                )
                if raw is not None:
                    break
            except RateLimitError as error:
                last_error = error
                if attempt == self.retry_attempts - 1:
                    continue
                delay = random.uniform(
                    0, min(self.retry_delay * (2**attempt), 60.0)
                )
                await asyncio.sleep(delay)
        else:
            raise ModelProcessingError(
                "Unable to process messages: "
                f"{last_error or 'empty model response'}"
            )

        if not isinstance(raw, ChatCompletion):
            raise TypeError(
                f"Expected ChatCompletion, got {type(raw).__name__}"
            )
        return self._parse_model_response(raw)

    def _parse_model_response(self, response: ChatCompletion) -> ModelResponse:
        """Convert a completion into messages and ordered tool calls."""
        output_messages: List[BaseMessage] = []
        for choice in response.choices:
            message = choice.message
            if not (message.content or message.tool_calls):
                continue
            meta: Dict[str, Any] = {}
            if logprobs := handle_logprobs(choice):
                meta["logprobs_info"] = logprobs
            output_messages.append(
                BaseMessage(
                    role_name=self.role_name,
                    role_type=self.role_type,
                    meta_dict=meta,
                    content=message.content or "",
                    parsed=getattr(message, "parsed", None),
                    reasoning_content=getattr(
                        message, "reasoning_content", None
                    ),
                )
            )

        requests: List[ToolCallRequest] = []
        for tool_call in response.choices[0].message.tool_calls or []:
            requests.append(
                ToolCallRequest(
                    tool_name=tool_call.function.name,
                    args=json.loads(tool_call.function.arguments),
                    tool_call_id=tool_call.id,
                    extra_content=getattr(tool_call, "extra_content", None),
                )
            )
        usage = safe_model_dump(response.usage) if response.usage else {}
        return ModelResponse(
            response=response,
            tool_call_requests=requests or None,
            output_messages=output_messages,
            finish_reasons=[
                str(choice.finish_reason) for choice in response.choices
            ],
            usage_dict=usage,
            response_id=response.id or "",
        )

    async def _aexecute_tools(
        self, requests: List[ToolCallRequest]
    ) -> List[ToolCallingRecord]:
        """Await each tool call in model-request order."""
        return [await self._aexecute_tool(request) for request in requests]

    async def _aexecute_tool(
        self, request: ToolCallRequest
    ) -> ToolCallingRecord:
        """Execute CAMEL functions and MCP tools without memory writes."""
        tool = self._internal_tools.get(request.tool_name)
        if tool is None:
            result: Any = (
                "Tool execution failed: Tool "
                f"'{request.tool_name}' not found in registered tools"
            )
        else:
            try:
                call = self._invoke_tool(tool, request.args)
                result = (
                    await asyncio.wait_for(
                        call, timeout=self.tool_execution_timeout
                    )
                    if self.tool_execution_timeout is not None
                    else await call
                )
            except Exception as error:
                result = (
                    f"Tool execution failed: Error executing async tool "
                    f"'{request.tool_name}': {error}"
                )
                logger.warning(result)

        images = result.images if isinstance(result, ToolResult) else None
        return ToolCallingRecord(
            tool_name=request.tool_name,
            args=request.args,
            result=result,
            tool_call_id=request.tool_call_id,
            images=images,
        )

    @staticmethod
    async def _invoke_tool(tool: FunctionTool, args: Dict[str, Any]) -> Any:
        """Invoke a tool without blocking the agent event loop.

        MCP ``async_call`` is preferred, followed by coroutine functions;
        ordinary synchronous tools run in the loop's executor.
        """
        if hasattr(tool, "func") and hasattr(tool.func, "async_call"):
            return await tool.func.async_call(**args)
        if hasattr(tool, "async_call") and callable(tool.async_call):
            return await tool.async_call(**args)
        if hasattr(tool, "func") and asyncio.iscoroutinefunction(tool.func):
            return await tool.func(**args)
        if asyncio.iscoroutinefunction(tool):
            return await tool(**args)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, functools.partial(tool, **args)
        )

    @staticmethod
    def _tool_result_content(result: Any) -> str:
        """Serialize a tool result for the OpenAI ``tool`` memory message."""
        return result.text if isinstance(result, ToolResult) else str(result)


__all__ = ["BaseChatAgent", "TerminationReason"]
