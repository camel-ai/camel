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
"""
Example: Subscribe to callbacks in Workforce

Includes:
- Custom callback `PrintCallback` that logs key lifecycle events.
- Subscribe callbacks via the `callbacks` parameter when constructing a
  `Workforce`.
"""

import asyncio

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.societies.workforce.events import (
    AllTasksCompletedEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDecomposedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    WorkerCreatedEvent,
    WorkerDeletedEvent,
)
from camel.societies.workforce.workforce import Workforce
from camel.societies.workforce.workforce_callback import WorkforceCallback
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


class PrintCallback(WorkforceCallback):
    r"""Simple callback printing events to logs to observe ordering."""

    def log_task_created(self, event: TaskCreatedEvent) -> None:
        print(
            f"[PrintCallback] task_created: id={event.task_id}, "
            f"desc={event.description!r}, parent={event.parent_task_id}"
        )

    def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        print(
            f"[PrintCallback] task_decomposed: parent={event.parent_task_id},"
            f" subtasks={event.subtask_ids}"
        )

    def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        print(
            f"[PrintCallback] task_assigned: task={event.task_id}, "
            f"worker={event.worker_id}"
        )

    def log_task_started(self, event: TaskStartedEvent) -> None:
        print(
            f"[PrintCallback] task_started: task={event.task_id}, "
            f"worker={event.worker_id}"
        )

    def log_task_completed(self, event: TaskCompletedEvent) -> None:
        print(
            f"[PrintCallback] task_completed: task={event.task_id}, "
            f"worker={event.worker_id}, took={event.processing_time_seconds}s"
        )

    def log_task_failed(self, event: TaskFailedEvent) -> None:
        logger.warning(
            f"[PrintCallback] task_failed: task={event.task_id}, "
            f"err={event.error_message}"
        )

    def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        print(
            f"[PrintCallback] worker_created: id={event.worker_id}, "
            f"type={event.worker_type}, role={event.role}"
        )

    def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        print(
            f"[PrintCallback] worker_deleted: id={event.worker_id}, "
            f"reason={event.reason}"
        )

    def log_all_tasks_completed(self, event: AllTasksCompletedEvent) -> None:
        print("[PrintCallback] all_tasks_completed")


def build_teacher_agent() -> ChatAgent:
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )
    return ChatAgent(system_message="You are a teacher", model=model)


def build_student_agent() -> ChatAgent:
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )
    return ChatAgent(system_message="You are a student", model=model)


async def run_demo() -> None:
    callbacks = [PrintCallback()]

    workforce = Workforce(
        "Workforce Callbacks Demo",
        callbacks=callbacks,
        use_structured_output_handler=True,
    )

    teacher = build_teacher_agent()
    student = build_student_agent()
    workforce.add_single_agent_worker("Teacher Worker", teacher)
    workforce.add_single_agent_worker("Student Worker", student)
    workforce.add_main_task(
        "The teacher set an exam question and had the students answer it."
    )

    # Start Workforce and wait for completion (timeout to avoid hanging)
    wf_task = asyncio.create_task(workforce.start())
    try:
        await asyncio.wait_for(wf_task, timeout=30.0)
    except asyncio.TimeoutError:
        logger.warning("Workforce run timed out; stopping...")
        workforce.stop()

    # Read KPIs and a simple "tree"
    print(f"KPIs: {workforce.get_workforce_kpis()}")
    print(f"Tree: {workforce.get_workforce_log_tree()}")


if __name__ == "__main__":
    asyncio.run(run_demo())
