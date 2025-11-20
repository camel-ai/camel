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
from enum import Enum
from functools import wraps
from typing import Callable, List, Optional

from pydantic import BaseModel, Field, field_validator


class WorkerConf(BaseModel):
    r"""The configuration of a worker."""

    role: str = Field(
        description="The role of the agent working in the work node."
    )
    sys_msg: str = Field(
        description="The system message that will be sent to the agent in "
        "the node."
    )
    description: str = Field(
        description="The description of the new work node itself."
    )


class TaskResult(BaseModel):
    r"""The result of a task."""

    content: str = Field(description="The result of the task.")
    failed: bool = Field(
        default=False,
        description="Flag indicating whether the task processing failed.",
    )


class QualityEvaluation(BaseModel):
    r"""Quality evaluation result for a completed task.

    .. deprecated::
        Use :class:`TaskAnalysisResult` instead. This class is kept for
        backward compatibility.
    """

    quality_sufficient: bool = Field(
        description="Whether the task result meets quality standards."
    )
    quality_score: int = Field(
        description="Quality score from 0 to 100.", ge=0, le=100
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of quality issues found in the result.",
    )
    recovery_strategy: Optional[str] = Field(
        default=None,
        description="Recommended recovery strategy if quality is "
        "insufficient: "
        "'retry', 'reassign', 'replan', or 'decompose'.",
    )
    modified_task_content: Optional[str] = Field(
        default=None,
        description="Modified task content for replan strategy.",
    )


class TaskAssignment(BaseModel):
    r"""An individual task assignment within a batch."""

    task_id: str = Field(description="The ID of the task to be assigned.")
    assignee_id: str = Field(
        description="The ID of the worker/workforce to assign the task to."
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of task IDs that must complete before this task. "
        "This is critical for the task decomposition and "
        "execution.",
    )

    # Allow LLMs to output dependencies as a comma-separated string or empty
    # string. This validator converts such cases into a list[str] so that
    # downstream logic does not break with validation errors.
    @staticmethod
    def _split_and_strip(dep_str: str) -> List[str]:
        r"""Utility to split a comma separated string and strip
        whitespace."""
        return [d.strip() for d in dep_str.split(',') if d.strip()]

    @field_validator("dependencies", mode="before")
    def validate_dependencies(cls, v) -> List[str]:
        if v is None:
            return []
        # Handle empty string or comma-separated string from LLM
        if isinstance(v, str):
            return TaskAssignment._split_and_strip(v)
        return v


class TaskAssignResult(BaseModel):
    r"""The result of task assignment for both single and batch
    assignments."""

    assignments: List[TaskAssignment] = Field(
        description="List of task assignments."
    )


class RecoveryStrategy(str, Enum):
    r"""Strategies for handling failed tasks."""

    RETRY = "retry"
    REPLAN = "replan"
    DECOMPOSE = "decompose"
    CREATE_WORKER = "create_worker"
    REASSIGN = "reassign"

    def __str__(self):
        return self.value

    def __repr__(self):
        return f"RecoveryStrategy.{self.name}"


class FailureContext(BaseModel):
    r"""Context information about a task failure."""

    task_id: str = Field(description="ID of the failed task")
    task_content: str = Field(description="Content of the failed task")
    failure_count: int = Field(
        description="Number of times this task has failed"
    )
    error_message: str = Field(description="Detailed error message")
    worker_id: Optional[str] = Field(
        default=None, description="ID of the worker that failed"
    )
    task_depth: int = Field(
        description="Depth of the task in the decomposition hierarchy"
    )
    additional_info: Optional[str] = Field(
        default=None, description="Additional context about the task"
    )


