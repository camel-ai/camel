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
import uuid
from collections import deque
from typing import Deque, Dict, List, Optional

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
from camel.tasks.task import Task, TaskState
from camel.toolkits import CodeExecutionToolkit, SearchToolkit, ThinkingToolkit
from camel.types import ModelPlatformType, ModelType
from camel.utils import dependencies_required

logger = get_logger(__name__)


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

    Example:
        >>> # Configure with custom model
        >>> model = ModelFactory.create(
        ...     ModelPlatformType.OPENAI, ModelType.GPT_4O
        ... )
        >>> workforce = Workforce(
        ...     "Research Team",
        ...     coordinator_agent_kwargs={"model": model, "token_limit": 4000},
        ...     task_agent_kwargs={"model": model, "token_limit": 8000}
        ... )
        >>>
        >>> # Process a task
        >>> task = Task(content="Research AI trends", id="1")
        >>> result = workforce.process_task(task)
    """

    def __init__(
        self,
        description: str,
        children: Optional[List[BaseNode]] = None,
        coordinator_agent_kwargs: Optional[Dict] = None,
        task_agent_kwargs: Optional[Dict] = None,
        new_worker_agent_kwargs: Optional[Dict] = None,
        graceful_shutdown_timeout: float = 15.0,
    ) -> None:
        super().__init__(description)
        self._child_listening_tasks: Deque[asyncio.Task] = deque()
        self._children = children or []
        self.new_worker_agent_kwargs = new_worker_agent_kwargs
        self.graceful_shutdown_timeout = graceful_shutdown_timeout

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
        return f"Workforce {self.node_id} ({self.description})"

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

        model = ModelFactory.create(
            model_platform=ModelPlatformType.DEFAULT,
            model_type=ModelType.DEFAULT,
            model_config_dict={"temperature": 0},
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
        # archive the packet, making it into a dependency
        self._pending_tasks.popleft()
        await self._channel.archive_task(task.id)
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

    @check_if_running(False)
    async def _listen_to_channel(self) -> None:
        r"""Continuously listen to the channel, post task to the channel and
        track the status of posted tasks.
        """

        self._running = True
        logger.info(f"Workforce {self.node_id} started.")

        await self._post_ready_tasks()

        while self._task is None or self._pending_tasks:
            returned_task = await self._get_returned_task()
            if returned_task.state == TaskState.DONE:
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
                # TODO: multi-layer workforce
                pass
            else:
                raise ValueError(
                    f"Task {returned_task.id} has an unexpected state."
                )

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
        new_instance = Workforce(
            description=self.description,
            coordinator_agent_kwargs={},
            task_agent_kwargs={},
            new_worker_agent_kwargs=self.new_worker_agent_kwargs,
            graceful_shutdown_timeout=self.graceful_shutdown_timeout,
        )

        new_instance.task_agent = self.task_agent.clone(with_memory)
        new_instance.coordinator_agent = self.coordinator_agent.clone(
            with_memory
        )

        for child in self._children:
            if isinstance(child, SingleAgentWorker):
                cloned_worker = child.worker.clone(with_memory)
                new_instance.add_single_agent_worker(
                    child.description, cloned_worker
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
        def process_task(task_content, task_id=None, additional_info=None):
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
                >>> result = process_task("Analyze market trends", "task_001")
                >>> print(result["status"])  # "success" or "error"
            """
            task = Task(
                content=task_content,
                id=task_id or str(uuid.uuid4()),
                additional_info=additional_info,
            )

            try:
                result_task = workforce_instance.process_task(task)
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
            children_info = []
            for child in workforce_instance._children:
                child_info = {
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
