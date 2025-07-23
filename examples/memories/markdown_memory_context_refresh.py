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
from camel.memories import MarkdownMemory
from camel.models.model_factory import ModelFactory
from camel.types import ModelPlatformType, ModelType
from camel.utils import OpenAITokenCounter
from camel.memories.context_creators.score_based import ScoreBasedContextCreator


model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O,
)

# create a summary agent to generate intelligent summaries of the conversation
summary_agent = ChatAgent(
    model=model,
    agent_id="summary_agent_001",
)

# create MarkdownMemory with arbitrary threshold
markdown_memory = MarkdownMemory(
    summary_agent=summary_agent,
    context_creator=ScoreBasedContextCreator(
        token_counter=OpenAITokenCounter(ModelType.GPT_4O),
        token_limit=1024,
    ),
    agent_id="markdown_memory_001",
    context_cleanup_threshold=5,
)

# make the main agent with MarkdownMemory
agent = ChatAgent(
    system_message="You are a helpful AI assistant working on data analysis tasks.",
    model=model,
    memory=markdown_memory,
    agent_id="markdown_agent_001",
)

# 1. start a conversation about data analysis
user_input_1 = "I need help analyzing customer sales data. The dataset has columns: customer_id, product_name, sale_amount, sale_date."
response_1 = agent.step(user_input_1)
print(f"User: {user_input_1}")
print(f"Assistant: {response_1.msgs[0].content}\n")

# 2. continue with more details  
user_input_2 = "I want to find the top 10 customers by total sales amount. Can you help me write a Python script?"
response_2 = agent.step(user_input_2)
print(f"User: {user_input_2}")
print(f"Assistant: {response_2.msgs[0].content}\n")

# 3. add more complexity
user_input_3 = "Also, I need to calculate monthly trends for each product category."
response_3 = agent.step(user_input_3)
print(f"User: {user_input_3}")
print(f"Assistant: {response_3.msgs[0].content}\n")

# 4. continue adding context
user_input_4 = "The data is stored in a PostgreSQL database. Can you modify the script to connect to the database?"
response_4 = agent.step(user_input_4)
print(f"User: {user_input_4}")
print(f"Assistant: {response_4.msgs[0].content}\n")

# 5. this should trigger the automatic context refresh (threshold=5)
user_input_5 = "Now I also need to create visualizations for the sales trends."
response_5 = agent.step(user_input_5)
print(f"User: {user_input_5}")
print(f"Assistant: {response_5.msgs[0].content}\n")

print("=== Context Refresh Triggered! ===")
print("The agent's memory has been automatically cleaned up and saved to markdown files.")
print(f"Summary and history saved in: {agent.memory._markdown_memory_toolkit.working_directory}\n")

# 6. continue conversation after context refresh
user_input_6 = "What visualization libraries do you recommend for this project?"
response_6 = agent.step(user_input_6)
print(f"User: {user_input_6}")
print(f"Assistant: {response_6.msgs[0].content}\n")

#TODO: add outputs