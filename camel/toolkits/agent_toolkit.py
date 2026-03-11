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

import concurrent.futures
import threading
import time
import types
import uuid
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Union,
)

from camel.logger import get_logger
from camel.toolkits.base import BaseToolkit, RegisteredAgentToolkit
from camel.toolkits.function_tool import FunctionTool

if TYPE_CHECKING:
    from camel.agents import ChatAgent
    from camel.responses import ChatAgentResponse

logger = get_logger(__name__)


@dataclass
class _AgentSession:
    agent: "ChatAgent"
    subagent_type: str
    description: str
    turns: int = 0
    active_task_id: Optional[str] = None


@dataclass
class _AgentTask:
    task_id: str
    agent_id: str
    prompt: str
    future: concurrent.futures.Future["ChatAgentResponse"]
    stop_event: threading.Event
    status: str = "running"
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class AgentToolkit(BaseToolkit, RegisteredAgentToolkit):
    r"""Toolkit for delegating a task to a persistent specialized sub-agent.

    This toolkit exposes tools for running a blocking delegated task and
    stopping a running sub-agent task.
    """

    _TYPE_INSTRUCTIONS = types.MappingProxyType(
        {
            "general-purpose": (
                "Complete the delegated task autonomously and return a "
                "direct, useful result."
            ),
            "research": (
                "Investigate the task carefully, synthesize findings, and "
                "note important uncertainties."
            ),
            "analysis": (
                "Break the problem down, compare options when relevant, and "
                "return the strongest conclusion."
            ),
            "coding": (
                "Focus on implementation details, correctness, and concrete "
                "engineering tradeoffs."
            ),
            "writing": (
                "Produce clear, polished writing that matches the requested "
                "tone and constraints."
            ),
        }
    )

    def __init__(
        self,
        default_tools: Optional[List[Union[FunctionTool, Callable]]] = None,
        share_parent_tools: bool = False,
        timeout: Optional[float] = None,
    ) -> None:
        r"""Initialize the AgentToolkit.

        Args:
            default_tools (Optional[List[Union[FunctionTool, Callable]]]):
                Tools made available to spawned sub-agents when parent tools
                are unavailable or disabled. This toolkit must be registered
                to a parent ChatAgent before use. (default: :obj:`None`)
            share_parent_tools (bool): Whether to clone tools from the parent
                ChatAgent when this toolkit is registered via
                :obj:`toolkits_to_register_agent`. (default: :obj:`False`)
            timeout (Optional[float]): Maximum execution time for toolkit
                calls. (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        RegisteredAgentToolkit.__init__(self)
        self.default_tools = list(default_tools or [])
        self.share_parent_tools = share_parent_tools
        self._sessions: Dict[str, _AgentSession] = {}
        self._tasks: Dict[str, _AgentTask] = {}
        self._lock = threading.RLock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    def _build_system_message(
        self,
        subagent_type: str,
        description: str,
    ) -> str:
        specialization = self._TYPE_INSTRUCTIONS.get(
            subagent_type.lower(),
            (
                "Approach the delegated task as a focused specialist and "
                "return the most useful result you can."
            ),
        )
        return (
            "You are a specialized sub-agent working on behalf of another "
            "agent.\n"
            f"Sub-agent type: {subagent_type}\n"
            f"Task description: {description}\n"
            f"Operating guidance: {specialization}\n"
        )

    def _error_result(
        self, error_message: str, **payload: Any
    ) -> Dict[str, Any]:
        logger.warning(error_message)
        result: Dict[str, Any] = {
            "status": "failed",
            "error": f"Error: {error_message}",
        }
        result.update(payload)
        return result

    def _require_parent_agent(self) -> Optional["ChatAgent"]:
        return self._agent

    def _resolve_child_tools(
        self,
        parent: Optional["ChatAgent"],
        share_parent_tools: Optional[bool] = None,
        tool_names: Optional[List[str]] = None,
    ) -> Tuple[
        Optional[List[Union[FunctionTool, Callable]]],
        Optional[List[RegisteredAgentToolkit]],
    ]:
        if parent is None:
            return None, None
        names = [name for name in (tool_names or []) if name]
        share = (
            self.share_parent_tools
            if share_parent_tools is None
            else share_parent_tools
        )
        if names:
            cloned_tools, toolkits_to_register = parent._clone_tools()
            tool_map = {
                tool.get_function_name(): tool for tool in cloned_tools
            }
            missing = [name for name in names if name not in tool_map]
            if missing:
                raise ValueError(
                    "Unknown parent tools requested for sub-agent: "
                    + ", ".join(sorted(missing))
                )
            return [tool_map[name] for name in names], toolkits_to_register
        if share:
            try:
                cloned_tools, toolkits_to_register = parent._clone_tools()
                return (
                    cloned_tools,  # type: ignore[return-value]
                    toolkits_to_register,
                )
            except Exception as exc:
                logger.warning(
                    "Failed to clone parent agent tools for AgentToolkit: "
                    f"{exc}"
                )
        if self.default_tools:
            return list(self.default_tools), None
        return None, None

    def _create_subagent(
        self,
        subagent_type: str,
        description: str,
        share_parent_tools: Optional[bool] = None,
        tool_names: Optional[List[str]] = None,
    ) -> Optional["ChatAgent"]:
        from camel.agents import ChatAgent

        parent = self._require_parent_agent()
        if parent is None:
            return None
        tools, toolkits_to_register = self._resolve_child_tools(
            parent=parent,
            share_parent_tools=share_parent_tools,
            tool_names=tool_names,
        )

        return ChatAgent(
            system_message=self._build_system_message(
                subagent_type=subagent_type,
                description=description,
            ),
            model=parent.model_backend.models,
            message_window_size=getattr(parent.memory, "window_size", None),
            token_limit=getattr(
                parent.memory.get_context_creator(),
                "token_limit",
                None,
            ),
            output_language=getattr(parent, "_output_language", None),
            tools=tools,
            toolkits_to_register_agent=toolkits_to_register,
            response_terminators=parent.response_terminators,
            scheduling_strategy=(
                parent.model_backend.scheduling_strategy.__name__
            ),
            max_iteration=parent.max_iteration,
            tool_execution_timeout=parent.tool_execution_timeout,
            prune_tool_calls_from_memory=(parent.prune_tool_calls_from_memory),
            on_request_usage=parent.on_request_usage,
            stream_accumulate=parent.stream_accumulate,
        )

    def _run_agent_step(
        self,
        agent: "ChatAgent",
        prompt: str,
    ) -> "ChatAgentResponse":
        return agent.step(prompt)

    def _complete_task(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if (
                task is None
                or not task.future.done()
                or task.status != "running"
            ):
                return

        try:
            response = task.future.result()
        except concurrent.futures.CancelledError:
            status = "stopped"
            result = None
            error = None
        except Exception as exc:
            status = "stopped" if task.stop_event.is_set() else "failed"
            result = None
            error = str(exc)
        else:
            status = "stopped" if task.stop_event.is_set() else "completed"
            result = response.msgs[0].content if response.msgs else ""
            error = None

        with self._lock:
            current = self._tasks.get(task_id)
            if current is None:
                return
            current.status = status
            current.result = result
            current.error = error
            current.completed_at = time.time()

            session = self._sessions.get(current.agent_id)
            if session is not None and session.active_task_id == task_id:
                session.active_task_id = None
                if status in {"completed", "stopped"}:
                    session.turns += 1

    _MAX_FINISHED_TASKS = 64

    def _submit_agent_task(
        self,
        agent_id: str,
        agent: "ChatAgent",
        prompt: str,
    ) -> _AgentTask:
        """Submit a new task. Caller MUST hold ``self._lock``."""
        if len(self._tasks) >= self._MAX_FINISHED_TASKS:
            self._purge_completed_tasks()
        stop_event = threading.Event()
        agent.stop_event = stop_event
        task_id = str(uuid.uuid4())
        future = self._executor.submit(self._run_agent_step, agent, prompt)
        task = _AgentTask(
            task_id=task_id,
            agent_id=agent_id,
            prompt=prompt,
            future=future,
            stop_event=stop_event,
        )

        self._tasks[task_id] = task
        self._sessions[agent_id].active_task_id = task_id

        future.add_done_callback(lambda _future: self._complete_task(task_id))
        return task

    def _get_task(self, task_id: str) -> Optional[_AgentTask]:
        self._complete_task(task_id)
        with self._lock:
            task = self._tasks.get(task_id)
        return task

    def _validate_prompt(
        self,
        prompt: Optional[str],
        agent_id: Optional[str],
        description: str,
        subagent_type: str,
    ) -> Optional[Dict[str, Any]]:
        if prompt and prompt.strip():
            return None
        return self._error_result(
            "prompt cannot be empty",
            agent_id=agent_id,
            task_id=None,
            created=False,
            subagent_type=subagent_type,
            description=description,
        )

    def _get_or_create_session(
        self,
        prompt: str,
        description: str,
        subagent_type: str,
        agent_id: Optional[str],
        share_parent_tools: Optional[bool],
        tool_names: Optional[List[str]],
    ) -> Tuple[Optional[_AgentSession], Optional[bool], Optional[Dict[str, Any]]]:
        err = self._validate_prompt(
            prompt=prompt,
            agent_id=agent_id,
            description=description,
            subagent_type=subagent_type,
        )
        if err is not None:
            return None, None, err
        if self._require_parent_agent() is None:
            return None, None, self._error_result(
                "AgentToolkit must be registered to a parent ChatAgent via "
                "'toolkits_to_register_agent' before it can spawn "
                "sub-agents.",
                agent_id=agent_id,
                task_id=None,
                created=False,
                subagent_type=subagent_type,
                description=description,
            )

        created = False
        if agent_id is None:
            try:
                agent = self._create_subagent(
                    subagent_type=subagent_type,
                    description=description,
                    share_parent_tools=share_parent_tools,
                    tool_names=tool_names,
                )
            except Exception as exc:
                return None, None, self._error_result(
                    f"Failed to create sub-agent: {exc}",
                    agent_id=None,
                    task_id=None,
                    created=False,
                    subagent_type=subagent_type,
                    description=description,
                )
            if agent is None:
                return None, None, self._error_result(
                    "AgentToolkit must be registered to a parent ChatAgent "
                    "via 'toolkits_to_register_agent' before it can spawn "
                    "sub-agents.",
                    agent_id=None,
                    task_id=None,
                    created=False,
                    subagent_type=subagent_type,
                    description=description,
                )
            agent_id = agent.agent_id
            session = _AgentSession(
                agent=agent,
                subagent_type=subagent_type,
                description=description,
            )
            with self._lock:
                self._sessions[agent_id] = session
            created = True
            return session, created, None

        with self._lock:
            session = self._sessions.get(agent_id)
        if session is None:
            return None, None, self._error_result(
                f"No sub-agent session found for agent_id '{agent_id}'.",
                agent_id=agent_id,
                task_id=None,
                created=False,
                subagent_type=subagent_type,
                description=description,
            )
        return session, created, None

    def _start_task(
        self,
        session: _AgentSession,
        prompt: str,
        created: bool,
    ) -> Tuple[Optional[_AgentTask], Optional[Dict[str, Any]]]:
        with self._lock:
            active_task_id = session.active_task_id
            active_task = (
                self._tasks.get(active_task_id) if active_task_id else None
            )
            if active_task is not None and active_task_id is not None:
                self._complete_task(active_task_id)
                active_task = self._tasks.get(active_task_id)
                if active_task is not None and active_task.status == "running":
                    return None, self._error_result(
                        f"Sub-agent '{session.agent.agent_id}' already has a "
                        f"running task ('{active_task_id}'). Stop it before "
                        f"starting another task.",
                        agent_id=session.agent.agent_id,
                        task_id=active_task_id,
                        created=created,
                        subagent_type=session.subagent_type,
                        description=session.description,
                    )

            try:
                task = self._submit_agent_task(
                    agent_id=session.agent.agent_id,
                    agent=session.agent,
                    prompt=prompt,
                )
            except Exception as exc:
                return None, self._error_result(
                    f"Failed to start sub-agent task: {exc}",
                    agent_id=session.agent.agent_id,
                    task_id=None,
                    created=created,
                    subagent_type=session.subagent_type,
                    description=session.description,
                )
        self._complete_task(task.task_id)
        return task, None

    def agent_run_subagent(
        self,
        prompt: str,
        description: str = "Specialized sub-agent task",
        subagent_type: str = "general-purpose",
        agent_id: Optional[str] = None,
        tool_names: Optional[List[str]] = None,
        share_parent_tools: Optional[bool] = None,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Run a specialized sub-agent and wait for its final result.

        Use this tool when the current task is complex enough to benefit from
        a focused child agent with its own conversation state. If
        :obj:`agent_id` is omitted, a new sub-agent session is created with a
        fresh ChatAgent instance and its own empty conversation state. If
        :obj:`agent_id` is provided, the matching sub-agent instance is reused
        rather than recreated. This means the sub-agent keeps its existing
        memory and any state accumulated from previous turns in that session.

        Args:
            prompt (str): The task instructions to send to the sub-agent for
                this turn.
            description (str): Short description of the sub-task or role for
                the sub-agent. This is primarily used when creating a new
                session. (default: :obj:`"Specialized sub-agent task"`)
            subagent_type (str): Specialization label for the spawned
                sub-agent, such as :obj:`general-purpose`, :obj:`research`,
                :obj:`analysis`, :obj:`coding`, or :obj:`writing`.
                (default: :obj:`"general-purpose"`)
            agent_id (Optional[str]): Existing sub-agent session ID to resume.
                When provided, the stored sub-agent instance is reused, so it
                continues with the same memory / conversation state from
                earlier turns. In this case, :obj:`description` and
                :obj:`subagent_type` are ignored. The spawned sub-agent always
                uses the calling parent agent's model. (default: :obj:`None`)

            tool_names (Optional[List[str]]): Specific parent tool names to
                clone into a new sub-agent. If omitted, tool inheritance is
                controlled by :obj:`share_parent_tools` and toolkit defaults.
            share_parent_tools (Optional[bool]): Per-call override for whether
                to inherit the parent agent's tools. (default: :obj:`None`)
            timeout (Optional[float]): Maximum wait time in seconds for the
                sub-agent to finish. If the timeout is reached, the task keeps
                running and the current status is returned.

        Returns:
            Dict[str, Any]: Final result for completed tasks, or the current
                running status when a timeout is reached.
        """
        session, created, err = self._get_or_create_session(
            prompt=prompt,
            description=description,
            subagent_type=subagent_type,
            agent_id=agent_id,
            share_parent_tools=share_parent_tools,
            tool_names=tool_names,
        )
        if err is not None or session is None or created is None:
            return err or self._error_result("Failed to create sub-agent.")
        task, err = self._start_task(
            session=session,
            prompt=prompt,
            created=created,
        )
        if err is not None or task is None:
            return err or self._error_result("Failed to start sub-agent task.")
        if not task.future.done():
            try:
                task.future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                pass
            except Exception:
                pass
        current_task = self._get_task(task.task_id)
        if current_task is None:
            return self._error_result(
                f"No sub-agent task found for task_id '{task.task_id}'.",
                task_id=task.task_id,
                agent_id=session.agent.agent_id,
                created=created,
                subagent_type=session.subagent_type,
                description=session.description,
            )
        return {
            "agent_id": session.agent.agent_id,
            "task_id": current_task.task_id,
            "created": created,
            "subagent_type": session.subagent_type,
            "description": session.description,
            "status": current_task.status,
            "result": current_task.result,
            "error": current_task.error,
        }

    def agent_stop_task(self, task_id: str) -> Dict[str, Any]:
        r"""Request cancellation of a running sub-agent task.

        Args:
            task_id (str): Sub-agent task ID returned by
                :obj:`agent_run_subagent`.

        Returns:
            Dict[str, Any]: Stop request status and the latest known task
                state.
        """
        task = self._get_task(task_id)
        if task is None:
            return self._error_result(
                f"No sub-agent task found for task_id '{task_id}'.",
                task_id=task_id,
                agent_id=None,
                message=None,
            )
        if task.status != "running":
            return {
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "status": task.status,
                "message": "Task is not running.",
            }

        try:
            task.stop_event.set()
            task.future.cancel()
            self._complete_task(task_id)
            refreshed = self._get_task(task_id)
        except Exception as exc:
            return self._error_result(
                f"Failed to stop task '{task_id}': {exc}",
                task_id=task.task_id,
                agent_id=task.agent_id,
                message=None,
            )
        if refreshed is None:
            return self._error_result(
                f"No sub-agent task found for task_id '{task_id}'.",
                task_id=task_id,
                agent_id=task.agent_id,
                message=None,
            )
        reported_status = (
            "stopping" if refreshed.status == "running" else refreshed.status
        )

        return {
            "task_id": refreshed.task_id,
            "agent_id": refreshed.agent_id,
            "status": reported_status,
            "message": "Stop requested.",
        }

    def clone_for_new_session(
        self,
        new_session_id: Optional[str] = None,
    ) -> "AgentToolkit":
        r"""Create a fresh AgentToolkit without carrying over sub-agent state.

        Args:
            new_session_id (Optional[str]): Unused compatibility parameter for
                ChatAgent toolkit cloning. (default: :obj:`None`)

        Returns:
            AgentToolkit: A new toolkit instance with the same configuration
                and no active sub-agent sessions.
        """
        del new_session_id
        return AgentToolkit(
            default_tools=list(self.default_tools),
            share_parent_tools=self.share_parent_tools,
            timeout=self.timeout,
        )

    def _purge_completed_tasks(self) -> None:
        """Remove finished tasks to prevent unbounded memory growth."""
        with self._lock:
            finished = [
                (tid, t)
                for tid, t in self._tasks.items()
                if t.status in {"completed", "failed", "stopped"}
            ]
            excess = len(self._tasks) - self._MAX_FINISHED_TASKS + 1
            if excess <= 0:
                return
            finished.sort(
                key=lambda item: (
                    item[1].completed_at or item[1].created_at,
                    item[1].created_at,
                )
            )
            for tid, _ in finished[:excess]:
                del self._tasks[tid]

    def cleanup(self) -> None:
        with self._lock:
            tasks = list(self._tasks.values())
        for task in tasks:
            if task.status == "running":
                task.stop_event.set()
                task.future.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def __del__(self) -> None:
        try:
            self.cleanup()
        except Exception:
            pass

    def get_tools(self) -> List[FunctionTool]:
        r"""Return the tool list for this toolkit."""
        return [
            FunctionTool(self.agent_run_subagent),
            FunctionTool(self.agent_stop_task),
        ]