class TaskAnalysisResult(BaseModel):
    r"""Unified result for task failure analysis and quality evaluation.

    This model combines both failure recovery decisions and quality evaluation
    results into a single structure. For failure analysis, only the recovery
    strategy and reasoning fields are populated. For quality evaluation, all
    fields including quality_score and issues are populated.
    """

    # Common fields - always populated
    reasoning: str = Field(
        description="Explanation for the analysis result or recovery "
        "decision"
    )

    recovery_strategy: Optional[RecoveryStrategy] = Field(
        default=None,
        description="Recommended recovery strategy: 'retry', 'replan', "
        "'decompose', 'create_worker', or 'reassign'. None indicates no "
        "recovery needed (quality sufficient).",
    )

    modified_task_content: Optional[str] = Field(
        default=None,
        description="Modified task content if strategy requires replan",
    )

    # Quality-specific fields - populated only for quality evaluation
    quality_score: Optional[int] = Field(
        default=None,
        description="Quality score from 0 to 100 (only for quality "
        "evaluation). "
        "None indicates this is a failure analysis, "
        "not quality evaluation.",
        ge=0,
        le=100,
    )

    issues: List[str] = Field(
        default_factory=list,
        description="List of issues found. For failures: error details. "
        "For quality evaluation: quality issues.",
    )

    @property
    def is_quality_evaluation(self) -> bool:
        r"""Check if this is a quality evaluation result.

        Returns:
            bool: True if this is a quality evaluation (has quality_score),
                False if this is a failure analysis.
        """
        return self.quality_score is not None

    @property
    def quality_sufficient(self) -> bool:
        r"""For quality evaluations, check if quality meets standards.

        Returns:
            bool: True if quality is sufficient (score >= 70 and no recovery
                strategy recommended), False otherwise. Always False for
                failure analysis results.
        """
        return (
            self.quality_score is not None
            and self.quality_score >= 70
            and self.recovery_strategy is None
        )


