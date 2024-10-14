# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========
# Licensed under the Apache License, Version 2.0 (the “License”);
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an “AS IS” BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =========== Copyright 2023 @ CAMEL-AI.org. All Rights Reserved. ===========

import inspect
from typing import List

from camel.utils import AgentOpsMeta

from .function_tool import FunctionTool


class BaseToolkit(metaclass=AgentOpsMeta):
    def get_tools(self) -> List[FunctionTool]:
        """Returns a list of FunctionTool objects representing the
        functions in the toolkit.

        Returns:
            List[FunctionTool]: A list of FunctionTool objects
                representing the functions in the toolkit.
        """
        tools = []
        for _, method in inspect.getmembers(self, predicate=inspect.ismethod):
            if getattr(method, '_is_exported', False):
                tools.append(
                    FunctionTool(
                        func=method, name_prefix=self.__class__.__name__
                    )
                )

        if not tools:
            raise NotImplementedError("Subclasses must implement the methods")

        return tools
