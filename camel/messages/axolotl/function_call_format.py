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
from abc import ABC, abstractmethod
from typing import List, Optional

from camel.messages.axolotl.tool_call import ToolCall
from camel.messages.axolotl.tool_response import ToolResponse


class FunctionCallFormat(ABC):
    """Abstract base class for function calling formats"""

    @abstractmethod
    def extract_tool_calls(self, message: str) -> List[ToolCall]:
        pass

    @abstractmethod
    def extract_tool_response(self, message: str) -> Optional[ToolResponse]:
        pass

    @abstractmethod
    def format_tool_call(self, content: str, tool_call: ToolCall) -> str:
        pass

    @abstractmethod
    def format_tool_response(self, tool_response: ToolResponse) -> str:
        pass