class PipelineTaskBuilder:
    r"""Helper class for building pipeline tasks with dependencies."""

    def __init__(self):
        """Initialize an empty pipeline task builder."""
        from camel.tasks import Task

        self._TaskClass = Task
        self.task_list = []
        self.task_counter = 0
        self._task_registry = {}  # task_id -> Task mapping for fast lookup
        self._last_task_id = (
            None  # Track the last added task for chain inference
        )
        # Track the last added parallel tasks for sync
        self._last_parallel_tasks: List[str] = []

    def add(
        self,
        content: str,
        task_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        additional_info: Optional[dict] = None,
        auto_depend: bool = True,
    ) -> 'PipelineTaskBuilder':
        """Add a task to the pipeline with support for chaining.

        Args:
            content (str): The content/description of the task.
            task_id (str, optional): Unique identifier for the task. If None,
                a unique ID will be generated. (default: :obj:`None`)
            dependencies (List[str], optional): List of task IDs that this
                task depends on. If None and auto_depend=True, will depend on
                the last added task. (default: :obj:`None`)
            additional_info (dict, optional): Additional information
                for the task. (default: :obj:`None`)
            auto_depend (bool, optional): If True and dependencies is None,
                automatically depend on the last added task.
                (default: :obj:`True`)

        Returns:
            PipelineTaskBuilder: Self for method chaining.

        Raises:
            ValueError: If task_id already exists or if any dependency is
                not found.

        Example:
            >>> builder.add("Step 1").add("Step 2").add("Step 3")
            # Step 2 depends on Step 1, Step 3 depends on Step 2
        """
        # Generate or validate task_id
        task_id = task_id or f"pipeline_task_{self.task_counter}"

        # Check ID uniqueness
        if task_id in self._task_registry:
            raise ValueError(f"Task ID '{task_id}' already exists")

        # Auto-infer dependencies if not specified
        if (
            dependencies is None
            and auto_depend
            and self._last_task_id is not None
        ):
            dependencies = [self._last_task_id]

        # Validate dependencies exist
        dep_tasks = []
        if dependencies:
            missing_deps = [
                dep for dep in dependencies if dep not in self._task_registry
            ]
            if missing_deps:
                raise ValueError(f"Dependencies not found: {missing_deps}")
            dep_tasks = [self._task_registry[dep] for dep in dependencies]

        # Create task
        task = self._TaskClass(
            content=content,
            id=task_id,
            dependencies=dep_tasks,
            additional_info=additional_info,
        )

        self.task_list.append(task)
        self._task_registry[task_id] = task
        self._last_task_id = task_id  # Update last task for chaining
        self.task_counter += 1
        return self

    def add_parallel_tasks(
        self,
        task_contents: List[str],
        dependencies: Optional[List[str]] = None,
        task_id_prefix: str = "parallel",
        auto_depend: bool = True,
    ) -> 'PipelineTaskBuilder':
        """Add multiple parallel tasks that can execute simultaneously.

        Args:
            task_contents (List[str]): List of task content strings.
            dependencies (List[str], optional): Common dependencies for all
                parallel tasks. If None and auto_depend=True, will depend on
                the last added task. (default: :obj:`None`)
            task_id_prefix (str, optional): Prefix for generated task IDs.
                (default: :obj:`"parallel"`)
            auto_depend (bool, optional): If True and dependencies is None,
                automatically depend on the last added task.
                (default: :obj:`True`)

        Returns:
            PipelineTaskBuilder: Self for method chaining.

        Raises:
            ValueError: If any task_id already exists or if any dependency
                is not found.

        Example:
            >>> builder.add("Collect Data").add_parallel_tasks([
            ...     "Technical Analysis", "Fundamental Analysis"
            ... ]).add_sync_task("Generate Report")
        """
        if not task_contents:
            raise ValueError("task_contents cannot be empty")

        # Auto-infer dependencies if not specified
        if (
            dependencies is None
            and auto_depend
            and self._last_task_id is not None
        ):
            dependencies = [self._last_task_id]

        parallel_task_ids = []
        base_counter = (
            self.task_counter
        )  # Save current counter for consistent naming

        for i, content in enumerate(task_contents):
            task_id = f"{task_id_prefix}_{i}_{base_counter}"
            # Use auto_depend=False since we're manually managing dependencies
            self.add(content, task_id, dependencies, auto_depend=False)
            parallel_task_ids.append(task_id)

        # Set the last task to None since we have multiple parallel endings
        # The next task will need to explicitly specify dependencies
        self._last_task_id = None
        # Store parallel task IDs for potential sync operations
        self._last_parallel_tasks = parallel_task_ids

        return self

    def add_sync_task(
        self,
        content: str,
        wait_for: Optional[List[str]] = None,
        task_id: Optional[str] = None,
    ) -> 'PipelineTaskBuilder':
        """Add a synchronization task that waits for multiple tasks.

        Args:
            content (str): Content of the synchronization task.
            wait_for (List[str], optional): List of task IDs to wait for.
                If None, will automatically wait for the last parallel tasks.
                (default: :obj:`None`)
            task_id (str, optional): ID for the sync task. If None, a unique
                ID will be generated. (default: :obj:`None`)

        Returns:
            PipelineTaskBuilder: Self for method chaining.

        Raises:
            ValueError: If task_id already exists or if any dependency is
                not found.

        Example:
            >>> builder.add_parallel_tasks(
            ...     ["Task A", "Task B"]
            ... ).add_sync_task("Merge Results")
            # Automatically waits for both parallel tasks
        """
        # Auto-infer wait_for from last parallel tasks
        if wait_for is None:
            if self._last_parallel_tasks:
                wait_for = self._last_parallel_tasks
                # Clear the parallel tasks after using them
                self._last_parallel_tasks = []
            else:
                raise ValueError(
                    "wait_for cannot be empty for sync task and no "
                    "parallel tasks found"
                )

        if not wait_for:
            raise ValueError("wait_for cannot be empty for sync task")

        return self.add(
            content, task_id, dependencies=wait_for, auto_depend=False
        )

    def build(self) -> List:
        """Build and return the complete task list with dependencies.

        Returns:
            List[Task]: List of tasks with proper dependency relationships.

        Raises:
            ValueError: If there are circular dependencies or other
                validation errors.
        """
        if not self.task_list:
            raise ValueError("No tasks defined in pipeline")

        # Validate no circular dependencies
        self._validate_dependencies()

        return self.task_list.copy()

    def clear(self) -> None:
        """Clear all tasks from the builder."""
        self.task_list.clear()
        self._task_registry.clear()
        self.task_counter = 0
        self._last_task_id = None
        self._last_parallel_tasks = []

    def fork(self, task_contents: List[str]) -> 'PipelineTaskBuilder':
        """Create parallel branches from the current task (alias for
        add_parallel_tasks).

        Args:
            task_contents (List[str]): List of task content strings for
                parallel execution.

        Returns:
            PipelineTaskBuilder: Self for method chaining.

        Example:
            >>> builder.add("Collect Data").fork([
            ...     "Technical Analysis", "Fundamental Analysis"
            ... ]).join("Generate Report")
        """
        return self.add_parallel_tasks(task_contents)

    def join(
        self, content: str, task_id: Optional[str] = None
    ) -> 'PipelineTaskBuilder':
        """Join parallel branches with a synchronization task (alias for
        add_sync_task).

        Args:
            content (str): Content of the join/sync task.
            task_id (str, optional): ID for the sync task.

        Returns:
            PipelineTaskBuilder: Self for method chaining.

        Example:
            >>> builder.fork(["Task A", "Task B"]).join("Merge Results")
        """
        return self.add_sync_task(content, task_id=task_id)

    def _validate_dependencies(self) -> None:
        """Validate that there are no circular dependencies.

        Raises:
            ValueError: If circular dependencies are detected.
        """
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()

        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)

            task = self._task_registry[task_id]
            for dep in task.dependencies:
                if dep.id not in visited:
                    if has_cycle(dep.id):
                        return True
                elif dep.id in rec_stack:
                    return True

            rec_stack.remove(task_id)
            return False

        for task_id in self._task_registry:
            if task_id not in visited:
                if has_cycle(task_id):
                    raise ValueError(
                        f"Circular dependency detected involving task: "
                        f"{task_id}"
                    )

    def get_task_info(self) -> dict:
        """Get information about all tasks in the pipeline.

        Returns:
            dict: Dictionary containing task count and task details.
        """
        return {
            "task_count": len(self.task_list),
            "tasks": [
                {
                    "id": task.id,
                    "content": task.content,
                    "dependencies": [dep.id for dep in task.dependencies],
                }
                for task in self.task_list
            ],
        }


