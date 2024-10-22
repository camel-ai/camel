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
from typing import List

from camel.messages import OpenAIMessage
from camel.messages.axolotl.function_call_format import FunctionCallFormat
from camel.messages.axolotl.hermes_function_format import HermesFunctionFormat
from camel.messages.axolotl.sharegpt.sharegpt_conversation import (
    ShareGPTConversation,
)
from camel.messages.axolotl.sharegpt.sharegpt_message import ShareGPTMessage
from camel.messages.axolotl.tool_call import ToolCall
from camel.messages.axolotl.tool_response import ToolResponse


def openai_to_sharegpt(
    messages: List[OpenAIMessage],
    function_format: FunctionCallFormat = HermesFunctionFormat(),
) -> ShareGPTConversation:
    """Convert OpenAI message format to ShareGPT format with validation"""
    try:
        sharegpt_messages = []

        for msg in messages:
            if msg["role"] == "system":
                sharegpt_messages.append(
                    ShareGPTMessage(from_="system", value=msg["content"])
                )
            elif msg["role"] == "user":
                sharegpt_messages.append(
                    ShareGPTMessage(from_="human", value=msg["content"])
                )
            elif msg["role"] == "assistant":
                content = msg["content"] or ""
                if msg.get("function_call"):
                    tool_call = ToolCall(
                        name=msg["function_call"]["name"],
                        arguments=json.loads(
                            msg["function_call"]["arguments"]
                        ),
                    )
                    content = function_format.format_tool_call(
                        content, tool_call
                    )
                sharegpt_messages.append(
                    ShareGPTMessage(from_="assistant", value=content)
                )
            elif msg["role"] == "function":
                tool_response = ToolResponse(
                    name=msg.get("name", "unknown"),
                    content=json.loads(msg["content"])
                    if isinstance(msg["content"], str)
                    else msg["content"],
                )
                value = function_format.format_tool_response(tool_response)
                sharegpt_messages.append(
                    ShareGPTMessage(from_="tool", value=value)
                )

        return ShareGPTConversation.model_validate(sharegpt_messages)
    except Exception as e:
        raise ValueError(
            f"Failed to convert OpenAI messages to ShareGPT format: {e!s}"
        )


def sharegpt_to_openai(
    conversation: ShareGPTConversation,
    function_format: FunctionCallFormat = HermesFunctionFormat(),
) -> List[OpenAIMessage]:
    """Convert ShareGPT format to OpenAI message format with validation"""
    try:
        openai_messages: List[OpenAIMessage] = []

        for msg in conversation:
            if msg.from_ == "system":
                openai_messages.append(
                    {"role": "system", "content": msg.value}
                )
            elif msg.from_ == "human":
                openai_messages.append({"role": "user", "content": msg.value})
            elif msg.from_ == "assistant":
                message: OpenAIMessage = {
                    "role": "assistant",
                    "content": msg.value,
                }

                tool_calls = function_format.extract_tool_calls(msg.value)
                if tool_calls:
                    message["content"] = re.sub(
                        r"<tool_call>.*?</tool_call>",
                        "",
                        msg.value,
                        flags=re.DOTALL,
                    ).strip()
                    message["function_call"] = {
                        "name": tool_calls[0].name,
                        "arguments": json.dumps(tool_calls[0].arguments),
                    }

                openai_messages.append(message)
            elif msg.from_ == "tool":
                tool_response = function_format.extract_tool_response(
                    msg.value
                )
                if tool_response:
                    openai_messages.append(
                        {
                            "role": "function",
                            "name": tool_response.name,
                            "content": json.dumps(tool_response.content),
                        }
                    )

        return openai_messages
    except Exception as e:
        raise ValueError(
            f"Failed to convert ShareGPT conversation to OpenAI format: {e!s}"
        )
