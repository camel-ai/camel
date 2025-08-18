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
        description="Flag indicating whether the task processing failed."
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
        "This is critical for the task decomposition and execution.",
    )

    # Allow LLMs to output dependencies as a comma-separated string or empty
    # string. This validator converts such cases into a list[str] so that
    # downstream logic does not break with validation errors.
    @staticmethod
    def _split_and_strip(dep_str: str) -> List[str]:
        r"""Utility to split a comma separated string and strip whitespace."""
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
    r"""The result of task assignment for both single and batch assignments."""

    assignments: List[TaskAssignment] = Field(
        description="List of task assignments."
    )


class RecoveryStrategy(str, Enum):
    r"""Strategies for handling failed tasks."""

    RETRY = "retry"
    REPLAN = "replan"
    DECOMPOSE = "decompose"
    CREATE_WORKER = "create_worker"

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


class RecoveryDecision(BaseModel):
    r"""Decision on how to recover from a task failure."""

    strategy: RecoveryStrategy = Field(
        description="The chosen recovery strategy"
    )
    reasoning: str = Field(description="Explanation for the chosen strategy")
    modified_task_content: Optional[str] = Field(
        default=None, description="Modified task content if strategy is REPLAN"
    )


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
                                f"(Attempt {retries+1}/{max_retries})"
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
                            f"(Attempt {retries+1}/{max_retries})"
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
                    f"Unexpected failure in {func.__name__}: {last_exception}"
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
