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
import datetime
import time
from collections import deque
from typing import Any, Dict, List, Optional

from colorama import Fore

from camel.agents import ChatAgent
from camel.agents.chat_agent import AsyncStreamingChatAgentResponse
from camel.logger import get_logger
from camel.societies.workforce.prompts import PROCESS_TASK_PROMPT
from camel.societies.workforce.structured_output_handler import (
    StructuredOutputHandler,
)
from camel.societies.workforce.utils import TaskResult
from camel.societies.workforce.worker import Worker
from camel.societies.workforce.workflow_memory_manager import (
    WorkflowMemoryManager,
)
from camel.tasks.task import Task, TaskState, is_task_result_insufficient
from camel.utils.context_utils import ContextUtility

logger = get_logger(__name__)


class AgentPool:
    r"""A pool of agent instances for efficient reuse.

    This pool manages a collection of pre-cloned agents with automatic
    scaling and idle timeout cleanup.

    Args:
        base_agent (ChatAgent): The base agent to clone from.
        initial_size (int): Initial number of agents in the pool.
            (default: :obj:`1`)
        max_size (int): Maximum number of agents in the pool.
            (default: :obj:`10`)
        auto_scale (bool): Whether to automatically scale the pool size.
            (default: :obj:`True`)
        idle_timeout (float): Time in seconds after which idle agents are
            removed. (default: :obj:`180.0`)
        cleanup_interval (float): Fixed interval in seconds between cleanup
            checks. (default: :obj:`60.0`)
    """

    def __init__(
        self,
        base_agent: ChatAgent,
        initial_size: int = 1,
        max_size: int = 10,
        auto_scale: bool = True,
        idle_timeout: float = 180.0,
        cleanup_interval: float = 60.0,
    ):
        self.base_agent = base_agent
        self.max_size = max_size
        self.auto_scale = auto_scale
        self.idle_timeout = idle_timeout
        self.cleanup_interval = cleanup_interval

        # Pool management
        self._available_agents: deque = deque()
        self._in_use_agents: set = set()
        self._agent_last_used: dict = {}
        self._lock = asyncio.Lock()
        self._condition = asyncio.Condition(self._lock)

        # Statistics
        self._total_borrows = 0
        self._total_clones_created = 0
        self._pool_hits = 0
        self._agents_cleaned = 0

        # Initialize pool
        self._initialize_pool(initial_size)

    def _initialize_pool(self, size: int) -> None:
        r"""Initialize the pool with the specified number of agents."""
        for _ in range(min(size, self.max_size)):
            agent = self._create_fresh_agent()
            self._available_agents.append(agent)
            self._agent_last_used[id(agent)] = time.time()

    def _create_fresh_agent(self) -> ChatAgent:
        r"""Create a fresh agent instance."""
        agent = self.base_agent.clone(with_memory=False)
        self._total_clones_created += 1
        return agent

    async def get_agent(self) -> ChatAgent:
        r"""Get an agent from the pool, creating one if necessary."""
        async with self._condition:
            self._total_borrows += 1

            # Try to get available agent or create new one
            while True:
                if self._available_agents:
                    agent = self._available_agents.popleft()
                    self._in_use_agents.add(id(agent))
                    self._pool_hits += 1
                    return agent

                # Check if we can create a new agent
                if len(self._in_use_agents) < self.max_size or self.auto_scale:
                    agent = self._create_fresh_agent()
                    self._in_use_agents.add(id(agent))
                    return agent

                # Wait for an agent to be returned
                await self._condition.wait()

    async def return_agent(self, agent: ChatAgent) -> None:
        r"""Return an agent to the pool."""
        agent_id = id(agent)

        async with self._condition:
            if agent_id not in self._in_use_agents:
                return

            self._in_use_agents.discard(agent_id)

            # Only add back to pool if under max size
            if len(self._available_agents) < self.max_size:
                agent.reset()
                self._agent_last_used[agent_id] = time.time()
                self._available_agents.append(agent)
                # Notify one waiting coroutine that an agent is available
                self._condition.notify()
            else:
                # Remove tracking for agents not returned to pool
                self._agent_last_used.pop(agent_id, None)

    async def cleanup_idle_agents(self) -> None:
        r"""Remove idle agents from the pool to free memory."""
        if not self.auto_scale:
            return

        async with self._condition:
            if not self._available_agents:
                return

            current_time = time.time()
            agents_to_remove = []

            for agent in list(self._available_agents):
                agent_id = id(agent)
                last_used = self._agent_last_used.get(agent_id, current_time)
                if current_time - last_used > self.idle_timeout:
                    agents_to_remove.append(agent)

            for agent in agents_to_remove:
                self._available_agents.remove(agent)
                self._agent_last_used.pop(id(agent), None)
                self._agents_cleaned += 1

    def get_stats(self) -> dict:
        r"""Get pool statistics."""
        return {
            "available_agents": len(self._available_agents),
            "in_use_agents": len(self._in_use_agents),
            "pool_size": len(self._available_agents)
            + len(self._in_use_agents),
            "total_borrows": self._total_borrows,
            "total_clones_created": self._total_clones_created,
            "pool_hits": self._pool_hits,
            "hit_rate": self._pool_hits / max(self._total_borrows, 1),
            "agents_cleaned_up": self._agents_cleaned,
        }


