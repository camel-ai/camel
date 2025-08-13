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
import concurrent.futures
from collections import deque
from typing import (
    Any,
    Callable,
    Coroutine,
    Deque,
    Dict,
    Generator,
    List,
    Optional,
    Set,
    Tuple,
    Union,
)

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.societies.workforce.base import BaseNode
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import (
    RecoveryDecision,
    TaskAssignment,
    TaskAssignResult,
    check_if_running,
    find_task_by_id,
)
from camel.societies.workforce.workforce_split.assignment import (
    TaskAssignmentManager,
)
from camel.societies.workforce.workforce_split.channel_communication import (
    ChannelCommunication,
)
from camel.societies.workforce.workforce_split.dependencies import (
    DependencyManager,
)
from camel.societies.workforce.workforce_split.failure import FailureAnalyzer
from camel.societies.workforce.workforce_split.in_flight_tracking import (
    InFlightTaskTracker,
)
from camel.societies.workforce.workforce_split.intervention import (
    WorkforceIntervention,
)
from camel.societies.workforce.workforce_split.introspection import (
    IntrospectionHelper,
)
from camel.societies.workforce.workforce_split.logger import (
    WorkforceLogger,
    WorkforceLoggerWrapper,
)
from camel.societies.workforce.workforce_split.memory import (
    SharedMemoryManager,
)
from camel.societies.workforce.workforce_split.snapshots import (
    WorkforceSnapshot,
    WorkforceSnapshotManager,
)
from camel.societies.workforce.workforce_split.state import WorkforceState
from camel.societies.workforce.workforce_split.task_management import (
    TaskManager,
)
from camel.societies.workforce.workforce_split.worker_management import (
    WorkerManagement,
)
from camel.tasks.task import (
    Task,
    TaskState,
    validate_task_content,
)
from camel.toolkits import TaskPlanningToolkit

from .complete_failure_dispatch import (
    WorkforceFailureDispatch,
)

logger = get_logger(__name__)