def check_if_running(
    running: bool,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    handle_exceptions: bool = False,
) -> Callable:
    r"""Check if the workforce is (not) running, specified by the boolean
    value. Provides fault tolerance through automatic retries and exception
    handling.

    Args:
        running (bool): Expected running state (True or False).
        max_retries (int, optional): Maximum number of retry attempts if the
            operation fails. Set to 0 to disable retries. (default: :obj:`3`)
        retry_delay (float, optional): Delay in seconds between retry attempts.
            (default: :obj:`1.0`)
        handle_exceptions (bool, optional): If True, catch and log exceptions
            instead of propagating them. (default: :obj:`False`)

    Raises:
        RuntimeError: If the workforce is not in the expected status and
            retries are exhausted or disabled.
        Exception: Any exception raised by the decorated function if
            handle_exceptions is False and retries are exhausted.
    """
    import logging
    import time

    logger = logging.getLogger(__name__)

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            retries = 0
            last_exception = None

            while retries <= max_retries:
                try:
                    # Check running state
                    if self._running != running:
                        status = "not running" if running else "running"
                        error_msg = (
                            f"The workforce is {status}. Cannot perform the "
                            f"operation {func.__name__}."
                        )

                        # If we have retries left, wait and try again
                        if retries < max_retries:
                            logger.warning(
                                f"{error_msg} Retrying in {retry_delay}s... "
                                f"(Attempt {retries + 1}/{max_retries})"
                            )
                            time.sleep(retry_delay)
                            retries += 1
                            continue
                        else:
                            raise RuntimeError(error_msg)

                    return func(self, *args, **kwargs)

                except Exception as e:
                    last_exception = e

                    if isinstance(e, RuntimeError) and "workforce is" in str(
                        e
                    ):
                        raise

                    if retries < max_retries:
                        logger.warning(
                            f"Exception in {func.__name__}: {e}. "
                            f"Retrying in {retry_delay}s... "
                            f"(Attempt {retries + 1}/{max_retries})"
                        )
                        time.sleep(retry_delay)
                        retries += 1
                    else:
                        if handle_exceptions:
                            logger.error(
                                f"Failed to execute {func.__name__} after "
                                f"{max_retries} retries: {e}"
                            )
                            return None
                        else:
                            # Re-raise the exception
                            raise

            # This should not be reached, but just in case
            if handle_exceptions:
                logger.error(
                    f"Unexpected failure in {func.__name__}: "
                    f"{last_exception}"
                )
                return None
            else:
                raise (
                    last_exception
                    if last_exception
                    else RuntimeError(
                        f"Unexpected failure in {func.__name__} "
                        "with no exception captured."
                    )
                )

        return wrapper

    return decorator
