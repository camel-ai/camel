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
import time
from typing import List
from pydantic import BaseModel, Field

from camel.agents import ChatAgent
from camel.models import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.toolkits import FunctionTool

# Create a streaming model
streaming_model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict={
        "stream": True,
    }
)

# Define structured output model
class TaskAnalysis(BaseModel):
    title: str = Field(description="Task title")
    priority: str = Field(description="Priority: High, Medium, Low")
    estimated_time: str = Field(description="Estimated completion time")
    subtasks: List[str] = Field(description="List of subtasks")

def get_weather(city: str) -> str:
    r"""Get weather information for a city"""
    return f"The weather in {city} is sunny, with a temperature of 22°C."

def example_basic_streaming():
    r"""Test basic streaming functionality"""
    print("=== Testing Basic Streaming Functionality ===")
    
    agent = ChatAgent(
        system_message="You are a helpful assistant.",
        model=streaming_model,
    )
    
    query = "Please write a short poem about spring."
    print(f"Query: {query}")
    print("Streaming response:")
    
    start_time = time.time()
    content_chunks = []
    
    for response in agent.stream(query):
        if response.msgs:
            content = response.msgs[0].content
            # Calculate the new content
            new_content = content[len(''.join(content_chunks)):]
            if new_content:
                print(new_content, end="", flush=True)
                content_chunks.append(new_content)
    
    end_time = time.time()
    print(f"\nTotal time: {end_time - start_time:.2f} seconds")
    print(f"Total word count: {len(''.join(content_chunks))}")
    print("="*50)

def example_tool_streaming():
    r"""Test tool call streaming functionality"""
    print("\n=== Testing Tool Call Streaming Functionality ===")
    
    agent = ChatAgent(
        system_message="You are a helpful assistant who can check the weather.",
        model=streaming_model,
        tools=[FunctionTool(get_weather)]
    )
    
    query = "What is the weather like in Beijing?"
    print(f"Query: {query}")
    print("Streaming response:")
    
    last_model_content = ""
    
    for response in agent.stream(query):
        if response.msgs:
            content = response.msgs[0].content
            
            # Check if this is a tool status message
            if hasattr(response, 'info') and response.info.get('tool_status'):
                # This is a tool status message, print it directly
                print(content, end="", flush=True)
            else:
                # This is model-generated content, print incrementally
                if len(content) > len(last_model_content):
                    new_content = content[len(last_model_content):]
                    print(new_content, end="", flush=True)
                    last_model_content = content
    
    print("\n" + "="*50)

def example_structured_streaming():
    r"""Test streaming structured output"""
    print("\n=== Testing Streaming Structured Output ===")
    
    agent = ChatAgent(
        system_message="You are a project management expert responsible for analyzing tasks.",
        model=streaming_model,
    )
    
    query = "Analyze this task: 'Develop a mobile shopping application.'"
    print(f"Query: {query}")
    print("Streaming structured response:")
    
    try:
        for response in agent.stream(query, response_format=TaskAnalysis):
            if response.msgs and response.msgs[0].parsed:
                # Successfully parsed structured output
                task_analysis = response.msgs[0].parsed
                print(f"\nTitle: {task_analysis.title}")
                print(f"Priority: {task_analysis.priority}")
                print(f"Estimated Time: {task_analysis.estimated_time}")
                print(f"Subtasks: {', '.join(task_analysis.subtasks)}")
                break
            elif response.msgs:
                # Partial content (not fully parsed yet)
                content = response.msgs[0].content
                partial_content = content
                print(f"Content: {partial_content}")
    except Exception as e:
        print(f"Error in structured output test: {e}")
    
    print("="*50)

async def example_async_streaming():
    r"""Test asynchronous streaming functionality"""
    print("\n=== Testing Asynchronous Streaming Functionality ===")
    
    agent = ChatAgent(
        system_message="You are a creative writing assistant.",
        model=streaming_model,
    )
    
    query = "Write a haiku about streaming data."
    print(f"Query: {query}")
    print("Asynchronous streaming response:")
    
    start_time = time.time()
    
    async for response in agent.astream(query):
        if response.msgs:
            content = response.msgs[0].content
            print(content, end="", flush=True)
    
    end_time = time.time()
    print(f"\nAsynchronous total time: {end_time - start_time:.2f} seconds")
    print("="*50)

async def example_async_tool_streaming():
    r"""Test asynchronous tool call streaming functionality"""
    print("\n=== Testing Asynchronous Tool Call Streaming Functionality ===")
    
    agent = ChatAgent(
        system_message="You are a helpful assistant who can check the weather.",
        model=streaming_model,
        tools=[FunctionTool(get_weather)]
    )
    
    query = "What is the weather like in Shanghai and Guangzhou?"
    print(f"Query: {query}")
    print("Asynchronous streaming response:")
    
    last_model_content = ""
    
    async for response in agent.astream(query):
        if response.msgs:
            content = response.msgs[0].content
            
            # Check if this is a tool status message
            if hasattr(response, 'info') and response.info.get('tool_status'):
                # This is a tool status message, print it directly
                print(content, end="", flush=True)
            else:
                # This is model-generated content, print incrementally
                if len(content) > len(last_model_content):
                    new_content = content[len(last_model_content):]
                    print(new_content, end="", flush=True)
                    last_model_content = content

    
    print("\n" + "="*50)

async def run_async_example():
    r"""Run asynchronous example"""
    # await example_async_streaming()
    await example_async_tool_streaming()

if __name__ == "__main__":
    try:
        # Synchronous examples
        example_basic_streaming()
        example_tool_streaming()
        example_structured_streaming()
        
        # Asynchronous example
        asyncio.run(run_async_example())
        
        print("\nAll examples completed!")
    except Exception as e:
        print(f"Test error: {e}")
        import traceback
        traceback.print_exc() 