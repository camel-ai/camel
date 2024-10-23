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
from typing import Any, Dict, List, Optional

from camel.messages.axolotl.sharegpt.functions.function_call_formatter import (
    FunctionCallFormatter,
)
from camel.messages.axolotl.sharegpt.functions.hermes.hermes_tool_call import (
    HermesToolCall,
)
from camel.messages.axolotl.sharegpt.functions.hermes.hermes_tool_response import (
    ToolResponse,
)


class HermesFunctionFormatter(FunctionCallFormatter):
    """Hermes-style function calling format implementation with validation"""

    def extract_tool_calls(self, message: str) -> List[HermesToolCall]:
        tool_calls = []
        pattern = r"<tool_call>\s*({.*?})\s*</tool_call>"
        matches = re.finditer(pattern, message, re.DOTALL)

        for match in matches:
            try:
                call_dict = json.loads(match.group(1).replace("'", '"'))
                tool_calls.append(HermesToolCall.model_validate(call_dict))
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

    def format_tool_call(
        self, content: str, func_name: str, args: Dict[str, Any]
    ) -> str:
        tool_call_dict = {"name": func_name, "arguments": args}
        return f"{content}\n<tool_call>\n{tool_call_dict}\n</tool_call>"

    def format_tool_response(self, func_name: str, result: Any) -> str:
        response_dict = {"name": func_name, "content": result}
        return f"<tool_response>\n{response_dict}\n</tool_response>"
