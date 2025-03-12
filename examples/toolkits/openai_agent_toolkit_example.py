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

from camel.agents import ChatAgent
from camel.configs import ChatGPTConfig
from camel.models import ModelFactory
from camel.toolkits import OpenAIAgentToolkit
from camel.types import ModelPlatformType, ModelType

# Define system message
sys_msg = """You are a helpful AI assistant that can use OpenAI's agent tools 
including web search and file search."""

# Set model config
model_config_dict = ChatGPTConfig(
    temperature=0.0,
).as_dict()

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,
    model_type=ModelType.GPT_4O_MINI,
    model_config_dict=model_config_dict,
)

# Initialize toolkit and get tools
toolkit = OpenAIAgentToolkit(model=model)
tools = toolkit.get_tools()

# Set agent
agent = ChatAgent(
    system_message=sys_msg,
    model=model,
    tools=tools,
)

# Example 1: Web Search
print("\n=== Using Web Search with Agent ===")
response = agent.step(
    "What was a positive news story from today? Use web search to find out."
)
print("Web Search Response:", response.msg.content)

# Example 2: Direct Web Search
print("\n=== Direct Web Search Usage ===")
web_result = toolkit.web_search(
    "What are the latest developments in renewable energy?"
)
print("Direct Web Search Result:", web_result)

# Example 3: File Search (if configured)
vector_store_id = os.getenv("OPENAI_VECTOR_STORE_ID")

if vector_store_id:
    print("\n=== Using File Search with Agent ===")
    response = agent.step(
        f"Search through my documents for information about climate change. "
        f"Use file search with vector store ID: {vector_store_id}"
    )
    print("File Search Response:", response.msg.content)

    print("\n=== Direct File Search Usage ===")
    file_result = toolkit.file_search(
        query="What are the key points about climate change?",
        vector_store_id=vector_store_id,
    )
    print("Direct File Search Result:", file_result)
else:
    print("\n=== File Search Examples Skipped ===")
    print("Set OPENAI_VECTOR_STORE_ID env var to run file search examples")
