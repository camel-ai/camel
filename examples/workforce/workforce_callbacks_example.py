# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
"""
Example: Subscribe to callbacks in Workforce

Includes:
- Custom callback `PrintCallback` that logs key lifecycle events.
- Subscribe callbacks via the `callbacks` parameter when constructing a
  `Workforce`.
"""

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.logger import get_logger
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.societies.workforce import FailureHandlingConfig
from camel.societies.workforce.events import (
    AllTasksCompletedEvent,
    LogEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDecomposedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    TaskUpdatedEvent,
    WorkerCreatedEvent,
    WorkerDeletedEvent,
)
from camel.societies.workforce.workforce import Workforce
from camel.societies.workforce.workforce_callback import WorkforceCallback
from camel.societies.workforce.workforce_logger import WorkforceLogger
from camel.tasks import Task
from camel.types import ModelPlatformType, ModelType

logger = get_logger(__name__)


class PrintCallback(WorkforceCallback):
    r"""Simple callback printing events to logs to observe ordering."""

    def log_message(self, event: LogEvent) -> None:
        print(
            f"[PrintCallback] {event.message} level={event.level}, "
            f"color={event.color}"
        )

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

    def log_task_updated(self, event: TaskUpdatedEvent) -> None:
        print(
            f"[PrintCallback] task_updated: task={event.task_id}, "
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


def main() -> None:
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
        model_config_dict=ChatGPTConfig(stream=True).as_dict(),
    )

    search_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Research Specialist",
            content="You are a research specialist who excels at finding and "
            "gathering information from the web.",
        ),
        model=model,
    )

    analyst_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Business Analyst",
            content="You are an expert business analyst. Your job is "
            "to analyze research findings, identify key insights, "
            "opportunities, and challenges.",
        ),
        model=model,
    )

    writer_agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Report Writer",
            content="You are a professional report writer. You take "
            "analytical insights and synthesize them into a clear, "
            "concise, and well-structured final report.",
        ),
        model=model,
    )

    workforce = Workforce(
        "Workforce Callbacks Demo",
        callbacks=[WorkforceLogger('demo-logger'), PrintCallback()],
        use_structured_output_handler=True,
        failure_handling_config=FailureHandlingConfig(enabled_strategies=[]),
        default_model=model,
    )

    workforce.add_single_agent_worker(
        "A researcher who can search online for information.",
        worker=search_agent,
    ).add_single_agent_worker(
        "An analyst who can process research findings.", worker=analyst_agent
    ).add_single_agent_worker(
        "A writer who can create a final report from the analysis.",
        worker=writer_agent,
    )

    # Use a simpler task to ensure fast and deterministic execution
    human_task = Task(
        content=(
            "Create a simple report about electric scooters. "
            "The report should have three sections: "
            "1. Market overview "
            "2. Target customers "
            "3. Summary"
        ),
        id='0',
    )

    workforce.process_task(human_task)

    # Read KPIs and a simple "tree"
    print(f"KPIs: {workforce.get_workforce_kpis()}")
    print(f"Tree: {workforce.get_workforce_log_tree()}")


if __name__ == "__main__":
    main()
