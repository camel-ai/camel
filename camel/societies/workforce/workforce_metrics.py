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
from abc import ABC, abstractmethod
from typing import Any, Dict


class WorkforceMetrics(ABC):
    r"""Abstract base class for collecting workforce metrics.

    Subclasses implement tracking of task-related data within a
    workforce and expose the collected metrics in different
    representations.
    """

    @abstractmethod
    def reset_task_data(self) -> None:
        r"""Reset all collected task data to its initial state."""
        pass

    @abstractmethod
    def dump_to_json(self, file_path: str) -> None:
        r"""Dump the collected metrics to a JSON file.

        Args:
            file_path (str): The path of the file to write the
                metrics to.
        """
        pass

    @abstractmethod
    def get_ascii_tree_representation(self) -> str:
        r"""Get an ASCII tree representation of the metrics.

        Returns:
            str: The ASCII tree representation of the collected
                metrics.
        """
        pass

    @abstractmethod
    def get_kpis(self) -> Dict[str, Any]:
        r"""Get the key performance indicators of the workforce.

        Returns:
            Dict[str, Any]: A dictionary mapping KPI names to their
                current values.
        """
        pass
