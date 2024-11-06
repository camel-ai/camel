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
from dataclasses import dataclass
from typing import Any, Dict, Optional

from camel.messages import (
    BaseMessage,
    OpenAIAssistantMessage,
    OpenAIFunctionMessage,
    OpenAIMessage,
)
from camel.messages.axolotl.sharegpt.functions.function_call_formatter import (
    FunctionCallFormatter,
)
from camel.messages.axolotl.sharegpt.functions.hermes.hermes_function_formatter import (
    HermesFunctionFormatter,
)
from camel.messages.axolotl.sharegpt.sharegpt_message import ShareGPTMessage
from camel.types import OpenAIBackendRole


@dataclass
class FunctionCallingMessage(BaseMessage):
    r"""Class for message objects used specifically for
    function-related messages.

    Args:
        func_name (Optional[str]): The name of the function used.
            (default: :obj:`None`)
        args (Optional[Dict]): The dictionary of arguments passed to the
            function. (default: :obj:`None`)
        result (Optional[Any]): The result of function execution.
            (default: :obj:`None`)
    """

    func_name: Optional[str] = None
    args: Optional[Dict] = None
    result: Optional[Any] = None

    def to_openai_message(
        self,
        role_at_backend: OpenAIBackendRole,
    ) -> OpenAIMessage:
        r"""Converts the message to an :obj:`OpenAIMessage` object.

        Args:
            role_at_backend (OpenAIBackendRole): The role of the message in
                OpenAI chat system.

        Returns:
            OpenAIMessage: The converted :obj:`OpenAIMessage` object.
        """
        if role_at_backend == OpenAIBackendRole.ASSISTANT:
            return self.to_openai_assistant_message()
        elif role_at_backend == OpenAIBackendRole.FUNCTION:
            return self.to_openai_function_message()
        else:
            raise ValueError(f"Unsupported role: {role_at_backend}.")

    def to_sharegpt(
        self,
        function_format: FunctionCallFormatter = HermesFunctionFormatter(),
    ) -> ShareGPTMessage:
        """Convert FunctionCallingMessage to ShareGPT message"""
        # The role of the message is an unreliable indicator of whether it is a function call or response, so use result
        if self.result is None:
            # This is a function call
            content = function_format.format_tool_call(
                self.content or "",
                self.func_name,
                self.args,
            )
            return ShareGPTMessage(from_="gpt", value=content)
        else:
            # This is a function response
            # TODO: Allow for more flexible setting of tool role, optionally to be the same as assistant messages
            content = function_format.format_tool_response(
                self.func_name,
                self.result,
            )
            return ShareGPTMessage(from_="tool", value=content)

    def to_openai_assistant_message(self) -> OpenAIAssistantMessage:
        r"""Converts the message to an :obj:`OpenAIAssistantMessage` object.

        Returns:
            OpenAIAssistantMessage: The converted :obj:`OpenAIAssistantMessage`
                object.
        """
        if (not self.func_name) or (self.args is None):
            raise ValueError(
                "Invalid request for converting into assistant message"
                " due to missing function name or arguments."
            )

        msg_dict: OpenAIAssistantMessage = {
            "role": "assistant",
            "content": self.content,
            "function_call": {
                "name": self.func_name,
                "arguments": str(self.args),
            },
        }

        return msg_dict

    def to_openai_function_message(self) -> OpenAIFunctionMessage:
        r"""Converts the message to an :obj:`OpenAIMessage` object
        with the role being "function".

        Returns:
            OpenAIMessage: The converted :obj:`OpenAIMessage` object
                with its role being "function".
        """
        if not self.func_name:
            raise ValueError(
                "Invalid request for converting into function message"
                " due to missing function name."
            )

        result_content = {"result": {str(self.result)}}
        msg_dict: OpenAIFunctionMessage = {
            "role": "function",
            "name": self.func_name,
            "content": f'{result_content}',
        }

        return msg_dict
