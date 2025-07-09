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
import json
import time
import uuid
from collections import deque
from enum import Enum
from typing import (
    Any,
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

from colorama import Fore

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce.base import BaseNode
from camel.societies.workforce.prompts import (
    ASSIGN_TASK_PROMPT,
    CREATE_NODE_PROMPT,
    FAILURE_ANALYSIS_PROMPT,
    TASK_DECOMPOSE_PROMPT,
)
from camel.societies.workforce.role_playing_worker import RolePlayingWorker
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.structured_output_handler import (
    StructuredOutputHandler,
)
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import (
    FailureContext,
    RecoveryDecision,
    RecoveryStrategy,
    TaskAssignment,
    TaskAssignResult,
    WorkerConf,
    check_if_running,
)
from camel.societies.workforce.worker import Worker
from camel.tasks.task import (
    Task,
    TaskState,
    is_task_result_insufficient,
    validate_task_content,
)
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

# Constants for configuration values
MAX_TASK_RETRIES = 3
MAX_PENDING_TASKS_LIMIT = 20
TASK_TIMEOUT_SECONDS = 180.0
DEFAULT_WORKER_POOL_SIZE = 10


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
        coordinator_agent (Optional[ChatAgent], optional): A custom coordinator
            agent instance for task assignment and worker creation. If
            provided, the workforce will create a new agent using this agent's
            model configuration but with the required system message and
            functionality.
            If None, a default agent will be created using DEFAULT model
            settings. (default: :obj:`None`)
        task_agent (Optional[ChatAgent], optional): A custom task planning
            agent instance for task decomposition and composition. If
            provided, the workforce will create a new agent using this agent's
            model configuration but with the required system message and tools
            (TaskPlanningToolkit). If None, a default agent will be created
            using DEFAULT model settings. (default: :obj:`None`)
        new_worker_agent (Optional[ChatAgent], optional): A template agent for
            workers created dynamically at runtime when existing workers cannot
            handle failed tasks. If None, workers will be created with default
            settings including SearchToolkit, CodeExecutionToolkit, and
            ThinkingToolkit. (default: :obj:`None`)
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
        use_structured_output_handler (bool, optional): Whether to use the
            structured output handler instead of native structured output.
            When enabled, the workforce will use prompts with structured
            output instructions and regex extraction to parse responses.
            This ensures compatibility with agents that don't reliably
            support native structured output. When disabled, the workforce
            uses the native response_format parameter.
            (default: :obj:`True`)

    Example:
        >>> import asyncio
        >>> from camel.agents import ChatAgent
        >>> from camel.models import ModelFactory
        >>> from camel.types import ModelPlatformType, ModelType
        >>> from camel.tasks import Task
        >>>
        >>> # Simple workforce with default agents
        >>> workforce = Workforce("Research Team")
        >>>
        >>> # Workforce with custom model configuration
        >>> model = ModelFactory.create(
        ...     ModelPlatformType.OPENAI, model_type=ModelType.GPT_4O
        ... )
        >>> coordinator_agent = ChatAgent(model=model)
        >>> task_agent = ChatAgent(model=model)
        >>>
        >>> workforce = Workforce(
        ...     "Research Team",
        ...     coordinator_agent=coordinator_agent,
        ...     task_agent=task_agent,
        ... )
        >>>
        >>> # Process a task
        >>> async def main():
        ...     task = Task(content="Research AI trends", id="1")
        ...     result = await workforce.process_task_async(task)
        ...     return result
        >>>
        >>> result_task = asyncio.run(main())

    Note:
        When custom coordinator_agent or task_agent are provided, the workforce
        will preserve the user's system message and append the required
        workforce coordination or task planning instructions to it. This
        ensures both the user's intent is preserved and proper workforce
        functionality is maintained. All other agent configurations (model,
        memory, tools, etc.) will also be preserved.
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
        if self.use_structured_output_handler:
            self.structured_handler = StructuredOutputHandler()
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
        self._cleanup_task: Optional[asyncio.Task] = None
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
                    for schema in coordinator_agent._external_tool_schemas.values()  # noqa: E501
                ],
                response_terminators=coordinator_agent.response_terminators,
                max_iteration=coordinator_agent.max_iteration,
                stop_event=coordinator_agent.stop_event,
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

        # ------------------------------------------------------------------
        # Helper for propagating pause control to externally supplied agents
        # ------------------------------------------------------------------

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
                logger.warning(
                    "No valid memory records could be reconstructed "
                    "for sharing"
                )
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

    def _update_dependencies_for_decomposition(
        self, original_task: Task, subtasks: List[Task]
    ) -> None:
        r"""Update dependency tracking when a task is decomposed into subtasks.
        Tasks that depended on the original task should now depend on all
        subtasks. The last subtask inherits the original task's dependencies.
        """
        if not subtasks:
            return

        original_task_id = original_task.id
        subtask_ids = [subtask.id for subtask in subtasks]

        # Find tasks that depend on the original task
        dependent_task_ids = [
            task_id
            for task_id, deps in self._task_dependencies.items()
            if original_task_id in deps
        ]

        # Update dependent tasks to depend on all subtasks
        for task_id in dependent_task_ids:
            dependencies = self._task_dependencies[task_id]
            dependencies.remove(original_task_id)
            dependencies.extend(subtask_ids)

        # The last subtask inherits original task's dependencies (if any)
        if original_task_id in self._task_dependencies:
            original_dependencies = self._task_dependencies[original_task_id]
            if original_dependencies:
                # Set dependencies for the last subtask to maintain execution
                # order
                self._task_dependencies[subtask_ids[-1]] = (
                    original_dependencies.copy()
                )
            # Remove original task dependencies as it's now decomposed
            del self._task_dependencies[original_task_id]

    def _increment_in_flight_tasks(self, task_id: str) -> None:
        r"""Safely increment the in-flight tasks counter with logging."""
        self._in_flight_tasks += 1
        logger.debug(
            f"Incremented in-flight tasks for {task_id}. "
            f"Count: {self._in_flight_tasks}"
        )

    def _decrement_in_flight_tasks(
        self, task_id: str, context: str = ""
    ) -> None:
        r"""Safely decrement the in-flight tasks counter with safety checks."""
        if self._in_flight_tasks > 0:
            self._in_flight_tasks -= 1
            logger.debug(
                f"Decremented in-flight tasks for {task_id} ({context}). "
                f"Count: {self._in_flight_tasks}"
            )
        else:
            logger.debug(
                f"Attempted to decrement in-flight tasks for {task_id} "
                f"({context}) but counter is already 0. "
                f"Counter: {self._in_flight_tasks}"
            )

    def _cleanup_task_tracking(self, task_id: str) -> None:
        r"""Clean up tracking data for a task to prevent memory leaks.

        Args:
            task_id (str): The ID of the task to clean up.
        """
        if task_id in self._task_start_times:
            del self._task_start_times[task_id]

        if task_id in self._task_dependencies:
            del self._task_dependencies[task_id]

        if task_id in self._assignees:
            del self._assignees[task_id]

    def _decompose_task(
        self, task: Task
    ) -> Union[List[Task], Generator[List[Task], None, None]]:
        r"""Decompose the task into subtasks. This method will also set the
        relationship between the task and its subtasks.

        Returns:
            Union[List[Task], Generator[List[Task], None, None]]:
            The subtasks or generator of subtasks.
        """
        decompose_prompt = TASK_DECOMPOSE_PROMPT.format(
            content=task.content,
            child_nodes_info=self._get_child_nodes_info(),
            additional_info=task.additional_info,
        )
        self.task_agent.reset()
        result = task.decompose(self.task_agent, decompose_prompt)

        # Handle both streaming and non-streaming results
        if isinstance(result, Generator):
            # This is a generator (streaming mode)
            def streaming_with_dependencies():
                all_subtasks = []
                for new_tasks in result:
                    all_subtasks.extend(new_tasks)
                    # Update dependency tracking for each batch of new tasks
                    if new_tasks:
                        self._update_dependencies_for_decomposition(
                            task, all_subtasks
                        )
                    yield new_tasks

            return streaming_with_dependencies()
        else:
            # This is a regular list (non-streaming mode)
            subtasks = result
            # Update dependency tracking for decomposed task
            if subtasks:
                self._update_dependencies_for_decomposition(task, subtasks)
            return subtasks

    def _analyze_failure(
        self, task: Task, error_message: str
    ) -> RecoveryDecision:
        r"""Analyze a task failure and decide on the best recovery strategy.

        Args:
            task (Task): The failed task
            error_message (str): The error message from the failure

        Returns:
            RecoveryDecision: The decided recovery strategy with reasoning
        """
        # First, do a quick smart analysis based on error patterns
        error_msg_lower = error_message.lower()
        if any(
            keyword in error_msg_lower
            for keyword in [
                'connection',
                'network',
                'server disconnected',
                'timeout',
                'apiconnectionerror',
            ]
        ):
            return RecoveryDecision(
                strategy=RecoveryStrategy.RETRY,
                reasoning="Network/connection error detected, retrying task",
                modified_task_content=None,
            )

        # Create failure context
        failure_context = FailureContext(
            task_id=task.id,
            task_content=task.content,
            failure_count=task.failure_count,
            error_message=error_message,
            worker_id=task.assigned_worker_id,
            task_depth=task.get_depth(),
            additional_info=str(task.additional_info)
            if task.additional_info
            else None,
        )

        # Format the analysis prompt
        analysis_prompt = FAILURE_ANALYSIS_PROMPT.format(
            task_id=failure_context.task_id,
            task_content=failure_context.task_content,
            failure_count=failure_context.failure_count,
            error_message=failure_context.error_message,
            worker_id=failure_context.worker_id or "unknown",
            task_depth=failure_context.task_depth,
            additional_info=failure_context.additional_info or "None",
        )

        try:
            # Check if we should use structured handler
            if self.use_structured_output_handler:
                # Use structured handler
                enhanced_prompt = (
                    self.structured_handler.generate_structured_prompt(
                        base_prompt=analysis_prompt,
                        schema=RecoveryDecision,
                        examples=[
                            {
                                "strategy": "RETRY",
                                "reasoning": "Temporary network error, "
                                "worth retrying",
                                "modified_task_content": None,
                            }
                        ],
                    )
                )

                self.task_agent.reset()
                response = self.task_agent.step(enhanced_prompt)

                result = self.structured_handler.parse_structured_response(
                    response.msg.content if response.msg else "",
                    schema=RecoveryDecision,
                    fallback_values={
                        "strategy": RecoveryStrategy.RETRY,
                        "reasoning": "Defaulting to retry due to parsing "
                        "issues",
                        "modified_task_content": None,
                    },
                )
                # Ensure we return a RecoveryDecision instance
                if isinstance(result, RecoveryDecision):
                    return result
                elif isinstance(result, dict):
                    return RecoveryDecision(**result)
                else:
                    return RecoveryDecision(
                        strategy=RecoveryStrategy.RETRY,
                        reasoning="Failed to parse recovery decision",
                        modified_task_content=None,
                    )
            else:
                # Use existing native structured output code
                self.task_agent.reset()
                response = self.task_agent.step(
                    analysis_prompt, response_format=RecoveryDecision
                )
                return response.msg.parsed

        except Exception as e:
            logger.warning(
                f"Error during failure analysis: {e}, defaulting to RETRY"
            )
            return RecoveryDecision(
                strategy=RecoveryStrategy.RETRY,
                reasoning=f"Analysis failed due to error: {e!s}, "
                f"defaulting to retry",
                modified_task_content=None,
            )

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
        invalid_ids = [
            task_id for task_id in task_ids if task_id not in tasks_dict
        ]
        if invalid_ids:
            logger.warning(
                f"Task IDs not found in pending tasks: {invalid_ids}"
            )
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
            >>> workforce = Workforce("My Team")
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
                f"Content preview: '{task.content[:50]}...'"
            )
            return task

        self.reset()
        self._task = task
        self._state = WorkforceState.RUNNING
        task.state = TaskState.FAILED  # TODO: Add logic for OPEN

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

    def _start_child_node_when_paused(
        self, start_coroutine: Coroutine
    ) -> None:
        r"""Helper to start a child node when workforce is paused.

        Args:
            start_coroutine: The coroutine to start (e.g., worker_node.start())
        """
        if self._state == WorkforceState.PAUSED and hasattr(
            self, '_child_listening_tasks'
        ):
            if self._loop and not self._loop.is_closed():
                # Use thread-safe coroutine execution for dynamic addition
                child_task: Union[asyncio.Task, concurrent.futures.Future]
                try:
                    # Check if we're in the same thread as the loop
                    current_loop = asyncio.get_running_loop()
                    if current_loop is self._loop:
                        # Same loop context - use create_task
                        child_task = self._loop.create_task(start_coroutine)
                    else:
                        # Different loop context - use thread-safe approach
                        child_task = asyncio.run_coroutine_threadsafe(
                            start_coroutine, self._loop
                        )
                except RuntimeError:
                    # No running loop in current thread - use thread-safe
                    # approach
                    child_task = asyncio.run_coroutine_threadsafe(
                        start_coroutine, self._loop
                    )
                self._child_listening_tasks.append(child_task)
        else:
            # Close the coroutine to prevent RuntimeWarning
            start_coroutine.close()

    def add_single_agent_worker(
        self,
        description: str,
        worker: ChatAgent,
        pool_max_size: int = DEFAULT_WORKER_POOL_SIZE,
    ) -> Workforce:
        r"""Add a worker node to the workforce that uses a single agent.
        Can be called when workforce is paused to dynamically add workers.

        Args:
            description (str): Description of the worker node.
            worker (ChatAgent): The agent to be added.
            pool_max_size (int): Maximum size of the agent pool.
                (default: :obj:`10`)

        Returns:
            Workforce: The workforce node itself.

        Raises:
            RuntimeError: If called while workforce is running (not paused).
            ValueError: If worker has tools and stream mode enabled but
                use_structured_output_handler is False.
        """
        if self._state == WorkforceState.RUNNING:
            raise RuntimeError(
                "Cannot add workers while workforce is running. "
                "Pause the workforce first."
            )

        # Validate worker agent compatibility
        self._validate_agent_compatibility(worker, "Worker agent")

        # Ensure the worker agent shares this workforce's pause control
        self._attach_pause_event_to_agent(worker)

        worker_node = SingleAgentWorker(
            description=description,
            worker=worker,
            pool_max_size=pool_max_size,
            use_structured_output_handler=self.use_structured_output_handler,
        )
        self._children.append(worker_node)

        # If we have a channel set up, set it for the new worker
        if hasattr(self, '_channel') and self._channel is not None:
            worker_node.set_channel(self._channel)

        # If workforce is paused, start the worker's listening task
        self._start_child_node_when_paused(worker_node.start())

        if self.metrics_logger:
            self.metrics_logger.log_worker_created(
                worker_id=worker_node.node_id,
                worker_type='SingleAgentWorker',
                role=worker_node.description,
            )
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
    ) -> Workforce:
        r"""Add a worker node to the workforce that uses `RolePlaying` system.
        Can be called when workforce is paused to dynamically add workers.

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

        Raises:
            RuntimeError: If called while workforce is running (not paused).
        """
        if self._state == WorkforceState.RUNNING:
            raise RuntimeError(
                "Cannot add workers while workforce is running. "
                "Pause the workforce first."
            )
        # Ensure provided kwargs carry pause_event so that internally created
        # ChatAgents (assistant/user/summarizer) inherit it.
        assistant_agent_kwargs = self._ensure_pause_event_in_kwargs(
            assistant_agent_kwargs
        )
        user_agent_kwargs = self._ensure_pause_event_in_kwargs(
            user_agent_kwargs
        )
        summarize_agent_kwargs = self._ensure_pause_event_in_kwargs(
            summarize_agent_kwargs
        )

        worker_node = RolePlayingWorker(
            description=description,
            assistant_role_name=assistant_role_name,
            user_role_name=user_role_name,
            assistant_agent_kwargs=assistant_agent_kwargs,
            user_agent_kwargs=user_agent_kwargs,
            summarize_agent_kwargs=summarize_agent_kwargs,
            chat_turn_limit=chat_turn_limit,
            use_structured_output_handler=self.use_structured_output_handler,
        )
        self._children.append(worker_node)

        # If we have a channel set up, set it for the new worker
        if hasattr(self, '_channel') and self._channel is not None:
            worker_node.set_channel(self._channel)

        # If workforce is paused, start the worker's listening task
        self._start_child_node_when_paused(worker_node.start())

        if self.metrics_logger:
            self.metrics_logger.log_worker_created(
                worker_id=worker_node.node_id,
                worker_type='RolePlayingWorker',
                role=worker_node.description,
            )
        return self

    def add_workforce(self, workforce: Workforce) -> Workforce:
        r"""Add a workforce node to the workforce.
        Can be called when workforce is paused to dynamically add workers.

        Args:
            workforce (Workforce): The workforce node to be added.

        Returns:
            Workforce: The workforce node itself.

        Raises:
            RuntimeError: If called while workforce is running (not paused).
        """
        if self._state == WorkforceState.RUNNING:
            raise RuntimeError(
                "Cannot add workers while workforce is running. "
                "Pause the workforce first."
            )
        # Align child workforce's pause_event with this one for unified
        # control of worker agents only.
        workforce._pause_event = self._pause_event
        self._children.append(workforce)

        # If we have a channel set up, set it for the new workforce
        if hasattr(self, '_channel') and self._channel is not None:
            workforce.set_channel(self._channel)

        # If workforce is paused, start the child workforce's listening task
        self._start_child_node_when_paused(workforce.start())
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

    def _get_valid_worker_ids(self) -> set:
        r"""Get all valid worker IDs from child nodes.

        Returns:
            set: Set of valid worker IDs that can be assigned tasks.
        """
        valid_worker_ids = {child.node_id for child in self._children}
        return valid_worker_ids

    def _call_coordinator_for_assignment(
        self, tasks: List[Task], invalid_ids: Optional[List[str]] = None
    ) -> TaskAssignResult:
        r"""Call coordinator agent to assign tasks with optional validation
        feedback in the case of invalid worker IDs.

        Args:
            tasks (List[Task]): Tasks to assign.
            invalid_ids (List[str], optional): Invalid worker IDs from previous
                attempt (if any).

        Returns:
            TaskAssignResult: Assignment result from coordinator.
        """
        # format tasks information for the prompt
        tasks_info = ""
        for task in tasks:
            tasks_info += f"Task ID: {task.id}\n"
            tasks_info += f"Content: {task.content}\n"
            if task.additional_info:
                tasks_info += f"Additional Info: {task.additional_info}\n"
            tasks_info += "---\n"

        prompt = str(
            ASSIGN_TASK_PROMPT.format(
                tasks_info=tasks_info,
                child_nodes_info=self._get_child_nodes_info(),
            )
        )

        # add feedback if this is a retry
        if invalid_ids:
            valid_worker_ids = list(self._get_valid_worker_ids())
            feedback = (
                f"VALIDATION ERROR: The following worker IDs are invalid: "
                f"{invalid_ids}. "
                f"VALID WORKER IDS: {valid_worker_ids}. "
                f"Please reassign ONLY the above tasks using these valid IDs."
            )
            prompt = prompt + f"\n\n{feedback}"

        # Check if we should use structured handler
        if self.use_structured_output_handler:
            # Use structured handler for prompt-based extraction
            enhanced_prompt = (
                self.structured_handler.generate_structured_prompt(
                    base_prompt=prompt,
                    schema=TaskAssignResult,
                    examples=[
                        {
                            "assignments": [
                                {
                                    "task_id": "task_1",
                                    "assignee_id": "worker_123",
                                    "dependencies": [],
                                }
                            ]
                        }
                    ],
                )
            )

            # Get response without structured format
            response = self.coordinator_agent.step(enhanced_prompt)

            if response.msg is None or response.msg.content is None:
                logger.error(
                    "Coordinator agent returned empty response for "
                    "task assignment"
                )
                return TaskAssignResult(assignments=[])

            # Parse with structured handler
            result = self.structured_handler.parse_structured_response(
                response.msg.content,
                schema=TaskAssignResult,
                fallback_values={"assignments": []},
            )
            # Ensure we return a TaskAssignResult instance
            if isinstance(result, TaskAssignResult):
                return result
            elif isinstance(result, dict):
                return TaskAssignResult(**result)
            else:
                return TaskAssignResult(assignments=[])
        else:
            # Use existing native structured output code
            response = self.coordinator_agent.step(
                prompt, response_format=TaskAssignResult
            )

            if response.msg is None or response.msg.content is None:
                logger.error(
                    "Coordinator agent returned empty response for "
                    "task assignment"
                )
                return TaskAssignResult(assignments=[])

            try:
                result_dict = json.loads(response.msg.content, parse_int=str)
                return TaskAssignResult(**result_dict)
            except json.JSONDecodeError as e:
                logger.error(
                    f"JSON parsing error in task assignment: Invalid response "
                    f"format - {e}. Response content: "
                    f"{response.msg.content[:50]}..."
                )
                return TaskAssignResult(assignments=[])

    def _validate_assignments(
        self, assignments: List[TaskAssignment], valid_ids: Set[str]
    ) -> Tuple[List[TaskAssignment], List[TaskAssignment]]:
        r"""Validate task assignments against valid worker IDs.

        Args:
            assignments (List[TaskAssignment]): Assignments to validate.
            valid_ids (Set[str]): Set of valid worker IDs.

        Returns:
            Tuple[List[TaskAssignment], List[TaskAssignment]]:
                (valid_assignments, invalid_assignments)
        """
        valid_assignments: List[TaskAssignment] = []
        invalid_assignments: List[TaskAssignment] = []

        for assignment in assignments:
            if assignment.assignee_id in valid_ids:
                valid_assignments.append(assignment)
            else:
                invalid_assignments.append(assignment)

        return valid_assignments, invalid_assignments

    async def _handle_task_assignment_fallbacks(
        self, tasks: List[Task]
    ) -> List:
        r"""Create new workers for unassigned tasks as fallback.

        Args:
            tasks (List[Task]): Tasks that need new workers.

        Returns:
            List[TaskAssignment]: Assignments for newly created workers.
        """
        fallback_assignments = []

        for task in tasks:
            logger.info(f"Creating new worker for unassigned task {task.id}")
            new_worker = await self._create_worker_node_for_task(task)

            assignment = TaskAssignment(
                task_id=task.id,
                assignee_id=new_worker.node_id,
                dependencies=[],
            )
            fallback_assignments.append(assignment)

        return fallback_assignments

    async def _handle_assignment_retry_and_fallback(
        self,
        invalid_assignments: List[TaskAssignment],
        tasks: List[Task],
        valid_worker_ids: Set[str],
    ) -> List[TaskAssignment]:
        r"""Called if Coordinator agent fails to assign tasks to valid worker
        IDs. Handles retry assignment and fallback worker creation for invalid
        assignments.

        Args:
            invalid_assignments (List[TaskAssignment]): Invalid assignments to
                retry.
            tasks (List[Task]): Original tasks list for task lookup.
            valid_worker_ids (set): Set of valid worker IDs.

        Returns:
            List[TaskAssignment]: Final assignments for the invalid tasks.
        """
        invalid_ids = [a.assignee_id for a in invalid_assignments]
        invalid_tasks = [
            task
            for task in tasks
            if any(a.task_id == task.id for a in invalid_assignments)
        ]

        # handle cases where coordinator returned no assignments at all
        if not invalid_assignments:
            invalid_tasks = tasks  # all tasks need assignment
            logger.warning(
                f"Coordinator returned no assignments. "
                f"Retrying assignment for all {len(invalid_tasks)} tasks."
            )
        else:
            logger.warning(
                f"Invalid worker IDs detected: {invalid_ids}. "
                f"Retrying assignment for {len(invalid_tasks)} tasks."
            )

        # retry assignment with feedback
        retry_result = self._call_coordinator_for_assignment(
            invalid_tasks, invalid_ids
        )
        final_assignments = []

        if retry_result.assignments:
            retry_valid, retry_invalid = self._validate_assignments(
                retry_result.assignments, valid_worker_ids
            )
            final_assignments.extend(retry_valid)

            # collect tasks that are still unassigned for fallback
            if retry_invalid:
                unassigned_tasks = [
                    task
                    for task in invalid_tasks
                    if any(a.task_id == task.id for a in retry_invalid)
                ]
            else:
                unassigned_tasks = []
        else:
            # retry failed completely, all invalid tasks need fallback
            logger.warning("Retry assignment failed")
            unassigned_tasks = invalid_tasks

        # handle fallback for any remaining unassigned tasks
        if unassigned_tasks:
            logger.warning(
                f"Creating fallback workers for {len(unassigned_tasks)} "
                f"unassigned tasks"
            )
            fallback_assignments = (
                await self._handle_task_assignment_fallbacks(unassigned_tasks)
            )
            final_assignments.extend(fallback_assignments)

        return final_assignments

    async def _find_assignee(
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
        valid_worker_ids = self._get_valid_worker_ids()

        logger.debug(
            f"Sending batch assignment request to coordinator "
            f"for {len(tasks)} tasks."
        )

        assignment_result = self._call_coordinator_for_assignment(tasks)

        # validate assignments
        valid_assignments, invalid_assignments = self._validate_assignments(
            assignment_result.assignments, valid_worker_ids
        )

        # check if we have assignments for all tasks
        assigned_task_ids = {
            a.task_id for a in valid_assignments + invalid_assignments
        }
        unassigned_tasks = [t for t in tasks if t.id not in assigned_task_ids]

        # if all assignments are valid and all tasks are assigned, return early
        if not invalid_assignments and not unassigned_tasks:
            return TaskAssignResult(assignments=valid_assignments)

        # handle retry and fallback for
        # invalid assignments and unassigned tasks
        all_problem_assignments = invalid_assignments
        retry_and_fallback_assignments = (
            await self._handle_assignment_retry_and_fallback(
                all_problem_assignments, tasks, valid_worker_ids
            )
        )
        valid_assignments.extend(retry_and_fallback_assignments)

        return TaskAssignResult(assignments=valid_assignments)

    async def _post_task(self, task: Task, assignee_id: str) -> None:
        # Record the start time when a task is posted
        self._task_start_times[task.id] = time.time()

        task.assigned_worker_id = assignee_id

        if self.metrics_logger:
            self.metrics_logger.log_task_started(
                task_id=task.id, worker_id=assignee_id
            )

        try:
            await self._channel.post_task(task, self.node_id, assignee_id)
            self._increment_in_flight_tasks(task.id)
            logger.debug(
                f"Posted task {task.id} to {assignee_id}. "
                f"In-flight tasks: {self._in_flight_tasks}"
            )
        except Exception as e:
            logger.error(
                f"Failed to post task {task.id} to {assignee_id}: {e}"
            )
            print(
                f"{Fore.RED}Failed to post task {task.id} to {assignee_id}: "
                f"{e}{Fore.RESET}"
            )

    async def _post_dependency(self, dependency: Task) -> None:
        await self._channel.post_dependency(dependency, self.node_id)

    async def _create_worker_node_for_task(self, task: Task) -> Worker:
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
        # Check if we should use structured handler
        if self.use_structured_output_handler:
            # Use structured handler
            enhanced_prompt = (
                self.structured_handler.generate_structured_prompt(
                    base_prompt=prompt,
                    schema=WorkerConf,
                    examples=[
                        {
                            "description": "Data analysis specialist",
                            "role": "Data Analyst",
                            "sys_msg": "You are an expert data analyst.",
                        }
                    ],
                )
            )

            response = self.coordinator_agent.step(enhanced_prompt)

            if response.msg is None or response.msg.content is None:
                logger.error(
                    "Coordinator agent returned empty response for "
                    "worker creation"
                )
                new_node_conf = WorkerConf(
                    description=f"Fallback worker for task: "
                    f"{task.content[:50]}...",
                    role="General Assistant",
                    sys_msg="You are a general assistant that can help "
                    "with various tasks.",
                )
            else:
                result = self.structured_handler.parse_structured_response(
                    response.msg.content,
                    schema=WorkerConf,
                    fallback_values={
                        "description": f"Worker for task: "
                        f"{task.content[:50]}...",
                        "role": "Task Specialist",
                        "sys_msg": f"You are a specialist for: {task.content}",
                    },
                )
                # Ensure we have a WorkerConf instance
                if isinstance(result, WorkerConf):
                    new_node_conf = result
                elif isinstance(result, dict):
                    new_node_conf = WorkerConf(**result)
                else:
                    new_node_conf = WorkerConf(
                        description=f"Worker for task: {task.content[:50]}...",
                        role="Task Specialist",
                        sys_msg=f"You are a specialist for: {task.content}",
                    )
        else:
            # Use existing native structured output code
            response = self.coordinator_agent.step(
                prompt, response_format=WorkerConf
            )
            if response.msg is None or response.msg.content is None:
                logger.error(
                    "Coordinator agent returned empty response for "
                    "worker creation"
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
                try:
                    result_dict = json.loads(response.msg.content)
                    new_node_conf = WorkerConf(**result_dict)
                except json.JSONDecodeError as e:
                    logger.error(
                        f"JSON parsing error in worker creation: Invalid "
                        f"response format - {e}. Response content: "
                        f"{response.msg.content[:100]}..."
                    )
                    raise RuntimeError(
                        f"Failed to create worker for task {task.id}: "
                        f"Coordinator agent returned malformed JSON response. "
                    ) from e

        new_agent = await self._create_new_agent(
            new_node_conf.role,
            new_node_conf.sys_msg,
        )

        # Validate the new agent compatibility before creating worker
        try:
            self._validate_agent_compatibility(
                new_agent, f"Agent for task {task.id}"
            )
        except ValueError as e:
            raise ValueError(f"Cannot create worker for task {task.id}: {e!s}")

        new_node = SingleAgentWorker(
            description=new_node_conf.description,
            worker=new_agent,
            pool_max_size=DEFAULT_WORKER_POOL_SIZE,
            use_structured_output_handler=self.use_structured_output_handler,
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

    async def _create_new_agent(self, role: str, sys_msg: str) -> ChatAgent:
        worker_sys_msg = BaseMessage.make_assistant_message(
            role_name=role,
            content=sys_msg,
        )

        if self.new_worker_agent is not None:
            # Clone the template agent to create an independent instance
            cloned_agent = self.new_worker_agent.clone(with_memory=False)
            # Update the system message for the specific role
            cloned_agent._system_message = worker_sys_msg
            cloned_agent.init_messages()  # Initialize with new system message
            return cloned_agent
        else:
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

            return ChatAgent(
                system_message=worker_sys_msg,
                model=model,
                tools=function_list,  # type: ignore[arg-type]
                pause_event=self._pause_event,
            )

    async def _get_returned_task(self) -> Optional[Task]:
        r"""Get the task that's published by this node and just get returned
        from the assignee. Includes timeout handling to prevent indefinite
        waiting.
        """
        try:
            # Add timeout to prevent indefinite waiting
            return await asyncio.wait_for(
                self._channel.get_returned_task_by_publisher(self.node_id),
                timeout=TASK_TIMEOUT_SECONDS,
            )
        except Exception as e:
            error_msg = (
                f"Error getting returned task {e} in "
                f"workforce {self.node_id}. "
                f"Current pending tasks: {len(self._pending_tasks)}, "
                f"In-flight tasks: {self._in_flight_tasks}"
            )
            logger.error(error_msg, exc_info=True)
            return None

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
            batch_result = await self._find_assignee(tasks_to_assign)
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
        # Pre-compute completed task IDs and their states for O(1) lookups
        completed_tasks_info = {t.id: t.state for t in self._completed_tasks}

        for task in self._pending_tasks:
            # A task must be assigned to be considered for posting
            if task.id in self._task_dependencies:
                dependencies = self._task_dependencies[task.id]
                # Check if all dependencies for this task are in the completed
                # set and their state is DONE
                if all(
                    dep_id in completed_tasks_info
                    and completed_tasks_info[dep_id] == TaskState.DONE
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

        # Determine detailed failure information
        # Use the actual error/result stored in task.result
        failure_reason = task.result or "Unknown error"

        # Add context about the worker and task
        worker_id = task.assigned_worker_id or "unknown"
        worker_info = f" (assigned to worker: {worker_id})"

        detailed_error = f"{failure_reason}{worker_info}"

        logger.error(
            f"Task {task.id} failed (attempt "
            f"{task.failure_count}/3): {detailed_error}"
        )

        if self.metrics_logger:
            self.metrics_logger.log_task_failed(
                task_id=task.id,
                worker_id=worker_id,
                error_message=detailed_error,
                metadata={
                    'failure_count': task.failure_count,
                    'task_content': task.content,
                    'result_length': len(task.result) if task.result else 0,
                },
            )

        # Check for immediate halt conditions - return immediately if we
        # should halt
        if task.failure_count >= MAX_TASK_RETRIES:
            logger.error(
                f"Task {task.id} has exceeded maximum retry attempts "
                f"({MAX_TASK_RETRIES}). Final failure "
                f"reason: {detailed_error}. "
                f"Task content: '{task.content[:100]}...'"
            )
            self._cleanup_task_tracking(task.id)
            # Mark task as completed for dependency tracking before halting
            self._completed_tasks.append(task)
            if task.id in self._assignees:
                await self._channel.archive_task(task.id)
            return True

        # If too many tasks are failing rapidly, also halt to prevent infinite
        # loops
        if len(self._pending_tasks) > MAX_PENDING_TASKS_LIMIT:
            logger.error(
                f"Too many pending tasks ({len(self._pending_tasks)} > "
                f"{MAX_PENDING_TASKS_LIMIT}). Halting to prevent task "
                f"explosion. Last failed task: {task.id}"
            )
            self._cleanup_task_tracking(task.id)
            # Mark task as completed for dependency tracking before halting
            self._completed_tasks.append(task)
            if task.id in self._assignees:
                await self._channel.archive_task(task.id)
            return True

        # Use intelligent failure analysis to decide recovery strategy
        recovery_decision = self._analyze_failure(task, detailed_error)

        logger.info(
            f"Task {task.id} failure "
            f"analysis: {recovery_decision.strategy.value} - "
            f"{recovery_decision.reasoning}"
        )

        # Clean up tracking before attempting recovery
        if task.id in self._assignees:
            await self._channel.archive_task(task.id)
        self._cleanup_task_tracking(task.id)

        try:
            if recovery_decision.strategy == RecoveryStrategy.RETRY:
                # Simply retry the task by reposting it
                if task.id in self._assignees:
                    assignee_id = self._assignees[task.id]
                    await self._post_task(task, assignee_id)
                    action_taken = f"retried with same worker {assignee_id}"
                else:
                    # Find a new assignee and retry
                    batch_result = await self._find_assignee([task])
                    assignment = batch_result.assignments[0]
                    self._assignees[task.id] = assignment.assignee_id
                    await self._post_task(task, assignment.assignee_id)
                    action_taken = (
                        f"retried with new worker {assignment.assignee_id}"
                    )

            elif recovery_decision.strategy == RecoveryStrategy.REPLAN:
                # Modify the task content and retry
                if recovery_decision.modified_task_content:
                    task.content = recovery_decision.modified_task_content
                    logger.info(f"Task {task.id} content modified for replan")

                # Repost the modified task
                if task.id in self._assignees:
                    assignee_id = self._assignees[task.id]
                    await self._post_task(task, assignee_id)
                    action_taken = (
                        f"replanned and retried with worker {assignee_id}"
                    )
                else:
                    # Find a new assignee for the replanned task
                    batch_result = await self._find_assignee([task])
                    assignment = batch_result.assignments[0]
                    self._assignees[task.id] = assignment.assignee_id
                    await self._post_task(task, assignment.assignee_id)
                    action_taken = (
                        f"replanned and assigned to "
                        f"worker {assignment.assignee_id}"
                    )

            elif recovery_decision.strategy == RecoveryStrategy.DECOMPOSE:
                # Decompose the task into subtasks
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

                await self._post_ready_tasks()
                action_taken = f"decomposed into {len(subtasks)} subtasks"

                logger.debug(
                    f"Task {task.id} failed and was {action_taken}. "
                    f"Dependencies updated for subtasks."
                )

                # Sync shared memory after task decomposition
                if self.share_memory:
                    logger.info(
                        f"Syncing shared memory after "
                        f"task {task.id} decomposition"
                    )
                    self._sync_shared_memory()

                # Check if any pending tasks are now ready to execute
                await self._post_ready_tasks()
                return False

            elif recovery_decision.strategy == RecoveryStrategy.CREATE_WORKER:
                assignee = await self._create_worker_node_for_task(task)
                await self._post_task(task, assignee.node_id)
                action_taken = (
                    f"created new worker {assignee.node_id} and assigned "
                    f"task {task.id} to it"
                )
        except Exception as e:
            logger.error(f"Recovery strategy failed for task {task.id}: {e}")
            # If max retries reached, halt the workforce
            if task.failure_count >= MAX_TASK_RETRIES:
                self._completed_tasks.append(task)
                return True
            self._completed_tasks.append(task)
            return False

        logger.debug(
            f"Task {task.id} failed and was {action_taken}. "
            f"Updating dependency state."
        )
        # Mark task as completed for dependency tracking
        self._completed_tasks.append(task)

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
            worker_id = task.assigned_worker_id or "unknown"
            processing_time_seconds = None
            token_usage = None

            # Get processing time from task start time or additional info
            if task.id in self._task_start_times:
                processing_time_seconds = (
                    time.time() - self._task_start_times[task.id]
                )
                self._cleanup_task_tracking(task.id)
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
            # Task was already removed from pending queue (common case when
            # it was posted and removed immediately).
            logger.debug(
                f"Completed task {task.id} was already removed from pending "
                "queue (normal for posted tasks)."
            )

        # Archive the task and update dependency tracking
        if task.id in self._assignees:
            await self._channel.archive_task(task.id)

        # Ensure it's in completed tasks set by updating if it exists or
        # appending if it's new.
        task_found_in_completed = False
        for i, t in enumerate(self._completed_tasks):
            if t.id == task.id:
                self._completed_tasks[i] = task
                task_found_in_completed = True
                break
        if not task_found_in_completed:
            self._completed_tasks.append(task)

        # Handle parent task completion logic
        parent = task.parent
        if parent:
            # Check if all subtasks are completed and successful
            all_subtasks_done = all(
                any(
                    t.id == sub.id and t.state == TaskState.DONE
                    for t in self._completed_tasks
                )
                for sub in parent.subtasks
            )
            if all_subtasks_done:
                # Collect results from successful subtasks only
                successful_results = []
                for sub in parent.subtasks:
                    completed_subtask = next(
                        (
                            t
                            for t in self._completed_tasks
                            if t.id == sub.id and t.state == TaskState.DONE
                        ),
                        None,
                    )
                    if completed_subtask and completed_subtask.result:
                        successful_results.append(
                            f"--- Subtask {sub.id} Result ---\n"
                            f"{completed_subtask.result}"
                        )

                # Set parent task state and result
                parent.state = TaskState.DONE
                parent.result = (
                    "\n\n".join(successful_results)
                    if successful_results
                    else "All subtasks completed"
                )

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

                # Get returned task
                returned_task = await self._get_returned_task()

                # If no task was returned, continue
                if returned_task is None:
                    logger.debug(
                        f"No task returned in workforce {self.node_id}. "
                        f"Pending: {len(self._pending_tasks)}, "
                        f"In-flight: {self._in_flight_tasks}"
                    )
                    await self._post_ready_tasks()
                    continue

                self._decrement_in_flight_tasks(
                    returned_task.id, "task returned successfully"
                )

                # Check for stop request after getting task
                if self._stop_requested:
                    logger.info("Stop requested after receiving task.")
                    break

                # Process the returned task based on its state
                if returned_task.state == TaskState.DONE:
                    # Check if the "completed" task actually failed to provide
                    # useful results
                    if is_task_result_insufficient(returned_task):
                        result_preview = (
                            returned_task.result[:100] + "..."
                            if returned_task.result
                            else "No result"
                        )
                        logger.warning(
                            f"Task {returned_task.id} marked as DONE but "
                            f"result is insufficient. "
                            f"Treating as failed. Result: '{result_preview}'"
                        )
                        returned_task.state = TaskState.FAILED
                        try:
                            halt = await self._handle_failed_task(
                                returned_task
                            )
                            if not halt:
                                continue
                            print(
                                f"{Fore.RED}Task {returned_task.id} has "
                                f"failed for {MAX_TASK_RETRIES} times after "
                                f"insufficient results, halting the "
                                f"workforce. Final error: "
                                f"{returned_task.result or 'Unknown error'}"
                                f"{Fore.RESET}"
                            )
                            await self._graceful_shutdown(returned_task)
                            break
                        except Exception as e:
                            logger.error(
                                f"Error handling insufficient task result "
                                f"{returned_task.id}: {e}",
                                exc_info=True,
                            )
                            continue
                    else:
                        print(
                            f"{Fore.CYAN}🎯 Task {returned_task.id} completed "
                            f"successfully.{Fore.RESET}"
                        )
                        await self._handle_completed_task(returned_task)
                elif returned_task.state == TaskState.FAILED:
                    try:
                        halt = await self._handle_failed_task(returned_task)
                        if not halt:
                            continue
                        print(
                            f"{Fore.RED}Task {returned_task.id} has failed "
                            f"for {MAX_TASK_RETRIES} times, halting "
                            f"the workforce. Final error: "
                            f"{returned_task.result or 'Unknown error'}"
                            f"{Fore.RESET}"
                        )
                        # Graceful shutdown instead of immediate break
                        await self._graceful_shutdown(returned_task)
                        break
                    except Exception as e:
                        logger.error(
                            f"Error handling failed task "
                            f"{returned_task.id}: {e}",
                            exc_info=True,
                        )
                        # Continue to prevent hanging
                        continue
                elif returned_task.state == TaskState.OPEN:
                    # TODO: Add logic for OPEN
                    pass
                else:
                    raise ValueError(
                        f"Task {returned_task.id} has an unexpected state."
                    )

            except Exception as e:
                # Decrement in-flight counter to prevent hanging
                self._decrement_in_flight_tasks(
                    "unknown", "exception in task processing loop"
                )

                logger.error(
                    f"Error processing task in workforce {self.node_id}: {e}"
                    f"Workforce state - Pending tasks: "
                    f"{len(self._pending_tasks)}, "
                    f"In-flight tasks: {self._in_flight_tasks}, "
                    f"Completed tasks: {len(self._completed_tasks)}"
                )

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
            coordinator_agent=self.coordinator_agent.clone(with_memory),
            task_agent=self.task_agent.clone(with_memory),
            new_worker_agent=self.new_worker_agent.clone(with_memory)
            if self.new_worker_agent
            else None,
            graceful_shutdown_timeout=self.graceful_shutdown_timeout,
            share_memory=self.share_memory,
            use_structured_output_handler=self.use_structured_output_handler,
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

                # Validate agent compatibility
                try:
                    workforce_instance._validate_agent_compatibility(
                        agent, "Worker agent"
                    )
                except ValueError as e:
                    return {
                        "status": "error",
                        "message": str(e),
                    }

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
