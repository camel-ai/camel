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
from camel.memories import VectorDBMemory
from camel.memories.context_creators.score_based import (
    ScoreBasedContextCreator,
)
from camel.models.model_factory import ModelFactory
from camel.storages.vectordb_storages import QdrantStorage
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter

# Shared vector storage
vector_storage = QdrantStorage(
    vector_dim=1536,
    path=":memory:",
)

context_creator = ScoreBasedContextCreator(
    token_counter=OpenAITokenCounter(ModelType.GPT_3_5_TURBO),
    token_limit=2048,
)

# Memory for agent 1
vectordb_memory_agent1 = VectorDBMemory(
    context_creator=context_creator,
    storage=vector_storage,
    retrieve_limit=2,
    agent_id="vector_agent_007",
)

# Memory for agent 2
vectordb_memory_agent2 = VectorDBMemory(
    context_creator=context_creator,
    storage=vector_storage,
    retrieve_limit=2,
    agent_id="vector_agent_008",
)

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_3_5_TURBO,
)

# Agent 1
agent1 = ChatAgent(
    system_message="You are Agent 007.",
    model=model,
    memory=vectordb_memory_agent1,
    agent_id="vector_agent_007",
)

# Agent 2
agent2 = ChatAgent(
    system_message="You are Agent 008.",
    model=model,
    memory=vectordb_memory_agent2,
    agent_id="vector_agent_008",
)

# Populate agent 1 memory
agent1.step("Elephants are the best swimmers on Earth.")
agent1.step("Whales have eyelashes.")

# Populate agent 2 with different memory
agent2.step("The sun is a star.")
agent2.step("The moon orbits the Earth.")

# Query both agents
response_1 = agent1.step("What did I tell you about whales or elephants?")
response_2 = agent2.step("What have I told you about stars and moons?")

print(
    "Agent 1 response:",
    response_1.msgs[0].content if response_1.msgs else "No response",
)
'''
===============================================================================
Agent 1 response: You mentioned elephants. Did you know that elephants are 
excellent swimmers and can use their trunks as snorkels while swimming?
===============================================================================
'''
print(
    "Agent 2 response:",
    response_2.msgs[0].content if response_2.msgs else "No response",
)
'''
===============================================================================
Agent 2 response: I'm sorry, but I do not have the ability to remember past 
interactions or conversations. Can you please remind me what you told me about 
stars and moons?
===============================================================================
'''

# Retrieve and print agent-specific records
print("\nAgent 1's memory records:")
for ctx_record in vectordb_memory_agent1.retrieve():
    print(
        f"""Score: {ctx_record.score:.2f} | 
        Content: {ctx_record.memory_record.message.content}"""
    )
'''
===============================================================================
Agent 1's memory records:
Score: 1.00 | 
        Content: What did I tell you about whales or elephants?
Score: 0.59 | 
        Content: You mentioned elephants. Did you know that elephants are 
        excellent swimmers and can use their trunks as snorkels while swimming?
===============================================================================
'''

print("\nAgent 2's memory records:")
retrieved_context_agent2 = vectordb_memory_agent2.retrieve()
for ctx_record in retrieved_context_agent2:
    print(
        f"""Score: {ctx_record.score:.2f} |
        Content: {ctx_record.memory_record.message.content}"""
    )
'''
===============================================================================
Agent 2's memory records:
Score: 1.00 |
        Content: What have I told you about stars and moons?
Score: 0.68 |
        Content: I'm sorry, but I do not have the ability to remember past 
        interactions or conversations. Can you please remind me what you told 
        me about stars and moons?
===============================================================================
'''