class WorkforceCore(BaseNode):
    r"""Core functionality for a workforce system where multiple worker nodes
    (agents) cooperate together to solve tasks.

    This class contains the essential lifecycle, configuration, and task
    processing methods extracted from the main Workforce class.
    """

    def __init__(
        self,
        description: str,
        children: Optional[List[BaseNode]] = None,
        coordinator_agent: Optional[ChatAgent] = None,
        task_agent: Optional[ChatAgent] = None,
        new_worker_agent: Optional[ChatAgent] = None,
        graceful_shutdown_timeout: float = 15.0,
        share_memory: bool = False,
        use_structured_output_handler: bool = True,
    ) -> None:
        super().__init__(description)
        self._child_listening_tasks: Deque[
            Union[asyncio.Task, concurrent.futures.Future]
        ] = deque()
        self._children = children or []
        self.new_worker_agent = new_worker_agent
        self.graceful_shutdown_timeout = graceful_shutdown_timeout
        self.share_memory = share_memory
        self.use_structured_output_handler = use_structured_output_handler
        self.metrics_logger = WorkforceLogger(workforce_id=self.node_id)
        self._task: Optional[Task] = None
        self._pending_tasks: Deque[Task] = deque()
        self._task_dependencies: Dict[str, List[str]] = {}
        self._assignees: Dict[str, str] = {}
        self._in_flight_tasks: int = 0
        # Dictionary to track task start times
        self._task_start_times: Dict[str, float] = {}
        # Human intervention support
        self._state: WorkforceState = WorkforceState.IDLE
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initially not paused
        self._stop_requested = False
        self._snapshots: List[WorkforceSnapshot] = []
        self._completed_tasks: List[Task] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._main_task_future: Optional[asyncio.Future] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        # Snapshot throttle support
        self._last_snapshot_time: float = 0.0
        # Minimum seconds between automatic snapshots
        self.snapshot_interval: float = 30.0

        self.snapshot_manager = WorkforceSnapshotManager()
        self.task_manager = TaskManager()
        self.shared_memory_manager = SharedMemoryManager()
        self.channel_communication = ChannelCommunication()
        self.failure_dispatch = WorkforceFailureDispatch()
        self.intervention = WorkforceIntervention()
        self.introspection_helper = IntrospectionHelper()
        self.logger_wrapper = WorkforceLoggerWrapper(
            metrics_logger=self.metrics_logger
        )
        self.in_flight_tracker = InFlightTaskTracker()
        self.failure_analyzer = FailureAnalyzer()
        self.dependency_manager = DependencyManager(
            task_dependencies=self._task_dependencies
        )

        # Set up coordinator agent with default system message
        coord_agent_sys_msg = BaseMessage.make_assistant_message(
            role_name="Workforce Manager",
            content="You are coordinating a group of workers. A worker "
            "can be a group of agents or a single agent. Each worker is "
            "created to solve a specific kind of task. Your job "
            "includes assigning tasks to a existing worker, creating "
            "a new worker for a task, etc.",
        )

        if coordinator_agent is None:
            logger.warning(
                "No coordinator_agent provided. Using default "
                "ChatAgent settings (ModelPlatformType.DEFAULT, "
                "ModelType.DEFAULT) with default system message."
            )
            self.coordinator_agent = ChatAgent(coord_agent_sys_msg)
        else:
            logger.info(
                "Custom coordinator_agent provided. Preserving user's "
                "system message and appending workforce coordination "
                "instructions to ensure proper functionality."
            )

            if coordinator_agent.system_message is not None:
                user_sys_msg_content = coordinator_agent.system_message.content
                combined_content = (
                    f"{user_sys_msg_content}\n\n"
                    f"{coord_agent_sys_msg.content}"
                )
                combined_sys_msg = BaseMessage.make_assistant_message(
                    role_name=coordinator_agent.system_message.role_name,
                    content=combined_content,
                )
            else:
                combined_sys_msg = coord_agent_sys_msg

            # Create a new agent with the provided agent's configuration
            # but with the combined system message
            self.coordinator_agent = ChatAgent(
                system_message=combined_sys_msg,
                model=coordinator_agent.model_backend,
                memory=coordinator_agent.memory,
                message_window_size=getattr(
                    coordinator_agent.memory, "window_size", None
                ),
                token_limit=getattr(
                    coordinator_agent.memory.get_context_creator(),
                    "token_limit",
                    None,
                ),
                output_language=coordinator_agent.output_language,
                tools=[
                    tool.func
                    for tool in coordinator_agent._internal_tools.values()
                ],
                external_tools=[
                    schema
                    for schema in (
                        coordinator_agent._external_tool_schemas.values()
                    )
                ],
                response_terminators=coordinator_agent.response_terminators,
                max_iteration=coordinator_agent.max_iteration,
                stop_event=coordinator_agent.stop_event,
            )

        # Initialize assignment manager
        self.assignment_manager = TaskAssignmentManager(
            coordinator_agent=self.coordinator_agent,
            use_structured_output_handler=self.use_structured_output_handler,
        )

        # Set up task agent with default system message and required tools
        task_sys_msg = BaseMessage.make_assistant_message(
            role_name="Task Planner",
            content="You are going to compose and decompose tasks. Keep "
            "tasks that are sequential and require the same type of "
            "agent together in one agent process. Only decompose tasks "
            "that can be handled in parallel and require different types "
            "of agents. This ensures efficient execution by minimizing "
            "context switching between agents.",
        )
        task_planning_tools = TaskPlanningToolkit().get_tools()

        if task_agent is None:
            logger.warning(
                "No task_agent provided. Using default ChatAgent "
                "settings (ModelPlatformType.DEFAULT, ModelType.DEFAULT) "
                "with default system message and TaskPlanningToolkit."
            )
            task_tools = TaskPlanningToolkit().get_tools()
            self.task_agent = ChatAgent(
                task_sys_msg,
                tools=task_tools,  # type: ignore[arg-type]
            )
        else:
            logger.info(
                "Custom task_agent provided. Preserving user's "
                "system message and appending task planning "
                "instructions to ensure proper functionality."
            )

            if task_agent.system_message is not None:
                user_task_sys_msg_content = task_agent.system_message.content
                combined_task_content = (
                    f"{user_task_sys_msg_content}\n\n"
                    f"{task_sys_msg.content}"
                )
                combined_task_sys_msg = BaseMessage.make_assistant_message(
                    role_name=task_agent.system_message.role_name,
                    content=combined_task_content,
                )
            else:
                combined_task_sys_msg = task_sys_msg

            # Since ChatAgent constructor uses a dictionary with
            # function names as keys, we don't need to manually deduplicate.
            combined_tools = [
                tool.func for tool in task_agent._internal_tools.values()
            ] + [tool.func for tool in task_planning_tools]

            # Create a new agent with the provided agent's configuration
            # but with the combined system message and tools
            self.task_agent = ChatAgent(
                system_message=combined_task_sys_msg,
                model=task_agent.model_backend,
                memory=task_agent.memory,
                message_window_size=getattr(
                    task_agent.memory, "window_size", None
                ),
                token_limit=getattr(
                    task_agent.memory.get_context_creator(),
                    "token_limit",
                    None,
                ),
                output_language=task_agent.output_language,
                tools=combined_tools,
                external_tools=[
                    schema
                    for schema in task_agent._external_tool_schemas.values()
                ],
                response_terminators=task_agent.response_terminators,
                max_iteration=task_agent.max_iteration,
                stop_event=task_agent.stop_event,
            )

        if new_worker_agent is None:
            logger.info(
                "No new_worker_agent provided. Workers created at runtime "
                "will use default ChatAgent settings with SearchToolkit, "
                "CodeExecutionToolkit, and ThinkingToolkit. To customize "
                "runtime worker creation, pass a ChatAgent instance."
            )
        else:
            # Validate new_worker_agent if provided
            self._validate_agent_compatibility(
                new_worker_agent, "new_worker_agent"
            )

        if self.share_memory:
            logger.info(
                "Shared memory enabled. All agents will share their complete "
                "conversation history and function-calling trajectory for "
                "better context continuity during task handoffs."
            )

        # Initialize worker management AFTER coordinator_agent is set up
        self.worker_management = WorkerManagement(
            coordinator_agent=self.coordinator_agent,
            new_worker_agent=self.new_worker_agent,
            use_structured_output_handler=self.use_structured_output_handler,
            children=self._children,
            pause_event=self._pause_event,
            loop=self._loop,
            state=self._state,
            metrics_logger=self.metrics_logger,
        )

    # ========== Core Actions ==========

    async def _async_reset(self) -> None:
        r"""Async implementation of reset to run on the event loop."""
        self._pause_event.set()

    @check_if_running(False)
    def reset(self) -> None:
        r"""Reset the workforce and all the child nodes under it. Can only
        be called when the workforce is not running.
        """
        super().reset()
        self._task = None
        self._pending_tasks.clear()
        self._child_listening_tasks.clear()
        # Clear dependency tracking
        self._task_dependencies.clear()
        self._completed_tasks = []
        self._assignees.clear()
        self._in_flight_tasks = 0
        self.coordinator_agent.reset()
        self.task_agent.reset()
        self._task_start_times.clear()
        for child in self._children:
            child.reset()

        # Reset intervention state
        self._state = WorkforceState.IDLE
        self.worker_management._state = self._state
        self._stop_requested = False
        # Handle asyncio.Event in a thread-safe way
        if self._loop and not self._loop.is_closed():
            # If we have a loop, use it to set the event safely
            try:
                asyncio.run_coroutine_threadsafe(
                    self._async_reset(), self._loop
                ).result()
            except RuntimeError as e:
                logger.warning(f"Failed to reset via existing loop: {e}")
                # Fallback to direct event manipulation
                self._pause_event.set()
        else:
            # No active loop, directly set the event
            self._pause_event.set()

        if hasattr(self, 'metrics_logger') and self.metrics_logger is not None:
            self.metrics_logger.reset_task_data()
        else:
            self.metrics_logger = WorkforceLogger(workforce_id=self.node_id)

        # Update worker management state
        self.worker_management._state = self._state
        self.worker_management._children = self._children

    @check_if_running(False)
    def set_channel(self, channel: TaskChannel) -> None:
        r"""Set the channel for the node and all the child nodes under it."""
        self._channel = channel
        # Update worker management channel
        self.worker_management._channel = channel
        for child in self._children:
            child.set_channel(channel)

    @check_if_running(False)
    async def start(self) -> None:
        r"""Start itself and all the child nodes under it."""
        # Set running state
        self._running = True
        self._state = WorkforceState.RUNNING
        self.worker_management._state = self._state

        try:
            # Sync shared memory at the start to ensure all agents have context
            if self.share_memory:
                logger.info(
                    f"Syncing shared memory at workforce "
                    f"{self.node_id} startup"
                )
                self._sync_shared_memory()

            for child in self._children:
                child_listening_task = asyncio.create_task(child.start())
                self._child_listening_tasks.append(child_listening_task)

            # Call the channel communication's listen_to_channel method
            await self.channel_communication.listen_to_channel(
                channel=self._channel,
                node_id=self.node_id,
                pending_tasks=list(self._pending_tasks),
                completed_tasks=self._completed_tasks,
                task_dependencies=self._task_dependencies,
                assignees=self._assignees,
                task_start_times=self._task_start_times,
                in_flight_tasks=self._in_flight_tasks,
                metrics_logger=self.metrics_logger,
                find_assignee_func=self._find_assignee,
                increment_in_flight_tasks_func=self._increment_in_flight_tasks,
                decrement_in_flight_tasks_func=self._decrement_in_flight_tasks,
                handle_failed_task_func=self._handle_failed_task,
                handle_completed_task_func=self._handle_completed_task,
                graceful_shutdown_func=self._graceful_shutdown,
                is_task_result_insufficient_func=None,  # You can add this if
                # needed
                pause_event=self._pause_event,
                stop_requested=self._stop_requested,
                running=self._running,
                state=self._state,
                last_snapshot_time=self._last_snapshot_time,
                snapshot_interval=self.snapshot_interval,
                save_snapshot_func=self.save_snapshot,
                loop=self._loop,
            )
        finally:
            self._running = False
            # Set final state based on stop request
            if self._stop_requested:
                self._state = WorkforceState.STOPPED
            else:
                self._state = WorkforceState.IDLE
            self.worker_management._state = self._state

    @check_if_running(True)
    def stop(self) -> None:
        r"""Stop all the child nodes under it. The node itself will be stopped
        by its parent node.
        """
        # Set stopping state
        self._state = WorkforceState.STOPPED
        self.worker_management._state = self._state
        self._stop_requested = True

        # Stop all child nodes first
        for child in self._children:
            if child._running:
                child.stop()

        # Cancel child listening tasks
        if self._child_listening_tasks:
            try:
                loop = asyncio.get_running_loop()
                if loop and not loop.is_closed():
                    # Create graceful cleanup task
                    async def cleanup():
                        await asyncio.sleep(0.1)  # Brief grace period
                        for task in self._child_listening_tasks:
                            if not task.done():
                                task.cancel()

                        # Handle both asyncio.Task and concurrent.futures.
                        # Future
                        awaitables = []
                        for task in self._child_listening_tasks:
                            if isinstance(task, concurrent.futures.Future):
                                # Convert Future to awaitable
                                awaitables.append(asyncio.wrap_future(task))
                            else:
                                # Already an asyncio.Task
                                awaitables.append(task)

                        await asyncio.gather(
                            *awaitables,
                            return_exceptions=True,
                        )

                    self._cleanup_task = loop.create_task(cleanup())
                else:
                    # No active loop, cancel immediately
                    for task in self._child_listening_tasks:
                        task.cancel()
            except (RuntimeError, Exception) as e:
                # Fallback: cancel immediately
                logger.debug(f"Exception during task cleanup: {e}")
                for task in self._child_listening_tasks:
                    task.cancel()

        self._running = False

    # ========== Worker Management Delegation ==========

    async def _create_worker_node_for_task(self, task: Task):
        """Delegate worker creation to worker management."""
        return await self.worker_management.create_worker_node_for_task(task)

    async def _create_new_agent(self, role: str, sys_msg: str) -> ChatAgent:
        """Delegate agent creation to worker management."""
        return await self.worker_management.create_new_agent(role, sys_msg)

    def _start_child_node_when_paused(
        self, start_coroutine: Coroutine
    ) -> None:
        """Delegate child node starting to worker management."""
        self.worker_management.start_child_node_when_paused(start_coroutine)

    def add_single_agent_worker(
        self,
        description: str,
        worker: ChatAgent,
        pool_max_size: int = 10,
    ) -> 'WorkforceCore':
        """Add a single agent worker to the workforce."""
        self.worker_management.add_single_agent_worker(
            description, worker, pool_max_size
        )
        # Update our children list to match worker management
        self._children = self.worker_management._children
        return self

    def add_role_playing_worker(
        self,
        description: str,
        assistant_role_name: str,
        user_role_name: str,
        assistant_agent_kwargs: Optional[Dict] = None,
        user_agent_kwargs: Optional[Dict] = None,
        summarize_agent_kwargs: Optional[Dict] = None,
        chat_turn_limit: int = 3,
    ) -> 'WorkforceCore':
        """Add a role playing worker to the workforce."""
        self.worker_management.add_role_playing_worker(
            description,
            assistant_role_name,
            user_role_name,
            assistant_agent_kwargs,
            user_agent_kwargs,
            summarize_agent_kwargs,
            chat_turn_limit,
        )
        # Update our children list to match worker management
        self._children = self.worker_management._children
        return self

    def add_workforce(self, workforce: 'WorkforceCore') -> 'WorkforceCore':
        """Add a workforce node to the workforce."""
        # Directly append to children instead of delegating to
        # worker_management since worker_management expects a
        # WorkerManagement instance
        self._children.append(workforce)
        return self

    # ========== Shared Memory Management Delegation ==========

    def _collect_shared_memory(self) -> Dict[str, List]:
        """Collect memory from all agents for sharing."""
        return self.shared_memory_manager.collect_shared_memory(
            coordinator_agent=self.coordinator_agent,
            task_agent=self.task_agent,
            children=self._children,
            share_memory=self.share_memory,
        )

    def _share_memory_with_agents(
        self, shared_memory: Dict[str, List]
    ) -> None:
        """Share collected memory with all agents."""
        self.shared_memory_manager.share_memory_with_agents(
            shared_memory=shared_memory,
            coordinator_agent=self.coordinator_agent,
            task_agent=self.task_agent,
            children=self._children,
            share_memory=self.share_memory,
        )

    def _sync_shared_memory(self) -> None:
        """Synchronize memory across all agents."""
        self.shared_memory_manager.sync_shared_memory(
            coordinator_agent=self.coordinator_agent,
            task_agent=self.task_agent,
            children=self._children,
            share_memory=self.share_memory,
        )

    # ========== High-level Entrypoints ==========

    @check_if_running(False)
    async def process_task_async(
        self, task: Task, interactive: bool = False
    ) -> Task:
        r"""Main entry point to process a task asynchronously.

        Args:
            task (Task): The task to be processed.
            interactive (bool, optional): If True, enables human-intervention
                workflow (pause/resume/snapshot). Defaults to False, which
                runs the task in a blocking one-shot manner.

        Returns:
            Task: The updated task.
        """
        # Delegate to intervention pipeline when requested to keep
        # backward-compat.
        if interactive:
            return await self._process_task_with_snapshot(task)

        if not validate_task_content(task.content, task.id):
            task.state = TaskState.FAILED
            task.result = "Task failed: Invalid or empty content provided"
            logger.warning(
                f"Task {task.id} rejected: Invalid or empty content. "
                f"Content preview: '{task.content}'"
            )
            return task

        self.reset()
        self._task = task
        if self.metrics_logger:
            self.metrics_logger.log_task_created(
                task_id=task.id,
                description=task.content,
                task_type=task.type,
                metadata=task.additional_info,
            )
        task.state = TaskState.FAILED

        # The agent tend to be overconfident on the whole task, so we
        # decompose the task into subtasks first
        subtasks_result = self._decompose_task(task)

        # Handle both streaming and non-streaming results
        if isinstance(subtasks_result, Generator):
            # This is a generator (streaming mode)
            subtasks = []
            for new_tasks in subtasks_result:
                subtasks.extend(new_tasks)
        else:
            # This is a regular list (non-streaming mode)
            subtasks = subtasks_result

        if self.metrics_logger and subtasks:
            self.metrics_logger.log_task_decomposed(
                parent_task_id=task.id, subtask_ids=[st.id for st in subtasks]
            )
            for subtask in subtasks:
                self.metrics_logger.log_task_created(
                    task_id=subtask.id,
                    description=subtask.content,
                    parent_task_id=task.id,
                    task_type=subtask.type,
                    metadata=subtask.additional_info,
                )

        if subtasks:
            # If decomposition happened, the original task becomes a container.
            # We only execute its subtasks.
            self._pending_tasks.extendleft(reversed(subtasks))
        else:
            # If no decomposition, execute the original task.
            self._pending_tasks.append(task)

        self.set_channel(TaskChannel())

        await self.start()

        if subtasks:
            task.result = "\n\n".join(
                f"--- Subtask {sub.id} Result ---\n{sub.result}"
                for sub in task.subtasks
                if sub.result
            )
            if task.subtasks and all(
                sub.state == TaskState.DONE for sub in task.subtasks
            ):
                task.state = TaskState.DONE
            else:
                task.state = TaskState.FAILED

        return task

    def process_task(self, task: Task) -> Task:
        r"""Synchronous wrapper for process_task that handles async operations
        internally.

        Args:
            task (Task): The task to be processed.

        Returns:
            Task: The updated task.

        Example:
            >>> workforce = WorkforceCore("My Team")
            >>> task = Task(content="Analyze data", id="1")
            >>> result = workforce.process_task(task)  # No async/await
            needed
            >>> print(result.result)
        """
        # Check if we're already in an event loop
        try:
            current_loop = asyncio.get_running_loop()
            # Store the current loop for potential reuse by async tools
            self._loop = current_loop

            logger.info(
                "Running in active event loop context. "
                "Consider using process_task_async() directly for better "
                "async tool compatibility."
            )

            # Create a new thread with a fresh event loop
            def run_in_thread():
                # Create new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(
                        self.process_task_async(task)
                    )
                finally:
                    new_loop.close()
                    # Restore original loop reference
                    self._loop = current_loop

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()

        except RuntimeError:
            # No event loop running, we can create one
            return asyncio.run(self.process_task_async(task))

    async def _process_task_with_snapshot(self, task: Task) -> Task:
        r"""Async version of process_task that supports human intervention.
        This method can be paused, resumed, and allows task modification.

        Args:
            task (Task): The task to be processed.

        Returns:
            Task: The updated task.
        """

        if not validate_task_content(task.content, task.id):
            task.state = TaskState.FAILED
            task.result = "Task failed: Invalid or empty content provided"
            logger.warning(
                f"Task {task.id} rejected: Invalid or empty content. "
                f"Content preview: '{task.content}'"
            )
            return task

        self.reset()
        self._task = task
        self._state = WorkforceState.RUNNING
        self.worker_management._state = self._state
        task.state = TaskState.OPEN  # Task is ready to be processed

        # Decompose the task into subtasks first
        subtasks_result = self._decompose_task(task)

        # Handle both streaming and non-streaming results
        if isinstance(subtasks_result, Generator):
            # This is a generator (streaming mode)
            subtasks = []
            for new_tasks in subtasks_result:
                subtasks.extend(new_tasks)
        else:
            # This is a regular list (non-streaming mode)
            subtasks = subtasks_result
        if subtasks:
            # If decomposition happened, the original task becomes a container.
            # We only execute its subtasks.
            self._pending_tasks.extendleft(reversed(subtasks))
        else:
            # If no decomposition, execute the original task.
            self._pending_tasks.append(task)

        self.set_channel(TaskChannel())

        # Save initial snapshot
        self.save_snapshot("Initial task decomposition")

        try:
            await self.start()
        except Exception as e:
            logger.error(f"Error in workforce execution: {e}")
            self._state = WorkforceState.STOPPED
            self.worker_management._state = self._state
            raise
        finally:
            if self._state != WorkforceState.STOPPED:
                self._state = WorkforceState.IDLE
                self.worker_management._state = self._state

        return task

    def _process_task_with_intervention(self, task: Task) -> Task:
        r"""Process task with human intervention support. This creates and
        manages its own event loop to allow for pausing/resuming functionality.

        Args:
            task (Task): The task to be processed.

        Returns:
            Task: The updated task.
        """
        # Create new event loop if none exists or if we need a fresh one
        try:
            self._loop = asyncio.get_event_loop()
            if self._loop.is_closed():
                self._loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self._loop)
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        try:
            return self._loop.run_until_complete(
                self._process_task_with_snapshot(task)
            )
        finally:
            # Decide whether to keep or close the loop
            if self._loop and not self._loop.is_closed():
                if self._state == WorkforceState.PAUSED:
                    # Keep alive to support resume()
                    logger.info(
                        "Event loop kept alive for potential resume "
                        "operations."
                    )
                else:
                    # No more tasks; shut everything down cleanly
                    try:
                        # Ensure all async generators are finished
                        self._loop.run_until_complete(
                            self._loop.shutdown_asyncgens()
                        )
                    except RuntimeError:
                        # Loop already running elsewhere
                        pass
                    self._loop.close()

    def continue_from_pause(self) -> Optional[Task]:
        r"""Continue execution from a paused state. This reuses the
        existing event loop.

        Returns:
            Optional[Task]: The completed task if execution finishes, None if
                still running/paused.
        """
        if self._state != WorkforceState.PAUSED:
            logger.warning("Workforce is not in paused state.")
            return None

        if self._loop is None or self._loop.is_closed():
            logger.error("No active event loop available for resuming.")
            return None

        # Resume execution
        self.resume(self.node_id)

        try:
            # Continue the existing async task
            remaining_task = self._loop.run_until_complete(
                self._continue_execution()
            )
            return remaining_task
        except Exception as e:
            logger.error(f"Error continuing execution: {e}")
            self._state = WorkforceState.STOPPED
            self.worker_management._state = self._state
            return None

    async def _continue_execution(self) -> Optional[Task]:
        r"""Internal method to continue execution after pause."""
        try:
            # Call the channel communication's listen_to_channel method
            await self.channel_communication.listen_to_channel(
                channel=self._channel,
                node_id=self.node_id,
                pending_tasks=list(self._pending_tasks),
                completed_tasks=self._completed_tasks,
                task_dependencies=self._task_dependencies,
                assignees=self._assignees,
                task_start_times=self._task_start_times,
                in_flight_tasks=self._in_flight_tasks,
                metrics_logger=self.metrics_logger,
                find_assignee_func=self._find_assignee,
                increment_in_flight_tasks_func=self._increment_in_flight_tasks,
                decrement_in_flight_tasks_func=self._decrement_in_flight_tasks,
                handle_failed_task_func=self._handle_failed_task,
                handle_completed_task_func=self._handle_completed_task,
                graceful_shutdown_func=self._graceful_shutdown,
                is_task_result_insufficient_func=None,
                pause_event=self._pause_event,
                stop_requested=self._stop_requested,
                running=self._running,
                state=self._state,
                last_snapshot_time=self._last_snapshot_time,
                snapshot_interval=self.snapshot_interval,
                save_snapshot_func=self.save_snapshot,
                loop=self._loop,
            )
        except Exception as e:
            logger.error(f"Error in continued execution: {e}")
            self._state = WorkforceState.STOPPED
            self.worker_management._state = self._state
            raise
        finally:
            if self._state != WorkforceState.STOPPED:
                self._state = WorkforceState.IDLE
                self.worker_management._state = self._state

        return self._task

    # ========== Introspection and Metrics ==========

    def get_workforce_status(self) -> Dict:
        r"""Get current workforce status for human review."""
        return {
            "state": self._state.value,
            "pending_tasks_count": len(self._pending_tasks),
            "completed_tasks_count": len(self._completed_tasks),
            "snapshots_count": len(self._snapshots),
            "children_count": len(self._children),
            "main_task_id": self._task.id if self._task else None,
        }

    # ========== Utility Methods ==========

    def _validate_agent_compatibility(
        self, agent: ChatAgent, agent_context: str = "agent"
    ) -> None:
        r"""Validate that agent configuration is compatible with workforce
        settings.

        Args:
            agent (ChatAgent): The agent to validate.
            agent_context (str): Context description for error messages.

        Raises:
            ValueError: If agent has tools and stream mode enabled but
                use_structured_output_handler is False.
        """
        agent_has_tools = (
            bool(agent.tool_dict) if hasattr(agent, 'tool_dict') else False
        )
        agent_stream_mode = (
            getattr(agent.model_backend, 'stream', False)
            if hasattr(agent, 'model_backend')
            else False
        )

        if (
            agent_has_tools
            and agent_stream_mode
            and not self.use_structured_output_handler
        ):
            raise ValueError(
                f"{agent_context} has tools and stream mode enabled, but "
                "use_structured_output_handler is False. Native structured "
                "output doesn't work with tool calls in stream mode. "
                "Please set use_structured_output_handler=True when creating "
                "the Workforce."
            )

    def _attach_pause_event_to_agent(self, agent: ChatAgent) -> None:
        r"""Ensure the given ChatAgent shares this workforce's pause_event.

        If the agent already has a different pause_event we overwrite it and
        emit a debug log (it is unlikely an agent needs multiple independent
        pause controls once managed by this workforce)."""
        try:
            existing_pause_event = getattr(agent, "pause_event", None)
            if existing_pause_event is not self._pause_event:
                if existing_pause_event is not None:
                    logger.debug(
                        f"Overriding pause_event for agent {agent.agent_id} "
                        f"(had different pause_event: "
                        f"{id(existing_pause_event)} "
                        f"-> {id(self._pause_event)})"
                    )
                agent.pause_event = self._pause_event
        except AttributeError:
            # Should not happen, but guard against unexpected objects
            logger.warning(
                f"Cannot attach pause_event to object {type(agent)} - "
                f"missing pause_event attribute"
            )

    def _ensure_pause_event_in_kwargs(self, kwargs: Optional[Dict]) -> Dict:
        r"""Insert pause_event into kwargs dict for ChatAgent construction."""
        new_kwargs = dict(kwargs) if kwargs else {}
        new_kwargs.setdefault("pause_event", self._pause_event)
        return new_kwargs

    # ========== Task Management Delegation ==========

    def get_pending_tasks(self) -> List[Task]:
        """Get current pending tasks for human review."""
        return self.task_manager.get_pending_tasks(self._pending_tasks)

    def get_completed_tasks(self) -> List[Task]:
        """Get completed tasks."""
        return self.task_manager.get_completed_tasks(self._completed_tasks)

    def modify_task_content(self, task_id: str, new_content: str) -> bool:
        """Modify the content of a pending task."""
        return self.task_manager.modify_task_content(
            task_id, new_content, self._pending_tasks
        )

    def add_task(
        self,
        content: str,
        task_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        insert_position: int = -1,
    ) -> Task:
        """Add a new task to the pending queue."""
        return self.task_manager.add_task(
            content=content,
            pending_tasks=self._pending_tasks,
            task_id=task_id,
            additional_info=additional_info,
            insert_position=insert_position,
        )

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the pending queue."""
        return self.task_manager.remove_task(task_id, self._pending_tasks)

    def reorder_tasks(self, task_ids: List[str]) -> bool:
        """Reorder pending tasks according to the provided task IDs list."""
        return self.task_manager.reorder_tasks(task_ids, self._pending_tasks)

    # ========== Snapshot Management Delegation ==========

    def save_snapshot(self, description: str = "") -> None:
        """Save current state as a snapshot."""
        self.snapshot_manager.save_snapshot(self, description)

    def list_snapshots(self) -> List[str]:
        """List all available snapshots."""
        return self.snapshot_manager.list_snapshots(self)

    def resume_from_task(self, task_id: str) -> bool:
        """Resume execution from a specific task."""
        return self.snapshot_manager.resume_from_task(self, task_id)

    def restore_from_snapshot(self, snapshot_index: int) -> bool:
        """Restore workforce state from a snapshot."""
        return self.snapshot_manager.restore_from_snapshot(
            self, snapshot_index
        )

    # ========== Assignment Management Delegation ==========

    def _call_coordinator_for_assignment(
        self,
        tasks: List[Task],
        child_nodes_info: str,
        invalid_ids: Optional[List[str]] = None,
    ) -> TaskAssignResult:
        """Delegate assignment coordination to assignment manager."""
        return self.assignment_manager.call_coordinator_for_assignment(
            tasks, child_nodes_info, invalid_ids
        )

    def _validate_assignments(
        self, assignments: List[TaskAssignment], valid_ids: Set[str]
    ) -> Tuple[List[TaskAssignment], List[TaskAssignment]]:
        """Delegate assignment validation to assignment manager."""
        return self.assignment_manager.validate_assignments(
            assignments, valid_ids
        )

    async def _handle_task_assignment_fallbacks(
        self, tasks: List[Task], create_worker_node_for_task_func: Callable
    ) -> List[TaskAssignment]:
        """Delegate assignment fallback handling to assignment manager."""
        return await self.assignment_manager.handle_task_assignment_fallbacks(
            tasks, create_worker_node_for_task_func
        )

    async def _handle_assignment_retry_and_fallback(
        self,
        invalid_assignments: List[TaskAssignment],
        tasks: List[Task],
        valid_worker_ids: Set[str],
        create_worker_node_for_task_func: Callable,
    ) -> List[TaskAssignment]:
        """Delegate assignment retry and fallback to assignment manager."""
        return (
            await self.assignment_manager.handle_assignment_retry_and_fallback(
                invalid_assignments,
                tasks,
                valid_worker_ids,
                create_worker_node_for_task_func,
            )
        )

    def _update_task_dependencies_from_assignments(
        self,
        assignments: List[TaskAssignment],
        tasks: List[Task],
        completed_tasks: List[Task],
        pending_tasks: List[Task],
    ) -> None:
        """Delegate dependency updates to assignment manager."""
        self.assignment_manager.update_task_dependencies_from_assignments(
            assignments, tasks, completed_tasks, pending_tasks
        )

    async def _find_assignee(self, tasks: List[Task]) -> TaskAssignResult:
        """Delegate assignee finding to assignment manager."""
        valid_worker_ids = self._get_valid_worker_ids()
        child_nodes_info = self._get_child_nodes_info()
        return await self.assignment_manager.find_assignee(
            tasks,
            valid_worker_ids,
            child_nodes_info,
            self._create_worker_node_for_task,
            self.get_completed_tasks(),
            self.get_pending_tasks(),
        )

    # ========== Channel Communication Delegation ==========

    async def _post_task(
        self,
        task: Task,
        assignee_id: str,
        channel: Optional[TaskChannel] = None,
        node_id: Optional[str] = None,
        task_start_times: Optional[Dict[str, float]] = None,
        metrics_logger=None,
        increment_in_flight_tasks_func=None,
    ) -> None:
        """Delegate task posting to channel communication manager."""
        # Use instance attributes if not provided
        if channel is None:
            channel = self._channel
        if node_id is None:
            node_id = self.node_id
        if task_start_times is None:
            task_start_times = self._task_start_times

        await self.channel_communication.post_task(
            task,
            assignee_id,
            channel,
            node_id,
            task_start_times,
            metrics_logger,
            increment_in_flight_tasks_func,
        )

    async def _get_returned_task(
        self,
        channel: Optional[TaskChannel] = None,
        node_id: Optional[str] = None,
        pending_tasks: Optional[List[Task]] = None,
        in_flight_tasks: Optional[int] = None,
    ) -> Optional[Task]:
        """Delegate task retrieval to channel communication manager."""
        # Use instance attributes if not provided
        if channel is None:
            channel = self._channel
        if node_id is None:
            node_id = self.node_id
        if pending_tasks is None:
            pending_tasks = list(self._pending_tasks)
        if in_flight_tasks is None:
            in_flight_tasks = self._in_flight_tasks

        return await self.channel_communication.get_returned_task(
            channel, node_id, pending_tasks, in_flight_tasks
        )

    async def _post_ready_tasks(
        self,
        pending_tasks: Optional[List[Task]] = None,
        completed_tasks: Optional[List[Task]] = None,
        task_dependencies: Optional[Dict[str, List[str]]] = None,
        assignees: Optional[Dict[str, str]] = None,
        channel: Optional[TaskChannel] = None,
        node_id: Optional[str] = None,
        task_start_times: Optional[Dict[str, float]] = None,
        metrics_logger=None,
        increment_in_flight_tasks_func=None,
        find_assignee_func=None,
    ) -> None:
        """Delegate ready task posting to channel communication manager."""
        # Use instance attributes if not provided
        if pending_tasks is None:
            pending_tasks = list(self._pending_tasks)
        if completed_tasks is None:
            completed_tasks = self._completed_tasks
        if task_dependencies is None:
            task_dependencies = self._task_dependencies
        if assignees is None:
            assignees = self._assignees
        if channel is None:
            channel = self._channel
        if node_id is None:
            node_id = self.node_id
        if task_start_times is None:
            task_start_times = self._task_start_times

        await self.channel_communication.post_ready_tasks(
            pending_tasks,
            completed_tasks,
            task_dependencies,
            assignees,
            channel,
            node_id,
            task_start_times,
            metrics_logger,
            increment_in_flight_tasks_func,
            find_assignee_func,
        )

    async def _listen_to_channel(self) -> None:
        """Listen to channel - base class implementation."""
        await self.channel_communication.listen_to_channel(
            self._channel,
            self.node_id,
            list(self._pending_tasks),
            self._completed_tasks,
            self._task_dependencies,
            self._assignees,
            self._task_start_times,
            self._in_flight_tasks,
            self.metrics_logger,
            self._find_assignee,
            self._increment_in_flight_tasks,
            self._decrement_in_flight_tasks,
            self._handle_failed_task,
            self._handle_completed_task,
            self._graceful_shutdown,
            None,
            self._pause_event,
            self._stop_requested,
            self._running,
            self._state,
            self._last_snapshot_time,
            self.snapshot_interval,
            None,
            self._loop,
        )

    async def _listen_to_channel_with_params(
        self,
        channel: TaskChannel,
        node_id: str,
        pending_tasks: List[Task],
        completed_tasks: List[Task],
        task_dependencies: Dict[str, List[str]],
        assignees: Dict[str, str],
        task_start_times: Dict[str, float],
        in_flight_tasks: int,
        metrics_logger=None,
        find_assignee_func=None,
        increment_in_flight_tasks_func=None,
        decrement_in_flight_tasks_func=None,
        handle_failed_task_func=None,
        handle_completed_task_func=None,
        graceful_shutdown_func=None,
        is_task_result_insufficient_func=None,
        pause_event=None,
        stop_requested=False,
        running=False,
        state=None,
        last_snapshot_time=0,
        snapshot_interval=60,
        save_snapshot_func=None,
        loop=None,
    ) -> None:
        """Listen to channel with parameters."""
        await self.channel_communication.listen_to_channel(
            channel,
            node_id,
            pending_tasks,
            completed_tasks,
            task_dependencies,
            assignees,
            task_start_times,
            in_flight_tasks,
            metrics_logger,
            find_assignee_func,
            increment_in_flight_tasks_func,
            decrement_in_flight_tasks_func,
            handle_failed_task_func,
            handle_completed_task_func,
            graceful_shutdown_func,
            is_task_result_insufficient_func,
            pause_event,
            stop_requested,
            running,
            state,
            last_snapshot_time,
            snapshot_interval,
            save_snapshot_func,
            loop,
        )

    def _submit_coro_to_loop(
        self, coro: Coroutine, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Delegate coroutine submission to channel communication manager."""
        self.channel_communication.submit_coro_to_loop(coro, loop)

    # ========== Failure Dispatch Delegation ==========

    async def _handle_failed_task(self, task: Task) -> bool:
        """Delegate failed task handling to failure dispatch manager."""
        return await self.failure_dispatch.handle_failed_task(self, task)

    async def _handle_completed_task(self, task: Task) -> None:
        """Delegate completed task handling to failure dispatch manager."""
        await self.failure_dispatch.handle_completed_task(self, task)

    async def _graceful_shutdown(self, failed_task: Task) -> None:
        """Delegate graceful shutdown to failure dispatch manager."""
        await self.failure_dispatch.graceful_shutdown(self, failed_task)

    def clone(self, with_memory: bool = False) -> 'WorkforceCore':
        """Clone the workforce core."""
        # Create a new instance with the same configuration
        cloned_core = WorkforceCore(
            description=self.description,
            children=self._children.copy() if self._children else None,
            coordinator_agent=self.coordinator_agent,
            task_agent=self.task_agent,
            new_worker_agent=self.new_worker_agent,
            graceful_shutdown_timeout=self.graceful_shutdown_timeout,
            share_memory=self.share_memory,
            use_structured_output_handler=self.use_structured_output_handler,
        )
        return cloned_core

    def to_mcp(
        self,
        name: str = "CAMEL-Workforce",
        description: str = (
            "A workforce system using the CAMEL AI framework for "
            "multi-agent collaboration."
        ),
        dependencies: Optional[List[str]] = None,
        host: str = "localhost",
        port: int = 8001,
    ):
        """Delegate MCP server creation to failure dispatch manager."""
        return self.failure_dispatch.to_mcp(
            self, name, description, dependencies, host, port
        )

    # ========== Intervention Delegation ==========

    async def async_pause(
        self, node_id: str, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Delegate async pause to intervention manager."""
        await self.intervention.async_pause(
            self._state, self._pause_event, node_id, loop
        )

    def pause(
        self, node_id: str, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Delegate pause to intervention manager."""
        self._state = WorkforceState.PAUSED
        self.worker_management._state = self._state
        self.intervention.pause(self._state, self._pause_event, node_id, loop)

    async def async_resume(
        self,
        node_id: str,
        pending_tasks=None,
        post_ready_tasks_func=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Delegate async resume to intervention manager."""
        await self.intervention.async_resume(
            self._state,
            self._pause_event,
            node_id,
            pending_tasks,
            post_ready_tasks_func,
            loop,
        )

    def resume(
        self,
        node_id: str,
        pending_tasks=None,
        post_ready_tasks_func=None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Delegate resume to intervention manager."""
        self._state = WorkforceState.RUNNING
        self.worker_management._state = self._state
        self.intervention.resume(
            self._state,
            self._pause_event,
            node_id,
            pending_tasks,
            post_ready_tasks_func,
            loop,
        )

    async def async_stop_gracefully(
        self, node_id: str, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Delegate async graceful stop to intervention manager."""
        await self.intervention.async_stop_gracefully(
            self._pause_event, node_id, loop
        )

    def stop_gracefully(
        self, node_id: str, loop: Optional[asyncio.AbstractEventLoop] = None
    ) -> None:
        """Delegate graceful stop to intervention manager."""
        self.intervention.stop_gracefully(self._pause_event, node_id, loop)

    # ========== Introspection Delegation ==========

    def _get_child_nodes_info(self) -> str:
        """Delegate child nodes info to introspection helper."""
        return self.introspection_helper.get_child_nodes_info(self._children)

    def _get_node_info(self, node) -> str:
        """Delegate node info to introspection helper."""
        return self.introspection_helper.get_node_info(node)

    def _get_single_agent_info(self, worker) -> str:
        """Delegate single agent info to introspection helper."""
        return self.introspection_helper.get_single_agent_info(worker)

    def _get_valid_worker_ids(self) -> Set[str]:
        """Delegate valid worker IDs to introspection helper."""
        return self.introspection_helper.get_valid_worker_ids(self._children)

    def _group_tools_by_toolkit(
        self, tool_dict: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """Delegate tool grouping to introspection helper."""
        return self.introspection_helper.group_tools_by_toolkit(tool_dict)

    # ========== Logger Delegation ==========

    def get_workforce_logs(self) -> Dict[str, Any]:
        """Delegate workforce logs to logger wrapper."""
        return self.logger_wrapper.get_workforce_logs()

    def get_workforce_log_tree(self) -> str:
        """Delegate workforce log tree to logger wrapper."""
        return self.logger_wrapper.get_workforce_log_tree()

    def get_workforce_kpis(self) -> Dict[str, Any]:
        """Delegate workforce KPIs to logger wrapper."""
        return self.logger_wrapper.get_workforce_kpis()

    def dump_workforce_logs(self, file_path: str) -> None:
        """Delegate log dumping to logger wrapper."""
        self.logger_wrapper.dump_workforce_logs(file_path)

    # ========== In-Flight Tracking Delegation ==========

    def _increment_in_flight_tasks(self, task_id: str) -> int:
        """Delegate in-flight task increment to tracker."""
        self._in_flight_tasks = (
            self.in_flight_tracker.increment_in_flight_tasks(
                self._in_flight_tasks, task_id
            )
        )
        return self._in_flight_tasks

    def _decrement_in_flight_tasks(
        self, task_id: str, context: str = ""
    ) -> int:
        """Delegate in-flight task decrement to tracker."""
        self._in_flight_tasks = (
            self.in_flight_tracker.decrement_in_flight_tasks(
                self._in_flight_tasks, task_id, context
            )
        )
        return self._in_flight_tasks

    def _cleanup_task_tracking(self, task_id: str) -> None:
        """Delegate task tracking cleanup to tracker."""
        self._task_start_times, self._task_dependencies, self._assignees = (
            self.in_flight_tracker.cleanup_task_tracking(
                task_id,
                self._task_start_times,
                self._task_dependencies,
                self._assignees,
            )
        )

    # ========== Failure Analysis Delegation ==========

    def _analyze_failure(
        self,
        task: Task,
        error_message: str,
        task_agent: Any,
        structured_handler: Any = None,
        use_structured: bool = True,
    ) -> RecoveryDecision:
        """Delegate failure analysis to failure analyzer."""
        return self.failure_analyzer.analyze_failure(
            task, error_message, task_agent, structured_handler, use_structured
        )

    # ========== Dependency Management Delegation ==========

    def _update_dependencies_for_decomposition(
        self, original_task: Task, subtasks: List[Task]
    ) -> None:
        """Delegate dependency updates to dependency manager."""
        self.dependency_manager.update_dependencies_for_decomposition(
            original_task, subtasks
        )

    def _decompose_task(
        self, task: Task
    ) -> Union[List[Task], Generator[List[Task], None, None]]:
        """Decompose the task into subtasks."""
        return self.failure_analyzer.decompose_task(
            task,
            self.task_agent,
            self._get_child_nodes_info(),
            self._update_dependencies_for_decomposition,
        )

    def _find_task_by_id(self, task_id: str) -> Optional[Task]:
        """Find a task by its ID in pending or completed tasks."""
        # Check pending tasks
        pending_task = find_task_by_id(list(self._pending_tasks), task_id)
        if pending_task:
            return pending_task

        # Check completed tasks
        completed_task = find_task_by_id(self._completed_tasks, task_id)
        if completed_task:
            return completed_task

        return None

    async def _post_dependency(self, dependency: Task) -> None:
        """Post a dependency to the channel."""
        await self.channel_communication.post_dependency(
            dependency, self._channel, self.node_id
        )

    def __repr__(self):
        return (
            f"WorkforceCore {self.node_id} ({self.description}) - "
            f"State: {self._state.value}"
        )