class SingleAgentWorker(Worker):
    r"""A worker node that consists of a single agent.

    Args:
        description (str): Description of the node.
        worker (ChatAgent): Worker of the node. A single agent.
        use_agent_pool (bool): Whether to use agent pool for efficiency.
            (default: :obj:`True`)
        pool_initial_size (int): Initial size of the agent pool.
            (default: :obj:`1`)
        pool_max_size (int): Maximum size of the agent pool.
            (default: :obj:`10`)
        auto_scale_pool (bool): Whether to auto-scale the agent pool.
            (default: :obj:`True`)
        use_structured_output_handler (bool, optional): Whether to use the
            structured output handler instead of native structured output.
            When enabled, the workforce will use prompts with structured
            output instructions and regex extraction to parse responses.
            This ensures compatibility with agents that don't reliably
            support native structured output. When disabled, the workforce
            uses the native response_format parameter.
            (default: :obj:`True`)
        context_utility (ContextUtility, optional): Shared context utility
            instance for workflow management. If provided, all workflow
            operations will use this shared instance instead of creating
            a new one. This ensures multiple workers share the same session
            directory. (default: :obj:`None`)
        enable_workflow_memory (bool, optional): Whether to enable workflow
            memory accumulation during task execution. When enabled,
            conversations from all task executions are accumulated for
            potential workflow saving. Set to True if you plan to call
            save_workflow_memories(). (default: :obj:`False`)
    """

    def __init__(
        self,
        description: str,
        worker: ChatAgent,
        use_agent_pool: bool = True,
        pool_initial_size: int = 1,
        pool_max_size: int = 10,
        auto_scale_pool: bool = True,
        use_structured_output_handler: bool = True,
        context_utility: Optional[ContextUtility] = None,
        enable_workflow_memory: bool = False,
    ) -> None:
        node_id = worker.agent_id
        super().__init__(
            description,
            node_id=node_id,
        )
        self.use_structured_output_handler = use_structured_output_handler
        self.structured_handler = (
            StructuredOutputHandler()
            if use_structured_output_handler
            else None
        )
        self.worker = worker
        self.use_agent_pool = use_agent_pool
        self.enable_workflow_memory = enable_workflow_memory
        self._shared_context_utility = context_utility
        self._context_utility: Optional[ContextUtility] = (
            None  # Will be initialized when needed
        )

        # accumulator agent for collecting conversations
        # from all task processing
        self._conversation_accumulator: Optional[ChatAgent] = None

        # workflow memory manager for handling workflow operations
        self._workflow_manager: Optional[WorkflowMemoryManager] = None

        # note: context utility is set on the worker agent during save/load
        # operations to avoid creating session folders during initialization

        self.agent_pool: Optional[AgentPool] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        # Initialize agent pool if enabled
        if self.use_agent_pool:
            self.agent_pool = AgentPool(
                base_agent=worker,
                initial_size=pool_initial_size,
                max_size=pool_max_size,
                auto_scale=auto_scale_pool,
            )

    def reset(self) -> Any:
        r"""Resets the worker to its initial state."""
        super().reset()
        self.worker.reset()

        # Reset agent pool if it exists
        if self.agent_pool:
            # Stop cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()

            # Reinitialize pool
            self.agent_pool = AgentPool(
                base_agent=self.worker,
            )

    async def _get_worker_agent(self) -> ChatAgent:
        r"""Get a worker agent, either from pool or by cloning."""
        if self.use_agent_pool and self.agent_pool:
            return await self.agent_pool.get_agent()
        else:
            # Fallback to original cloning approach
            return self.worker.clone(with_memory=False)

    async def _return_worker_agent(self, agent: ChatAgent) -> None:
        r"""Return a worker agent to the pool if pooling is enabled."""
        if self.use_agent_pool and self.agent_pool:
            await self.agent_pool.return_agent(agent)
        # If not using pool, agent will be garbage collected

    def _get_context_utility(self) -> ContextUtility:
        r"""Get context utility with lazy initialization."""
        if self._context_utility is None:
            self._context_utility = (
                self._shared_context_utility
                or ContextUtility.get_workforce_shared()
            )
        return self._context_utility

    def _get_conversation_accumulator(self) -> ChatAgent:
        r"""Get or create the conversation accumulator agent."""
        if self._conversation_accumulator is None:
            # create a clone of the original worker to serve as accumulator
            self._conversation_accumulator = self.worker.clone(
                with_memory=False
            )
        return self._conversation_accumulator

    def _get_workflow_manager(self) -> WorkflowMemoryManager:
        r"""Get or create the workflow memory manager."""
        if self._workflow_manager is None:
            context_util = (
                self._shared_context_utility
                if self._shared_context_utility is not None
                else None
            )
            self._workflow_manager = WorkflowMemoryManager(
                worker=self.worker,
                description=self.description,
                context_utility=context_util,
            )
        return self._workflow_manager

    async def _process_task(
        self, task: Task, dependencies: List[Task]
    ) -> TaskState:
        r"""Processes a task with its dependencies using an efficient agent
        management system.

        This method asynchronously processes a given task, considering its
        dependencies, by sending a generated prompt to a worker agent.
        Uses an agent pool for efficiency when enabled, or falls back to
        cloning when pool is disabled.

        Args:
            task (Task): The task to process, which includes necessary details
                like content and type.
            dependencies (List[Task]): Tasks that the given task depends on.

        Returns:
            TaskState: `TaskState.DONE` if processed successfully, otherwise
                `TaskState.FAILED`.
        """
        # Get agent efficiently (from pool or by cloning)
        worker_agent = await self._get_worker_agent()
        response_content = ""

        try:
            dependency_tasks_info = self._get_dep_tasks_info(dependencies)
            prompt = str(
                PROCESS_TASK_PROMPT.format(
                    content=task.content,
                    parent_task_content=task.parent.content
                    if task.parent
                    else "",
                    dependency_tasks_info=dependency_tasks_info,
                    additional_info=task.additional_info,
                )
            )

            if self.use_structured_output_handler and self.structured_handler:
                # Use structured output handler for prompt-based extraction
                enhanced_prompt = (
                    self.structured_handler.generate_structured_prompt(
                        base_prompt=prompt,
                        schema=TaskResult,
                        examples=[
                            {
                                "content": "I have successfully completed the "
                                "task...",
                                "failed": False,
                            }
                        ],
                        additional_instructions="Ensure you provide a clear "
                        "description of what was done and whether the task "
                        "succeeded or failed.",
                    )
                )
                response = await worker_agent.astep(enhanced_prompt)

                # Handle streaming response
                if isinstance(response, AsyncStreamingChatAgentResponse):
                    content = ""
                    async for chunk in response:
                        if chunk.msg:
                            content = chunk.msg.content
                    response_content = content
                else:
                    # Regular ChatAgentResponse
                    response_content = (
                        response.msg.content if response.msg else ""
                    )

                task_result = (
                    self.structured_handler.parse_structured_response(
                        response_text=response_content,
                        schema=TaskResult,
                        fallback_values={
                            "content": "Task processing failed",
                            "failed": True,
                        },
                    )
                )
            else:
                # Use native structured output if supported
                response = await worker_agent.astep(
                    prompt, response_format=TaskResult
                )

                # Handle streaming response for native output
                if isinstance(response, AsyncStreamingChatAgentResponse):
                    task_result = None
                    async for chunk in response:
                        if chunk.msg and chunk.msg.parsed:
                            task_result = chunk.msg.parsed
                            response_content = chunk.msg.content
                    # If no parsed result found in streaming, create fallback
                    if task_result is None:
                        task_result = TaskResult(
                            content="Failed to parse streaming response",
                            failed=True,
                        )
                else:
                    # Regular ChatAgentResponse
                    task_result = response.msg.parsed
                    response_content = (
                        response.msg.content if response.msg else ""
                    )

            # Get token usage from the response
            if isinstance(response, AsyncStreamingChatAgentResponse):
                # For streaming responses, get the final response info
                final_response = await response
                usage_info = final_response.info.get(
                    "usage"
                ) or final_response.info.get("token_usage")
            else:
                final_response = response
                usage_info = response.info.get("usage") or response.info.get(
                    "token_usage"
                )
            total_tokens = (
                usage_info.get("total_tokens", 0) if usage_info else 0
            )

            # collect conversation from working agent to
            # accumulator for workflow memory
            # Only transfer memory if workflow memory is enabled
            if self.enable_workflow_memory:
                accumulator = self._get_conversation_accumulator()

                # transfer all memory records from working agent to accumulator
                try:
                    # retrieve all context records from the working agent
                    work_records = worker_agent.memory.retrieve()

                    # write these records to the accumulator's memory
                    memory_records = [
                        record.memory_record for record in work_records
                    ]
                    accumulator.memory.write_records(memory_records)

                    logger.debug(
                        f"Transferred {len(memory_records)} memory records to "
                        f"accumulator"
                    )

                except Exception as e:
                    logger.warning(
                        f"Failed to transfer conversation to accumulator: {e}"
                    )

        except Exception as e:
            logger.error(
                f"Error processing task {task.id}: {type(e).__name__}: {e}"
            )
            # Store error information in task result
            task.result = f"{type(e).__name__}: {e!s}"
            return TaskState.FAILED
        finally:
            # Return agent to pool or let it be garbage collected
            await self._return_worker_agent(worker_agent)

        # Populate additional_info with worker attempt details
        if task.additional_info is None:
            task.additional_info = {}

        # Create worker attempt details with descriptive keys
        worker_attempt_details = {
            "agent_id": getattr(
                worker_agent, "agent_id", worker_agent.role_name
            ),
            "original_worker_id": getattr(
                self.worker, "agent_id", self.worker.role_name
            ),
            "timestamp": str(datetime.datetime.now()),
            "description": f"Attempt by "
            f"{getattr(worker_agent, 'agent_id', worker_agent.role_name)} "
            f"(from pool/clone of "
            f"{getattr(self.worker, 'agent_id', self.worker.role_name)}) "
            f"to process task: {task.content}",
            "response_content": response_content[:50],
            "tool_calls": str(
                final_response.info.get("tool_calls")
                if isinstance(response, AsyncStreamingChatAgentResponse)
                else response.info.get("tool_calls")
            )[:50],
            "total_tokens": total_tokens,
        }

        # Store the worker attempt in additional_info
        if "worker_attempts" not in task.additional_info:
            task.additional_info["worker_attempts"] = []
        task.additional_info["worker_attempts"].append(worker_attempt_details)

        # Store the actual token usage for this specific task
        task.additional_info["token_usage"] = {"total_tokens": total_tokens}

        print(f"======\n{Fore.GREEN}Response from {self}:{Fore.RESET}")
        logger.info(f"Response from {self}:")

        if not self.use_structured_output_handler:
            # Handle native structured output parsing
            if task_result is None:
                logger.error(
                    "Error in worker step execution: Invalid task result"
                )
                task_result = TaskResult(
                    content="Failed to generate valid task result.",
                    failed=True,
                )

        color = Fore.RED if task_result.failed else Fore.GREEN  # type: ignore[union-attr]
        print(
            f"\n{color}{task_result.content}{Fore.RESET}\n======",  # type: ignore[union-attr]
        )
        if task_result.failed:  # type: ignore[union-attr]
            logger.error(f"{task_result.content}")  # type: ignore[union-attr]
        else:
            logger.info(f"{task_result.content}")  # type: ignore[union-attr]

        task.result = task_result.content  # type: ignore[union-attr]

        if task_result.failed:  # type: ignore[union-attr]
            return TaskState.FAILED

        if is_task_result_insufficient(task):
            logger.warning(
                f"Task {task.id}: Content validation failed - "
                f"task marked as failed"
            )
            return TaskState.FAILED
        return TaskState.DONE

    async def _listen_to_channel(self):
        r"""Override to start cleanup task when pool is enabled."""
        # Start cleanup task for agent pool
        if self.use_agent_pool and self.agent_pool:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

        # Call parent implementation
        await super()._listen_to_channel()

        # Stop cleanup task
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()

    async def _periodic_cleanup(self):
        r"""Periodically clean up idle agents from the pool."""
        while True:
            try:
                # Fixed interval cleanup
                if self.agent_pool:
                    await asyncio.sleep(self.agent_pool.cleanup_interval)
                    await self.agent_pool.cleanup_idle_agents()
                else:
                    break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in pool cleanup: {e}")

    def get_pool_stats(self) -> Optional[dict]:
        r"""Get agent pool statistics if pool is enabled."""
        if self.use_agent_pool and self.agent_pool:
            return self.agent_pool.get_stats()
        return None

    def save_workflow_memories(self) -> Dict[str, Any]:
        r"""Save the worker's current workflow memories using agent
        summarization.

        .. deprecated:: 0.2.80
            Use :meth:`save_workflow_memories_async` for async/await support
            and better integration with parallel workflow saving.

        This method generates a workflow summary from the worker agent's
        conversation history and saves it to a markdown file. The filename
        is based on either the worker's explicit role_name or the generated
        task_title from the summary.

        Delegates to WorkflowMemoryManager for all workflow operations.

        Returns:
            Dict[str, Any]: Result dictionary with keys:
                - status (str): "success" or "error"
                - summary (str): Generated workflow summary
                - file_path (str): Path to saved file
                - worker_description (str): Worker description used

        See Also:
            :meth:`save_workflow_memories_async`: Async version for better
                performance in parallel workflows.
        """
        import warnings

        warnings.warn(
            "save_workflow_memories() is synchronous. Consider using "
            "save_workflow_memories_async() for async/await support.",
            DeprecationWarning,
            stacklevel=2,
        )

        manager = self._get_workflow_manager()
        result = manager.save_workflow(
            conversation_accumulator=self._conversation_accumulator
        )

        # clean up accumulator after successful save
        if (
            result.get("status") == "success"
            and self._conversation_accumulator is not None
        ):
            logger.info(
                "Cleaning up conversation accumulator after workflow "
                "summarization"
            )
            self._conversation_accumulator = None

        return result

    async def save_workflow_memories_async(self) -> Dict[str, Any]:
        r"""Asynchronously save the worker's current workflow memories using
        agent summarization.

        This is the async version of save_workflow_memories() that uses
        asummarize() for non-blocking LLM calls, enabling parallel
        summarization of multiple workers.

        Delegates to WorkflowMemoryManager for all workflow operations.

        Returns:
            Dict[str, Any]: Result dictionary with keys:
                - status (str): "success" or "error"
                - summary (str): Generated workflow summary
                - file_path (str): Path to saved file
                - worker_description (str): Worker description used
        """
        manager = self._get_workflow_manager()
        result = await manager.save_workflow_async(
            conversation_accumulator=self._conversation_accumulator
        )

        # clean up accumulator after successful save
        if (
            result.get("status") == "success"
            and self._conversation_accumulator is not None
        ):
            logger.info(
                "Cleaning up conversation accumulator after workflow "
                "summarization"
            )
            self._conversation_accumulator = None

        return result

    def load_workflow_memories(
        self,
        pattern: Optional[str] = None,
        max_workflows: int = 3,
        session_id: Optional[str] = None,
        use_smart_selection: bool = True,
    ) -> bool:
        r"""Load workflow memories using intelligent agent-based selection.

        This method uses the worker agent to intelligently select the most
        relevant workflows based on metadata (title, description, tags)
        rather than simple filename pattern matching.

        Delegates to WorkflowMemoryManager for all workflow operations.

        Args:
            pattern (Optional[str]): Legacy parameter for backward
                compatibility. When use_smart_selection=False, uses this
                pattern for file matching. Ignored when smart selection
                is enabled.
            max_workflows (int): Maximum number of workflow files to load.
                (default: :obj:`3`)
            session_id (Optional[str]): Specific workforce session ID to load
                from. If None, searches across all sessions.
                (default: :obj:`None`)
            use_smart_selection (bool): Whether to use agent-based intelligent
                workflow selection. When True, uses metadata and LLM to select
                most relevant workflows. When False, falls back to pattern
                matching. (default: :obj:`True`)

        Returns:
            bool: True if workflow memories were successfully loaded, False
                otherwise.
        """
        manager = self._get_workflow_manager()
        return manager.load_workflows(
            pattern=pattern,
            max_files_to_load=max_workflows,
            session_id=session_id,
            use_smart_selection=use_smart_selection,
        )
