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
from camel.messages.axolotl.sharegpt.conversion import (
    openai_to_sharegpt,
    sharegpt_to_openai,
)
from camel.messages.axolotl.sharegpt.sharegpt_conversation import (
    ShareGPTConversation,
)
from camel.messages.axolotl.sharegpt.sharegpt_message import ShareGPTMessage

if __name__ == "__main__":
    sharegpt_conv = ShareGPTConversation.model_validate(
        [
            ShareGPTMessage(
                from_="system", value="You are a helpful assistant."
            ),
            ShareGPTMessage(from_="human", value="What's Tesla's P/E ratio?"),
            ShareGPTMessage(
                from_="assistant",
                value="Let me check Tesla's stock fundamentals.\n<tool_call>\n{'name': 'get_stock_fundamentals', 'arguments': {'symbol': 'TSLA'}}\n</tool_call>",
            ),
            ShareGPTMessage(
                from_="tool",
                value='''<tool_response>
{"name": "get_stock_fundamentals", "content": {"symbol": "TSLA", "company_name": "Tesla, Inc.", "sector": "Consumer Cyclical", "pe_ratio": 49.604652}}
</tool_response>''',
            ),
            ShareGPTMessage(
                from_="assistant",
                value="Tesla (TSLA) currently has a P/E ratio of 49.60.",
            ),
        ]
    )

    # Using default Hermes format
    openai_messages = sharegpt_to_openai(sharegpt_conv)
    print("OpenAI format:", openai_messages)

    # Convert back to ShareGPT format
    converted_back = openai_to_sharegpt(openai_messages)
    print(
        "\nConverted back to ShareGPT format:",
        converted_back.model_dump_json(indent=2, by_alias=True),
    )
