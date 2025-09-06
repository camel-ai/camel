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
from camel.societies.workforce.prompts import PROCESS_TASK_PROMPT
from camel.societies.workforce.structured_output_handler import (
    StructuredOutputHandler,
)
from camel.societies.workforce.utils import TaskResult
from camel.societies.workforce.worker import Worker
from camel.tasks.task import Task, TaskState, is_task_result_insufficient


class AgentPool:
    r"""A pool of agent instances for efficient reuse.

    This pool manages a collection of pre-cloned agents. It supports
    auto-scaling based ondemand and intelligent reuse of existing agents.

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
    """

    def __init__(
        self,
        base_agent: ChatAgent,
        initial_size: int = 1,
        max_size: int = 10,
        auto_scale: bool = True,
        idle_timeout: float = 180.0,
        max_tasks_per_agent: int = 10,
        min_cleanup_interval: float = 15.0,
        max_cleanup_interval: float = 120.0,
    ):
        self.base_agent = base_agent
        self.max_size = max_size
        self.auto_scale = auto_scale
        self.idle_timeout = idle_timeout
        self._max_tasks_per_agent = max_tasks_per_agent
        self.min_cleanup_interval = min_cleanup_interval
        self.max_cleanup_interval = max_cleanup_interval
        self._agent_metadata_pool: Dict[int, Dict[str, Any]] = {}

        # Pool management
        self._available_agents: deque = deque()
        self._in_use_agents: set = set()
        self._agent_last_used: dict = {}
        self._lock = asyncio.Lock()

        # Statistics
        self._total_borrows = 0
        self._total_clones_created = 0
        self._pool_hits = 0
        self._agents_cleaned = 0
        self._tasks_waited = 0
        self._total_wait_time = 0.0

        # Initialize pool
        self._initialize_pool(initial_size)

    def _initialize_pool(self, size: int) -> None:
        r"""Initialize the pool with the specified number of agents."""
        for _ in range(min(size, self.max_size)):
            agent = self._create_fresh_agent()
            self._available_agents.append(agent)

    def _create_fresh_agent(self) -> ChatAgent:
        r"""Create a fresh agent instance."""
        agent = self.base_agent.clone(with_memory=False)
        self._agent_metadata_pool[id(agent)] = {
            'task_count': 0,
            'error_count': 0,
            'total_tokens_used': 0,
            'average_tokens_per_task': 0,
        }
        self._total_clones_created += 1
        return agent

    def _calculate_affinity_score(
        self,
        agent: ChatAgent,
        metric_weights: Optional[List[float]] = None,
        default_fresh_agent_score: float = 0.75,
    ) -> float:
        r"""Calculate the affinity score of a task based on its metadata."""
        if metric_weights is None:
            metric_weights = [0.7, 0.3]
        metadata = self._agent_metadata_pool.get(id(agent), {})

        success_rate = (
            1 - (metadata['error_count'] / metadata['task_count'])
            if metadata['task_count'] > 0
            else default_fresh_agent_score
        )

        freshness = 1.0 - (metadata['task_count'] / self._max_tasks_per_agent)

        return (metric_weights[0] * success_rate) + (
            metric_weights[1] * max(freshness, 0.0)
        )

    async def get_agent(
        self,
        metric_weights: Optional[List[float]] = None,
        default_fresh_agent_score: float = 0.75,
    ) -> ChatAgent:
        r"""Get an agent from the pool, creating one if necessary."""
        async with self._lock:
            self._total_borrows += 1
            best_agent: Optional[ChatAgent] = None
            metric_weights = metric_weights or [0.7, 0.3]

            if self._available_agents:
                best_agent = max(
                    self._available_agents,
                    key=lambda agent: self._calculate_affinity_score(
                        agent, metric_weights, default_fresh_agent_score
                    ),
                )
                self._available_agents.remove(best_agent)
                self._pool_hits += 1

            elif len(self._in_use_agents) < self.max_size or self.auto_scale:
                best_agent = self._create_fresh_agent()

            else:
                wait_start = time.time()
                self._tasks_waited += 1
                while not self._available_agents:
                    await asyncio.sleep(0.1)
                self._total_wait_time += time.time() - wait_start

                best_agent = max(
                    self._available_agents,
                    key=lambda agent: self._calculate_affinity_score(
                        agent, metric_weights, default_fresh_agent_score
                    ),
                )
                self._available_agents.remove(best_agent)
                self._pool_hits += 1

            best_agent.reset()
            self._in_use_agents.add(id(best_agent))
            return best_agent

    async def return_agent(
        self, agent: ChatAgent, task_status: Optional[str] = None
    ) -> None:
        r"""Return an agent to the pool."""
        async with self._lock:
            agent_id = id(agent)
            if agent_id not in self._in_use_agents:
                return

            if agent_id in self._agent_metadata_pool:
                metadata = self._agent_metadata_pool.get(agent_id, {})
                metadata['task_count'] += 1
                if task_status == 'FAILED':
                    metadata['error_count'] += 1

                _, final_token_count = agent.memory.get_context()
                metadata['total_tokens_used'] += final_token_count
                metadata['average_tokens_per_task'] = (
                    metadata['total_tokens_used'] / metadata['task_count']
                )

                self._agent_last_used[agent_id] = time.time()

            self._in_use_agents.remove(agent_id)
            if len(self._available_agents) < self.max_size:
                self._available_agents.append(agent)

    async def cleanup_idle_agents(self) -> None:
        r"""Remove idle agents from the pool to free memory."""
        if not self.auto_scale:
            return

        async with self._lock:
            current_time = time.time()
            agents_to_remove = []

            for agent in list(self._available_agents):
                agent_id = id(agent)
                last_used = self._agent_last_used.get(agent_id, current_time)

                agent_metadata = self._agent_metadata_pool.get(agent_id, {})
                agent_token_limit = (
                    agent.memory.get_context_creator().token_limit
                )

                if (
                    current_time - last_used > self.idle_timeout
                    or agent_metadata['task_count']
                    >= self._max_tasks_per_agent
                    or agent_metadata['total_tokens_used']
                    >= agent_token_limit * 0.8
                ):
                    agents_to_remove.append(agent)

            self._agents_cleaned += len(agents_to_remove)

            for agent in agents_to_remove:
                self._available_agents.remove(agent)
                self._agent_last_used.pop(id(agent), None)
                self._agent_metadata_pool.pop(id(agent), None)

    def get_stats(self) -> dict:
        r"""Get pool statistics."""
        return {
            "available_agents": len(self._available_agents),
            "in_use_agents": len(self._in_use_agents),
            "pool_size": len(self._agent_metadata_pool),
            "total_borrows": self._total_borrows,
            "total_clones_created": self._total_clones_created,
            "pool_hits": self._pool_hits,
            "hit_rate": self._pool_hits / max(self._total_borrows, 1),
            "agents_cleaned_up": self._agents_cleaned,
            "tasks_had_to_wait": self._tasks_waited,
            "average_wait_time": self._total_wait_time
            / max(self._tasks_waited, 1),
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

    async def _return_worker_agent(
        self, agent: ChatAgent, task_stat: str
    ) -> None:
        r"""Return a worker agent to the pool if pooling is enabled."""
        if self.use_agent_pool and self.agent_pool:
            await self.agent_pool.return_agent(agent, task_stat)
        # If not using pool, agent will be garbage collected

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
            prompt = PROCESS_TASK_PROMPT.format(
                content=task.content,
                parent_task_content=task.parent.content if task.parent else "",
                dependency_tasks_info=dependency_tasks_info,
                additional_info=task.additional_info,
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
                usage_info = response.info.get("usage") or response.info.get(
                    "token_usage"
                )
            total_tokens = (
                usage_info.get("total_tokens", 0) if usage_info else 0
            )

        except Exception as e:
            print(
                f"{Fore.RED}Error processing task {task.id}: "
                f"{type(e).__name__}: {e}{Fore.RESET}"
            )
            # Store error information in task result
            task.result = f"{type(e).__name__}: {e!s}"
            return TaskState.FAILED
        finally:
            # Return agent to pool or let it be garbage collected
            await self._return_worker_agent(worker_agent, task.state.value)

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

        if not self.use_structured_output_handler:
            # Handle native structured output parsing
            if task_result is None:
                print(
                    f"{Fore.RED}Error in worker step execution: Invalid "
                    f"task result{Fore.RESET}"
                )
                task_result = TaskResult(
                    content="Failed to generate valid task result.",
                    failed=True,
                )

        color = Fore.RED if task_result.failed else Fore.GREEN  # type: ignore[union-attr]
        print(
            f"\n{color}{task_result.content}{Fore.RESET}\n======",  # type: ignore[union-attr]
        )

        task.result = task_result.content  # type: ignore[union-attr]

        if task_result.failed:  # type: ignore[union-attr]
            return TaskState.FAILED

        if is_task_result_insufficient(task):
            print(
                f"{Fore.RED}Task {task.id}: Content validation failed - "
                f"task marked as failed{Fore.RESET}"
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
                idle_ratio = (
                    len(self.agent_pool.get_stats()["available_agents"])
                    / self.agent_pool.max_size
                    if self.agent_pool.max_size > 0
                    else 0.0
                )

                sleep_duration = (
                    self.agent_pool.min_cleanup_interval
                    + (
                        self.agent_pool.max_cleanup_interval
                        - self.agent_pool.min_cleanup_interval
                    )
                    * idle_ratio
                )

                await asyncio.sleep(sleep_duration)

                if self.agent_pool:
                    await self.agent_pool.cleanup_idle_agents()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in pool cleanup: {e}")

    def get_pool_stats(self) -> Optional[dict]:
        r"""Get agent pool statistics if pool is enabled."""
        if self.use_agent_pool and self.agent_pool:
            return self.agent_pool.get_stats()
        return None
