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
import os
from abc import ABC, abstractmethod
from typing import Any, List

from camel.toolkits import ACIToolkit


class ToolSelector(ABC):
    r"""Abstract base class for all tool selectors.

    Subclasses must implement the [select_tools] method to provide
    different strategies for selecting tools based on task content.
    """

    @abstractmethod
    def select_tools(self, task_content: str) -> List[Any]:
        r"""
        Selects appropriate tools based on the given task content.

        Args:
            task_content (str): The description of the task that requires
            tools.

        Returns:
            List[Any]: A list of available tools.
        """
        pass


class ACIFunctionToolSelector(ToolSelector):
    r"""
    Tool selector using ACIToolkit to dynamically search functions based on
    task intent.
    """

    def __init__(self, linked_account_owner_id: str | None = None):
        self.aci_toolkit = ACIToolkit(
            linked_account_owner_id=linked_account_owner_id,
            api_key=os.getenv("ACI_API_KEY"),
        )

    def select_tools(self, task_content: str) -> list:
        r"""
        Searches for functions via ACI Toolkit based on the task intent.

        Args:
            task_content (str): Description of the task for function
            discovery.

        Returns:
            List[FunctionTool]: A list of matched function tools.
        """
        return self.aci_toolkit.get_tools()
