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

from typing import List

from camel.utils import AgentOpsMeta

from .openai_function import OpenAIFunction


class BaseToolkit(metaclass=AgentOpsMeta):
    def get_tools(self) -> List[OpenAIFunction]:
        raise NotImplementedError("Subclasses must implement this method.")

    def list_tools(self) -> List[str]:
        tools = self.get_tools()
        tool_names = [tool.func.__name__ for tool in tools]
        return tool_names

    def get_a_tool(self, func_name: str) -> List[OpenAIFunction]:
        tools = self.get_tools()
        for tool in tools:
            if tool.func.__name__ == func_name:
                return [tool]
        raise AttributeError(
            f"{func_name} is not a valid tool name or is not part of "
            f"{self.__class__.__name__}'s module."
        )
