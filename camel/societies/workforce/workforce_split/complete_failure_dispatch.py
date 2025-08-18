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
import time
import uuid
from collections import deque
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

from colorama import Fore

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.messages.base import BaseMessage
from camel.societies.workforce.role_playing_worker import RolePlayingWorker
from camel.societies.workforce.single_agent_worker import SingleAgentWorker
from camel.societies.workforce.utils import (
    RecoveryStrategy,
)
from camel.tasks.task import Task, TaskState
from camel.utils import dependencies_required

if TYPE_CHECKING:
    from camel.societies.workforce.workforce_split.core import (
        WorkforceCore as Workforce,
    )

logger = get_logger(__name__)

# Constants for configuration values
MAX_TASK_RETRIES = 3
MAX_PENDING_TASKS_LIMIT = 20


class WorkforceFailureDispatch:
    r"""A class that provides workforce failure handling and dispatch
    utilities.

    This class encapsulates various functions for handling failed tasks,
    completed tasks, graceful shutdown, workforce cloning, and MCP server
    creation for workforce management.
    """

    def __init__(
        self,
        max_task_retries: int = MAX_TASK_RETRIES,
        max_pending_tasks_limit: int = MAX_PENDING_TASKS_LIMIT,
    ):
        r"""Initialize the WorkforceFailureDispatch class.

        Args:
            max_task_retries (int): Maximum number of retry attempts for
                failed tasks. (default: :obj:`MAX_TASK_RETRIES`)
            max_pending_tasks_limit (int): Maximum number of pending tasks
                before halting. (default: :obj:`MAX_PENDING_TASKS_LIMIT`)
        """
        self.max_task_retries = max_task_retries
        self.max_pending_tasks_limit = max_pending_tasks_limit

    async def handle_failed_task(
        self, workforce_instance: "Workforce", task: Task
    ) -> bool:
        r"""Handle a failed task with intelligent recovery strategies.

        Args:
            workforce_instance: The workforce instance
            task (Task): The task that failed.

        Returns:
            bool: True if the workforce should halt, False otherwise.
        """
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

        if workforce_instance.metrics_logger:
            workforce_instance.metrics_logger.log_task_failed(
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
        if task.failure_count >= self.max_task_retries:
            logger.error(
                f"Task {task.id} has exceeded maximum retry attempts "
                f"({self.max_task_retries}). Final failure "
                f"reason: {detailed_error}. "
                f"Task content: '{task.content}'"
            )
            workforce_instance._cleanup_task_tracking(task.id)
            # Mark task as completed for dependency tracking before halting
            workforce_instance._completed_tasks.append(task)
            if task.id in workforce_instance._assignees:
                await workforce_instance._channel.archive_task(task.id)
            return True

        # If too many tasks are failing rapidly, also halt to prevent infinite
        # loops
        if (
            len(workforce_instance._pending_tasks)
            > self.max_pending_tasks_limit
        ):
            logger.error(
                f"Too many pending tasks "
                f"({len(workforce_instance._pending_tasks)} > "
                f"{self.max_pending_tasks_limit}). Halting to prevent task "
                f"explosion. Last failed task: {task.id}"
            )
            workforce_instance._cleanup_task_tracking(task.id)
            # Mark task as completed for dependency tracking before halting
            workforce_instance._completed_tasks.append(task)
            if task.id in workforce_instance._assignees:
                await workforce_instance._channel.archive_task(task.id)
            return True

        # Use intelligent failure analysis to decide recovery strategy
        recovery_decision = workforce_instance._analyze_failure(
            task, detailed_error
        )

        logger.info(
            f"Task {task.id} failure "
            f"analysis: {recovery_decision.strategy.value} - "
            f"{recovery_decision.reasoning}"
        )

        # Clean up tracking before attempting recovery
        if task.id in workforce_instance._assignees:
            await workforce_instance._channel.archive_task(task.id)
        workforce_instance._cleanup_task_tracking(task.id)

        try:
            if recovery_decision.strategy == RecoveryStrategy.RETRY:
                # Simply retry the task by reposting it
                if task.id in workforce_instance._assignees:
                    assignee_id = workforce_instance._assignees[task.id]
                    await workforce_instance._post_task(task, assignee_id)
                    action_taken = f"retried with same worker {assignee_id}"
                else:
                    # Find a new assignee and retry
                    batch_result = await workforce_instance._find_assignee(
                        [task]
                    )
                    assignment = batch_result.assignments[0]
                    workforce_instance._assignees[task.id] = (
                        assignment.assignee_id
                    )
                    await workforce_instance._post_task(
                        task, assignment.assignee_id
                    )
                    action_taken = (
                        f"retried with new worker {assignment.assignee_id}"
                    )

            elif recovery_decision.strategy == RecoveryStrategy.REPLAN:
                # Modify the task content and retry
                if recovery_decision.modified_task_content:
                    task.content = recovery_decision.modified_task_content
                    logger.info(f"Task {task.id} content modified for replan")

                # Repost the modified task
                if task.id in workforce_instance._assignees:
                    assignee_id = workforce_instance._assignees[task.id]
                    await workforce_instance._post_task(task, assignee_id)
                    action_taken = (
                        f"replanned and retried with worker {assignee_id}"
                    )
                else:
                    # Find a new assignee for the replanned task
                    batch_result = await workforce_instance._find_assignee(
                        [task]
                    )
                    assignment = batch_result.assignments[0]
                    workforce_instance._assignees[task.id] = (
                        assignment.assignee_id
                    )
                    await workforce_instance._post_task(
                        task, assignment.assignee_id
                    )
                    action_taken = (
                        f"replanned and assigned to "
                        f"worker {assignment.assignee_id}"
                    )

            elif recovery_decision.strategy == RecoveryStrategy.DECOMPOSE:
                # Decompose the task into subtasks
                subtasks_result = workforce_instance._decompose_task(task)

                # Handle both streaming and non-streaming results
                if isinstance(subtasks_result, Generator):
                    # This is a generator (streaming mode)
                    subtasks = []
                    for new_tasks in subtasks_result:
                        subtasks.extend(new_tasks)
                else:
                    # This is a regular list (non-streaming mode)
                    subtasks = subtasks_result
                if workforce_instance.metrics_logger and subtasks:
                    workforce_instance.metrics_logger.log_task_decomposed(
                        parent_task_id=task.id,
                        subtask_ids=[st.id for st in subtasks],
                    )
                    for subtask in subtasks:
                        workforce_instance.metrics_logger.log_task_created(
                            task_id=subtask.id,
                            description=subtask.content,
                            parent_task_id=task.id,
                            task_type=subtask.type,
                            metadata=subtask.additional_info,
                        )
                # Insert packets at the head of the queue
                workforce_instance._pending_tasks.extendleft(
                    reversed(subtasks)
                )

                await workforce_instance._post_ready_tasks()
                action_taken = f"decomposed into {len(subtasks)} subtasks"

                logger.debug(
                    f"Task {task.id} failed and was {action_taken}. "
                    f"Dependencies updated for subtasks."
                )

                # Sync shared memory after task decomposition
                if workforce_instance.share_memory:
                    logger.info(
                        f"Syncing shared memory after "
                        f"task {task.id} decomposition"
                    )
                    workforce_instance._sync_shared_memory()

                # Check if any pending tasks are now ready to execute
                await workforce_instance._post_ready_tasks()
                return False

            elif recovery_decision.strategy == RecoveryStrategy.CREATE_WORKER:
                assignee = (
                    await workforce_instance._create_worker_node_for_task(task)
                )
                await workforce_instance._post_task(task, assignee.node_id)
                action_taken = (
                    f"created new worker {assignee.node_id} and assigned "
                    f"task {task.id} to it"
                )
        except Exception as e:
            logger.error(f"Recovery strategy failed for task {task.id}: {e}")
            # If max retries reached, halt the workforce
            if task.failure_count >= self.max_task_retries:
                workforce_instance._completed_tasks.append(task)
                return True
            workforce_instance._completed_tasks.append(task)
            return False

        logger.debug(
            f"Task {task.id} failed and was {action_taken}. "
            f"Updating dependency state."
        )
        # Mark task as completed for dependency tracking
        workforce_instance._completed_tasks.append(task)

        # Sync shared memory after task completion to share knowledge
        if workforce_instance.share_memory:
            logger.info(
                f"Syncing shared memory after task {task.id} completion"
            )
            workforce_instance._sync_shared_memory()

        # Check if any pending tasks are now ready to execute
        await workforce_instance._post_ready_tasks()
        return False

    async def handle_completed_task(
        self, workforce_instance: "Workforce", task: Task
    ) -> None:
        r"""Handle a completed task and update workforce state.

        Args:
            workforce_instance: The workforce instance
            task (Task): The task that was completed.
        """
        if workforce_instance.metrics_logger:
            worker_id = task.assigned_worker_id or "unknown"
            processing_time_seconds = None
            token_usage = None

            # Get processing time from task start time or additional info
            if task.id in workforce_instance._task_start_times:
                processing_time_seconds = (
                    time.time() - workforce_instance._task_start_times[task.id]
                )
                workforce_instance._cleanup_task_tracking(task.id)
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
                        for child in workforce_instance._children
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
            workforce_instance.metrics_logger.log_task_completed(
                task_id=task.id,
                worker_id=worker_id,
                result_summary=task.result if task.result else "Completed",
                processing_time_seconds=processing_time_seconds,
                token_usage=token_usage,
                metadata={'current_state': task.state.value},
            )

        # Find and remove the completed task from pending tasks
        tasks_list = list(workforce_instance._pending_tasks)
        found_and_removed = False

        for i, pending_task in enumerate(tasks_list):
            if pending_task.id == task.id:
                # Remove this specific task
                tasks_list.pop(i)
                workforce_instance._pending_tasks = deque(tasks_list)
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
        if task.id in workforce_instance._assignees:
            await workforce_instance._channel.archive_task(task.id)

        # Ensure it's in completed tasks set by updating if it exists or
        # appending if it's new.
        task_found_in_completed = False
        for i, t in enumerate(workforce_instance._completed_tasks):
            if t.id == task.id:
                workforce_instance._completed_tasks[i] = task
                task_found_in_completed = True
                break
        if not task_found_in_completed:
            workforce_instance._completed_tasks.append(task)

        # Handle parent task completion logic
        parent = task.parent
        if parent:
            # Check if all subtasks are completed and successful
            all_subtasks_done = all(
                any(
                    t.id == sub.id and t.state == TaskState.DONE
                    for t in workforce_instance._completed_tasks
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
                            for t in workforce_instance._completed_tasks
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
                await self.handle_completed_task(workforce_instance, parent)

        # Sync shared memory after task completion to share knowledge
        if workforce_instance.share_memory:
            logger.info(
                f"Syncing shared memory after task {task.id} completion"
            )
            workforce_instance._sync_shared_memory()

        # Check if any pending tasks are now ready to execute
        await workforce_instance._post_ready_tasks()

    async def graceful_shutdown(
        self, workforce_instance: "Workforce", failed_task: Task
    ) -> None:
        r"""Handle graceful shutdown with configurable timeout.

        This is used to keep the workforce running for a while to debug
        the failed task.

        Args:
            workforce_instance: The workforce instance
            failed_task (Task): The task that failed and triggered shutdown.
        """
        if workforce_instance.graceful_shutdown_timeout <= 0:
            # Immediate shutdown if timeout is 0 or negative
            return

        logger.warning(
            f"Workforce will shutdown in "
            f"{workforce_instance.graceful_shutdown_timeout} "
            f"seconds due to failure. You can use this time to inspect the "
            f"current state of the workforce."
        )
        # Wait for the full timeout period
        await asyncio.sleep(workforce_instance.graceful_shutdown_timeout)

    def clone_workforce(
        self, workforce_instance: "Workforce", with_memory: bool = False
    ) -> 'Workforce':
        r"""Creates a new instance of Workforce with the same configuration.

        Args:
            workforce_instance: The workforce instance to clone
            with_memory (bool, optional): Whether to copy the memory
                (conversation history) to the new instance. If True, the new
                instance will have the same conversation history. If False,
                the new instance will have a fresh memory.
                (default: :obj:`False`)

        Returns:
            Workforce: A new instance of Workforce with the same configuration.
        """
        # Create a new instance with the same configuration
        new_instance = workforce_instance.__class__(
            description=workforce_instance.description,
            coordinator_agent=workforce_instance.coordinator_agent.clone(
                with_memory
            ),
            task_agent=workforce_instance.task_agent.clone(with_memory),
            new_worker_agent=workforce_instance.new_worker_agent.clone(
                with_memory
            )
            if workforce_instance.new_worker_agent
            else None,
            graceful_shutdown_timeout=workforce_instance.graceful_shutdown_timeout,
            share_memory=workforce_instance.share_memory,
            use_structured_output_handler=workforce_instance.use_structured_output_handler,
        )

        for child in workforce_instance._children:
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
            elif isinstance(child, workforce_instance.__class__):
                new_instance.add_workforce(
                    self.clone_workforce(child, with_memory)
                )
            else:
                logger.warning(f"{type(child)} is not being cloned.")
                continue

        return new_instance

    @dependencies_required("mcp")
    def to_mcp(
        self,
        workforce_instance: "Workforce",
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
            workforce_instance: The workforce instance
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
        workforce_ref = workforce_instance

        # Process task tool
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
                result_task = await workforce_ref.process_task_async(task)
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
            """Reset the workforce to its initial state.

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
                workforce_ref.reset()
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
                "node_id": workforce_ref.node_id,
                "description": workforce_ref.description,
                "mcp_description": description,
                "children_count": len(workforce_ref._children),
                "is_running": workforce_ref._running,
                "pending_tasks_count": len(workforce_ref._pending_tasks),
                "current_task_id": (
                    workforce_ref._task.id if workforce_ref._task else None
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
            for child in workforce_ref._children:
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
                elif isinstance(child, workforce_ref.__class__):
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
                if workforce_ref._running:
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
                    workforce_ref._validate_agent_compatibility(
                        agent, "Worker agent"
                    )
                except ValueError as e:
                    return {
                        "status": "error",
                        "message": str(e),
                    }

                workforce_ref.add_single_agent_worker(description, agent)

                return {
                    "status": "success",
                    "message": f"Single agent worker '{description}' added",
                    "worker_id": workforce_ref._children[-1].node_id,
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
                if workforce_ref._running:
                    return {
                        "status": "error",
                        "message": "Cannot add workers while workforce is running",  # noqa: E501
                    }

                workforce_ref.add_role_playing_worker(
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
                    "worker_id": workforce_ref._children[-1].node_id,
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
