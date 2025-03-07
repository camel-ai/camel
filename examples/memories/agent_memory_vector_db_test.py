import os
from pathlib import Path

from camel.agents import ChatAgent
from camel.memories import VectorDBMemory
from camel.memories.context_creators.score_based import ScoreBasedContextCreator
from camel.models.model_factory import ModelFactory
from camel.storages.vectordb_storages import QdrantStorage
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter

def test_chat_agent_vectordb_memory_save_and_load():
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
    print("Agent #1 response:", response_1.msgs[0].content if response_1.msgs else "No response")

    user_input_2 = "And whales are the largest mammals."
    response_2 = agent1.step(user_input_2)
    print("Agent #1 response:", response_2.msgs[0].content if response_2.msgs else "No response")

    # 6) SAVE agent1's memory to a JSON file (storing the conversation)
    save_path = Path("./agent1_vectordb_memory.json")
    agent1.save_memory(save_path)
    print(f"Agent #1 memory saved to {save_path}.")

    # 7) Create a new agent, load that JSON memory to confirm retrieval
    new_agent1 = ChatAgent(
        system_message="You are the resurrected assistant #1 with vector DB memory.",
        agent_id="agent_001",   # same agent_id to match the saved records
        model=model,
    )
    # Use a new VectorDBMemory pointing to the same underlying storage
    # (or a new vector store if you prefer, but that won't have the original embeddings)
    new_agent1_memory = VectorDBMemory(
        context_creator=context_creator,
        storage=vector_storage,
        retrieve_limit=2,
        agent_id=new_agent1.agent_id,
    )

    # Load memory from JSON, which replays the stored MemoryRecords
    new_agent1.load_memory_from_path(save_path)

    # 8) Check if the new agent can recall previous info from loaded conversation
    user_input_3 = "What do you remember about marine mammals?"
    response_3 = new_agent1.step(user_input_3)
    print("New Agent #1 response (after loading memory):", response_3.msgs[0].content if response_3.msgs else "No response")

    # Optionally, remove the JSON file
    if os.path.exists(save_path):
        os.remove(save_path)

if __name__ == "__main__":
    test_chat_agent_vectordb_memory_save_and_load()
