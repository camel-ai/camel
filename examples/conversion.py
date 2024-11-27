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
from typing import List

from camel.messages import BaseMessage, HermesFunctionFormatter
from camel.messages.conversion import (
    ShareGPTConversation,
    ShareGPTMessage,
)
from camel.messages.func_message import FunctionCallingMessage


def sharegpt_to_camel_messages(
    conversation: ShareGPTConversation,
) -> List[BaseMessage]:
    r"""Convert ShareGPT conversation to list of CAMEL messages"""
    return [
        BaseMessage.from_sharegpt(msg, HermesFunctionFormatter())
        for msg in conversation
    ]


def camel_messages_to_sharegpt(
    messages: List[BaseMessage],
) -> ShareGPTConversation:
    r"""Convert list of CAMEL messages to ShareGPT conversation"""
    sharegpt_messages = [
        msg.to_sharegpt(HermesFunctionFormatter()) for msg in messages
    ]
    return ShareGPTConversation.model_validate(sharegpt_messages)


# Example usage
if __name__ == "__main__":
    # Create a sample ShareGPT conversation
    sharegpt_conv = ShareGPTConversation.model_validate(
        [
            ShareGPTMessage(
                from_="system", value="You are a helpful assistant."
            ),
            ShareGPTMessage(from_="human", value="What's Tesla's P/E ratio?"),
            ShareGPTMessage(
                from_="gpt",
                value="Let me check Tesla's stock fundamentals.\n"
                "<tool_call>\n{'name': 'get_stock_fundamentals',"
                " 'arguments': {'symbol': 'TSLA'}}\n</tool_call>",
            ),
            ShareGPTMessage(
                from_="tool",
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
        ]
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
    for msg in converted_back:
        print(f"From: {msg.from_}")
        print(f"Value: {msg.value}")
        print()
