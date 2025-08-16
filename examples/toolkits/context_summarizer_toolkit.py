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

from camel.agents import ChatAgent
from camel.models.model_factory import ModelFactory
from camel.toolkits.context_summarizer_toolkit import ContextSummarizerToolkit
from camel.types import ModelPlatformType, ModelType

"""
This example demonstrates the ContextSummarizerToolkit, which provides intelligent
context summarization and memory management capabilities for ChatAgent. The toolkit
enables agents to:
1. Manually save conversation memory when context becomes cluttered
2. Load previous context summaries 
3. Search through conversation history using text search
4. Get information about current memory state
5. Check if context should be compressed based on message/token limits

The toolkit is particularly useful when you want the agent to have control over
when to save/refresh memory, rather than relying on automatic thresholds.
"""

# Set up directory for saving context files
memory_dir = "./agent_context_toolkit"

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

# Create agent without auto-compression - we'll use the toolkit for manual
# control
agent = ChatAgent(
    system_message="""You are a helpful AI assistant providing travel advice. 
    
    You have access to context management tools that allow you to:
    - Save conversation memory when context becomes cluttered: 
      summarize_context_and_save_memory()
    - Load previous context: load_memory_context()  
    - Search conversation history: search_conversation_history()
    - Check memory status: get_memory_info()
    - Check if compression is needed: should_compress_context()
    
    Use these tools strategically when conversations become complex or 
    unfocused.""",
    model=model,
    agent_id="context_toolkit_agent_001",
)

# Initialize the context summarizer toolkit
context_toolkit = ContextSummarizerToolkit(
    agent=agent,
    working_directory=memory_dir,
)

# Add toolkit to agent
agent.add_tools(context_toolkit.get_tools())

print("=== ContextSummarizerToolkit Example ===\n")

# 1. Start conversation about travel planning
user_input_1 = (
    "Hello my name is John. I'm planning a trip to Japan in "
    "spring. What are the best cities to visit?"
)
response_1 = agent.step(user_input_1)
print(f"User: {user_input_1}")
print(f"Assistant: {response_1.msgs[0].content}\n")

# 2. Continue with more details
user_input_2 = (
    "How many days should I spend in Tokyo? I'm interested in "
    "culture and food."
)
response_2 = agent.step(user_input_2)
print(f"User: {user_input_2}")
print(f"Assistant: {response_2.msgs[0].content}\n")

# 3. Add more complexity
user_input_3 = "What's the best way to travel between cities in Japan?"
response_3 = agent.step(user_input_3)
print(f"User: {user_input_3}")
print(f"Assistant: {response_3.msgs[0].content}\n")

# 4. Continue building context
user_input_4 = "Should I book accommodations in advance?"
response_4 = agent.step(user_input_4)
print(f"User: {user_input_4}")
print(f"Assistant: {response_4.msgs[0].content}\n")

# 5. Add more topics - this will make context more complex
user_input_5 = "What are some essential Japanese phrases for travelers?"
response_5 = agent.step(user_input_5)
print(f"User: {user_input_5}")
print(f"Assistant: {response_5.msgs[0].content}\n")

print("=== Asking agent to check memory status ===")
# 6. Ask agent to check memory status
user_input_6 = "Can you check our current memory status using your tools?"
response_6 = agent.step(user_input_6)
print(f"User: {user_input_6}")
print(f"Assistant: {response_6.msgs[0].content}\n")

print("=== Suggesting agent save memory ===")
# 7. Suggest agent save memory as conversation is getting complex
user_input_7 = (
    "We've covered a lot of ground on Japan travel. Maybe you "
    "should save our conversation memory to keep things "
    "organized?"
)
response_7 = agent.step(user_input_7)
print(f"User: {user_input_7}")
print(f"Assistant: {response_7.msgs[0].content}\n")

print("=== Starting new topic after memory save ===")
# 8. Start a new topic to test context refresh
user_input_8 = (
    "Now I want to ask about something completely different - can "
    "you help me plan a workout routine?"
)
response_8 = agent.step(user_input_8)
print(f"User: {user_input_8}")
print(f"Assistant: {response_8.msgs[0].content}\n")

print("=== Testing memory recall ===")
# 9. Test if agent can recall previous context when needed
user_input_9 = (
    "Wait, let me go back to my Japan trip. What was my name "
    "again, and what did we discuss about Tokyo?"
)
response_9 = agent.step(user_input_9)
print(f"User: {user_input_9}")
print(f"Assistant: {response_9.msgs[0].content}\n")

print("=== Testing text search ===")
# 10. Test text search functionality
user_input_10 = (
    "Can you search our conversation history for information "
    "about transportation in Japan?"
)
response_10 = agent.step(user_input_10)
print(f"User: {user_input_10}")
print(f"Assistant: {response_10.msgs[0].content}\n")

print("=== Final memory check ===")
# 11. Final memory status check
user_input_11 = (
    "Can you give me a final status of our memory management for this session?"
)
response_11 = agent.step(user_input_11)
print(f"User: {user_input_11}")
print(f"Assistant: {response_11.msgs[0].content}\n")

print("\n=== Example Complete ===")
print("This example demonstrated:")
print("- Manual memory management using the ContextSummarizerToolkit")
print("- Agent-driven decision making about when to save memory")
print("- Context loading and text search capabilities")
print("- Integration of memory tools with natural conversation flow")
print(f"- Memory files saved in: {memory_dir}")