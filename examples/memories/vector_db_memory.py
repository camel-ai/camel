# vector_db_memory_test.py

import os
from pathlib import Path
from camel.agents import ChatAgent
from camel.memories import VectorDBMemory
from camel.memories.context_creators.score_based import ScoreBasedContextCreator
from camel.models.model_factory import ModelFactory
from camel.storages.vectordb_storages import QdrantStorage
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter

def test_chat_agent_vectordb_memory():
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

    print("Agent 1 response:", response_1.msgs[0].content if response_1.msgs else "No response")
    print("Agent 2 response:", response_2.msgs[0].content if response_2.msgs else "No response")

    # Retrieve and print agent-specific records
    print("\nAgent 1's memory records:")
    for ctx_record in vectordb_memory_agent1.retrieve():
        print(f"Score: {ctx_record.score:.2f} | Content: {ctx_record.memory_record.message.content}")

    print("\nAgent 2's memory records:")
    retrieved_context_agent2 = vectordb_memory_agent2.retrieve()
    for ctx_record in retrieved_context_agent2:
        print(f"Score: {ctx_record.score:.2f} | Content: {ctx_record.memory_record.message.content}")

if __name__ == "__main__":
    test_chat_agent_vectordb_memory()
