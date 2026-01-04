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
from __future__ import annotations

import typing
from abc import ABC, abstractmethod

from colorama import Fore

from .events import (
    AllTasksCompletedEvent,
    LogEvent,
    TaskAssignedEvent,
    TaskCompletedEvent,
    TaskCreatedEvent,
    TaskDecomposedEvent,
    TaskFailedEvent,
    TaskStartedEvent,
    WorkerCreatedEvent,
    WorkerDeletedEvent,
)


class WorkforceCallback(ABC):
    r"""Interface for recording workforce lifecycle events.

    Implementations should persist or stream events as appropriate.
    """

    __COLOR_MAP: typing.ClassVar = {
        "yellow": Fore.YELLOW,
        "red": Fore.RED,
        "green": Fore.GREEN,
        "blue": Fore.BLUE,
        "cyan": Fore.CYAN,
        "magenta": Fore.MAGENTA,
        "gray": Fore.LIGHTBLACK_EX,
        "black": Fore.BLACK,
    }

    def _get_color_message(self, event: LogEvent) -> str:
        r"""Gets a colored message for a log event."""
        if event.color is None or event.color not in self.__COLOR_MAP:
            return event.message
        color = self.__COLOR_MAP.get(event.color)
        return f"{color}{event.message}{Fore.RESET}"

    @abstractmethod
    def log_message(
        self,
        event: LogEvent,
    ) -> None:
        pass

    @abstractmethod
    def log_task_created(
        self,
        event: TaskCreatedEvent,
    ) -> None:
        pass

    @abstractmethod
    def log_task_decomposed(self, event: TaskDecomposedEvent) -> None:
        pass

    @abstractmethod
    def log_task_assigned(self, event: TaskAssignedEvent) -> None:
        pass

    @abstractmethod
    def log_task_started(self, event: TaskStartedEvent) -> None:
        pass

    @abstractmethod
    def log_task_completed(self, event: TaskCompletedEvent) -> None:
        pass

    @abstractmethod
    def log_task_failed(self, event: TaskFailedEvent) -> None:
        pass

    @abstractmethod
    def log_worker_created(self, event: WorkerCreatedEvent) -> None:
        pass

    @abstractmethod
    def log_worker_deleted(self, event: WorkerDeletedEvent) -> None:
        pass

    @abstractmethod
    def log_all_tasks_completed(self, event: AllTasksCompletedEvent) -> None:
        pass
