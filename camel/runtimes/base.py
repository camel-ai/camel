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
from abc import ABC, abstractmethod
from typing import Any, List, Union

from camel.toolkits import FunctionTool


class BaseRuntime(ABC):
    r"""An abstract base class for all CAMEL runtimes."""

    def __init__(self):
        super().__init__()

        self.tools_map = dict()

    @abstractmethod
    def add(
        self,
        funcs: Union[FunctionTool, List[FunctionTool]],
        *args: Any,
        **kwargs: Any,
    ) -> "BaseRuntime":
        r"""Adds a new tool to the runtime."""
        pass

    @abstractmethod
    def reset(self, *args: Any, **kwargs: Any) -> Any:
        r"""Resets the runtime to its initial state."""
        pass

    def get_tools(self) -> List[FunctionTool]:
        r"""Returns a list of all tools in the runtime."""
        return list(self.tools_map.values())
