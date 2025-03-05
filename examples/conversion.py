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
from typing import List

from camel.data_schemas import (
    ShareGPTData,
    ShareGPTMessage,
)
from camel.messages import BaseMessage, HermesFunctionFormatter
from camel.messages.func_message import FunctionCallingMessage


def sharegpt_to_camel_messages(
    conversation: ShareGPTData,
) -> List[BaseMessage]:
    r"""Convert ShareGPT conversation to a list of CAMEL messages.

    This function processes a ShareGPTData conversation and converts it into
    a list of BaseMessage objects formatted using HermesFunctionFormatter.
    If a system message exists, it is included as the first element in the
    list.

    Args:
        conversation (ShareGPTData): The structured conversation data
        containing an optional system message and a list of
        conversation messages.

    Returns:
        List[BaseMessage]: A list of messages converted into CAMEL's
        BaseMessage format.
    """
    messages = []

    if conversation.system:
        messages.append(
            BaseMessage.make_user_message(
                role_name="system", content=conversation.system
            )
        )

    messages.extend(
        BaseMessage.from_sharegpt(msg, HermesFunctionFormatter())
        for msg in conversation.conversations
    )

    return messages


def camel_messages_to_sharegpt(
    messages: List[BaseMessage],
) -> ShareGPTData:
    r"""Convert a list of CAMEL messages to a ShareGPTData conversation.

    This function processes a list of BaseMessage objects and converts them
    into a structured ShareGPTData conversation. If the first message is a
    system message, it is stored in the system field, while the remaining
    messages are placed in the conversations field.

    Args:
        messages (List[BaseMessage]): A list of messages in CAMEL format.

    Returns:
        ShareGPTData: A structured ShareGPTData conversation.
    """
    if messages and messages[0].role_name == "system":
        system_message = messages[0].content
        conversation_messages = messages[1:]
    else:
        system_message = None
        conversation_messages = messages

    sharegpt_messages = []
    tools_set = set()
    # function_formatter = HermesFunctionFormatter()

    for msg in conversation_messages:
        sharegpt_msg = msg.to_sharegpt()
        sharegpt_messages.append(sharegpt_msg)

        # For function/tool calls, track the tool information in tool_set
        if isinstance(msg, FunctionCallingMessage) and msg.result is None:
            tools_set.add(
                json.dumps(
                    {"name": msg.func_name, "arguments": list(msg.args.keys())}
                )
            )

    tools_list = list(tools_set)
    tools_json = f"[{', '.join(tools_list)}]" if tools_list else None

    return ShareGPTData(
        system=system_message,
        conversations=sharegpt_messages,
        tools=tools_json,
    )


# Example usage
if __name__ == "__main__":
    # Create a sample ShareGPT conversation
    sharegpt_conv = ShareGPTData(
        system="You are a helpful assistant.",
        conversations=[
            ShareGPTMessage(from_="human", value="What's Tesla's P/E ratio?"),
            ShareGPTMessage(
                from_="function_call",
                value="Let me check Tesla's stock fundamentals.\n"
                "<tool_call>\n{'name': 'get_stock_fundamentals',"
                " 'arguments': {'symbol': 'TSLA'}}\n</tool_call>",
            ),
            ShareGPTMessage(
                from_="observation",
                value='''<tool_response>
    {"name": "get_stock_fundamentals", "content": 
    {"symbol": "TSLA", "company_name": "Tesla, Inc.", 
    "sector": "Consumer Cyclical", "pe_ratio": 49.604652}}
    </tool_response>''',
            ),
            ShareGPTMessage(
                from_="gpt",
                value="Tesla (TSLA) currently has a P/E ratio of 49.60.",
            ),
        ],
        tools='[{"name": "get_stock_fundamentals", "arguments": ["symbol"]}]',
    )

    # Convert to CAMEL messages
    camel_messages = sharegpt_to_camel_messages(sharegpt_conv)

    print("\nCAMEL Messages:")
    for msg in camel_messages:
        print(f"Role: {msg.role_name}")
        print(f"Content: {msg.content}")
        if isinstance(msg, FunctionCallingMessage):
            print(f"Function Name: {msg.func_name}")
            if msg.args:
                print(f"Arguments: {msg.args}")
            if msg.result:
                print(f"Result: {msg.result}")
        print()

    # Convert back to ShareGPT
    converted_back = camel_messages_to_sharegpt(camel_messages)
    print("\nConverted back to ShareGPT:")
    print(f"System: {converted_back.system}")
    print(f"Tools: {converted_back.tools}")
    print()
    print("Conversation messages as ShareGPTMessages:")
    for msg in converted_back.conversations:
        print(f"From: {msg.from_}")
        print(f"Value: {msg.value}")
        print()

"""
CAMEL Messages:
Role: system
Content: You are a helpful assistant.

Role: user
Content: What's Tesla's P/E ratio?

Role: assistant
Content: Let me check Tesla's stock fundamentals.
Function Name: get_stock_fundamentals
Arguments: {'symbol': 'TSLA'}

Role: assistant
Content: 
Function Name: get_stock_fundamentals
Result: {'symbol': 'TSLA', 'company_name': 'Tesla, Inc.', 'sector': 
'Consumer Cyclical', 'pe_ratio': 49.604652}

Role: assistant
Content: Tesla (TSLA) currently has a P/E ratio of 49.60.


Converted back to ShareGPT:
System: You are a helpful assistant.
Tools: [{"name": "get_stock_fundamentals", "arguments": ["symbol"]}]

Conversation messages as ShareGPTMessages:
From: human
Value: What's Tesla's P/E ratio?

From: function_call
Value: Let me check Tesla's stock fundamentals.
<tool_call>
{'name': 'get_stock_fundamentals', 'arguments': {'symbol': 'TSLA'}}
</tool_call>

From: observation
Value: <tool_response>
{'name': 'get_stock_fundamentals', 'content': {'symbol': 'TSLA', 'company_name'
: 'Tesla, Inc.', 'sector': 'Consumer Cyclical', 'pe_ratio': 49.604652}}
</tool_response>

From: gpt
Value: Tesla (TSLA) currently has a P/E ratio of 49.60.
"""
