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
from collections import deque
from typing import Deque, Dict, List, Optional
from enum import Enum
import time

from colorama import Fore

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
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
from camel.tasks.task import Task, TaskState
from camel.toolkits import CodeExecutionToolkit, SearchToolkit, ThinkingToolkit
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


class WorkforceState(Enum):
    """Workforce execution state for human intervention support."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class WorkforceSnapshot:
    """Snapshot of workforce state for resuming execution."""
    def __init__(
        self,
        main_task: Optional[Task] = None,
        pending_tasks: Optional[Deque[Task]] = None,
        completed_tasks: Optional[List[Task]] = None,
        current_task_index: int = 0,
        description: str = ""
    ):
        self.main_task = main_task
        self.pending_tasks = pending_tasks.copy() if pending_tasks else deque()
        self.completed_tasks = completed_tasks.copy() if completed_tasks else []
        self.current_task_index = current_task_index
        self.description = description
        self.timestamp = time.time()


class Workforce(BaseNode):
    r"""A system where multiple workder nodes (agents) cooperate together
    to solve tasks. It can assign tasks to workder nodes and also take
    strategies such as create new worker, decompose tasks, etc. to handle
    situations when the task fails.

    Args:
        description (str): Description of the node.
        children (Optional[List[BaseNode]], optional): List of child nodes
            under this node. Each child node can be a worker node or
            another workforce node. (default: :obj:`None`)
        coordinator_agent_kwargs (Optional[Dict], optional): Keyword
            arguments for the coordinator agent, e.g. `model`, `api_key`,
            `tools`, etc. If not provided, default model settings will be used.
            (default: :obj:`None`)
        task_agent_kwargs (Optional[Dict], optional): Keyword arguments for
            the task agent, e.g. `model`, `api_key`, `tools`, etc.
            If not provided, default model settings will be used.
            (default: :obj:`None`)
        new_worker_agent_kwargs (Optional[Dict]): Default keyword arguments
            for the worker agent that will be created during runtime to
            handle failed tasks, e.g. `model`, `api_key`, `tools`, etc.
            If not provided, default model settings will be used.
            (default: :obj:`None`)
    """

    def __init__(
        self,
        description: str,
        children: Optional[List[BaseNode]] = None,
        coordinator_agent_kwargs: Optional[Dict] = None,
        task_agent_kwargs: Optional[Dict] = None,
        new_worker_agent_kwargs: Optional[Dict] = None,
    ) -> None:
        super().__init__(description)
        self._child_listening_tasks: Deque[asyncio.Task] = deque()
        self._children = children or []
        self.new_worker_agent_kwargs = new_worker_agent_kwargs

        # Human intervention support
        self._state = WorkforceState.IDLE
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initially not paused
        self._stop_requested = False
        self._snapshots: List[WorkforceSnapshot] = []
        self._completed_tasks: List[Task] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._main_task_future: Optional[asyncio.Future] = None

        # Warning messages for default model usage
        if coordinator_agent_kwargs is None:
            logger.warning(
                "No coordinator_agent_kwargs provided. "
                "Using `ModelPlatformType.DEFAULT` and `ModelType.DEFAULT` "
                "for coordinator agent."
            )
        if task_agent_kwargs is None:
            logger.warning(
                "No task_agent_kwargs provided. "
                "Using `ModelPlatformType.DEFAULT` and `ModelType.DEFAULT` "
                "for task agent."
            )
        if new_worker_agent_kwargs is None:
            logger.warning(
                "No new_worker_agent_kwargs provided. "
                "Using `ModelPlatformType.DEFAULT` and `ModelType.DEFAULT` "
                "for worker agents created during runtime."
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
            coord_agent_sys_msg, **(coordinator_agent_kwargs or {})
        )

        task_sys_msg = BaseMessage.make_assistant_message(
            role_name="Task Planner",
            content="You are going to compose and decompose tasks.",
        )
        self.task_agent = ChatAgent(task_sys_msg, **(task_agent_kwargs or {}))

        # If there is one, will set by the workforce class wrapping this
        self._task: Optional[Task] = None
        self._pending_tasks: Deque[Task] = deque()

    def __repr__(self):
        return f"Workforce {self.node_id} ({self.description}) - State: {self._state.value}"

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
    def pause(self) -> None:
        """Pause the workforce execution."""
        if self._state == WorkforceState.RUNNING:
            self._state = WorkforceState.PAUSED
            self._pause_event.clear()
            logger.info(f"Workforce {self.node_id} paused.")
            print(f"{Fore.YELLOW}Workforce paused. Call resume() to continue.{Fore.RESET}")

    def resume(self) -> None:
        """Resume the paused workforce execution."""
        if self._state == WorkforceState.PAUSED:
            self._state = WorkforceState.RUNNING
            self._pause_event.set()
            logger.info(f"Workforce {self.node_id} resumed.")
            print(f"{Fore.GREEN}Workforce resumed.{Fore.RESET}")

    def stop_gracefully(self) -> None:
        """Request graceful stop of the workforce."""
        self._stop_requested = True
        self._state = WorkforceState.STOPPED
        if self._pause_event.is_set() is False:
            self._pause_event.set()  # Resume if paused to process stop
        logger.info(f"Workforce {self.node_id} stop requested.")
        print(f"{Fore.RED}Workforce stop requested.{Fore.RESET}")

    def save_snapshot(self, description: str = "") -> None:
        """Save current state as a snapshot."""
        snapshot = WorkforceSnapshot(
            main_task=self._task,
            pending_tasks=self._pending_tasks,
            completed_tasks=self._completed_tasks,
            current_task_index=len(self._completed_tasks),
            description=description
        )
        self._snapshots.append(snapshot)
        logger.info(f"Snapshot saved: {description}")
        print(f"{Fore.CYAN}Snapshot saved at index {len(self._snapshots) - 1}: {description}{Fore.RESET}")

    def list_snapshots(self) -> List[str]:
        """List all available snapshots."""
        snapshots_info = []
        for i, snapshot in enumerate(self._snapshots):
            desc_part = f" - {snapshot.description}" if snapshot.description else ""
            info = f"Snapshot {i}: {len(snapshot.completed_tasks)} completed, {len(snapshot.pending_tasks)} pending{desc_part}"
            snapshots_info.append(info)
        return snapshots_info

    def get_pending_tasks(self) -> List[Task]:
        """Get current pending tasks for human review."""
        return list(self._pending_tasks)

    def get_completed_tasks(self) -> List[Task]:
        """Get completed tasks."""
        return self._completed_tasks.copy()

    def modify_task_content(self, task_id: str, new_content: str) -> bool:
        """Modify the content of a pending task."""
        for task in self._pending_tasks:
            if task.id == task_id:
                task.content = new_content
                logger.info(f"Task {task_id} content modified.")
                print(f"{Fore.GREEN}Task {task_id} content updated.{Fore.RESET}")
                return True
        logger.warning(f"Task {task_id} not found in pending tasks.")
        return False

    def add_task(self, content: str, task_id: Optional[str] = None, 
                 additional_info: str = "", insert_position: int = -1) -> Task:
        """Add a new task to the pending queue."""
        new_task = Task(
            content=content,
            id=task_id or f"human_added_{len(self._pending_tasks)}",
            additional_info=additional_info
        )
        if insert_position == -1:
            self._pending_tasks.append(new_task)
        else:
            # Convert deque to list, insert, then back to deque
            tasks_list = list(self._pending_tasks)
            tasks_list.insert(insert_position, new_task)
            self._pending_tasks = deque(tasks_list)
        
        logger.info(f"New task added: {new_task.id}")
        print(f"{Fore.GREEN}Task added: {new_task.id}{Fore.RESET}")
        return new_task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the pending queue."""
        # Convert to list to find and remove
        tasks_list = list(self._pending_tasks)
        for i, task in enumerate(tasks_list):
            if task.id == task_id:
                tasks_list.pop(i)
                self._pending_tasks = deque(tasks_list)
                logger.info(f"Task {task_id} removed.")
                print(f"{Fore.YELLOW}Task {task_id} removed.{Fore.RESET}")
                return True
        logger.warning(f"Task {task_id} not found in pending tasks.")
        return False

    def reorder_tasks(self, task_ids: List[str]) -> bool:
        """Reorder pending tasks according to the provided task IDs list."""
        # Create a mapping of task_id to task
        tasks_dict = {task.id: task for task in self._pending_tasks}
        
        # Check if all provided IDs exist
        if not all(task_id in tasks_dict for task_id in task_ids):
            logger.warning("Some task IDs not found in pending tasks.")
            return False
        
        # Check if we have the same number of tasks
        if len(task_ids) != len(self._pending_tasks):
            logger.warning("Number of task IDs doesn't match pending tasks count.")
            return False
        
        # Reorder tasks
        reordered_tasks = deque([tasks_dict[task_id] for task_id in task_ids])
        self._pending_tasks = reordered_tasks
        
        logger.info("Tasks reordered successfully.")
        print(f"{Fore.GREEN}Tasks reordered successfully.{Fore.RESET}")
        return True

    def resume_from_task(self, task_id: str) -> bool:
        """Resume execution from a specific task."""
        if self._state != WorkforceState.PAUSED:
            logger.warning("Workforce must be paused to resume from specific task.")
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
        
        # Move previously "completed" tasks that are after target back to pending
        if tasks_to_move_back:
            logger.info(f"Moving {len(tasks_to_move_back)} tasks back to pending state.")
        
        logger.info(f"Ready to resume from task: {task_id}")
        print(f"{Fore.GREEN}Ready to resume from task: {task_id}{Fore.RESET}")
        return True

    def restore_from_snapshot(self, snapshot_index: int) -> bool:
        """Restore workforce state from a snapshot."""
        if not (0 <= snapshot_index < len(self._snapshots)):
            logger.warning(f"Invalid snapshot index: {snapshot_index}")
            return False
        
        if self._state == WorkforceState.RUNNING:
            logger.warning("Cannot restore snapshot while workforce is running. Pause first.")
            return False
        
        snapshot = self._snapshots[snapshot_index]
        self._task = snapshot.main_task
        self._pending_tasks = snapshot.pending_tasks.copy()
        self._completed_tasks = snapshot.completed_tasks.copy()
        
        logger.info(f"Workforce state restored from snapshot {snapshot_index}")
        print(f"{Fore.GREEN}State restored from snapshot {snapshot_index}{Fore.RESET}")
        return True

    def get_workforce_status(self) -> Dict:
        """Get current workforce status for human review."""
        return {
            "state": self._state.value,
            "pending_tasks_count": len(self._pending_tasks),
            "completed_tasks_count": len(self._completed_tasks),
            "snapshots_count": len(self._snapshots),
            "children_count": len(self._children),
            "main_task_id": self._task.id if self._task else None,
        }

    @check_if_running(False)
    def process_task(self, task: Task) -> Task:
        r"""The main entry point for the workforce to process a task. It will
        start the workforce and all the child nodes under it, process the
        task provided and return the updated task.

        Args:
            task (Task): The task to be processed.

        Returns:
            Task: The updated task.
        """
        self.reset()
        self._task = task
        task.state = TaskState.FAILED
        self._pending_tasks.append(task)
        # The agent tend to be overconfident on the whole task, so we
        # decompose the task into subtasks first
        subtasks = self._decompose_task(task)
        self._pending_tasks.extendleft(reversed(subtasks))
        self.set_channel(TaskChannel())

        asyncio.run(self.start())

        return task

    async def process_task_async(self, task: Task) -> Task:
        r"""Async version of process_task that supports human intervention.
        This method can be paused, resumed, and allows task modification.

        Args:
            task (Task): The task to be processed.

        Returns:
            Task: The updated task.
        """
        self.reset()
        self._task = task
        self._state = WorkforceState.RUNNING
        task.state = TaskState.FAILED
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

    def process_task_with_intervention(self, task: Task) -> Task:
        r"""Process task with human intervention support. This creates and manages
        its own event loop to allow for pausing/resuming functionality.

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
            return self._loop.run_until_complete(self.process_task_async(task))
        finally:
            # Keep the loop running for potential resume operations
            if not self._loop.is_closed() and self._state == WorkforceState.PAUSED:
                logger.info("Event loop kept alive for potential resume operations.")
            elif self._state == WorkforceState.STOPPED:
                if not self._loop.is_closed():
                    self._loop.close()

    def continue_from_pause(self) -> Optional[Task]:
        r"""Continue execution from a paused state. This reuses the existing event loop.

        Returns:
            Optional[Task]: The completed task if execution finishes, None if still running/paused.
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
            remaining_task = self._loop.run_until_complete(self._continue_execution())
            return remaining_task
        except Exception as e:
            logger.error(f"Error continuing execution: {e}")
            self._state = WorkforceState.STOPPED
            return None

    async def _continue_execution(self) -> Task:
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
        self, description: str, worker: ChatAgent
    ) -> Workforce:
        r"""Add a worker node to the workforce that uses a single agent.

        Args:
            description (str): Description of the worker node.
            worker (ChatAgent): The agent to be added.

        Returns:
            Workforce: The workforce node itself.
        """
        worker_node = SingleAgentWorker(description, worker)
        self._children.append(worker_node)
        return self

    @check_if_running(False)
    def add_role_playing_worker(
        self,
        description: str,
        assistant_role_name: str,
        user_role_name: str,
        assistant_agent_kwargs: Optional[Dict] = None,
        user_agent_kwargs: Optional[Dict] = None,
        chat_turn_limit: int = 3,
    ) -> Workforce:
        r"""Add a worker node to the workforce that uses `RolePlaying` system.

        Args:
            description (str): Description of the node.
            assistant_role_name (str): The role name of the assistant agent.
            user_role_name (str): The role name of the user agent.
            assistant_agent_kwargs (Optional[Dict], optional): The keyword
                arguments to initialize the assistant agent in the role
                playing, like the model name, etc. Defaults to `None`.
            user_agent_kwargs (Optional[Dict], optional): The keyword arguments
                to initialize the user agent in the role playing, like the
                model name, etc. Defaults to `None`.
            chat_turn_limit (int, optional): The maximum number of chat turns
                in the role playing. Defaults to 3.

        Returns:
            Workforce: The workforce node itself.
        """
        worker_node = RolePlayingWorker(
            description,
            assistant_role_name,
            user_role_name,
            assistant_agent_kwargs,
            user_agent_kwargs,
            chat_turn_limit,
        )
        self._children.append(worker_node)
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

    @check_if_running(False)
    def reset(self) -> None:
        r"""Reset the workforce and all the child nodes under it. Can only
        be called when the workforce is not running."""
        super().reset()
        self._task = None
        self._pending_tasks.clear()
        self._child_listening_tasks.clear()
        # Reset intervention state
        self._state = WorkforceState.IDLE
        self._stop_requested = False
        self._pause_event.set()
        self._completed_tasks.clear()
        # Don't clear snapshots - they should persist across resets
        
        self.coordinator_agent.reset()
        self.task_agent.reset()
        for child in self._children:
            child.reset()

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
        task: Task,
    ) -> str:
        r"""Assigns a task to a worker node with the best capability.

        Parameters:
            task (Task): The task to be assigned.

        Returns:
            str: ID of the worker node to be assigned.
        """
        self.coordinator_agent.reset()
        prompt = ASSIGN_TASK_PROMPT.format(
            content=task.content,
            child_nodes_info=self._get_child_nodes_info(),
            additional_info=task.additional_info,
        )

        response = self.coordinator_agent.step(
            prompt, response_format=TaskAssignResult
        )
        result_dict = json.loads(response.msg.content, parse_int=str)
        task_assign_result = TaskAssignResult(**result_dict)
        return task_assign_result.assignee_id

    async def _post_task(self, task: Task, assignee_id: str) -> None:
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
        result_dict = json.loads(response.msg.content)
        new_node_conf = WorkerConf(**result_dict)

        new_agent = self._create_new_agent(
            new_node_conf.role,
            new_node_conf.sys_msg,
        )

        new_node = SingleAgentWorker(
            description=new_node_conf.description,
            worker=new_agent,
        )
        new_node.set_channel(self._channel)

        print(f"{Fore.CYAN}{new_node} created.{Fore.RESET}")

        self._children.append(new_node)
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

        model_config_dict = ChatGPTConfig(
            tools=function_list,
            temperature=0.0,
        ).as_dict()

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict=model_config_dict,
        )

        return ChatAgent(worker_sys_msg, model=model, tools=function_list)  # type: ignore[arg-type]

    async def _get_returned_task(self) -> Task:
        r"""Get the task that's published by this node and just get returned
        from the assignee.
        """
        return await self._channel.get_returned_task_by_publisher(self.node_id)

    async def _post_ready_tasks(self) -> None:
        r"""Send all the pending tasks that have all the dependencies met to
        the channel, or directly return if there is none. For now, we will
        directly send the first task in the pending list because all the tasks
        are linearly dependent."""

        if not self._pending_tasks:
            return

        ready_task = self._pending_tasks[0]

        # If the task has failed previously, just compose and send the task
        # to the channel as a dependency
        if ready_task.state == TaskState.FAILED:
            # TODO: the composing of tasks seems not work very well
            self.task_agent.reset()
            ready_task.compose(self.task_agent)
            # Remove the subtasks from the channel
            for subtask in ready_task.subtasks:
                await self._channel.remove_task(subtask.id)
            # Send the task to the channel as a dependency
            await self._post_dependency(ready_task)
            self._pending_tasks.popleft()
            # Try to send the next task in the pending list
            await self._post_ready_tasks()
        else:
            # Directly post the task to the channel if it's a new one
            # Find a node to assign the task
            assignee_id = self._find_assignee(task=ready_task)
            await self._post_task(ready_task, assignee_id)

    async def _handle_failed_task(self, task: Task) -> bool:
        if task.failure_count >= 3:
            return True
        task.failure_count += 1
        # Remove the failed task from the channel
        await self._channel.remove_task(task.id)
        if task.get_depth() >= 3:
            # Create a new worker node and reassign
            assignee = self._create_worker_node_for_task(task)
            await self._post_task(task, assignee.node_id)
        else:
            subtasks = self._decompose_task(task)
            # Insert packets at the head of the queue
            self._pending_tasks.extendleft(reversed(subtasks))
            await self._post_ready_tasks()
        return False

    async def _handle_completed_task(self, task: Task) -> None:
        # Find and remove the completed task from pending tasks
        # Instead of just popping the first task, find the actual completed task
        tasks_list = list(self._pending_tasks)
        found_and_removed = False
        
        for i, pending_task in enumerate(tasks_list):
            if pending_task.id == task.id:
                # Remove this specific task
                tasks_list.pop(i)
                self._pending_tasks = deque(tasks_list)
                found_and_removed = True
                print(f"{Fore.GREEN}✅ Task {task.id} completed and removed from queue.{Fore.RESET}")
                break
        
        if not found_and_removed:
            # If not found in pending, just log it
            print(f"{Fore.YELLOW}⚠️ Completed task {task.id} was not in pending queue.{Fore.RESET}")
        
        # Ensure it's in completed tasks list
        if task not in self._completed_tasks:
            self._completed_tasks.append(task)
        
        # Archive the task in the channel
        await self._channel.archive_task(task.id)
        
        # Post next ready tasks
        await self._post_ready_tasks()

    @check_if_running(False)
    async def _listen_to_channel(self) -> None:
        r"""Continuously listen to the channel, post task to the channel and
        track the status of posted tasks. Now supports pause/resume and graceful stop.
        """

        self._running = True
        self._state = WorkforceState.RUNNING
        logger.info(f"Workforce {self.node_id} started.")

        await self._post_ready_tasks()

        while (self._task is None or self._pending_tasks) and not self._stop_requested:
            try:
                # Check for pause request at the beginning of each loop iteration
                await self._pause_event.wait()
                
                # Check for stop request after potential pause
                if self._stop_requested:
                    logger.info("Stop requested, breaking execution loop.")
                    break
                    
                # Save snapshot before processing next task
                if self._pending_tasks:
                    current_task = self._pending_tasks[0]
                    self.save_snapshot(f"Before processing task: {current_task.id}")
                
                # Get returned task (this may block until a task is returned)
                returned_task = await self._get_returned_task()
                
                # Check for stop request after getting task (but don't check pause again)
                if self._stop_requested:
                    logger.info("Stop requested after receiving task.")
                    break
                
                # Process the returned task based on its state
                if returned_task.state == TaskState.DONE:
                    print(f"{Fore.CYAN}🎯 Task {returned_task.id} completed successfully.{Fore.RESET}")
                    await self._handle_completed_task(returned_task)
                elif returned_task.state == TaskState.FAILED:
                    halt = await self._handle_failed_task(returned_task)
                    if not halt:
                        continue
                    print(
                        f"{Fore.RED}Task {returned_task.id} has failed "
                        f"for 3 times, halting the workforce.{Fore.RESET}"
                    )
                    break
                elif returned_task.state == TaskState.OPEN:
                    # TODO: multi-layer workforce
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
        elif not self._pending_tasks:
            self._state = WorkforceState.IDLE
            logger.info("All tasks completed.")
        
        # shut down the whole workforce tree
        self.stop()

    @check_if_running(False)
    async def start(self) -> None:
        r"""Start itself and all the child nodes under it."""
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
            child.stop()
        for child_task in self._child_listening_tasks:
            child_task.cancel()
        self._running = False
