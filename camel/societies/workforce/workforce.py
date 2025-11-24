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
import os
import time
import uuid
from collections import deque
from enum import Enum
from typing import (
    TYPE_CHECKING,
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
    cast,
)

from .workforce_callback import WorkforceCallback
from .workforce_metrics import WorkforceMetrics

if TYPE_CHECKING:
    from camel.utils.context_utils import ContextUtility

from colorama import Fore

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce.base import BaseNode
from camel.societies.workforce.prompts import (
    ASSIGN_TASK_PROMPT,
    CREATE_NODE_PROMPT,
    FAILURE_ANALYSIS_RESPONSE_FORMAT,
    QUALITY_EVALUATION_RESPONSE_FORMAT,
    TASK_AGENT_SYSTEM_MESSAGE,
    TASK_ANALYSIS_PROMPT,
    TASK_DECOMPOSE_PROMPT,
)
from camel.societies.workforce.role_playing_worker import RolePlayingWorker
from camel.societies.workforce.single_agent_worker import (
    SingleAgentWorker,
)
from camel.societies.workforce.structured_output_handler import (
    StructuredOutputHandler,
)
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import (
    PipelineTaskBuilder,
    RecoveryStrategy,
    TaskAnalysisResult,
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
    FunctionTool,
    SearchToolkit,
    ThinkingToolkit,
)
from camel.types import ModelPlatformType, ModelType
from camel.utils import dependencies_required

from .events import (
    AllTasksCompletedEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDecomposedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    WorkerCreatedEvent,
)

if os.environ.get("TRACEROOT_ENABLED", "False").lower() == "true":
    try:
        import traceroot  # type: ignore[import]

        logger = traceroot.get_logger('camel')
    except ImportError:
        logger = get_logger(__name__)
else:
    logger = get_logger(__name__)

# Constants for configuration values
MAX_TASK_RETRIES = 3
MAX_PENDING_TASKS_LIMIT = 20
TASK_TIMEOUT_SECONDS = 600.0
DEFAULT_WORKER_POOL_SIZE = 10


