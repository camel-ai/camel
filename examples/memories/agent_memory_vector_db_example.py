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
from camel.memories import VectorDBMemory
from camel.memories.context_creators.score_based import (
    ScoreBasedContextCreator,
)
from camel.models.model_factory import ModelFactory
from camel.storages.vectordb_storages import QdrantStorage
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter

# 1) Create a QdrantStorage in-memory instance
#    (in production, set path to a real directory or remote)
vector_storage = QdrantStorage(
    vector_dim=1536,
    path=":memory:",
)

# 2) Create a ScoreBasedContextCreator for token limiting
context_creator = ScoreBasedContextCreator(
    token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
    token_limit=1024,
)

# 3) Build a model
model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
)

# 4) Create first ChatAgent with VectorDBMemory
agent1 = ChatAgent(
    system_message="You are assistant #1 with vector DB memory.",
    agent_id="agent_001",
    model=model,
)
agent1_memory = VectorDBMemory(
    context_creator=context_creator,
    storage=vector_storage,
    retrieve_limit=2,
    agent_id=agent1.agent_id,  # ensure consistent agent_id
)
agent1.memory = agent1_memory

# 5) Agent #1 accumulates some conversation
user_input_1 = "Remember that dolphins use echolocation."
response_1 = agent1.step(user_input_1)
print(
    "Agent #1 response:",
    response_1.msgs[0].content if response_1.msgs else "No response",
)
'''
===============================================================================
Agent #1 response: Yes, dolphins use echolocation as a way to navigate and 
hunt for food in their aquatic environment. They emit sound waves that travel 
through the water, and when these sound waves hit an object, they bounce back 
to the dolphin. By interpreting the returning echoes, dolphins can determine 
the size, shape, distance, and even the texture of objects around them. This 
ability is particularly useful in murky waters where visibility is limited. 
Echolocation is a remarkable adaptation that enhances their ability to survive 
and thrive in their habitats.
===============================================================================
'''

user_input_2 = "And whales are the largest mammals."
response_2 = agent1.step(user_input_2)
print(
    "Agent #1 response:",
    response_2.msgs[0].content if response_2.msgs else "No response",
)
'''
===============================================================================
Agent #1 response: That's correct! Whales are indeed the largest mammals on 
Earth, with the blue whale being the largest animal known to have ever 
existed. They belong to the order Cetacea, which also includes dolphins and 
porpoises. Both dolphins and whales use echolocation to navigate and hunt for 
food in the ocean, although their methods and the specifics of their 
echolocation can vary. Would you like to know more about either dolphins or 
whales?
===============================================================================
'''

# 6) SAVE agent1's memory to a JSON file (storing the conversation)
save_path = Path("./agent1_vectordb_memory.json")
agent1.save_memory(save_path)
print(f"Agent #1 memory saved to {save_path}.")
'''
===============================================================================
Agent #1 memory saved to agent1_vectordb_memory.json.
===============================================================================
'''

# 7) Create a new agent, load that JSON memory to confirm retrieval
new_agent1 = ChatAgent(
    system_message="""You are the resurrected assistant #1 with 
    vector DB memory.""",
    agent_id="agent_001",  # same agent_id to match the saved records
    model=model,
)
# Use a new VectorDBMemory pointing to the same underlying storage
# (or a new vector store if you prefer, but that won't have the
# original embeddings)
new_agent1_memory = VectorDBMemory(
    context_creator=context_creator,
    storage=vector_storage,
    retrieve_limit=2,
    agent_id=new_agent1.agent_id,
)

new_agent1.memory = new_agent1_memory

# Load memory from JSON, which replays the stored MemoryRecords
new_agent1.load_memory_from_path(save_path)

# 8) Check if the new agent can recall previous info from loaded
# conversation
user_input_3 = "What do you remember about marine mammals?"
response_3 = new_agent1.step(user_input_3)
print(
    "New Agent #1 response (after loading memory):",
    response_3.msgs[0].content if response_3.msgs else "No response",
)
'''
===============================================================================
New Agent #1 response (after loading memory): Marine mammals are a diverse 
group of mammals that are primarily adapted to life in the ocean. They include 
several different orders, each with unique characteristics and adaptations. 
Here are some key points about marine mammals:

1. **Orders of Marine Mammals**:
   - **Cetacea**: This order includes whales, dolphins, and porpoises. They 
   are fully aquatic and have adaptations such as streamlined bodies and the 
   ability to hold their breath for long periods.
   - **Pinnipedia**: This group includes seals, sea lions, and walruses. They 
   are semi-aquatic, spending time both in the water and on land.
   - **Sirenia**: This order includes manatees and dugongs, which are 
   herbivorous and primarily inhabit warm coastal waters and rivers.
   - **Marine Carnivora**: This includes animals like sea otters and polar 
   bears, which rely on marine environments for food.

2. **Adaptations**: Marine mammals have various adaptations for life in the 
water, including:
   - Streamlined bodies for efficient swimming.
   - Blubber for insulation against cold water.
   - Specialized respiratory systems for holding breath and diving.
   - Echolocation in some species (like dolphins and certain whales) for 
   navigation and hunting.

3. **Reproduction**: Most marine mammals give live birth and nurse their young 
with milk. They typically have longer gestation periods compared to 
terrestrial mammals.

4. **Social Structures**: Many marine mammals are social animals, living in 
groups called pods (in the case of dolphins and some whales) or colonies (in 
the case of seals).

5. **Conservation**: Many marine mammals face threats from human activities, 
including habitat loss, pollution, climate change, and hunting. Conservation 
efforts are crucial to protect these species and their habitats.

6. **Intelligence**: Many marine mammals, particularly cetaceans, are known 
for their high intelligence, complex social behaviors, and communication 
skills.

If you have specific questions or topics related to marine mammals that you'd 
like to explore further, feel free to ask!
===============================================================================
'''

# Optionally, remove the JSON file
if os.path.exists(save_path):
    os.remove(save_path)
