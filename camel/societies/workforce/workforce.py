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
import time
import uuid
from collections import deque
from enum import Enum
from typing import Any, Coroutine, Deque, Dict, List, Optional

from colorama import Fore

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce.base import BaseNode
from camel.societies.workforce.prompts import (
    ASSIGN_TASK_PROMPT,
    CREATE_NODE_PROMPT,
    WF_TASK_DECOMPOSE_PROMPT,
)
from camel.societies.workforce.role_playing_worker import RolePlayingWorker
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import (
    TaskAssignResult,
    WorkerConf,
    check_if_running,
)
from camel.societies.workforce.worker import Worker
from camel.tasks.task import Task, TaskState, validate_task_content
from camel.toolkits import (
    CodeExecutionToolkit,
    SearchToolkit,
    TaskPlanningToolkit,
    ThinkingToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.utils import dependencies_required

from .workforce_logger import WorkforceLogger

logger = get_logger(__name__)


class WorkforceState(Enum):
    r"""Workforce execution state for human intervention support."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class WorkforceSnapshot:
    r"""Snapshot of workforce state for resuming execution."""

    def __init__(
        self,
        main_task: Optional[Task] = None,
        pending_tasks: Optional[Deque[Task]] = None,
        completed_tasks: Optional[List[Task]] = None,
        task_dependencies: Optional[Dict[str, List[str]]] = None,
        assignees: Optional[Dict[str, str]] = None,
        current_task_index: int = 0,
        description: str = "",
    ):
        self.main_task = main_task
        self.pending_tasks = pending_tasks.copy() if pending_tasks else deque()
        self.completed_tasks = (
            completed_tasks.copy() if completed_tasks else []
        )
        self.task_dependencies = (
            task_dependencies.copy() if task_dependencies else {}
        )
        self.assignees = assignees.copy() if assignees else {}
        self.current_task_index = current_task_index
        self.description = description
        self.timestamp = time.time()


class Workforce(BaseNode):
    r"""A system where multiple worker nodes (agents) cooperate together
    to solve tasks. It can assign tasks to worker nodes and also take
    strategies such as create new worker, decompose tasks, etc. to handle
    situations when the task fails.

    The workforce uses three specialized ChatAgents internally:
    - Coordinator Agent: Assigns tasks to workers based on their
      capabilities
    - Task Planner Agent: Decomposes complex tasks and composes results
    - Dynamic Workers: Created at runtime when tasks fail repeatedly

    Args:
        description (str): Description of the workforce.
        children (Optional[List[BaseNode]], optional): List of child nodes
            under this node. Each child node can be a worker node or
            another workforce node. (default: :obj:`None`)
        coordinator_agent_kwargs (Optional[Dict], optional): Keyword
            arguments passed directly to the coordinator :obj:`ChatAgent`
            constructor. The coordinator manages task assignment and failure
            handling strategies. See :obj:`ChatAgent` documentation
            for all available parameters.
            (default: :obj:`None` - uses ModelPlatformType.DEFAULT,
            ModelType.DEFAULT)
        task_agent_kwargs (Optional[Dict], optional): Keyword arguments
            passed directly to the task planning :obj:`ChatAgent` constructor.
            The task agent handles task decomposition into subtasks and result
            composition. See :obj:`ChatAgent` documentation for all
            available parameters.
            (default: :obj:`None` - uses ModelPlatformType.DEFAULT,
            ModelType.DEFAULT)
        new_worker_agent_kwargs (Optional[Dict], optional): Default keyword
            arguments passed to :obj:`ChatAgent` constructor for workers
            created dynamically at runtime when existing workers cannot handle
            failed tasks. See :obj:`ChatAgent` documentation for all
            available parameters.
            (default: :obj:`None` - creates workers with SearchToolkit,
            CodeExecutionToolkit, and ThinkingToolkit)
        graceful_shutdown_timeout (float, optional): The timeout in seconds
            for graceful shutdown when a task fails 3 times. During this
            period, the workforce remains active for debugging.
            Set to 0 for immediate shutdown. (default: :obj:`15.0`)
        share_memory (bool, optional): Whether to enable shared memory across
            SingleAgentWorker instances in the workforce. When enabled, all
            SingleAgentWorker instances, coordinator agent, and task planning
            agent will share their complete conversation history and
            function-calling trajectory, providing better context for task
            handoffs and continuity. Note: Currently only supports
            SingleAgentWorker instances; RolePlayingWorker and nested
            Workforce instances do not participate in memory sharing.
            (default: :obj:`False`)

    Example:
        >>> # Configure with custom model and shared memory
        >>> import asyncio
        >>> model = ModelFactory.create(
        ...     ModelPlatformType.OPENAI, ModelType.GPT_4O
        ... )
        >>> workforce = Workforce(
        ...     "Research Team",
        ...     coordinator_agent_kwargs={"model": model, "token_limit": 4000},
        ...     task_agent_kwargs={"model": model, "token_limit": 8000},
        ...     share_memory=True  # Enable shared memory
        ... )
        >>>
        >>> # Process a task
        >>> async def main():
        ...     task = Task(content="Research AI trends", id="1")
        ...     result = workforce.process_task(task)
        ...     return result
        >>> asyncio.run(main())
    """

    def __init__(
        self,
        description: str,
        children: Optional[List[BaseNode]] = None,
        coordinator_agent_kwargs: Optional[Dict] = None,
        task_agent_kwargs: Optional[Dict] = None,
        new_worker_agent_kwargs: Optional[Dict] = None,
        graceful_shutdown_timeout: float = 15.0,
        share_memory: bool = False,
    ) -> None:
        super().__init__(description)
        self._child_listening_tasks: Deque[asyncio.Task] = deque()
        self._children = children or []
        self.new_worker_agent_kwargs = new_worker_agent_kwargs
        self.graceful_shutdown_timeout = graceful_shutdown_timeout
        self.share_memory = share_memory
        self.metrics_logger = WorkforceLogger(workforce_id=self.node_id)
        self._task: Optional[Task] = None
        self._pending_tasks: Deque[Task] = deque()
        self._task_dependencies: Dict[str, List[str]] = {}
        self._assignees: Dict[str, str] = {}
        self._in_flight_tasks: int = 0
        # Dictionary to track task start times
        self._task_start_times: Dict[str, float] = {}
        # Human intervention support
        self._state = WorkforceState.IDLE
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initially not paused
        self._stop_requested = False
        self._snapshots: List[WorkforceSnapshot] = []
        self._completed_tasks: List[Task] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._main_task_future: Optional[asyncio.Future] = None
        # Snapshot throttle support
        self._last_snapshot_time: float = 0.0
        # Minimum seconds between automatic snapshots
        self.snapshot_interval: float = 30.0
        if self.metrics_logger:
            for child in self._children:
                worker_type = type(child).__name__
                role_or_desc = child.description
                self.metrics_logger.log_worker_created(
                    worker_id=child.node_id,
                    worker_type=worker_type,
                    role=role_or_desc,
                )

        # Warning messages for default model usage
        if coordinator_agent_kwargs is None:
            logger.warning(
                "No coordinator_agent_kwargs provided. Using default "
                "ChatAgent settings (ModelPlatformType.DEFAULT, "
                "ModelType.DEFAULT). To customize the coordinator agent "
                "that assigns tasks and handles failures, pass a dictionary "
                "with ChatAgent parameters, e.g.: {'model': your_model, "
                "'tools': your_tools, 'token_limit': 8000}. See ChatAgent "
                "documentation for all available options."
            )
        if task_agent_kwargs is None:
            logger.warning(
                "No task_agent_kwargs provided. Using default ChatAgent "
                "settings (ModelPlatformType.DEFAULT, ModelType.DEFAULT). "
                "To customize the task planning agent that "
                "decomposes/composes tasks, pass a dictionary with "
                "ChatAgent parameters, e.g.: {'model': your_model, "
                "'token_limit': 16000}. See ChatAgent documentation for "
                "all available options."
            )
        if new_worker_agent_kwargs is None:
            logger.warning(
                "No new_worker_agent_kwargs provided. Workers created at "
                "runtime will use default ChatAgent settings with "
                "SearchToolkit, CodeExecutionToolkit, and ThinkingToolkit. "
                "To customize runtime worker creation, pass a dictionary "
                "with ChatAgent parameters, e.g.: {'model': your_model, "
                "'tools': your_tools}. See ChatAgent documentation for all "
                "available options."
            )

        if self.share_memory:
            logger.info(
                "Shared memory enabled. All agents will share their complete "
                "conversation history and function-calling trajectory for "
                "better context continuity during task handoffs."
            )

        coord_agent_sys_msg = BaseMessage.make_assistant_message(
            role_name="Workforce Manager",
            content="You are coordinating a group of workers. A worker can be "
            "a group of agents or a single agent. Each worker is "
            "created to solve a specific kind of task. Your job "
            "includes assigning tasks to a existing worker, creating "
            "a new worker for a task, etc.",
        )
        self.coordinator_agent = ChatAgent(
            coord_agent_sys_msg,
            **(coordinator_agent_kwargs or {}),
        )

        task_sys_msg = BaseMessage.make_assistant_message(
            role_name="Task Planner",
            content="You are going to compose and decompose tasks. Keep "
            "tasks that are sequential and require the same type of "
            "agent together in one agent process. Only decompose tasks "
            "that can be handled in parallel and require different types "
            "of agents. This ensures efficient execution by minimizing "
            "context switching between agents.",
        )
        _task_agent_kwargs = dict(task_agent_kwargs or {})
        extra_tools = TaskPlanningToolkit().get_tools()
        _task_agent_kwargs["tools"] = [
            *_task_agent_kwargs.get("tools", []),
            *extra_tools,
        ]
        self.task_agent = ChatAgent(task_sys_msg, **_task_agent_kwargs)

    def __repr__(self):
        return (
            f"Workforce {self.node_id} ({self.description}) - "
            f"State: {self._state.value}"
        )

    def _collect_shared_memory(self) -> Dict[str, List]:
        r"""Collect memory from all SingleAgentWorker instances for sharing.

        Returns:
            Dict[str, List]: A dictionary mapping agent types to their memory
                records. Contains entries for 'coordinator', 'task_agent',
                and 'workers'.
        """
        # TODO: add memory collection for RolePlayingWorker and nested
        # Workforce instances
        if not self.share_memory:
            return {}

        shared_memory: Dict[str, List] = {
            'coordinator': [],
            'task_agent': [],
            'workers': [],
        }

        try:
            # Collect coordinator agent memory
            coord_records = self.coordinator_agent.memory.retrieve()
            shared_memory['coordinator'] = [
                record.memory_record.to_dict() for record in coord_records
            ]

            # Collect task agent memory
            task_records = self.task_agent.memory.retrieve()
            shared_memory['task_agent'] = [
                record.memory_record.to_dict() for record in task_records
            ]

            # Collect worker memory only from SingleAgentWorker instances
            for child in self._children:
                if isinstance(child, SingleAgentWorker):
                    worker_records = child.worker.memory.retrieve()
                    worker_memory = [
                        record.memory_record.to_dict()
                        for record in worker_records
                    ]
                    shared_memory['workers'].extend(worker_memory)

        except Exception as e:
            logger.warning(f"Error collecting shared memory: {e}")

        return shared_memory

    def _share_memory_with_agents(
        self, shared_memory: Dict[str, List]
    ) -> None:
        r"""Share collected memory with coordinator, task agent, and
        SingleAgentWorker instances.

        Args:
            shared_memory (Dict[str, List]): Memory records collected from
                all agents to be shared.
        """
        if not self.share_memory or not shared_memory:
            return

        try:
            # Create a consolidated memory from all collected records
            all_records = []
            for _memory_type, records in shared_memory.items():
                all_records.extend(records)

            if not all_records:
                return

            # Import necessary classes for memory record reconstruction
            from camel.memories.records import MemoryRecord

            # Create consolidated memory objects from records
            memory_records: List[MemoryRecord] = []
            for record_dict in all_records:
                try:
                    memory_record = MemoryRecord.from_dict(record_dict)
                    memory_records.append(memory_record)
                except Exception as e:
                    logger.warning(f"Failed to reconstruct memory record: {e}")
                    continue

            if not memory_records:
                return

            # Share with coordinator agent
            for record in memory_records:
                # Only add records from other agents to avoid duplication
                if record.agent_id != self.coordinator_agent.agent_id:
                    self.coordinator_agent.memory.write_record(record)

            # Share with task agent
            for record in memory_records:
                if record.agent_id != self.task_agent.agent_id:
                    self.task_agent.memory.write_record(record)

            # Share with SingleAgentWorker instances only
            single_agent_workers = [
                child
                for child in self._children
                if isinstance(child, SingleAgentWorker)
            ]

            for worker in single_agent_workers:
                for record in memory_records:
                    if record.agent_id != worker.worker.agent_id:
                        worker.worker.memory.write_record(record)

            logger.info(
                f"Shared {len(memory_records)} memory records across "
                f"{len(single_agent_workers) + 2} agents in workforce "
                f"{self.node_id}"
            )

        except Exception as e:
            logger.warning(f"Error sharing memory with agents: {e}")

    def _sync_shared_memory(self) -> None:
        r"""Synchronize memory across all agents by collecting and sharing."""
        if not self.share_memory:
            return

        try:
            shared_memory = self._collect_shared_memory()
            self._share_memory_with_agents(shared_memory)
        except Exception as e:
            logger.warning(f"Error synchronizing shared memory: {e}")

    def _decompose_task(self, task: Task) -> List[Task]:
        r"""Decompose the task into subtasks. This method will also set the
        relationship between the task and its subtasks.

        Returns:
            List[Task]: The subtasks.
        """
        decompose_prompt = WF_TASK_DECOMPOSE_PROMPT.format(
            content=task.content,
            child_nodes_info=self._get_child_nodes_info(),
            additional_info=task.additional_info,
        )
        self.task_agent.reset()
        subtasks = task.decompose(self.task_agent, decompose_prompt)
        task.subtasks = subtasks
        for subtask in subtasks:
            subtask.parent = task

        return subtasks

    # Human intervention methods
    async def _async_pause(self) -> None:
        r"""Async implementation of pause to run on the event loop."""
        if self._state == WorkforceState.RUNNING:
            self._state = WorkforceState.PAUSED
            self._pause_event.clear()
            logger.info(f"Workforce {self.node_id} paused.")

    def pause(self) -> None:
        r"""Pause the workforce execution.
        If the internal event-loop is already running we schedule the
        asynchronous pause coroutine onto it.  When the loop has not yet
        been created (e.g. the caller presses the hot-key immediately after
        workforce start-up) we fall back to a synchronous state change so
        that no tasks will be scheduled until the loop is ready.
        """

        if self._loop and not self._loop.is_closed():
            self._submit_coro_to_loop(self._async_pause())
        else:
            # Loop not yet created, just mark state so when loop starts it
            # will proceed.
            if self._state == WorkforceState.RUNNING:
                self._state = WorkforceState.PAUSED
                self._pause_event.clear()
                logger.info(
                    f"Workforce {self.node_id} paused "
                    f"(event-loop not yet started)."
                )

    async def _async_resume(self) -> None:
        r"""Async implementation of resume to run on the event loop."""
        if self._state == WorkforceState.PAUSED:
            self._state = WorkforceState.RUNNING
            self._pause_event.set()
            logger.info(f"Workforce {self.node_id} resumed.")

            # Re-post ready tasks (if any)
            if self._pending_tasks:
                await self._post_ready_tasks()

    def resume(self) -> None:
        r"""Resume execution after a manual pause."""

        if self._loop and not self._loop.is_closed():
            self._submit_coro_to_loop(self._async_resume())
        else:
            # Loop not running yet, just mark state so when loop starts it
            # will proceed.
            if self._state == WorkforceState.PAUSED:
                self._state = WorkforceState.RUNNING
                self._pause_event.set()
                logger.info(
                    f"Workforce {self.node_id} resumed "
                    f"(event-loop not yet started)."
                )

    async def _async_stop_gracefully(self) -> None:
        r"""Async implementation of stop_gracefully to run on the event
        loop.
        """
        self._stop_requested = True
        if self._pause_event.is_set() is False:
            self._pause_event.set()  # Resume if paused to process stop
        logger.info(f"Workforce {self.node_id} stop requested.")

    def stop_gracefully(self) -> None:
        r"""Request workforce to finish current in-flight work then halt.

        Works both when the internal event-loop is alive and when it has not
        yet been started.  In the latter case we simply mark the stop flag so
        that the loop (when it eventually starts) will exit immediately after
        initialisation.
        """

        if self._loop and not self._loop.is_closed():
            self._submit_coro_to_loop(self._async_stop_gracefully())
        else:
            # Loop not yet created, set the flag synchronously so later
            # startup will respect it.
            self._stop_requested = True
            # Ensure any pending pause is released so that when the loop does
            # start it can see the stop request and exit.
            self._pause_event.set()
            logger.info(
                f"Workforce {self.node_id} stop requested "
                f"(event-loop not yet started)."
            )

    def save_snapshot(self, description: str = "") -> None:
        r"""Save current state as a snapshot."""
        snapshot = WorkforceSnapshot(
            main_task=self._task,
            pending_tasks=self._pending_tasks,
            completed_tasks=self._completed_tasks,
            task_dependencies=self._task_dependencies,
            assignees=self._assignees,
            current_task_index=len(self._completed_tasks),
            description=description or f"Snapshot at {time.time()}",
        )
        self._snapshots.append(snapshot)
        logger.info(f"Snapshot saved: {description}")

    def list_snapshots(self) -> List[str]:
        r"""List all available snapshots."""
        snapshots_info = []
        for i, snapshot in enumerate(self._snapshots):
            desc_part = (
                f" - {snapshot.description}" if snapshot.description else ""
            )
            info = (
                f"Snapshot {i}: {len(snapshot.completed_tasks)} completed, "
                f"{len(snapshot.pending_tasks)} pending{desc_part}"
            )
            snapshots_info.append(info)
        return snapshots_info

    def get_pending_tasks(self) -> List[Task]:
        r"""Get current pending tasks for human review."""
        return list(self._pending_tasks)

    def get_completed_tasks(self) -> List[Task]:
        r"""Get completed tasks."""
        return self._completed_tasks.copy()

    def modify_task_content(self, task_id: str, new_content: str) -> bool:
        r"""Modify the content of a pending task."""
        # Validate the new content first
        if not validate_task_content(new_content, task_id):
            logger.warning(
                f"Task {task_id} content modification rejected: "
                f"Invalid content. Content preview: '{new_content[:50]}...'"
            )
            return False

        for task in self._pending_tasks:
            if task.id == task_id:
                task.content = new_content
                logger.info(f"Task {task_id} content modified.")
                return True
        logger.warning(f"Task {task_id} not found in pending tasks.")
        return False

    def add_task(
        self,
        content: str,
        task_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        insert_position: int = -1,
    ) -> Task:
        r"""Add a new task to the pending queue."""
        new_task = Task(
            content=content,
            id=task_id or f"human_added_{len(self._pending_tasks)}",
            additional_info=additional_info,
        )
        if insert_position == -1:
            self._pending_tasks.append(new_task)
        else:
            # Convert deque to list, insert, then back to deque
            tasks_list = list(self._pending_tasks)
            tasks_list.insert(insert_position, new_task)
            self._pending_tasks = deque(tasks_list)

        logger.info(f"New task added: {new_task.id}")
        return new_task

    def remove_task(self, task_id: str) -> bool:
        r"""Remove a task from the pending queue."""
        # Convert to list to find and remove
        tasks_list = list(self._pending_tasks)
        for i, task in enumerate(tasks_list):
            if task.id == task_id:
                tasks_list.pop(i)
                self._pending_tasks = deque(tasks_list)
                logger.info(f"Task {task_id} removed.")
                return True
        logger.warning(f"Task {task_id} not found in pending tasks.")
        return False

    def reorder_tasks(self, task_ids: List[str]) -> bool:
        r"""Reorder pending tasks according to the provided task IDs list."""
        # Create a mapping of task_id to task
        tasks_dict = {task.id: task for task in self._pending_tasks}

        # Check if all provided IDs exist
        if not all(task_id in tasks_dict for task_id in task_ids):
            logger.warning("Some task IDs not found in pending tasks.")
            return False

        # Check if we have the same number of tasks
        if len(task_ids) != len(self._pending_tasks):
            logger.warning(
                "Number of task IDs doesn't match pending tasks count."
            )
            return False

        # Reorder tasks
        reordered_tasks = deque([tasks_dict[task_id] for task_id in task_ids])
        self._pending_tasks = reordered_tasks

        logger.info("Tasks reordered successfully.")
        return True

    def resume_from_task(self, task_id: str) -> bool:
        r"""Resume execution from a specific task."""
        if self._state != WorkforceState.PAUSED:
            logger.warning(
                "Workforce must be paused to resume from specific task."
            )
            return False

        # Find the task in pending tasks
        tasks_list = list(self._pending_tasks)
        target_index = -1

        for i, task in enumerate(tasks_list):
            if task.id == task_id:
                target_index = i
                break

        if target_index == -1:
            logger.warning(f"Task {task_id} not found in pending tasks.")
            return False

        # Move completed tasks that come after the target task back to pending
        tasks_to_move_back = tasks_list[:target_index]
        remaining_tasks = tasks_list[target_index:]

        # Update pending tasks to start from the target task
        self._pending_tasks = deque(remaining_tasks)

        # Move previously "completed" tasks that are after target back to
        # pending and reset their state
        if tasks_to_move_back:
            # Reset state for tasks being moved back to pending
            for task in tasks_to_move_back:
                # Handle all possible task states
                if task.state in [TaskState.DONE, TaskState.OPEN]:
                    task.state = TaskState.FAILED  # TODO: Add logic for OPEN
                    # Clear result to avoid confusion
                    task.result = None
                    # Reset failure count to give task a fresh start
                    task.failure_count = 0

            logger.info(
                f"Moving {len(tasks_to_move_back)} tasks back to pending "
                f"state."
            )

        logger.info(f"Ready to resume from task: {task_id}")
        return True

    def restore_from_snapshot(self, snapshot_index: int) -> bool:
        r"""Restore workforce state from a snapshot."""
        if not (0 <= snapshot_index < len(self._snapshots)):
            logger.warning(f"Invalid snapshot index: {snapshot_index}")
            return False

        if self._state == WorkforceState.RUNNING:
            logger.warning(
                "Cannot restore snapshot while workforce is running. "
                "Pause first."
            )
            return False

        snapshot = self._snapshots[snapshot_index]
        self._task = snapshot.main_task
        self._pending_tasks = snapshot.pending_tasks.copy()
        self._completed_tasks = snapshot.completed_tasks.copy()
        self._task_dependencies = snapshot.task_dependencies.copy()
        self._assignees = snapshot.assignees.copy()

        logger.info(f"Workforce state restored from snapshot {snapshot_index}")
        return True

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
                f"Content preview: '{task.content[:50]}...'"
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
        subtasks = self._decompose_task(task)
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
            >>> workforce = Workforce("My Team")
            >>> task = Task(content="Analyze data", id="1")
            >>> result = workforce.process_task(task)  # No async/await
            needed
            >>> print(result.result)
        """
        import asyncio
        import concurrent.futures

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
                f"Content preview: '{task.content[:50]}...'"
            )
            return task

        self.reset()
        self._task = task
        self._state = WorkforceState.RUNNING
        task.state = TaskState.FAILED  # TODO: Add logic for OPEN
        self._pending_tasks.append(task)

        # Decompose the task into subtasks first
        subtasks = self._decompose_task(task)
        self._pending_tasks.extendleft(reversed(subtasks))
        self.set_channel(TaskChannel())

        # Save initial snapshot
        self.save_snapshot("Initial task decomposition")

        try:
            await self.start()
        except Exception as e:
            logger.error(f"Error in workforce execution: {e}")
            self._state = WorkforceState.STOPPED
            raise
        finally:
            if self._state != WorkforceState.STOPPED:
                self._state = WorkforceState.IDLE

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
        self.resume()

        try:
            # Continue the existing async task
            remaining_task = self._loop.run_until_complete(
                self._continue_execution()
            )
            return remaining_task
        except Exception as e:
            logger.error(f"Error continuing execution: {e}")
            self._state = WorkforceState.STOPPED
            return None

    async def _continue_execution(self) -> Optional[Task]:
        r"""Internal method to continue execution after pause."""
        try:
            await self._listen_to_channel()
        except Exception as e:
            logger.error(f"Error in continued execution: {e}")
            self._state = WorkforceState.STOPPED
            raise
        finally:
            if self._state != WorkforceState.STOPPED:
                self._state = WorkforceState.IDLE

        return self._task

    @check_if_running(False)
    def add_single_agent_worker(
        self,
        description: str,
        worker: ChatAgent,
        pool_max_size: int = 10,
    ) -> Workforce:
        r"""Add a worker node to the workforce that uses a single agent.

        Args:
            description (str): Description of the worker node.
            worker (ChatAgent): The agent to be added.
            pool_max_size (int): Maximum size of the agent pool.
                (default: :obj:`10`)

        Returns:
            Workforce: The workforce node itself.
        """
        worker_node = SingleAgentWorker(
            description=description,
            worker=worker,
            pool_max_size=pool_max_size,
        )
        self._children.append(worker_node)
        if self.metrics_logger:
            self.metrics_logger.log_worker_created(
                worker_id=worker_node.node_id,
                worker_type='SingleAgentWorker',
                role=worker_node.description,
            )
        return self

    @check_if_running(False)
    def add_role_playing_worker(
        self,
        description: str,
        assistant_role_name: str,
        user_role_name: str,
        assistant_agent_kwargs: Optional[Dict] = None,
        user_agent_kwargs: Optional[Dict] = None,
        summarize_agent_kwargs: Optional[Dict] = None,
        chat_turn_limit: int = 3,
    ) -> Workforce:
        r"""Add a worker node to the workforce that uses `RolePlaying` system.

        Args:
            description (str): Description of the node.
            assistant_role_name (str): The role name of the assistant agent.
            user_role_name (str): The role name of the user agent.
            assistant_agent_kwargs (Optional[Dict]): The keyword arguments to
                initialize the assistant agent in the role playing, like the
                model name, etc. (default: :obj:`None`)
            user_agent_kwargs (Optional[Dict]): The keyword arguments to
                initialize the user agent in the role playing, like the
                model name, etc. (default: :obj:`None`)
            summarize_agent_kwargs (Optional[Dict]): The keyword arguments to
                initialize the summarize agent, like the model name, etc.
                (default: :obj:`None`)
            chat_turn_limit (int): The maximum number of chat turns in the
                role playing. (default: :obj:`3`)

        Returns:
            Workforce: The workforce node itself.
        """
        worker_node = RolePlayingWorker(
            description=description,
            assistant_role_name=assistant_role_name,
            user_role_name=user_role_name,
            assistant_agent_kwargs=assistant_agent_kwargs,
            user_agent_kwargs=user_agent_kwargs,
            summarize_agent_kwargs=summarize_agent_kwargs,
            chat_turn_limit=chat_turn_limit,
        )
        self._children.append(worker_node)
        if self.metrics_logger:
            self.metrics_logger.log_worker_created(
                worker_id=worker_node.node_id,
                worker_type='RolePlayingWorker',
                role=worker_node.description,
            )
        return self

    @check_if_running(False)
    def add_workforce(self, workforce: Workforce) -> Workforce:
        r"""Add a workforce node to the workforce.

        Args:
            workforce (Workforce): The workforce node to be added.

        Returns:
            Workforce: The workforce node itself.
        """
        self._children.append(workforce)
        return self

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
        self._stop_requested = False
        # Handle asyncio.Event in a thread-safe way
        if self._loop and not self._loop.is_closed():
            # If we have a loop, use it to set the event safely
            asyncio.run_coroutine_threadsafe(
                self._async_reset(), self._loop
            ).result()
        else:
            try:
                self._reset_task = asyncio.create_task(self._async_reset())
            except RuntimeError:
                asyncio.run(self._async_reset())

        if hasattr(self, 'logger') and self.metrics_logger is not None:
            self.metrics_logger.reset_task_data()
        else:
            self.metrics_logger = WorkforceLogger(workforce_id=self.node_id)

    @check_if_running(False)
    def set_channel(self, channel: TaskChannel) -> None:
        r"""Set the channel for the node and all the child nodes under it."""
        self._channel = channel
        for child in self._children:
            child.set_channel(channel)

    def _get_child_nodes_info(self) -> str:
        r"""Get the information of all the child nodes under this node."""
        info = ""
        for child in self._children:
            if isinstance(child, Workforce):
                additional_info = "A Workforce node"
            elif isinstance(child, SingleAgentWorker):
                additional_info = "tools: " + (
                    ", ".join(child.worker.tool_dict.keys())
                )
            elif isinstance(child, RolePlayingWorker):
                additional_info = "A Role playing node"
            else:
                additional_info = "Unknown node"
            info += (
                f"<{child.node_id}>:<{child.description}>:<"
                f"{additional_info}>\n"
            )
        return info

    def _find_assignee(
        self,
        tasks: List[Task],
    ) -> TaskAssignResult:
        r"""Assigns multiple tasks to worker nodes with the best capabilities.

        Parameters:
            tasks (List[Task]): The tasks to be assigned.

        Returns:
            TaskAssignResult: Assignment result containing task assignments
                with their dependencies.
        """
        self.coordinator_agent.reset()

        # Format tasks information for the prompt
        tasks_info = ""
        for task in tasks:
            tasks_info += f"Task ID: {task.id}\n"
            tasks_info += f"Content: {task.content}\n"
            if task.additional_info:
                tasks_info += f"Additional Info: {task.additional_info}\n"
            tasks_info += "---\n"

        prompt = ASSIGN_TASK_PROMPT.format(
            tasks_info=tasks_info,
            child_nodes_info=self._get_child_nodes_info(),
        )

        logger.debug(
            f"Sending batch assignment request to coordinator "
            f"for {len(tasks)} tasks."
        )

        response = self.coordinator_agent.step(
            prompt, response_format=TaskAssignResult
        )
        if response.msg is None or response.msg.content is None:
            logger.error(
                "Coordinator agent returned empty response for task assignment"
            )
            # Return empty result as fallback
            return TaskAssignResult(assignments=[])

        result_dict = json.loads(response.msg.content, parse_int=str)
        task_assign_result = TaskAssignResult(**result_dict)
        return task_assign_result

    async def _post_task(self, task: Task, assignee_id: str) -> None:
        # Record the start time when a task is posted
        self._task_start_times[task.id] = time.time()

        if self.metrics_logger:
            self.metrics_logger.log_task_started(
                task_id=task.id, worker_id=assignee_id
            )
        self._in_flight_tasks += 1
        await self._channel.post_task(task, self.node_id, assignee_id)

    async def _post_dependency(self, dependency: Task) -> None:
        await self._channel.post_dependency(dependency, self.node_id)

    def _create_worker_node_for_task(self, task: Task) -> Worker:
        r"""Creates a new worker node for a given task and add it to the
        children list of this node. This is one of the actions that
        the coordinator can take when a task has failed.

        Args:
            task (Task): The task for which the worker node is created.

        Returns:
            Worker: The created worker node.
        """
        prompt = CREATE_NODE_PROMPT.format(
            content=task.content,
            child_nodes_info=self._get_child_nodes_info(),
            additional_info=task.additional_info,
        )
        response = self.coordinator_agent.step(
            prompt, response_format=WorkerConf
        )
        if response.msg is None or response.msg.content is None:
            logger.error(
                "Coordinator agent returned empty response for worker creation"
            )
            # Create a fallback worker configuration
            new_node_conf = WorkerConf(
                description=f"Fallback worker for "
                f"task: {task.content[:50]}...",
                role="General Assistant",
                sys_msg="You are a general assistant that can help "
                "with various tasks.",
            )
        else:
            result_dict = json.loads(response.msg.content)
            new_node_conf = WorkerConf(**result_dict)

        new_agent = self._create_new_agent(
            new_node_conf.role,
            new_node_conf.sys_msg,
        )

        new_node = SingleAgentWorker(
            description=new_node_conf.description,
            worker=new_agent,
            pool_max_size=10,  # TODO: make this configurable
        )
        new_node.set_channel(self._channel)

        print(f"{Fore.CYAN}{new_node} created.{Fore.RESET}")

        self._children.append(new_node)
        if self.metrics_logger:
            self.metrics_logger.log_worker_created(
                worker_id=new_node.node_id,
                worker_type='SingleAgentWorker',
                role=new_node_conf.role,
                metadata={'description': new_node_conf.description},
            )
        self._child_listening_tasks.append(
            asyncio.create_task(new_node.start())
        )
        return new_node

    def _create_new_agent(self, role: str, sys_msg: str) -> ChatAgent:
        worker_sys_msg = BaseMessage.make_assistant_message(
            role_name=role,
            content=sys_msg,
        )

        if self.new_worker_agent_kwargs is not None:
            return ChatAgent(worker_sys_msg, **self.new_worker_agent_kwargs)

        # Default tools for a new agent
        function_list = [
            SearchToolkit().search_duckduckgo,
            *CodeExecutionToolkit().get_tools(),
            *ThinkingToolkit().get_tools(),
        ]

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict={"temperature": 0},
        )

        return ChatAgent(worker_sys_msg, model=model, tools=function_list)  # type: ignore[arg-type]

    async def _get_returned_task(self) -> Task:
        r"""Get the task that's published by this node and just get returned
        from the assignee. Includes timeout handling to prevent indefinite
        waiting.
        """
        try:
            # Add timeout to prevent indefinite waiting
            return await asyncio.wait_for(
                self._channel.get_returned_task_by_publisher(self.node_id),
                timeout=180.0,  # 3 minute timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Timeout waiting for returned task in "
                f"workforce {self.node_id}. "
                f"This may indicate an issue with async tool execution. "
                f"Current pending tasks: {len(self._pending_tasks)}, "
                f"In-flight tasks: {self._in_flight_tasks}"
            )
            raise

    async def _post_ready_tasks(self) -> None:
        r"""Checks for unassigned tasks, assigns them, and then posts any
        tasks whose dependencies have been met."""

        # Step 1: Identify and assign any new tasks in the pending queue
        tasks_to_assign = [
            task
            for task in self._pending_tasks
            if task.id not in self._task_dependencies
        ]
        if tasks_to_assign:
            logger.debug(
                f"Found {len(tasks_to_assign)} new tasks. "
                f"Requesting assignment..."
            )
            batch_result = self._find_assignee(tasks_to_assign)
            logger.debug(
                f"Coordinator returned assignments:\n"
                f"{json.dumps(batch_result.dict(), indent=2)}"
            )
            for assignment in batch_result.assignments:
                self._task_dependencies[assignment.task_id] = (
                    assignment.dependencies
                )
                self._assignees[assignment.task_id] = assignment.assignee_id
                if self.metrics_logger:
                    # queue_time_seconds can be derived by logger if task
                    # creation time is logged
                    self.metrics_logger.log_task_assigned(
                        task_id=assignment.task_id,
                        worker_id=assignment.assignee_id,
                        dependencies=assignment.dependencies,
                        queue_time_seconds=None,
                    )

        # Step 2: Iterate through all pending tasks and post those that are
        # ready
        posted_tasks = []
        for task in self._pending_tasks:
            # A task must be assigned to be considered for posting
            if task.id in self._task_dependencies:
                dependencies = self._task_dependencies[task.id]
                # Check if all dependencies for this task are in the completed
                # set
                if all(
                    dep_id in {t.id for t in self._completed_tasks}
                    for dep_id in dependencies
                ):
                    assignee_id = self._assignees[task.id]
                    logger.debug(
                        f"Posting task {task.id} to assignee {assignee_id}. "
                        f"Dependencies met."
                    )
                    await self._post_task(task, assignee_id)
                    posted_tasks.append(task)

        # Step 3: Remove the posted tasks from the pending list
        for task in posted_tasks:
            try:
                self._pending_tasks.remove(task)
            except ValueError:
                # Task might have been removed by another process, which is
                # fine
                pass

    async def _handle_failed_task(self, task: Task) -> bool:
        task.failure_count += 1

        if self.metrics_logger:
            worker_id = self._assignees.get(task.id)
            self.metrics_logger.log_task_failed(
                task_id=task.id,
                worker_id=worker_id,
                error_message=task.result or "Task execution failed",
                error_type="TaskFailure",
                metadata={'failure_count': task.failure_count},
            )

        if task.failure_count > 3:
            return True

        if task.get_depth() > 3:
            # Create a new worker node and reassign
            assignee = self._create_worker_node_for_task(task)

            # Sync shared memory after creating new worker to provide context
            if self.share_memory:
                logger.info(
                    f"Syncing shared memory after creating new worker "
                    f"{assignee.node_id} for failed task {task.id}"
                )
                self._sync_shared_memory()

            await self._post_task(task, assignee.node_id)
            action_taken = f"reassigned to new worker {assignee.node_id}"
        else:
            subtasks = self._decompose_task(task)
            if self.metrics_logger and subtasks:
                self.metrics_logger.log_task_decomposed(
                    parent_task_id=task.id,
                    subtask_ids=[st.id for st in subtasks],
                )
                for subtask in subtasks:
                    self.metrics_logger.log_task_created(
                        task_id=subtask.id,
                        description=subtask.content,
                        parent_task_id=task.id,
                        task_type=subtask.type,
                        metadata=subtask.additional_info,
                    )
            # Insert packets at the head of the queue
            self._pending_tasks.extendleft(reversed(subtasks))

            # Sync shared memory after task decomposition
            if self.share_memory:
                logger.info(
                    f"Syncing shared memory after decomposing failed "
                    f"task {task.id}"
                )
                self._sync_shared_memory()

            await self._post_ready_tasks()
            action_taken = f"decomposed into {len(subtasks)} subtasks"
        if task.id in self._assignees:
            await self._channel.archive_task(task.id)

        logger.debug(
            f"Task {task.id} failed and was {action_taken}. "
            f"Updating dependency state."
        )
        # Mark task as completed for dependency tracking
        self._completed_tasks.append(task)

        # Post next ready tasks

        # Sync shared memory after task completion to share knowledge
        if self.share_memory:
            logger.info(
                f"Syncing shared memory after task {task.id} completion"
            )
            self._sync_shared_memory()

        # Check if any pending tasks are now ready to execute
        await self._post_ready_tasks()
        return False

    async def _handle_completed_task(self, task: Task) -> None:
        if self.metrics_logger:
            worker_id = self._assignees.get(task.id, "unknown")
            processing_time_seconds = None
            token_usage = None

            # Get processing time from task start time or additional info
            if task.id in self._task_start_times:
                processing_time_seconds = (
                    time.time() - self._task_start_times[task.id]
                )
                del self._task_start_times[task.id]  # Prevent memory leaks
            elif (
                task.additional_info is not None
                and 'processing_time_seconds' in task.additional_info
            ):
                processing_time_seconds = task.additional_info[
                    'processing_time_seconds'
                ]

            # Get token usage from task additional info (preferred - actual
            # usage)
            if (
                task.additional_info is not None
                and 'token_usage' in task.additional_info
            ):
                token_usage = task.additional_info['token_usage']
            else:
                # Fallback: Try to get token usage from SingleAgentWorker
                # memory
                assignee_node = next(
                    (
                        child
                        for child in self._children
                        if child.node_id == worker_id
                    ),
                    None,
                )
                if isinstance(assignee_node, SingleAgentWorker):
                    try:
                        _, total_tokens = (
                            assignee_node.worker.memory.get_context()
                        )
                        token_usage = {'total_tokens': total_tokens}
                    except Exception:
                        token_usage = None

            # Log the completed task
            self.metrics_logger.log_task_completed(
                task_id=task.id,
                worker_id=worker_id,
                result_summary=task.result if task.result else "Completed",
                processing_time_seconds=processing_time_seconds,
                token_usage=token_usage,
                metadata={'current_state': task.state.value},
            )

        # Find and remove the completed task from pending tasks
        tasks_list = list(self._pending_tasks)
        found_and_removed = False

        for i, pending_task in enumerate(tasks_list):
            if pending_task.id == task.id:
                # Remove this specific task
                tasks_list.pop(i)
                self._pending_tasks = deque(tasks_list)
                found_and_removed = True
                print(
                    f"{Fore.GREEN}✅ Task {task.id} completed and removed "
                    f"from queue.{Fore.RESET}"
                )
                break

        if not found_and_removed:
            # Task was already removed from pending queue (expected case when
            # it had been popped immediately after posting).  No need to
            # draw user attention with a warning; record at debug level.
            logger.debug(
                f"Completed task {task.id} was already removed from pending "
                "queue."
            )

        # Archive the task and update dependency tracking
        if task.id in self._assignees:
            await self._channel.archive_task(task.id)

        # Ensure it's in completed tasks set
        self._completed_tasks.append(task)

        # Handle parent task completion logic
        parent = task.parent
        if parent and parent.id not in {t.id for t in self._completed_tasks}:
            all_subtasks_done = all(
                sub.id in {t.id for t in self._completed_tasks}
                for sub in parent.subtasks
            )
            if all_subtasks_done:
                # Set the parent task state to done
                parent.state = TaskState.DONE
                logger.debug(
                    f"All subtasks of {parent.id} are done. "
                    f"Marking parent as complete."
                )
                # Treat the parent task as a completed task to unblock
                # its dependents. Since it was never sent to a worker,
                # we call this method recursively.
                await self._handle_completed_task(parent)

        # Sync shared memory after task completion to share knowledge
        if self.share_memory:
            logger.info(
                f"Syncing shared memory after task {task.id} completion"
            )
            self._sync_shared_memory()

        # Check if any pending tasks are now ready to execute
        await self._post_ready_tasks()

    async def _graceful_shutdown(self, failed_task: Task) -> None:
        r"""Handle graceful shutdown with configurable timeout. This is used to
        keep the workforce running for a while to debug the failed task.

        Args:
            failed_task (Task): The task that failed and triggered shutdown.
        """
        if self.graceful_shutdown_timeout <= 0:
            # Immediate shutdown if timeout is 0 or negative
            return

        logger.warning(
            f"Workforce will shutdown in {self.graceful_shutdown_timeout} "
            f"seconds due to failure. You can use this time to inspect the "
            f"current state of the workforce."
        )
        # Wait for the full timeout period
        await asyncio.sleep(self.graceful_shutdown_timeout)

    def get_workforce_log_tree(self) -> str:
        r"""Returns an ASCII tree representation of the task hierarchy and
        worker status.
        """
        if not self.metrics_logger:
            return "Logger not initialized."
        return self.metrics_logger.get_ascii_tree_representation()

    def get_workforce_kpis(self) -> Dict[str, Any]:
        r"""Returns a dictionary of key performance indicators."""
        if not self.metrics_logger:
            return {"error": "Logger not initialized."}
        return self.metrics_logger.get_kpis()

    def dump_workforce_logs(self, file_path: str) -> None:
        r"""Dumps all collected logs to a JSON file.

        Args:
            file_path (str): The path to the JSON file.
        """
        if not self.metrics_logger:
            print("Logger not initialized. Cannot dump logs.")
            return
        self.metrics_logger.dump_to_json(file_path)
        # Use logger.info or print, consistent with existing style
        logger.info(f"Workforce logs dumped to {file_path}")

    @check_if_running(False)
    async def _listen_to_channel(self) -> None:
        r"""Continuously listen to the channel, post task to the channel and
        track the status of posted tasks. Now supports pause/resume and
        graceful stop.
        """

        self._running = True
        self._state = WorkforceState.RUNNING
        logger.info(f"Workforce {self.node_id} started.")

        await self._post_ready_tasks()

        while (
            self._task is None
            or self._pending_tasks
            or self._in_flight_tasks > 0
        ) and not self._stop_requested:
            try:
                # Check for pause request at the beginning of each loop
                # iteration
                await self._pause_event.wait()

                # Check for stop request after potential pause
                if self._stop_requested:
                    logger.info("Stop requested, breaking execution loop.")
                    break

                # Save snapshot before processing next task
                if self._pending_tasks:
                    current_task = self._pending_tasks[0]
                    # Throttled snapshot
                    if (
                        time.time() - self._last_snapshot_time
                        >= self.snapshot_interval
                    ):
                        self.save_snapshot(
                            f"Before processing task: {current_task.id}"
                        )
                        self._last_snapshot_time = time.time()

                # Get returned task (this may block until a task is returned)
                returned_task = await self._get_returned_task()
                self._in_flight_tasks -= 1

                # Check for stop request after getting task
                if self._stop_requested:
                    logger.info("Stop requested after receiving task.")
                    break

                # Process the returned task based on its state
                if returned_task.state == TaskState.DONE:
                    print(
                        f"{Fore.CYAN}🎯 Task {returned_task.id} completed "
                        f"successfully.{Fore.RESET}"
                    )
                    await self._handle_completed_task(returned_task)
                elif returned_task.state == TaskState.FAILED:
                    halt = await self._handle_failed_task(returned_task)
                    if not halt:
                        continue
                    print(
                        f"{Fore.RED}Task {returned_task.id} has failed "
                        f"for 3 times, halting the workforce.{Fore.RESET}"
                    )
                    # Graceful shutdown instead of immediate break
                    await self._graceful_shutdown(returned_task)
                    break
                elif returned_task.state == TaskState.OPEN:
                    # TODO: Add logic for OPEN
                    pass
                else:
                    raise ValueError(
                        f"Task {returned_task.id} has an unexpected state."
                    )

            except Exception as e:
                logger.error(f"Error processing task: {e}")
                if self._stop_requested:
                    break
                # Continue with next iteration unless stop is requested
                continue

        # Handle final state
        if self._stop_requested:
            self._state = WorkforceState.STOPPED
            logger.info("Workforce stopped by user request.")
        elif not self._pending_tasks and self._in_flight_tasks == 0:
            self._state = WorkforceState.IDLE
            logger.info("All tasks completed.")

        # shut down the whole workforce tree
        self.stop()

    def _submit_coro_to_loop(self, coro: 'Coroutine') -> None:
        r"""Thread-safe submission of coroutine to the workforce loop."""

        loop = self._loop
        if loop is None or loop.is_closed():
            logger.warning("Cannot submit coroutine - no active event loop")
            return
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        if running_loop is loop:
            loop.create_task(coro)
        else:
            asyncio.run_coroutine_threadsafe(coro, loop)

    @check_if_running(False)
    async def start(self) -> None:
        r"""Start itself and all the child nodes under it."""
        # Sync shared memory at the start to ensure all agents have context
        if self.share_memory:
            logger.info(
                f"Syncing shared memory at workforce {self.node_id} startup"
            )
            self._sync_shared_memory()

        for child in self._children:
            child_listening_task = asyncio.create_task(child.start())
            self._child_listening_tasks.append(child_listening_task)
        await self._listen_to_channel()

    @check_if_running(True)
    def stop(self) -> None:
        r"""Stop all the child nodes under it. The node itself will be stopped
        by its parent node.
        """
        for child in self._children:
            if child._running:
                child.stop()
        for child_task in self._child_listening_tasks:
            child_task.cancel()
        self._running = False

    def clone(self, with_memory: bool = False) -> 'Workforce':
        r"""Creates a new instance of Workforce with the same configuration.

        Args:
            with_memory (bool, optional): Whether to copy the memory
                (conversation history) to the new instance. If True, the new
                instance will have the same conversation history. If False,
                the new instance will have a fresh memory.
                (default: :obj:`False`)

        Returns:
            Workforce: A new instance of Workforce with the same configuration.
        """

        # Create a new instance with the same configuration
        # Extract the original kwargs from the agents to properly clone them
        coordinator_kwargs = (
            getattr(self.coordinator_agent, 'init_kwargs', {}) or {}
        )
        task_kwargs = getattr(self.task_agent, 'init_kwargs', {}) or {}

        new_instance = Workforce(
            description=self.description,
            coordinator_agent_kwargs=coordinator_kwargs.copy(),
            task_agent_kwargs=task_kwargs.copy(),
            new_worker_agent_kwargs=self.new_worker_agent_kwargs.copy()
            if self.new_worker_agent_kwargs
            else None,
            graceful_shutdown_timeout=self.graceful_shutdown_timeout,
            share_memory=self.share_memory,
        )

        new_instance.task_agent = self.task_agent.clone(with_memory)
        new_instance.coordinator_agent = self.coordinator_agent.clone(
            with_memory
        )

        for child in self._children:
            if isinstance(child, SingleAgentWorker):
                cloned_worker = child.worker.clone(with_memory)
                new_instance.add_single_agent_worker(
                    child.description,
                    cloned_worker,
                    pool_max_size=10,
                )
            elif isinstance(child, RolePlayingWorker):
                new_instance.add_role_playing_worker(
                    child.description,
                    child.assistant_role_name,
                    child.user_role_name,
                    child.assistant_agent_kwargs,
                    child.user_agent_kwargs,
                    child.summarize_agent_kwargs,
                    child.chat_turn_limit,
                )
            elif isinstance(child, Workforce):
                new_instance.add_workforce(child.clone(with_memory))
            else:
                logger.warning(f"{type(child)} is not being cloned.")
                continue

        return new_instance

    @dependencies_required("mcp")
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
        r"""Expose this Workforce as an MCP server.

        Args:
            name (str): Name of the MCP server.
                (default: :obj:`CAMEL-Workforce`)
            description (str): Description of the workforce. If
                None, a generic description is used. (default: :obj:`A
                workforce system using the CAMEL AI framework for
                multi-agent collaboration.`)
            dependencies (Optional[List[str]]): Additional
                dependencies for the MCP server. (default: :obj:`None`)
            host (str): Host to bind to for HTTP transport.
                (default: :obj:`localhost`)
            port (int): Port to bind to for HTTP transport.
                (default: :obj:`8001`)

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

        # Store workforce reference
        workforce_instance = self

        # Define functions first
        async def process_task(
            task_content, task_id=None, additional_info=None
        ):
            r"""Process a task using the workforce.

            Args:
                task_content (str): The content of the task to be processed.
                task_id (str, optional): Unique identifier for the task. If
                    None, a UUID will be automatically generated.
                    (default: :obj:`None`)
                additional_info (Optional[Dict[str, Any]]): Additional
                    information or context for the task. (default: :obj:`None`)

            Returns:
                Dict[str, Any]: A dictionary containing the processing result
                    with the following keys:
                    - status (str): "success" or "error"
                    - task_id (str): The ID of the processed task
                    - state (str): Final state of the task
                    - result (str): Task result content
                    - subtasks (List[Dict]): List of subtask information
                    - message (str): Error message if status is "error"

            Example:
                >>> result = await process_task("Analyze market trends",
                "task_001")
                >>> print(result["status"])  # "success" or "error"
            """
            task = Task(
                content=task_content,
                id=task_id or str(uuid.uuid4()),
                additional_info=additional_info,
            )

            try:
                result_task = await workforce_instance.process_task_async(task)
                return {
                    "status": "success",
                    "task_id": result_task.id,
                    "state": str(result_task.state),
                    "result": result_task.result or "",
                    "subtasks": [
                        {
                            "id": subtask.id,
                            "content": subtask.content,
                            "state": str(subtask.state),
                            "result": subtask.result or "",
                        }
                        for subtask in (result_task.subtasks or [])
                    ],
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": str(e),
                    "task_id": task.id,
                }

        # Reset tool
        def reset():
            r"""Reset the workforce to its initial state.

            Clears all pending tasks, resets all child nodes, and returns
            the workforce to a clean state ready for new task processing.

            Returns:
                Dict[str, str]: A dictionary containing the reset result with:
                    - status (str): "success" or "error"
                    - message (str): Descriptive message about the operation

            Example:
                >>> result = reset()
                >>> print(result["message"])  # "Workforce reset successfully"
            """
            try:
                workforce_instance.reset()
                return {
                    "status": "success",
                    "message": "Workforce reset successfully",
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # Workforce info resource and tool
        def get_workforce_info():
            r"""Get comprehensive information about the workforce.

            Retrieves the current state and configuration of the workforce
            including its ID, description, running status, and task queue
            information.

            Returns:
                Dict[str, Any]: A dictionary containing workforce information:
                    - node_id (str): Unique identifier of the workforce
                    - description (str): Workforce description
                    - mcp_description (str): MCP server description
                    - children_count (int): Number of child workers
                    - is_running (bool): Whether the workforce is active
                    - pending_tasks_count (int): Number of queued tasks
                    - current_task_id (str or None): ID of the active task

            Example:
                >>> info = get_workforce_info()
                >>> print(f"Running: {info['is_running']}")
                >>> print(f"Children: {info['children_count']}")
            """
            info = {
                "node_id": workforce_instance.node_id,
                "description": workforce_instance.description,
                "mcp_description": description,
                "children_count": len(workforce_instance._children),
                "is_running": workforce_instance._running,
                "pending_tasks_count": len(workforce_instance._pending_tasks),
                "current_task_id": (
                    workforce_instance._task.id
                    if workforce_instance._task
                    else None
                ),
            }
            return info

        # Children info resource and tool
        def get_children_info():
            r"""Get information about all child nodes in the workforce.

            Retrieves comprehensive information about each child worker
            including their type, capabilities, and configuration details.

            Returns:
                List[Dict[str, Any]]: A list of dictionaries, each containing
                    child node information with common keys:
                    - node_id (str): Unique identifier of the child
                    - description (str): Child node description
                    - type (str): Type of worker (e.g., "SingleAgentWorker")

                    Additional keys depend on worker type:

                    For SingleAgentWorker:
                    - tools (List[str]): Available tool names
                    - role_name (str): Agent's role name

                    For RolePlayingWorker:
                    - assistant_role (str): Assistant agent role
                    - user_role (str): User agent role
                    - chat_turn_limit (int): Maximum conversation turns

                    For Workforce:
                    - children_count (int): Number of nested children
                    - is_running (bool): Whether the nested workforce is active

            Example:
                >>> children = get_children_info()
                >>> for child in children:
                ...     print(f"{child['type']}: {child['description']}")
            """
            children_info: List[Dict[str, Any]] = []
            for child in workforce_instance._children:
                child_info: Dict[str, Any] = {
                    "node_id": child.node_id,
                    "description": child.description,
                    "type": type(child).__name__,
                }

                if isinstance(child, SingleAgentWorker):
                    child_info["tools"] = list(child.worker.tool_dict.keys())
                    child_info["role_name"] = child.worker.role_name
                elif isinstance(child, RolePlayingWorker):
                    child_info["assistant_role"] = child.assistant_role_name
                    child_info["user_role"] = child.user_role_name
                    child_info["chat_turn_limit"] = child.chat_turn_limit
                elif isinstance(child, Workforce):
                    child_info["children_count"] = len(child._children)
                    child_info["is_running"] = child._running

                children_info.append(child_info)

            return children_info

        # Add single agent worker
        def add_single_agent_worker(
            description,
            system_message=None,
            role_name="Assistant",
            agent_kwargs=None,
        ):
            r"""Add a single agent worker to the workforce.

            Creates and adds a new SingleAgentWorker to the workforce with
            the specified configuration. The worker cannot be added while
            the workforce is currently running.

            Args:
                description (str): Description of the worker's role and
                    capabilities.
                system_message (str, optional): Custom system message for the
                    agent. If None, a default message based on role_name is
                    used. (default: :obj:`None`)
                role_name (str, optional): Name of the agent's role.
                    (default: :obj:`"Assistant"`)
                agent_kwargs (Dict, optional): Additional keyword arguments
                    to pass to the ChatAgent constructor, such as model
                    configuration, tools, etc. (default: :obj:`None`)

            Returns:
                Dict[str, str]: A dictionary containing the operation result:
                    - status (str): "success" or "error"
                    - message (str): Descriptive message about the operation
                    - worker_id (str): ID of the created worker (on success)

            Example:
                >>> result = add_single_agent_worker(
                ...     "Data Analyst",
                ...     "You are a data analysis expert.",
                ...     "Analyst"
                ... )
                >>> print(result["status"])  # "success" or "error"
            """
            try:
                if workforce_instance._running:
                    return {
                        "status": "error",
                        "message": "Cannot add workers while workforce is running",  # noqa: E501
                    }

                # Create agent with provided configuration
                sys_msg = BaseMessage.make_assistant_message(
                    role_name=role_name,
                    content=system_message or f"You are a {role_name}.",
                )

                agent = ChatAgent(sys_msg, **(agent_kwargs or {}))
                workforce_instance.add_single_agent_worker(description, agent)

                return {
                    "status": "success",
                    "message": f"Single agent worker '{description}' added",
                    "worker_id": workforce_instance._children[-1].node_id,
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # Add role playing worker
        def add_role_playing_worker(
            description,
            assistant_role_name,
            user_role_name,
            chat_turn_limit=20,
            assistant_agent_kwargs=None,
            user_agent_kwargs=None,
            summarize_agent_kwargs=None,
        ):
            r"""Add a role playing worker to the workforce.

            Creates and adds a new RolePlayingWorker to the workforce that
            uses two agents in a conversational role-playing setup. The
            worker cannot be added while the workforce is currently running.

            Args:
                description (str): Description of the role playing worker's
                    purpose and capabilities.
                assistant_role_name (str): Name/role of the assistant agent
                    in the role playing scenario.
                user_role_name (str): Name/role of the user agent in the
                    role playing scenario.
                chat_turn_limit (int, optional): Maximum number of
                    conversation turns between the two agents.
                    (default: :obj:`20`)
                assistant_agent_kwargs (Dict, optional): Keyword arguments
                    for configuring the assistant ChatAgent, such as model
                    type, tools, etc. (default: :obj:`None`)
                user_agent_kwargs (Dict, optional): Keyword arguments for
                    configuring the user ChatAgent, such as model type,
                    tools, etc. (default: :obj:`None`)
                summarize_agent_kwargs (Dict, optional): Keyword arguments
                    for configuring the summarization agent used to process
                    the conversation results. (default: :obj:`None`)

            Returns:
                Dict[str, str]: A dictionary containing the operation result:
                    - status (str): "success" or "error"
                    - message (str): Descriptive message about the operation
                    - worker_id (str): ID of the created worker (on success)

            Example:
                >>> result = add_role_playing_worker(
                ...     "Design Review Team",
                ...     "Design Critic",
                ...     "Design Presenter",
                ...     chat_turn_limit=5
                ... )
                >>> print(result["status"])  # "success" or "error"
            """
            try:
                if workforce_instance._running:
                    return {
                        "status": "error",
                        "message": "Cannot add workers while workforce is running",  # noqa: E501
                    }

                workforce_instance.add_role_playing_worker(
                    description=description,
                    assistant_role_name=assistant_role_name,
                    user_role_name=user_role_name,
                    chat_turn_limit=chat_turn_limit,
                    assistant_agent_kwargs=assistant_agent_kwargs,
                    user_agent_kwargs=user_agent_kwargs,
                    summarize_agent_kwargs=summarize_agent_kwargs,
                )

                return {
                    "status": "success",
                    "message": f"Role playing worker '{description}' added",
                    "worker_id": workforce_instance._children[-1].node_id,
                }
            except Exception as e:
                return {"status": "error", "message": str(e)}

        # Now register everything using decorators
        mcp_server.tool()(process_task)
        mcp_server.tool()(reset)
        mcp_server.tool()(add_single_agent_worker)
        mcp_server.tool()(add_role_playing_worker)

        mcp_server.resource("workforce://")(get_workforce_info)
        mcp_server.tool()(get_workforce_info)

        mcp_server.resource("children://")(get_children_info)
        mcp_server.tool()(get_children_info)

        return mcp_server
