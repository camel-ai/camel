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
from typing import Any, Coroutine, Dict, List, Optional, Union

from colorama import Fore

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce.prompts import CREATE_NODE_PROMPT
from camel.societies.workforce.role_playing_worker import RolePlayingWorker
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.task_channel import TaskChannel
from camel.societies.workforce.utils import WorkerConf
from camel.societies.workforce.worker import Worker
from camel.societies.workforce.workforce_split.introspection import (
    IntrospectionHelper,
)
from camel.tasks.task import Task
from camel.toolkits import (
    CodeExecutionToolkit,
    SearchToolkit,
    ThinkingToolkit,
)
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)

# Constants
DEFAULT_WORKER_POOL_SIZE = 10


class WorkerManagement:
    """Class for managing worker operations in a workforce system."""

    def __init__(
        self,
        coordinator_agent: Optional[ChatAgent] = None,
        new_worker_agent: Optional[ChatAgent] = None,
        use_structured_output_handler: bool = True,
        structured_handler: Optional[Any] = None,
        children: Optional[list] = None,
        channel: Optional[TaskChannel] = None,
        pause_event: Optional[asyncio.Event] = None,
        loop: Optional[asyncio.AbstractEventLoop] = None,
        state: Optional[Any] = None,
        metrics_logger: Optional[Any] = None,
    ):
        """Initialize the WorkerManagement class.

        Args:
            coordinator_agent: The coordinator agent for task assignment.
            new_worker_agent: Template agent for creating new workers.
            use_structured_output_handler: Whether to use structured output
                handler.
            structured_handler: The structured output handler instance.
            children: List of child nodes.
            channel: The task channel for communication.
            pause_event: Event for pausing the workforce.
            loop: The asyncio event loop.
            state: The current workforce state.
            metrics_logger: Logger for metrics.
        """
        self.coordinator_agent = coordinator_agent
        self.new_worker_agent = new_worker_agent
        self.use_structured_output_handler = use_structured_output_handler
        self.structured_handler = structured_handler
        self._children = children or []
        self._channel = channel
        self._pause_event = pause_event
        self._loop = loop
        self._state = state
        self.metrics_logger = metrics_logger
        self._child_listening_tasks: List = []

    async def create_worker_node_for_task(self, task: Task) -> Worker:
        r"""Creates a new worker node for a given task and add it to the
        children list of this node. This is one of the actions that
        the coordinator can take when a task has failed.

        Args:
            task (Task): The task for which the worker node is created.

        Returns:
            Worker: The created worker node.
        """
        introspection_helper = IntrospectionHelper()
        prompt = CREATE_NODE_PROMPT.format(
            content=task.content,
            child_nodes_info=introspection_helper.get_child_nodes_info(
                self._children
            ),
            additional_info=task.additional_info,
        )
        # Check if we should use structured handler
        if (
            self.use_structured_output_handler
            and self.structured_handler is not None
        ):
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

            if self.coordinator_agent is None:
                raise RuntimeError("Coordinator agent is not set")
            response = self.coordinator_agent.step(enhanced_prompt)

            if response.msg is None or response.msg.content is None:
                logger.error(
                    "Coordinator agent returned empty response for "
                    "worker creation"
                )
                new_node_conf = WorkerConf(
                    description=f"Fallback worker for task: "
                    f"{task.content}",
                    role="General Assistant",
                    sys_msg="You are a general assistant that can help "
                    "with various tasks.",
                )
            else:
                result = self.structured_handler.parse_structured_response(
                    response.msg.content,
                    schema=WorkerConf,
                    fallback_values={
                        "description": f"Worker for task: " f"{task.content}",
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
            if self.coordinator_agent is None:
                raise RuntimeError("Coordinator agent is not set")
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
                    f"task: {task.content}",
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

        new_agent = await self.create_new_agent(
            new_node_conf.role, new_node_conf.sys_msg
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

    async def create_new_agent(self, role: str, sys_msg: str) -> ChatAgent:
        """Create a new agent with the specified role and system message.

        Args:
            role (str): The role name for the agent.
            sys_msg (str): The system message for the agent.

        Returns:
            ChatAgent: The created agent.
        """
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

    def start_child_node_when_paused(self, start_coroutine: Coroutine) -> None:
        r"""Helper to start a child node when workforce is paused.

        Args:
            start_coroutine: The coroutine to start (e.g., worker_node.start())
        """
        if self._state == "PAUSED" and hasattr(self, '_child_listening_tasks'):
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
    ) -> 'WorkerManagement':
        r"""Add a worker node to the workforce that uses a single agent.
        Can be called when workforce is paused to dynamically add workers.

        Args:
            description (str): Description of the worker node.
            worker (ChatAgent): The agent to be added.
            pool_max_size (int): Maximum size of the agent pool.
                (default: :obj:`10`)

        Returns:
            WorkerManagement: The worker management instance itself.

        Raises:
            RuntimeError: If called while workforce is running (not paused).
            ValueError: If worker has tools and stream mode enabled but
                use_structured_output_handler is False.
        """
        if self._state == "RUNNING":
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
        self.start_child_node_when_paused(worker_node.start())

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
    ) -> 'WorkerManagement':
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
            WorkerManagement: The worker management instance itself.

        Raises:
            RuntimeError: If called while workforce is running (not paused).
        """
        if self._state == "RUNNING":
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
        self.start_child_node_when_paused(worker_node.start())

        if self.metrics_logger:
            self.metrics_logger.log_worker_created(
                worker_id=worker_node.node_id,
                worker_type='RolePlayingWorker',
                role=worker_node.description,
            )
        return self

    def add_workforce(
        self, workforce: 'WorkerManagement'
    ) -> 'WorkerManagement':
        r"""Add a workforce node to the workforce.
        Can be called when workforce is paused to dynamically add workers.

        Args:
            workforce (WorkerManagement): The workforce node to be added.

        Returns:
            WorkerManagement: The worker management instance itself.

        Raises:
            RuntimeError: If called while workforce is running (not paused).
        """
        if self._state == "RUNNING":
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
        self.start_child_node_when_paused(workforce.start())
        return self

    def _validate_agent_compatibility(
        self, agent: ChatAgent, agent_name: str
    ) -> None:
        """Validate agent compatibility (placeholder method)."""
        # This would contain the actual validation logic
        pass

    def _attach_pause_event_to_agent(self, agent: ChatAgent) -> None:
        """Attach pause event to agent (placeholder method)."""
        # This would contain the actual attachment logic
        pass

    def _ensure_pause_event_in_kwargs(
        self, kwargs: Optional[Dict]
    ) -> Optional[Dict]:
        """Ensure pause event is in kwargs (placeholder method)."""
        # This would contain the actual logic
        return kwargs

    def set_channel(self, channel: TaskChannel) -> None:
        """Set the task channel (placeholder method)."""
        # This would contain the actual logic
        pass

    def start(self) -> Coroutine:
        """Start the worker management (placeholder method)."""
        # This would contain the actual start logic
        raise NotImplementedError("WorkerManagement.start() not implemented")
