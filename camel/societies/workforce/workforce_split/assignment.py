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

import json
from typing import Any, Callable, List, Optional, Set, Tuple

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.societies.workforce.prompts import ASSIGN_TASK_PROMPT
from camel.societies.workforce.utils import (
    TaskAssignment,
    TaskAssignResult,
)
from camel.tasks.task import Task

logger = get_logger(__name__)


class TaskAssignmentManager:
    """Manages task assignment operations including coordination, validation,
    retry logic, and fallback mechanisms.

    This class encapsulates all the functionality related to assigning tasks
    to worker nodes in a workforce system, including handling invalid
    assignments, retries, and fallback worker creation.
    """

    def __init__(
        self,
        coordinator_agent: ChatAgent,
        use_structured_output_handler: bool = True,
        structured_handler: Optional[Any] = None,
    ):
        """Initialize the TaskAssignmentManager.

        Args:
            coordinator_agent (ChatAgent): The coordinator agent for task
                assignment.
            use_structured_output_handler (bool): Whether to use structured
                output handler.
            structured_handler: The structured output handler instance.
        """
        self.coordinator_agent = coordinator_agent
        self.use_structured_output_handler = use_structured_output_handler
        self.structured_handler = structured_handler

    def call_coordinator_for_assignment(
        self,
        tasks: List[Task],
        child_nodes_info: str,
        invalid_ids: Optional[List[str]] = None,
    ) -> TaskAssignResult:
        """Call coordinator agent to assign tasks with optional validation
        feedback in the case of invalid worker IDs.

        Args:
            tasks (List[Task]): Tasks to assign.
            child_nodes_info (str): Information about available worker nodes.
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
                child_nodes_info=child_nodes_info,
            )
        )

        # add feedback if this is a retry
        if invalid_ids:
            feedback = (
                f"VALIDATION ERROR: The following worker IDs are invalid: "
                f"{invalid_ids}. "
                f"Please reassign ONLY the above tasks using valid IDs."
            )
            prompt = prompt + f"\n\n{feedback}"

        # Check if we should use structured handler
        if self.use_structured_output_handler and self.structured_handler:
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

    def validate_assignments(
        self, assignments: List[TaskAssignment], valid_ids: Set[str]
    ) -> Tuple[List[TaskAssignment], List[TaskAssignment]]:
        """Validate task assignments against valid worker IDs.

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

    async def handle_task_assignment_fallbacks(
        self,
        tasks: List[Task],
        create_worker_node_for_task_func: Callable,
    ) -> List[TaskAssignment]:
        """Create new workers for unassigned tasks as fallback.

        Args:
            tasks (List[Task]): Tasks that need new workers.
            create_worker_node_for_task_func: Function to create worker nodes.

        Returns:
            List[TaskAssignment]: Assignments for newly created workers.
        """
        fallback_assignments = []

        for task in tasks:
            logger.info(f"Creating new worker for unassigned task {task.id}")
            new_worker = await create_worker_node_for_task_func(task)

            assignment = TaskAssignment(
                task_id=task.id,
                assignee_id=new_worker.node_id,
                dependencies=[],
            )
            fallback_assignments.append(assignment)

        return fallback_assignments

    async def handle_assignment_retry_and_fallback(
        self,
        invalid_assignments: List[TaskAssignment],
        tasks: List[Task],
        valid_worker_ids: Set[str],
        create_worker_node_for_task_func: Callable,
    ) -> List[TaskAssignment]:
        """Called if Coordinator agent fails to assign tasks to valid worker
        IDs. Handles retry assignment and fallback worker creation for invalid
        assignments.

        Args:
            invalid_assignments (List[TaskAssignment]): Invalid assignments to
                retry.
            tasks (List[Task]): Original tasks list for task lookup.
            valid_worker_ids (set): Set of valid worker IDs.
            create_worker_node_for_task_func: Function to create worker nodes.

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
        retry_result = self.call_coordinator_for_assignment(
            invalid_tasks, "", invalid_ids
        )
        final_assignments = []

        if retry_result.assignments:
            retry_valid, retry_invalid = self.validate_assignments(
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
            fallback_assignments = await self.handle_task_assignment_fallbacks(
                unassigned_tasks, create_worker_node_for_task_func
            )
            final_assignments.extend(fallback_assignments)

        return final_assignments

    def update_task_dependencies_from_assignments(
        self,
        assignments: List[TaskAssignment],
        tasks: List[Task],
        completed_tasks: List[Task],
        pending_tasks: List[Task],
    ) -> None:
        """Update Task.dependencies with actual Task objects based on
        assignments.

        Args:
            assignments (List[TaskAssignment]): The task assignments
                containing dependency IDs.
            tasks (List[Task]): The tasks that were assigned.
            completed_tasks (List[Task]): List of completed tasks.
            pending_tasks (List[Task]): List of pending tasks.
        """
        # Create a lookup map for all available tasks
        all_tasks = {}
        for task_list in [completed_tasks, pending_tasks, tasks]:
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

    async def find_assignee(
        self,
        tasks: List[Task],
        valid_worker_ids: Set[str],
        child_nodes_info: str,
        create_worker_node_for_task_func: Callable,
        completed_tasks: List[Task],
        pending_tasks: List[Task],
    ) -> TaskAssignResult:
        """Assigns multiple tasks to worker nodes with the best capabilities.

        Parameters:
            tasks (List[Task]): The tasks to be assigned.
            valid_worker_ids (Set[str]): Set of valid worker IDs.
            child_nodes_info (str): Information about available worker nodes.
            create_worker_node_for_task_func: Function to create worker nodes.
            completed_tasks (List[Task]): List of completed tasks.
            pending_tasks (List[Task]): List of pending tasks.

        Returns:
            TaskAssignResult: Assignment result containing task assignments
                with their dependencies.
        """
        self.coordinator_agent.reset()

        logger.debug(
            f"Sending batch assignment request to coordinator "
            f"for {len(tasks)} tasks."
        )

        assignment_result = self.call_coordinator_for_assignment(
            tasks, child_nodes_info
        )

        # validate assignments
        valid_assignments, invalid_assignments = self.validate_assignments(
            assignment_result.assignments, valid_worker_ids
        )

        # check if we have assignments for all tasks
        assigned_task_ids = {
            a.task_id for a in valid_assignments + invalid_assignments
        }
        unassigned_tasks = [t for t in tasks if t.id not in assigned_task_ids]

        # if all assignments are valid and all tasks are assigned, return early
        if not invalid_assignments and not unassigned_tasks:
            self.update_task_dependencies_from_assignments(
                valid_assignments, tasks, completed_tasks, pending_tasks
            )
            return TaskAssignResult(assignments=valid_assignments)

        # handle retry and fallback for invalid assignments and unassigned
        # tasks
        retry_and_fallback_assignments = (
            await self.handle_assignment_retry_and_fallback(
                invalid_assignments,
                tasks,
                valid_worker_ids,
                create_worker_node_for_task_func,
            )
        )
        all_assignments = valid_assignments + retry_and_fallback_assignments

        # Update Task.dependencies for all final assignments
        self.update_task_dependencies_from_assignments(
            all_assignments, tasks, completed_tasks, pending_tasks
        )

        return TaskAssignResult(assignments=all_assignments)