class WorkforceState(Enum):
    r"""Workforce execution state for human intervention support."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"


class WorkforceMode(Enum):
    r"""Workforce execution mode for different task processing strategies."""

    AUTO_DECOMPOSE = "auto_decompose"  # Automatic task decomposition mode
    PIPELINE = "pipeline"  # Predefined pipeline mode


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
            model configuration but with the required system message. If None,
            a default agent will be created using DEFAULT model settings.
            (default: :obj:`None`)
        new_worker_agent (Optional[ChatAgent], optional): A template agent for
            workers created dynamically at runtime when existing workers cannot
            handle failed tasks. If None, workers will be created with default
            settings including SearchToolkit, CodeExecutionToolkit, and
            ThinkingToolkit. (default: :obj:`None`)
        graceful_shutdown_timeout (float, optional): The timeout in seconds
            for graceful shutdown when a task fails 3 times. During this
            period, the workforce remains active for debugging.
            Set to 0 for immediate shutdown. (default: :obj:`15.0`)
        task_timeout_seconds (Optional[float], optional): The timeout in
            seconds for waiting for tasks to be returned by workers. If None,
            uses the global TASK_TIMEOUT_SECONDS value (600.0 seconds).
            Increase this value for tasks that require more processing time.
            (default: :obj:`None`)
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
        callbacks (Optional[List[WorkforceCallback]], optional): A list of
            callback handlers to observe and record workforce lifecycle events
            and metrics (e.g., task creation/assignment/start/completion/
            failure, worker creation/deletion, all-tasks-completed). All
            items must be instances of :class:`WorkforceCallback`, otherwise
            a :class:`ValueError` is raised. If none of the provided
            callbacks implement :class:`WorkforceMetrics`, a built-in
            :class:`WorkforceLogger` (implements both callback and metrics)
            is added automatically. If at least one provided callback
            implements :class:`WorkforceMetrics`, no default logger is added.
            (default: :obj:`None`)
        mode (WorkforceMode, optional): The execution mode for task
            processing. AUTO_DECOMPOSE mode uses intelligent recovery
            strategies (decompose, replan, etc.) when tasks fail.
            PIPELINE mode uses simple retry logic and allows failed
            tasks to continue the workflow, passing error information
            to dependent tasks. (default: :obj:`WorkforceMode.AUTO_DECOMPOSE`)

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
        task_timeout_seconds: Optional[float] = None,
        mode: WorkforceMode = WorkforceMode.AUTO_DECOMPOSE,
        callbacks: Optional[List[WorkforceCallback]] = None,
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
        self.task_timeout_seconds = (
            task_timeout_seconds or TASK_TIMEOUT_SECONDS
        )
        self.mode = mode
        self._initial_mode = mode  # Store initial mode for reset()
        if self.use_structured_output_handler:
            self.structured_handler = StructuredOutputHandler()
        self._task: Optional[Task] = None
        self._pending_tasks: Deque[Task] = deque()
        self._task_dependencies: Dict[str, List[str]] = {}
        self._assignees: Dict[str, str] = {}
        self._in_flight_tasks: int = 0

        # Pipeline building state
        self._pipeline_builder: Optional[PipelineTaskBuilder] = None
        # Dictionary to track task start times
        self._task_start_times: Dict[str, float] = {}
        # Human intervention support
        self._state = WorkforceState.IDLE
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initially not paused
        self._stop_requested = False
        self._skip_requested = False
        self._snapshots: List[WorkforceSnapshot] = []
        self._completed_tasks: List[Task] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._main_task_future: Optional[asyncio.Future] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        # Snapshot throttle support
        self._last_snapshot_time: float = 0.0
        # Minimum seconds between automatic snapshots
        self.snapshot_interval: float = 30.0
        # Shared memory UUID tracking to prevent re-sharing duplicates
        self._shared_memory_uuids: Set[str] = set()
        self._initialize_callbacks(callbacks)

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
                    f"{user_sys_msg_content}\n\n{coord_agent_sys_msg.content}"
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
                tools=list(coordinator_agent._internal_tools.values()),
                external_tools=[
                    schema
                    for schema in coordinator_agent._external_tool_schemas.values()  # noqa: E501
                ],
                response_terminators=coordinator_agent.response_terminators,
                max_iteration=coordinator_agent.max_iteration,
                stop_event=coordinator_agent.stop_event,
            )

        # Set up task agent with default system message
        task_sys_msg = BaseMessage.make_assistant_message(
            role_name="Task Planner",
            content=TASK_AGENT_SYSTEM_MESSAGE,
        )

        if task_agent is None:
            logger.warning(
                "No task_agent provided. Using default ChatAgent "
                "settings (ModelPlatformType.DEFAULT, ModelType.DEFAULT) "
                "with default system message."
            )
            self.task_agent = ChatAgent(
                task_sys_msg,
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
                    f"{user_task_sys_msg_content}\n\n{task_sys_msg.content}"
                )
                combined_task_sys_msg = BaseMessage.make_assistant_message(
                    role_name=task_agent.system_message.role_name,
                    content=combined_task_content,
                )
            else:
                combined_task_sys_msg = task_sys_msg

            # Since ChatAgent constructor uses a dictionary with
            # function names as keys, we don't need to manually deduplicate.
            combined_tools: List[Union[FunctionTool, Callable]] = cast(
                List[Union[FunctionTool, Callable]],
                list(task_agent._internal_tools.values()),
            )

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

        # Shared context utility for workflow management (created lazily)
        self._shared_context_utility: Optional["ContextUtility"] = None

        # ------------------------------------------------------------------
        # Helper for propagating pause control to externally supplied agents
        # ------------------------------------------------------------------

    def _initialize_callbacks(
        self, callbacks: Optional[List[WorkforceCallback]]
    ) -> None:
        r"""Validate, register, and prime workforce callbacks."""
        self._callbacks: List[WorkforceCallback] = []

        if callbacks:
            for cb in callbacks:
                if not isinstance(cb, WorkforceCallback):
                    raise ValueError(
                        "All callbacks must be instances of WorkforceCallback"
                    )
                self._callbacks.append(cb)
        # Check if any metrics callback is provided
        has_metrics_callback = any(
            isinstance(cb, WorkforceMetrics) for cb in self._callbacks
        )

        if not has_metrics_callback:
            # Add default WorkforceLogger if no metrics callback provided
            try:
                from camel.societies.workforce.workforce_logger import (
                    WorkforceLogger,
                )

                self._callbacks.append(
                    WorkforceLogger(workforce_id=self.node_id)
                )
            except ImportError:
                # If WorkforceLogger is not available, continue without it
                pass
        else:
            logger.info(
                "WorkforceMetrics implementation detected. Skipping default "
                "WorkforceLogger addition."
            )

        for child in self._children:
            self._notify_worker_created(child)

    def _notify_worker_created(
        self,
        worker_node: BaseNode,
        *,
        worker_type: Optional[str] = None,
        role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        r"""Emit a worker-created event to all registered callbacks."""
        event = WorkerCreatedEvent(
            worker_id=worker_node.node_id,
            worker_type=worker_type or type(worker_node).__name__,
            role=role or worker_node.description,
            metadata=metadata,
        )
        for cb in self._callbacks:
            cb.log_worker_created(event)

    def _get_or_create_shared_context_utility(
        self,
        session_id: Optional[str] = None,
    ) -> "ContextUtility":
        r"""Get or create the shared context utility for workflow management.

        This method creates the context utility only when needed, avoiding
        unnecessary session folder creation during initialization.

        Args:
            session_id (Optional[str]): Custom session ID to use. If None,
                auto-generates a timestamped session ID. (default: :obj:`None`)

        Returns:
            ContextUtility: The shared context utility instance.
        """
        if self._shared_context_utility is None:
            from camel.utils.context_utils import ContextUtility

            self._shared_context_utility = ContextUtility.get_workforce_shared(
                session_id=session_id
            )
        return self._shared_context_utility

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

    # ------------------------------------------------------------------
    # Helper for propagating pause control to externally supplied agents
    # ------------------------------------------------------------------
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
            f"State: {self._state.value} - Mode: {self.mode.value}"
        )

    def set_mode(self, mode: WorkforceMode) -> Workforce:
        """Set the execution mode of the workforce.

        This allows switching between AUTO_DECOMPOSE and PIPELINE modes.
        Useful when you want to reuse the same workforce instance for
        different task processing strategies.

        Args:
            mode (WorkforceMode): The desired execution mode.
                - AUTO_DECOMPOSE: Intelligent task decomposition with recovery
                - PIPELINE: Predefined task pipeline with simple retry logic

        Returns:
            Workforce: Self for method chaining.

        Example:
            >>> # Run a pipeline
            >>> workforce.set_mode(WorkforceMode.PIPELINE)
            >>> workforce.pipeline_add("Step 1").pipeline_build()
            >>> workforce.process_task(task)
            >>>
            >>> # Reset to original mode
            >>> workforce.reset()  # Automatically resets to initial mode
            >>> # Or manually switch mode
            >>> workforce.set_mode(WorkforceMode.AUTO_DECOMPOSE)
            >>> workforce.process_task(another_task)
        """
        self.mode = mode
        logger.info(f"Workforce mode changed to {mode.value}")
        return self

    def _ensure_pipeline_builder(self) -> PipelineTaskBuilder:
        """Ensure pipeline builder is initialized and switch to
        pipeline mode.

        Returns:
            PipelineTaskBuilder: The initialized pipeline builder instance.
        """
        if self._pipeline_builder is None:
            from camel.societies.workforce.utils import PipelineTaskBuilder

            self._pipeline_builder = PipelineTaskBuilder()

        # Auto-switch to pipeline mode
        if self.mode != WorkforceMode.PIPELINE:
            logger.info(
                f"Auto-switching workforce mode from {self.mode.value} to "
                f"PIPELINE. Use workforce.set_mode() to manually control mode."
            )
            self.mode = WorkforceMode.PIPELINE

        return self._pipeline_builder

    def pipeline_add(
        self,
        content: Union[str, Task],
        task_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        auto_depend: bool = True,
    ) -> Workforce:
        """Add a task to the pipeline with support for chaining.

        Accepts either a string for simple tasks or a Task object for
        advanced usage with metadata, images, or custom configurations.

        Args:
            content (Union[str, Task]): The task content string or a Task
                object. If a Task object is provided, task_id and
                additional_info parameters are ignored.
            task_id (str, optional): Unique identifier for the task. If None,
                a unique ID will be generated. Only used when content is a
                string. (default: :obj:`None`)
            dependencies (List[str], optional): List of task IDs that this
                task depends on. If None and auto_depend=True, will depend on
                the last added task. (default: :obj:`None`)
            additional_info (Dict[str, Any], optional): Additional information
                for the task. Only used when content is a string.
                (default: :obj:`None`)
            auto_depend (bool, optional): If True and dependencies is None,
                automatically depend on the last added task.
                (default: :obj:`True`)

        Returns:
            Workforce: Self for method chaining.

        Example:
            >>> # Simple usage with strings
            >>> workforce.pipeline_add("Step 1").pipeline_add("Step 2")
            >>>
            >>> # Advanced usage with Task objects
            >>> task = Task(
            ...     content="Complex Task",
            ...     additional_info={"priority": "high"},
            ...     image_list=["path/to/image.png"]
            ... )
            >>> workforce.pipeline_add(task)
        """
        builder = self._ensure_pipeline_builder()

        # Convert Task object to parameters if needed
        if isinstance(content, Task):
            task_content = content.content
            task_id = content.id
            task_additional_info = content.additional_info
        else:
            task_content = content
            task_additional_info = additional_info

        builder.add(
            task_content,
            task_id,
            dependencies,
            task_additional_info,
            auto_depend,
        )
        return self

    def add_parallel_pipeline_tasks(
        self,
        task_contents: Union[List[str], List[Task]],
        dependencies: Optional[List[str]] = None,
        task_id_prefix: str = "parallel",
        auto_depend: bool = True,
    ) -> Workforce:
        """Add multiple parallel tasks to the pipeline.

        Accepts either a list of strings for simple tasks or a list of Task
        objects for advanced usage with metadata, images, or custom
        configurations.

        Args:
            task_contents (Union[List[str], List[Task]]): List of task content
                strings or Task objects. If Task objects are provided,
                task_id_prefix is ignored.
            dependencies (List[str], optional): Common dependencies for all
                parallel tasks. (default: :obj:`None`)
            task_id_prefix (str, optional): Prefix for generated task IDs.
                Only used when task_contents contains strings.
                (default: :obj:`"parallel"`)
            auto_depend (bool, optional): If True and dependencies is None,
                automatically depend on the last added task.
                (default: :obj:`True`)

        Returns:
            Workforce: Self for method chaining.

        Example:
            >>> # Simple usage with strings
            >>> workforce.add_parallel_pipeline_tasks([
            ...     "Task A", "Task B", "Task C"
            ... ])
            >>>
            >>> # Advanced usage with Task objects
            >>> tasks = [
            ...     Task(
            ...         content="Analysis 1",
            ...         additional_info={"type": "tech"},
            ...     ),
            ...     Task(
            ...         content="Analysis 2",
            ...         additional_info={"type": "biz"},
            ...     ),
            ... ]
            >>> workforce.add_parallel_pipeline_tasks(tasks)
        """
        builder = self._ensure_pipeline_builder()

        # Convert Task objects to content strings if needed
        if task_contents and isinstance(task_contents[0], Task):
            # Extract content from Task objects
            task_list = cast(List[Task], task_contents)
            content_list = [task.content for task in task_list]
            builder.add_parallel_tasks(
                content_list, dependencies, task_id_prefix, auto_depend
            )
        else:
            # task_contents is List[str] in else branch
            builder.add_parallel_tasks(
                task_contents,  # type: ignore[arg-type]
                dependencies,
                task_id_prefix,
                auto_depend,
            )
        return self

    def add_sync_pipeline_task(
        self,
        content: Union[str, Task],
        wait_for: Optional[List[str]] = None,
        task_id: Optional[str] = None,
    ) -> Workforce:
        """Add a synchronization task that waits for multiple tasks.

        Accepts either a string for simple tasks or a Task object for
        advanced usage with metadata, images, or custom configurations.

        Args:
            content (Union[str, Task]): Content of the synchronization task
                or a Task object. If a Task object is provided, task_id
                parameter is ignored.
            wait_for (List[str], optional): List of task IDs to wait for.
                If None, will automatically wait for the last parallel tasks.
                (default: :obj:`None`)
            task_id (str, optional): ID for the sync task. Only used when
                content is a string. (default: :obj:`None`)

        Returns:
            Workforce: Self for method chaining.

        Example:
            >>> # Simple usage
            >>> workforce.add_sync_pipeline_task("Merge Results")
            >>>
            >>> # Advanced usage with Task object
            >>> sync_task = Task(
            ...     content="Combine outputs",
            ...     additional_info={"type": "aggregation"}
            ... )
            >>> workforce.add_sync_pipeline_task(sync_task)
        """
        builder = self._ensure_pipeline_builder()

        # Convert Task object to parameters if needed
        if isinstance(content, Task):
            task_content = content.content
            task_id = content.id
        else:
            task_content = content

        builder.add_sync_task(task_content, wait_for, task_id)
        return self

    def pipeline_fork(
        self, task_contents: Union[List[str], List[Task]]
    ) -> Workforce:
        """Create parallel branches from the current task.

        Accepts either a list of strings for simple tasks or a list of Task
        objects for advanced usage with metadata, images, or custom
        configurations.

        Args:
            task_contents (Union[List[str], List[Task]]): List of task content
                strings or Task objects for parallel execution.

        Returns:
            Workforce: Self for method chaining.

        Example:
            >>> # Simple usage with strings
            >>> workforce.pipeline_add("Collect Data").pipeline_fork(
            ...     ["Technical Analysis", "Fundamental Analysis"]
            ... ).pipeline_join("Generate Report")
            >>>
            >>> # Advanced usage with Task objects
            >>> tasks = [
            ...     Task(
            ...         content="Parse JSON",
            ...         additional_info={"format": "json"},
            ...     ),
            ...     Task(
            ...         content="Parse XML",
            ...         additional_info={"format": "xml"},
            ...     ),
            ... ]
            >>> workforce.pipeline_add("Fetch Data").pipeline_fork(tasks)
        """
        builder = self._ensure_pipeline_builder()

        # Convert Task objects to content strings if needed
        if task_contents and isinstance(task_contents[0], Task):
            # Extract content from Task objects
            task_list = cast(List[Task], task_contents)
            content_list = [task.content for task in task_list]
            builder.fork(content_list)
        else:
            # task_contents is List[str] in else branch
            builder.fork(task_contents)  # type: ignore[arg-type]
        return self

    def pipeline_join(
        self, content: Union[str, Task], task_id: Optional[str] = None
    ) -> Workforce:
        """Join parallel branches with a synchronization task.

        Accepts either a string for simple tasks or a Task object for
        advanced usage with metadata, images, or custom configurations.

        Args:
            content (Union[str, Task]): Content of the join/sync task or a
                Task object. If a Task object is provided, task_id parameter
                is ignored.
            task_id (str, optional): ID for the sync task. Only used when
                content is a string. (default: :obj:`None`)

        Returns:
            Workforce: Self for method chaining.

        Example:
            >>> # Simple usage
            >>> workforce.pipeline_fork(["Task A", "Task B"]).pipeline_join(
            ...     "Merge Results"
            ... )
            >>>
            >>> # Advanced usage with Task object
            >>> join_task = Task(
            ...     content="Aggregate analysis",
            ...     additional_info={"aggregation_type": "mean"}
            ... )
            >>> workforce.pipeline_fork(["A", "B"]).pipeline_join(join_task)
        """
        builder = self._ensure_pipeline_builder()

        # Convert Task object to parameters if needed
        if isinstance(content, Task):
            task_content = content.content
            task_id = content.id
        else:
            task_content = content

        builder.join(task_content, task_id)
        return self

    def pipeline_build(self) -> Workforce:
        """Build the pipeline and set up the tasks for execution.

        Returns:
            Workforce: Self for method chaining.

        Example:
            >>> workforce.pipeline_add("Step 1").pipeline_fork(
            ...     ["Task A", "Task B"]
            ... ).pipeline_join("Merge").pipeline_build()
        """
        if self._pipeline_builder is None:
            raise ValueError("No pipeline tasks defined")

        tasks = self._pipeline_builder.build()
        self.set_pipeline_tasks(tasks)

        return self

    def get_pipeline_builder(self) -> PipelineTaskBuilder:
        """Get the underlying PipelineTaskBuilder for advanced usage.

        Returns:
            PipelineTaskBuilder: The pipeline builder instance.

        Example:
            >>> builder = workforce.get_pipeline_builder()
            >>> builder.add("Complex Task").fork(["A", "B"]).join("Merge")
            >>> tasks = builder.build()
            >>> workforce.set_pipeline_tasks(tasks)
        """
        return self._ensure_pipeline_builder()

    def set_pipeline_tasks(self, tasks: List[Task]) -> None:
        """Set predefined pipeline tasks for PIPELINE mode.

        Args:
            tasks (List[Task]): List of tasks with dependencies already set.
                The dependencies should be Task objects in the
                Task.dependencies attribute.

        Raises:
            ValueError: If tasks are invalid.
        """
        if not tasks:
            raise ValueError("Cannot set empty task list for pipeline")

        # Auto-switch to pipeline mode if not already
        if self.mode != WorkforceMode.PIPELINE:
            self.mode = WorkforceMode.PIPELINE

        # Clear existing tasks and dependencies
        self._pending_tasks.clear()
        self._task_dependencies.clear()
        self._assignees.clear()

        # Add tasks and set up dependencies
        for task in tasks:
            self._pending_tasks.append(task)
            if task.dependencies:
                self._task_dependencies[task.id] = [
                    dep.id for dep in task.dependencies
                ]
            else:
                self._task_dependencies[task.id] = []

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

            # Filter out already-shared records to prevent re-sharing
            # This prevents exponential growth of duplicate records
            new_records = []
            for record in memory_records:
                record_uuid = str(record.uuid)
                if record_uuid not in self._shared_memory_uuids:
                    new_records.append(record)
                    self._shared_memory_uuids.add(record_uuid)

            if not new_records:
                logger.debug(
                    "No new records to share (all were already shared)"
                )
                return

            # Share with coordinator agent
            for record in new_records:
                # Only add records from other agents to avoid duplication
                if record.agent_id != self.coordinator_agent.agent_id:
                    self.coordinator_agent.memory.write_record(record)

            # Share with task agent
            for record in new_records:
                if record.agent_id != self.task_agent.agent_id:
                    self.task_agent.memory.write_record(record)

            # Share with SingleAgentWorker instances only
            single_agent_workers = [
                child
                for child in self._children
                if isinstance(child, SingleAgentWorker)
            ]

            for worker in single_agent_workers:
                for record in new_records:
                    if record.agent_id != worker.worker.agent_id:
                        worker.worker.memory.write_record(record)

            logger.info(
                f"Shared {len(new_records)} new memory records across "
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

        Args:
            task (Task): The task to decompose.

        Returns:
            Union[List[Task], Generator[List[Task], None, None]]:
            The subtasks or generator of subtasks. Returns empty list for
            PIPELINE mode.
        """
        # In PIPELINE mode, don't decompose - use predefined tasks
        if self.mode == WorkforceMode.PIPELINE:
            return []

        decompose_prompt = str(
            TASK_DECOMPOSE_PROMPT.format(
                content=task.content,
                child_nodes_info=self._get_child_nodes_info(),
                additional_info=task.additional_info,
            )
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

    def _analyze_task(
        self,
        task: Task,
        *,
        for_failure: bool,
        error_message: Optional[str] = None,
    ) -> TaskAnalysisResult:
        r"""Unified task analysis for both failures and quality evaluation.

        This method consolidates the logic for analyzing task failures and
        evaluating task quality, using the unified TASK_ANALYSIS_PROMPT.

        Args:
            task (Task): The task to analyze
            for_failure (bool): True for failure analysis, False for quality
                evaluation
            error_message (Optional[str]): Error message, required when
                for_failure=True

        Returns:
            TaskAnalysisResult: Unified analysis result with recovery strategy
                and optional quality metrics

        Raises:
            ValueError: If for_failure=True but error_message is None
        """
        # Validate required parameters
        if for_failure and error_message is None:
            raise ValueError("error_message is required when for_failure=True")

        # Determine task result and issue-specific analysis based on context
        if for_failure:
            task_result = "N/A (task failed)"
            issue_type = "Task Failure"
            issue_analysis = f"**Error Message:** {error_message}"
            response_format = FAILURE_ANALYSIS_RESPONSE_FORMAT
            result_schema = TaskAnalysisResult
            fallback_values: Dict[str, Any] = {
                "reasoning": "Defaulting to retry due to parsing error",
                "recovery_strategy": RecoveryStrategy.RETRY,
                "modified_task_content": None,
                "issues": [error_message] if error_message else [],
            }
            examples: List[Dict[str, Any]] = [
                {
                    "reasoning": "Temporary network error, worth retrying",
                    "recovery_strategy": "retry",
                    "modified_task_content": None,
                    "issues": ["Network timeout"],
                }
            ]
        else:
            # Quality evaluation
            task_result = task.result or "No result available"
            issue_type = "Quality Evaluation"
            issue_analysis = (
                "Provide a quality score (0-100) and list any specific "
                "issues found."
            )
            response_format = QUALITY_EVALUATION_RESPONSE_FORMAT
            result_schema = TaskAnalysisResult
            fallback_values = {
                "reasoning": (
                    "Defaulting to acceptable quality due to parsing error"
                ),
                "issues": [],
                "recovery_strategy": None,
                "modified_task_content": None,
                "quality_score": 80,
            }
            examples = [
                {
                    "reasoning": (
                        "Excellent implementation with comprehensive tests"
                    ),
                    "issues": [],
                    "recovery_strategy": None,
                    "modified_task_content": None,
                    "quality_score": 98,
                },
                {
                    "reasoning": (
                        "Implementation incomplete with missing features"
                    ),
                    "issues": [
                        "Incomplete implementation",
                        "Missing error handling",
                    ],
                    "recovery_strategy": "replan",
                    "modified_task_content": (
                        "Previous attempt was incomplete. "
                        "Please implement with: 1) Full feature "
                        "coverage, 2) Proper error handling"
                    ),
                    "quality_score": 45,
                },
            ]

        # Format the unified analysis prompt
        analysis_prompt = str(
            TASK_ANALYSIS_PROMPT.format(
                task_id=task.id,
                task_content=task.content,
                task_result=task_result,
                failure_count=task.failure_count,
                task_depth=task.get_depth(),
                assigned_worker=task.assigned_worker_id or "unknown",
                issue_type=issue_type,
                issue_specific_analysis=issue_analysis,
                response_format=response_format,
            )
        )

        try:
            if self.use_structured_output_handler:
                enhanced_prompt = (
                    self.structured_handler.generate_structured_prompt(
                        base_prompt=analysis_prompt,
                        schema=result_schema,
                        examples=examples,
                    )
                )

                self.task_agent.reset()
                response = self.task_agent.step(enhanced_prompt)

                result = self.structured_handler.parse_structured_response(
                    response.msg.content if response.msg else "",
                    schema=result_schema,
                    fallback_values=fallback_values,
                )

                if isinstance(result, TaskAnalysisResult):
                    return result
                elif isinstance(result, dict):
                    return result_schema(**result)
                else:
                    # Fallback based on context
                    return TaskAnalysisResult(**fallback_values)
            else:
                self.task_agent.reset()
                response = self.task_agent.step(
                    analysis_prompt, response_format=result_schema
                )
                return response.msg.parsed

        except Exception as e:
            logger.warning(
                f"Error during task analysis "
                f"({'failure' if for_failure else 'quality'}): {e}, "
                f"using fallback"
            )
            return TaskAnalysisResult(**fallback_values)

    async def _apply_recovery_strategy(
        self,
        task: Task,
        recovery_decision: TaskAnalysisResult,
    ) -> bool:
        r"""Apply the recovery strategy from a task analysis result.

        This method centralizes the recovery logic for both execution failures
        and quality-based failures.

        Args:
            task (Task): The task that needs recovery
            recovery_decision (TaskAnalysisResult): The analysis result with
                recovery strategy

        Returns:
            bool: True if workforce should halt (e.g., decompose needs
                different handling), False otherwise
        """
        strategy = (
            recovery_decision.recovery_strategy or RecoveryStrategy.RETRY
        )
        action_taken = ""

        try:
            if strategy == RecoveryStrategy.RETRY:
                # Simply retry the task by reposting it to the same worker
                # Check both _assignees dict and task.assigned_worker_id
                assignee_id = (
                    self._assignees.get(task.id) or task.assigned_worker_id
                )

                if assignee_id:
                    # Retry with the same worker - no coordinator call needed
                    await self._post_task(task, assignee_id)
                    action_taken = f"retried with same worker {assignee_id}"
                    logger.info(
                        f"Task {task.id} retrying with same worker "
                        f"{assignee_id} (no coordinator call)"
                    )
                else:
                    # No previous assignment exists - find a new assignee
                    logger.info(
                        f"Task {task.id} has no previous assignee, "
                        f"calling coordinator"
                    )
                    batch_result = await self._find_assignee([task])
                    assignment = batch_result.assignments[0]
                    self._assignees[task.id] = assignment.assignee_id
                    await self._post_task(task, assignment.assignee_id)
                    action_taken = (
                        f"retried with new worker {assignment.assignee_id}"
                    )

            elif strategy == RecoveryStrategy.REPLAN:
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

            elif strategy == RecoveryStrategy.REASSIGN:
                # Reassign to a different worker
                old_worker = task.assigned_worker_id
                logger.info(
                    f"Task {task.id} will be reassigned from worker "
                    f"{old_worker}"
                )

                # Find a different worker
                batch_result = await self._find_assignee([task])
                assignment = batch_result.assignments[0]
                new_worker = assignment.assignee_id

                # If same worker, force find another
                if new_worker == old_worker and len(self._children) > 1:
                    logger.info("Same worker selected, finding alternative")
                    # Try to find different worker by adding note to
                    # task content
                    task.content = (
                        f"{task.content}\n\n"
                        f"Note: Previous worker {old_worker} had quality "
                        f"issues. Needs different approach."
                    )
                    batch_result = await self._find_assignee([task])
                    assignment = batch_result.assignments[0]
                    new_worker = assignment.assignee_id

                self._assignees[task.id] = new_worker
                await self._post_task(task, new_worker)
                action_taken = f"reassigned from {old_worker} to {new_worker}"
                logger.info(
                    f"Task {task.id} reassigned from {old_worker} to "
                    f"{new_worker}"
                )

            elif strategy == RecoveryStrategy.DECOMPOSE:
                # Decompose the task into subtasks
                reason = (
                    "failure"
                    if not recovery_decision.is_quality_evaluation
                    else "quality issues"
                )
                logger.info(
                    f"Task {task.id} will be decomposed due to {reason}"
                )
                subtasks_result = self._decompose_task(task)

                # Handle both streaming and non-streaming results
                if isinstance(subtasks_result, Generator):
                    subtasks = []
                    for new_tasks in subtasks_result:
                        subtasks.extend(new_tasks)
                else:
                    subtasks = subtasks_result

                if subtasks:
                    task_decomposed_event = TaskDecomposedEvent(
                        parent_task_id=task.id,
                        subtask_ids=[st.id for st in subtasks],
                    )
                    for cb in self._callbacks:
                        cb.log_task_decomposed(task_decomposed_event)
                    for subtask in subtasks:
                        task_created_event = TaskCreatedEvent(
                            task_id=subtask.id,
                            description=subtask.content,
                            parent_task_id=task.id,
                            task_type=subtask.type,
                            metadata=subtask.additional_info,
                        )
                        for cb in self._callbacks:
                            cb.log_task_created(task_created_event)

                # Insert subtasks at the head of the queue
                self._pending_tasks.extendleft(reversed(subtasks))
                await self._post_ready_tasks()
                action_taken = f"decomposed into {len(subtasks)} subtasks"

                logger.info(
                    f"Task {task.id} decomposed into {len(subtasks)} subtasks"
                )

                # Sync shared memory after task decomposition
                if self.share_memory:
                    logger.info(
                        f"Syncing shared memory after task {task.id} "
                        f"decomposition"
                    )
                    self._sync_shared_memory()

                # For decompose, we return early with special handling
                return True

            elif strategy == RecoveryStrategy.CREATE_WORKER:
                assignee = await self._create_worker_node_for_task(task)
                await self._post_task(task, assignee.node_id)
                action_taken = (
                    f"created new worker {assignee.node_id} and assigned "
                    f"task {task.id} to it"
                )

        except Exception as e:
            logger.error(
                f"Recovery strategy {strategy} failed for task {task.id}: {e}",
                exc_info=True,
            )
            raise

        logger.debug(
            f"Task {task.id} recovery: {action_taken}. "
            f"Strategy: {strategy.value}"
        )

        return False

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

    async def _async_skip_gracefully(self) -> None:
        r"""Async implementation of skip_gracefully to run on the event
        loop.
        """
        self._skip_requested = True
        if self._pause_event.is_set() is False:
            self._pause_event.set()  # Resume if paused to process skip
        logger.info(f"Workforce {self.node_id} skip requested.")

    def skip_gracefully(self) -> None:
        r"""Request workforce to skip current pending tasks and move to next
        main task from the queue. If no main tasks exist, acts like
        stop_gracefully.

        This method clears the current pending subtasks and moves to the next
        main task in the queue if available. Works both when the internal
        event-loop is alive and when it has not yet been started.
        """

        if self._loop and not self._loop.is_closed():
            self._submit_coro_to_loop(self._async_skip_gracefully())
        else:
            # Loop not yet created, set the flag synchronously so later
            # startup will respect it.
            self._skip_requested = True
            # Ensure any pending pause is released so that when the loop does
            # start it can see the skip request and exit.
            self._pause_event.set()
            logger.info(
                f"Workforce {self.node_id} skip requested "
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
                f"Invalid content. Content preview: '{new_content}'"
            )
            return False

        for task in self._pending_tasks:
            if task.id == task_id:
                task.content = new_content
                logger.info(f"Task {task_id} content modified.")
                return True
        logger.warning(f"Task {task_id} not found in pending tasks.")
        return False

    def get_main_task_queue(self) -> List[Task]:
        r"""Get current main task queue for human review.
        Returns:
            List[Task]: List of main tasks waiting to be decomposed
                and executed.
        """
        # Return tasks from pending queue that need decomposition
        return [
            t
            for t in self._pending_tasks
            if t.additional_info
            and t.additional_info.get('_needs_decomposition')
        ]

    def add_task(
        self,
        content: str,
        task_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        as_subtask: bool = False,
        insert_position: int = -1,
    ) -> Task:
        r"""Add a new task to the workforce.

        By default, this method adds a main task that will be decomposed into
        subtasks. Set `as_subtask=True` to add a task directly to the pending
        subtask queue without decomposition.

        Args:
            content (str): The content of the task.
            task_id (Optional[str], optional): Optional ID for the task.
                If not provided, a unique ID will be generated.
            additional_info (Optional[Dict[str, Any]], optional): Optional
                additional metadata for the task.
            as_subtask (bool, optional): If True, adds the task directly to
                the pending subtask queue. If False, adds as a main task that
                will be decomposed. Defaults to False.
            insert_position (int, optional): Position to insert the task in
                the pending queue. Only applies when as_subtask=True.
                Defaults to -1 (append to end).

        Returns:
            Task: The created task object.
        """
        if as_subtask:
            new_task = Task(
                content=content,
                id=task_id or f"human_added_{len(self._pending_tasks)}",
                additional_info=additional_info,
            )

            # Add directly to current pending subtasks
            if insert_position == -1:
                self._pending_tasks.append(new_task)
            else:
                # Convert deque to list, insert, then back to deque
                tasks_list = list(self._pending_tasks)
                tasks_list.insert(insert_position, new_task)
                self._pending_tasks = deque(tasks_list)

            logger.info(f"New subtask added to pending queue: {new_task.id}")
            return new_task
        else:
            # Add as main task that needs decomposition
            # Use additional_info to mark this task needs decomposition
            # Make a copy to avoid modifying user's dict
            info = additional_info.copy() if additional_info else {}
            info['_needs_decomposition'] = True

            task_count = sum(
                1
                for t in self._pending_tasks
                if t.additional_info
                and t.additional_info.get('_needs_decomposition')
            )

            new_task = Task(
                content=content,
                id=task_id or f"main_task_{task_count}",
                additional_info=info,
            )

            self._pending_tasks.append(new_task)
            logger.info(f"New main task added to pending queue: {new_task.id}")
            return new_task

    def add_main_task(
        self,
        content: str,
        task_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> Task:
        r"""Add a new main task that will be decomposed into subtasks.

        This is an alias for :meth:`add_task` with `as_subtask=False`.

        Args:
            content (str): The content of the main task.
            task_id (Optional[str], optional): Optional ID for the task.
            additional_info (Optional[Dict[str, Any]], optional): Optional
                additional metadata.

        Returns:
            Task: The created main task object.
        """
        return self.add_task(
            content=content,
            task_id=task_id,
            additional_info=additional_info,
            as_subtask=False,
        )

    def add_subtask(
        self,
        content: str,
        task_id: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
        insert_position: int = -1,
    ) -> Task:
        r"""Add a new subtask to the current pending queue.

        This is an alias for :meth:`add_task` with `as_subtask=True`.

        Args:
            content (str): The content of the subtask.
            task_id (Optional[str], optional): Optional ID for the task.
            additional_info (Optional[Dict[str, Any]], optional): Optional
                additional metadata.
            insert_position (int, optional): Position to insert the task.
                Defaults to -1 (append to end).

        Returns:
            Task: The created subtask object.
        """
        return self.add_task(
            content=content,
            task_id=task_id,
            additional_info=additional_info,
            as_subtask=True,
            insert_position=insert_position,
        )

    def remove_task(self, task_id: str) -> bool:
        r"""Remove a task from the pending queue or main task queue.

        Args:
            task_id (str): The ID of the task to remove.

        Returns:
            bool: True if task was found and removed, False otherwise.
        """
        # Check main task queue first
        pending_tasks_list = list(self._pending_tasks)
        for i, task in enumerate(pending_tasks_list):
            if task.id == task_id:
                pending_tasks_list.pop(i)
                self._pending_tasks = deque(pending_tasks_list)
                logger.info(f"Task {task_id} removed from pending queue.")
                return True

        logger.warning(f"Task {task_id} not found in any task queue.")
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

    async def handle_decompose_append_task(
        self, task: Task, reset: bool = True
    ) -> List[Task]:
        r"""Handle task decomposition and validation with
        workforce environment functions. Then append to
        pending tasks if decomposition happened.

        Args:
            task (Task): The task to be processed.
            reset (Bool): Should trigger workforce reset (Workforce must not
                be running). Default: True

        Returns:
            List[Task]: The decomposed subtasks or the original task.
        """
        if not validate_task_content(task.content, task.id):
            task.state = TaskState.FAILED
            task.result = "Task failed: Invalid or empty content provided"
            logger.warning(
                f"Task {task.id} rejected: Invalid or empty content. "
                f"Content preview: '{task.content}'"
            )
            return [task]

        self.reset()
        self._task = task
        task.state = TaskState.FAILED

        task_created_event = TaskCreatedEvent(
            task_id=task.id,
            description=task.content,
            task_type=task.type,
            metadata=task.additional_info,
        )
        for cb in self._callbacks:
            cb.log_task_created(task_created_event)

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
        if subtasks:
            task_decomposed_event = TaskDecomposedEvent(
                parent_task_id=task.id,
                subtask_ids=[st.id for st in subtasks],
            )
            for cb in self._callbacks:
                cb.log_task_decomposed(task_decomposed_event)
            for subtask in subtasks:
                task_created_event = TaskCreatedEvent(
                    task_id=subtask.id,
                    description=subtask.content,
                    parent_task_id=task.id,
                    task_type=subtask.type,
                    metadata=subtask.additional_info,
                )
                for cb in self._callbacks:
                    cb.log_task_created(task_created_event)

        if subtasks:
            # _pending_tasks will contain both undecomposed
            # and decomposed tasks, so we use additional_info
            # to mark the tasks that need decomposition instead
            self._pending_tasks.extendleft(reversed(subtasks))
        else:
            # If no decomposition, execute the original task.
            self._pending_tasks.append(task)

        return subtasks

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

        # Handle different execution modes
        if self.mode == WorkforceMode.PIPELINE:
            return await self._process_task_with_pipeline(task)
        else:
            # AUTO_DECOMPOSE mode (default)
            subtasks = await self.handle_decompose_append_task(task)

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

    async def _process_task_with_pipeline(self, task: Task) -> Task:
        """Process task using predefined pipeline tasks."""
        if not self._pending_tasks:
            raise ValueError(
                "No pipeline tasks defined. Use set_pipeline_tasks() first."
            )

        # Don't reset here - keep the predefined tasks
        self._task = task

        # Log main task creation event through callbacks
        # (following source code pattern)
        task_created_event = TaskCreatedEvent(
            task_id=task.id,
            description=task.content,
            parent_task_id=None,
            task_type=task.type,
            metadata=task.additional_info,
        )
        for cb in self._callbacks:
            cb.log_task_created(task_created_event)

        task.state = TaskState.FAILED
        self.set_channel(TaskChannel())
        await self.start()

        # Collect results from all pipeline tasks
        task.result = self._collect_pipeline_results()
        task.state = (
            TaskState.DONE
            if self._all_pipeline_tasks_successful()
            else TaskState.FAILED
        )

        # Auto-reset mode to initial value after pipeline completion
        previous_mode = self.mode
        self.mode = self._initial_mode
        logger.info(
            f"Pipeline execution completed. Mode automatically reset from "
            f"{previous_mode.value} to {self._initial_mode.value}."
        )

        return task

    def _collect_pipeline_results(self) -> str:
        """Collect results from all completed pipeline tasks."""
        results = []
        for task in self._completed_tasks:
            if task.result:
                results.append(f"--- Task {task.id} Result ---\n{task.result}")
        return "\n\n".join(results) if results else "Pipeline completed"

    def _all_pipeline_tasks_successful(self) -> bool:
        """Check if all pipeline tasks completed successfully.

        INTENT: This method determines the FINAL STATE of the entire
        pipeline but does NOT affect task execution flow. It's called
        AFTER all tasks have finished to decide whether the overall
        pipeline succeeded or failed.

        WHY THIS DESIGN:
        - In PIPELINE mode, we want failed tasks to pass their error info
          to downstream tasks (for recovery in join tasks)
        - We still need to report the overall pipeline status correctly
        - This separation allows execution to continue and keeps a correct
          final status

        EXECUTION FLOW (handled in _post_ready_tasks()):
        - Failed tasks still pass their results (including errors) to
          dependent tasks, allowing join tasks to execute even when
          upstream tasks fail.

        FINAL STATUS (this method):
        - Runs AFTER all tasks have been processed to decide whether the
          overall pipeline should be marked as DONE or FAILED.

        Returns:
            bool: True if all tasks completed successfully (DONE state),
                False if any tasks failed or are still pending.

        Example:
            Fork-Join pattern with one failed branch:
            - Task A (search) → DONE
            - Task B (parallel summary 1) → DONE
            - Task C (parallel summary 2) → FAILED
            - Task D (join/synthesis) → DONE (receives B's result + C's error)

            Result: _all_pipeline_tasks_successful() returns False,
            main pipeline task marked as FAILED, but Task D still executed
            and received all information.
        """
        # Check 1: Pipeline incomplete if tasks still pending
        # Intent: Don't evaluate success until all execution finished
        if self._pending_tasks:
            return False

        # Check 2: No completed tasks = empty pipeline = failure
        # Intent: Catch edge case of malformed or empty pipeline
        if not self._completed_tasks:
            return False

        # Check 3: All tasks must be DONE for pipeline to be successful
        # Intent: Even one failed task means the pipeline didn't fully succeed,
        # though downstream tasks still ran (for error handling/recovery)
        return all(
            task.state == TaskState.DONE for task in self._completed_tasks
        )

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

        await self.handle_decompose_append_task(task)

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
        else:
            # Close the coroutine to prevent RuntimeWarning
            start_coroutine.close()

    def add_single_agent_worker(
        self,
        description: str,
        worker: ChatAgent,
        pool_max_size: int = DEFAULT_WORKER_POOL_SIZE,
        enable_workflow_memory: bool = False,
    ) -> Workforce:
        r"""Add a worker node to the workforce that uses a single agent.
        Can be called when workforce is paused to dynamically add workers.

        Args:
            description (str): Description of the worker node.
            worker (ChatAgent): The agent to be added.
            pool_max_size (int): Maximum size of the agent pool.
                (default: :obj:`10`)
            enable_workflow_memory (bool): Whether to enable workflow memory
                accumulation. Set to True if you plan to call
                save_workflow_memories(). (default: :obj:`False`)

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
            context_utility=None,  # Will be set during save/load operations
            enable_workflow_memory=enable_workflow_memory,
        )
        self._children.append(worker_node)

        # If we have a channel set up, set it for the new worker
        if hasattr(self, '_channel') and self._channel is not None:
            worker_node.set_channel(self._channel)

        # If workforce is paused, start the worker's listening task
        self._start_child_node_when_paused(worker_node.start())

        self._notify_worker_created(
            worker_node,
            worker_type='SingleAgentWorker',
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

        self._notify_worker_created(
            worker_node,
            worker_type='RolePlayingWorker',
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

        # Reset pipeline building state
        self._pipeline_builder = None

        # Reset mode to initial value
        self.mode = self._initial_mode
        logger.debug(f"Workforce mode reset to {self._initial_mode.value}")

        for child in self._children:
            child.reset()

        # Reset intervention state
        self._state = WorkforceState.IDLE
        self._stop_requested = False
        self._skip_requested = False
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

        for cb in self._callbacks:
            if isinstance(cb, WorkforceMetrics):
                cb.reset_task_data()

    def save_workflow_memories(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, str]:
        r"""Save workflow memories for all SingleAgentWorker instances in the
        workforce.

        .. deprecated:: 0.2.80
            This synchronous method processes workers sequentially, which can
            be slow for multiple agents. Use
            :meth:`save_workflow_memories_async`
            instead for parallel processing and significantly better
            performance.

        This method iterates through all child workers and triggers workflow
        saving for SingleAgentWorker instances using their
        save_workflow_memories()
        method.
        Other worker types are skipped.

        Args:
            session_id (Optional[str]): Custom session ID to use for saving
                workflows. If None, auto-generates a timestamped session ID.
                Useful for organizing workflows by project or context.
                (default: :obj:`None`)

        Returns:
            Dict[str, str]: Dictionary mapping worker node IDs to save results.
                Values are either file paths (success) or error messages
                (failure).

        Example:
            >>> workforce = Workforce("My Team")
            >>> # ... add workers and process tasks ...
            >>> # save with auto-generated session id
            >>> results = workforce.save_workflow_memories()
            >>> print(results)
            {'worker_123': '/path/to/developer_agent_workflow.md',
             'worker_456': 'error: No conversation context available'}
            >>> # save with custom project id
            >>> results = workforce.save_workflow_memories(
            ...     session_id="project_123"
            ... )

        Note:
            For better performance with multiple workers, use the async
            version::

                results = await workforce.save_workflow_memories_async()

        See Also:
            :meth:`save_workflow_memories_async`: Async version with parallel
                processing for significantly better performance.
        """
        import warnings

        warnings.warn(
            "save_workflow_memories() is slow for multiple workers. "
            "Consider using save_workflow_memories_async() for parallel "
            "processing and ~4x faster performance.",
            DeprecationWarning,
            stacklevel=2,
        )
        results = {}

        # Get or create shared context utility for this save operation
        shared_context_utility = self._get_or_create_shared_context_utility(
            session_id=session_id
        )

        for child in self._children:
            if isinstance(child, SingleAgentWorker):
                try:
                    # Set the shared context utility for this operation
                    child._shared_context_utility = shared_context_utility
                    child.worker.set_context_utility(shared_context_utility)

                    result = child.save_workflow_memories()
                    if result.get("status") == "success":
                        results[child.node_id] = result.get(
                            "file_path", "unknown_path"
                        )
                    else:
                        # Error: check if there's a separate message field,
                        # otherwise use the status itself
                        error_msg = result.get(
                            "message", result.get("status", "Unknown error")
                        )
                        results[child.node_id] = f"error: {error_msg}"

                except Exception as e:
                    results[child.node_id] = f"error: {e!s}"
            else:
                # Skip non-SingleAgentWorker types
                results[child.node_id] = (
                    f"skipped: {type(child).__name__} not supported"
                )

        logger.info(f"Workflow save completed for {len(results)} workers")
        return results

    async def save_workflow_memories_async(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, str]:
        r"""Asynchronously save workflow memories for all SingleAgentWorker
        instances in the workforce.

        This is the async version of save_workflow_memories() that parallelizes
        LLM summarization calls across all workers using asyncio.gather(),
        significantly reducing total save time.

        This method iterates through all child workers and triggers workflow
        saving for SingleAgentWorker instances using their
        save_workflow_memories_async() method in parallel.
        Other worker types are skipped.

        Args:
            session_id (Optional[str]): Custom session ID to use for saving
                workflows. If None, auto-generates a timestamped session ID.
                Useful for organizing workflows by project or context.
                (default: :obj:`None`)

        Returns:
            Dict[str, str]: Dictionary mapping worker node IDs to save results.
                Values are either file paths (success) or error messages
                (failure).

        Example:
            >>> workforce = Workforce("My Team")
            >>> # ... add workers and process tasks ...
            >>> # save with parallel summarization (faster)
            >>> results = await workforce.save_workflow_memories_async()
            >>> print(results)
            {'worker_123': '/path/to/developer_agent_workflow.md',
             'worker_456': '/path/to/search_agent_workflow.md',
             'worker_789': '/path/to/document_agent_workflow.md'}
        """
        import asyncio

        results = {}

        # Get or create shared context utility for this save operation
        shared_context_utility = self._get_or_create_shared_context_utility(
            session_id=session_id
        )

        # Prepare tasks for parallel execution
        async def save_single_worker(
            child: BaseNode,
        ) -> tuple[str, str]:
            """Save workflow for a single worker, then return (node_id,
            result)."""
            if isinstance(child, SingleAgentWorker):
                try:
                    # Set the shared context utility for this operation
                    child._shared_context_utility = shared_context_utility
                    child.worker.set_context_utility(shared_context_utility)

                    result = await child.save_workflow_memories_async()
                    if result.get("status") == "success":
                        return (
                            child.node_id,
                            result.get("file_path", "unknown_path"),
                        )
                    else:
                        # Error: check if there's a separate message field,
                        # otherwise use the status itself
                        error_msg = result.get(
                            "message", result.get("status", "Unknown error")
                        )
                        return (child.node_id, f"error: {error_msg}")

                except Exception as e:
                    return (child.node_id, f"error: {e!s}")
            else:
                # Skip non-SingleAgentWorker types
                return (
                    child.node_id,
                    f"skipped: {type(child).__name__} not supported",
                )

        # Create tasks for all workers
        tasks = [save_single_worker(child) for child in self._children]

        # Execute all tasks in parallel using asyncio.gather()
        parallel_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in parallel_results:
            if isinstance(result, Exception):
                # Handle any unexpected exceptions
                logger.error(
                    f"Unexpected error during workflow save: {result}"
                )
                results["unknown"] = f"error: {result!s}"
            elif isinstance(result, tuple) and len(result) == 2:
                # Successfully got (node_id, save_result) tuple
                node_id, save_result = result
                results[node_id] = save_result
            else:
                # Unexpected result format
                logger.error(f"Unexpected result format: {result}")
                results["unknown"] = "error: unexpected result format"

        logger.info(
            f"Workflow save completed for {len(results)} workers "
            f"(parallelized)"
        )
        return results

    def load_workflow_memories(
        self,
        session_id: Optional[str] = None,
        worker_max_workflows: int = 3,
        coordinator_max_workflows: int = 5,
        task_agent_max_workflows: int = 3,
    ) -> Dict[str, bool]:
        r"""Load workflow memories for all SingleAgentWorker instances in the
        workforce.

        This method iterates through all child workers and loads relevant
        workflow files for SingleAgentWorker instances using their
        load_workflow_memories()
        method. Workers match files based on their description names.

        Args:
            session_id (Optional[str]): Specific workforce session ID to load
                from. If None, searches across all sessions.
                (default: :obj:`None`)
            worker_max_workflows (int): Maximum number of workflow files to
                load per worker agent. (default: :obj:`3`)
            coordinator_max_workflows (int): Maximum number of workflow files
                to load for the coordinator agent. (default: :obj:`5`)
            task_agent_max_workflows (int): Maximum number of workflow files
                to load for the task planning agent. (default: :obj:`3`)

        Returns:
            Dict[str, bool]: Dictionary mapping worker node IDs to load
                success status.
                True indicates successful loading, False indicates failure.

        Example:
            >>> workforce = Workforce("My Team")
            >>> workforce.add_single_agent_worker(
            ...     "data_analyst", analyst_agent
            ... )
            >>> success_status = workforce.load_workflow_memories(
            ...     worker_max_workflows=5,
            ...     coordinator_max_workflows=10,
            ...     task_agent_max_workflows=5
            ... )
            >>> print(success_status)
            {'worker_123': True}  # Successfully loaded workflows for
            # data_analyst
        """
        results = {}

        # For loading, we don't create a new session - instead we search
        # existing ones
        # Each worker will search independently across all existing sessions

        # First, load workflows for SingleAgentWorker instances
        for child in self._children:
            if isinstance(child, SingleAgentWorker):
                try:
                    # For loading, don't set shared context utility
                    # Let each worker search across existing sessions
                    success = child.load_workflow_memories(
                        max_workflows=worker_max_workflows,
                        session_id=session_id,
                    )
                    results[child.node_id] = success

                except Exception as e:
                    logger.error(
                        f"Failed to load workflow for {child.node_id}: {e!s}"
                    )
                    results[child.node_id] = False
            else:
                # Skip non-SingleAgentWorker types
                results[child.node_id] = False

        # Load aggregated workflow summaries for coordinator and task agents
        self._load_management_agent_workflows(
            coordinator_max_workflows, task_agent_max_workflows, session_id
        )

        logger.info(f"Workflow load completed for {len(results)} workers")
        return results

    def _load_management_agent_workflows(
        self,
        coordinator_max_workflows: int,
        task_agent_max_workflows: int,
        session_id: Optional[str] = None,
    ) -> None:
        r"""Load workflow summaries for coordinator and task planning agents.

        This method loads aggregated workflow summaries to help:
        - Coordinator agent: understand task assignment patterns and worker
          capabilities
        - Task agent: understand task decomposition patterns and
          successful strategies

        Args:
            coordinator_max_workflows (int): Maximum number of workflow files
                to load for the coordinator agent.
            task_agent_max_workflows (int): Maximum number of workflow files
                to load for the task planning agent.
            session_id (Optional[str]): Specific session ID to load from.
                If None, searches across all sessions.
        """
        try:
            import glob
            import os
            from pathlib import Path

            from camel.utils.context_utils import ContextUtility

            # For loading management workflows, search across all sessions
            camel_workdir = os.environ.get("CAMEL_WORKDIR")
            if camel_workdir:
                base_dir = os.path.join(camel_workdir, "workforce_workflows")
            else:
                base_dir = "workforce_workflows"

            # Search for workflow files in specified or all session directories
            if session_id:
                search_path = str(
                    Path(base_dir) / session_id / "*_workflow*.md"
                )
            else:
                search_path = str(Path(base_dir) / "*" / "*_workflow*.md")
            workflow_files = glob.glob(search_path)

            if not workflow_files:
                logger.info(
                    "No workflow files found for management agent context"
                )
                return

            # Sort by modification time (most recent first)
            workflow_files.sort(
                key=lambda x: os.path.getmtime(x), reverse=True
            )

            # Load workflows for coordinator agent
            coordinator_loaded = 0
            for file_path in workflow_files[:coordinator_max_workflows]:
                try:
                    filename = os.path.basename(file_path).replace('.md', '')
                    session_dir = os.path.dirname(file_path)
                    session_id = os.path.basename(session_dir)

                    # Use shared context utility with specific session
                    temp_utility = ContextUtility.get_workforce_shared(
                        session_id
                    )

                    status = temp_utility.load_markdown_context_to_memory(
                        self.coordinator_agent, filename
                    )
                    if "Context appended" in status:
                        coordinator_loaded += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to load coordinator workflow {file_path}: {e}"
                    )

            # Load workflows for task agent
            task_agent_loaded = 0
            for file_path in workflow_files[:task_agent_max_workflows]:
                try:
                    filename = os.path.basename(file_path).replace('.md', '')
                    session_dir = os.path.dirname(file_path)
                    session_id = os.path.basename(session_dir)

                    # Use shared context utility with specific session
                    temp_utility = ContextUtility.get_workforce_shared(
                        session_id
                    )

                    status = temp_utility.load_markdown_context_to_memory(
                        self.task_agent, filename
                    )
                    if "Context appended" in status:
                        task_agent_loaded += 1
                except Exception as e:
                    logger.warning(
                        f"Failed to load task agent workflow {file_path}: {e}"
                    )

            logger.info(
                f"Loaded {coordinator_loaded} workflows for coordinator, "
                f"{task_agent_loaded} workflows for task agent"
            )

        except Exception as e:
            logger.error(f"Error loading management agent workflows: {e}")

    @check_if_running(False)
    def set_channel(self, channel: TaskChannel) -> None:
        r"""Set the channel for the node and all the child nodes under it."""
        self._channel = channel
        for child in self._children:
            child.set_channel(channel)

    def _get_child_nodes_info(self) -> str:
        r"""Get the information of all the child nodes under this node."""
        return "".join(
            f"<{child.node_id}>:<{child.description}>:<{self._get_node_info(child)}>\n"
            for child in self._children
        )

    def _get_node_info(self, node) -> str:
        r"""Get descriptive information for a specific node type."""
        if isinstance(node, Workforce):
            return "A Workforce node"
        elif isinstance(node, SingleAgentWorker):
            return self._get_single_agent_toolkit_info(node)
        elif isinstance(node, RolePlayingWorker):
            return "A Role playing node"
        else:
            return "Unknown node"

    def _get_single_agent_toolkit_info(
        self, worker: 'SingleAgentWorker'
    ) -> str:
        r"""Get formatted information for a SingleAgentWorker node."""
        toolkit_tools = self._group_tools_by_toolkit(worker.worker.tool_dict)

        if not toolkit_tools:
            return ""

        toolkit_info = []
        for toolkit_name, tools in sorted(toolkit_tools.items()):
            tools_str = ', '.join(sorted(tools))
            toolkit_info.append(f"{toolkit_name}({tools_str})")

        return ", ".join(toolkit_info)

    def _group_tools_by_toolkit(self, tool_dict: dict) -> dict[str, list[str]]:
        r"""Group tools by their parent toolkit class names."""
        toolkit_tools: dict[str, list[str]] = {}

        for tool_name, tool in tool_dict.items():
            if hasattr(tool.func, '__self__'):
                toolkit_name = tool.func.__self__.__class__.__name__
            else:
                toolkit_name = "Standalone"

            if toolkit_name not in toolkit_tools:
                toolkit_tools[toolkit_name] = []
            toolkit_tools[toolkit_name].append(tool_name)

        return toolkit_tools

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
                    f"{response.msg.content}"
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

    def _update_task_dependencies_from_assignments(
        self, assignments: List[TaskAssignment], tasks: List[Task]
    ) -> None:
        r"""Update Task.dependencies with actual Task objects based on
        assignments.

        Args:
            assignments (List[TaskAssignment]): The task assignments
                containing dependency IDs.
            tasks (List[Task]): The tasks that were assigned.
        """
        # Create a lookup map for all available tasks
        all_tasks = {}
        for task_list in [self._completed_tasks, self._pending_tasks, tasks]:
            for task in task_list:
                all_tasks[task.id] = task

        # Update dependencies for each assigned task
        for assignment in assignments:
            if not assignment.dependencies:
                continue

            matching_tasks = [t for t in tasks if t.id == assignment.task_id]
            if matching_tasks:
                task = matching_tasks[0]
                task.dependencies = [
                    all_tasks[dep_id]
                    for dep_id in assignment.dependencies
                    if dep_id in all_tasks
                ]

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
        # Wait for workers to be ready before assignment with exponential
        # backoff
        worker_readiness_timeout = 2.0  # Maximum wait time in seconds
        worker_readiness_check_interval = 0.05  # Initial check interval
        start_time = time.time()
        check_interval = worker_readiness_check_interval
        backoff_multiplier = 1.5  # Exponential backoff factor
        max_interval = 0.5  # Cap the maximum interval

        while (time.time() - start_time) < worker_readiness_timeout:
            valid_worker_ids = self._get_valid_worker_ids()
            if len(valid_worker_ids) > 0:
                elapsed = time.time() - start_time
                logger.debug(
                    f"Workers ready after {elapsed:.3f}s: "
                    f"{len(valid_worker_ids)} workers available"
                )
                break

            await asyncio.sleep(check_interval)
            # Exponential backoff with cap
            check_interval = min(
                check_interval * backoff_multiplier, max_interval
            )
        else:
            # Timeout reached, log warning but continue
            logger.warning(
                f"Worker readiness timeout after "
                f"{worker_readiness_timeout}s, "
                f"proceeding with {len(self._children)} children"
            )
            valid_worker_ids = self._get_valid_worker_ids()

        self.coordinator_agent.reset()

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
            self._update_task_dependencies_from_assignments(
                valid_assignments, tasks
            )
            return TaskAssignResult(assignments=valid_assignments)

        # handle retry and fallback for invalid assignments and unassigned
        # tasks
        retry_and_fallback_assignments = (
            await self._handle_assignment_retry_and_fallback(
                invalid_assignments, tasks, valid_worker_ids
            )
        )

        # Combine assignments with deduplication, prioritizing retry results
        assignment_map = {a.task_id: a for a in valid_assignments}
        assignment_map.update(
            {a.task_id: a for a in retry_and_fallback_assignments}
        )
        all_assignments = list(assignment_map.values())

        # Log any overwrites for debugging
        valid_task_ids = {a.task_id for a in valid_assignments}
        retry_task_ids = {a.task_id for a in retry_and_fallback_assignments}
        overlap_task_ids = valid_task_ids & retry_task_ids

        if overlap_task_ids:
            logger.warning(
                f"Retry assignments overrode {len(overlap_task_ids)} "
                f"valid assignments for tasks: {sorted(overlap_task_ids)}"
            )

        # Update Task.dependencies for all final assignments
        self._update_task_dependencies_from_assignments(all_assignments, tasks)

        return TaskAssignResult(assignments=all_assignments)

    async def _post_task(self, task: Task, assignee_id: str) -> None:
        # Record the start time when a task is posted
        self._task_start_times[task.id] = time.time()

        task.assigned_worker_id = assignee_id

        task_started_event = TaskStartedEvent(
            task_id=task.id, worker_id=assignee_id
        )
        for cb in self._callbacks:
            cb.log_task_started(task_started_event)

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
        prompt = str(
            CREATE_NODE_PROMPT.format(
                content=task.content,
                child_nodes_info=self._get_child_nodes_info(),
                additional_info=task.additional_info,
            )
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
                    description=f"Fallback worker for task: {task.content}",
                    role="General Assistant",
                    sys_msg="You are a general assistant that can help "
                    "with various tasks.",
                )
            else:
                result = self.structured_handler.parse_structured_response(
                    response.msg.content,
                    schema=WorkerConf,
                    fallback_values={
                        "description": f"Worker for task: {task.content}",
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
                        description=f"Worker for task: {task.content}",
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
                    description=f"Fallback worker for task: {task.content}",
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
                        f"{response.msg.content}"
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

        self._notify_worker_created(
            new_node,
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

        Raises:
            asyncio.TimeoutError: If waiting for task exceeds timeout
        """
        try:
            # Add timeout to prevent indefinite waiting
            return await asyncio.wait_for(
                self._channel.get_returned_task_by_publisher(self.node_id),
                timeout=self.task_timeout_seconds,
            )
        except asyncio.TimeoutError:
            # Re-raise timeout errors to be handled by caller
            # This prevents hanging when tasks are stuck
            logger.warning(
                f"Timeout waiting for task return in workforce "
                f"{self.node_id}. "
                f"Timeout: {self.task_timeout_seconds}s, "
                f"Pending tasks: {len(self._pending_tasks)}, "
                f"In-flight tasks: {self._in_flight_tasks}"
            )
            raise
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
        # In PIPELINE mode, tasks already have dependencies set but need
        # worker assignment.
        # In other modes, tasks without a dependencies entry are new and
        # need both assignments and dependencies.
        if self.mode == WorkforceMode.PIPELINE:
            tasks_to_assign = [
                task
                for task in self._pending_tasks
                if task.id not in self._assignees
            ]
        else:
            tasks_to_assign = [
                task
                for task in self._pending_tasks
                if (
                    task.id not in self._task_dependencies
                    and (
                        task.additional_info is None
                        or not task.additional_info.get(
                            "_needs_decomposition", False
                        )
                    )
                )
            ]
        if tasks_to_assign:
            logger.debug(
                f"Found {len(tasks_to_assign)} new tasks. "
                f"Requesting assignment..."
            )
            batch_result = await self._find_assignee(tasks_to_assign)
            logger.debug(
                f"Coordinator returned assignments:\n"
                f"{json.dumps(batch_result.model_dump(), indent=2)}"
            )
            for assignment in batch_result.assignments:
                # For pipeline mode, dependencies are already set, only
                # update assignees.
                # For other modes, update both dependencies and assignees.
                if self.mode != WorkforceMode.PIPELINE:
                    self._task_dependencies[assignment.task_id] = (
                        assignment.dependencies
                    )
                self._assignees[assignment.task_id] = assignment.assignee_id

                task_assigned_event = TaskAssignedEvent(
                    task_id=assignment.task_id,
                    worker_id=assignment.assignee_id,
                    dependencies=assignment.dependencies,
                    queue_time_seconds=None,
                )
                for cb in self._callbacks:
                    # queue_time_seconds can be derived by logger if task
                    # creation time is logged
                    cb.log_task_assigned(task_assigned_event)

        # Step 2: Iterate through all pending tasks and post those that are
        # ready
        posted_tasks = []
        # Pre-compute completed task IDs and their states for O(1) lookups
        completed_tasks_info = {t.id: t.state for t in self._completed_tasks}

        for task in self._pending_tasks:
            # A task must be assigned to be considered for posting
            if task.id in self._task_dependencies:
                # Skip if task has already been posted to prevent duplicates
                try:
                    task_from_channel = await self._channel.get_task_by_id(
                        task.id
                    )
                    # Check if task is already assigned to a worker
                    if (
                        task_from_channel
                        and task_from_channel.assigned_worker_id
                    ):
                        logger.debug(
                            f"Task {task.id} already assigned to "
                            f"{task_from_channel.assigned_worker_id}, "
                            f"skipping to prevent duplicate"
                        )
                        continue
                except Exception as e:
                    logger.info(
                        f"Task {task.id} non existent in channel. "
                        f"Assigning task: {e}"
                    )
                dependencies = self._task_dependencies[task.id]

                # Check if all dependencies are in the completed state
                # (regardless of success or failure).
                all_deps_completed = all(
                    dep_id in completed_tasks_info for dep_id in dependencies
                )

                # Only proceed with dependency checks if all deps are completed
                if all_deps_completed:
                    # Intent: decide whether this task should run based on
                    # dependency state.
                    # Pipeline mode allows error propagation so joins can
                    # handle upstream failures.
                    # Auto-decompose mode requires successful inputs to avoid
                    # cascading errors.
                    should_post_task = False

                    if self.mode == WorkforceMode.PIPELINE:
                        # PIPELINE mode: post if dependencies are complete
                        # (success OR failure).
                        # Intent: allow downstream tasks to handle and report
                        # upstream failures.
                        # Benefit: join tasks can aggregate partial results
                        # plus error context.
                        should_post_task = True
                        logger.debug(
                            f"Task {task.id} ready in PIPELINE mode. "
                            f"All dependencies completed (success or failure)."
                        )
                    else:
                        # AUTO_DECOMPOSE mode: post ONLY if all dependencies
                        # succeeded.
                        # Intent: prevent executing tasks with invalid or
                        # incomplete inputs.
                        # Benefit: stops cascading failures and keeps the error
                        # source clear.
                        all_deps_done = all(
                            completed_tasks_info[dep_id] == TaskState.DONE
                            for dep_id in dependencies
                        )
                        should_post_task = all_deps_done

                    if should_post_task:
                        # Post the task
                        assignee_id = self._assignees[task.id]
                        logger.debug(
                            f"Posting task {task.id} to "
                            f"assignee {assignee_id}. "
                            f"Dependencies met."
                        )
                        await self._post_task(task, assignee_id)
                        posted_tasks.append(task)
                    elif self.mode == WorkforceMode.AUTO_DECOMPOSE:
                        # AUTO_DECOMPOSE mode: handle dependency failures.
                        any_dep_failed = any(
                            completed_tasks_info[dep_id] == TaskState.FAILED
                            for dep_id in dependencies
                        )
                        if any_dep_failed:
                            # Check if any failed dependencies can still be
                            # retried.
                            failed_deps = [
                                dep_id
                                for dep_id in dependencies
                                if completed_tasks_info[dep_id]
                                == TaskState.FAILED
                            ]

                        # Check if any failed dependency is still retryable
                        failed_tasks_with_retry_potential = []
                        permanently_failed_deps = []

                        for dep_id in failed_deps:
                            # Find the failed dependency task
                            failed_task = next(
                                (
                                    t
                                    for t in self._completed_tasks
                                    if t.id == dep_id
                                ),
                                None,
                            )
                            if (
                                failed_task
                                and failed_task.failure_count
                                < MAX_TASK_RETRIES
                            ):
                                failed_tasks_with_retry_potential.append(
                                    dep_id
                                )
                            else:
                                permanently_failed_deps.append(dep_id)

                        # Only fail the task if ALL dependencies are
                        # permanently failed
                        if (
                            permanently_failed_deps
                            and not failed_tasks_with_retry_potential
                        ):
                            logger.error(
                                f"Task {task.id} cannot proceed: dependencies "
                                f"{permanently_failed_deps} have "
                                f"permanently failed. "
                                f"Marking task as failed."
                            )
                            task.state = TaskState.FAILED
                            task.result = (
                                f"Task failed due to permanently "
                                f"failed dependencies: "
                                f"{permanently_failed_deps}"
                            )

                            # Log the failure to metrics
                            task_failed_event = TaskFailedEvent(
                                task_id=task.id,
                                worker_id=task.assigned_worker_id or "unknown",
                                error_message=task.result,
                                metadata={
                                    'failure_reason': 'dependency_failure',
                                    'failed_dependencies': (
                                        permanently_failed_deps
                                    ),
                                },
                            )
                            for cb in self._callbacks:
                                cb.log_task_failed(task_failed_event)

                            self._completed_tasks.append(task)
                            self._cleanup_task_tracking(task.id)
                            posted_tasks.append(task)  # Remove from pending
                        else:
                            # Some dependencies may still be retried, keep
                            # task pending
                            logger.debug(
                                f"Task {task.id} waiting: dependencies "
                                f"{failed_tasks_with_retry_potential} "
                                f"failed but may be retried "
                                f"(attempt < {MAX_TASK_RETRIES})"
                            )
                # else: Not all dependencies completed yet, skip this task

        # Step 3: Remove the posted tasks from the pending list
        for task in posted_tasks:
            try:
                self._pending_tasks.remove(task)
            except ValueError:
                # Task might have been removed by another process, which is
                # fine
                pass

    async def _handle_failed_task(self, task: Task) -> bool:
        r"""Handle a task that failed during execution.

        Args:
            task (Task): The failed task

        Returns:
            bool: True if workforce should halt, False otherwise
        """
        task.failure_count += 1

        # Determine detailed failure information
        failure_reason = task.result or "Unknown error"
        worker_id = task.assigned_worker_id or "unknown"
        detailed_error = f"{failure_reason} (assigned to worker: {worker_id})"

        logger.error(
            f"Task {task.id} failed (attempt "
            f"{task.failure_count}/{MAX_TASK_RETRIES}): {detailed_error}"
        )

        print(
            f"{Fore.RED}❌ Task {task.id} failed "
            f"(attempt {task.failure_count}/{MAX_TASK_RETRIES}): "
            f"{failure_reason}{Fore.RESET}"
        )

        task_failed_event = TaskFailedEvent(
            task_id=task.id,
            worker_id=worker_id,
            error_message=detailed_error,
            metadata={
                'failure_count': task.failure_count,
                'task_content': task.content,
                'result_length': len(task.result) if task.result else 0,
            },
        )
        for cb in self._callbacks:
            cb.log_task_failed(task_failed_event)

        # Check for immediate halt conditions after max retries.
        if task.failure_count >= MAX_TASK_RETRIES:
            # Intent: handle max retry failures differently per mode.
            # Pipeline mode continues to allow downstream recovery.
            # Auto-decompose mode halts to avoid cascading errors.

            if self.mode == WorkforceMode.PIPELINE:
                # PIPELINE: Mark as failed but continue workflow
                # Intent: Failed tasks pass error info to downstream tasks
                logger.warning(
                    f"Task {task.id} failed after {MAX_TASK_RETRIES} retries "
                    f"in PIPELINE mode. Marking as failed and allowing the "
                    f"workflow to continue. Error: {failure_reason}"
                )
                task.state = TaskState.FAILED
                self._cleanup_task_tracking(task.id)
                self._completed_tasks.append(task)
                if task.id in self._assignees:
                    await self._channel.archive_task(task.id)

                # Resume workflow: Check if downstream tasks can now proceed
                # (they'll receive this failed task's error message)
                await self._post_ready_tasks()
                return False  # Don't halt workforce

            # AUTO_DECOMPOSE: Halt immediately on max retries
            # Intent: Stop execution to prevent cascading failures
            logger.error(
                f"Task {task.id} has exceeded maximum retry attempts "
                f"({MAX_TASK_RETRIES}). Final failure reason: "
                f"{detailed_error}. "
                f"Task content: '{task.content}'"
            )
            self._cleanup_task_tracking(task.id)
            self._completed_tasks.append(task)
            if task.id in self._assignees:
                await self._channel.archive_task(task.id)
            return True  # Halt workforce

        if len(self._pending_tasks) > MAX_PENDING_TASKS_LIMIT:
            logger.error(
                f"Too many pending tasks ({len(self._pending_tasks)} > "
                f"{MAX_PENDING_TASKS_LIMIT}). Halting to prevent task "
                f"explosion. Last failed task: {task.id}"
            )
            self._cleanup_task_tracking(task.id)
            self._completed_tasks.append(task)
            if task.id in self._assignees:
                await self._channel.archive_task(task.id)
            return True

        # Recovery strategies differ by mode.
        # Pipeline mode retries quickly without additional analysis.
        # Auto-decompose mode analyzes the failure to choose a recovery plan.

        if self.mode == WorkforceMode.PIPELINE:
            # PIPELINE: Simple retry logic (no LLM analysis needed)
            # Intent: Fast recovery for predefined workflows
            logger.info(
                f"Task {task.id} failed in PIPELINE mode. Will retry "
                f"(attempt {task.failure_count}/{MAX_TASK_RETRIES})"
            )
            # Reset task to pending and retry with same configuration
            task.state = TaskState.OPEN
            self._pending_tasks.append(task)
            await self._post_ready_tasks()
            return False

        # AUTO_DECOMPOSE: Intelligent failure analysis and recovery
        # Intent: Use LLM analysis to choose an optimal recovery strategy.
        recovery_decision = self._analyze_task(
            task, for_failure=True, error_message=detailed_error
        )

        strategy_str = (
            recovery_decision.recovery_strategy.value
            if recovery_decision.recovery_strategy
            else "none"
        )
        logger.info(
            f"Task {task.id} failure "
            f"analysis: {strategy_str} - "
            f"{recovery_decision.reasoning}"
        )

        # Clean up tracking before attempting recovery
        if task.id in self._assignees:
            await self._channel.archive_task(task.id)
        self._cleanup_task_tracking(task.id)

        # Apply recovery strategy
        try:
            is_decompose = await self._apply_recovery_strategy(
                task, recovery_decision
            )

            # For decompose, we handle it specially
            if is_decompose:
                # Task was decomposed, add to completed tasks
                self._completed_tasks.append(task)
                return False

        except Exception as e:
            logger.error(
                f"Recovery strategy failed for task {task.id}: {e}",
                exc_info=True,
            )
            # If max retries reached, halt the workforce
            if task.failure_count >= MAX_TASK_RETRIES:
                self._completed_tasks.append(task)
                return True
            self._completed_tasks.append(task)
            return False

        # Task is being retried - don't add to completed tasks
        # It will be added when it actually completes or permanently fails
        logger.debug(
            f"Task {task.id} is being retried (strategy: "
            f"{recovery_decision.recovery_strategy}). "
            f"Not adding to completed tasks until final outcome."
        )

        # Sync shared memory after task recovery
        if self.share_memory:
            logger.info(f"Syncing shared memory after task {task.id} recovery")
            self._sync_shared_memory()

        # Check if any pending tasks are now ready to execute
        await self._post_ready_tasks()
        return False

    async def _handle_completed_task(self, task: Task) -> None:
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
                    _, total_tokens = assignee_node.worker.memory.get_context()
                    token_usage = {'total_tokens': total_tokens}
                except Exception:
                    token_usage = None

        # Log the completed task
        task_completed_event = TaskCompletedEvent(
            task_id=task.id,
            worker_id=worker_id,
            result_summary=task.result if task.result else "Completed",
            processing_time_seconds=processing_time_seconds,
            token_usage=token_usage,
            metadata={'current_state': task.state.value},
        )
        for cb in self._callbacks:
            cb.log_task_completed(task_completed_event)

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
        metrics_cb: List[WorkforceMetrics] = [
            cb for cb in self._callbacks if isinstance(cb, WorkforceMetrics)
        ]
        if len(metrics_cb) == 0:
            return "Metrics Callback not initialized."
        else:
            return metrics_cb[0].get_ascii_tree_representation()

    def get_workforce_kpis(self) -> Dict[str, Any]:
        r"""Returns a dictionary of key performance indicators."""
        metrics_cb: List[WorkforceMetrics] = [
            cb for cb in self._callbacks if isinstance(cb, WorkforceMetrics)
        ]
        if len(metrics_cb) == 0:
            return {"error": "Metrics Callback not initialized."}
        else:
            return metrics_cb[0].get_kpis()

    def dump_workforce_logs(self, file_path: str) -> None:
        r"""Dumps all collected logs to a JSON file.

        Args:
            file_path (str): The path to the JSON file.
        """
        metrics_cb: List[WorkforceMetrics] = [
            cb for cb in self._callbacks if isinstance(cb, WorkforceMetrics)
        ]
        if len(metrics_cb) == 0:
            print("Logger not initialized. Cannot dump logs.")
            return
        metrics_cb[0].dump_to_json(file_path)
        # Use logger.info or print, consistent with existing style
        logger.info(f"Workforce logs dumped to {file_path}")

    async def _handle_skip_task(self) -> bool:
        r"""Handle skip request by marking pending and in-flight tasks
        as completed.

        Returns:
            bool: True if workforce should stop (no independent tasks),
            False to continue.
        """
        logger.info("Skip requested, processing skip logic.")

        # Mark all pending tasks as completed instead of just clearing
        pending_tasks_to_complete = list(self._pending_tasks)
        if pending_tasks_to_complete:
            logger.info(
                f"Marking {len(pending_tasks_to_complete)} pending tasks "
                f"as completed."
            )
            for task in pending_tasks_to_complete:
                # Don't remove tasks that need decomposition
                if task.additional_info and task.additional_info.get(
                    '_needs_decomposition', False
                ):
                    continue
                # Set task state to DONE and add a completion message
                task.state = TaskState.DONE
                task.result = "Task marked as completed due to skip request"

                # Use the existing handle completed task function
                await self._handle_completed_task(task)

        # Handle in-flight tasks if they exist
        if self._in_flight_tasks > 0:
            logger.info(
                f"Found {self._in_flight_tasks} in-flight tasks. "
                f"Retrieving and completing them."
            )
            try:
                # Get all in-flight tasks for this publisher from the channel
                in_flight_tasks = await self._channel.get_in_flight_tasks(
                    self.node_id
                )
                logger.info(
                    f"Retrieved {len(in_flight_tasks)} in-flight "
                    f"tasks from channel."
                )

                for task in in_flight_tasks:
                    # Set task state to DONE and add a completion message
                    task.state = TaskState.DONE
                    task.result = (
                        "Task marked as completed due to skip request"
                    )

                    # Remove the task from the channel to avoid hanging
                    await self._channel.remove_task(task.id)

                    # Decrement in-flight counter
                    self._decrement_in_flight_tasks(
                        task.id, "skip request - removed from channel"
                    )

                    # Handle as completed task to update dependencies
                    await self._handle_completed_task(task)

                    logger.info(
                        f"Completed in-flight task {task.id} due "
                        f"to skip request."
                    )

            except Exception as e:
                logger.error(
                    f"Error handling in-flight tasks during skip: {e}",
                    exc_info=True,
                )
                # Reset in-flight counter to prevent hanging
                self._in_flight_tasks = 0

        # Check if there are any main pending tasks after filtering
        if self._pending_tasks:
            # Check if the first pending task needs decomposition
            next_task = self._pending_tasks[0]
            if next_task.additional_info and next_task.additional_info.get(
                '_needs_decomposition'
            ):
                logger.info(
                    f"Decomposing main task {next_task.id} after skip request."
                )
                try:
                    # Remove the decomposition flag to avoid re-decomposition
                    next_task.additional_info['_needs_decomposition'] = False

                    # Decompose the task and append subtasks to _pending_tasks
                    await self.handle_decompose_append_task(
                        next_task, reset=False
                    )

                    # Mark the main task as completed and remove from pending
                    await self._handle_completed_task(next_task)
                    logger.info(
                        f"Main task {next_task.id} decomposed after "
                        f"skip request"
                    )
                except Exception as e:
                    logger.error(
                        f"Error decomposing main task {next_task.id} "
                        f"after skip: {e}",
                        exc_info=True,
                    )

            logger.info("Pending tasks available after skip, continuing.")
            await self._post_ready_tasks()
            return False  # Continue processing
        else:
            # No pending tasks available, act like stop
            logger.info("No pending tasks available, acting like stop.")
            return True  # Stop processing

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

                # Check for skip request after potential pause
                if self._skip_requested:
                    should_stop = await self._handle_skip_task()
                    if should_stop:
                        self._stop_requested = True
                        break

                    # Reset skip flag
                    self._skip_requested = False
                    continue

                # Check if we should decompose a main task
                # Only decompose when no tasks are in flight and pending queue
                # is empty
                if not self._pending_tasks and self._in_flight_tasks == 0:
                    # All tasks completed, will exit loop
                    break

                # Check if the first pending task needs decomposition
                # This happens when add_task(as_subtask=False) was called
                if self._pending_tasks and self._in_flight_tasks == 0:
                    next_task = self._pending_tasks[0]
                    if (
                        next_task.additional_info
                        and next_task.additional_info.get(
                            '_needs_decomposition'
                        )
                    ):
                        logger.info(f"Decomposing main task: {next_task.id}")
                        try:
                            # Remove the decomposition flag to avoid
                            # re-decomposition
                            next_task.additional_info[
                                '_needs_decomposition'
                            ] = False

                            # Decompose the task and append subtasks to
                            # _pending_tasks
                            await self.handle_decompose_append_task(
                                next_task, reset=False
                            )

                            # Mark the main task as completed (decomposition
                            # successful) and Remove it from pending tasks
                            await self._handle_completed_task(next_task)
                            logger.info(
                                f"Main task {next_task.id} decomposed and "
                                f"ready for processing"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error decomposing main task {next_task.id}: "
                                f"{e}",
                                exc_info=True,
                            )
                            # Revert back to the queue for retry later if
                            # decomposition failed
                            if not self._pending_tasks:
                                self._pending_tasks.appendleft(next_task)
                            else:
                                logger.warning(
                                    "Pending tasks exist after decomposition "
                                    "error."
                                )

                        # Immediately assign and post the transferred tasks
                        await self._post_ready_tasks()
                        continue

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
                try:
                    returned_task = await self._get_returned_task()
                except asyncio.TimeoutError:
                    # Handle timeout - check if we have tasks stuck in flight
                    if self._in_flight_tasks > 0:
                        logger.warning(
                            f"Timeout waiting for {self._in_flight_tasks} "
                            f"in-flight tasks. Breaking to prevent hanging."
                        )
                        # Break the loop to prevent indefinite hanging
                        # The finally block will handle cleanup
                        break
                    else:
                        # No tasks in flight, safe to continue
                        await self._post_ready_tasks()
                        continue

                # If no task was returned (other errors), continue
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
                            returned_task.result
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

                            # Do not halt if we have main tasks in queue
                            if len(self.get_main_task_queue()) > 0:
                                print(
                                    f"{Fore.RED}Task {returned_task.id} has "
                                    f"failed for {MAX_TASK_RETRIES} times "
                                    f"after insufficient results, skipping "
                                    f"that task. Final error: "
                                    f"{returned_task.result or 'Unknown err'}"
                                    f"{Fore.RESET}"
                                )
                                self._skip_requested = True
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
                        quality_eval = self._analyze_task(
                            returned_task, for_failure=False
                        )

                        if not quality_eval.quality_sufficient:
                            logger.info(
                                f"Task {returned_task.id} quality check: "
                                f"score={quality_eval.quality_score}, "
                                f"issues={quality_eval.issues}, "
                                f"strategy={quality_eval.recovery_strategy}"
                            )

                            # Check retry limit before attempting recovery
                            if returned_task.failure_count >= 2:
                                print(
                                    f"{Fore.YELLOW}Task {returned_task.id} "
                                    f"completed with low quality score: "
                                    f"{quality_eval.quality_score} "
                                    f"(retry limit reached){Fore.RESET}"
                                )
                                await self._handle_completed_task(
                                    returned_task
                                )
                                continue

                            # Print visual feedback for quality-failed tasks
                            # with recovery strategy
                            recovery_action = (
                                quality_eval.recovery_strategy.value
                                if quality_eval.recovery_strategy
                                else ""
                            )
                            print(
                                f"{Fore.YELLOW}⚠️ Task {returned_task.id} "
                                f"failed quality check (score: "
                                f"{quality_eval.quality_score}). "
                                f"Issues: {', '.join(quality_eval.issues)}. "
                                f"Recovery: {recovery_action}{Fore.RESET}"
                            )

                            # Mark as failed for recovery
                            returned_task.failure_count += 1
                            returned_task.state = TaskState.FAILED
                            returned_task.result = (
                                f"Quality insufficient (score: "
                                f"{quality_eval.quality_score}). "
                                f"Issues: {', '.join(quality_eval.issues)}"
                            )

                            # Clean up tracking before attempting recovery
                            if returned_task.id in self._assignees:
                                await self._channel.archive_task(
                                    returned_task.id
                                )
                            self._cleanup_task_tracking(returned_task.id)

                            # Apply LLM-recommended recovery strategy
                            try:
                                is_decompose = (
                                    await self._apply_recovery_strategy(
                                        returned_task, quality_eval
                                    )
                                )

                                # For decompose, cleanup happens in the method
                                if is_decompose:
                                    continue

                            except Exception as e:
                                logger.error(
                                    f"Error handling quality-failed task "
                                    f"{returned_task.id}: {e}",
                                    exc_info=True,
                                )
                                continue
                        else:
                            print(
                                f"{Fore.CYAN}Task {returned_task.id} "
                                f"completed successfully (quality score: "
                                f"{quality_eval.quality_score}).{Fore.RESET}"
                            )
                            await self._handle_completed_task(returned_task)
                elif returned_task.state == TaskState.FAILED:
                    try:
                        halt = await self._handle_failed_task(returned_task)
                        if not halt:
                            continue

                        # Do not halt if we have main tasks in queue
                        if len(self.get_main_task_queue()) > 0:
                            print(
                                f"{Fore.RED}Task {returned_task.id} has "
                                f"failed for {MAX_TASK_RETRIES} times, "
                                f"skipping that task. Final error: "
                                f"{returned_task.result or 'Unknown error'}"
                                f"{Fore.RESET}"
                            )
                            self._skip_requested = True
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
            all_tasks_completed_event = AllTasksCompletedEvent()
            for cb in self._callbacks:
                cb.log_all_tasks_completed(all_tasks_completed_event)

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
            task_timeout_seconds=self.task_timeout_seconds,
            mode=self.mode,
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
