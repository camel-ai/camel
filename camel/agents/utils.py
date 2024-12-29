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
import json
import logging
import re
import textwrap
import uuid
from typing import Any, Dict, List, Optional

from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)

logger = logging.getLogger(__name__)


def generate_tool_prompt(tool_schema_list: List[Dict[str, Any]]) -> str:
    r"""Generates a tool prompt based on the provided tool schema list.

    Returns:
        str: A string representing the tool prompt.
    """
    tool_prompts = []

    for tool in tool_schema_list:
        tool_info = tool["function"]
        tool_name = tool_info["name"]
        tool_description = tool_info["description"]
        tool_json = json.dumps(tool_info, indent=4)

        prompt = (
            f"Use the function '{tool_name}' to '{tool_description}':\n"
            f"{tool_json}\n"
        )
        tool_prompts.append(prompt)

    tool_prompt_str = "\n".join(tool_prompts)

    final_prompt = textwrap.dedent(
        f"""\
        You have access to the following functions:

        {tool_prompt_str}

        If you choose to call a function ONLY reply in the following format with no prefix or suffix:

        <function=example_function_name>{{"example_name": "example_value"}}</function>

        Reminder:
        - Function calls MUST follow the specified format, start with <function= and end with </function>
        - Required parameters MUST be specified
        - Only call one function at a time
        - Put the entire function call reply on one line
        - If there is no function call available, answer the question like normal with your current knowledge and do not tell the user about function calls.
        """  # noqa: E501
    )
    return final_prompt


def _parse_tool_response(response: str) -> Optional[Dict[str, Any]]:
    r"""Parses the tool response to extract the function name and
    arguments.

    Args:
        response (str): The response from the model containing the
            function call.

    Returns:
        Optional[Dict[str, Any]]: The parsed function name and arguments
            if found, otherwise :obj:`None`.
    """
    function_regex = r"<function=(\w+)>(.*?)</function>"
    match = re.search(function_regex, response)

    if match:
        function_name, args_string = match.groups()
        try:
            args = json.loads(args_string)
            return {"function": function_name, "arguments": args}
        except json.JSONDecodeError as error:
            logger.error(f"Error parsing function arguments: {error}")
            return None
    return None


def extract_tool_call(
    self, response: Any
) -> Optional[ChatCompletionMessageToolCall]:
    r"""Extract the tool call from the model response, if present.

    Args:
        response (Any): The model's response object.

    Returns:
        Optional[ChatCompletionMessageToolCall]: The parsed tool call if
            present, otherwise None.
    """
    # Check if the response contains tool calls
    if (
        self.has_tools
        and not self.model_type.support_native_tool_calling
        and "</function>" in response.choices[0].message.content
    ):
        parsed_content = _parse_tool_response(
            response.choices[0].message.content
        )
        if parsed_content:
            return ChatCompletionMessageToolCall(
                id=str(uuid.uuid4()),
                function=Function(
                    arguments=str(parsed_content["arguments"]).replace(
                        "'", '"'
                    ),
                    name=str(parsed_content["function"]),
                ),
                type="function",
            )
    elif (
        self.has_tools
        and self.model_type.support_native_tool_calling
        and response.choices[0].message.tool_calls
    ):
        return response.choices[0].message.tool_calls[0]

    # No tool call found
    return None
