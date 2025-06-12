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
from functools import wraps
from typing import Callable

from pydantic import BaseModel, Field

from camel.logger import get_logger

logger = get_logger(__name__)


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


class TaskAssignResult(BaseModel):
    r"""The result of task assignment."""

    assignee_id: str = Field(
        description="The ID of the workforce that is assigned to the task."
    )


def check_if_running(running: bool) -> Callable:
    r"""Check if the workforce is (not) running, specified the boolean value.
    If the workforce is not in the expected status, raise an exception.

    Raises:
        RuntimeError: If the workforce is not in the expected status.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._running != running:
                status = "not running" if running else "running"
                raise RuntimeError(
                    f"The workforce is {status}. Cannot perform the "
                    f"operation {func.__name__}."
                )
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


def validate_task_content(
    content: str, task_id: str = "unknown", min_length: int = 10
) -> bool:
    r"""Validates task result content to avoid silent failures.
    It performs basic checks to ensure the content meets minimum
    quality standards.

    Args:
        content (str): The task result content to validate.
        task_id (str): Task ID for logging purposes.
            (default: :obj:`"unknown"`)
        min_length (int): Minimum content length after stripping whitespace.
            (default: :obj:`10`)

    Returns:
        bool: True if content passes validation, False otherwise.
    """
    # 1: Content must not be None
    if content is None:
        logger.warning(f"Task {task_id}: None content rejected")
        return False

    # 2: Content must not be empty after stripping whitespace
    stripped_content = content.strip()
    if not stripped_content:
        logger.warning(
            f"Task {task_id}: Empty or whitespace-only content rejected."
        )
        return False

    # 3: Content must meet minimum meaningful length
    if len(stripped_content) < min_length:
        logger.warning(
            f"Task {task_id}: Content too short ({len(stripped_content)} "
            f"chars < {min_length} minimum). Content preview: "
            f"'{stripped_content[:50]}...'"
        )
        return False

    # All validation checks passed
    logger.debug(
        f"Task {task_id}: Content validation passed "
        f"({len(stripped_content)} chars)"
    )
    return True
