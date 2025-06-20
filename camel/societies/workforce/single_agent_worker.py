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
import json
import time
from collections import deque
from typing import Any, List, Optional

from colorama import Fore

from camel.agents import ChatAgent
from camel.societies.workforce.prompts import PROCESS_TASK_PROMPT
from camel.societies.workforce.utils import TaskResult
from camel.societies.workforce.worker import Worker
from camel.tasks.task import Task, TaskState, validate_task_content


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
        scale_factor (float): Factor by which to scale the pool when needed.
            (default: :obj:`1.5`)
        idle_timeout (float): Time in seconds after which idle agents are
            removed. (default: :obj:`180.0`)
    """

    def __init__(
        self,
        base_agent: ChatAgent,
        initial_size: int = 1,
        max_size: int = 10,
        auto_scale: bool = True,
        scale_factor: float = 1.5,
        idle_timeout: float = 180.0,  # 3 minutes
    ):
        self.base_agent = base_agent
        self.max_size = max_size
        self.auto_scale = auto_scale
        self.scale_factor = scale_factor
        self.idle_timeout = idle_timeout

        # Pool management
        self._available_agents: deque = deque()
        self._in_use_agents: set = set()
        self._agent_last_used: dict = {}
        self._lock = asyncio.Lock()

        # Statistics
        self._total_borrows = 0
        self._total_clones_created = 0
        self._pool_hits = 0

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
        self._total_clones_created += 1
        return agent

    async def get_agent(self) -> ChatAgent:
        r"""Get an agent from the pool, creating one if necessary."""
        async with self._lock:
            self._total_borrows += 1

            # Try to get from available agents first
            if self._available_agents:
                agent = self._available_agents.popleft()
                self._in_use_agents.add(id(agent))
                self._pool_hits += 1

                # Reset the agent state
                agent.reset()
                return agent

            # Check if we can create new agents
            total_agents = len(self._available_agents) + len(
                self._in_use_agents
            )
            if total_agents < self.max_size:
                agent = self._create_fresh_agent()
                self._in_use_agents.add(id(agent))
                return agent

            # Pool exhausted, wait and retry or create temporary agent
            if self.auto_scale:
                # Create a temporary agent that won't be returned to pool
                return self._create_fresh_agent()
            else:
                # Wait for an agent to become available
                while not self._available_agents:
                    await asyncio.sleep(0.1)

                agent = self._available_agents.popleft()
                self._in_use_agents.add(id(agent))
                agent.reset()
                return agent

    async def return_agent(self, agent: ChatAgent) -> None:
        r"""Return an agent to the pool."""
        async with self._lock:
            agent_id = id(agent)

            if agent_id in self._in_use_agents:
                self._in_use_agents.remove(agent_id)

                # Only return to pool if we're under max size
                if len(self._available_agents) < self.max_size:
                    # Reset agent state before returning to pool
                    agent.reset()
                    self._available_agents.append(agent)
                    self._agent_last_used[agent_id] = time.time()

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

                if current_time - last_used > self.idle_timeout:
                    agents_to_remove.append(agent)

            for agent in agents_to_remove:
                self._available_agents.remove(agent)
                agent_id = id(agent)
                self._agent_last_used.pop(agent_id, None)

    def get_stats(self) -> dict:
        r"""Get pool statistics."""
        return {
            "available_agents": len(self._available_agents),
            "in_use_agents": len(self._in_use_agents),
            "total_borrows": self._total_borrows,
            "total_clones_created": self._total_clones_created,
            "pool_hits": self._pool_hits,
            "hit_rate": self._pool_hits / max(self._total_borrows, 1),
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
    """

    def __init__(
        self,
        description: str,
        worker: ChatAgent,
        use_agent_pool: bool = True,
        pool_initial_size: int = 1,
        pool_max_size: int = 10,
        auto_scale_pool: bool = True,
    ) -> None:
        node_id = worker.agent_id
        super().__init__(
            description,
            node_id=node_id,
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

    async def _return_worker_agent(self, agent: ChatAgent) -> None:
        r"""Return a worker agent to the pool if pooling is enabled."""
        if self.use_agent_pool and self.agent_pool:
            await self.agent_pool.return_agent(agent)
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

        try:
            dependency_tasks_info = self._get_dep_tasks_info(dependencies)
            prompt = PROCESS_TASK_PROMPT.format(
                content=task.content,
                dependency_tasks_info=dependency_tasks_info,
                additional_info=task.additional_info,
            )

            response = await worker_agent.astep(
                prompt, response_format=TaskResult
            )
        except Exception as e:
            print(
                f"{Fore.RED}Error processing task {task.id}: "
                f"{type(e).__name__}: {e}{Fore.RESET}"
            )
            return TaskState.FAILED
        finally:
            # Return agent to pool or let it be garbage collected
            await self._return_worker_agent(worker_agent)

        # Get actual token usage from the agent that processed this task
        try:
            _, total_token_count = worker_agent.memory.get_context()
        except Exception:
            # Fallback if memory context unavailable
            total_token_count = 0

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
            f"to process task {task.content}",
            "response_content": response.msg.content,
            "tool_calls": response.info.get("tool_calls"),
            "total_token_count": total_token_count,
        }

        # Store the worker attempt in additional_info
        if "worker_attempts" not in task.additional_info:
            task.additional_info["worker_attempts"] = []
        task.additional_info["worker_attempts"].append(worker_attempt_details)

        # Store the actual token usage for this specific task
        task.additional_info["token_usage"] = {
            "total_tokens": total_token_count
        }

        print(f"======\n{Fore.GREEN}Reply from {self}:{Fore.RESET}")

        try:
            result_dict = json.loads(response.msg.content)
            task_result = TaskResult(**result_dict)
        except json.JSONDecodeError as e:
            print(
                f"{Fore.RED}JSON parsing error for task {task.id}: "
                f"Invalid response format - {e}{Fore.RESET}"
            )
            return TaskState.FAILED

        color = Fore.RED if task_result.failed else Fore.GREEN
        print(
            f"\n{color}{task_result.content}{Fore.RESET}\n======",
        )

        if task_result.failed:
            return TaskState.FAILED

        if not validate_task_content(task_result.content, task.id):
            print(
                f"{Fore.RED}Task {task.id}: Content validation failed - "
                f"task marked as failed{Fore.RESET}"
            )
            return TaskState.FAILED

        task.result = task_result.content
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
                await asyncio.sleep(60)  # Cleanup every minute
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
