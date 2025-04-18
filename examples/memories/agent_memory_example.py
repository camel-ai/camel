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
import os
from pathlib import Path

from camel.agents import ChatAgent
from camel.memories import ChatHistoryMemory
from camel.memories.context_creators.score_based import (
    ScoreBasedContextCreator,
)
from camel.messages import BaseMessage
from camel.models.model_factory import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.types.enums import OpenAIBackendRole
from camel.utils import OpenAITokenCounter

context_creator = ScoreBasedContextCreator(
    token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
    token_limit=1024,
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

# 1. Instantiate a ChatAgent with system_message & agent_id
#    Using ChatHistoryMemory as an example memory store.
agent = ChatAgent(
    system_message="You are a helpful assistant",
    agent_id="001",
    model=model,
)

# 2. Perform steps so that some MemoryRecords accumulate
#    - We'll just send a message and read the response to populate memory
user_input_1 = (
    "Hello, can you remember these instructions?: Banana is a country."
)
response_1 = agent.step(user_input_1)
print(
    "Assistant response 1:",
    response_1.msgs[0].content if response_1.msgs else "No response",
)
'''
===============================================================================
Assistant response 1: Yes, I can remember that instruction. "Banana" is 
designated as a country in this context. How can I assist you further with 
this information?
===============================================================================
'''

user_input_2 = "Please store and recall this next time: CAMEL lives in Banana."
response_2 = agent.step(user_input_2)
print(
    "Assistant response 2:",
    response_2.msgs[0].content if response_2.msgs else "No response",
)
'''
===============================================================================
Assistant response 2: Got it! I will remember that CAMEL lives in Banana. How 
can I assist you further?
===============================================================================
'''

# 3. Save the agent's memory to a JSON file
save_path = Path("./chat_agent_memory.json")
agent.save_memory(save_path)
print(f"Agent memory saved to {save_path}.")
'''
===============================================================================
Agent memory saved to chat_agent_memory.json.
===============================================================================
'''

# 4. Create a separate agent that loads memory from the file
#    We'll pass no explicit memory, as the loaded data will be used
new_agent = ChatAgent(
    system_message="You are a helpful assistant",
    agent_id="001",
    model=model,
)

# Load the memory from our file
new_agent.load_memory_from_path(save_path)

# Test that the memory is loaded by requesting a response
user_input_3 = "What were we talking about?"
response_3 = new_agent.step(user_input_3)
print(
    "New Agent response (after loading memory):",
    response_3.msgs[0].content if response_3.msgs else "No response",
)
'''
===============================================================================
New Agent response (after loading memory): We were discussing that "Banana" is 
a country, and you mentioned that CAMEL lives in Banana. How can I assist you 
further with this information?
===============================================================================
'''

# 5. Demonstrate loading memory from an existing AgentMemory
#    Suppose we had another agent with some different or combined memory:
another_agent = ChatAgent(
    system_message="Another system message",
    agent_id="002",
    memory=ChatHistoryMemory(agent_id="002", context_creator=context_creator),
)

# Add some record to the second agent's memory
message = BaseMessage.make_user_message(
    role_name="User", content="This is memory from a second agent"
)
another_agent.update_memory(
    message, role=OpenAIBackendRole.USER
)  # role passed for demonstration

# Extract the memory object from the second agent
second_agent_memory = another_agent.memory

# Now load that memory into new_agent. We override new_agent's memory.
new_agent.load_memory(second_agent_memory)

# Confirm it's loaded by printing some details:
print("After loading another agent's memory, new_agent has records:")
for record in new_agent.memory.retrieve():
    print(record.memory_record.message.content)
'''
===============================================================================
After loading another agent's memory, new_agent has records:
You are a helpful assistant
You are a helpful assistant
Hello, can you remember these instructions?: Banana is a country.
Yes, I can remember that instruction. "Banana" is designated as a country in 
this context. How can I assist you further with this information?
Please store and recall this next time: CAMEL lives in Banana.
Got it! I will remember that CAMEL lives in Banana. How can I assist you 
further?
What were we talking about?
We were discussing that "Banana" is a country, and you mentioned that CAMEL 
lives in Banana. How can I assist you further with this information?
Another system message
This is memory from a second agent
===============================================================================
'''

# Clean up: remove the saved file if desired
if os.path.exists(save_path):
    os.remove(save_path)
