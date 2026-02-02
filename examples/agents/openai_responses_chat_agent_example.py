# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
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
# ========= Copyright 2023-2026 @ CAMEL-AI.org. All Rights Reserved. =========
"""
This example demonstrates how to use the CAMEL ChatAgent with the OpenAI
Responses API model. It covers:

  1) Basic chat
  2) Structured output
  3) Streaming chat
  4) Tool calling
  5) Image analysis
  6) File analysis

Requirements:
  export OPENAI_API_KEY=sk-...
"""

from pydantic import BaseModel

from camel.agents import ChatAgent
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType, RoleType


def basic_chat():
    print("\n=== Basic Chat ===")
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a helpful assistant."
        ),
        model=model,
    )

    response = agent.step("Tell me a joke about camels.")
    print(response.msgs[0].content)


def structured_output_chat():
    print("\n=== Structured Output Chat ===")

    class CountryInfo(BaseModel):
        name: str
        capital: str
        population: int

    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You provide country info."
        ),
        model=model,
    )

    response = agent.step("France", response_format=CountryInfo)
    print(f"Structured Output: {response.msgs[0].parsed}")


def streaming_chat():
    print("\n=== Streaming Chat ===")
    # To enable streaming, we configure the model with stream=True
    # ChatAgent will consume the stream and return the final response.
    # To see the stream, we would need to use agent.step_stream (if it existed)
    # or rely on the fact that ChatAgent accumulates it.

    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES,
        ModelType.GPT_4_1_MINI,
        model_config_dict={"stream": True},
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a poet."
        ),
        model=model,
    )

    # This will block until completion, but internally it uses streaming
    response = agent.step("Write a short poem about the sunrise.")
    print(f"Streaming Result: {response.msgs[0].content}")


def tool_call_chat():
    print("\n=== Tool Call Chat ===")

    def add(a: int, b: int) -> int:
        """Adds two numbers."""
        return a + b

    tools = [FunctionTool(add)]

    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )

    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a math helper."
        ),
        model=model,
        tools=tools,
    )

    response = agent.step("What is 5 + 7?")

    print(f"Tool Call Result: {response.msgs[0].content}")
    print(f"Tool Calls: {response.info['tool_calls']}")


def image_analysis_chat():
    print("\n=== Image Analysis Chat ===")
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are an image analyst."
        ),
        model=model,
    )

    # Construct a message with image
    msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict={},
        content="What is in this image?",
        image_list=[
            {
                "url": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
                "detail": "auto",
            }
        ],
    )

    response = agent.step(msg)
    print(f"Image Analysis: {response.msgs[0].content}")


def file_analysis_chat():
    print("\n=== File Analysis Chat ===")
    model = ModelFactory.create(
        ModelPlatformType.OPENAI_RESPONSES, ModelType.GPT_4_1_MINI
    )
    agent = ChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="Assistant", content="You are a file analyst."
        ),
        model=model,
    )

    # Construct a message with file
    # We use the newly added file_list field in BaseMessage
    msg = BaseMessage(
        role_name="User",
        role_type=RoleType.USER,
        meta_dict={},
        content="What is in this file?",
        file_list=[
            {
                "file_url": "https://www.berkshirehathaway.com/letters/2024ltr.pdf"
            }
        ],
    )

    response = agent.step(msg)
    print(f"File Analysis: {response.msgs[0].content}")


if __name__ == "__main__":
    basic_chat()
    structured_output_chat()
    streaming_chat()
    tool_call_chat()
    image_analysis_chat()
    file_analysis_chat()


'''
=== Basic Chat ===
Sure! Here's a camel joke for you:

Why do camels make terrible secret agents?
Because they always let the hump out of the bag!

=== Structured Output Chat ===
Structured Output: name='France' capital='Paris' population=67081000

=== Streaming Chat ===
Streaming Result: Golden hues ignite the sky,
Whispers of dawn begin to fly.
Night retreats with gentle grace,
Sunrise paints a warm embrace.

=== Tool Call Chat ===
Tool Call Result: Yes, 5 + 7 equals 12. If you have any more math questions, feel free to ask!
Tool Calls: [ToolCallingRecord(tool_name='add', args={'a': 5, 'b': 7}, result=12, tool_call_id='call_z3DX7GyVj6sSYk7e6iEd3nVV', images=None)]

=== Image Analysis Chat ===
Image Analysis: This image shows the Google logo. The logo features the word "Google" written in a stylized font with the letters in different colors: blue for "G," red for the first "o," yellow for the second "o," blue for the "g," green for the "l," and red for the "e."

=== File Analysis Chat ===
File Analysis: This file is a detailed excerpt from the 2024 Berkshire Hathaway Inc. annual shareholder letter written by Warren E. Buffett, the company's Chairman of the Board. The letter covers a wide range of topics including:

1. **Introduction and Philosophy**:
   - Buffett explains the purpose of the annual letter, emphasizing transparency and honest communication with shareholders.
   - He acknowledges that Berkshire makes mistakes in business acquisitions and personnel decisions but also shares stories of success.

2. **Notable Tribute**:
   - A specific tribute to Pete Liegl, the founder of Forest River (an RV manufacturer acquired by Berkshire), highlighting his integrity, compensation agreement, and outstanding business performance.

3. **Company Performance**:
   - Summary of Berkshire’s financial performance in 2024, including operating earnings ($47.4 billion) and breakdowns by business segments (insurance underwriting, investment income, railroad, utilities, and other businesses).
   - Discussion about the growth and improvements in GEICO and the overall property-casualty insurance sector.
   - Commentary on challenges posed by climate change and natural disasters.

4. **Historical Context**:
   - Reflection on Berkshire’s 60-year transformation since Buffett took control, including record corporate income tax payments made to the U.S. Treasury ($26.8 billion in 2024).
   - Details on Berkshire’s investment strategy that emphasizes reinvestment over dividends for long-term growth.

5. **Investment Philosophy and Holdings**:
   - Berkshire’s dual strategy of owning controlling interest in many companies (generally 100%) and significant minority stakes in major public companies like Apple, American Express, and Coca-Cola.
   - The company’s preference for equities over cash or bonds, focusing on long-term value.

6. **Property-Casualty Insurance Business**:
   - Explanation of the unique challenges of the P/C insurance business model, where premiums are collected upfront but costs may be settled many years later.
   - The importance of prudent underwriting and risk management to avoid losses.
   - Description of Berkshire's capability to handle large insurance losses without dependence on reinsurers.

7. **International Investments**:
   - Information on Berkshire’s growing investments in five major Japanese trading companies, their shareholder-friendly practices, and plans for long-term involvement.
   - Commentary on currency risk management related to yen-denominated debt.

8. **Annual Meeting in Omaha**:
   - Invitation to shareholders for the annual meeting on May 3rd, 2025.
   - Details on event activities, merchandise, and featured book selling.
   - Personal notes including mention of Buffett’s sister and light-hearted commentary.

9. **Historical Performance Comparison**:
   - Comparative data showing Berkshire Hathaway’s annual percentage change in per-share market value against the S&P 500, spanning from 1965 to 2024.
   - Highlights Buffett's surpassed compound annual gain of 19.9% compared to the S&P 500’s 10.4% and extraordinary long-term gains of 5,502,284% vs. 39,054%.

**Summary:**
This document is a comprehensive, candid, and reflective communication from Warren Buffett about Berkshire Hathaway’s business performance, management philosophy, investment strategies, historical context, and future outlook, intended for the company’s shareholders. It combines financial data, storytelling, and personal insights characteristic of Berkshire Hathaway's annual shareholder letters.
'''  # noqa: E501, RUF001
