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
from typing import Any, Dict, Optional

from camel.logger import get_logger
from camel.societies.workforce.workforce_logger import WorkforceLogger

logger = get_logger(__name__)


class WorkforceLoggerWrapper:
    r"""A wrapper class for workforce logging functionality."""

    def __init__(self, metrics_logger: Optional[WorkforceLogger] = None):
        r"""Initialize the WorkforceLoggerWrapper.

        Args:
            metrics_logger (Optional[WorkforceLogger]): The metrics logger
                instance.
        """
        self.metrics_logger = metrics_logger

    def get_workforce_logs(self) -> Dict[str, Any]:
        r"""Returns all workforce logs.

        Returns:
            Dict[str, Any]: Dictionary containing all workforce logs.
        """
        if not self.metrics_logger:
            return {"error": "Logger not initialized."}
        return {"log_entries": self.metrics_logger.log_entries}

    def get_workforce_log_tree(self) -> str:
        r"""Returns an ASCII tree representation of the task hierarchy and
        worker status.

        Returns:
            str: ASCII tree representation of the workforce state.
        """
        if not self.metrics_logger:
            return "Logger not initialized."
        return self.metrics_logger.get_ascii_tree_representation()

    def get_workforce_kpis(self) -> Dict[str, Any]:
        r"""Returns a dictionary of key performance indicators.

        Returns:
            Dict[str, Any]: Dictionary containing KPIs for the workforce.
        """
        if not self.metrics_logger:
            return {"error": "Logger not initialized."}
        return self.metrics_logger.get_kpis()

    def dump_workforce_logs(self, file_path: str) -> None:
        r"""Dumps all collected logs to a JSON file.

        Args:
            file_path (str): The path to the JSON file.
        """
        if not self.metrics_logger:
            print("Logger not initialized. Cannot dump logs.")
            return
        self.metrics_logger.dump_to_json(file_path)
        logger.info(f"Workforce logs dumped to {file_path}")
