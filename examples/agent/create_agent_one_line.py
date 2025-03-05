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

# Method 1: Initialize the agent with just a string (model name)
# This uses the default platform (OpenAI)
agent1 = ChatAgent("You are a helpful assistant.", model="gpt-4o-mini")

# Method 2: Initialize the agent with a tuple (platform, model)
agent2 = ChatAgent(
    "You are a helpful assistant.", model=("openai", "gpt-4o-mini")
)

# Method 3: Initialize with a pre-created model (original approach)
from camel.models import ModelFactory  # noqa: E402
from camel.types import ModelPlatformType, ModelType  # noqa: E402

model = ModelFactory.create(
    model_platform=ModelPlatformType.OPENAI,  # Using enum
    model_type=ModelType.GPT_4O_MINI,  # Using enum
)
agent3 = ChatAgent("You are a helpful assistant.", model=model)

# Method 4: Initialize with a pre-created model using strings
model = ModelFactory.create(
    model_platform="openai",  # Using string
    model_type="gpt-4o-mini",  # Using string
)
agent4 = ChatAgent("You are a helpful assistant.", model=model)

# Method 5: Default model when none is specified
agent5 = ChatAgent("You are a helpful assistant.")

# Test with a simple question
user_msg = "What is the capital of France?"

# Get the response from one of the agents
response = agent1.step(user_msg)
print("Response from agent1 (string model):")
print(response.msgs[0].content)
"""
Response from agent1 (string model):
The capital of France is Paris.
"""

# You can test other agents similarly:
# response = agent2.step(user_msg)
# print("Response from agent2 (tuple model):")
# print(response.msgs[0].content)
