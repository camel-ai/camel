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
import asyncio
import logging
import time

from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.logger import get_logger
from camel.models import ModelFactory
from camel.toolkits import FunctionTool
from camel.types import ModelPlatformType, ModelType

# Set up logging to see debug info from chat agent
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = get_logger(__name__)

# Also set the camel chat agent logger to INFO level to see tool execution logs
chat_agent_logger = get_logger('camel.agents.chat_agent')
chat_agent_logger.setLevel(logging.INFO)

# Create a streaming model
streaming_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict={
        "stream": True,
    },
)


# Define structured output model
class Thinking(BaseModel):
    think: str = Field(description="Your thinking process")
    answer: str = Field(description="Your answer")


def get_weather(city: str) -> str:
    r"""Get weather information for a city"""
    time.sleep(1)  # Simulate some processing time
    return f"The weather in {city} is sunny, with a temperature of 22°C."


def slow_calculation(n: int) -> str:
    r"""Perform a slow calculation"""
    time.sleep(3)  # Simulate slow calculation
    result = n * n
    return f"The square of {n} is {result}"


def fast_lookup(word: str) -> str:
    r"""Perform a fast lookup"""
    time.sleep(0.5)  # Simulate fast lookup
    return f"Definition of '{word}': a sample definition"


def test_content_accumulation():
    r"""Test that content accumulation works correctly"""
    print("=== Testing Content Accumulation Fix ===")

    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=streaming_model,
    )

    query = "Say hello to me"
    print(f"Query: {query}")
    print("Checking content accumulation:")

    previous_content = ""

    for i, response in enumerate(agent.step(query)):
        if response.msgs:
            current_content = response.msgs[0].content

            # Verify that current content always contains all previous content
            if not current_content.startswith(previous_content):
                print(f"❌ CONTENT ACCUMULATION ERROR at response {i}:")
                print(f"Previous: '{previous_content}'")
                print(f"Current:  '{current_content}'")
                print("Current content should contain all previous content!")
                return False

            # Only print new content
            new_content = current_content[len(previous_content) :]
            if new_content:
                print(new_content, end="", flush=True)

            previous_content = current_content

    print("\n✅ Content accumulation test passed!")
    print("\n" + "=" * 50)
    return True


async def test_async_tool_execution():
    r"""Test async tool execution with proper content accumulation"""
    print("\n=== Testing Async Tool Execution ===")

    agent = ChatAgent(
        system_message="You are a helpful assistant who can perform calculations and lookups.",  # noqa: E501
        model=streaming_model,
        tools=[
            FunctionTool(slow_calculation),
            FunctionTool(fast_lookup),
            FunctionTool(get_weather),
        ],
    )

    query = "Calculate the square of 5, look up the word 'sync', and get weather for Shanghai"  # noqa: E501
    print(f"Query: {query}")
    print("Testing async execution and content accumulation:")

    previous_content = ""

    streaming_response = await agent.astep(query)
    async for response in streaming_response:
        if response.msgs:
            current_content = response.msgs[0].content

            # Verify content accumulation
            if not current_content.startswith(previous_content):
                print("❌ ASYNC CONTENT ACCUMULATION ERROR:")
                print(f"Previous: '{previous_content}'")
                print(f"Current:  '{current_content}'")
                return False

            # Only print new content
            new_content = current_content[len(previous_content) :]
            if new_content:
                print(new_content, end="", flush=True)

            previous_content = current_content

    print("\n" + "=" * 50)
    return True


def test_sync_tool_execution():
    r"""Test sync tool execution with proper content accumulation"""
    print("\n=== Testing Sync Tool Execution ===")

    agent = ChatAgent(
        system_message="You are a helpful assistant who can perform calculations and lookups.",  # noqa: E501
        model=streaming_model,
        tools=[
            FunctionTool(slow_calculation),
            FunctionTool(fast_lookup),
            FunctionTool(get_weather),
        ],
    )

    query = "Calculate the square of 5, look up the word 'sync', and get weather for Shanghai"  # noqa: E501
    print(f"Query: {query}")
    print("Testing sync structured output and content accumulation:")

    previous_content = ""

    for response in agent.step(query):
        if response.msgs:
            current_content = response.msgs[0].content

            # Verify content accumulation
            if not current_content.startswith(previous_content):
                print("❌ SYNC CONTENT ACCUMULATION ERROR:")
                print(f"Previous: '{previous_content}'")
                print(f"Current:  '{current_content}'")
                return False

            # Only print new content
            new_content = current_content[len(previous_content) :]
            if new_content:
                print(new_content, end="", flush=True)

            previous_content = current_content

    print("\n" + "=" * 50)
    return True


def test_sync_structured_output():
    r"""Test sync structured output"""
    print("\n=== Testing Sync Structured Output ===")

    agent = ChatAgent(
        system_message="You are a helpful assistant .", model=streaming_model
    )

    query = "how many r in strawberry?"
    print(f"Query: {query}")
    print("Testing sync structured output and content accumulation:")

    previous_content = ""

    for response in agent.step(query, response_format=Thinking):
        if response.msgs:
            current_content = response.msgs[0].content

            # Verify content accumulation
            if not current_content.startswith(previous_content):
                print("❌ SYNC CONTENT ACCUMULATION ERROR:")
                print(f"Previous: '{previous_content}'")
                print(f"Current:  '{current_content}'")
                return False

            # Only print new content
            new_content = current_content[len(previous_content) :]
            if new_content:
                print(new_content, end="", flush=True)

            previous_content = current_content

    print("\n" + "=" * 50)
    return True


async def test_async_structured_output():
    r"""Test async structured output"""
    print("\n=== Testing Async Structured Output ===")

    agent = ChatAgent(
        system_message="You are a helpful assistant .", model=streaming_model
    )

    query = "how many r in strawberry?"
    print(f"Query: {query}")
    print("Testing async structured output and content accumulation:")

    previous_content = ""

    streaming_response = await agent.astep(query, response_format=Thinking)
    async for response in streaming_response:
        if response.msgs:
            current_content = response.msgs[0].content

            # Verify content accumulation
            if not current_content.startswith(previous_content):
                print("❌ ASYNC CONTENT ACCUMULATION ERROR:")
                print(f"Previous: '{previous_content}'")
                print(f"Current:  '{current_content}'")
                return False

            # Only print new content
            new_content = current_content[len(previous_content) :]
            if new_content:
                print(new_content, end="", flush=True)

            previous_content = current_content

    print("\n" + "=" * 50)
    return True


async def run_all_tests():
    r"""Run all tests"""
    print("🧪 Running Content Accumulation and Tool Execution Tests\n")

    # Test basic content accumulation
    if not test_content_accumulation():
        print("❌ Basic content accumulation test failed!")
        return

    # # Test sync tool execution
    if not test_sync_tool_execution():
        print("❌ Sync tool execution test failed!")
        return

    # Test async tool execution
    if not await test_async_tool_execution():
        print("❌ Async tool execution test failed!")
        return

    # Test sync structured output
    if not test_sync_structured_output():
        print("❌ Sync structured output test failed!")
        return

    # Test async structured output

    if not await test_async_structured_output():
        print("❌ Async structured output test failed!")
        return


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except Exception as e:
        print(f"Test error: {e}")
        import traceback

        traceback.print_exc()
