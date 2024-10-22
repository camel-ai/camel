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
import json
import re
from typing import List, Optional

from camel.messages.axolotl.function_call_format import FunctionCallFormat
from camel.messages.axolotl.tool_call import ToolCall
from camel.messages.axolotl.tool_response import ToolResponse


class HermesFunctionFormat(FunctionCallFormat):
    """Hermes-style function calling format implementation with validation"""

    def extract_tool_calls(self, message: str) -> List[ToolCall]:
        tool_calls = []
        pattern = r"<tool_call>\s*({.*?})\s*</tool_call>"
        matches = re.finditer(pattern, message, re.DOTALL)

        for match in matches:
            try:
                call_dict = json.loads(match.group(1).replace("'", '"'))
                tool_calls.append(ToolCall.model_validate(call_dict))
            except Exception as e:
                print(f"Warning: Failed to parse tool call: {e}")
                continue

        return tool_calls

    def extract_tool_response(self, message: str) -> Optional[ToolResponse]:
        pattern = r"<tool_response>\s*({.*?})\s*</tool_response>"
        match = re.search(pattern, message, re.DOTALL)

        if match:
            try:
                response_dict = json.loads(match.group(1).replace("'", '"'))
                return ToolResponse.model_validate(response_dict)
            except Exception as e:
                print(f"Warning: Failed to parse tool response: {e}")
                return None
        return None

    def format_tool_call(self, content: str, tool_call: ToolCall) -> str:
        tool_call_dict = tool_call.model_dump()
        return f"{content}\n<tool_call>\n{json.dumps(tool_call_dict, indent=2)}\n</tool_call>"

    def format_tool_response(self, tool_response: ToolResponse) -> str:
        response_dict = tool_response.model_dump()
        return f"<tool_response>\n{json.dumps(response_dict, indent=2)}\n</tool_response>"
