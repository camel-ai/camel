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
from camel.memories import GraphDBBlock, GraphDBMemory
from camel.memories.context_creators.score_based import (
    ScoreBasedContextCreator,
)
from camel.models.model_factory import ModelFactory
from camel.storages.graph_storages import Neo4jGraph
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter


def main():
    # --- Setup Instructions ---
    # 1. Ensure Neo4j is installed and running locally (e.g., via Neo4j
    # Desktop or Docker).
    # 2. Install the Neo4j Python driver: `pip install neo4j`.
    # 3. Set your OpenAI API key if using OpenAIEmbedding
    #    (default for GraphDBBlock):
    #    export OPENAI_API_KEY='your-api-key-here'
    # 4. Update the Neo4j connection details below to match your instance.

    # Neo4j connection details
    url = (
        "neo4j://localhost:7687"  # Default Bolt URL for a local Neo4j instance
    )
    username = "neo4j"  # Default username
    password = "u4CQDJCKVs@4-LW"  # Replace with your Neo4j password

    # Initialize Neo4jGraph storage
    storage = Neo4jGraph(url=url, username=username, password=password)

    # Create a ScoreBasedContextCreator for token limiting
    context_creator = ScoreBasedContextCreator(
        token_counter=OpenAITokenCounter(ModelType.GPT_4O_MINI),
        token_limit=1024,
    )

    # Build a model
    model = ModelFactory.create(
        model_platform=ModelPlatformType.OPENAI,
        model_type=ModelType.GPT_4O_MINI,
    )

    # Initialize GraphDBBlock with Neo4j storage
    graph_db_block = GraphDBBlock(storage=storage)

    # Initialize GraphDBMemory
    memory = GraphDBMemory(
        context_creator=context_creator,
        graph_db_block=graph_db_block,
        retrieve_limit=5,  # Limit retrieval to 5 records
        agent_id="example_agent",  # Unique identifier for the agent
    )

    # Create a ChatAgent with GraphDBMemory
    agent = ChatAgent(
        system_message="You are a helpful assistant with graph DB memory.",
        agent_id="example_agent",
        model=model,
        memory=memory,
    )

    # Simulate a conversation
    user_input_1 = "Remember that dolphins use echolocation."
    response_1 = agent.step(user_input_1)
    print(
        "Agent response 1:",
        response_1.msgs[0].content if response_1.msgs else "No response",
    )

    user_input_2 = "And whales are the largest mammals."
    response_2 = agent.step(user_input_2)
    print(
        "Agent response 2:",
        response_2.msgs[0].content if response_2.msgs else "No response",
    )

    # Retrieve records based on the last user message
    print("\nRetrieving records from GraphDBMemory...")
    retrieved_records = memory.retrieve()

    # Display the retrieved records
    print(f"Retrieved {len(retrieved_records)} records:")
    for record in retrieved_records:
        print(f"""Role: {record.memory_record.message.role_name}, 
              Content: {record.memory_record.message.content}""")

    # Open http://localhost:7474/browser/ in your browser and go to
    # the Database Information tab on the left hand side to check the graph


if __name__ == "__main__":
    main()
