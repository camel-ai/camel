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

    This toolkit exposes tools for either waiting on a delegated task directly
    or starting one and checking its result later.

    **Sub-agent tool inheritance policy**

    Sub-agents spawned by :meth:`agent_run_subagent` receive **cloned
    tools** from the parent agent.  However, because ``AgentToolkit``
    inherits from :class:`RegisteredAgentToolkit`, the sub-agent's
    ``step()`` method detects that it is being called from inside a
    registered toolkit (via stack inspection in
    :meth:`~camel.agents.ChatAgent._is_called_from_registered_toolkit`)
    and passes an **empty tool schema list** to the model.  This prevents
    the sub-agent from invoking tools, which in turn prevents infinite
    recursion (a sub-agent calling a sub-agent calling a sub-agent…).

    The **effective default** is therefore:

    * Sub-agents *have* tools in their internal toolbelt (cloned from
      the parent).
    * Sub-agents *cannot use* those tools during ``step()`` — the model
      never sees the tool schemas.

    This behavior is intentional and backward-compatible.  The
    ``child_tool_policy``, ``allowed_tool_names``, and
    ``excluded_tool_names`` constructor parameters make the policy
    **explicit and configurable**: they control which tools are *cloned*
    into the sub-agent's toolbelt (useful for memory/cost control and
    for future use if the recursive guard is selectively relaxed).
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
        timeout: Optional[float] = None,
        child_tool_policy: Optional[str] = "none",
        allowed_tool_names: Optional[List[str]] = None,
        excluded_tool_names: Optional[List[str]] = None,
    ) -> None:
        r"""Initialize the AgentToolkit.

        Sub-agents created by this toolkit inherit cloned tools from the
        parent agent via :meth:`_resolve_child_tools`.  However, when a
        sub-agent's :meth:`~camel.agents.ChatAgent.step` is invoked from
        inside a :class:`RegisteredAgentToolkit` (which ``AgentToolkit``
        is), :meth:`~camel.agents.ChatAgent._is_called_from_registered_toolkit`
        returns ``True`` and the model is given an **empty** tool list to
        prevent recursive agent-tool calls.  Consequently, the **effective
        default behaviour** is that sub-agents run **without usable tools**
        even though cloned tools are present in their toolbelt.

        This is intentional — it avoids infinite recursion where a
        sub-agent could spawn further sub-agents — but it was previously
        undocumented.  The parameters below make the policy explicit and
        allow developers to opt-in to a safe, filtered subset of parent
        tools for sub-agents.

        Args:
            timeout (Optional[float]): Maximum execution time for toolkit
                calls. (default: :obj:`None`)
            child_tool_policy (Optional[str]): Controls which parent tools
                are **cloned into** sub-agents.  Does **not** override the
                recursive-call guard in
                :meth:`~camel.agents.ChatAgent._is_called_from_registered_toolkit`.

                - ``"none"`` (default): All parent tools are cloned into
                  the sub-agent's toolbelt.  They will appear in the
                  toolbelt but, because the sub-agent's ``step()`` is
                  called from within a ``RegisteredAgentToolkit``, the
                  model receives an empty tool list and **cannot invoke
                  any tools**.  This is the current, backward-compatible
                  behaviour.
                - ``"filtered"``: Only tools whose names appear in
                  ``allowed_tool_names`` (and are not in
                  ``excluded_tool_names``) are cloned into the sub-agent.
                  This is useful when you want to limit which tools are
                  *available* to the sub-agent's toolbelt, e.g. for
                  memory or cost reasons, even though the recursive guard
                  still prevents direct tool calls during ``step()``.
                - ``"all"``: Explicitly document that all parent tools are
                  cloned.  Functionally identical to ``"none"`` but makes
                  the intent explicit in user code.

                (default: :obj:`"none"`)
            allowed_tool_names (Optional[List[str]]): Whitelist of tool
                names to clone into sub-agents.  Only effective when
                ``child_tool_policy="filtered"``.  If :obj:`None`, no
                whitelist filtering is applied.  Tool names are matched
                against the function name of each tool (i.e., the
                ``openai_function`` name).
                (default: :obj:`None`)
            excluded_tool_names (Optional[List[str]]): Blacklist of tool
                names to exclude from sub-agents.  Applied **after** the
                whitelist.  Effective when
                ``child_tool_policy="filtered"`` or ``"all"``.
                (default: :obj:`None`)
        """
        super().__init__(timeout=timeout)
        RegisteredAgentToolkit.__init__(self)
        self._sessions: Dict[str, _AgentSession] = {}
        self._tasks: Dict[str, _AgentTask] = {}
        self._lock = threading.RLock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

        if child_tool_policy not in ("none", "filtered", "all"):
            raise ValueError(
                f"child_tool_policy must be 'none', 'filtered', or 'all', "
                f"got '{child_tool_policy}'"
            )
        if (
            child_tool_policy == "filtered"
            and allowed_tool_names is None
        ):
            logger.warning(
                "child_tool_policy='filtered' but allowed_tool_names is "
                "None; sub-agents will receive only non-function tools."
            )

        self._child_tool_policy = child_tool_policy
        self._allowed_tool_names = (
            set(allowed_tool_names) if allowed_tool_names is not None else None
        )
        self._excluded_tool_names = (
            set(excluded_tool_names) if excluded_tool_names else set()
        )

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
    ) -> Tuple[
        Optional[List[Union[FunctionTool, Callable]]],
        Optional[List[RegisteredAgentToolkit]],
    ]:
        r"""Resolve which tools to clone from the parent agent for sub-agents.

        The set of tools returned depends on ``self._child_tool_policy``:

        - ``"none"`` or ``"all"``: All parent tools are cloned
          (backward-compatible default).
        - ``"filtered"``: Only tools whose openai_function name is in
          ``self._allowed_tool_names`` (if set) and not in
          ``self._excluded_tool_names`` are included.

        .. note::
            Regardless of which tools are cloned, the recursive-call guard
            in :meth:`~camel.agents.ChatAgent._is_called_from_registered_toolkit`
            prevents the sub-agent from actually *invoking* tools during
            ``step()``.  The filtering here controls which tools appear in
            the sub-agent's toolbelt for potential future use (e.g. if the
            guard is relaxed) and for memory/cost control.

        Args:
            parent (Optional[ChatAgent]): The parent agent to clone tools
                from.

        Returns:
            Tuple containing:
            - List of tools/functions to pass to the sub-agent (or None).
            - List of RegisteredAgentToolkit instances that need
              registration (or None).
        """
        if parent is None:
            return None, None
        cloned_tools, toolkits_to_register = parent._clone_tools()

        if self._child_tool_policy in ("none", "all"):
            # Exclude blacklisted tools even in "all" mode
            if self._excluded_tool_names:
                cloned_tools = [
                    t for t in cloned_tools
                    if self._get_tool_name(t) not in self._excluded_tool_names
                ]
            return list(cloned_tools), toolkits_to_register

        # filtered mode
        filtered_tools = []
        for tool in cloned_tools:
            name = self._get_tool_name(tool)
            if name is None:
                # Non-function tools pass through in filtered mode
                # if no whitelist is set
                if self._allowed_tool_names is None:
                    filtered_tools.append(tool)
                continue
            # Apply whitelist
            if self._allowed_tool_names is not None and name not in self._allowed_tool_names:
                continue
            # Apply blacklist
            if name in self._excluded_tool_names:
                continue
            filtered_tools.append(tool)

        return filtered_tools, toolkits_to_register

    def _get_tool_name(self, tool: Union[FunctionTool, Callable]) -> Optional[str]:
        r"""Extract the function name from a tool.

        Args:
            tool: A FunctionTool or callable.

        Returns:
            The function name, or None if it cannot be determined.
        """
        if isinstance(tool, FunctionTool):
            return tool.func.__name__
        if callable(tool):
            return getattr(tool, '__name__', None)
        return None

    def _create_subagent(
        self,
        subagent_type: str,
        description: str,
    ) -> Optional["ChatAgent"]:
        from camel.agents import ChatAgent

        parent = self._require_parent_agent()
        if parent is None:
            return None
        tools, toolkits_to_register = self._resolve_child_tools(parent=parent)

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
            if current is None or current.status != "running":
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
        finished_count = sum(
            1
            for t in self._tasks.values()
            if t.status in {"completed", "failed", "stopped"}
        )
        if finished_count >= self._MAX_FINISHED_TASKS:
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

    def agent_run_subagent(
        self,
        prompt: str,
        description: str = "Specialized sub-agent task",
        subagent_type: str = "general-purpose",
        agent_id: Optional[str] = None,
        wait: bool = True,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Run a specialized sub-agent, optionally waiting for completion.

        Use this tool when the current task is complex enough to benefit from
        a focused child agent with its own conversation state. If
        :obj:`agent_id` is omitted, a new sub-agent session is created with a
        fresh ChatAgent instance and its own empty conversation state. If
        :obj:`agent_id` is provided, the matching sub-agent instance is reused
        rather than recreated. This means the sub-agent keeps its existing
        memory and any state accumulated from previous turns in that session.

        Prefer :obj:`wait=True` when the parent agent needs the sub-agent
        result before it can continue. Use :obj:`wait=False` only when the
        parent agent intentionally wants to do other work first and check the
        task later with :obj:`agent_get_task_output`.

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

            wait (bool): Whether to wait for the sub-agent to finish before
                returning. Set to :obj:`False` to start the task and check it
                later with :obj:`agent_get_task_output`.
                (default: :obj:`True`)
            timeout (Optional[float]): Maximum wait time in seconds for the
                sub-agent to finish when :obj:`wait` is True. If the timeout is
                reached, the task keeps running and the current status is
                returned.

        Returns:
            Dict[str, Any]: Final result for completed tasks, or current task
                metadata if still running.
        """
        if self._require_parent_agent() is None:
            return self._error_result(
                "AgentToolkit must be registered to a parent ChatAgent via "
                "'toolkits_to_register_agent' before it can spawn "
                "sub-agents.",
                agent_id=agent_id,
                task_id=None,
                created=False,
                subagent_type=subagent_type,
                description=description,
            )
        if not prompt or not prompt.strip():
            return self._error_result(
                "prompt cannot be empty",
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
                )
            except Exception as exc:
                return self._error_result(
                    f"Failed to create sub-agent: {exc}",
                    agent_id=None,
                    task_id=None,
                    created=False,
                    subagent_type=subagent_type,
                    description=description,
                )
            if agent is None:
                return self._error_result(
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
        else:
            with self._lock:
                existing_session = self._sessions.get(agent_id)
            if existing_session is None:
                return self._error_result(
                    f"No sub-agent session found for agent_id '{agent_id}'.",
                    agent_id=agent_id,
                    task_id=None,
                    created=False,
                    subagent_type=subagent_type,
                    description=description,
                )
            session = existing_session
            agent = session.agent

        with self._lock:
            active_task_id = self._sessions[agent_id].active_task_id
            active_task = (
                self._tasks.get(active_task_id) if active_task_id else None
            )
            if active_task is not None and active_task_id is not None:
                self._complete_task(active_task_id)
                active_task = self._tasks.get(active_task_id)
                if active_task is not None and active_task.status == "running":
                    return self._error_result(
                        f"Sub-agent '{agent_id}' already has a running task "
                        f"('{active_task_id}'). Query it or stop it before "
                        f"starting another task.",
                        agent_id=agent_id,
                        task_id=active_task_id,
                        created=False,
                        subagent_type=session.subagent_type,
                        description=session.description,
                    )

            try:
                task = self._submit_agent_task(
                    agent_id=agent_id,
                    agent=agent,
                    prompt=prompt,
                )
            except Exception as exc:
                return self._error_result(
                    f"Failed to start sub-agent task: {exc}",
                    agent_id=agent_id,
                    task_id=None,
                    created=created,
                    subagent_type=session.subagent_type,
                    description=session.description,
                )

        if wait and not task.future.done():
            try:
                task.future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                logger.debug(
                    "Timed out waiting for sub-agent task '%s'.",
                    task.task_id,
                )
            except Exception as exc:
                logger.debug(
                    "Sub-agent task '%s' raised while waiting: %s",
                    task.task_id,
                    exc,
                )
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

    def agent_get_task_output(
        self,
        task_id: str,
        block: bool = False,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        r"""Get the latest result of a sub-agent task started earlier.

        Use this after calling :obj:`agent_run_subagent(wait=False)`. When
        :obj:`block` is False, the call returns immediately with the latest
        known status. When :obj:`block` is True, the tool waits up to
        :obj:`timeout` seconds for completion before returning.

        Args:
            task_id (str): Sub-agent task ID returned by
                :obj:`agent_run_subagent`.
            block (bool): Whether to wait for the task to finish before
                returning status and output. (default: :obj:`False`)
            timeout (Optional[float]): Maximum wait time in seconds when
                :obj:`block` is True. (default: :obj:`None`)

        Returns:
            Dict[str, Any]: Task status, associated :obj:`agent_id`, and any
                available result or error output.
        """
        task = self._get_task(task_id)
        if task is None:
            return self._error_result(
                f"No sub-agent task found for task_id '{task_id}'.",
                task_id=task_id,
                agent_id=None,
                result=None,
            )
        if block and not task.future.done():
            try:
                task.future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                pass
            except Exception:
                pass
            task = self._get_task(task_id)
            if task is None:
                return self._error_result(
                    f"No sub-agent task found for task_id '{task_id}'.",
                    task_id=task_id,
                    agent_id=None,
                    result=None,
                )

        return {
            "task_id": task.task_id,
            "agent_id": task.agent_id,
            "status": task.status,
            "result": task.result,
            "error": task.error,
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
            timeout=self.timeout,
            child_tool_policy=self._child_tool_policy,
            allowed_tool_names=(
                list(self._allowed_tool_names)
                if self._allowed_tool_names
                else None
            ),
            excluded_tool_names=(
                list(self._excluded_tool_names)
                if self._excluded_tool_names
                else None
            ),
        )

    def _purge_completed_tasks(self) -> None:
        """Remove finished tasks to prevent unbounded memory growth."""
        with self._lock:
            finished = [
                (tid, t)
                for tid, t in self._tasks.items()
                if t.status in {"completed", "failed", "stopped"}
            ]
            excess = len(finished) - self._MAX_FINISHED_TASKS + 1
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
            FunctionTool(self.agent_get_task_output),
            FunctionTool(self.agent_stop_task),
        ]
